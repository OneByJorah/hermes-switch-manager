"""Serial console client for out-of-band switch management.

Ported from nethermind project. Enables direct interaction with network
switches via physical serial connections (RS-232, USB-to-serial).

Use cases:
- Initial device provisioning before IP/SSH is configured
- Recovery scenarios (password recovery, boot issues)
- Out-of-band management when network is down
- Lab environments with direct console access
"""
import logging
import time
from typing import Optional
import serial
from serial.tools.list_ports import comports

logger = logging.getLogger(__name__)


class SerialClient:
    """Client for serial console connections to network devices."""

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        parity: str = serial.PARITY_NONE,
        stopbits: int = serial.STOPBITS_ONE,
        bytesize: int = serial.EIGHTBITS,
        timeout: float = 10.0,
    ):
        self.port = port
        self.baudrate = baudrate
        self.parity = parity
        self.stopbits = stopbits
        self.bytesize = bytesize
        self.timeout = timeout
        self._connection: Optional[serial.Serial] = None

    @staticmethod
    def list_ports() -> list[dict]:
        """List available serial ports."""
        ports = comports()
        return [
            {
                "device": p.device,
                "description": p.description,
                "hwid": p.hwid,
                "manufacturer": p.manufacturer,
            }
            for p in ports
        ]

    def connect(self) -> bool:
        """Open serial connection."""
        try:
            self._connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                parity=self.parity,
                stopbits=self.stopbits,
                bytesize=self.bytesize,
                timeout=self.timeout,
            )
            logger.info("Connected to serial port %s at %d baud", self.port, self.baudrate)
            return True
        except serial.SerialException as e:
            logger.error("Failed to connect to %s: %s", self.port, e)
            return False

    def disconnect(self):
        """Close serial connection."""
        if self._connection and self._connection.is_open:
            self._connection.close()
            logger.info("Disconnected from %s", self.port)

    def send_command(self, command: str, wait_time: float = 1.0) -> str:
        """Send a command and return the response."""
        if not self._connection or not self._connection.is_open:
            raise ConnectionError("Serial port not connected")

        self._connection.write(f"{command}\n".encode())
        time.sleep(wait_time)

        response = b""
        while self._connection.in_waiting:
            response += self._connection.read(self._connection.in_waiting)
            time.sleep(0.1)

        return response.decode(errors="replace")

    def send_commands(self, commands: list[str], wait_time: float = 1.0) -> str:
        """Send multiple commands and return combined response."""
        responses = []
        for cmd in commands:
            resp = self.send_command(cmd, wait_time)
            responses.append(resp)
        return "\n".join(responses)

    def send_config_lines(self, lines: list[str], save: bool = True) -> dict:
        """Send configuration lines and optionally save config."""
        responses = []
        for line in lines:
            resp = self.send_command(line, wait_time=0.5)
            responses.append(resp)

        if save:
            # Common save commands across vendors
            save_cmds = ["write memory", "copy running-config startup-config", "save"]
            for cmd in save_cmds:
                resp = self.send_command(cmd, wait_time=2.0)
                if "error" not in resp.lower():
                    responses.append(f"Config saved with: {cmd}")
                    break

        return {
            "success": True,
            "port": self.port,
            "lines_sent": len(lines),
            "config_saved": save,
            "responses": responses,
        }

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False


def parse_switch_config(model_output: str) -> dict:
    """Parse show command output into structured data."""
    result = {
        "raw_output": model_output,
        "interfaces": [],
        "vlans": [],
        "version": "",
    }

    lines = model_output.split("\n")
    current_section = None

    for line in lines:
        line = line.strip()

        if "Interface" in line and "Status" in line:
            current_section = "interfaces"
        elif "VLAN" in line and "Name" in line:
            current_section = "vlans"
        elif line.startswith("Cisco") or line.startswith("HP") or line.startswith("Arista"):
            result["version"] = line

        if current_section == "interfaces" and line and not line.startswith("Interface"):
            parts = line.split()
            if len(parts) >= 3:
                result["interfaces"].append({
                    "name": parts[0],
                    "status": parts[1],
                    "vlan": parts[2] if len(parts) > 2 else "",
                })

    return result
