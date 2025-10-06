#!/usr/bin/env python3
import subprocess
import sys
import os
import re
import csv
from datetime import datetime
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

# ------------------------------
# Configuration
# ------------------------------
PPRIMES_PATH = Path("./pprimes")  # executable expected in same directory
NS = [1, 10, 100, 1000, 10000, 100000, 1000000, 10000000, 100000000]
THREADS = [1, 2, 4, 8, 16, 32, 64]
TRIALS = 3            # set to 3 (or more) when you want multiple trials
TIMEOUT_SEC = 3600    # per run cap

# ------------------------------
# Helpers (parsing)
# ------------------------------
ELAPSED_RE = re.compile(r'\[(?:sequential|threaded)\]\s+elapsed:\s*([0-9.]+)\s*ms', re.I)
TOTAL_RE   = re.compile(r'total primes:\s*([0-9]+)', re.I)

def run_once(n: int, t: int):
    """
    Run ./pprimes n t once, parse and return (elapsed_ms, total_primes).
    """
    if not PPRIMES_PATH.exists() or not os.access(PPRIMES_PATH, os.X_OK):
        raise FileNotFoundError(f"Executable not found or not executable: {PPRIMES_PATH}")
    try:
        # To suppress printing the prime list in your C, add an env var check (see note below),
        # then pass env=env with env['PPRIMES_QUIET']='1' here.
        result = subprocess.run([str(PPRIMES_PATH), str(n), str(t)],
                                capture_output=True, text=True, timeout=TIMEOUT_SEC)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Timed out: ./pprimes {n} {t}")

    stdout = result.stdout or ""
    m_time  = ELAPSED_RE.search(stdout)
    m_total = TOTAL_RE.search(stdout)
    if m_time is None or m_total is None:
        debug_path = Path(f"pprimes_output_n{n}_t{t}.txt")
        debug_path.write_text(stdout)
        raise RuntimeError(f"Failed to parse output for N={n}, threads={t}. Saved stdout to {debug_path}")
    return float(m_time.group(1)), int(m_total.group(1))

def run_trials(n: int, t: int, trials: int):
    """
    Returns (avg_ms, total_primes_from_last, times_ms_list)
    """
    times_ms = []
    total_last = None
    for i in range(trials):
        elapsed_ms, total = run_once(n, t)
        times_ms.append(elapsed_ms)
        total_last = total
        print(f"N={n}, T={t}, trial {i+1}/{trials}: {elapsed_ms:.3f} ms (total primes {total})")
    avg_ms = sum(times_ms) / len(times_ms)
    return avg_ms, total_last, times_ms

# ------------------------------
# Main
# ------------------------------
def main():
    if not PPRIMES_PATH.exists():
        print(f"Error: {PPRIMES_PATH} not found. Place 'pprimes' next to this script.", file=sys.stderr)
        sys.exit(1)
    if not os.access(PPRIMES_PATH, os.X_OK):
        print(f"Error: {PPRIMES_PATH} is not executable. Run: chmod +x pprimes", file=sys.stderr)
        sys.exit(1)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = Path(f"./trial_data/trial_data_{ts}")
    outdir.mkdir(exist_ok=True)

    # Collect data
    rows = []
    trials_map = {}  # (N, T) -> list of ms
    for n in NS:
        for t in THREADS:
            try:
                avg_ms, total_primes, times_ms = run_trials(n, t, TRIALS)
            except Exception as e:
                print(f"WARNING: failed (N={n}, T={t}): {e}", file=sys.stderr)
                avg_ms, total_primes, times_ms = float('nan'), -1, []
            rows.append({
                "N": n,
                "threads": t,
                "trials": TRIALS,
                "avg_ms": avg_ms,
                "avg_sec": (avg_ms / 1000.0) if avg_ms == avg_ms else float('nan'),
                "total_primes": total_primes,
            })
            trials_map[(n, t)] = times_ms

    # Build speedup (T1 / Tk) per (N, t)
    base_ms_by_n = {}
    for n in NS:
        base_row = next((r for r in rows if r["N"] == n and r["threads"] == 1), None)
        if base_row and base_row["avg_ms"] == base_row["avg_ms"]:
            base_ms_by_n[n] = base_row["avg_ms"]

    for r in rows:
        n, t = r["N"], r["threads"]
        base = base_ms_by_n.get(n)
        r["speedup"] = (base / r["avg_ms"]) if (base and r["avg_ms"] and r["avg_ms"] == r["avg_ms"] and r["avg_ms"] > 0) else float("nan")

    # Save CSV with per-trial columns too
    trial_cols = [f"trial_{i+1}_ms" for i in range(TRIALS)]
    csv_path = outdir / "pprimes_bench.csv"
    with open(csv_path, "w", newline="") as f:
        fieldnames = ["N", "threads", "trials"] + trial_cols + ["avg_ms", "avg_sec", "speedup", "total_primes"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            n, t = r["N"], r["threads"]
            rec = {k: r.get(k) for k in ["N", "threads", "trials", "avg_ms", "avg_sec", "speedup", "total_primes"]}
            # fill per-trial
            times = trials_map.get((n, t), [])
            for i in range(TRIALS):
                rec[f"trial_{i+1}_ms"] = times[i] if i < len(times) else ""
            writer.writerow(rec)
    print(f"Wrote CSV: {csv_path}")

    df = pd.DataFrame(rows)

    # ------------------------------
    # Plot 1: Seconds (linear y)
    # ------------------------------
    plt.figure()
    for t in THREADS:
        df_t = df[df["threads"] == t].sort_values("N")
        label = "Sequential" if t == 1 else f"{t} threads"
        plt.plot(df_t["N"], df_t["avg_sec"], marker="o", label=label)
    plt.title("Execution Time vs Problem Size (seconds)")
    plt.xlabel("Input Number")
    plt.ylabel("Execution Time (seconds)")
    plt.grid(True, linestyle=":")
    plt.xscale("log")
    plt.legend()
    plt.savefig(outdir / "time_seconds_vs_problem_size_all_threads.png", dpi=150, bbox_inches="tight")
    plt.close()

    # ------------------------------
    # Plot 2: Milliseconds (logarithmic y)
    # ------------------------------
    plt.figure()
    for t in THREADS:
        df_t = df[df["threads"] == t].sort_values("N")
        label = "Sequential" if t == 1 else f"{t} threads"
        plt.plot(df_t["N"], df_t["avg_ms"], marker="o", label=label)
    plt.title("Execution Time vs Problem Size (milliseconds, log scale)")
    plt.xlabel("Input Number")
    plt.ylabel("Execution Time (ms, log scale)")
    plt.grid(True, linestyle=":")
    plt.xscale("log")
    plt.yscale("log")
    plt.legend()
    plt.savefig(outdir / "time_milliseconds_logscale_vs_problem_size_all_threads.png", dpi=150, bbox_inches="tight")
    plt.close()

    # ------------------------------
    # Plot 3: Speedup vs Problem Size (baseline = 1 thread)
    # ------------------------------
    plt.figure()
    # Recompute speedup lines from df so it mirrors the chart pipeline
    base_map = df[df["threads"] == 1].set_index("N")["avg_ms"].to_dict()
    for t in THREADS:
        df_t = df[df["threads"] == t].sort_values("N").copy()
        if df_t.empty:
            continue
        df_t["speedup"] = df_t.apply(lambda row: (base_map.get(row["N"], float("nan")) / row["avg_ms"])
                                     if (pd.notna(row["avg_ms"]) and row["avg_ms"] > 0 and pd.notna(base_map.get(row["N"], float("nan"))))
                                     else float("nan"), axis=1)
        label = "Sequential" if t == 1 else f"{t} threads"
        plt.plot(df_t["N"], df_t["speedup"], marker="o", label=label)
    plt.title("Speedup vs Problem Size (T1 / Tk)")
    plt.xlabel("Input Number")
    plt.ylabel("Speedup (×)")
    plt.grid(True, linestyle=":")
    plt.xscale("log")
    plt.legend()
    plt.savefig(outdir / "speedup_vs_problem_size_all_threads.png", dpi=150, bbox_inches="tight")
    plt.close()

    # ---------------------------------------------
    # CSV (seconds columns) + Display Table (sci notation, 3 decimals)
    # ---------------------------------------------

    import math

    # Build baseline (avg of 1-thread trials in SECONDS) per N
    baseline_sec_by_n = {}
    for n in NS:
        t1_ms = trials_map.get((n, 1), [])
        if t1_ms:
            baseline_sec_by_n[n] = (sum(t1_ms) / len(t1_ms)) / 1000.0  # ms -> s

    # Assemble per-row records with seconds (NOT ms)
    sec_trial_cols = [f"trial_{i+1}_s" for i in range(TRIALS)]
    table_rows_raw = []
    for n in NS:
        for t in THREADS:
            times_ms = trials_map.get((n, t), [])
            secs = [ms / 1000.0 for ms in times_ms]
            avg_sec = (sum(secs) / len(secs)) if secs else float("nan")

            base = baseline_sec_by_n.get(n, float("nan"))
            speedup = (base / avg_sec) if (math.isfinite(base) and math.isfinite(avg_sec) and avg_sec > 0) else float("nan")

            rec = {"N": n, "threads": t, "trials": TRIALS}
            # fill trial seconds; if fewer than TRIALS for any reason, leave blank
            for i in range(TRIALS):
                rec[f"trial_{i+1}_s"] = secs[i] if i < len(secs) else float("nan")
            rec["avg_sec"] = avg_sec
            rec["speedup"] = speedup
            # keep total_primes from the compact 'rows' list (same (N, t))
            total_row = next((r for r in rows if r["N"] == n and r["threads"] == t), None)
            rec["total_primes"] = (total_row or {}).get("total_primes", "")
            table_rows_raw.append(rec)

    # Create DataFrame and sort
    df_table = pd.DataFrame(table_rows_raw).sort_values(["N", "threads"])

    # --- Formatting helpers (3-decimals everywhere) ---
    def fmt_scientific_sec(x):
        return "" if (x is None or (isinstance(x, float) and not math.isfinite(x))) else f"{x:.3e}"

    def fmt_three_dec(x):
        return "" if (x is None or (isinstance(x, float) and not math.isfinite(x))) else f"{x:.3f}"

    # Format a *copy* for display/image (strings)
    df_disp = df_table.copy()

    # Seconds-in-sci-notation for trials + avg_sec
    for col in sec_trial_cols + ["avg_sec"]:
        df_disp[col] = df_disp[col].apply(fmt_scientific_sec)

    # Speedup to 3 decimals
    df_disp["speedup"] = df_disp["speedup"].apply(fmt_three_dec)

    # Integers left as-is
    df_disp["N"] = df_disp["N"].astype(int)
    df_disp["threads"] = df_disp["threads"].astype(int)
    df_disp["trials"] = df_disp["trials"].astype(int)
    # total_primes already integer-like in your pipeline

    # --- Write CSV in this new format (seconds columns, no avg_ms) ---
    csv_path = outdir / "pprimes_bench_seconds.csv"
    df_csv = df_table.copy()
    # (Optional) round numeric fields in CSV to 3 decimals as well:
    for col in sec_trial_cols + ["avg_sec", "speedup"]:
        df_csv[col] = df_csv[col].apply(lambda v: (None if (v is None or (isinstance(v, float) and not math.isfinite(v))) else float(f"{v:.3f}")))
    df_csv.to_csv(csv_path, index=False)
    print(f"Wrote CSV: {csv_path}")

    # --- Render a table image like your screenshot ---
    # Columns order
    # --- Render a simplified table with renamed columns and no "trials" column ---

    # Column renaming and order
    display_cols = [
        "N",
        "threads",
        "trial_1_s",
        "trial_2_s",
        "trial_3_s",
        "avg_sec",
        "speedup",
        "total_primes"
    ]

    # Rename columns for display
    rename_map = {
        "trial_1_s": "trial 1 (sec)",
        "trial_2_s": "trial 2 (sec)",
        "trial_3_s": "trial 3 (sec)",
        "avg_sec": "avg (sec)",
        "total_primes": "prime count"
    }

    df_show = df_disp[display_cols].rename(columns=rename_map)

    # Figure sizing scales automatically with number of rows
    rows_count = len(df_show)
    cols_count = len(df_show.columns)
    fig_w = max(10, 1.1 * cols_count)
    fig_h = max(4, 0.45 * rows_count + 2.5)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis("off")

    # Create the table
    cell_text = df_show.values.tolist()
    col_labels = df_show.columns.tolist()

    tbl = ax.table(
        cellText=cell_text,
        colLabels=col_labels,
        loc="center"
    )

    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1.1, 1.3)

    # Align cells for better readability
    for (_, _), cell in tbl.get_celld().items():
        cell.set_text_props(va="center", ha="center")
        cell.PAD = 0.2

    ax.set_title("Benchmark Results (seconds, sci notation, 3 decimals)", pad=20)

    png_table = outdir / "summary_table_seconds_sci.png"
    fig.savefig(png_table, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote table image: {png_table}")
    
    print("Done.")

if __name__ == "__main__":
    main()
