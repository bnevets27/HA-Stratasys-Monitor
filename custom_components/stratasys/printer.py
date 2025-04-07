"""Stratasys Printer Monitor."""

import socket
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum, auto

_LOGGER = logging.getLogger(__name__)  # Standard Home Assistant logging

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

    async def _send_packet(self, data: bytes) -> None:
        """Send a packet to the printer."""
        try:
            await asyncio.to_thread(self.sock.send, data.ljust(self.config.packet_size, b'\x00'))
        except socket.timeout:
            raise ConnectionError("Timeout sending packet")
        except socket.error as e:
            raise ConnectionError(f"Socket error: {e}")

    async def _recv_packet(self, size: int = None) -> bytes:
        """Receive a packet from the printer."""
        size = size or self.config.packet_size
        return await asyncio.to_thread(self.sock.recv, size)

    async def _get_printer_data(self) -> bytes:
        """Execute the full printer protocol sequence."""
        try:
            await self._send_packet(b'GetFile')
            await asyncio.sleep(self.PROTOCOL_DELAYS['command'])

            await self._send_packet(b'status.sts')
            await asyncio.sleep(self.PROTOCOL_DELAYS['command'])

            await self._send_packet(b'NA')
            await asyncio.sleep(self.PROTOCOL_DELAYS['response'])

            sendfile = await self._recv_packet()
            if b'SendFile' not in sendfile:
                raise ProtocolError(f"Expected SendFile, got: {sendfile}")
            await asyncio.sleep(self.PROTOCOL_DELAYS['transfer'])

            na = await self._recv_packet()
            if b'NA' not in na:
                raise ProtocolError(f"Expected NA, got: {na}")

            await self._send_packet(b'OK')
            size_data = await self._recv_packet()
            if not size_data:
                raise ProtocolError("No size data received")

            try:
                size_str = size_data.strip().split(b' ')[0]
                expected_size = int(size_str)
            except (ValueError, IndexError):
                raise ProtocolError(f"Invalid size data: {size_data}")

            await self._send_packet(b'OK')

            data = bytearray()
            self.sock.settimeout(5.0)

            while len(data) < expected_size:
                chunk = await self._recv_packet(1460)
                if not chunk:
                    if len(data) == 0:
                        raise ProtocolError("Connection closed without data")
                    break
                data.extend(chunk)

                if b'Transferred:' in chunk:
                    break

            _LOGGER.debug(f"Received {len(data)} bytes of {expected_size} expected")

            confirm_msg = f"Transferred: {len(data)}".encode()
            await self._send_packet(confirm_msg)

            return bytes(data)

        except Exception as e:
            _LOGGER.error(f"Protocol sequence failed: {e}")
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
            return parsed

        except Exception as e:
            _LOGGER.error(f"Status parsing failed: {e}")
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
            _LOGGER.error(f"TCL parsing error: {e}")
            return {}

        return result

    async def connect(self):
        """Establish connection to the printer."""
        try:
            def _create_socket():
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.config.timeout)
                sock.connect((self.config.host, self.config.port))
                return sock

            self.sock = await asyncio.to_thread(_create_socket)

            _LOGGER.info(f"Connected to printer at {self.config.host}:{self.config.port}")
            self.connected = True

        except Exception as e:
            _LOGGER.error(f"Connection failed: {e}")
            self.connected = False
            raise ConnectionError(f"Failed to connect: {e}")

    async def get_status(self) -> Dict[str, Any]:
        """Get printer status with retries."""
        for attempt in range(self.config.retry_attempts):
            try:
                await self.connect()  # Always connect fresh!

                data = await self._get_printer_data()
                return self._parse_status(data)

            except PrinterError as e:
                _LOGGER.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay)
                    continue
                raise

            finally:
                self.cleanup()  # Always cleanup socket after attempt!

    def cleanup(self):
        """Clean up resources."""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        self.connected = False
        _LOGGER.info("Monitor stopped")
