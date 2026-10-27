# Measurement contract

Every profile writes the same kind of file, so `compare` and the loop work the same on every platform.

## Result file (`measure.py run`)

| Key | Required | Meaning |
|---|---|---|
| `profile` | yes | Profile that wrote the file (`web`, …). Files without it are read as `web`. |
| identity keys | yes | The target and the settings that must match for a fair compare (web: `url`, `preset`; apple: `app`, `platform`, `device`, `mode`, `settle`, `window`). Listed in the profile module's `IDENTITY`. |
| `runs` | yes | Number of runs. |
| `measured_at` | yes | UTC timestamp. |
| `median_run` | yes | 1-based index of the run that `metrics` comes from. Every metric comes from one real run, never a mix. |
| `metrics` | yes | Metric key → value of the median run, plus single-shot values (build size) that do not vary per run. |
| `spread` | yes | Metric key → `[min, max]` over the runs. |
| `all_runs` | yes | One metrics dict per run. `compare` reads it to check whether the before and after ranges overlap. |
| `warnings` | yes | Anything that makes a number less reliable. Read before trusting `metrics`. |
| `findings` | yes | The tool's failing checks with their top items (may be empty). |
| tool version and extras | no | For example web: `lighthouse`, `lcp_element`, `report`; apple: `bundle_id`. |

## Metric registry (profile module `METRICS`)

`key -> (label, unit, absolute floor, higher_is_better)`. Units `compare` formats: `ms`, `B` (bytes), `MB`, `%`, `/s`, `pts`, `""` (count or ratio). A metric moves only when all three hold: the change beats `--threshold` (relative, default 5 %), it beats the absolute floor, and the before and after run ranges do not overlap.

## Adding a profile

1. `scripts/profile_<profile>.py` with `METRICS`, `IDENTITY`, `add_run_args`, `run`, `summary` (see `scripts/profiles.py`).
2. Add the name to `PROFILES`.
3. `references/<profile>/profile.md` (detect, build, baseline, areas, plan columns, profile rules) and one reference per area.
4. Check: an A/A measurement of an unchanged build reports `NO CHANGE`, and one deliberate change shows up in `compare`.
