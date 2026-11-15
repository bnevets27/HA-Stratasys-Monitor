"""Transport regression checks; run with py -3 -B tests/test_transport.py."""

import asyncio
import importlib.util
from pathlib import Path
import sys
import socket
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Load the standalone protocol module without importing Home Assistant.
spec = importlib.util.spec_from_file_location(
    "stratasys_transport", Path(__file__).resolve().parents[1]
    / "custom_components" / "stratasys" / "printer.py",
)
printer = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = printer
spec.loader.exec_module(printer)


def frame(value):
    return value.ljust(64, b"\x00")


class StreamSocket:
    """Socket-like stream with configurable fragmentation and real recv limits."""

    def __init__(self, data, chunk_size=65536):
        self.data = data
        self.chunk_size = chunk_size
        self.sent = []
        self.timeout = None

    def recv(self, size):
        size = min(size, self.chunk_size)
        result, self.data = self.data[:size], self.data[size:]
        return result

    def sendall(self, data):
        self.sent.append(data)

    def settimeout(self, timeout):
        self.timeout = timeout


class TransportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.monitor = printer.StratasysMonitor(printer.PrinterConfig(host="test", port=1))
        sleep = patch.object(printer.asyncio, "sleep", new=AsyncMock())
        sleep.start()
        self.addCleanup(sleep.stop)

    async def test_split_and_coalesced_frames_preserve_next_frame(self):
        for chunk_size in (1, 3, 17, 65536):
            with self.subTest(chunk_size=chunk_size):
                self.monitor.sock = StreamSocket(frame(b"SendFile") + frame(b"NA"), chunk_size)
                self.assertEqual(await self.monitor._recv_packet(), frame(b"SendFile"))
                self.assertEqual(await self.monitor._recv_packet(), frame(b"NA"))

    async def test_full_exchange_reads_exact_payload_and_acknowledges_size(self):
        payload = b"set machineStatus(mariner)\n-lightsOn 1\n" + b"# filler\n" * 180
        for chunk_size in (7, 65536):
            with self.subTest(chunk_size=chunk_size):
                trailer = frame(b"Transferred: done")
                sock = StreamSocket(
                    frame(b"SendFile") + frame(b"NA") + frame(str(len(payload)).encode())
                    + payload + trailer, chunk_size,
                )
                self.monitor.sock = sock
                self.assertEqual(await self.monitor._get_printer_data(), payload)
                self.assertEqual(sock.data, trailer)
                self.assertEqual(sock.sent, [frame(command) for command in (
                    b"GetFile", b"status.sts", b"NA", b"OK", b"OK",
                    f"Transferred: {len(payload)}".encode(),
                )])
                self.assertEqual(sock.timeout, self.monitor.config.timeout)

    async def test_exchange_over_real_local_sockets(self):
        payload = b"set machineStatus(mariner)\n-lightsOn 1"
        loop = asyncio.get_running_loop()
        client, peer = socket.socketpair()
        with client, peer:
            client.settimeout(2)
            peer.setblocking(False)
            self.monitor.sock = client

            async def expect(command):
                received = bytearray()
                while len(received) < 64:
                    chunk = await loop.sock_recv(peer, 64 - len(received))
                    if not chunk:
                        raise AssertionError("Client closed during handshake")
                    received.extend(chunk)
                self.assertEqual(bytes(received), frame(command))

            async def serve():
                for command in (b"GetFile", b"status.sts", b"NA"):
                    await expect(command)
                await loop.sock_sendall(peer, frame(b"SendFile") + frame(b"NA"))
                await expect(b"OK")
                await loop.sock_sendall(peer, frame(str(len(payload)).encode()))
                await expect(b"OK")
                await loop.sock_sendall(peer, payload)
                await expect(f"Transferred: {len(payload)}".encode())

            async with asyncio.timeout(5):
                result, _ = await asyncio.gather(self.monitor._get_printer_data(), serve())
            self.assertEqual(result, payload)

    async def test_eof_in_frame_or_payload_is_connection_failure(self):
        for stream in (
            b"Send",
            frame(b"SendFile") + frame(b"NA") + frame(b"20 ") + b"partial",
        ):
            with self.subTest(stream=stream):
                self.monitor.sock = StreamSocket(stream, 3)
                with self.assertRaises(printer.ConnectionError):
                    await self.monitor._get_printer_data()

    async def test_invalid_size_does_not_start_payload_transfer(self):
        for size in (b"0", b"-1", b"bad", b""):
            with self.subTest(size=size):
                sock = StreamSocket(frame(b"SendFile") + frame(b"NA") + frame(size))
                self.monitor.sock = sock
                with self.assertRaises(printer.ProtocolError):
                    await self.monitor._get_printer_data()
                self.assertEqual(sock.sent.count(frame(b"OK")), 1)

    async def test_sendall_is_used_and_failure_stays_connection_failure(self):
        sock = MagicMock()
        sock.send.return_value = 1
        self.monitor.sock = sock
        await self.monitor._send_packet(b"GetFile")
        sock.send.assert_not_called()
        sock.sendall.assert_called_once_with(frame(b"GetFile"))
        sock.sendall.side_effect = TimeoutError("timed out")
        with self.assertRaises(printer.ConnectionError):
            await self.monitor._send_packet(b"GetFile")

    def test_parse_payload_without_trailer_preserves_final_character(self):
        payload = b"set machineStatus(mariner)\n-lightsOn 1"
        self.assertEqual(self.monitor._parse_status(payload), {"mariner": {"lightsOn": 1}})


if __name__ == "__main__":
    unittest.main()
