"""Message handlers for RPL-UDP protocol."""


def handle_keepalive(msg: dict):
    """Handle keepalive message with sensor data."""
    parts = [f"seq={msg.get('s', '?')}"]

    if "r" in msg:
        parts.append(f"rssi={msg['r']}dBm")
    if "tmp" in msg:
        parts.append(f"temp={msg['tmp'] / 100.0:.1f}C")
    if "hum" in msg:
        parts.append(f"hum={msg['hum'] / 100.0:.1f}%")
    if "bat" in msg:
        parts.append(f"bat={msg['bat'] / 1000.0:.2f}V")

    print(f"[KEEPALIVE] {' '.join(parts)}")


def handle_button(msg: dict):
    """Handle button press event."""
    seq = msg.get("s", "?")
    button_id = msg.get("b", "?")
    print(f"[BUTTON] seq={seq} button={button_id}")


def handle_ack(msg: dict):
    """Handle acknowledgment message."""
    seq = msg.get("s", "?")
    rssi = msg.get("r", "?")
    print(f"[ACK] seq={seq} rssi={rssi}dBm")


def handle_unknown(msg: dict):
    """Handle unknown message type."""
    print(f"[UNKNOWN] {msg}")


# Message type to handler mapping
HANDLERS = {
    "k": handle_keepalive,
    "b": handle_button,
    "a": handle_ack,
}


def process_message(msg: dict):
    """Process a parsed message based on type."""
    msg_type = msg.get("t")
    handler = HANDLERS.get(msg_type, handle_unknown)
    handler(msg)
