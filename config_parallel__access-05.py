#!/usr/bin/env python3

from pyats.topology import loader
from pyats.async_ import pcall
from tabulate import tabulate
import time
import sys

# ==============================
# Configuration to push
# ==============================
CONFIG_COMMANDS = """
ip http server
"""

# ==============================
# Available testbeds
# ==============================
TESTBEDS = {
    "1": "testbed_access_9200.yaml",
    "2": "testbed_access_9300.yaml",
    "3": "testbed_access_2960.yaml",
    "4": "testbed_datacenter_n9k.yaml",
    "5": "testbed_routers.yaml",
    "6": "testbed_industrial.yaml",
    "7": "testbed_core_9500.yaml",
}

# ==============================
# Per-device worker (parallel)
# ==============================
def run_on_device(device):
    try:
        device.connect(
            learn_hostname=True,
            init_exec_commands=[],
            init_config_commands=[]
        )

        device.configure(CONFIG_COMMANDS)
        device.execute("write memory")

        print(f"[OK] {device.name}")
        return (device.name, "OK")

    except Exception as e:
        print(f"[ERROR] {device.name}: {e}")
        return (device.name, "NOT OK")

    finally:
        if device.connected:
            device.disconnect()

# ==============================
# Testbed selection logic
# ==============================
def select_testbeds():
    print("\nSelect target testbeds:")
    print("0) ALL testbeds")
    for key, tb in TESTBEDS.items():
        print(f"{key}) {tb}")

    choice = input("\nEnter choice (e.g. 1,2,3): ").strip()

    if choice == "0":
        return list(TESTBEDS.values())

    selected = []
    for item in choice.split(","):
        key = item.strip()
        if key not in TESTBEDS:
            print(f"❌ Invalid selection: {key}")
            sys.exit(1)
        selected.append(TESTBEDS[key])

    selected = list(dict.fromkeys(selected))

    if len(selected) > 1:
        confirm = input(
            f"⚠️ You selected {len(selected)} testbeds. Continue? (y/n): "
        ).lower()
        if confirm != "y":
            print("❌ Aborted by user")
            sys.exit(0)

    return selected

# ==============================
# Execution report (table)
# ==============================
def print_report(results):
    table = []
    ok_count = 0
    fail_count = 0

    for device, status in results:
        table.append([device, status])
        if status == "OK":
            ok_count += 1
        else:
            fail_count += 1

    print("\n================ Execution Report ================\n")
    print(tabulate(
        table,
        headers=["Device", "Status"],
        tablefmt="grid"
    ))

    print(f"\nSuccess: {ok_count}")
    print(f"Failed : {fail_count}")
    print("==================================================")

# ==============================
# Main
# ==============================
def main():
    start_time = time.time()
    all_results = []

    selected_testbeds = select_testbeds()

    for tb_file in selected_testbeds:
        print(f"\n🚀 Running on testbed: {tb_file}")
        testbed = loader.load(tb_file)

        results = pcall(
            run_on_device,
            device=testbed.devices.values()
        )

        all_results.extend(results)

    print_report(all_results)
    print(f"\n⏱️ Total runtime: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    main()
