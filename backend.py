#!/usr/bin/env python3
"""FastAPI backend with WebSocket for RPL-UDP sensor data."""

import argparse
import asyncio
import json
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import serial
import yaml
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


# Connected WebSocket clients
clients: set[WebSocket] = set()

# Latest sensor data (for new clients)
latest_data: dict[str, Any] = {}

# Serial connection
ser: serial.Serial | None = None

# Packet stats for PRR calculation
packet_stats: dict[str, Any] = {
    "first_seq": None,
    "last_seq": None,
    "received": 0,
    "expected": 0,
    "prr": 100.0,
    "button_count": 0,
}

# RSSI history (last 60 readings)
rssi_history: list[dict] = []


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def parse_message(data: bytes) -> dict | None:
    """Parse JSON message from serial data."""
    try:
        text = data.decode("utf-8").strip()
        if not text:
            return None

        # Try to extract JSON from log format: Rx '{"t":...}'
        match = re.search(r"Rx '(\{[^']+\})'", text)
        if match:
            return json.loads(match.group(1))

        # Fallback: try parsing as raw JSON
        if text.startswith("{"):
            return json.loads(text)

        # Return as log message
        return {"type": "log", "message": text}
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


async def broadcast(message: dict):
    """Broadcast message to all connected WebSocket clients."""
    if not clients:
        return

    data = json.dumps(message)
    disconnected = set()

    for client in clients:
        try:
            await client.send_text(data)
        except Exception:
            disconnected.add(client)

    clients.difference_update(disconnected)


def update_packet_stats(seq: int) -> dict:
    """Update packet reception statistics based on sequence number."""
    global packet_stats

    if packet_stats["first_seq"] is None:
        packet_stats["first_seq"] = seq
        packet_stats["last_seq"] = seq
        packet_stats["received"] = 1
        packet_stats["expected"] = 1
    else:
        packet_stats["received"] += 1
        if seq > packet_stats["last_seq"]:
            packet_stats["last_seq"] = seq
        packet_stats["expected"] = packet_stats["last_seq"] - packet_stats["first_seq"] + 1

    if packet_stats["expected"] > 0:
        packet_stats["prr"] = round(100.0 * packet_stats["received"] / packet_stats["expected"], 1)

    return packet_stats.copy()


def format_sensor_data(msg: dict) -> dict:
    """Format raw message into frontend-friendly data."""
    msg_type = msg.get("t")

    # Update packet stats for any message with sequence number
    seq = msg.get("s")
    stats = update_packet_stats(seq) if seq is not None else None

    if msg_type == "k":  # Keepalive
        rssi = msg.get("r")

        # Store RSSI history
        if rssi is not None and seq is not None:
            rssi_history.append({"seq": seq, "rssi": rssi})
            # Keep only last 60 readings
            if len(rssi_history) > 60:
                rssi_history.pop(0)

        data = {
            "type": "keepalive",
            "seq": seq,
            "rssi": rssi,
            "battery_mv": msg.get("bat"),
            "temp_c": msg.get("tmp", 0) / 100.0 if "tmp" in msg else None,
            "humidity_pct": msg.get("hum", 0) / 100.0 if "hum" in msg else None,
            "light_lux": msg.get("lgt", 0) / 100.0 if "lgt" in msg else None,
            "stats": stats,
        }
        # Update latest data
        latest_data.update({k: v for k, v in data.items() if v is not None})
        return data

    elif msg_type == "b":  # Button
        packet_stats["button_count"] += 1
        return {
            "type": "button",
            "seq": seq,
            "button_id": msg.get("b"),
            "stats": packet_stats.copy(),
        }

    elif msg_type == "a":  # Ack
        return {
            "type": "ack",
            "seq": seq,
            "rssi": msg.get("r"),
            "stats": stats,
        }

    elif msg.get("type") == "log":
        return msg

    return {"type": "unknown", "raw": msg}


async def serial_reader(config: dict):
    """Background task to read serial data."""
    global ser

    cfg = config["serial"]
    print(f"Connecting to {cfg['port']} at {cfg['baudrate']} baud...")

    try:
        ser = serial.Serial(
            port=cfg["port"],
            baudrate=cfg["baudrate"],
            bytesize=cfg["bytesize"],
            parity=cfg["parity"],
            stopbits=cfg["stopbits"],
            timeout=0.1,  # Short timeout for async
        )
        print("Serial connected.")

        while True:
            if ser.in_waiting > 0:
                data = ser.readline()
                if data:
                    # Print raw data for debugging
                    try:
                        line = data.decode("utf-8").rstrip()
                        print(f"[SERIAL] {line}")
                    except UnicodeDecodeError:
                        print(f"[SERIAL] (binary) {data.hex()}")

                    msg = parse_message(data)
                    if msg:
                        formatted = format_sensor_data(msg)
                        await broadcast(formatted)
            else:
                await asyncio.sleep(0.01)  # Yield to other tasks

    except serial.SerialException as e:
        print(f"Serial error: {e}")
        await broadcast({"type": "error", "message": str(e)})
    except asyncio.CancelledError:
        if ser:
            ser.close()
        raise


# Store background task reference
serial_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage serial reader lifecycle."""
    global serial_task

    # Start serial reader
    config_path = app.state.config_path
    config = load_config(config_path)

    if app.state.port_override:
        config["serial"]["port"] = app.state.port_override

    print(f"Starting serial reader task for {config['serial']['port']}...")
    serial_task = asyncio.create_task(serial_reader(config))
    print("Serial reader task created.")

    yield

    # Cleanup
    if serial_task:
        serial_task.cancel()
        try:
            await serial_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="DroneCom", lifespan=lifespan)

# CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time sensor data."""
    await websocket.accept()
    clients.add(websocket)

    # Send initial state to new client
    init_data = {
        "type": "init",
        "latest": latest_data,
        "stats": packet_stats,
        "rssi_history": rssi_history,
    }
    await websocket.send_text(json.dumps(init_data))

    try:
        while True:
            # Handle incoming messages (commands from frontend)
            data = await websocket.receive_text()
            msg = json.loads(data)

            # Handle commands
            if msg.get("cmd") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif msg.get("cmd") == "send":
                # Send text to serial port
                text = msg.get("text", "")
                if ser and ser.is_open and text:
                    ser.write((text + "\n").encode("utf-8"))
                    print(f"[SEND] {text}")

    except WebSocketDisconnect:
        clients.discard(websocket)
    except Exception:
        clients.discard(websocket)


@app.get("/api/status")
async def get_status():
    """Get current status and latest sensor data."""
    return {
        "connected_clients": len(clients),
        "serial_connected": ser is not None and ser.is_open,
        "latest_data": latest_data,
    }


# Serve React frontend (production)
frontend_path = Path(__file__).parent / "frontend" / "dist"
if frontend_path.exists():
    app.mount("/assets", StaticFiles(directory=frontend_path / "assets"), name="assets")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(frontend_path / "index.html")

    @app.get("/demo")
    async def serve_demo():
        return FileResponse(frontend_path / "index.html")


def main():
    import uvicorn

    parser = argparse.ArgumentParser(description="DroneCom backend server")
    parser.add_argument(
        "-c", "--config",
        choices=["pi", "mac", "win"],
        default="pi",
        help="Config to use: 'pi' (default), 'mac', or 'win'"
    )
    parser.add_argument(
        "-p", "--port",
        help="Override serial port"
    )
    args = parser.parse_args()

    # Select config file
    config_dir = Path(__file__).parent
    if args.config == "mac":
        config_path = config_dir / "config-mac.yaml"
    elif args.config == "win":
        config_path = config_dir / "config-win.yaml"
    else:
        config_path = config_dir / "config.yaml"

    # Load config to get server settings
    config = load_config(config_path)
    server_cfg = config.get("server", {})
    host = server_cfg.get("host", "0.0.0.0")
    web_port = server_cfg.get("port", 8080)

    # Store config in app state
    app.state.config_path = config_path
    app.state.port_override = args.port

    print(f"Starting DroneCom backend on http://{host}:{web_port}")
    uvicorn.run(app, host=host, port=web_port)


if __name__ == "__main__":
    main()
