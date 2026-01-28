#!/usr/bin/env python3

import os
import requests
import pandas as pd
from tabulate import tabulate
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ======================
# CONFIGURATION
# ======================
LIBRENMS_BASE_URL = "http://localhost:8081"
INPUT_EXCEL = "librenms_devices.xlsx"
OUTPUT_EXCEL = "device_ports_status.xlsx"

API_TOKEN = os.getenv("LIBRENMS_TOKEN")
if not API_TOKEN:
    raise RuntimeError("LIBRENMS_TOKEN environment variable not set")

HEADERS = {
    "X-Auth-Token": API_TOKEN,
    "Accept": "application/json"
}

# ======================
# API FUNCTIONS
# ======================
def get_ports(hostname):
    url = f"{LIBRENMS_BASE_URL}/api/v0/devices/{hostname}/ports"
    r = requests.get(url, headers=HEADERS, verify=False, timeout=10)

    if r.status_code != 200:
        print(f"❌ Failed to fetch ports for {hostname}")
        return []

    return r.json().get("ports", [])

# ======================
# LOGIC FUNCTIONS
# ======================
def count_active_ports(ports):
    """Cisco-correct active port logic"""
    active = 0
    for p in ports:
        if p.get("ifAdminStatus") == "up" and p.get("ifOperStatus") == "up":
            active += 1
    return active

def utilization_percent(active, total):
    if total == 0:
        return 0.0
    return round((active / total) * 100, 2)

# ======================
# MAIN
# ======================
def main():
    df = pd.read_excel(INPUT_EXCEL)

    if "hostname" not in df.columns:
        raise ValueError("Excel must contain a 'hostname' column")

    results = []

    for hostname in df["hostname"]:
        print(f"🔍 Checking ports for {hostname} ...")

        ports = get_ports(hostname)
        total_ports = len(ports)
        active_ports = count_active_ports(ports)
        utilization = utilization_percent(active_ports, total_ports)

        results.append([
            hostname,
            total_ports,
            active_ports,
            utilization
        ])

    result_df = pd.DataFrame(
        results,
        columns=[
            "Hostname",
            "Total Ports",
            "Active Ports",
            "Port Utilization %"
        ]
    )

    # Print table
    print("\n📊 Port Utilization Summary\n")
    print(tabulate(result_df.values, headers=result_df.columns, tablefmt="grid"))

    # Export to Excel
    result_df.to_excel(OUTPUT_EXCEL, index=False)
    print(f"\n✅ Results saved to {OUTPUT_EXCEL}")

# ======================
if __name__ == "__main__":
    main()
