#!/usr/bin/env python3

import os
import requests
import pandas as pd
from tabulate import tabulate
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================================================
# CONFIGURATION
# ==================================================
LIBRENMS_BASE_URL = "http://localhost:8081"
INPUT_EXCEL = "librenms_devices.xlsx"
OUTPUT_EXCEL = "device_ports_status.xlsx"

# 🔎 DEBUG MODE (set to True to PROVE API values)
DEBUG_MODE = True
DEBUG_DEVICE = "home-lab-access-sw01"  # device to debug

API_TOKEN = os.getenv("LIBRENMS_TOKEN")
if not API_TOKEN:
    raise RuntimeError("❌ LIBRENMS_TOKEN environment variable not set")

HEADERS = {
    "X-Auth-Token": API_TOKEN,
    "Accept": "application/json"
}

# ==================================================
# API FUNCTIONS
# ==================================================
def get_ports(hostname):
    url = f"{LIBRENMS_BASE_URL}/api/v0/devices/{hostname}/ports"
    r = requests.get(url, headers=HEADERS, verify=False, timeout=15)

    if r.status_code != 200:
        print(f"❌ Failed to fetch ports for {hostname}")
        return []

    return r.json().get("ports", [])

# ==================================================
# DEBUG / PROOF FUNCTION
# ==================================================
def debug_ports(hostname, limit=20):
    print(f"\n🔎 DEBUG: RAW PORT STATES FROM API ({hostname})\n")

    ports = get_ports(hostname)

    for p in ports[:limit]:
        print(
            f"{p.get('ifName'):10} "
            f"admin={p.get('ifAdminStatus')} "
            f"oper={p.get('ifOperStatus')} "
            f"speed={p.get('ifSpeed')}"
        )

    print("\n🔎 END DEBUG\n")

# ==================================================
# CORE LOGIC (SNMP-CORRECT)
# ==================================================
def is_active_port(port):
    """
    LibreNMS / SNMP correct definition of ACTIVE:
    ifAdminStatus == 1 AND ifOperStatus == 1
    """
    try:
        admin = int(port.get("ifAdminStatus"))
        oper = int(port.get("ifOperStatus"))
    except (TypeError, ValueError):
        return False

    return admin == 1 and oper == 1

def count_active_ports(ports):
    return sum(1 for p in ports if is_active_port(p))

def utilization_percent(active, total):
    if total == 0:
        return 0.0
    return round((active / total) * 100, 2)

# ==================================================
# MAIN
# ==================================================
def main():
    df = pd.read_excel(INPUT_EXCEL)

    if "hostname" not in df.columns:
        raise ValueError("Excel must contain a 'hostname' column")

    # 🔎 Run DEBUG ONCE (proof)
    if DEBUG_MODE:
        debug_ports(DEBUG_DEVICE)

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

    print("\n📊 Port Utilization Summary\n")
    print(tabulate(result_df.values, headers=result_df.columns, tablefmt="grid"))

    result_df.to_excel(OUTPUT_EXCEL, index=False)
    print(f"\n✅ Results saved to {OUTPUT_EXCEL}")

# ==================================================
if __name__ == "__main__":
    main()
