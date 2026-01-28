#!/usr/bin/env python3

from pyats.topology import loader
from pyats.async_ import pcall
import time
from pathlib import Path


BASE_DIR = Path(__file__).parent
COMMANDS_DIR = BASE_DIR / "commands"

SHOW_FILE = COMMANDS_DIR / "show_commands.txt"
EXEC_FILE = COMMANDS_DIR / "exec_commands.txt"
CONFIG_FILE = COMMANDS_DIR / "config_commands.txt"


def load_commands(file_path):
    """
    Load commands from text file
    - ignores empty lines
    - ignores comments starting with #
    """
    if not file_path.exists():
        return []

    with open(file_path) as f:
        return [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]


SHOW_COMMANDS = load_commands(SHOW_FILE)
EXEC_COMMANDS = load_commands(EXEC_FILE)
CONFIG_COMMANDS = load_commands(CONFIG_FILE)

testbed = loader.load("testbed.yaml")

start_time = time.time()


def run_on_device(device):
    try:
        device.connect(
            learn_hostname=False,
            log_stdout=False
        )

        # --- SHOW commands ---
        for cmd in SHOW_COMMANDS:
            output = device.execute(cmd)
            print(f"\n===== {device.name} | {cmd} =====\n{output}")

        # --- CONFIG commands (if any) ---
        if CONFIG_COMMANDS:
            device.configure(CONFIG_COMMANDS)

        # --- EXEC commands ---
        for cmd in EXEC_COMMANDS:
            device.execute(cmd)

    except Exception as e:
        print(f"[ERROR] {device.name}: {e}")

    finally:
        if device.connected:
            device.disconnect()


pcall(run_on_device, device=testbed.devices.values())

print(f"\nRuntime: {time.time() - start_time:.2f} seconds")

