# DroneCom

Real-time sensor dashboard for RPL-UDP wireless sensor networks. Displays RSSI, packet reception ratio, temperature, humidity, light, and battery data from CC1352R SensorTag nodes over SubGHz radio.

## Features

- **Web Dashboard** - Real-time sensor cards, RSSI graph, event log
- **Demo Page** - Minimalistic display for presentations (RSSI + packet loss)
- **Terminal** - Send shell commands to nodes via web interface
- **Packet Stats** - PRR tracking, button press counter
- **Multi-platform** - Runs on Raspberry Pi, Mac, Windows, Linux

## Requirements

- [Pixi](https://pixi.sh) package manager
- Serial connection to CC1352R SensorTag (USB or UART)

## Quick Start

### Install Pixi

**Mac/Linux:**
```bash
curl -fsSL https://pixi.sh/install.sh | bash
```

**Windows (PowerShell):**
```powershell
iwr -useb https://pixi.sh/install.ps1 | iex
```

### Run

```bash
# Clone and enter directory
cd dronecom

# Install dependencies and start (Mac)
pixi run serve-mac

# Or for Raspberry Pi
pixi run serve
```

Open http://localhost:8080 in your browser.

## Configuration

### Mac

Edit `config-mac.yaml`:
```yaml
serial:
  port: "/dev/tty.usbmodemXXXXXX"  # Find with: ls /dev/tty.usbmodem*
  baudrate: 115200

server:
  host: "0.0.0.0"
  port: 8080
```

### Raspberry Pi

Edit `config.yaml`:
```yaml
serial:
  port: "/dev/serial0"
  baudrate: 115200

server:
  host: "0.0.0.0"
  port: 8080
```

Enable serial port:
```bash
sudo raspi-config
# Interface Options -> Serial Port -> No login shell, Yes enable hardware
sudo usermod -a -G dialout $USER
# Reboot
```

### Windows

Create `config-win.yaml`:
```yaml
serial:
  port: "COM3"  # Find in Device Manager -> Ports
  baudrate: 115200
  bytesize: 8
  parity: "N"
  stopbits: 1
  timeout: 1.0

server:
  host: "0.0.0.0"
  port: 8080
```

Run with:
```bash
pixi run python backend.py -c win
```

Or add to `pixi.toml`:
```toml
serve-win = { cmd = "python backend.py -c win", depends-on = ["frontend-build"] }
```

## Pixi Tasks

| Task | Description |
|------|-------------|
| `pixi run serve-mac` | Build frontend and start server (Mac) |
| `pixi run serve` | Build frontend and start server (Raspberry Pi) |
| `pixi run backend-mac` | Start backend only (Mac) |
| `pixi run run-mac` | CLI serial reader only (Mac) |
| `pixi run frontend-build` | Build React frontend |
| `pixi run test` | Run tests |

## Web Interface

- **Dashboard** (`/`) - Full sensor display with graphs
- **Demo** (`/demo`) - Minimalistic RSSI + packet loss for presentations

### Dashboard Features

- Temperature, humidity, light, battery, RSSI cards
- Packet reception ratio (PRR) tracking
- Button press counter
- RSSI history graph (last 60 readings)
- Event log with all messages
- Terminal input for shell commands (`help`, `interval 30`, `log mac 4`, etc.)

### Demo Page Features

- Large RSSI display with signal quality indicator
- Packet loss counter
- "Packets delayed - probable loss" warning after 15s silence
- Clean design for presentations

## Protocol

JSON messages from RPL-UDP nodes:

| Type | Description | Fields |
|------|-------------|--------|
| `k` | Keepalive | `s` (seq), `r` (rssi), `bat` (mV), `tmp` (C×100), `hum` (%×100), `lgt` (centilux) |
| `b` | Button press | `s` (seq), `b` (button id) |
| `a` | Acknowledgment | `s` (seq), `r` (rssi) |

Example messages:
```json
{"t":"k","s":5,"r":-70,"bat":3300,"tmp":2450,"hum":5500,"lgt":18900}
{"t":"b","s":3,"b":0}
{"t":"a","s":3,"r":-65}
```

## Project Structure

```
dronecom/
├── backend.py          # FastAPI server with WebSocket
├── serial_reader.py    # CLI serial reader (standalone)
├── handlers.py         # Message handlers for CLI
├── config.yaml         # Raspberry Pi config
├── config-mac.yaml     # Mac config
├── pixi.toml           # Pixi dependencies and tasks
└── frontend/
    ├── src/
    │   ├── App.jsx     # Main dashboard
    │   ├── Demo.jsx    # Demo page
    │   └── *.css       # Styles
    ├── package.json
    └── vite.config.js
```

## Troubleshooting

### No serial data
- Check serial port path in config
- Verify SensorTag is connected and powered
- Try `ls /dev/tty.usbmodem*` (Mac) or check Device Manager (Windows)

### WebSocket not connecting
- Check browser console for errors
- Verify backend is running on correct port
- Check firewall settings

### Packets delayed warning
- Normal if SensorTag is powered off or out of range
- Check radio interference
- Verify RPL network is formed (run `routes` command)
