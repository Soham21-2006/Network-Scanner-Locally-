# NetScan — Network Scanner with Web GUI

A modern web-based network scanner built with **Python (Flask + SocketIO)** and a
clean **HTML/CSS/JS** dashboard. Discovers live hosts on your LAN via ARP and
scans open TCP ports with live progress updates in the browser.

## Features

- 🔍 ARP-based host discovery (fast, reliable on LAN)
- ⚡ Multithreaded TCP port scanning
- 🏷️ Service banner grabbing
- 🎨 Modern dashboard UI (dark / light theme)
- 📡 Real-time updates via WebSockets
- 📊 Live stats: hosts, open ports, services, elapsed time
- 🔎 Filter results by IP, MAC, or port
- 💾 Export results as JSON

## Requirements

- Python 3.9+
- Root / Administrator privileges (for raw ARP packets)

## Installation

```bash
git clone <your-repo>
cd network-scanner
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
