#!/usr/bin/env python3

import os
import time
import pandas as pd
import requests
from netmiko import ConnectHandler
from tabulate import tabulate
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3
from collections import Counter

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

DEVICE_TYPE = "cisco_ios"

MAX_WORKERS = 5
CONNECT_DELAY = 0.8

# ===============================
# HEADERS
# ===============================
HEADERS = {
    "X-Auth-Token": API_TOKEN,
    "Accept": "application/json",
}

# ===============================
# LIBRENMS
# ===============================
def get_active_cisco_devices():
    r = requests.get(
        f"{LIBRENMS_URL}/api/v0/devices",
        headers=HEADERS,
        verify=False,
        timeout=20,
    )
    r.raise_for_status()

    return {
        d["hostname"]
        for d in r.json()["devices"]
        if d.get("status") == 1 and d.get("os") in ("ios", "iosxe")
    }

# ===============================
# PARSING
# ===============================
def parse_interfaces(output):
    total_ports = 0
    active_ports = 0
    media_counter = Counter()

    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("Port"):
            continue

        # Only physical / logical interfaces
        if not line.startswith(("Fa", "Gi", "Te", "Po")):
            continue

        total_ports += 1

        parts = line.split()
        status = parts[2] if len(parts) > 2 else ""

        if status == "connected":
            active_ports += 1

            # Type is always at the end
            port_type = " ".join(parts[-2:]) if "Base" in parts[-1] else parts[-1]
            media_counter[port_type] += 1

    return total_ports, active_ports, media_counter

# ===============================
# SSH
# ===============================
def ssh_check(hostname):
    time.sleep(CONNECT_DELAY)

    device = {
        "device_type": DEVICE_TYPE,
        "host": hostname,
        "username": USERNAME,
        "password": PASSWORD,
        "fast_cli": False,
    }

    try:
        print(f"🔍 Connecting to {hostname} ...")

        with ConnectHandler(**device) as conn:
            output = conn.send_command(
                "show interfaces status",
                expect_string=r"#",
                read_timeout=20,
            )

        total, active, media = parse_interfaces(output)

        media_summary = ", ".join(
            f"{k}: {v}" for k, v in media.items()
        ) if media else "None"

        return {
            "Hostname": hostname,
            "Total Ports": total,
            "Active Ports": active,
            "Port Utilization %": round((active / total) * 100, 2) if total else 0,
            "Active Port Types": media_summary,
        }

    except Exception as e:
        print(f"❌ SSH failed for {hostname}: {e}")
        return {
            "Hostname": hostname,
            "Total Ports": 0,
            "Active Ports": 0,
            "Port Utilization %": 0,
            "Active Port Types": "N/A",
        }

# ===============================
# MAIN
# ===============================
def main():
    if not API_TOKEN:
        raise RuntimeError("LIBRENMS_TOKEN not set")

    df = pd.read_excel(INPUT_EXCEL)
    active_devices = get_active_cisco_devices()

    targets = [
        str(h).strip()
        for h in df["hostname"]
        if str(h).strip() in active_devices
    ]

    print(
        f"\n🚀 Running parallel SSH for {len(targets)} active devices "
        f"(workers={MAX_WORKERS})\n"
    )

    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(ssh_check, h) for h in targets]
        for future in as_completed(futures):
            results.append(future.result())

    result_df = pd.DataFrame(results)

    print("\n📊 SSH Port Utilization Summary (WITH MEDIA TYPE)\n")
    print(tabulate(result_df, headers="keys", tablefmt="grid", showindex=False))

    result_df.to_excel(OUTPUT_EXCEL, index=False)
    print(f"\n✅ Results saved to {OUTPUT_EXCEL}")

if __name__ == "__main__":
    main()
