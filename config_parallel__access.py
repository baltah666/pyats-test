#!/usr/bin/env python3

from pyats.topology import loader
from pyats.async_ import pcall
import time

config_commands = """
show running-config | section VfSnmpReadAcl
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

        device.configure(config_commands, error_pattern=[])
        device.execute("write memory")

    except Exception as e:
        print(f"[ERROR] {device.name}: {e}")

    finally:
        if device.connected:
            device.disconnect()


# Run ALL devices in parallel
pcall(run_on_device, device=testbed.devices.values())

print(f"Runtime of the program is {time.time() - start_time:.2f} seconds")
