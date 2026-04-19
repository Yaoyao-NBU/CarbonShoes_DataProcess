"""
C3D Extraction — Kistler Type 3 Force Plates (Plate-Local Output)
=================================================================
Reads C3D files with Kistler Type 3 (8-channel) force plates and exports:
  - Marker trajectories (mm)
  - Ground Reaction Forces in Kistler plate-local frame (N)
  - Centre of Pressure in Kistler plate-local frame (mm, from plate centre)
  - Free vertical moment Tz (N·mm)

Kistler plate-local coordinate system:
  X-axis: medio-lateral,          right     = positive
  Y-axis: anterior-posterior,     posterior = positive
  Z-axis: vertical (into plate),  downward  = positive
  Origin: plate centre for X/Y

Channels per platform (Type 3, 8-channel):
  ch0=fx12, ch1=fx34, ch2=fy14, ch3=fy23, ch4=fz1, ch5=fz2, ch6=fz3, ch7=fz4

FORCE_PLATFORM:ORIGIN interpretation:
  ORIGIN[0] = b   (sensor offset in local X / ML direction, mm)
  ORIGIN[1] = a   (sensor offset in local Y / walking direction, mm)
  ORIGIN[2] = az0 (top-plate offset, mm, typically negative)

Usage:
  python extract_kistler_local.py <data_folder> [output_folder]

  If output_folder is omitted, CSVs are written to <data_folder>/output_local/
"""

import os
import sys
import glob
import numpy as np
import pandas as pd
import ezc3d

FZ_THRESHOLD = 20.0   # N — COP/Tz set to NaN when |Fz| below this


# ── Kistler Type 3 formulae ──────────────────────────────────────────────────

def compute_kistler_type3(channels_8, a, b, az0):
    """
    Compute GRF, COP, and free moment from 8 raw Kistler channels.

    Parameters
    ----------
    channels_8 : ndarray (8, N)
        [fx12, fx34, fy14, fy23, fz1, fz2, fz3, fz4]
    a   : float — sensor offset in local-Y (AP/walking), mm
    b   : float — sensor offset in local-X (ML), mm
    az0 : float — top-plate offset, mm (negative)

    Returns
    -------
    dict: Fx, Fy, Fz (N), ax, ay (mm from plate centre), Tz (N·mm)
    """
    fx12, fx34, fy14, fy23, fz1, fz2, fz3, fz4 = channels_8

    Fx_raw = fx12 + fx34
    Fy_raw = fy14 + fy23
    Fz_raw = fz1 + fz2 + fz3 + fz4

    Mx = b * (fz1 + fz2 - fz3 - fz4)
    My = a * (-fz1 + fz2 + fz3 - fz4)
    Mz = b * (-fx12 + fx34) + a * (fy14 - fy23)

    Mxp = Mx + Fy_raw * az0
    Myp = My - Fx_raw * az0

    valid = np.abs(Fz_raw) >= FZ_THRESHOLD
    with np.errstate(invalid='ignore', divide='ignore'):
        ax = np.where(valid, -Myp / Fz_raw, np.nan)
        ay = np.where(valid,  Mxp / Fz_raw, np.nan)

    Tz_raw = Mz - Fy_raw * ax + Fx_raw * ay
    Tz = np.where(valid, -Tz_raw, np.nan)

    return dict(Fx=-Fx_raw, Fy=-Fy_raw, Fz=-Fz_raw, ax=ax, ay=ay, Tz=Tz)


# ── per-file extraction ──────────────────────────────────────────────────────

def extract_one(c3d_path, output_dir):
    trial = os.path.splitext(os.path.basename(c3d_path))[0]
    print(f"  Processing: {trial}")

    c = ezc3d.c3d(c3d_path)

    point_rate  = c['header']['points']['frame_rate']
    analog_rate = c['header']['analogs']['frame_rate']
    first_frame = c['header']['points']['first_frame']

    n_pt = c['data']['points'].shape[2]
    n_an = c['data']['analogs'].shape[2]

    t_pt = (np.arange(n_pt) + first_frame) / point_rate
    t_an = (np.arange(n_an) + first_frame) / analog_rate

    # ── Markers ───────────────────────────────────────────────────────────────
    pt     = c['data']['points']
    labels = c['parameters']['POINT']['LABELS']['value']

    cols = {'Time_s': t_pt}
    for mi, lbl in enumerate(labels):
        cols[f'{lbl}_X']        = pt[0, mi, :]
        cols[f'{lbl}_Y']        = pt[1, mi, :]
        cols[f'{lbl}_Z']        = pt[2, mi, :]
        cols[f'{lbl}_Residual'] = pt[3, mi, :]

    out_markers = os.path.join(output_dir, f'{trial}_markers.csv')
    pd.DataFrame(cols).to_csv(out_markers, index=False, float_format='%.6f')
    print(f"    -> {out_markers}  ({n_pt} frames, {len(labels)} markers)")

    # ── Force platforms ───────────────────────────────────────────────────────
    analogs   = c['data']['analogs'][0]
    fp_params = c['parameters']['FORCE_PLATFORM']
    n_plates  = int(fp_params['USED']['value'][0])
    channels  = fp_params['CHANNEL']['value']
    origin    = fp_params['ORIGIN']['value']

    grf_cols = {'Time_s': t_an}
    cop_cols = {'Time_s': t_an}
    tz_cols  = {'Time_s': t_an}

    for pi in range(n_plates):
        tag = f'FP{pi + 1}'

        ch_idx = channels[:, pi].astype(int) - 1
        ch8    = analogs[ch_idx, :]

        b   = float(origin[0, pi])
        a   = float(origin[1, pi])
        az0 = float(origin[2, pi])

        r = compute_kistler_type3(ch8, a, b, az0)

        grf_cols[f'{tag}_Fx'] = r['Fx']
        grf_cols[f'{tag}_Fy'] = r['Fy']
        grf_cols[f'{tag}_Fz'] = r['Fz']

        cop_cols[f'{tag}_ax'] = r['ax']
        cop_cols[f'{tag}_ay'] = r['ay']

        tz_cols[f'{tag}_Tz'] = r['Tz']

    out_grf = os.path.join(output_dir, f'{trial}_GRF.csv')
    out_cop = os.path.join(output_dir, f'{trial}_COP.csv')
    out_tz  = os.path.join(output_dir, f'{trial}_free_moments.csv')

    pd.DataFrame(grf_cols).to_csv(out_grf, index=False, float_format='%.6f')
    pd.DataFrame(cop_cols).to_csv(out_cop, index=False, float_format='%.6f')
    pd.DataFrame(tz_cols ).to_csv(out_tz,  index=False, float_format='%.6f')

    print(f"    -> GRF  (Fx=right+, Fy=posterior+, Fz=down+)")
    print(f"    -> COP  (plate-local, mm from centre)")
    print(f"    -> Tz   (N·mm)")
    print(f"       ({n_an} frames, {n_plates} platform(s), "
          f"a={a:.0f} b={b:.0f} az0={az0:.0f} mm)")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_kistler_local.py <data_folder> [output_folder]")
        print("       Processes all .c3d files in <data_folder>.")
        sys.exit(1)

    data_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(data_dir, 'output_local')
    os.makedirs(output_dir, exist_ok=True)

    c3d_files = sorted(glob.glob(os.path.join(data_dir, '*.c3d')))
    if not c3d_files:
        print(f"No .c3d files found in {data_dir}")
        return

    print(f"Found {len(c3d_files)} .c3d file(s) — output → {output_dir}\n")
    for path in c3d_files:
        try:
            extract_one(path, output_dir)
        except Exception as e:
            print(f"  ERROR: {path}: {e}")

    print("\nDone.")


if __name__ == '__main__':
    main()
