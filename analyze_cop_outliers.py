"""
Analyze COP data patterns in STO files to understand why median-based
outlier detection with 0.08m threshold misses certain outliers.
"""

import numpy as np
from scipy.signal import find_peaks

def read_sto_file(filepath):
    """Read an OpenSim STO file and return column names + data dict."""
    with open(filepath, 'r') as f:
        lines = f.readlines()

    # Find endheader line
    header_end = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('endheader'):
            header_end = i
            break

    # Column names are on the line right after endheader
    col_line = lines[header_end + 1].strip()
    # Skip the 'time' column name if present, or just split
    cols = col_line.split('\t')

    # Data starts from header_end + 2
    data_lines = lines[header_end + 2:]
    data = []
    for line in data_lines:
        line = line.strip()
        if not line:
            continue
        vals = line.split('\t')
        data.append([float(v) for v in vals])

    data = np.array(data)

    result = {}
    for j, col in enumerate(cols):
        result[col] = data[:, j]

    return cols, result


def find_stance_phase(force_vy, force_vz, threshold=30.0):
    """
    Find stance phase indices using peak detection on ground reaction force.
    Uses the larger of vy or vz, with threshold.
    Returns boolean mask of stance phase.
    """
    # Use magnitude of vertical forces
    # vy is typically the vertical GRF in OpenSim
    force_mag = np.sqrt(force_vy**2 + force_vz**2)

    # Simple threshold: force above threshold means contact
    stance_mask = force_mag > threshold

    return stance_mask


def analyze_file(filepath, label, focus_col):
    """Full analysis of one STO file."""
    print("=" * 80)
    print(f"FILE: {label}")
    print(f"Path: {filepath}")
    print(f"Focus column with expected outliers: {focus_col}")
    print("=" * 80)

    cols, data = read_sto_file(filepath)

    # Get relevant columns
    time = data['time']
    force_vy = data['2_ground_force_vy']
    force_vz = data['2_ground_force_vz']
    copx = data['2_ground_force_px']
    copz = data['2_ground_force_pz']

    # Note: Header says ground_force_p=mm, but actual data is in METERS (known OpenSim issue)
    # e.g., COPx values of 0.18-0.47 = 0.18m-0.47m = 180mm-470mm (realistic foot COP range)
    # The codebase has fix_sto_ground_force_units() to correct the header
    print(f"\n--- Unit clarification: Header says 'mm' but data is actually in METERS ---")
    print(f"--- (COPx ~0.18-0.55m = 180-550mm is realistic for running foot COP) ---")
    print(f"Threshold: 0.08m from median")
    print(f"Total data points: {len(time)}")

    # Find stance phase
    stance_mask = find_stance_phase(force_vy, force_vz, threshold=30.0)
    stance_indices = np.where(stance_mask)[0]
    print(f"\nStance phase points: {len(stance_indices)}")

    if len(stance_indices) == 0:
        print("NO STANCE PHASE DETECTED - trying with lower threshold")
        stance_mask = find_stance_phase(force_vy, force_vz, threshold=10.0)
        stance_indices = np.where(stance_mask)[0]
        print(f"Stance phase points (threshold=10N): {len(stance_indices)}")

    if len(stance_indices) == 0:
        print("Still no stance phase. Aborting this file.")
        return

    # Extract COP during stance
    copx_stance = copx[stance_mask]
    copz_stance = copz[stance_mask]
    time_stance = time[stance_mask]
    force_vy_stance = force_vy[stance_mask]
    force_vz_stance = force_vz[stance_mask]

    print(f"Stance time range: {time_stance[0]:.3f}s - {time_stance[-1]:.3f}s")

    # ---- COPx analysis ----
    print(f"\n{'-'*60}")
    print(f"COPx (2_ground_force_px) during stance")
    print(f"{'-'*60}")
    _analyze_cop_component(copx_stance, time_stance, force_vy_stance, "COPx", 0.08)

    # ---- COPz analysis ----
    print(f"\n{'-'*60}")
    print(f"COPz (2_ground_force_pz) during stance")
    print(f"{'-'*60}")
    _analyze_cop_component(copz_stance, time_stance, force_vy_stance, "COPz", 0.08)

    # ---- Temporal pattern: show COP over time with running stats ----
    print(f"\n{'-'*60}")
    print(f"TEMPORAL ANALYSIS - Looking for clusters/jumps")
    print(f"{'-'*60}")

    for comp_name, comp_data in [("COPx", copx_stance), ("COPz", copz_stance)]:
        print(f"\n  --- {comp_name} temporal breakdown ---")
        n = len(comp_data)
        # Split into early/mid/late stance thirds
        third = n // 3
        early = comp_data[:third]
        mid = comp_data[third:2*third]
        late = comp_data[2*third:]

        print(f"  Early stance ({time_stance[0]:.3f}-{time_stance[third-1]:.3f}s): "
              f"median={np.median(early):.4f}m, mean={np.mean(early):.4f}m, "
              f"std={np.std(early):.4f}m, min={np.min(early):.4f}, max={np.max(early):.4f}")
        print(f"  Mid stance   ({time_stance[third]:.3f}-{time_stance[2*third-1]:.3f}s): "
              f"median={np.median(mid):.4f}m, mean={np.mean(mid):.4f}m, "
              f"std={np.std(mid):.4f}m, min={np.min(mid):.4f}, max={np.max(mid):.4f}")
        print(f"  Late stance  ({time_stance[2*third]:.3f}-{time_stance[-1]:.3f}s): "
              f"median={np.median(late):.4f}m, mean={np.mean(late):.4f}m, "
              f"std={np.std(late):.4f}m, min={np.min(late):.4f}, max={np.max(late):.4f}")

    # ---- Show consecutive differences to detect jumps ----
    print(f"\n{'-'*60}")
    print(f"CONSECUTIVE DIFFERENCES (detecting jumps)")
    print(f"{'-'*60}")
    for comp_name, comp_data in [("COPx", copx_stance), ("COPz", copz_stance)]:
        diffs = np.diff(comp_data)
        print(f"\n  --- {comp_name} frame-to-frame differences ---")
        print(f"  Mean diff: {np.mean(diffs):.5f}m ({np.mean(diffs)*1000:.2f}mm)")
        print(f"  Std diff:  {np.std(diffs):.5f}m ({np.std(diffs)*1000:.2f}mm)")
        print(f"  Max abs diff: {np.max(np.abs(diffs)):.5f}m ({np.max(np.abs(diffs))*1000:.2f}mm)")
        # Show top 10 largest jumps
        jump_idx = np.argsort(np.abs(diffs))[::-1][:10]
        print(f"  Top 10 largest jumps:")
        for rank, idx in enumerate(jump_idx):
            abs_idx = stance_indices[idx]
            print(f"    #{rank+1}: at t={time_stance[idx]:.3f}s (row {abs_idx}), "
                  f"from {comp_data[idx]:.4f} to {comp_data[idx+1]:.4f}m "
                  f"(jump={diffs[idx]:.4f}m, |jump|={abs(diffs[idx])*1000:.1f}mm), "
                  f"force_vy={force_vy_stance[idx]:.1f}N")

    # ---- Show the actual COP trajectory with context ----
    print(f"\n{'-'*60}")
    print(f"FULL COP TRAJECTORY SAMPLE (every 5th point or all if <60)")
    print(f"{'-'*60}")
    step = max(1, len(copx_stance) // 60)
    print(f"  {'time':>8s} {'COPx(m)':>10s} {'COPz(m)':>10s} {'Fvy':>10s} {'COPx-med':>10s} {'COPz-med':>10s} {'|Cx-med|>0.08?':>14s} {'|Cz-med|>0.08?':>14s}")
    copx_med = np.median(copx_stance)
    copz_med = np.median(copz_stance)
    for i in range(0, len(copx_stance), step):
        t = time_stance[i]
        cx = copx_stance[i]
        cz = copz_stance[i]
        fvy = force_vy_stance[i]
        dx = abs(cx - copx_med)
        dz = abs(cz - copz_med)
        flag_x = "YES<--" if dx > 0.08 else ""
        flag_z = "YES<--" if dz > 0.08 else ""
        print(f"  {t:8.3f} {cx:10.4f} {cz:10.4f} {fvy:10.1f} {dx:10.4f} {dz:10.4f} {flag_x:>14s} {flag_z:>14s}")

    print()


def _analyze_cop_component(cop_data, time_stance, force_stance, name, threshold_m):
    """Analyze one COP component (COPx or COPz). Data is in METERS."""
    median_val = np.median(cop_data)
    mean_val = np.mean(cop_data)
    std_val = np.std(cop_data)

    abs_dist = np.abs(cop_data - median_val)

    print(f"  Median:  {median_val:.4f} m ({median_val*1000:.1f} mm)")
    print(f"  Mean:    {mean_val:.4f} m ({mean_val*1000:.1f} mm)")
    print(f"  Std:     {std_val:.4f} m ({std_val*1000:.1f} mm)")
    print(f"  Min:     {np.min(cop_data):.4f} m ({np.min(cop_data)*1000:.1f} mm)")
    print(f"  Max:     {np.max(cop_data):.4f} m ({np.max(cop_data)*1000:.1f} mm)")
    print(f"  Range:   {np.max(cop_data) - np.min(cop_data):.4f} m ({(np.max(cop_data) - np.min(cop_data))*1000:.1f} mm)")

    print(f"\n  Percentiles:")
    for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
        val = np.percentile(cop_data, p)
        print(f"    {p:3d}th: {val:.4f} m ({val*1000:.1f} mm)")

    print(f"\n  Distance from median (|value - median|):")
    print(f"    Median distance:  {np.median(abs_dist):.4f} m ({np.median(abs_dist)*1000:.1f} mm)")
    print(f"    Mean distance:    {np.mean(abs_dist):.4f} m ({np.mean(abs_dist)*1000:.1f} mm)")
    print(f"    Max distance:     {np.max(abs_dist):.4f} m ({np.max(abs_dist)*1000:.1f} mm)")
    print(f"    95th pctile dist: {np.percentile(abs_dist, 95):.4f} m ({np.percentile(abs_dist, 95)*1000:.1f} mm)")
    print(f"    99th pctile dist: {np.percentile(abs_dist, 99):.4f} m ({np.percentile(abs_dist, 99)*1000:.1f} mm)")

    # How many exceed threshold
    n_exceed = np.sum(abs_dist > threshold_m)
    pct_exceed = 100.0 * n_exceed / len(abs_dist)
    print(f"\n  Points exceeding {threshold_m:.2f}m from median: {n_exceed} / {len(abs_dist)} ({pct_exceed:.1f}%)")

    # Show the actual values that are farthest from median
    far_idx = np.argsort(abs_dist)[::-1][:15]
    print(f"\n  Top 15 points farthest from median:")
    print(f"    {'Rank':>4s} {'Time':>8s} {'Value(m)':>10s} {'|Dist|(m)':>10s} {'Force_vy':>10s} {'Exceeds?':>8s}")
    for rank, idx in enumerate(far_idx):
        exceed = "YES" if abs_dist[idx] > threshold_m else "no"
        print(f"    {rank+1:4d} {time_stance[idx]:8.3f} {cop_data[idx]:10.4f} {abs_dist[idx]:10.4f} {force_stance[idx]:10.1f} {exceed:>8s}")

    # Distribution histogram (text-based) with 0.01m bins
    print(f"\n  Distribution of |distance from median| (bin width 0.01m = 10mm):")
    bins = np.arange(0, np.max(abs_dist) + 0.01, 0.01)
    hist, _ = np.histogram(abs_dist, bins=bins)
    for i in range(len(hist)):
        if hist[i] == 0:
            continue
        bar = '#' * hist[i]
        label = f"{bins[i]:.2f}-{bins[i+1]:.2f}m"
        marker = " <-- THRESHOLD (0.08m)" if bins[i] <= threshold_m < bins[i+1] else ""
        print(f"    {label:>18s}: {hist[i]:4d} {bar}{marker}")


if __name__ == "__main__":
    files = [
        (r"E:\Python_Learn\CarbonShoes_DataProcess\OPenSIm\Data\input\Amateur_Runner\S1\T3\S1T3V22.sto",
         "S1T3V22 (COPz late-stance outliers not caught)"),
        (r"E:\Python_Learn\CarbonShoes_DataProcess\OPenSIm\Data\input\Amateur_Runner\S1\T1\S1T1V23.sto",
         "S1T1V23 (COPx early-stance outliers not caught)"),
        (r"E:\Python_Learn\CarbonShoes_DataProcess\OPenSIm\Data\input\Amateur_Runner\S1\T2\S1T2V11.sto",
         "S1T2V11 (COPx late-stance outliers not caught)"),
    ]

    for filepath, label in files:
        # Infer focus column from label
        if "COPz" in label:
            focus = "COPz"
        else:
            focus = "COPx"
        analyze_file(filepath, label, focus)

    # ---- Summary ----
    print("\n" + "=" * 80)
    print("SUMMARY: Why median-based 0.08m threshold fails")
    print("=" * 80)
    print("""
Key insight: A median-based threshold checks |value - median| > 0.08m (80mm).

This fails when outliers form a CLUSTER that shifts the median itself, or when
the outliers are at one end of the stance phase but not far enough from the
overall median to exceed 80mm, even though they represent a discontinuous jump
from the normal COP trajectory.

Common failure patterns:
1. LATE-STANCE outliers: The COP drifts to an abnormal position gradually (or
   jumps in the last few frames). The median is pulled toward the middle of the
   full stance range, and the late-stance abnormal values, while clearly
   separated from the main trajectory, may not be 80mm away from that median.

2. EARLY-STANCE outliers: Similarly, the first few frames of contact may have
   noisy/unrealistic COP values that are part of a cluster (e.g., 5-10 points)
   all offset in the same direction. The cluster is internally consistent but
   discontinuous from the rest of the trajectory. The median doesn't capture
   this because it's computed over the entire stance phase.

3. The median is robust to individual outliers but NOT to clustered outliers.
   When 10-20% of stance points are systematically offset, the median shifts
   toward the cluster, reducing the apparent distance.

Recommendations:
- Use a RUNNING/MOVING median or segment-based analysis instead of global median
- Check for DISCONTINUITIES (frame-to-frame jumps) rather than distance from median
- Split stance into phases and check each phase separately
- Use IQR-based methods or MAD (median absolute deviation) which are more sensitive
- Look at the derivative (rate of change) of COP - outliers often show sudden jumps
""")
