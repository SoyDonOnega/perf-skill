"""Apple profile: a built .app on macOS or in an iOS Simulator, measured with ps, top and footprint.
macOS only (the simulator runs as macOS processes). No sudo, no Instruments.

Modes:
    launch  CPU time the process uses from launch until --settle seconds later, and its memory then.
    idle    launch, wait --settle seconds, then sample for --window seconds: CPU %, context
            switches per second (how often it wakes up), memory at the end. The resident cost of an app that stays open.
    size    bundle and main binary size. One run; nothing is launched.

The script launches the app itself and quits it after each run. It refuses to start while
another process with the same executable name runs (for example the user's installed copy):
quit that one first.
"""
import os
import plistlib
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

from profiles import fail

# key -> (label, unit, absolute floor, higher_is_better)
METRICS = {
    "launch_cpu_ms": ("CPU time until settled", "ms", 20, False),
    "settled_footprint_mb": ("Memory footprint, settled", "MB", 2, False),
    "idle_cpu_pct": ("Idle CPU", "%", 0.1, False),
    "idle_csw_s": ("Idle context switches", "/s", 1, False),
    "idle_footprint_mb": ("Memory footprint, after idle window", "MB", 2, False),
    "app_bytes": ("App bundle size", "B", 10240, False),
    "binary_bytes": ("Main binary size", "B", 4096, False),
}

IDENTITY = ("app", "platform", "device", "mode", "settle", "window")

PRIMARY = {"launch": "launch_cpu_ms", "idle": "idle_cpu_pct", "size": "app_bytes"}


def add_run_args(r):
    r.add_argument("app", help="path to the built .app")
    r.add_argument("--mode", choices=list(PRIMARY), default="idle")
    r.add_argument("--device", help="iOS Simulator UDID (required for an iOS app)")
    r.add_argument("--runs", type=int, default=3)
    r.add_argument("--settle", type=int, default=10, help="seconds after launch before reading")
    r.add_argument("--window", type=int, default=60, help="idle sampling window in seconds")


def sh(cmd, check=True):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        fail(f"{' '.join(cmd)} failed ({proc.returncode}): {proc.stderr.strip()[-400:]}", 3)
    return proc.stdout


def bundle_info(app):
    mac = os.path.join(app, "Contents", "Info.plist")
    ios = os.path.join(app, "Info.plist")
    path = mac if os.path.exists(mac) else ios
    if not os.path.exists(path):
        fail(f"no Info.plist in {app}: not an app bundle")
    with open(path, "rb") as f:
        info = plistlib.load(f)
    platform = "macos" if path == mac else "ios-sim"
    exe_dir = os.path.join(app, "Contents", "MacOS") if platform == "macos" else app
    return platform, info["CFBundleIdentifier"], os.path.join(exe_dir, info["CFBundleExecutable"])


def pids_of(executable, exact_path=False):
    """PIDs running this executable: by exact path, or by name (catches other installed copies)."""
    cmd = ["pgrep", "-f", "^" + re.escape(executable) + "$"] if exact_path else ["pgrep", "-x", os.path.basename(executable)]
    return [int(p) for p in sh(cmd, check=False).split()]


def cpu_ms(pid):
    """Cumulative CPU time of a process, from ps (format [[hh:]mm:]ss.cc)."""
    out = sh(["ps", "-o", "time=", "-p", str(pid)], check=False).strip()
    if not out:
        fail(f"process {pid} exited during the measurement (crash or quit)", 3)
    seconds = 0.0
    for part in out.split(":"):
        seconds = seconds * 60 + float(part)
    return seconds * 1000


def context_switches(pid):
    """Cumulative context switches of a process, from top: the proxy for how often it wakes up.
    (top's IDLEW only counts wakeups from package idle, so it depends on the rest of the machine.)"""
    out = sh(["top", "-l", "1", "-pid", str(pid), "-stats", "pid,csw"], check=False)
    rows = [line.split() for line in out.splitlines() if line.split()[:1] == [str(pid)]]
    if not rows:
        fail(f"process {pid} not found by top", 3)
    return int(re.sub(r"\D", "", rows[-1][1]) or 0)


def footprint_mb(pid):
    out = sh(["footprint", "-f", "bytes", str(pid)], check=False)
    m = re.search(r"Footprint:\s*(\d+) B", out)
    if not m:
        fail(f"footprint could not read process {pid}", 3)
    return int(m.group(1)) / (1024 * 1024)


def launch(platform, bundle_id, executable, app, device):
    if platform == "macos":
        sh(["open", "-n", "-g", app])
        for _ in range(100):
            pids = pids_of(executable, exact_path=True)
            if pids:
                return pids[0]
            time.sleep(0.1)
        fail(f"{app} did not start within 10 s", 3)
    out = sh(["xcrun", "simctl", "launch", "--terminate-running-process", device, bundle_id])
    return int(out.strip().rsplit(":", 1)[1])


def quit_app(platform, bundle_id, pid, device):
    if platform == "ios-sim":
        sh(["xcrun", "simctl", "terminate", device, bundle_id], check=False)
        return
    sh(["kill", "-TERM", str(pid)], check=False)
    for _ in range(50):
        if not sh(["ps", "-o", "pid=", "-p", str(pid)], check=False).strip():
            return
        time.sleep(0.1)
    sh(["kill", "-KILL", str(pid)], check=False)


def tree_bytes(root):
    total = 0
    for dirpath, _, files in os.walk(root):
        for name in files:
            path = os.path.join(dirpath, name)
            if not os.path.islink(path):
                total += os.path.getsize(path)
    return total


def one_run(args, platform, bundle_id, executable):
    pid = launch(platform, bundle_id, executable, args.app, args.device)
    try:
        time.sleep(args.settle)
        row = {"launch_cpu_ms": cpu_ms(pid), "settled_footprint_mb": footprint_mb(pid)}
        if args.mode == "idle":
            cpu0, csw0, t0 = cpu_ms(pid), context_switches(pid), time.monotonic()
            time.sleep(args.window)
            cpu1, csw1, elapsed = cpu_ms(pid), context_switches(pid), time.monotonic() - t0
            row["idle_cpu_pct"] = (cpu1 - cpu0) / (elapsed * 1000) * 100
            row["idle_csw_s"] = (csw1 - csw0) / elapsed
            row["idle_footprint_mb"] = footprint_mb(pid)
    finally:
        quit_app(platform, bundle_id, pid, args.device)
    return row


def run(args):
    args.app = os.path.abspath(args.app.rstrip("/"))
    platform, bundle_id, executable = bundle_info(args.app)
    if platform == "ios-sim" and not args.device and args.mode != "size":
        fail("an iOS app needs --device <simulator UDID>")
    warnings = []
    if args.mode == "size":
        rows = [{"app_bytes": tree_bytes(args.app), "binary_bytes": os.path.getsize(executable)}]
    else:
        if platform == "macos":
            running = pids_of(executable)
            if running:
                fail(f"{os.path.basename(executable)} is already running (pid {running}); quit it first", 2)
        else:
            sh(["xcrun", "simctl", "install", args.device, args.app])
        rows = []
        for i in range(args.runs):
            print(f"run {i + 1}/{args.runs} …", file=sys.stderr)
            rows.append(one_run(args, platform, bundle_id, executable))
            time.sleep(2)
    key = PRIMARY[args.mode]
    order = sorted(range(len(rows)), key=lambda i: rows[i][key])
    pick = order[(len(order) - 1) // 2]
    if platform == "ios-sim":
        warnings.append("iOS Simulator: runs on the Mac's CPU and memory; compare before/after only, "
                        "not as device numbers")
    spread = {k: [min(r[k] for r in rows), max(r[k] for r in rows)] for k in rows[0]}
    return {
        "app": args.app,
        "platform": platform,
        "device": args.device,
        "bundle_id": bundle_id,
        "mode": args.mode,
        "settle": args.settle if args.mode != "size" else None,
        "window": args.window if args.mode == "idle" else None,
        "runs": len(rows),
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "median_run": pick + 1,
        "metrics": dict(rows[pick]),
        "spread": spread,
        "warnings": warnings,
        "findings": [],
        "all_runs": rows,
    }


def summary(result):
    return {"mode": result["mode"], "metrics": result["metrics"], "warnings": result["warnings"]}
