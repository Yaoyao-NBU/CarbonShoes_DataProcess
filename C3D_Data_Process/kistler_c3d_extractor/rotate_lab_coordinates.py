"""
Rotate Laboratory Coordinates for C3D Extracted Data
======================================================
Rotates coordinates from extract_kistler_global.py output files.

Supported rotations:
  - Axis: X, Y, Z (right-hand rule)
  - Angles: -270, -180, -90, 90, 180, 270 (degrees)

Data files affected:
  - *_markers.csv: rotates X, Y, Z for all markers
  - *_GRF.csv: rotates Fx, Fy, Fz for all force plates
  - *_COP.csv: rotates COFP_X, COFP_Y for all force plates (3D rotation)
  - *_free_moments.csv: rotates Mx, My, Mz for all force plates

Right-hand rule coordinate system:
  X = forward (anterior+)
  Y = left (left+)
  Z = upward (up+)
"""

import os
import glob
import numpy as np
import pandas as pd


# ==================== CONFIGURATION ====================
# Edit these settings to change rotation behavior

# Input folder containing CSV files
DATA_DIR = r"E:\Python_Learn\CarbonShoes_DataProcess\C3D_Data_Process\kistler_c3d_extractor"

# Output folder (use None to save to same folder as input)
OUTPUT_DIR = None

# Rotation axis: 'X', 'Y', or 'Z'
# X = forward axis, Y = left axis, Z = upward axis
ROTATION_AXIS = 'X'

# Rotation angle in degrees
# Positive = counter-clockwise, Negative = clockwise
# Supported: -270, -180, -90, 90, 180, 270
ROTATION_ANGLE = -90
# ======================================================


def get_rotation_matrix(axis, angle_deg):
    """
    Get 3D rotation matrix for specified axis and angle.

    Parameters
    ----------
    axis : str — 'X', 'Y', or 'Z'
    angle_deg : int — -270, -180, -90, 90, 180, or 270

    Returns
    -------
    ndarray (3, 3) — rotation matrix
    """
    theta = np.radians(angle_deg)
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)

    if axis.upper() == 'X':
        return np.array([
            [1, 0, 0],
            [0, cos_t, -sin_t],
            [0, sin_t, cos_t]
        ])
    elif axis.upper() == 'Y':
        return np.array([
            [cos_t, 0, sin_t],
            [0, 1, 0],
            [-sin_t, 0, cos_t]
        ])
    elif axis.upper() == 'Z':
        return np.array([
            [cos_t, -sin_t, 0],
            [sin_t, cos_t, 0],
            [0, 0, 1]
        ])
    else:
        raise ValueError(f"Invalid axis: {axis}. Use 'X', 'Y', or 'Z'.")


def rotate_markers(df, rotation_matrix):
    df_rotated = df.copy()

    for col in df.columns:
        if col.endswith('_X'):
            marker_name = col[:-2]
            y_col = f'{marker_name}_Y'
            z_col = f'{marker_name}_Z'

            if y_col in df.columns and z_col in df.columns:
                x = df[col].values
                y = df[y_col].values
                z = df[z_col].values

                coords = np.vstack([x, y, z])
                rotated = rotation_matrix @ coords

                df_rotated[col] = rotated[0, :]
                df_rotated[y_col] = rotated[1, :]
                df_rotated[z_col] = rotated[2, :]

    return df_rotated


def rotate_grf(df, rotation_matrix):
    df_rotated = df.copy()

    for col in df.columns:
        if col.endswith('_Fx'):
            fp_name = col[:-3]
            fy_col = f'{fp_name}_Fy'
            fz_col = f'{fp_name}_Fz'

            if fy_col in df.columns and fz_col in df.columns:
                fx = df[col].values
                fy = df[fy_col].values
                fz = df[fz_col].values

                forces = np.vstack([fx, fy, fz])
                rotated = rotation_matrix @ forces

                df_rotated[col] = rotated[0, :]
                df_rotated[fy_col] = rotated[1, :]
                df_rotated[fz_col] = rotated[2, :]

    return df_rotated


def rotate_cop_3d(df, rotation_matrix):
    df_rotated = df.copy()

    for col in df.columns:
        if col.endswith('_COFP_X'):
            fp_name = col[:-7]
            y_col = f'{fp_name}_COFP_Y'
            z_col = f'{fp_name}_COFP_Z'

            if y_col in df.columns:
                x = df[col].values            # 原始 COFP_X
                y_val = df[y_col].values       # 原始 COFP_Y

                # 实验室坐标系转OpenSim坐标系
                # OpenSim: X=前, Y=上, Z=左
                # 实验室: X=前, Y=左, Z=上
                df_rotated[col] = x           # COFP_X 不变
                df_rotated[z_col] = -y_val     # COFP_Z = -原始COFP_Y

    return df_rotated


def rotate_free_moments(df, rotation_matrix):
    df_rotated = df.copy()

    for col in df.columns:
        if col.endswith('_Mx'):
            fp_name = col[:-3]
            my_col = f'{fp_name}_My'
            mz_col = f'{fp_name}_Mz'

            if my_col in df.columns and mz_col in df.columns:
                mx = df[col].values
                my = df[my_col].values
                mz = df[mz_col].values

                moments = np.vstack([mx, my, mz])
                rotated = rotation_matrix @ moments

                df_rotated[col] = rotated[0, :]
                df_rotated[my_col] = rotated[1, :]
                df_rotated[mz_col] = rotated[2, :]

    return df_rotated


def process_file(filepath, rotation_matrix, axis, angle_deg, output_dir):
    filename = os.path.basename(filepath)
    df = pd.read_csv(filepath)

    if 'markers' in filename:
        df_rotated = rotate_markers(df, rotation_matrix)
    elif 'GRF' in filename:
        df_rotated = rotate_grf(df, rotation_matrix)
    elif 'COP' in filename:
        df_rotated = rotate_cop_3d(df, rotation_matrix)
    elif 'free_moments' in filename:
        df_rotated = rotate_free_moments(df, rotation_matrix)
    else:
        print(f"  INFO: Unknown file type. Skipping: {filename}")
        return False

    output_path = os.path.join(output_dir, filename)
    df_rotated.to_csv(output_path, index=False, float_format='%.6f')
    print(f"  Rotated: {filename}")

    return True


def main():
    print("=" * 60)
    print("Laboratory Coordinate Rotation Tool")
    print("=" * 60)

    data_dir = DATA_DIR
    output_dir = OUTPUT_DIR if OUTPUT_DIR else data_dir

    axis = ROTATION_AXIS.upper()
    angle_deg = ROTATION_ANGLE

    if axis not in ['X', 'Y', 'Z']:
        print(f"ERROR: Invalid axis. Must be X, Y, or Z.")
        return

    if angle_deg not in [-270, -180, -90, 90, 180, 270]:
        print(f"ERROR: Invalid angle {angle_deg}. Must be -270, -180, -90, 90, 180, or 270.")
        return

    rotation_matrix = get_rotation_matrix(axis, angle_deg)

    print(f"\nConfiguration:")
    print(f"  Input folder:  {data_dir}")
    print(f"  Output folder: {output_dir}")
    print(f"  Rotation axis: {axis}")
    print(f"  Rotation angle: {angle_deg}°")
    print(f"\nRotation matrix:")
    for row in rotation_matrix:
        print(f"  [{row[0]:8.3f}, {row[1]:8.3f}, {row[2]:8.3f}]")
    print("=" * 60)

    csv_files = sorted(glob.glob(os.path.join(data_dir, '*.csv')))
    if not csv_files:
        print(f"\nNo CSV files found in {data_dir}")
        return

    print(f"\nFound {len(csv_files)} CSV file(s)\n")
    os.makedirs(output_dir, exist_ok=True)

    rotated_count = 0
    for filepath in csv_files:
        try:
            if process_file(filepath, rotation_matrix, axis, angle_deg, output_dir):
                rotated_count += 1
        except Exception as e:
            print(f"  ERROR processing {os.path.basename(filepath)}: {e}")

    print("\n" + "=" * 60)
    print(f"Done. Rotated {rotated_count} file(s).")
    print("=" * 60)


if __name__ == '__main__':
    main()
