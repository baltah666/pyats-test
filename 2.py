#!/usr/bin/env python3

import requests
from tabulate import tabulate
import urllib3
import os

# Disable SSL warnings (safe for HTTP / lab environments)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ======================
# CONFIGURATION
# ======================
LIBRENMS_BASE_URL = "http://localhost:8081"

# Use environment variable for security
API_TOKEN = os.getenv("LIBRENMS_TOKEN")
if not API_TOKEN:
    raise RuntimeError("❌ LIBRENMS_TOKEN environment variable is not set")

HEADERS = {
    "X-Auth-Token": API_TOKEN,
    "Accept": "application/json"
}

# ======================
# HELPER FUNCTIONS
# ======================
def device_status(status):
    """Convert LibreNMS numeric status to ACTIVE / INACTIVE"""
    return "ACTIVE" if status == 1 else "INACTIVE"

# ======================
# API FUNCTIONS
# ======================
def get_devices():
    url = f"{LIBRENMS_BASE_URL}/api/v0/devices"
    response = requests.get(url, headers=HEADERS, verify=False, timeout=10)

    if response.status_code != 200:
        raise Exception(f"API Error {response.status_code}: {response.text}")

    return response.json()

def print_devices_table(devices):
    table = []

    for d in devices:
        table.append([
            d.get("device_id"),
            d.get("hostname"),
            d.get("ip"),
            d.get("os"),
            d.get("hardware"),
            device_status(d.get("status")),
            d.get("location"),
            d.get("last_ping")
        ])

    headers = [
        "ID",
        "Hostname",
        "IP",
        "OS",
        "Hardware",
        "Status",
        "Location",
        "Last Ping"
    ]

    print(tabulate(table, headers=headers, tablefmt="grid"))

# ======================
# MAIN
# ======================
if __name__ == "__main__":
    try:
        data = get_devices()
        devices = data.get("devices", [])

        print(f"\n✅ Retrieved {len(devices)} devices from LibreNMS\n")
        print_devices_table(devices)

    except Exception as e:
        print(f"❌ Error: {e}")
