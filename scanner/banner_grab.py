"""Service banner grabbing for open ports."""

import socket
import logging

log = logging.getLogger(__name__)


def grab_banner(host: str, port: int, timeout: float = 2.0) -> str:
    """
    Connect to a service and try to read its banner.

    Returns:
        str: first line of the banner, or None if unavailable.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)

    try:
        s.connect((host, port))

        # Some services require a nudge before replying
        if port in (80, 8000, 8080, 8888):
            try:
                s.send(b"HEAD / HTTP/1.0\r\nHost: %b\r\n\r\n" % host.encode())
            except Exception:
                pass
        elif port == 443 or port == 8443:
            return None  # TLS handshake needed; skip for simplicity

        banner = s.recv(2048).decode(errors="ignore").strip()
        if not banner:
            return None

        # Return first meaningful line
        first_line = banner.splitlines()[0].strip()
        return first_line[:200]  # truncate long banners
    except Exception as e:
        log.debug(f"Banner grab failed for {host}:{port} — {e}")
        return None
    finally:
        try:
            s.close()
        except Exception:
            pass
