#!/usr/bin/env python3
import argparse
import pathlib
import numpy as np
import pandas as pd


def resolve_repo_outdir(outdir_arg: str | None) -> pathlib.Path:
    if outdir_arg:
        return pathlib.Path(outdir_arg)
    return pathlib.Path(__file__).resolve().parents[1] / "data"


def read_lookup(path: pathlib.Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """
    File format (as produced by your GP script):
      - First row: meta, length N (size_lookup_table). Entries:
          [0]=N, [1]=minForce, [2]=maxForce, [3]=minVoltage, [4]=maxVoltage, rest zeros
      - Next N rows: Z (N x N) grid of 'cmd' values; axes are:
          rows: voltage grid (minVoltage..maxVoltage), columns: force grid (minForce..maxForce)
    Returns:
      voltages (N,), forces (N,), Z (N,N), meta dict
    """
    data = np.loadtxt(path, delimiter=",")
    meta = data[0, :]
    Z = data[1:, :]
    N = int(round(meta[0]))
    if Z.shape[0] != N or Z.shape[1] != N:
        # handle case where file has more columns than N (padding zeros in first row)
        Z = Z[:, :N]
    fmin, fmax = float(meta[1]), float(meta[2])
    vmin, vmax = float(meta[3]), float(meta[4])
    forces = np.linspace(fmin, fmax, N)
    voltages = np.linspace(vmin, vmax, N)
    return voltages, forces, Z, {"N": N, "fmin": fmin, "fmax": fmax, "vmin": vmin, "vmax": vmax}


def melt_grid(voltages: np.ndarray, forces: np.ndarray, Z: np.ndarray) -> pd.DataFrame:
    V, F = np.meshgrid(voltages, forces, indexing="ij")  # V and F are (N,N)
    df = pd.DataFrame({
        "voltage_V": V.ravel(),
        "force_N": F.ravel(),
        "cmd": Z.ravel(),
    })
    return df


def slice_voltage_curve(voltages: np.ndarray, forces: np.ndarray, Z: np.ndarray, target_voltage: float | None) -> tuple[float, np.ndarray, np.ndarray]:
    if target_voltage is None:
        # pick middle voltage
        idx = len(voltages) // 2
    else:
        idx = int(np.argmin(np.abs(voltages - target_voltage)))
    v_sel = float(voltages[idx])
    cmd_row = Z[idx, :]
    return v_sel, forces.copy(), cmd_row.copy()


def invert_cmd_vs_force_to_force_vs_cmd(cmd: np.ndarray, force: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Given cmd(f) which should be monotonic in this region, invert to f(cmd) by sorting and unique-ifying.
    Returns arrays (cmd_sorted, thrust_interp)
    """
    order = np.argsort(cmd)
    cmd_s = cmd[order]
    force_s = force[order]
    # Remove duplicate cmd entries by averaging their forces
    df = pd.DataFrame({"cmd": cmd_s, "thrust_N": force_s})
    df = df.groupby("cmd", as_index=False).mean(numeric_only=True)
    return df["cmd"].to_numpy(), df["thrust_N"].to_numpy()


def main():
    ap = argparse.ArgumentParser(description="Convert thrust lookup (grid CSV) to tidy CSVs and 1D thrust–throttle curve")
    ap.add_argument("--input", required=True, help="Path to thrust_map.csv (lookup grid with meta row)")
    ap.add_argument("--name", required=True, help="Name suffix for outputs")
    ap.add_argument("--outdir", default=None, help="Output directory (default: repo_root/data)")
    ap.add_argument("--voltage", type=float, default=None, help="Voltage slice for 1D curve (default: middle voltage)")
    ap.add_argument("--min-cmd", type=float, default=None, help="Min command for throttle normalization (optional)")
    ap.add_argument("--max-cmd", type=float, default=None, help="Max command for throttle normalization (optional)")
    args = ap.parse_args()

    inp = pathlib.Path(args.input)
    outdir = resolve_repo_outdir(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    voltages, forces, Z, meta = read_lookup(inp)

    # Long form for contour/surface plots
    df_long = melt_grid(voltages, forces, Z)
    out_long = outdir / f"thrust_lookup_long_{args.name}.csv"
    df_long.to_csv(out_long, index=False)
    print(f"[INFO] Wrote {out_long}")

    # 1D curve at selected voltage
    v_sel, f_vec, cmd_vec = slice_voltage_curve(voltages, forces, Z, args.voltage)
    cmd_1d, thrust_1d = invert_cmd_vs_force_to_force_vs_cmd(cmd_vec, f_vec)

    # Normalize throttle percent
    cmin = float(np.min(cmd_1d)) if args.min_cmd is None else args.min_cmd
    cmax = float(np.max(cmd_1d)) if args.max_cmd is None else args.max_cmd
    span = max(cmax - cmin, 1e-9)
    throttle_pct = (cmd_1d - cmin) / span * 100.0

    df_curve = pd.DataFrame({
        "cmd": cmd_1d,
        "throttle_pct": throttle_pct,
        "thrust_N": thrust_1d,
        "voltage_V": v_sel,
    })
    out_curve = outdir / f"thrustmap_throttle_from_lookup_{args.name}.csv"
    df_curve.to_csv(out_curve, index=False)
    print(f"[INFO] Wrote {out_curve} (slice at {v_sel:.2f} V)")


if __name__ == "__main__":
    main()
