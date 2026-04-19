# Kistler C3D Extractor

Extract marker trajectories, ground reaction forces (GRF), centre of pressure (COP), and free moments from C3D files recorded with **Kistler Type 3 (8-channel) force plates**.

## Scripts

| Script | Output frame | COP units | Use case |
|--------|-------------|-----------|----------|
| `extract_kistler_local.py` | Kistler plate-local (right+, posterior+, down+) | mm from plate centre | Plate-level analysis |
| `extract_kistler_global.py` | Lab global (forward+, left+, up+) | m from plate corner | Comparison with V3D / OpenSim |

## Quick Start

```bash
pip install -r requirements.txt

# Plate-local output
python extract_kistler_local.py demo_data

# Lab-global output
python extract_kistler_global.py demo_data
```

## Usage

```
python extract_kistler_local.py  <data_folder> [output_folder]
python extract_kistler_global.py <data_folder> [output_folder]
```

- `<data_folder>` — folder containing `.c3d` files
- `[output_folder]` — optional; defaults to `<data_folder>/output_local/` or `output_global/`

## Output Files (per trial)

| File | Content |
|------|---------|
| `*_markers.csv` | 3D marker positions (X, Y, Z in mm) + residual |
| `*_GRF.csv` | Ground reaction forces (N) per force plate |
| `*_COP.csv` | Centre of pressure per force plate |
| `*_free_moments.csv` | Free vertical moment Tz (N·mm) per force plate |

All files include a `Time_s` column. Columns are prefixed with `FP1_`, `FP2_`, etc.

## Coordinate Systems

### Plate-local output (`extract_kistler_local.py`)

```
Fx: medio-lateral,       right     = positive (N)
Fy: anterior-posterior,   posterior = positive (N)
Fz: vertical,            downward  = positive (N)
ax: COP ML from centre,  right     = positive (mm)
ay: COP AP from centre,  posterior = positive (mm)
```

### Lab-global output (`extract_kistler_global.py`)

```
         Z (up)
         |
         |
         +------→ X (forward, 900 mm side)
        /
       /
      Y (left, 600 mm side)

Fx: forward+  (N)        COP_X: forward from corner  (m)
Fy: left+     (N)        COP_Y: left from corner     (m)
Fz: upward+   (N)        Tz:    about Z-up           (N·mm)
```

## Force Plate Parameters

The scripts read `FORCE_PLATFORM:ORIGIN` from the C3D file to obtain:

| Parameter | Description | Typical value |
|-----------|-------------|---------------|
| `b` (ORIGIN[0]) | Sensor offset, local X / ML | 210 mm |
| `a` (ORIGIN[1]) | Sensor offset, local Y / AP | 350 mm |
| `az0` (ORIGIN[2]) | Top-plate surface offset | −52 mm |

## Threshold

COP and Tz are set to `NaN` when `|Fz| < 20 N` to avoid noise-level scatter. Adjust `FZ_THRESHOLD` at the top of each script if needed.

## Requirements

- Python 3.7+
- numpy
- pandas
- ezc3d

## Demo Data

`demo_data/` contains one sample C3D file (`Trimmed_S15T1V11.c3d`) for testing.

## Notes

- These scripts are designed for **Kistler Type 3** force plates (8 raw channels per plate). They will not work with Type 2 (6-channel Fx/Fy/Fz/Mx/My/Mz) or other plate types.
- `ezc3d` automatically applies the analog scale factors stored in the C3D file. No manual calibration is needed.
- The global script uses `FORCE_PLATFORM:CORNERS` to determine plate position. If your C3D stores both plates at the same corner coordinates, the COP will be relative to that shared origin.
