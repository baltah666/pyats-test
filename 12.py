#!/usr/bin/env python3

import os
import pandas as pd
import requests
from netmiko import ConnectHandler
from tabulate import tabulate
from concurrent.futures import ThreadPoolExecutor, as_completed
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
SECRET = "cisco"  # optional

DEVICE_TYPE = "cisco_ios"

MAX_WORKERS = 5   # 👈 parallel SSH sessions (safe value)

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
    r = requests.get(
        f"{LIBRENMS_URL}/api/v0/devices",
        headers=HEADERS,
        verify=False,
        timeout=20
    )
    r.raise_for_status()
    return r.json()["devices"]


def get_active_cisco_devices():
    """
    Returns a set of hostnames:
    - status == UP
    - os == ios or iosxe
    """
    devices = get_librenms_devices()
    return {
        d["hostname"]
        for d in devices
        if d.get("status") == 1 and d.get("os") in ("ios", "iosxe")
    }

# ===============================
# SSH FUNCTIONS
# ===============================
def parse_interfaces(output):
    total = 0
    active = 0

    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith(("Fa", "Gi", "Te", "Po")) and not line.startswith("Port"):
            total += 1
            if "connected" in line:
                active += 1

    return total, active


def ssh_check(hostname):
    device = {
        "device_type": DEVICE_TYPE,
        "host": hostname,
        "username": USERNAME,
        "password": PASSWORD,
        "secret": SECRET,
        "fast_cli": True,
    }

    try:
        print(f"🔍 Connecting to {hostname} ...")

        with ConnectHandler(**device) as conn:
            if SECRET:
                conn.enable()

            output = conn.send_command("show interfaces status")

        total, active = parse_interfaces(output)

        return {
            "Hostname": hostname,
            "Total Ports": total,
            "Active Ports": active,
            "Port Utilization %": round((active / total) * 100, 2) if total else 0,
        }

    except Exception as e:
        print(f"❌ SSH failed for {hostname}: {e}")
        return {
            "Hostname": hostname,
            "Total Ports": 0,
            "Active Ports": 0,
            "Port Utilization %": 0,
        }

# ===============================
# MAIN
# ===============================
def main():
    if not API_TOKEN:
        raise RuntimeError("LIBRENMS_TOKEN environment variable not set")

    df = pd.read_excel(INPUT_EXCEL)
    if "hostname" not in df.columns:
        raise ValueError("Excel must contain column: hostname")

    active_devices = get_active_cisco_devices()

    targets = [
        str(h).strip()
        for h in df["hostname"]
        if str(h).strip() in active_devices
    ]

    print(f"\n🚀 Running parallel SSH for {len(targets)} active devices "
          f"(workers={MAX_WORKERS})\n")

    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(ssh_check, h): h for h in targets}

        for future in as_completed(futures):
            results.append(future.result())

    result_df = pd.DataFrame(results)

    print("\n📊 SSH Port Utilization Summary (PARALLEL)\n")
    print(tabulate(result_df, headers="keys", tablefmt="grid", showindex=False))

    result_df.to_excel(OUTPUT_EXCEL, index=False)
    print(f"\n✅ Results saved to {OUTPUT_EXCEL}")

# ===============================
# ENTRY POINT
# ===============================
if __name__ == "__main__":
    main()
