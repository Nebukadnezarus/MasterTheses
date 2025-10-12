# Data pipeline

This folder contains small, reproducible scripts to turn raw logs into clean CSVs consumed by pgfplots in the thesis.

## Setup

Create a Python environment of your choice and install requirements:

- If you use a global env: `pip install -r scripts/requirements.txt`
- Or create a venv/conda env first (recommended).

## Scripts

- `process_thrust_map.py`
  - Input: raw log CSV with columns like `time_s, throttle_pct, rpm, thrust_N, voltage_V, current_A`.
  - Output: clean CSVs ready for LaTeX (in `data/`):
    - `thrustmap_throttle_<name>.csv` with `throttle_pct, thrust_N`
    - `thrustmap_rpm_<name>.csv` with `rpm, thrust_N`
    - Also writes optional power column if voltage/current are present.

- `process_efficiency.py`
  - Input: flight log CSV with `time_s, speed_mps, thrust_sum_N, voltage_V, current_A`.
  - Output: aggregated efficiency CSV in `data/` with `speed_mps, energy_Wh_per_km, power_W`.

## Conventions

- Use SI units in column names, e.g., `thrust_N`, `speed_mps`.
- Decimal point `.` in numeric fields.
- Keep file names short and descriptive; the LaTeX uses these paths directly.

## Example usage

```
python scripts/process_thrust_map.py --input logs/thrust_sweep_motorA.csv --name motorA
python scripts/process_efficiency.py --input logs/aida_run_2025-09-10.csv --name xwing_indi
```

Outputs go to `data/` by default. You can change with `--outdir`.
