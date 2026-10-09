"""Host discovery via ARP broadcast (Layer 2)."""

import logging
from scapy.all import ARP, Ether, srp

log = logging.getLogger(__name__)


def arp_scan(ip_range: str, timeout: int = 2, iface: str = None):
    """
    Send ARP requests to every IP in `ip_range` and collect responses.

    Returns:
        list of dicts: [{'ip': '192.168.1.1', 'mac': 'aa:bb:cc:dd:ee:ff'}, ...]
    """
    log.info(f"Starting ARP scan on {ip_range}")

    arp_request = ARP(pdst=ip_range)
    broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = broadcast / arp_request

    try:
        answered, _ = srp(packet, timeout=timeout, iface=iface, verbose=False)
    except PermissionError:
        log.error("ARP scan requires root/admin privileges.")
        raise
    except Exception as e:
        log.error(f"ARP scan failed: {e}")
        raise

    hosts = []
    for _, received in answered:
        hosts.append({
            "ip": received.psrc,
            "mac": received.hwsrc.upper(),
        })

    log.info(f"Found {len(hosts)} live host(s).")
    return hosts
