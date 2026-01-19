# transport/tcp_server.py
from __future__ import annotations

import socket
import threading
from typing import Tuple

from apdu.parser import parse_apdu, ApduParseError
from apdu.router import dispatch
from apdu import status_words as sw
from card.context import CardContext


"""
Here the TCP-based transport for the USIM emulator is implemented.

Protocol is:
- Client sends one APDU per line, encoded as HEX ASCII
    Example: 00A4000C023F00\n
- Server responds with HEX ASCII of:
    <response data><SW1><SW2>\n

This is NOT ISO-7816 transport.
It is just a convenient way to test APDU logic without PC/SC.
"""


def _handle_client(conn: socket.socket, addr: Tuple[str, int], ctx: CardContext) -> None:
    """
    Handle one TCP client connection.
    The same CardContext is reused so selection state persists
    across APDUs in this session.
    """
    with conn:
        print(f"[USIM] Client connected from {addr}")
        buffer = b""

        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buffer += chunk

            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                line = line.strip()
                if not line:
                    continue

                try:
                    # Expect hex-encoded APDU
                    raw_apdu = bytes.fromhex(line.decode("ascii"))
                    apdu = parse_apdu(raw_apdu)
                    response = dispatch(ctx, apdu)

                except ValueError:
                    # Hex decode error
                    response = sw.SW_WRONG_LENGTH
                except ApduParseError:
                    response = sw.SW_WRONG_LENGTH
                except Exception as exc:
                    # Catch-all to avoid crashing server
                    print(f"[USIM] Internal error: {exc}")
                    response = sw.SW_FUNC_NOT_SUPPORTED

                # Send hex-encoded response
                conn.sendall(response.hex().upper().encode("ascii") + b"\n")

        print(f"[USIM] Client disconnected from {addr}")


def run_server(ctx: CardContext, host: str = "127.0.0.1", port: int = 9999) -> None:
    """
    Start the TCP server and listen for APDU clients.
    Each client connection gets its own thread but shares
    the same CardContext by default.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen()

        print(f"[USIM] Emulator listening on {host}:{port}")

        while True:
            conn, addr = s.accept()
            t = threading.Thread(
                target=_handle_client,
                args=(conn, addr, ctx),
                daemon=True,
            )
            t.start()
