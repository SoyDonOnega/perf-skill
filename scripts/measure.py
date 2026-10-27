#!/usr/bin/env python3
"""Measure a target with a platform profile (median of N runs) and compare two measurements.
Standard library only. Each profile needs its own tools (web: Node and Google Chrome).

Usage:
    python3 measure.py run [--profile web] <target> [profile options] --out FILE
    python3 measure.py bundle <dir> [--top 10]
    python3 measure.py compare <before.json> <after.json> [--threshold 0.05]

Profiles (scripts/profile_<name>.py):
    web      run <url> [--runs 3] [--preset mobile|desktop] [--dist DIR]: Lighthouse, full report
             of the median run kept as <FILE stem>.lh.json.

run      Writes FILE: the profile, metadata, the metrics of the median run, the spread over all
         runs, warnings, and the profile's findings. Every metric in "metrics" comes from one
         real run. Contract: references/core/metrics.md.
bundle   Prints raw and gzip bytes by type (js, css, font, image, other) and the largest
         files. Point it at the generated output (Vite: dist/assets, Next: .next/static),
         not at a folder that also holds files copied from public/.
compare  Prints a Markdown table (before, after, delta, verdict per metric) and an overall
         verdict. Both files must come from the same profile. Exit 0 = nothing regressed,
         exit 1 = at least one metric regressed, exit 2 = bad input.

A change counts only when it beats the relative threshold and the metric's absolute floor
(set per metric by the profile), and the ranges of the before and after runs do not overlap,
so lab noise does not read as a win or a loss.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import profiles  # noqa: E402
from profiles import DEFAULT_PROFILE, PROFILES, fail  # noqa: E402


def cmd_run(args, mod):
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    result = {"profile": args.profile, **mod.run(args)}
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(mod.summary(result), indent=2))
    for w in result["warnings"]:
        print(f"warning: {w}", file=sys.stderr)


def cmd_bundle(args):
    import profile_web as web
    print(json.dumps(web.bundle_sizes(args.dir, args.top), indent=2))


def fmt(value, unit, floor):
    if unit == "B":
        return f"{value / 1024:.1f} KB"
    if unit == "ms":
        return f"{value:.0f} ms"
    return f"{value:.3f}" if floor < 1 else f"{value:g}"


def load(path):
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        fail(str(e))
    data["metrics"] = data.get("metrics") or data.get("median")  # files from version 1 used "median"
    if not data["metrics"]:
        fail(f"no metrics in {path}")
    data.setdefault("profile", "web")  # files written before profiles existed are web
    return data


def run_range(data, key):
    """(min, max) of a metric over the runs, or None if it was not measured per run."""
    values = [r[key] for r in data.get("all_runs", []) if key in r]
    return (min(values), max(values)) if len(values) > 1 else None


def cmd_compare(args):
    before, after = load(args.before), load(args.after)
    if before["profile"] != after["profile"]:
        fail(f"profiles differ: {before['profile']} vs {after['profile']}")
    mod = profiles.load(before["profile"])
    if any(before.get(k) != after.get(k) for k in mod.IDENTITY):
        print(f"warning: {' or '.join(mod.IDENTITY)} differ between the two files", file=sys.stderr)
    for name, data in (("before", before), ("after", after)):
        for w in data.get("warnings", []):
            print(f"warning ({name}): {w}", file=sys.stderr)
    b, a = before["metrics"], after["metrics"]
    lines = ["| Metric | Before | After | Delta | Verdict |", "|---|---|---|---|---|"]
    improved, regressed = [], []
    for key, (label, unit, floor, higher_better) in mod.METRICS.items():
        if key not in b or key not in a:
            continue
        delta = a[key] - b[key]
        rel = abs(delta) / b[key] if b[key] else (1 if delta else 0)
        rb, ra = run_range(before, key), run_range(after, key)
        overlap = rb and ra and rb[0] <= ra[1] and ra[0] <= rb[1]
        if abs(delta) < floor or rel < args.threshold or overlap:
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
    # The profile decides the arguments of `run`, so read it before building that parser.
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--profile", default=DEFAULT_PROFILE)
    profile = pre.parse_known_args(sys.argv[2:])[0].profile if sys.argv[1:2] == ["run"] else DEFAULT_PROFILE
    mod = profiles.load(profile)

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--profile", choices=PROFILES, default=DEFAULT_PROFILE)
    mod.add_run_args(r)
    r.add_argument("--out", required=True)
    s = sub.add_parser("bundle")
    s.add_argument("dir")
    s.add_argument("--top", type=int, default=10)
    c = sub.add_parser("compare")
    c.add_argument("before")
    c.add_argument("after")
    c.add_argument("--threshold", type=float, default=0.05)
    args = p.parse_args()
    if args.cmd == "run":
        cmd_run(args, mod)
    elif args.cmd == "bundle":
        cmd_bundle(args)
    else:
        cmd_compare(args)


if __name__ == "__main__":
    main()
