import os

class Config:
    """Central configuration for the Network Scanner app."""

    # ---------- Flask ----------
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-in-production")
    HOST = "0.0.0.0"
    PORT = 5000
    DEBUG = True

    # ---------- Scanner Defaults ----------
    DEFAULT_PORT_RANGE = "1-1024"
    ARP_TIMEOUT = 2           # seconds
    PORT_SCAN_TIMEOUT = 1.0   # seconds per port
    MAX_THREADS = 200         # concurrent port scan threads
    BANNER_TIMEOUT = 2.0      # seconds

    # ---------- Paths ----------
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXPORT_DIR = os.path.join(BASE_DIR, "exports")
    LOG_DIR = os.path.join(BASE_DIR, "logs")

    # ---------- Security ----------
    # Only allow scanning private RFC1918 ranges by default
    ALLOWED_PREFIXES = ("192.168.", "10.", "172.16.", "172.17.",
                        "172.18.", "172.19.", "172.2", "172.30.",
                        "172.31.", "127.0.0.1")


def ensure_dirs():
    """Create required directories if missing."""
    os.makedirs(Config.EXPORT_DIR, exist_ok=True)
    os.makedirs(Config.LOG_DIR, exist_ok=True)
