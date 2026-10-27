"""Web profile: Lighthouse (median of N runs) plus optional build size.
Lighthouse runs through npx; it needs Node and Google Chrome.

The median run is the run with the median score (ties: median LCP), so every metric in
"metrics" comes from one real run. The full report of the median run is kept next to the
output file as <FILE stem>.lh.json.
"""
import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

from profiles import fail

LIGHTHOUSE = os.environ.get("PERF_LIGHTHOUSE", "lighthouse@13.5.0")

# key -> (label, unit, absolute floor, higher_is_better)
METRICS = {
    "score": ("Performance score", "pts", 1, True),
    "fcp_ms": ("First Contentful Paint", "ms", 50, False),
    "lcp_ms": ("Largest Contentful Paint (simulated)", "ms", 50, False),
    "lcp_observed_ms": ("Largest Contentful Paint (observed)", "ms", 50, False),
    "tbt_ms": ("Total Blocking Time", "ms", 20, False),
    "cls": ("Cumulative Layout Shift", "", 0.01, False),
    "si_ms": ("Speed Index", "ms", 50, False),
    "bytes_total": ("Transfer size, total", "B", 1024, False),
    "bytes_js": ("Transfer size, JS", "B", 1024, False),
    "requests": ("Requests", "", 1, False),
    "dist_js_gzip": ("Build JS (gzip)", "B", 512, False),
    "dist_css_gzip": ("Build CSS (gzip)", "B", 256, False),
}

IDENTITY = ("url", "preset")

AUDITS = {
    "fcp_ms": "first-contentful-paint",
    "lcp_ms": "largest-contentful-paint",
    "tbt_ms": "total-blocking-time",
    "cls": "cumulative-layout-shift",
    "si_ms": "speed-index",
    "bytes_total": "total-byte-weight",
}

# Audits that are metrics or raw data, not findings.
NOT_FINDINGS = set(AUDITS.values()) | {
    "interactive", "max-potential-fid", "metrics", "network-requests", "screenshot-thumbnails",
    "final-screenshot", "main-thread-tasks", "diagnostics", "script-treemap-data",
    "resource-summary", "network-rtt", "network-server-latency", "user-timings",
}

TYPES = {
    "js": {".js", ".mjs", ".cjs"},
    "css": {".css"},
    "font": {".woff", ".woff2", ".ttf", ".otf", ".eot"},
    "image": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".ico"},
}

# Simulated LCP this many times above observed LCP is flagged as suspect.
LCP_SUSPECT_RATIO = 3


def add_run_args(r):
    r.add_argument("url")
    r.add_argument("--runs", type=int, default=3)
    r.add_argument("--preset", choices=["mobile", "desktop"], default="mobile")
    r.add_argument("--dist", help="generated build output folder to size (e.g. dist/assets)")


def lighthouse_once(url, preset, out):
    cmd = ["npx", "-y", LIGHTHOUSE, url, "--output=json", f"--output-path={out}",
           "--only-categories=performance", "--quiet", "--chrome-flags=--headless=new"]
    if preset == "desktop":
        cmd.append("--preset=desktop")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not os.path.exists(out):
        fail(f"lighthouse failed ({proc.returncode}): {proc.stderr.strip()[-800:]}", 3)
    with open(out) as f:
        report = json.load(f)
    errors = [line.strip() for line in proc.stderr.splitlines() if "Error" in line]
    return report, errors


def extract(report):
    audits = report["audits"]
    row = {"score": round((report["categories"]["performance"]["score"] or 0) * 100)}
    for key, audit in AUDITS.items():
        value = audits.get(audit, {}).get("numericValue")
        if value is not None:
            row[key] = value
    observed = (audits.get("metrics", {}).get("details", {}).get("items") or [{}])[0]
    if "observedLargestContentfulPaint" in observed:
        row["lcp_observed_ms"] = observed["observedLargestContentfulPaint"]
    items = audits.get("network-requests", {}).get("details", {}).get("items", [])
    row["requests"] = len(items)
    row["bytes_js"] = sum(i.get("transferSize", 0) for i in items if i.get("resourceType") == "Script")
    return row


def lcp_element(report):
    details = report["audits"].get("lcp-breakdown-insight", {}).get("details", {})
    for part in details.get("items", []):
        if part.get("type") == "node":
            return part.get("selector") or part.get("snippet")
    return None


def item_summary(item):
    keep = {}
    for key in ("url", "wastedBytes", "wastedMs", "totalBytes", "cacheLifetimeMs"):
        if key in item:
            keep[key] = item[key]
    node = item.get("node")
    if isinstance(node, dict):
        keep["selector"] = node.get("selector")
    return keep


def findings(report, top=5):
    out = []
    for audit_id, audit in report["audits"].items():
        score = audit.get("score")
        if audit_id in NOT_FINDINGS or score is None or score >= 1:
            continue
        items = [i for i in audit.get("details", {}).get("items", []) if isinstance(i, dict)]
        items = [s for s in (item_summary(i) for i in items) if s]
        out.append({
            "id": audit_id,
            "title": audit.get("title"),
            "score": score,
            "display": audit.get("displayValue"),
            "savings": {k: v for k, v in (audit.get("metricSavings") or {}).items() if v},
            "items": items[:top],
        })
    out.sort(key=lambda f: f["score"])
    return out


def median_run(rows):
    """Index of the run with the median score; ties broken by median LCP."""
    order = sorted(range(len(rows)), key=lambda i: (rows[i]["score"], -rows[i].get("lcp_ms", 0)))
    return order[(len(order) - 1) // 2]


def bundle_sizes(root, top=10):
    if not os.path.isdir(root):
        fail(f"not a directory: {root}")
    sizes = {t: {"raw": 0, "gzip": 0, "files": 0} for t in list(TYPES) + ["other"]}
    files_seen = []
    for dirpath, _, files in os.walk(root):
        for name in files:
            if name.endswith(".map"):
                continue
            path = os.path.join(dirpath, name)
            ext = os.path.splitext(name)[1].lower()
            kind = next((t for t, exts in TYPES.items() if ext in exts), "other")
            with open(path, "rb") as f:
                data = f.read()
            gz = len(gzip.compress(data, 9))
            sizes[kind]["raw"] += len(data)
            sizes[kind]["gzip"] += gz
            sizes[kind]["files"] += 1
            files_seen.append({"file": os.path.relpath(path, root), "raw": len(data), "gzip": gz})
    files_seen.sort(key=lambda f: f["raw"], reverse=True)
    return {"by_type": sizes, "largest": files_seen[:top]}


def run(args):
    rows, warnings = [], []
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for i in range(args.runs):
            print(f"run {i + 1}/{args.runs} …", file=sys.stderr)
            path = os.path.join(tmp, f"lh-{i}.json")
            report, errors = lighthouse_once(args.url, args.preset, path)
            rows.append(extract(report))
            warnings += [f"run {i + 1}: {e}" for e in errors]
            warnings += [f"run {i + 1}: {w}" for w in report.get("runWarnings", [])]
            paths.append(path)
        pick = median_run(rows)
        report_path = os.path.splitext(os.path.abspath(args.out))[0] + ".lh.json"
        shutil.copyfile(paths[pick], report_path)
        with open(report_path) as f:
            report = json.load(f)
    metrics = dict(rows[pick])
    sim, obs = metrics.get("lcp_ms"), metrics.get("lcp_observed_ms")
    if sim and obs and sim > LCP_SUSPECT_RATIO * obs:
        warnings.append(f"simulated LCP ({sim:.0f} ms) is over {LCP_SUSPECT_RATIO}x observed LCP "
                        f"({obs:.0f} ms): the simulation may be unreliable; check the LCP element")
    if args.dist:
        sizes = bundle_sizes(args.dist)["by_type"]
        metrics["dist_js_gzip"] = sizes["js"]["gzip"]
        metrics["dist_css_gzip"] = sizes["css"]["gzip"]
    spread = {k: [min(r[k] for r in rows if k in r), max(r[k] for r in rows if k in r)] for k in rows[0]}
    return {
        "url": args.url,
        "preset": args.preset,
        "runs": args.runs,
        "lighthouse": report.get("lighthouseVersion"),
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "median_run": pick + 1,
        "metrics": metrics,
        "spread": spread,
        "lcp_element": lcp_element(report),
        "warnings": warnings,
        "report": os.path.basename(report_path),
        "findings": findings(report),
        "all_runs": rows,
    }


def summary(result):
    return {"metrics": result["metrics"], "lcp_element": result["lcp_element"],
            "warnings": result["warnings"], "findings": len(result["findings"])}
