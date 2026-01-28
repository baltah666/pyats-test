#!/usr/bin/env python3

from pyats.topology import loader
from pyats.async_ import pcall
import time

#SHOW_COMMANDS = [
#    "show mac address-table | include b8a4:4f",
#    "show interface status",
#]

config_commands = """\
no ip access-list standard SnmpReadAcl

ip access-list standard VfSnmpReadAcl
 remark sneoshh1122.eur.corp.vattenfall.com
 permit 193.111.44.164
 permit 10.40.133.143
 permit 10.40.133.144
 remark sastorm5672.tech.vattenfall.com
 permit 10.204.127.62
 remark sneyexx0966.eur.corp.vattenfall.com
 permit 151.156.179.40
 remark sneosbe1201.eur.corp.vattenfall.com
 permit 10.255.1.86
 remark sastorm2860.eur.corp.vattenfall.com
 permit 151.156.178.91
 remark sneyexx0965.eur.corp.vattenfall.com
 permit 151.156.179.74
 permit 10.186.13.0 0.0.0.255
 remark sedc-zon3-TechIT-MGMT
 permit 151.156.226.96 0.0.0.31
 deny   any log 0x894DACD6
"""

testbed = loader.load("testbed.yaml")

start_time = time.time()

def run_on_device(device):
    try:
        device.connect(
            learn_hostname=True,
            init_exec_commands=[],
            init_config_commands=[]
        )

        for cmd in SHOW_COMMANDS:
            output = device.execute(cmd)
            print(f"\n===== {device.name} | {cmd} =====\n{output}")

        device.execute("write memory")

    except Exception as e:
        print(f"[ERROR] {device.name}: {e}")

    finally:
        if device.connected:
            device.disconnect()


pcall(run_on_device, device=testbed.devices.values())

print(f"\nRuntime of the program is {time.time() - start_time:.2f} seconds")
