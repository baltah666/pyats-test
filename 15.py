#!/usr/bin/env python3

import os
import time
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
PASSWORD = "cisco"   # <-- set correctly

DEVICE_TYPE = "cisco_ios"
MAX_WORKERS = 5
CONNECT_DELAY = 0.2

HEADERS = {
    "X-Auth-Token": API_TOKEN,
    "Accept": "application/json",
}

# Media types we want as columns
MEDIA_COLUMNS = [
    "10/100BaseTX",
    "10/100/1000BaseTX",
    "1000BaseLX SFP",
]

STATUS_WORDS = {
    "connected",
    "notconnect",
    "disabled",
    "err-disabled",
    "inactive",
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
# PARSER (CORRECT)
# ===============================
def parse_interfaces(output: str):
    total_ports = 0
    active_ports = 0

    media_counts = {m: 0 for m in MEDIA_COLUMNS}

    for raw in output.splitlines():
        line = raw.strip()
        if not line or line.startswith("Port"):
            continue

        if not line.startswith(("Fa", "Gi", "Te", "Po")):
            continue

        parts = line.split()

        # Find status token position
        status_idx = None
        for i, p in enumerate(parts):
            if p in STATUS_WORDS:
                status_idx = i
                break

        if status_idx is None or len(parts) < status_idx + 5:
            continue

        status = parts[status_idx]
        port_type = " ".join(parts[status_idx + 4:])

        total_ports += 1

        if status == "connected":
            active_ports += 1
            for media in MEDIA_COLUMNS:
                if media in port_type:
                    media_counts[media] += 1

    return total_ports, active_ports, media_counts

def pct(active, total):
    return round((active / total) * 100, 2) if total else 0

# ===============================
# SSH WORKER
# ===============================
def ssh_worker(hostname: str):
    time.sleep(CONNECT_DELAY)

    device = {
        "device_type": DEVICE_TYPE,
        "host": hostname,
        "username": USERNAME,
        "password": PASSWORD,
        "fast_cli": False,
    }

    base_row = {
        "Hostname": hostname,
        "Total Ports": 0,
        "Active Ports": 0,
        "Port Utilization %": 0,
    }
    for m in MEDIA_COLUMNS:
        base_row[m] = 0

    try:
        print(f" Connecting to {hostname} ...")

        with ConnectHandler(**device) as conn:
            output = conn.send_command(
                "show interfaces status",
                expect_string=r"#",
                read_timeout=25,
            )

        total, active, media = parse_interfaces(output)

        base_row["Total Ports"] = total
        base_row["Active Ports"] = active
        base_row["Port Utilization %"] = pct(active, total)

        for m in MEDIA_COLUMNS:
            base_row[m] = media[m]

    except Exception as e:
        print(f"❌ SSH failed for {hostname}: {e}")

    return base_row

# ===============================
# MAIN
# ===============================
def main():
    if not API_TOKEN:
        raise RuntimeError("LIBRENMS_TOKEN not set")

    df = pd.read_excel(INPUT_EXCEL)
    if "hostname" not in df.columns:
        raise ValueError("Excel must contain a column named 'hostname'")

    active_devices = get_active_cisco_devices()
    targets = [h for h in df["hostname"] if h in active_devices]

    print(f"\n Running parallel SSH for {len(targets)} active devices (workers={MAX_WORKERS})\n")

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(ssh_worker, h) for h in targets]
        for f in as_completed(futures):
            results.append(f.result())

    result_df = pd.DataFrame(results)

    print("\n SSH Port Utilization Summary (MEDIA COLUMNS)\n")
    print(tabulate(result_df, headers="keys", tablefmt="grid", showindex=False))

    result_df.to_excel(OUTPUT_EXCEL, index=False)
    print(f"\n✅ Results saved to {OUTPUT_EXCEL}")

if __name__ == "__main__":
    main()
