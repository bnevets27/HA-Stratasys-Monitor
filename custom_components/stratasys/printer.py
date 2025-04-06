"""Stratasys Printer Monitor."""

import socket
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum, auto
import json
from pathlib import Path
import sys

class PrinterError(Exception):
    """Base exception for printer errors."""
    pass

class ConnectionError(PrinterError):
    """Connection-related errors."""
    pass

class ProtocolError(PrinterError):
    """Protocol sequence errors."""
    pass

class PrinterStatus(Enum):
    """Printer status states."""
    IDLE = auto()
    BUILDING = auto()
    ERROR = auto()
    UNKNOWN = auto()

@dataclass
class PrinterConfig:
    """Printer configuration settings."""
    host: str
    port: int
    timeout: float = 1.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    packet_size: int = 64
    status_file: str = 'status.sts'
    log_level: int = logging.INFO

class StratasysMonitor:
    """Stratasys printer monitor with robust error handling and configuration."""

    PROTOCOL_DELAYS = {
        'command': 0.004,
        'response': 0.018,
        'transfer': 0.046
    }

    def __init__(self, config: Optional[PrinterConfig] = None):
        self.config = config or PrinterConfig(host='127.0.0.1', port=53742)
        self.sock: Optional[socket.socket] = None
        self.connected: bool = False
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure logging with rotation and proper formatting."""
        log_path = Path('/config/logs')
        log_path.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=self.config.log_level,
            format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
            handlers=[
                logging.FileHandler(log_path / 'stratasys_monitor.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('StratasysMonitor')

    async def _send_packet(self, data: bytes, expected_response: Optional[bytes] = None) -> Optional[bytes]:
        """Send a packet and optionally wait for a specific response."""
        try:
            self.sock.send(data.ljust(self.config.packet_size, b'\x00'))

            if expected_response:
                response = self.sock.recv(self.config.packet_size)
                if expected_response not in response:
                    raise ProtocolError(f"Expected {expected_response}, got {response}")
                return response
            return None

        except socket.timeout:
            raise ConnectionError("Timeout sending packet")
        except socket.error as e:
            raise ConnectionError(f"Socket error: {e}")

    async def _get_printer_data(self) -> bytes:
        """Execute the full printer protocol sequence."""
        try:
            # Sequence 1-2: Initial commands
            await self._send_packet(b'GetFile')
            await asyncio.sleep(self.PROTOCOL_DELAYS['command'])

            await self._send_packet(b'status.sts')
            await asyncio.sleep(self.PROTOCOL_DELAYS['command'])

            # Sequence 3-5: Handshake
            await self._send_packet(b'NA')
            await asyncio.sleep(self.PROTOCOL_DELAYS['response'])

            # Wait for SendFile response
            sendfile = self.sock.recv(self.config.packet_size)
            if b'SendFile' not in sendfile:
                raise ProtocolError(f"Expected SendFile, got: {sendfile}")
            await asyncio.sleep(self.PROTOCOL_DELAYS['transfer'])

            # Wait for NA response
            na = self.sock.recv(self.config.packet_size)
            if b'NA' not in na:
                raise ProtocolError(f"Expected NA, got: {na}")

            # Send OK and get size
            await self._send_packet(b'OK')
            size_data = self.sock.recv(self.config.packet_size)
            if not size_data:
                raise ProtocolError("No size data received")

            try:
                size_str = size_data.strip().split(b' ')[0]
                expected_size = int(size_str)
            except (ValueError, IndexError):
                raise ProtocolError(f"Invalid size data: {size_data}")

            # Send final OK
            await self._send_packet(b'OK')

            # Receive data chunks
            data = bytearray()
            self.sock.settimeout(5.0)

            while len(data) < expected_size:
                chunk = self.sock.recv(1460)
                if not chunk:
                    if len(data) == 0:
                        raise ProtocolError("Connection closed without data")
                    break
                data.extend(chunk)

                if b'Transferred:' in chunk:
                    break

            self.logger.debug(f"Received {len(data)} bytes of {expected_size} expected")

            confirm_msg = f"Transferred: {len(data)}".encode()
            await self._send_packet(confirm_msg)

            return bytes(data)

        except Exception as e:
            self.logger.error(f"Protocol sequence failed: {e}")
            raise ProtocolError(f"Protocol sequence failed: {e}")
        finally:
            if self.sock:
                self.sock.settimeout(self.config.timeout)

    def _parse_status(self, data: bytes) -> Dict[str, Any]:
        """Parse printer status with error handling."""
        try:
            status_data = data[data.find(b'set machineStatus'):data.find(b'Transferred:')]
            if not status_data:
                raise ValueError("No status data found")

            parsed = self._parse_tcl_status(status_data.decode('utf-8', errors='ignore'))

            status_cache = Path('/config/cache')
            status_cache.mkdir(parents=True, exist_ok=True)
            with open(status_cache / 'last_status.json', 'w') as f:
                json.dump(parsed, f, indent=2)

            return parsed

        except Exception as e:
            self.logger.error(f"Status parsing failed: {e}")
            return {}

    def _parse_tcl_status(self, tcl_data: str) -> Dict[str, Any]:
        """Parse TCL formatted status data into a Python dictionary."""
        result = {}
        current_section = result
        section_stack = []

        try:
            lines = [line.strip() for line in tcl_data.split('\n') if line.strip()]

            for line in lines:
                if not line or line.startswith('#'):
                    continue

                if line.startswith('set machineStatus('):
                    section = line[line.find('(') + 1:line.find(')')]
                    if section not in result:
                        result[section] = {}
                    current_section = result[section]
                    continue

                if line.startswith('{'):
                    new_section = {}
                    if isinstance(current_section, list):
                        current_section.append(new_section)
                    section_stack.append(current_section)
                    current_section = new_section
                    continue

                if line.startswith('}'):
                    if section_stack:
                        current_section = section_stack.pop()
                    continue

                if '-' in line:
                    key = line[1:line.find(' ')]
                    value = line[line.find(' ') + 1:].strip()

                    if value.startswith('{'):
                        value = value[1:-1]
                        if ' ' in value:
                            value = [v.strip() for v in value.split()]

                    elif value.replace('.', '').isdigit():
                        value = float(value) if '.' in value else int(value)

                    elif value.lower() in ('true', 'false'):
                        value = value.lower() == 'true'

                    current_section[key] = value

        except Exception as e:
            self.logger.error(f"TCL parsing error: {e}")
            return {}

        return result

    async def get_status(self) -> Dict[str, Any]:
        """Get printer status with retries."""
        for attempt in range(self.config.retry_attempts):
            try:
                if not self.connected:
                    await self.connect()

                data = await self._get_printer_data()
                return self._parse_status(data)

            except PrinterError as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay)
                    continue
                raise

    async def connect(self) -> None:
        """Establish connection to the printer."""
        try:
            if self.sock:
                try:
                    self.sock.close()
                except Exception:
                    pass
                self.sock = None

            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.config.timeout)
            self.sock.connect((self.config.host, self.config.port))
            self.connected = True
            self.logger.info(f"Successfully connected to printer at {self.config.host}:{self.config.port}")

        except Exception as e:
            self.connected = False
            raise ConnectionError(f"Failed to connect: {str(e)}")

    def cleanup(self):
        """Clean up resources."""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        self.connected = False
        self.logger.info("Monitor stopped")
