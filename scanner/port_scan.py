"""TCP port scanning with multithreading."""

import socket
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from .utils import get_service_name

log = logging.getLogger(__name__)


def _tcp_connect(host: str, port: int, timeout: float = 1.0) -> bool:
    """Attempt a TCP connection. True if the port is open."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        return s.connect_ex((host, port)) == 0
    except (socket.timeout, OSError):
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def scan_ports(host: str, ports: list, timeout: float = 1.0,
               max_workers: int = 200, progress_cb=None):
    """
    Scan a list of TCP ports on `host` using a thread pool.

    Args:
        host: target IP
        ports: list of ints
        timeout: per-port timeout
        max_workers: concurrent threads
        progress_cb: optional callable(port) fired after each port completes

    Returns:
        list of dicts: [{'port': 22, 'service': 'SSH', 'state': 'open'}, ...]
    """
    open_ports = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_tcp_connect, host, port, timeout): port
            for port in ports
        }
        for future in as_completed(futures):
            port = futures[future]
            try:
                if future.result():
                    open_ports.append({
                        "port": port,
                        "service": get_service_name(port),
                        "state": "open",
                    })
            except Exception as e:
                log.debug(f"Error scanning {host}:{port} — {e}")

            if progress_cb:
                progress_cb(port)

    return sorted(open_ports, key=lambda p: p["port"])
