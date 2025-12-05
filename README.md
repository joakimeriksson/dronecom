# dronecom

Experimental drone communication - serial data reader for Raspberry Pi 3.

## Requirements

- Raspberry Pi 3
- [Pixi](https://pixi.sh) package manager

## Setup

Install pixi (if not already installed):
```bash
curl -fsSL https://pixi.sh/install.sh | bash
```

Install dependencies:
```bash
pixi install
```

### Raspberry Pi Serial Port Setup

Enable the serial port:
```bash
sudo raspi-config
# Interface Options -> Serial Port -> No login shell, Yes enable hardware
```

Add your user to the dialout group:
```bash
sudo usermod -a -G dialout $USER
```

Reboot or log out/in for the group change to take effect.

## Configuration

Edit `config.yaml` to set serial port parameters:

```yaml
serial:
  port: "/dev/serial0"
  baudrate: 115200
  bytesize: 8
  parity: "N"
  stopbits: 1
  timeout: 1.0
```

## Usage

```bash
pixi run
```

## Protocol

The reader handles JSON messages from RPL-UDP nodes:

| Type | Description | Fields |
|------|-------------|--------|
| `k` | Keepalive | `s` (seq), `r` (rssi), `bat` (mV), `tmp` (C×100), `hum` (%×100) |
| `b` | Button press | `s` (seq), `b` (button id) |
| `a` | Acknowledgment | `s` (seq), `r` (rssi) |

Example messages:
```json
{"t":"k","s":5,"r":-70,"bat":3300}
{"t":"b","s":3,"b":0}
{"t":"a","s":3,"r":-65}
```

## Project Structure

```
serial_reader.py   # Serial connection and read loop
handlers.py        # Message handlers
config.yaml        # Serial port configuration
pixi.toml          # Pixi environment
```
