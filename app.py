"""Network Scanner — Flask + SocketIO main server."""

import os
import time
import logging

from flask import Flask, render_template, send_from_directory, jsonify
from flask_socketio import SocketIO, emit

from config import Config, ensure_dirs
from scanner.arp_scan import arp_scan
from scanner.port_scan import scan_ports
from scanner.banner_grab import grab_banner
from scanner.utils import (
    validate_target,
    parse_port_range,
    get_vendor,
)

# ---------- Setup ----------
ensure_dirs()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("netscan")

app = Flask(__name__)
app.config["SECRET_KEY"] = Config.SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "version": "1.0.0"})


@app.route("/exports/<path:filename>")
def download_export(filename):
    return send_from_directory(Config.EXPORT_DIR, filename, as_attachment=True)


# ---------- SocketIO Events ----------
@socketio.on("connect")
def on_connect():
    log.info("Client connected")
    emit("connected", {"message": "Connected to NetScan server"})


@socketio.on("disconnect")
def on_disconnect():
    log.info("Client disconnected")


@socketio.on("start_scan")
def on_start_scan(data):
    """Client clicked 'Start Scan'."""
    target = (data.get("target") or "").strip()
    port_range = (data.get("ports") or Config.DEFAULT_PORT_RANGE).strip()
    scan_type = (data.get("scan_type") or "connect").strip()

    if not validate_target(target):
        emit("scan_error", {"message": f"Invalid target: {target}"})
        return

    # Basic security guard — only private ranges by default
    # (loopback is also allowed for local testing)
    is_loopback = target in ("127.0.0.1", "localhost", "::1")
    if not is_loopback and not any(target.startswith(p) for p in Config.ALLOWED_PREFIXES):
        log.warning(f"Blocked scan on non-private target: {target}")
        emit("scan_error", {
            "message": "Only private IP ranges (192.168.x, 10.x, 172.16-31.x) are allowed."
        })
        return

    log.info(f"Scan requested: target={target} ports={port_range} type={scan_type}")
    socketio.start_background_task(run_scan, target, port_range, scan_type)


# ---------- Scan Worker ----------
def discover_hosts(target: str):
    """
    Return a list of {'ip', 'mac'} dicts for the target.

    - Loopback (127.0.0.1 / localhost): skip ARP, return directly.
    - Single IP: try ARP, fall back to a direct scan if ARP fails.
    - CIDR range: use ARP discovery.
    """
    # Loopback — no ARP needed
    if target in ("127.0.0.1", "localhost", "::1"):
        log.info(f"Loopback target detected: {target}")
        return [{"ip": "127.0.0.1", "mac": "00:00:00:00:00:00"}]

    # Single IP — ARP with fallback
    if "/" not in target:
        try:
            hosts = arp_scan(target, timeout=Config.ARP_TIMEOUT)
        except Exception as e:
            log.warning(f"ARP scan failed for {target}: {e}")
            hosts = []

        if not hosts:
            log.info(f"ARP found nothing for {target}; scanning IP directly.")
            hosts = [{"ip": target, "mac": "00:00:00:00:00:00"}]
        return hosts

    # CIDR range — ARP discovery
    return arp_scan(target, timeout=Config.ARP_TIMEOUT)


def run_scan(target: str, port_range: str, scan_type: str):
    """Full scan pipeline with live progress events."""
    started_at = time.time()

    try:
        # ---- Phase 1: Host discovery ----
        socketio.emit("scan_status", {"message": f"Discovering hosts in {target}..."})

        hosts = discover_hosts(target)

        if not hosts:
            socketio.emit("scan_complete", {
                "hosts": [],
                "summary": {"hosts": 0, "open_ports": 0, "services": {}},
                "elapsed": round(time.time() - started_at, 2),
            })
            return

        log.info(f"Found {len(hosts)} live host(s).")

        socketio.emit("hosts_found", {
            "count": len(hosts),
            "hosts": [
                {"ip": h["ip"], "mac": h["mac"], "vendor": get_vendor(h["mac"])}
                for h in hosts
            ],
        })

        # ---- Phase 2: Parse ports ----
        try:
            ports = parse_port_range(port_range)
        except Exception:
            socketio.emit("scan_error", {"message": f"Invalid port range: {port_range}"})
            return

        log.info(f"Scanning {len(ports)} port(s) on each host.")

        # ---- Phase 3: Port scan each host ----
        all_results = []
        service_counter = {}

        for idx, host in enumerate(hosts, start=1):
            socketio.emit("scan_progress", {
                "current": idx,
                "total": len(hosts),
                "current_host": host["ip"],
                "percent": int((idx - 1) / len(hosts) * 100),
            })

            open_ports = scan_ports(
                host=host["ip"],
                ports=ports,
                timeout=Config.PORT_SCAN_TIMEOUT,
                max_workers=Config.MAX_THREADS,
            )

            log.info(f"{host['ip']}: {len(open_ports)} open port(s)")

            # ---- Phase 4: Banner grab ----
            for p in open_ports:
                p["banner"] = grab_banner(
                    host["ip"], p["port"], timeout=Config.BANNER_TIMEOUT
                )
                if p["service"] != "unknown":
                    service_counter[p["service"]] = (
                        service_counter.get(p["service"], 0) + 1
                    )

            host_result = {
                "ip": host["ip"],
                "mac": host["mac"],
                "vendor": get_vendor(host["mac"]),
                "open_ports": open_ports,
            }
            all_results.append(host_result)

            # Stream this host to the browser immediately
            socketio.emit("host_result", host_result)

        # ---- Done ----
        summary = {
            "hosts": len(all_results),
            "open_ports": sum(len(h["open_ports"]) for h in all_results),
            "services": service_counter,
        }
        socketio.emit("scan_complete", {
            "hosts": all_results,
            "summary": summary,
            "elapsed": round(time.time() - started_at, 2),
        })

    except PermissionError:
        socketio.emit("scan_error", {
            "message": "Permission denied. Run the server with sudo/administrator."
        })
    except Exception as e:
        log.exception("Scan failed")
        socketio.emit("scan_error", {"message": f"Scan failed: {e}"})


# ---------- Entry Point ----------
if __name__ == "__main__":
    log.info(f"Starting NetScan on http://{Config.HOST}:{Config.PORT}")
    socketio.run(
        app,
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
        allow_unsafe_werkzeug=True,   # required when running as a service
    )
