"""Stratasys Printer Monitor."""

import socket
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
import os

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

    async def send_light_command(self, command: str) -> bool:
        """Send a light control command (on, off, or toggle) to the printer."""
        valid_commands = ["on", "off", "toggle"]
        if command.lower() not in valid_commands:
            _LOGGER.error(f"Invalid light command: {command}")
            return False
            
        try:
            # Get the path to the binary file
            integration_dir = Path(__file__).parent
            bin_path = integration_dir / "light-control.bin"
            
            if not bin_path.exists():
                _LOGGER.error(f"Light control binary not found: {bin_path}")
                return False
                
            # Load the raw capture
            raw = bin_path.read_bytes()
            
            # Create the command bytes (15 bytes exactly)
            cmd_lower = command.lower()
            if cmd_lower == "on":
                new_command = b"lights on      "  # 15 bytes
            elif cmd_lower == "off":
                new_command = b"lights off     "  # 15 bytes  
            else:  # toggle
                new_command = b"lights toggle  "  # 15 bytes
                
            # Replace the last 15 bytes with our command
            modified_raw = raw[:-15] + new_command
            
            # Create a fresh connection for light command
            sock = None
            try:
                def _create_light_socket():
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(5.0)
                    s.connect((self.config.host, self.config.port))
                    return s
                    
                sock = await asyncio.to_thread(_create_light_socket)
                await asyncio.to_thread(sock.sendall, modified_raw)
                
                # Read any responses (optional)
                responses = []
                sock.settimeout(0.5)
                try:
                    while True:
                        data = await asyncio.to_thread(sock.recv, 4096)
                        if not data:
                            break
                        responses.append(data)
                except socket.timeout:
                    pass
                    
                _LOGGER.info(f"Light command '{command}' sent successfully")
                return True
                
            finally:
                if sock:
                    try:
                        sock.close()
                    except Exception:
                        pass
                        
        except Exception as e:
            _LOGGER.error(f"Failed to send light command '{command}': {e}")
            return False
            
    async def turn_light_on(self) -> bool:
        """Turn the printer light ON."""
        return await self.send_light_command("on")
        
    async def turn_light_off(self) -> bool:
        """Turn the printer light OFF."""
        return await self.send_light_command("off")
        
    async def toggle_light(self) -> bool:
        """Toggle the printer light."""
        return await self.send_light_command("toggle")
        
    async def toggle_door_latch(self) -> bool:
        """Toggle the printer door latch."""
        try:
            # Get the path to the binary file
            integration_dir = Path(__file__).parent
            bin_path = integration_dir / "door-latch-toggle.bin"
            
            if not bin_path.exists():
                _LOGGER.error(f"Door latch control binary not found: {bin_path}")
                return False
                
            # Load the raw capture
            raw = bin_path.read_bytes()
            
            # Create a fresh connection for door latch command
            sock = None
            try:
                def _create_door_socket():
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(5.0)
                    s.connect((self.config.host, self.config.port))
                    return s
                    
                sock = await asyncio.to_thread(_create_door_socket)
                await asyncio.to_thread(sock.sendall, raw)
                
                # Read any responses (optional)
                responses = []
                sock.settimeout(0.5)
                try:
                    while True:
                        data = await asyncio.to_thread(sock.recv, 4096)
                        if not data:
                            break
                        responses.append(data)
                except socket.timeout:
                    pass
                    
                _LOGGER.info("Door latch toggle command sent successfully")
                return True
                
            finally:
                if sock:
                    try:
                        sock.close()
                    except Exception:
                        pass
                        
        except Exception as e:
            _LOGGER.error(f"Failed to toggle door latch: {e}")
            return False

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
