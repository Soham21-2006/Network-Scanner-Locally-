"""Helper utilities: IP validation, MAC vendor lookup, port parsing."""

import ipaddress
from mac_vendor_lookup import MacLookup

try:
    _mac_lookup = MacLookup()
    _mac_lookup.load_vendors()
    MAC_LOOKUP_AVAILABLE = True
except Exception:
    _mac_lookup = None
    MAC_LOOKUP_AVAILABLE = False


def validate_target(target: str) -> bool:
    """Validate a single IP or CIDR range (e.g. 192.168.1.0/24)."""
    target = target.strip()
    if not target:
        return False
    try:
        if "/" in target:
            ipaddress.ip_network(target, strict=False)
        else:
            ipaddress.ip_address(target)
        return True
    except ValueError:
        return False


def parse_port_range(port_str: str):
    """Parse '1-1024' or '80,443,8080' into a sorted list of ints."""
    port_str = port_str.strip()
    ports = set()

    for part in port_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            start, end = int(start), int(end)
            if start > end:
                start, end = end, start
            ports.update(range(start, end + 1))
        else:
            ports.add(int(part))

    # Clamp to valid port range
    return sorted(p for p in ports if 1 <= p <= 65535)


def get_vendor(mac: str) -> str:
    """Return the vendor name for a MAC address (OUI lookup)."""
    if not mac or not MAC_LOOKUP_AVAILABLE:
        return "Unknown"
    try:
        return _mac_lookup.lookup(mac)
    except Exception:
        return "Unknown"


COMMON_SERVICES = {
    20: "FTP-Data", 21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
    53: "DNS", 67: "DHCP", 68: "DHCP", 69: "TFTP", 80: "HTTP",
    110: "POP3", 123: "NTP", 135: "MSRPC", 137: "NetBIOS", 138: "NetBIOS",
    139: "NetBIOS", 143: "IMAP", 161: "SNMP", 162: "SNMP-Trap",
    389: "LDAP", 443: "HTTPS", 445: "SMB", 465: "SMTPS",
    514: "Syslog", 587: "SMTP-Sub", 636: "LDAPS", 993: "IMAPS",
    995: "POP3S", 1080: "SOCKS", 1433: "MSSQL", 1521: "Oracle",
    1723: "PPTP", 1883: "MQTT", 2049: "NFS", 2082: "cPanel",
    2083: "cPanel-SSL", 3000: "Node-Dev", 3306: "MySQL",
    3389: "RDP", 4443: "HTTPS-Alt", 5000: "Flask-Dev",
    5432: "PostgreSQL", 5900: "VNC", 5985: "WinRM", 6379: "Redis",
    7001: "WebLogic", 8000: "HTTP-Alt", 8080: "HTTP-Alt",
    8443: "HTTPS-Alt", 8888: "HTTP-Alt", 9000: "PHP-FPM",
    9090: "WebSphere", 9200: "Elasticsearch", 27017: "MongoDB",
}


def get_service_name(port: int) -> str:
    """Return the common service name for a port."""
    return COMMON_SERVICES.get(port, "unknown")
