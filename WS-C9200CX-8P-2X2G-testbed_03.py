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
# HARDWARE MODELS (used for filtering & splitting)
# ==================================================
MODEL_C9200 = "C9200CX-8P-2X2G"
MODEL_2960 = "WS-C2960C-8PC-L"

ALLOWED_MODELS = (MODEL_C9200, MODEL_2960)

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
inventory = []
print("Alias,IP,PID,Version")

for device in api_data.get("devices", []):

    os_name = device.get("os")
    status = device.get("status")
    hardware = device.get("hardware", "")

    if (
        os_name in ("ios", "iosxe")
        and status != 0
        and any(model in hardware for model in ALLOWED_MODELS)
    ):
        hostname = device.get("hostname", "")
        alias = hostname.split(".")[0] if hostname else ""

        entry = {
            "dev_name": hostname,
            "dev_alias": alias,
            "dev_os": os_name,
            "dev_ip": device.get("ip", ""),
            "dev_net_location": device.get("location", "home-lab"),
            "dev_net_type": "accessctrl-techit",
            "dev_netmiko_type": "cisco_ios",
            "dev_model": hardware,
        }

        inventory.append(entry)
        print(f"{alias},{entry['dev_ip']},{hardware},{device.get('version')}")

print(f"\nTotal matched devices: {len(inventory)}\n")

# ==================================================
# SPLIT INVENTORY BY MODEL (OPTION 2)
# ==================================================
inventory_c9200 = {
    "inventory": [
        d for d in inventory if MODEL_C9200 in d["dev_model"]
    ]
}

inventory_2960 = {
    "inventory": [
        d for d in inventory if MODEL_2960 in d["dev_model"]
    ]
}

print("C9200 devices:", len(inventory_c9200["inventory"]))
print("2960 devices :", len(inventory_2960["inventory"]))

# ==================================================
# DEBUG (OPTIONAL)
# ==================================================
print("\n--- C9200 INVENTORY ---")
pprint(inventory_c9200)

print("\n--- 2960 INVENTORY ---")
pprint(inventory_2960)

# ==================================================
# WRITE JSON FILES (OPTIONAL)
# ==================================================
with open("inventory_c9200.json", "w", encoding="utf-8") as f:
    json.dump(inventory_c9200, f, indent=4)

with open("inventory_2960.json", "w", encoding="utf-8") as f:
    json.dump(inventory_2960, f, indent=4)

# ==================================================
# RENDER TESTBED FILES
# ==================================================
env = jinja2.Environment(
    loader=jinja2.FileSystemLoader("."),
    trim_blocks=True,
    lstrip_blocks=True
)

template = env.get_template("pyats_testbed_template.j2")

if inventory_c9200["inventory"]:
    with open("C9200CX-testbed.yaml", "w", encoding="utf-8") as f:
        f.write(template.render(**inventory_c9200))
    print("✅ Generated C9200CX-testbed.yaml")

if inventory_2960["inventory"]:
    with open("WS-C2960C-testbed.yaml", "w", encoding="utf-8") as f:
        f.write(template.render(**inventory_2960))
    print("✅ Generated WS-C2960C-testbed.yaml")

print("\n🎉 Testbed generation completed successfully")
