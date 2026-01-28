#!/usr/bin/env python3
"""
LibreNMS Port Utilization (GUI-aligned)

Reads devices from an Excel file (column: hostname)
For each device, pulls ports from LibreNMS API and calculates:
- Total Ports
- Active Ports (admin up + oper up + speed > 0 + not deleted)
- Port Utilization %

Outputs:
- Console table
- Excel report: device_ports_status.xlsx

Requirements (venv):
  pip install requests pandas openpyxl tabulate

Run:
  export LIBRENMS_TOKEN="your_token"
  python FINAL_librenms_port_utilization.py
"""

import os
import sys
import requests
import pandas as pd
from tabulate import tabulate
from urllib.parse import quote
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================================================
# CONFIGURATION
# ==================================================
LIBRENMS_BASE_URL = "http://localhost:8081"

# ✅ Your requested input name
INPUT_EXCEL = "librenms_devices.xlsx"

OUTPUT_EXCEL = "device_ports_status.xlsx"

# Debug (proof)
DEBUG_MODE = True
DEBUG_DEVICE = "home-lab-access-sw01"
DEBUG_LIMIT = 25

# Port filtering (to match “physical ports usage” better)
EXCLUDE_VLANS = True          # Exclude Vlan interfaces (ifType=vlan or ifName startswith Vl/Vlan)
EXCLUDE_LOOPBACKS = True      # Exclude loopbacks (ifType=softwareLoopback or name starts Lo)
EXCLUDE_NULL = True           # Exclude Null interfaces (name starts Nu/Null)
EXCLUDE_PORTCHANNELS = False  # If you want ONLY physical ports, set True to exclude Po/Port-channel

# ==================================================
# AUTH
# ==================================================
API_TOKEN = os.getenv("LIBRENMS_TOKEN")
if not API_TOKEN:
    print("❌ ERROR: LIBRENMS_TOKEN environment variable not set.")
    print("   Example: export LIBRENMS_TOKEN='xxxxxxxxxxxxxxxxxxxx'")
    sys.exit(1)

HEADERS = {
    "X-Auth-Token": API_TOKEN,
    "Accept": "application/json",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ==================================================
# API HELPERS
# ==================================================
def api_get(path: str, timeout: int = 20) -> dict:
    """GET helper that returns JSON or raises with useful context."""
    url = f"{LIBRENMS_BASE_URL}{path}"
    r = SESSION.get(url, verify=False, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"API GET failed: {r.status_code} {url}\n{r.text}")
    return r.json()

def build_device_id_map() -> dict:
    """Map hostname -> device_id from /api/v0/devices."""
    data = api_get("/api/v0/devices")
    devices = data.get("devices", [])
    mapping = {}
    for d in devices:
        hn = d.get("hostname")
        did = d.get("device_id")
        if hn and did is not None:
            mapping[str(hn)] = int(did)
    return mapping

def get_ports_by_hostname(hostname: str) -> list:
    """
    Try the hostname endpoint first:
      /api/v0/devices/{hostname}/ports
    """
    hn = quote(str(hostname), safe="")
    data = api_get(f"/api/v0/devices/{hn}/ports")
    return data.get("ports", [])

def get_ports_by_device_id(device_id: int) -> list:
    """Fallback endpoint (often more reliable in some installs)."""
    data = api_get(f"/api/v0/devices/{int(device_id)}/ports")
    return data.get("ports", [])

def get_ports(hostname: str, id_map: dict) -> list:
    """
    Fetch ports robustly:
    1) Try hostname endpoint
    2) If fails, try device_id endpoint
    """
    try:
        return get_ports_by_hostname(hostname)
    except Exception:
        # fallback by id
        did = id_map.get(str(hostname))
        if did is None:
            # Sometimes Excel has sysName or IP. Try to find a matching key.
            # We'll attempt case-insensitive match.
            for k, v in id_map.items():
                if k.lower() == str(hostname).lower():
                    did = v
                    break
        if did is None:
            return []
        try:
            return get_ports_by_device_id(did)
        except Exception:
            return []

# ==================================================
# PORT LOGIC (GUI-ALIGNED)
# ==================================================
def _name_starts_with_any(name: str, prefixes: tuple) -> bool:
    n = (name or "").lower()
    return any(n.startswith(p.lower()) for p in prefixes)

def should_exclude_port(port: dict) -> bool:
    """
    Exclude non-physical / special interfaces if configured.
    Uses both ifType and ifName heuristics (because some devices differ).
    """
    ifname = str(port.get("ifName") or port.get("ifDescr") or "").strip()
    iftype = str(port.get("ifType") or "").strip().lower()

    # VLAN/SVI
    if EXCLUDE_VLANS:
        if iftype == "vlan" or _name_starts_with_any(ifname, ("vl", "vlan")):
            return True

    # Loopback
    if EXCLUDE_LOOPBACKS:
        if iftype == "softwareloopback" or _name_starts_with_any(ifname, ("lo", "loopback")):
            return True

    # Null
    if EXCLUDE_NULL:
        if _name_starts_with_any(ifname, ("nu", "null")):
            return True

    # Port-Channel
    if EXCLUDE_PORTCHANNELS:
        if _name_starts_with_any(ifname, ("po", "port-channel", "portchannel")):
            return True

    return False

def is_active_port(port: dict) -> bool:
    """
    Active = matches GUI “connected/up” concept:
      - not deleted
      - admin up (1)
      - oper up  (1)
      - speed > 0
      - not excluded (vlan/loopback/null/po based on config)
    """
    if should_exclude_port(port):
        return False

    # deleted flag: 0 = valid, 1 = deleted
    deleted = port.get("deleted", 0)
    try:
        if int(deleted) != 0:
            return False
    except (TypeError, ValueError):
        pass

    # admin/oper status
    try:
        admin = int(port.get("ifAdminStatus"))
        oper = int(port.get("ifOperStatus"))
    except (TypeError, ValueError):
        return False

    if admin != 1 or oper != 1:
        return False

    # speed
    speed_val = port.get("ifSpeed", 0)
    try:
        speed = int(float(speed_val))
    except (TypeError, ValueError):
        speed = 0

    return speed > 0

def safe_percent(active: int, total: int) -> float:
    return round((active / total) * 100, 2) if total else 0.0

# ==================================================
# DEBUG / PROOF
# ==================================================
def debug_ports(hostname: str, id_map: dict, limit: int = 20) -> None:
    print(f"\n🔎 DEBUG (PROOF): Port fields returned by API for: {hostname}\n")

    ports = get_ports(hostname, id_map)
    if not ports:
        print("⚠️ No ports returned for this device (API returned empty or device not found).")
        return

    for p in ports[:limit]:
        ifname = p.get("ifName") or p.get("ifDescr")
        print(
            f"{str(ifname):12} "
            f"admin={p.get('ifAdminStatus')} "
            f"oper={p.get('ifOperStatus')} "
            f"speed={p.get('ifSpeed')} "
            f"type={p.get('ifType')} "
            f"deleted={p.get('deleted')}"
        )

    print("\n🔎 END DEBUG\n")

# ==================================================
# MAIN
# ==================================================
def main():
    # Load Excel
    df = pd.read_excel(INPUT_EXCEL)
    if "hostname" not in df.columns:
        raise ValueError("❌ Excel must contain a column named: hostname")

    # Build hostname->device_id map once
    id_map = build_device_id_map()

    # Debug once
    if DEBUG_MODE and DEBUG_DEVICE:
        debug_ports(DEBUG_DEVICE, id_map, limit=DEBUG_LIMIT)

    results = []
    for hostname in df["hostname"].astype(str).tolist():
        hostname = hostname.strip()
        if not hostname:
            continue

        print(f"🔍 Processing {hostname} ...")
        ports = get_ports(hostname, id_map)

        # total ports (after exclusions, so utilization makes sense for “physical ports usage”)
        filtered_ports = [p for p in ports if not should_exclude_port(p)]
        total_ports = len(filtered_ports)

        active_ports = sum(1 for p in filtered_ports if is_active_port(p))
        utilization = safe_percent(active_ports, total_ports)

        results.append({
            "Hostname": hostname,
            "Total Ports": total_ports,
            "Active Ports": active_ports,
            "Port Utilization %": utilization,
        })

    out_df = pd.DataFrame(results, columns=["Hostname", "Total Ports", "Active Ports", "Port Utilization %"])

    print("\n📊 Port Utilization Summary\n")
    if len(out_df) > 0:
        print(tabulate(out_df.values, headers=out_df.columns, tablefmt="grid"))
    else:
        print("⚠️ No results. Check Excel hostnames and LibreNMS API access.")

    out_df.to_excel(OUTPUT_EXCEL, index=False)
    print(f"\n✅ Results saved to {OUTPUT_EXCEL}")

if __name__ == "__main__":
    main()
