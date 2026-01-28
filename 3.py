#!/usr/bin/env python3

import requests
from tabulate import tabulate
import urllib3
import os
import pandas as pd

# Disable SSL warnings (safe for HTTP / lab environments)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ======================
# CONFIGURATION
# ======================
LIBRENMS_BASE_URL = "http://localhost:8081"
OUTPUT_EXCEL = "librenms_devices.xlsx"

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

# ======================
# OUTPUT FUNCTIONS
# ======================
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

def export_devices_to_excel(devices, filename):
    """Export device list to Excel"""
    rows = []

    for d in devices:
        rows.append({
            "ID": d.get("device_id"),
            "Hostname": d.get("hostname"),
            "IP": d.get("ip"),
            "OS": d.get("os"),
            "Hardware": d.get("hardware"),
            "Status": device_status(d.get("status")),
            "Location": d.get("location"),
            "Last Ping": d.get("last_ping")
        })

    df = pd.DataFrame(rows)
    df.to_excel(filename, index=False)
    print(f"\n📁 Excel file created: {filename}")

# ======================
# MAIN
# ======================
if __name__ == "__main__":
    try:
        data = get_devices()
        devices = data.get("devices", [])

        print(f"\n✅ Retrieved {len(devices)} devices from LibreNMS\n")

        # Print to terminal
        print_devices_table(devices)

        # Export to Excel
        export_devices_to_excel(devices, OUTPUT_EXCEL)

    except Exception as e:
        print(f"❌ Error: {e}")
