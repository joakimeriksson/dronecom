"""Tests for serial reader and protocol handlers."""

from pathlib import Path
import pytest
from serial_reader import parse_message
from handlers import process_message, HANDLERS


class TestParseMessage:
    """Tests for parse_message function."""

    def test_parse_log_format_ack(self):
        """Parse ACK message from log format."""
        data = b"[INFO: App       ] Rx '{\"t\":\"a\",\"s\":0,\"r\":-28}' rssi=-26 from fd00::212:4b00:1cab:6bc0\n"
        result = parse_message(data)
        assert result == {"t": "a", "s": 0, "r": -28}

    def test_parse_log_format_keepalive(self):
        """Parse keepalive message from log format."""
        data = b"[INFO: App       ] Rx '{\"t\":\"k\",\"s\":5,\"r\":-70,\"bat\":3300}' rssi=-65 from fd00::1\n"
        result = parse_message(data)
        assert result == {"t": "k", "s": 5, "r": -70, "bat": 3300}

    def test_parse_log_format_button(self):
        """Parse button message from log format."""
        data = b"[INFO: App       ] Rx '{\"t\":\"b\",\"s\":3,\"b\":0}' rssi=-50 from fd00::1\n"
        result = parse_message(data)
        assert result == {"t": "b", "s": 3, "b": 0}

    def test_parse_raw_json(self):
        """Parse raw JSON (backwards compatibility)."""
        data = b'{"t":"a","s":1,"r":-30}\n'
        result = parse_message(data)
        assert result == {"t": "a", "s": 1, "r": -30}

    def test_parse_empty_line(self):
        """Empty line returns None."""
        assert parse_message(b"") is None
        assert parse_message(b"\n") is None
        assert parse_message(b"   \n") is None

    def test_parse_non_json_line(self):
        """Non-JSON log line without Rx returns None."""
        data = b"[INFO: App       ] Stats: Tx=0 Rx=0\n"
        assert parse_message(data) is None

    def test_parse_tx_line(self):
        """Tx log line (no JSON) returns None."""
        data = b"[INFO: App       ] Tx keepalive seq=0 rssi=0 tmp=0.-1 hum=0.-1 bat=3015mV\n"
        assert parse_message(data) is None

    def test_parse_invalid_json(self):
        """Invalid JSON returns None."""
        data = b"[INFO: App       ] Rx '{invalid}' rssi=-26\n"
        assert parse_message(data) is None

    def test_parse_invalid_utf8(self):
        """Invalid UTF-8 returns None."""
        data = b"\xff\xfe invalid bytes"
        assert parse_message(data) is None


class TestSampleLog:
    """Tests using sample log file."""

    @pytest.fixture
    def sample_log_path(self):
        return Path(__file__).parent / "tests" / "sample.log"

    def test_parse_sample_log(self, sample_log_path):
        """Parse all messages from sample log file."""
        with open(sample_log_path) as f:
            lines = f.readlines()

        parsed = [parse_message(line.encode()) for line in lines]
        messages = [m for m in parsed if m is not None]

        # Should find 4 Rx messages: 1 button + 3 acks
        assert len(messages) == 4

        # First is button press
        assert messages[0] == {"t": "b", "s": 5, "b": 0}

        # Rest are acks
        assert messages[1] == {"t": "a", "s": 0, "r": -28}
        assert messages[2] == {"t": "a", "s": 1, "r": -27}
        assert messages[3] == {"t": "a", "s": 2, "r": -30}

    def test_process_sample_log(self, sample_log_path, capsys):
        """Process all messages from sample log and verify output."""
        with open(sample_log_path) as f:
            lines = f.readlines()

        for line in lines:
            msg = parse_message(line.encode())
            if msg:
                process_message(msg)

        captured = capsys.readouterr()
        assert "[BUTTON] seq=5 button=0" in captured.out
        assert "[ACK] seq=0 rssi=-28dBm" in captured.out
        assert "[ACK] seq=1 rssi=-27dBm" in captured.out
        assert "[ACK] seq=2 rssi=-30dBm" in captured.out


class TestHandlers:
    """Tests for message handlers."""

    def test_handler_mapping(self):
        """Verify handler mapping exists for known types."""
        assert "k" in HANDLERS
        assert "b" in HANDLERS
        assert "a" in HANDLERS

    def test_keepalive_handler(self, capsys):
        """Test keepalive handler output."""
        msg = {"t": "k", "s": 5, "r": -70, "bat": 3300, "tmp": 2500, "hum": 6500}
        process_message(msg)
        captured = capsys.readouterr()
        assert "[KEEPALIVE]" in captured.out
        assert "seq=5" in captured.out
        assert "rssi=-70dBm" in captured.out
        assert "bat=3.30V" in captured.out
        assert "temp=25.0C" in captured.out
        assert "hum=65.0%" in captured.out

    def test_button_handler(self, capsys):
        """Test button handler output."""
        msg = {"t": "b", "s": 3, "b": 0}
        process_message(msg)
        captured = capsys.readouterr()
        assert "[BUTTON]" in captured.out
        assert "seq=3" in captured.out
        assert "button=0" in captured.out

    def test_ack_handler(self, capsys):
        """Test ack handler output."""
        msg = {"t": "a", "s": 1, "r": -28}
        process_message(msg)
        captured = capsys.readouterr()
        assert "[ACK]" in captured.out
        assert "seq=1" in captured.out
        assert "rssi=-28dBm" in captured.out

    def test_unknown_handler(self, capsys):
        """Test unknown message type handler."""
        msg = {"t": "x", "data": "test"}
        process_message(msg)
        captured = capsys.readouterr()
        assert "[UNKNOWN]" in captured.out

    def test_missing_type_field(self, capsys):
        """Message without type field goes to unknown handler."""
        msg = {"s": 1, "r": -28}
        process_message(msg)
        captured = capsys.readouterr()
        assert "[UNKNOWN]" in captured.out
