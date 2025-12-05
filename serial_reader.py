#!/usr/bin/env python3
"""Serial data reader for Raspberry Pi 3 - RPL-UDP protocol."""

import json
import serial
import yaml
from pathlib import Path

from handlers import process_message


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def create_serial_connection(config: dict) -> serial.Serial:
    """Create serial connection from config."""
    cfg = config["serial"]
    return serial.Serial(
        port=cfg["port"],
        baudrate=cfg["baudrate"],
        bytesize=cfg["bytesize"],
        parity=cfg["parity"],
        stopbits=cfg["stopbits"],
        timeout=cfg["timeout"],
    )


def parse_message(data: bytes) -> dict | None:
    """Parse JSON message from serial data."""
    try:
        text = data.decode("utf-8").strip()
        if not text:
            return None
        return json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def read_loop(ser: serial.Serial):
    """Main read loop for serial data."""
    print("Reading data (Ctrl+C to stop)...")

    while True:
        if ser.in_waiting > 0:
            data = ser.readline()
            msg = parse_message(data)
            if msg:
                process_message(msg)
            elif data.strip():
                print(f"[RAW] {data.hex()}")


def main():
    config_path = Path(__file__).parent / "config.yaml"
    config = load_config(config_path)

    print(f"Connecting to {config['serial']['port']} at {config['serial']['baudrate']} baud...")

    try:
        with create_serial_connection(config) as ser:
            print("Connected.")
            read_loop(ser)
    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
