"""
C3D Extraction — Kistler Type 3 Force Plates (Lab Global Output)
================================================================
Reads C3D files with Kistler Type 3 (8-channel) force plates and exports:
  - Marker trajectories (mm, as stored in C3D)
  - Ground Reaction Forces in lab global frame (N)
  - Centre of Pressure in lab global frame (m, from CORNERS origin)
  - Free vertical moment Tz about Z-up (N·mm)

Lab global coordinate system:
  X = forward  (along 900 mm long side of plate),  positive = anterior
  Y = left     (along 600 mm short side of plate), positive = left
  Z = upward,                                      positive = up
  Origin = plate corner (from FORCE_PLATFORM:CORNERS)

Kistler plate-local → Global axis mapping:
  Kistler Y (posterior+, a, 900 mm) → Global −X
  Kistler X (right+,     b, 600 mm) → Global −Y
  Kistler Z (down+)                 → Global −Z

GRF is the ground reaction force (from ground ON the person):
  GRF_Fx = Kistler Fy (double negation: reaction + axis flip cancel)
  GRF_Fy = Kistler Fx
  GRF_Fz = Kistler Fz

COP conversion:
  COP_X = (plate_centre_X − Kistler_ay) / 1000  (m, forward from corner)
  COP_Y = (plate_centre_Y − Kistler_ax) / 1000  (m, left from corner)

Channels per platform (Type 3, 8-channel):
  ch0=fx12, ch1=fx34, ch2=fy14, ch3=fy23, ch4=fz1, ch5=fz2, ch6=fz3, ch7=fz4

FORCE_PLATFORM:ORIGIN interpretation:
  ORIGIN[0] = b   (sensor offset in local X / ML direction, mm)
  ORIGIN[1] = a   (sensor offset in local Y / walking direction, mm)
  ORIGIN[2] = az0 (top-plate offset, mm, typically negative)

Usage:
  python extract_kistler_global.py <data_folder> [output_folder]

  If output_folder is omitted, CSVs are written to <data_folder>/output_global/
"""

import os
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
    dict: Fx, Fy, Fz (N) in Kistler convention,
          ax, ay (mm from plate centre), Tz (N·mm)
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
    corners   = np.array(fp_params['CORNERS']['value'])  # (3, 4, n_plates)

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

        # Plate centre from CORNERS (mm)
        plate_cx = np.mean(corners[0, :, pi])  # along lab X (forward)
        plate_cy = np.mean(corners[1, :, pi])  # along lab Y (left)

        # COP: plate-local → lab global (m)
        cop_x_m = (plate_cx - r['ay']) / 1000.0   # forward
        cop_y_m = (plate_cy - r['ax']) / 1000.0   # left

        # GRF in lab global (N): reaction force, axes swapped
        grf_cols[f'{tag}_Fx'] = r['Fy']    # forward+
        grf_cols[f'{tag}_Fy'] = r['Fx']    # left+
        grf_cols[f'{tag}_Fz'] = r['Fz']    # upward+

        # COP in lab global (m)
        cop_cols[f'{tag}_COFP_X'] = cop_x_m
        cop_cols[f'{tag}_COFP_Y'] = cop_y_m

        # Free moment: Z down→up → negate
        tz_cols[f'{tag}_Tz'] = -r['Tz']

        print(f"    {tag}: plate centre = ({plate_cx:.0f}, {plate_cy:.0f}) mm")

    out_grf = os.path.join(output_dir, f'{trial}_GRF.csv')
    out_cop = os.path.join(output_dir, f'{trial}_COP.csv')
    out_tz  = os.path.join(output_dir, f'{trial}_free_moments.csv')

    pd.DataFrame(grf_cols).to_csv(out_grf, index=False, float_format='%.6f')
    pd.DataFrame(cop_cols).to_csv(out_cop, index=False, float_format='%.6f')
    pd.DataFrame(tz_cols ).to_csv(out_tz,  index=False, float_format='%.6f')

    print(f"    -> GRF  (Fx=forward+, Fy=left+, Fz=up+)")
    print(f"    -> COP  (lab global, metres from corner)")
    print(f"    -> Tz   (about Z-up, N·mm)")
    print(f"       ({n_an} frames, {n_plates} platform(s), "
          f"a={a:.0f} b={b:.0f} az0={az0:.0f} mm)")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    data_dir = r"E:\Python_Learn\CarbonShoes_DataProcess\C3D_Data_Process\kistler_c3d_extractor"
    output_input = r"E:\Python_Learn\CarbonShoes_DataProcess\C3D_Data_Process\kistler_c3d_extractor"
    output_dir = output_input if output_input else os.path.join(data_dir, 'output_global')
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
