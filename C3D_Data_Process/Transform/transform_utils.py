"""
Transform Utilities for C3D → OpenSim Conversion
=================================================
Provides coordinate rotation, force computation, filtering, resampling,
stance detection, and .trc / .mot file I/O functions.

Coordinate Systems:
  Kistler plate-local:  X=right+,    Y=posterior+, Z=down+
  Lab global:           X=forward+,  Y=left+,      Z=up+
  OpenSim:              X=forward+,  Y=up+,        Z=right+
"""

import os
import numpy as np
from math import gcd
from scipy.signal import butter, filtfilt, resample_poly


# ═══════════════════════════════════════════════════════════════════════════════
#  Rotation Matrices
# ═══════════════════════════════════════════════════════════════════════════════

def rotation_matrix(axis, angle_deg):
    """
    Generate a 3×3 rotation matrix (right-hand rule).

    Parameters
    ----------
    axis : str — 'X', 'Y', or 'Z'
    angle_deg : float — rotation angle in degrees

    Returns
    -------
    R : ndarray (3, 3)
    """
    theta = np.radians(angle_deg)
    c, s = np.cos(theta), np.sin(theta)

    if axis.upper() == 'X':
        return np.array([[1, 0,  0],
                         [0, c, -s],
                         [0, s,  c]])
    elif axis.upper() == 'Y':
        return np.array([[ c, 0, s],
                         [ 0, 1, 0],
                         [-s, 0, c]])
    elif axis.upper() == 'Z':
        return np.array([[c, -s, 0],
                         [s,  c, 0],
                         [0,  0, 1]])
    else:
        raise ValueError(f"Invalid axis '{axis}'. Use 'X', 'Y', or 'Z'.")


def chain_rotations(*rotations):
    """
    Chain multiple rotations.  e.g. chain_rotations(('X', -90), ('Y', 90))

    Parameters
    ----------
    *rotations : tuples of (axis, angle_deg)

    Returns
    -------
    R : ndarray (3, 3) — combined rotation matrix (applied left-to-right)
    """
    R = np.eye(3)
    for axis, angle in rotations:
        R = rotation_matrix(axis, angle) @ R
    return R


def apply_rotation(data_3xN, R):
    """
    Apply a 3×3 rotation matrix to (3, N) data.

    Parameters
    ----------
    data_3xN : ndarray (3, N)
    R : ndarray (3, 3)

    Returns
    -------
    rotated : ndarray (3, N)
    """
    return R @ data_3xN


# ═══════════════════════════════════════════════════════════════════════════════
#  Kistler Type 3 → Type 2  Force-Plate Computation
# ═══════════════════════════════════════════════════════════════════════════════

FZ_THRESHOLD = 20.0   # N — COP / Tz set to 0 when |Fz| below this


def compute_kistler_type2(channels_8, a, b, az0):
    """
    Compute Type 2 force-plate data from 8-channel Kistler Type 3 raw data.

    Parameters
    ----------
    channels_8 : ndarray (8, N)
        [fx12, fx34, fy14, fy23, fz1, fz2, fz3, fz4]
    a   : float — sensor offset in local-Y (AP / walking), mm
    b   : float — sensor offset in local-X (ML), mm
    az0 : float — top-plate offset, mm (typically negative)

    Returns
    -------
    dict  Fx, Fy, Fz  (N, ground reaction),
          ax, ay      (mm, COP from plate centre),
          Tz          (N·mm, free vertical moment)
    """
    fx12, fx34, fy14, fy23, fz1, fz2, fz3, fz4 = channels_8

    Fx_raw = fx12 + fx34
    Fy_raw = fy14 + fy23
    Fz_raw = fz1 + fz2 + fz3 + fz4

    Mx = b * (fz1 + fz2 - fz3 - fz4)
    My = a * (-fz1 + fz2 + fz3 - fz4)
    Mz = b * (-fx12 + fx34) + a * (fy14 - fy23)

    # Transfer moments to plate surface
    Mxp = Mx + Fy_raw * az0
    Myp = My - Fx_raw * az0

    # COP (valid only when |Fz| ≥ threshold)
    valid = np.abs(Fz_raw) >= FZ_THRESHOLD
    with np.errstate(invalid='ignore', divide='ignore'):
        ax = np.where(valid, -Myp / Fz_raw, 0.0)
        ay = np.where(valid,  Mxp / Fz_raw, 0.0)

    # Free vertical moment
    Tz_raw = Mz - Fy_raw * ax + Fx_raw * ay
    Tz = np.where(valid, -Tz_raw, 0.0)

    # Negate to get ground reaction force (from ground ON the person)
    return dict(Fx=-Fx_raw, Fy=-Fy_raw, Fz=-Fz_raw, ax=ax, ay=ay, Tz=Tz)


# ═══════════════════════════════════════════════════════════════════════════════
#  Coordinate Transforms
# ═══════════════════════════════════════════════════════════════════════════════

def plate_local_to_lab(type2, corners):
    """
    Convert Type 2 force data from Kistler plate-local → lab global.

    Kistler local:  X=right+,     Y=posterior+,  Z=down+
    Lab global:     X=forward+,   Y=left+,       Z=up+

    Mapping (ground reaction, double negation on axis flip):
        GRF_Lab_Fx =  type2['Fy']         (forward)
        GRF_Lab_Fy =  type2['Fx']         (left)
        GRF_Lab_Fz =  type2['Fz']         (up)
        COP_Lab_X  = plate_cx − ay        (forward, mm)
        COP_Lab_Y  = plate_cy − ax        (left, mm)
        COP_Lab_Z  = 0                    (ground level)
        Tz_lab     = −Tz_kistler          (about Z-up)

    Parameters
    ----------
    type2 : dict — output of compute_kistler_type2()
    corners : ndarray (3, 4) — FORCE_PLATFORM:CORNERS for this plate

    Returns
    -------
    dict  Fx, Fy, Fz (N),  COPx, COPy, COPz (mm),  Tz (N·mm)
    """
    plate_cx = np.mean(corners[0, :])   # lab X (forward)
    plate_cy = np.mean(corners[1, :])   # lab Y (left)

    # Forces — ground reaction in lab global
    Fx_lab = type2['Fy']    # forward
    Fy_lab = type2['Fx']    # left
    Fz_lab = type2['Fz']    # up

    # COP in lab global (mm)
    COPx_lab = plate_cx - type2['ay']    # forward
    COPy_lab = plate_cy - type2['ax']    # left
    COPz_lab = np.zeros_like(COPx_lab)   # ground level

    # Free moment: Kistler Z is down, lab Z is up → negate
    Tz_lab = -type2['Tz']

    return dict(Fx=Fx_lab, Fy=Fy_lab, Fz=Fz_lab,
                COPx=COPx_lab, COPy=COPy_lab, COPz=COPz_lab,
                Tz=Tz_lab)


def lab_to_opensim_force(data_lab):
    """
    Convert force data from lab global → OpenSim (Y-up).

    Lab:     X=forward, Y=left,  Z=up
    OpenSim: X=forward, Y=up,    Z=right

    Mapping:  X_os = X_lab,  Y_os = Z_lab,  Z_os = −Y_lab

    Parameters
    ----------
    data_lab : dict — Fx, Fy, Fz, COPx, COPy, COPz, Tz  (lab global)

    Returns
    -------
    dict — same keys, values in OpenSim coordinate system
    """
    return dict(
        Fx  =  data_lab['Fx'],       # forward
        Fy  =  data_lab['Fz'],       # up   (lab Z → OS Y)
        Fz  = -data_lab['Fy'],       # right (lab −Y → OS Z)
        COPx =  data_lab['COPx'],    # forward
        COPy =  data_lab['COPz'],    # up = 0  (ground)
        COPz = -data_lab['COPy'],    # right
        Tz   =  data_lab['Tz'],      # free vertical moment (stays about vert axis)
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Filtering & Resampling
# ═══════════════════════════════════════════════════════════════════════════════

def butter_lowpass_filter(data, cutoff, fs, order=4):
    """
    4th-order Butterworth low-pass filter (zero-phase via filtfilt).

    Parameters
    ----------
    data   : ndarray (N,)
    cutoff : float — cutoff frequency (Hz)
    fs     : float — sampling frequency (Hz)
    order  : int   — filter order (default 4)

    Returns
    -------
    filtered : ndarray (N,)
    """
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, data)


def resample_to_target_rate(data_1d, src_rate, tgt_rate):
    """
    Resample a 1-D signal from src_rate to tgt_rate (polyphase).

    Parameters
    ----------
    data_1d  : ndarray (N,)
    src_rate : float — source sampling rate (Hz)
    tgt_rate : float — target sampling rate (Hz)

    Returns
    -------
    resampled : ndarray (M,)
    """
    up   = int(tgt_rate)
    down = int(src_rate)
    g    = gcd(up, down)
    up  //= g
    down //= g
    return resample_poly(data_1d, up, down)


# ═══════════════════════════════════════════════════════════════════════════════
#  Stance Phase Detection
# ═══════════════════════════════════════════════════════════════════════════════

def detect_stance_phase(vertical_force, threshold=30.0, pad_frames=25):
    """
    Detect stance phase from vertical ground reaction force.

    Parameters
    ----------
    vertical_force : ndarray (N,) — vertical GRF (positive = up in OpenSim Y)
    threshold      : float        — force threshold (N, default 30)
    pad_frames     : int          — extra frames before / after (default 25)

    Returns
    -------
    start_idx : int — 0-indexed start (with padding)
    end_idx   : int — 0-indexed end   (with padding)
    hs_idx    : int — 0-indexed heel-strike frame
    to_idx    : int — 0-indexed toe-off frame
    """
    contact = np.abs(vertical_force) > threshold

    if not np.any(contact):
        raise ValueError("No stance phase detected (force never exceeds threshold)")

    contact_indices = np.where(contact)[0]
    hs_idx = int(contact_indices[0])
    to_idx = int(contact_indices[-1])

    start_idx = max(0, hs_idx - pad_frames)
    end_idx   = min(len(vertical_force) - 1, to_idx + pad_frames)

    return start_idx, end_idx, hs_idx, to_idx


# ═══════════════════════════════════════════════════════════════════════════════
#  File Writers — .trc  (Markers)
# ═══════════════════════════════════════════════════════════════════════════════

def write_trc(filepath, marker_data, marker_labels, frame_rate,
              units='mm', orig_start_frame=1):
    """
    Write marker data to OpenSim .trc file.

    Parameters
    ----------
    filepath       : str
    marker_data    : ndarray (n_frames, n_markers * 3)  — X Y Z interleaved
    marker_labels  : list[str]       — marker names
    frame_rate     : float           — Hz
    units          : str             — 'mm' or 'm'
    orig_start_frame : int           — original first frame number
    """
    n_frames  = marker_data.shape[0]
    n_markers = len(marker_labels)
    filename  = os.path.basename(filepath)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, 'w', newline='') as f:
        # ── Line 1: file type identifier ──
        f.write(f"PathFileType\t4\t(X/Y/Z)\t{filename}\n")

        # ── Line 2: header field names ──
        f.write("DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits\t"
                "OrigDataRate\tOrigDataStartFrame\tOrigNumFrames\n")

        # ── Line 3: header field values ──
        f.write(f"{frame_rate:.0f}\t{frame_rate:.0f}\t{n_frames}\t{n_markers}\t"
                f"{units}\t{frame_rate:.0f}\t{orig_start_frame}\t{n_frames}\n")

        # ── Line 4: marker name row (each name spans 3 columns) ──
        name_parts = ["Frame#", "Time"]
        for lbl in marker_labels:
            name_parts.extend([lbl, "", ""])
        f.write("\t".join(name_parts) + "\n")

        # ── Line 5: axis sub-headers ──
        sub_parts = ["", ""]
        for i in range(n_markers):
            idx = i + 1
            sub_parts.extend([f"X{idx}", f"Y{idx}", f"Z{idx}"])
        f.write("\t".join(sub_parts) + "\n")

        # ── Line 6: blank line ──
        f.write("\n")

        # ── Data rows ──
        for i in range(n_frames):
            frame_num = i + 1
            time_val  = i / frame_rate
            row = [f"{frame_num}", f"{time_val:.6f}"]
            for j in range(marker_data.shape[1]):
                row.append(f"{marker_data[i, j]:.6f}")
            f.write("\t".join(row) + "\n")

    print(f"  [OK] TRC -> {filepath}  ({n_frames} frames, {n_markers} markers)")


# ═══════════════════════════════════════════════════════════════════════════════
#  File Writers — .mot  (Ground Reaction Forces)
# ═══════════════════════════════════════════════════════════════════════════════

def write_mot(filepath, force_data_per_plate, n_plates, frame_rate,
              filename=None):
    """
    Write force-plate data to OpenSim .mot file.

    Column layout (matching standard OpenSim template):
      time
      [FP1 force 3] [FP1 COP 3]  [FP2 force 3] [FP2 COP 3] …
      [FP1 torque 3]            [FP2 torque 3] …

    Parameters
    ----------
    filepath             : str
    force_data_per_plate : list[dict]
        Each dict has keys 'force' (n, 3), 'cop' (n, 3), 'torque' (n, 3)
    n_plates             : int
    frame_rate           : float — Hz
    filename             : str or None — header filename (default: basename)
    """
    n_frames = force_data_per_plate[0]['force'].shape[0]
    fname    = filename or os.path.basename(filepath)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # ── Build column labels ──
    labels = ["time"]

    # Force + COP columns for all plates first
    for pi in range(n_plates):
        prefix = "" if pi == 0 else f"{pi}_"
        labels.extend([
            f"{prefix}ground_force_vx",
            f"{prefix}ground_force_vy",
            f"{prefix}ground_force_vz",
            f"{prefix}ground_force_px",
            f"{prefix}ground_force_py",
            f"{prefix}ground_force_pz",
        ])
    # Then torque columns for all plates
    for pi in range(n_plates):
        prefix = "" if pi == 0 else f"{pi}_"
        labels.extend([
            f"{prefix}ground_torque_x",
            f"{prefix}ground_torque_y",
            f"{prefix}ground_torque_z",
        ])

    n_cols = len(labels)

    with open(filepath, 'w', newline='') as f:
        # ── Header ──
        f.write(f"{fname}\n")
        f.write("version=1\n")
        f.write(f"nRows={n_frames}\n")
        f.write(f"nColumns={n_cols}\n")
        f.write("inDegrees=yes\n")
        f.write("endheader\n")

        # ── Column labels ──
        f.write("\t".join(labels) + "\n")

        # ── Data rows ──
        for i in range(n_frames):
            time_val = i / frame_rate
            row = [f"{time_val:.6f}"]

            # Force + COP for each plate
            for pi in range(n_plates):
                d = force_data_per_plate[pi]
                for v in d['force'][i, :]:
                    row.append(f"{v:.6f}")
                for v in d['cop'][i, :]:
                    row.append(f"{v:.6f}")

            # Torque for each plate
            for pi in range(n_plates):
                d = force_data_per_plate[pi]
                for v in d['torque'][i, :]:
                    row.append(f"{v:.6f}")

            f.write("\t".join(row) + "\n")

    print(f"  [OK] MOT -> {filepath}  ({n_frames} frames, {n_plates} plates, {n_cols} columns)")
