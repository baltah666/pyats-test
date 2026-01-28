#!/usr/bin/env python3

import os
import sys
import time
from pyats.topology import loader
from pyats.async_ import pcall
from tabulate import tabulate

# ==========================================================
# Required Jenkins parameters
# ==========================================================

CONFIG_COMMANDS = os.getenv("CONFIG_COMMANDS")
TESTBEDS_ENV = os.getenv("TESTBEDS")

if not CONFIG_COMMANDS or not CONFIG_COMMANDS.strip():
    print("❌ CONFIG_COMMANDS is not set or empty")
    sys.exit(1)

if not TESTBEDS_ENV or not TESTBEDS_ENV.strip():
    print("❌ TESTBEDS is not set or empty")
    sys.exit(1)

# ==========================================================
# Parse testbed files
# ==========================================================

TESTBED_FILES = [tb.strip() for tb in TESTBEDS_ENV.split(",") if tb.strip()]

if not TESTBED_FILES:
    print("❌ No testbeds selected")
    sys.exit(1)

for tb in TESTBED_FILES:
    if not os.path.isfile(tb):
        print(f"❌ Testbed file not found: {tb}")
        sys.exit(1)

# ==========================================================
# Per-device worker (parallel)
# ==========================================================

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

# ==========================================================
# Execution report
# ==========================================================

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
    print(tabulate(table, headers=["Device", "Status"], tablefmt="grid"))
    print(f"\nSuccess: {ok_count}")
    print(f"Failed : {fail_count}")
    print("==================================================")

# ==========================================================
# Main
# ==========================================================

def main():
    start_time = time.time()
    all_results = []

    print("\n🔧 Configuration to be pushed:")
    print("--------------------------------------------------")
    print(CONFIG_COMMANDS)
    print("--------------------------------------------------")

    for tb_file in TESTBED_FILES:
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
