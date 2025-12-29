#!/usr/bin/env python3
"""Serial data reader for Raspberry Pi 3 - RPL-UDP protocol."""

import argparse
import json
import re
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
    """Parse JSON message from serial data.

    Handles both raw JSON and log-formatted messages like:
    [INFO: App       ] Rx '{"t":"a","s":0,"r":-28}' rssi=-26 from ...
    """
    try:
        text = data.decode("utf-8").strip()
        if not text:
            return None

        # Try to extract JSON from log format: Rx '{"t":...}'
        match = re.search(r"Rx '(\{[^']+\})'", text)
        if match:
            return json.loads(match.group(1))

        # Fallback: try parsing as raw JSON
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
                try:
                    print(data.decode("utf-8").rstrip())
                except UnicodeDecodeError:
                    print(f"[RAW] {data.hex()}")


def main():
    parser = argparse.ArgumentParser(description="Serial data reader for RPL-UDP protocol")
    parser.add_argument(
        "-c", "--config",
        choices=["pi", "mac"],
        default="pi",
        help="Config to use: 'pi' (default) or 'mac'"
    )
    parser.add_argument(
        "-p", "--port",
        help="Override serial port (e.g., /dev/tty.usbmodem0001)"
    )
    args = parser.parse_args()

    # Select config file
    config_dir = Path(__file__).parent
    if args.config == "mac":
        config_path = config_dir / "config-mac.yaml"
    else:
        config_path = config_dir / "config.yaml"

    config = load_config(config_path)

    # Override port if specified
    if args.port:
        config["serial"]["port"] = args.port

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
