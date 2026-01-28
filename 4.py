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
API_TOKEN = os.getenv("LIBRENMS_TOKEN")

if not API_TOKEN:
    raise RuntimeError("LIBRENMS_TOKEN environment variable not set")

INPUT_EXCEL = "librenms_devices.xlsx"
OUTPUT_EXCEL = "device_ports_status.xlsx"

HEADERS = {
    "X-Auth-Token": API_TOKEN,
    "Accept": "application/json"
}

# ======================
# FUNCTIONS
# ======================
def get_ports(hostname):
    """Get ports for a device"""
    url = f"{LIBRENMS_BASE_URL}/api/v0/devices/{hostname}/ports"
    r = requests.get(url, headers=HEADERS, verify=False, timeout=10)

    if r.status_code != 200:
        print(f"❌ Failed to fetch ports for {hostname}")
        return []

    return r.json().get("ports", [])

def count_active_ports(ports):
    """Count active (UP) ports"""
    return sum(1 for p in ports if p.get("ifOperStatus") == "up")

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
        active_ports = count_active_ports(ports)
        total_ports = len(ports)

        results.append([
            hostname,
            total_ports,
            active_ports
        ])

    result_df = pd.DataFrame(
        results,
        columns=["Hostname", "Total Ports", "Active Ports"]
    )

    # Print table
    print("\n📊 Port Status Summary\n")
    print(tabulate(result_df.values, headers=result_df.columns, tablefmt="grid"))

    # Save to Excel
    result_df.to_excel(OUTPUT_EXCEL, index=False)
    print(f"\n✅ Results saved to {OUTPUT_EXCEL}")

# ======================
if __name__ == "__main__":
    main()
