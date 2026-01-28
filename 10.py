#!/usr/bin/env python3

import os
import pandas as pd
import requests
from netmiko import ConnectHandler
from tabulate import tabulate
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ===============================
# CONFIG
# ===============================
INPUT_EXCEL = "librenms_devices.xlsx"
OUTPUT_EXCEL = "ssh_device_ports_status.xlsx"

LIBRENMS_URL = "http://localhost:8081"
API_TOKEN = os.getenv("LIBRENMS_TOKEN")

USERNAME = "admin"
PASSWORD = "cisco"
SECRET = "cisco"  # optional

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


def build_active_device_map():
    """
    Returns dict: hostname -> device_info
    Only ACTIVE Cisco IOS/IOS-XE devices
    """
    devices = get_librenms_devices()
    active = {}

    for d in devices:
        if (
            d.get("status") == 1 and
            d.get("os") in ("ios", "iosxe")
        ):
            active[d["hostname"]] = d

    return active

# ===============================
# SSH FUNCTIONS
# ===============================
def parse_interfaces(output):
    total = 0
    active = 0

    for line in output.splitlines():
        if line.startswith(("Fa", "Gi", "Te", "Po")):
            total += 1
            if "connected" in line:
                active += 1

    return total, active


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
        raise RuntimeError("LIBRENMS_TOKEN environment variable not set")

    excel_df = pd.read_excel(INPUT_EXCEL)

    if "hostname" not in excel_df.columns:
        raise ValueError("Excel file must contain column: hostname")

    active_devices = build_active_device_map()

    results = []

    for hostname in excel_df["hostname"]:
        hostname = str(hostname).strip()

        # 🔒 FILTER: only ACTIVE Cisco devices
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

    df = pd.DataFrame(results)

    print("\n📊 SSH Port Utilization Summary (ACTIVE devices only)\n")
    print(tabulate(df, headers="keys", tablefmt="grid", showindex=False))

    df.to_excel(OUTPUT_EXCEL, index=False)
    print(f"\n✅ Results saved to {OUTPUT_EXCEL}")

if __name__ == "__main__":
    main()
