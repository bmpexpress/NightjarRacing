"""Nightjar Data Analysis 0.7.5 low-memory entry point.

Place this file beside the existing 0.7.4b app.py and start Streamlit with:
    streamlit run app_0.7.5.py

The existing application UI and analysis functions are retained. This entry point
replaces the high-memory startup functions before calling app.main().
"""
from __future__ import annotations

import io
import resource
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import app as base

base.APP_VERSION = "0.7.5"
base.DATA_DIR = Path("/Data")


def log_memory(stage):
    """Write peak process memory to Railway logs."""
    try:
        memory_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        print(
            f"[Nightjar] {stage}: peak memory approximately {memory_mb:.1f} MB",
            flush=True,
        )
    except Exception:
        pass


def optimise_dtypes(df):
    """Downcast columns in place to avoid duplicating the complete DataFrame."""
    if df is None or df.empty:
        return df
    for column in df.select_dtypes(include=["float64"]).columns:
        df[column] = pd.to_numeric(df[column], downcast="float")
    for column in df.select_dtypes(include=["int64", "int32"]).columns:
        df[column] = pd.to_numeric(df[column], downcast="integer")
    for column in ("Boat", "Sail"):
        if column in df.columns:
            try:
                df[column] = df[column].astype("category")
            except Exception:
                pass
    return df


def local_cache_path_for(path):
    p = Path(path)
    stat = p.stat()
    safe = base.re.sub(r"[^A-Za-z0-9_.-]+", "_", p.stem)
    return p.with_name(
        f".{safe}_{stat.st_size}_{stat.st_mtime_ns}_nightjar_075.parquet"
    )


def parse_log(src):
    """Parse volume files directly, avoiding complete byte and text copies."""
    if isinstance(src, (str, Path)):
        path = Path(src)
        if not path.exists():
            raise FileNotFoundError(f"Log file not found: {path}")
        if path.stat().st_size == 0:
            raise ValueError("The log file is empty")

        with path.open(
            "r", encoding="utf-8-sig", errors="replace", newline=""
        ) as handle:
            first_line = handle.readline()
            second_line = handle.readline()

        if first_line.startswith("!") and second_line.lower().startswith("!boat"):
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            return base.parse_sparse(text)

        df = pd.read_csv(path, low_memory=False, on_bad_lines="warn")
    else:
        text = base.decode(src)
        if not text.strip():
            raise ValueError("The log file is empty")
        first_lines = text.splitlines()[:2]
        if (
            first_lines
            and first_lines[0].startswith("!")
            and len(first_lines) > 1
            and first_lines[1].lower().startswith("!boat")
        ):
            return base.parse_sparse(text)
        df = pd.read_csv(io.StringIO(text), low_memory=False, on_bad_lines="warn")

    if "Boat" in df.columns:
        boat_mask = df["Boat"].astype(str).str.strip().eq("0")
        df = df.loc[boat_mask]

    mapping = base.detect_columns(df)
    timestamp_column = mapping.get("timestamp")
    if timestamp_column:
        df[timestamp_column] = base.excel_dt(df[timestamp_column])
        df.sort_values(timestamp_column, inplace=True)

    for column in df.columns:
        if column != timestamp_column and df[column].dtype == object:
            numeric = pd.to_numeric(df[column], errors="coerce")
            populated = df[column].notna().sum()
            if numeric.notna().sum() >= max(1, int(0.8 * populated)):
                df[column] = numeric

    df.reset_index(drop=True, inplace=True)
    return ensure_vmg(df)


def ensure_vmg(df):
    """Add VMG in place where a logged VMG channel is absent."""
    if df is None or df.empty:
        return df
    mapping = base.detect_columns(df)
    if mapping.get("vmg"):
        return df
    bsp_col, twa_col = mapping.get("bsp"), mapping.get("twa")
    if not bsp_col or not twa_col:
        return df
    bsp_values = pd.to_numeric(df[bsp_col], errors="coerce")
    twa_values = base.signed_twa(pd.to_numeric(df[twa_col], errors="coerce"))
    df["VMG"] = bsp_values * np.cos(np.deg2rad(twa_values))
    return df


def ensure_vmg_pct(df, polar):
    """Create or complete VMG_PCT in place to avoid a full DataFrame copy."""
    if df is None or df.empty or polar is None:
        return df
    mapping = base.detect_columns(df)
    vmg_col = mapping.get("vmg")
    tws_col = mapping.get("tws")
    twa_col = mapping.get("twa")
    if not vmg_col or not tws_col or not twa_col:
        return df

    actual_vmg = pd.to_numeric(df[vmg_col], errors="coerce")
    twa_abs = base.signed_twa(
        pd.to_numeric(df[twa_col], errors="coerce")
    ).abs()
    target_bsp = base.target_bsp_from_polar(
        polar, df[tws_col], df[twa_col]
    )
    target_vmg = target_bsp * np.cos(np.deg2rad(twa_abs))
    denominator = target_vmg.abs().where(target_vmg.abs() >= 0.05)
    calculated = actual_vmg.abs().div(denominator).mul(100.0)
    calculated = calculated.replace([np.inf, -np.inf], np.nan)

    existing_col = mapping.get("vmg_pct")
    if existing_col and existing_col in df.columns:
        existing = pd.to_numeric(df[existing_col], errors="coerce")
        df[existing_col] = existing.where(existing.notna(), calculated)
    else:
        df["VMG_PCT"] = calculated
    return df


def load_log_fast(src):
    """Use a persistent disk cache for volume files."""
    if isinstance(src, (str, Path)):
        source_path = Path(src)
        cache = local_cache_path_for(source_path)
        pickle_cache = cache.with_suffix(".pkl")

        if cache.exists() and cache.stat().st_mtime_ns >= source_path.stat().st_mtime_ns:
            try:
                return pd.read_parquet(cache)
            except Exception:
                pass
        if (
            pickle_cache.exists()
            and pickle_cache.stat().st_mtime_ns >= source_path.stat().st_mtime_ns
        ):
            try:
                return pd.read_pickle(pickle_cache)
            except Exception:
                pass

        log_memory("before CSV parse")
        df = optimise_dtypes(parse_log(source_path))
        log_memory("after CSV parse")
        try:
            df.to_parquet(cache, index=False)
        except Exception:
            try:
                df.to_pickle(pickle_cache)
            except Exception as exc:
                print(f"[Nightjar] Could not write data cache: {exc}", flush=True)
        return df

    raw = base.read_bytes(src)
    return optimise_dtypes(parse_log(io.BytesIO(raw)))


# Install the low-memory implementations into the original application module.
base.log_memory = log_memory
base.optimise_dtypes = optimise_dtypes
base.local_cache_path_for = local_cache_path_for
base.parse_log = parse_log
base.ensure_vmg = ensure_vmg
base.ensure_vmg_pct = ensure_vmg_pct
base.load_log_fast = load_log_fast

# Update names shown in downloads generated by the original application.
_original_download_button = st.download_button


def versioned_download_button(label, data, file_name=None, *args, **kwargs):
    if isinstance(file_name, str):
        file_name = file_name.replace("0.7.4", "0.7.5")
    return _original_download_button(label, data, file_name, *args, **kwargs)


st.download_button = versioned_download_button

if __name__ == "__main__":
    log_memory("before application start")
    with st.spinner("Starting Nightjar Data Analysis 0.7.5..."):
        base.main()
