#!/usr/bin/env python3
import sys
import subprocess
import time
import signal
import argparse
import shlex

def run_command_and_measure(cmd):
    """Run a command to completion and measure execution time."""
    start = time.time()
    proc = subprocess.Popen(cmd)
    proc.wait()
    end = time.time()
    return end - start, proc.returncode

def run_with_sigint(setup_cmd, target_cmd, delay):
    """Run setup to completion, then run target and send SIGINT after delay."""
    print(f"Running setup: {' '.join(setup_cmd)}")
    setup_rc = subprocess.run(setup_cmd).returncode
    if setup_rc != 0:
        print(f"Setup failed with exit code {setup_rc}", file=sys.stderr)
        return None

    print(f"Starting target: {' '.join(target_cmd)}")
    target_proc = subprocess.Popen(target_cmd)
    time.sleep(delay)

    print(f"Sending SIGINT after {delay:.2f}s...")
    target_proc.send_signal(signal.SIGINT)

    try:
        target_proc.wait(timeout=30)
        return target_proc.returncode
    except subprocess.TimeoutExpired:
        target_proc.kill()
        print(f"Target process hung after SIGINT at delay {delay:.2f}s", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description="Test target command's SIGINT handling after setup.")
    parser.add_argument("--setup", required=True, help="Setup command (quoted)")
    parser.add_argument("--target", required=True, help="Target command to test (quoted)")
    args = parser.parse_args()

    setup_cmd = shlex.split(args.setup)
    target_cmd = shlex.split(args.target)

    print(f"\nMeasuring total runtime of target command...")
    total_time, rc = run_command_and_measure(target_cmd)
    print(f"Target completed in {total_time:.2f}s with exit code {rc}")

    print("\nBeginning signal interruption tests:")
    #step = max(0.1, total_time / 10)
    step = 0.1
    t = 0.0
    while t < total_time + step:
        print(f"\nCycle with SIGINT after {t:.2f}s")
        rc = run_with_sigint(setup_cmd, target_cmd, t)
        if rc is None:
            print("Target did not exit cleanly (hung).")
        else:
            print(f"Target exited with code {rc}")
        t += step

if __name__ == "__main__":
    main()
