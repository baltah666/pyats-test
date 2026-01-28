#!/usr/bin/env python3
import json
import requests
import jinja2
import urllib3
from pprint import pprint

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================================================
# LibreNMS API CONFIG
# ==================================================
LIBRENMS_URL = "http://192.168.1.254:8081"
API_TOKEN = "4f448a042f7cbfcc875c3be51627f100"

HEADERS = {
    "X-Auth-Token": API_TOKEN
}

# ==================================================
# HARDWARE FAMILIES & MODELS
# ==================================================
HARDWARE_FAMILIES = {
    "access_9200": [
        "C9200-24P",
        "C9200-48P",
        "C9200L-24P-4G",
        "C9200L-48P-4G",
        "C9200CX-8P-2X2G",
    ],
    "access_9300": [
        "C9300-24P",
        "C9300-48UXM",
        "C9300X-24Y",
    ],
    "core_9500": [
        "C9500-16X",
    ],
    "access_2960": [
        "WS-C2960C-8PC-L",
        "WS-C2960X-24PS-L",
    ],
    "industrial": [
        "IE-2000-8TC-G-B",
    ],
    "routers": [
        "ISR4431/K9",
        "ISR4451-X/K9",
    ],
    "datacenter_n9k": [
        "N9K-C92348GC-X",
    ],
}

# Flatten list for filtering
ALL_MODELS = [m for models in HARDWARE_FAMILIES.values() for m in models]

# ==================================================
# GET DEVICES FROM LIBRENMS
# ==================================================
response = requests.get(
    f"{LIBRENMS_URL}/api/v0/devices",
    headers=HEADERS,
    timeout=30
)
response.raise_for_status()

api_data = response.json()

# ==================================================
# BUILD MASTER INVENTORY
# ==================================================
master_inventory = []

print("Alias,IP,PID,Version")

for device in api_data.get("devices", []):

    os_name = device.get("os")
    status = device.get("status")
    hardware = device.get("hardware", "")

    if (
        os_name in ("ios", "iosxe", "nxos")
        and status != 0
        and any(model in hardware for model in ALL_MODELS)
    ):
        hostname = device.get("hostname", "")
        alias = hostname.split(".")[0] if hostname else ""

        # Detect family
        dev_family = "unknown"
        for family, models in HARDWARE_FAMILIES.items():
            if any(model in hardware for model in models):
                dev_family = family
                break

        entry = {
            "dev_name": hostname,
            "dev_alias": alias,
            "dev_os": os_name,
            "dev_ip": device.get("ip", ""),
            "dev_net_location": device.get("location", "unknown"),
            "dev_net_type": "accessctrl-techit",
            "dev_netmiko_type": "cisco_ios",
            "dev_model": hardware,
            "dev_family": dev_family,
        }

        master_inventory.append(entry)

        print(f"{alias},{entry['dev_ip']},{hardware},{device.get('version')}")

print(f"\nTotal matched devices: {len(master_inventory)}\n")

# ==================================================
# SPLIT INVENTORY BY FAMILY
# ==================================================
inventories_by_family = {}

for item in master_inventory:
    inventories_by_family.setdefault(item["dev_family"], []).append(item)

# Debug
for fam, items in inventories_by_family.items():
    print(f"{fam}: {len(items)} devices")

# ==================================================
# JINJA ENVIRONMENT
# ==================================================
env = jinja2.Environment(
    loader=jinja2.FileSystemLoader("."),
    trim_blocks=True,
    lstrip_blocks=True
)

template = env.get_template("pyats_testbed_template.j2")

# ==================================================
# GENERATE TESTBED FILES
# ==================================================
for family, items in inventories_by_family.items():

    if family == "unknown":
        continue

    data = {"inventory": items}

    filename = f"testbed_{family}.yaml"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(template.render(**data))

    print(f"✅ Generated {filename}")

print("\n🎉 All pyATS testbeds generated successfully")
