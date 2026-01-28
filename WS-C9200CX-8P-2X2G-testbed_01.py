#!/usr/bin/env python3
import json
import requests
import jinja2
import urllib3
from pprint import pprint

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==============================
# LibreNMS API CONFIG
# ==============================
LIBRENMS_URL = "http://192.168.1.254:8081"   # <-- HTTP confirmed
API_TOKEN = "4f448a042f7cbfcc875c3be51627f100"

HEADERS = {
    "X-Auth-Token": API_TOKEN
}

# ==============================
# GET DEVICES FROM LIBRENMS
# ==============================
response = requests.get(
    f"{LIBRENMS_URL}/api/v0/devices",
    headers=HEADERS,
    timeout=30
)
response.raise_for_status()

api_data = response.json()

# ==============================
# BUILD INVENTORY
# ==============================
inventory_dict = {"inventory": []}
count = 0

print("Alias,IP,PID,Version")

for device in api_data.get("devices", []):

    os_name = device.get("os")
    status = device.get("status")
    hardware = device.get("hardware", "")

    # FILTER CONDITIONS
    if (
        os_name in ("ios", "iosxe")
        and status != 0
        and "C9200CX-8P-2X2G" in hardware
    ):
        hostname = device.get("hostname", "")
        alias = hostname.split(".")[0] if hostname else ""

        inventory_dict["inventory"].append({
            "dev_name": hostname,
            "dev_alias": alias,
            "dev_os": os_name,
            "dev_ip": device.get("ip", ""),
            "dev_net_location": device.get("location", "home-lab"),
            "dev_net_type": "accessctrl-techit",
            "dev_netmiko_type": "cisco_ios",
        })

        print(f"{alias},{device.get('ip')},{hardware},{device.get('version')}")
        count += 1

print(f"\nMatched devices: {count}\n")

# ==============================
# DEBUG OUTPUT (OPTIONAL)
# ==============================
pprint(inventory_dict)

# ==============================
# WRITE JSON INVENTORY (OPTIONAL)
# ==============================
with open("pyats_inventory_access.json", "w", encoding="utf-8") as f:
    json.dump(inventory_dict, f, indent=4)

# ==============================
# RENDER JINJA TEMPLATE
# ==============================
env = jinja2.Environment(
    loader=jinja2.FileSystemLoader("."),
    trim_blocks=True,
    lstrip_blocks=True
)

template = env.get_template("pyats_testbed_template.j2")
rendered_yaml = template.render(**inventory_dict)

# ==============================
# WRITE TESTBED YAML
# ==============================
with open("C9200CX-8P-2X2G-testbedaccess.yaml", "w", encoding="utf-8") as f:
    f.write(rendered_yaml)

print("✅ pyATS testbed file generated successfully")
