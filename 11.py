#!/usr/bin/env python3

import os
import pandas as pd
import requests
from netmiko import ConnectHandler
from tabulate import tabulate
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ===============================
# CONFIGURATION
# ===============================
INPUT_EXCEL = "librenms_devices.xlsx"
OUTPUT_EXCEL = "ssh_device_ports_status.xlsx"

LIBRENMS_URL = "http://localhost:8081"
API_TOKEN = os.getenv("LIBRENMS_TOKEN")

USERNAME = "admin"
PASSWORD = "cisco"
SECRET = "cisco"  # optional, can be ""

DEVICE_TYPE = "cisco_ios"

# ===============================
# HEADERS
# ===============================
HEADERS = {
    "X-Auth-Token": API_TOKEN,
    "Accept": "application/json",
}

# ===============================
# LIBRENMS FUNCTIONS
# ===============================
def get_librenms_devices():
    url = f"{LIBRENMS_URL}/api/v0/devices"
    r = requests.get(url, headers=HEADERS, verify=False, timeout=20)
    r.raise_for_status()
    return r.json()["devices"]


def build_active_cisco_devices():
    """
    Returns a set of hostnames that are:
    - status == UP
    - os == ios or iosxe
    """
    devices = get_librenms_devices()
    active = set()

    for d in devices:
        if d.get("status") == 1 and d.get("os") in ("ios", "iosxe"):
            active.add(d["hostname"])

    return active

# ===============================
# SSH & PARSING FUNCTIONS
# ===============================
def parse_interfaces(output):
    """
    Counts total and active interfaces from:
    show interfaces status

    - Counts Fa/Gi/Te/Po
    - Excludes header line ("Port Name Status ...")
    """
    total_ports = 0
    active_ports = 0

    for line in output.splitlines():
        line = line.strip()

        if not line:
            continue

        if line.startswith(("Fa", "Gi", "Te", "Po")) and not line.startswith("Port"):
            total_ports += 1
            if "connected" in line:
                active_ports += 1

    return total_ports, active_ports


def percent(active, total):
    return round((active / total) * 100, 2) if total else 0


def ssh_check(hostname):
    print(f"🔍 Connecting to {hostname} ...")

    device = {
        "device_type": DEVICE_TYPE,
        "host": hostname,
        "username": USERNAME,
        "password": PASSWORD,
        "secret": SECRET,
        "fast_cli": True,
    }

    try:
        with ConnectHandler(**device) as conn:
            if SECRET:
                conn.enable()

            output = conn.send_command("show interfaces status")

        return parse_interfaces(output)

    except Exception as e:
        print(f"❌ SSH failed for {hostname}: {e}")
        return 0, 0

# ===============================
# MAIN
# ===============================
def main():
    if not API_TOKEN:
        raise RuntimeError("LIBRENMS_TOKEN environment variable is not set")

    df = pd.read_excel(INPUT_EXCEL)

    if "hostname" not in df.columns:
        raise ValueError("Excel file must contain a column named 'hostname'")

    active_devices = build_active_cisco_devices()

    results = []

    for hostname in df["hostname"]:
        hostname = str(hostname).strip()

        # Filter: only ACTIVE Cisco devices
        if hostname not in active_devices:
            print(f"⏭ Skipping {hostname} (inactive or unsupported)")
            continue

        total, active = ssh_check(hostname)

        results.append({
            "Hostname": hostname,
            "Total Ports": total,
            "Active Ports": active,
            "Port Utilization %": percent(active, total),
        })

    result_df = pd.DataFrame(results)

    print("\n📊 SSH Port Utilization Summary (ACTIVE devices only)\n")
    print(tabulate(result_df, headers="keys", tablefmt="grid", showindex=False))

    result_df.to_excel(OUTPUT_EXCEL, index=False)
    print(f"\n✅ Results saved to {OUTPUT_EXCEL}")

# ===============================
# ENTRY POINT
# ===============================
if __name__ == "__main__":
    main()
