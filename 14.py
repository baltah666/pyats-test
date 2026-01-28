#!/usr/bin/env python3

import os
import time
import pandas as pd
import requests
from netmiko import ConnectHandler
from tabulate import tabulate
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
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
PASSWORD = "cisco"   # <-- put the right password

DEVICE_TYPE = "cisco_ios"

MAX_WORKERS = 5
CONNECT_DELAY = 0.2  # small stagger to avoid SSH bursts

# Optional debug: set DEBUG_HOST=home-lab-access-sw02 to see parsing
DEBUG_HOST = os.getenv("DEBUG_HOST", "").strip()

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
# PARSING (FINAL FIX)
# ===============================
STATUS_WORDS = {
    "connected",
    "notconnect",
    "disabled",
    "err-disabled",
    "inactive",
    "monitoring",
    "sfpAbsent",
}

def parse_interfaces(show_int_status_output: str, hostname: str):
    """
    Robust parser for: show interfaces status
    Works even when Name column is blank (variable-width).
    """
    total_ports = 0
    active_ports = 0
    media_counter = Counter()

    for raw in show_int_status_output.splitlines():
        line = raw.rstrip("\n")

        if not line.strip():
            continue
        if line.strip().startswith("Port"):
            continue

        # Only count Fa/Gi/Te/Po
        l = line.lstrip()
        if not l.startswith(("Fa", "Gi", "Te", "Po")):
            continue

        parts = l.split()
        # Example (no Name):
        # Fa0/1 connected 1 a-full a-100 10/100BaseTX
        #
        # Example (with Name):
        # Gi0/1 Home-Lab-Core-sw01 connected trunk a-full a-1000 10/100/1000BaseTX

        # Find status token position (connected/notconnect/disabled/...)
        status_idx = None
        for i, tok in enumerate(parts):
            if tok in STATUS_WORDS:
                status_idx = i
                break

        if status_idx is None:
            # Couldn't parse this line
            if hostname == DEBUG_HOST:
                print(f"DEBUG: could not find status in line: {line}")
            continue

        # Must have at least: status vlan duplex speed type
        if len(parts) < status_idx + 5:
            if hostname == DEBUG_HOST:
                print(f"DEBUG: line too short after status: {line}")
            continue

        port = parts[0]
        status = parts[status_idx]
        vlan = parts[status_idx + 1]
        duplex = parts[status_idx + 2]
        speed = parts[status_idx + 3]
        port_type = " ".join(parts[status_idx + 4:]).strip()  # type may be multi-word (e.g. "1000BaseLX SFP")

        # Count total physical/logical interfaces
        total_ports += 1

        # Count active only
        if status == "connected":
            active_ports += 1
            media_counter[port_type] += 1

        if hostname == DEBUG_HOST:
            print(f"DEBUG parsed: {port=} {status=} {vlan=} {duplex=} {speed=} {port_type=}")

    return total_ports, active_ports, media_counter

def pct(active, total):
    return round((active / total) * 100, 2) if total else 0

# ===============================
# SSH
# ===============================
def ssh_check(hostname: str):
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
                read_timeout=25,
            )

        total, active, media = parse_interfaces(output, hostname)

        media_summary = ", ".join(f"{k}: {v}" for k, v in media.most_common()) if media else "None"

        return {
            "Hostname": hostname,
            "Total Ports": total,
            "Active Ports": active,
            "Port Utilization %": pct(active, total),
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
        raise RuntimeError("LIBRENMS_TOKEN not set (export LIBRENMS_TOKEN=...)")

    df = pd.read_excel(INPUT_EXCEL)
    if "hostname" not in df.columns:
        raise ValueError("Excel must contain a column named: hostname")

    active_devices = get_active_cisco_devices()

    targets = [
        str(h).strip()
        for h in df["hostname"]
        if str(h).strip() in active_devices
    ]

    print(f"\n🚀 Running parallel SSH for {len(targets)} active devices (workers={MAX_WORKERS})\n")

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(ssh_check, h) for h in targets]
        for f in as_completed(futures):
            results.append(f.result())

    result_df = pd.DataFrame(results)

    print("\n📊 SSH Port Utilization Summary (WITH MEDIA TYPE)\n")
    print(tabulate(result_df, headers="keys", tablefmt="grid", showindex=False))

    result_df.to_excel(OUTPUT_EXCEL, index=False)
    print(f"\n✅ Results saved to {OUTPUT_EXCEL}")

if __name__ == "__main__":
    main()
