#!/usr/bin/env python3
import argparse
import pathlib
import sys
from typing import Optional, Tuple
import pandas as pd


def resolve_repo_outdir(outdir_arg: Optional[str]) -> pathlib.Path:
    if outdir_arg:
        return pathlib.Path(outdir_arg)
    # Default to repo root data/
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    return repo_root / "data"


def pick_column(df: pd.DataFrame, aliases: Tuple[str, ...]) -> Optional[str]:
    for a in aliases:
        if a in df.columns:
            return a
    return None


def ensure_thrust_newton(df: pd.DataFrame) -> Tuple[pd.DataFrame, Optional[str]]:
    # Try thrust in Newtons
    thrust_col = pick_column(df, ("thrust_N", "thrust", "force_N"))
    if thrust_col:
        if thrust_col != "thrust_N":
            df = df.rename(columns={thrust_col: "thrust_N"})
        return df, "thrust_N"
    # Try grams/kgf
    g_col = pick_column(df, ("thrust_g", "force_g"))
    if g_col:
        df["thrust_N"] = df[g_col].astype(float) * 9.80665e-3
        return df, "thrust_N"
    kgf_col = pick_column(df, ("thrust_kgf", "force_kgf"))
    if kgf_col:
        df["thrust_N"] = df[kgf_col].astype(float) * 9.80665
        return df, "thrust_N"
    return df, None


def add_power_if_possible(df: pd.DataFrame) -> pd.DataFrame:
    v = pick_column(df, ("voltage_V", "voltage", "V", "battery_V"))
    i = pick_column(df, ("current_A", "current", "I"))
    if v and i:
        df["power_W"] = df[v].astype(float) * df[i].astype(float)
    return df


def main():
    ap = argparse.ArgumentParser(description="Process thrust map logs into LaTeX-friendly CSVs")
    ap.add_argument("--input", required=True, help="Path to raw log CSV")
    ap.add_argument("--name", required=True, help="Name suffix (e.g., motorA)")
    ap.add_argument("--outdir", default=None, help="Output directory (default: repo_root/data)")
    args = ap.parse_args()

    inp = pathlib.Path(args.input)
    outdir = resolve_repo_outdir(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(inp)

    # Normalize thrust to Newtons
    df, thrust_col = ensure_thrust_newton(df)
    # Optional power computation
    df = add_power_if_possible(df)

    # Identify throttle and rpm columns
    throttle_col = pick_column(df, ("throttle_pct", "throttle_percent", "throttle"))
    rpm_col = pick_column(df, ("rpm", "motor_rpm"))

    wrote_any = False

    # Throttle mapping (if fields exist)
    if throttle_col and thrust_col:
        throttle = df[[throttle_col, thrust_col]].dropna()
        throttle = (
            throttle.groupby(throttle_col, as_index=False)
            .mean(numeric_only=True)
            .sort_values(throttle_col)
        )
        out_throttle = outdir / f"thrustmap_throttle_{args.name}.csv"
        throttle.rename(columns={throttle_col: "throttle_pct", thrust_col: "thrust_N"}).to_csv(out_throttle, index=False)
        print(f"[INFO] Wrote {out_throttle}")
        wrote_any = True
    else:
        print("[WARN] Skipping throttle→thrust: missing columns (need throttle and thrust)")

    # RPM mapping (if fields exist)
    if rpm_col and thrust_col:
        rpm = df[[rpm_col, thrust_col]].dropna()
        rpm = (
            rpm.groupby(rpm_col, as_index=False)
            .mean(numeric_only=True)
            .sort_values(rpm_col)
        )
        out_rpm = outdir / f"thrustmap_rpm_{args.name}.csv"
        rpm.rename(columns={rpm_col: "rpm", thrust_col: "thrust_N"}).to_csv(out_rpm, index=False)
        print(f"[INFO] Wrote {out_rpm}")
        wrote_any = True
    else:
        print("[WARN] Skipping rpm→thrust: missing columns (need rpm and thrust)")

    # Save a combined clean file for tables/plots
    keep_cols = [c for c in ["time_s", throttle_col, rpm_col, thrust_col, "voltage_V", "current_A", "power_W"] if c in df.columns or c in (thrust_col, throttle_col, rpm_col)]
    keep_cols = [c for c in keep_cols if c is not None]
    if keep_cols:
        out_clean = outdir / f"thrustmap_clean_{args.name}.csv"
        df[keep_cols].to_csv(out_clean, index=False)
        print(f"[INFO] Wrote {out_clean}")
        wrote_any = True

    if not wrote_any:
        print("[ERROR] No outputs were generated. Check your input column names.")
        print("        Expected some of: throttle_pct/throttle, rpm, thrust_N/thrust (or thrust_g/thrust_kgf)")
        sys.exit(1)


if __name__ == "__main__":
    main()
