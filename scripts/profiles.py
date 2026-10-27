"""Profile registry. One measurement module per platform profile: profile_<name>.py.

Each profile module exposes:
    METRICS            key -> (label, unit, absolute floor, higher_is_better); what compare reads
    IDENTITY           result keys that must match for a fair compare (target and settings)
    add_run_args(p)    adds the positional target and the profile's options to the `run` parser
    run(args)          measures and returns the result dict (see references/core/metrics.md)
    summary(result)    the short dict printed to stdout after `run`
"""
import importlib
import sys

PROFILES = ("web", "apple")
DEFAULT_PROFILE = "web"


def fail(msg, code=2):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def load(profile):
    if profile not in PROFILES:
        fail(f"unknown profile '{profile}' (available: {', '.join(PROFILES)})")
    return importlib.import_module(f"profile_{profile}")
