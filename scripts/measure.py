#!/usr/bin/env python3
"""Measure a page with Lighthouse (median of N runs) and compare two measurements.
Standard library only. Lighthouse runs through npx; it needs Node and Google Chrome.

Usage:
    python3 measure.py run <url> [--runs 3] [--preset mobile|desktop] [--dist DIR] --out FILE
    python3 measure.py bundle <dist-dir>
    python3 measure.py compare <before.json> <after.json> [--threshold 0.05]

run      Writes JSON: metadata + the median of each metric over the runs.
bundle   Prints raw and gzip bytes of the build output by type (js, css, font, image, other).
compare  Prints a Markdown table (before, after, delta, verdict per metric) and an overall
         verdict. Exit 0 = nothing regressed, exit 1 = at least one metric regressed,
         exit 2 = bad input.

A change counts only when it beats both the relative threshold and the metric's absolute
floor (below), so lab noise does not read as a win or a loss.
"""
import argparse
import gzip
import json
import os
import statistics
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

LIGHTHOUSE = os.environ.get("PERF_LIGHTHOUSE", "lighthouse@13.5.0")

# key -> (label, unit, absolute floor, higher_is_better)
METRICS = {
    "score": ("Performance score", "pts", 1, True),
    "fcp_ms": ("First Contentful Paint", "ms", 50, False),
    "lcp_ms": ("Largest Contentful Paint", "ms", 50, False),
    "tbt_ms": ("Total Blocking Time", "ms", 20, False),
    "cls": ("Cumulative Layout Shift", "", 0.01, False),
    "si_ms": ("Speed Index", "ms", 50, False),
    "bytes_total": ("Transfer size, total", "B", 1024, False),
    "bytes_js": ("Transfer size, JS", "B", 1024, False),
    "requests": ("Requests", "", 1, False),
    "dist_js_gzip": ("Build JS (gzip)", "B", 512, False),
    "dist_css_gzip": ("Build CSS (gzip)", "B", 256, False),
}

AUDITS = {
    "fcp_ms": "first-contentful-paint",
    "lcp_ms": "largest-contentful-paint",
    "tbt_ms": "total-blocking-time",
    "cls": "cumulative-layout-shift",
    "si_ms": "speed-index",
    "bytes_total": "total-byte-weight",
}

TYPES = {
    "js": {".js", ".mjs", ".cjs"},
    "css": {".css"},
    "font": {".woff", ".woff2", ".ttf", ".otf", ".eot"},
    "image": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".ico"},
}


def fail(msg, code=2):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def lighthouse_once(url, preset):
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "lh.json")
        cmd = ["npx", "-y", LIGHTHOUSE, url, "--output=json", f"--output-path={out}",
               "--only-categories=performance", "--quiet", "--chrome-flags=--headless=new"]
        if preset == "desktop":
            cmd.append("--preset=desktop")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0 or not os.path.exists(out):
            fail(f"lighthouse failed ({proc.returncode}): {proc.stderr.strip()[-800:]}", 3)
        with open(out) as f:
            return json.load(f)


def extract(report):
    audits = report["audits"]
    row = {"score": round((report["categories"]["performance"]["score"] or 0) * 100)}
    for key, audit in AUDITS.items():
        value = audits.get(audit, {}).get("numericValue")
        if value is not None:
            row[key] = value
    items = audits.get("network-requests", {}).get("details", {}).get("items", [])
    row["requests"] = len(items)
    row["bytes_js"] = sum(i.get("transferSize", 0) for i in items if i.get("resourceType") == "Script")
    return row, report.get("lighthouseVersion")


def bundle_sizes(root):
    if not os.path.isdir(root):
        fail(f"not a directory: {root}")
    sizes = {t: {"raw": 0, "gzip": 0, "files": 0} for t in list(TYPES) + ["other"]}
    for dirpath, _, files in os.walk(root):
        for name in files:
            if name.endswith(".map"):
                continue
            ext = os.path.splitext(name)[1].lower()
            kind = next((t for t, exts in TYPES.items() if ext in exts), "other")
            with open(os.path.join(dirpath, name), "rb") as f:
                data = f.read()
            sizes[kind]["raw"] += len(data)
            sizes[kind]["gzip"] += len(gzip.compress(data, 9))
            sizes[kind]["files"] += 1
    return sizes


def cmd_run(args):
    runs, version = [], None
    for i in range(args.runs):
        print(f"run {i + 1}/{args.runs} …", file=sys.stderr)
        row, version = extract(lighthouse_once(args.url, args.preset))
        runs.append(row)
    median = {k: statistics.median(r[k] for r in runs if k in r) for k in runs[0]}
    if args.dist:
        sizes = bundle_sizes(args.dist)
        median["dist_js_gzip"] = sizes["js"]["gzip"]
        median["dist_css_gzip"] = sizes["css"]["gzip"]
    result = {
        "url": args.url,
        "preset": args.preset,
        "runs": args.runs,
        "lighthouse": version,
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "median": median,
        "all_runs": runs,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(median, indent=2))


def cmd_bundle(args):
    print(json.dumps(bundle_sizes(args.dir), indent=2))


def fmt(value, unit, floor):
    if unit == "B":
        return f"{value / 1024:.1f} KB"
    if unit == "ms":
        return f"{value:.0f} ms"
    return f"{value:.3f}" if floor < 1 else f"{value:g}"


def cmd_compare(args):
    try:
        with open(args.before) as f:
            before = json.load(f)
        with open(args.after) as f:
            after = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        fail(str(e))
    if (before.get("url"), before.get("preset")) != (after.get("url"), after.get("preset")):
        print("warning: URL or preset differ between the two files", file=sys.stderr)
    b, a = before["median"], after["median"]
    lines = ["| Metric | Before | After | Delta | Verdict |", "|---|---|---|---|---|"]
    improved, regressed = [], []
    for key, (label, unit, floor, higher_better) in METRICS.items():
        if key not in b or key not in a:
            continue
        delta = a[key] - b[key]
        rel = abs(delta) / b[key] if b[key] else (1 if delta else 0)
        if abs(delta) < floor or rel < args.threshold:
            verdict = "same"
        elif (delta > 0) == higher_better:
            verdict = "better"
            improved.append(label)
        else:
            verdict = "worse"
            regressed.append(label)
        sign = "+" if delta > 0 else ""
        pct = f" ({sign}{delta / b[key] * 100:.1f}%)" if b[key] else ""
        lines.append(f"| {label} | {fmt(b[key], unit, floor)} | {fmt(a[key], unit, floor)} | "
                     f"{sign}{fmt(delta, unit, floor)}{pct} | {verdict} |")
    print("\n".join(lines))
    if regressed:
        overall = "REGRESSED: " + ", ".join(regressed)
    elif improved:
        overall = "IMPROVED: " + ", ".join(improved)
    else:
        overall = "NO CHANGE beyond noise"
    print(f"\nOverall: {overall}")
    sys.exit(1 if regressed else 0)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("url")
    r.add_argument("--runs", type=int, default=3)
    r.add_argument("--preset", choices=["mobile", "desktop"], default="mobile")
    r.add_argument("--dist", help="build output folder to size")
    r.add_argument("--out", required=True)
    s = sub.add_parser("bundle")
    s.add_argument("dir")
    c = sub.add_parser("compare")
    c.add_argument("before")
    c.add_argument("after")
    c.add_argument("--threshold", type=float, default=0.05)
    args = p.parse_args()
    {"run": cmd_run, "bundle": cmd_bundle, "compare": cmd_compare}[args.cmd](args)


if __name__ == "__main__":
    main()
