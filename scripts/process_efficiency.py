#!/usr/bin/env python3
import argparse
import pathlib
import numpy as np
import pandas as pd


def energy_per_km(power_W, speed_mps):
    # Energy per distance [Wh/km] = (Power [W] / Speed [m/s]) * (1000 m / 3600 s)
    with np.errstate(divide='ignore', invalid='ignore'):
        e = (power_W / speed_mps) * (1000.0 / 3600.0)
    return e


def main():
    ap = argparse.ArgumentParser(description="Process efficiency logs into aggregated CSVs for LaTeX plots")
    ap.add_argument("--input", required=True, help="Path to raw flight log CSV")
    ap.add_argument("--name", required=True, help="Name suffix (e.g., xwing_indi)")
    ap.add_argument("--outdir", default="data", help="Output directory (default: data)")
    ap.add_argument("--bins", type=int, default=12, help="Number of speed bins for averaging (default: 12)")
    args = ap.parse_args()

    inp = pathlib.Path(args.input)
    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(inp)

    # Compute power if possible
    if {"voltage_V", "current_A"}.issubset(df.columns):
        df["power_W"] = df["voltage_V"] * df["current_A"]

    # Drop rows without speed or power
    need = [c for c in ["speed_mps", "power_W", "thrust_sum_N"] if c in df.columns]
    if "speed_mps" not in df.columns or ("power_W" not in df.columns and "thrust_sum_N" not in df.columns):
        raise ValueError("Input must contain speed_mps and either power_W or voltage_V,current_A; optionally thrust_sum_N")

    # If only thrust is provided, you can still compare thrust-per-speed. Keep both where available.
    # Bin by speed for smoother curves
    smin, smax = df["speed_mps"].quantile([0.05, 0.95])
    bins = np.linspace(smin, smax, args.bins + 1)
    df["speed_bin"] = pd.cut(df["speed_mps"], bins=bins, include_lowest=True)

    agg = {
        "speed_mps": "mean",
    }
    if "power_W" in df.columns:
        agg["power_W"] = "mean"
    if "thrust_sum_N" in df.columns:
        agg["thrust_sum_N"] = "mean"

    g = df.groupby("speed_bin").agg(agg).dropna().reset_index(drop=True)

    if "power_W" in g.columns:
        g["energy_Wh_per_km"] = energy_per_km(g["power_W"], g["speed_mps"])

    g.to_csv(outdir / f"efficiency_{args.name}.csv", index=False)


if __name__ == "__main__":
    main()
