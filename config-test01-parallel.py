#!/usr/bin/env python3

from pyats.topology import loader
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import traceback

CONFIG_COMMANDS = """\
logging host 192.168.1.254 session-id string techit
logging trap informational
logging facility local7
logging source-interface Vlan1
exit
"""

def configure_device(device):
    """
    Configure one device (runs inside a thread)
    """
    try:
        print(f"🔌 Connecting to {device.name}")
        device.connect(
            learn_hostname=True,
            init_exec_commands=[],
            init_config_commands=[]
        )

        print(f"⚙️  Configuring {device.name}")
        device.configure(CONFIG_COMMANDS, error_pattern=[])

        print(f"💾 Saving config on {device.name}")
        device.execute("write memory")

        device.disconnect()
        print(f"✅ Done: {device.name}")

        return device.name, "SUCCESS"

    except Exception as e:
        print(f"❌ Error on {device.name}")
        traceback.print_exc()
        return device.name, f"FAILED: {e}"


def main():
    testbed = loader.load("testbed.yaml")

    start_time = time.time()

    devices = list(testbed.devices.values())
    print(f"🚀 Running in parallel on {len(devices)} devices\n")

    results = []

    # Tune max_workers if needed (e.g. CPU / SSH limits)
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(configure_device, device): device.name
            for device in devices
        }

        for future in as_completed(futures):
            results.append(future.result())

    print("\n📊 Summary")
    for device, status in results:
        print(f"{device}: {status}")

    print(f"\n⏱️ Runtime: {time.time() - start_time:.2f} seconds")


if __name__ == "__main__":
    main()
