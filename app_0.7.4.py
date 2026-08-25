from __future__ import annotations
import csv, hashlib, hmac, io, json, math, os, re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, time, UTC
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

NIGHTJAR_ORANGE = "#f28c28"
NIGHTJAR_ORANGE_RGBA = "rgba(242,140,40,0.58)"

APP_TITLE, APP_VERSION = "Nightjar Polar Analysis", "0.7.4"
DEFAULT_FILES = {
    "log":"0_MASTER LOG FILE.csv",
    "polar":"20260807 - A31 Polar for Expedition -REDUCED TARGETS - max tws 35 kt.txt",
    "events":"20260821_events_export.csv",
    "event_list":"Event List.txt",
    "tests":"20260821_Tests_Export.csv",
    "sail_chart":"20260728 - A31-SAILCHART.xml",
    "logo":"Nightjar Logo 2025.jpg",
}

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
ALIASES = {
    "timestamp":["utc","time","timestamp","datetime"],
    "bsp":["bsp","boat speed","log bsp"],
    "twa":["twa","true wind angle"],
    "tws":["tws","true wind speed"],
    "awa":["awa","apparent wind angle"],
    "aws":["aws"],
    "vmg":["vmg","velocity made good","vmg kt","vmg knots","vmg value","vmg kts"],
    "vmg_pct":["vmg%","vmg %","vmg pc","vmg percent","vmg_pct"],
    "heel":["heel"],
    "drift":["drift","tide rate"],
    "lat":["lat","latitude","lat1"],
    "lon":["lon","longitude","lon1"],
    "sog":["sog"],
    "cog":["cog"],
    "sail":["sail","foresail_id","foresail"],
}
CSS = """
<style>
:root {
  --nightjar-bg:#08141f;
  --nightjar-panel:#102435;
  --nightjar-control:#071018;
  --nightjar-line:#1e4058;
  --nightjar-orange:#f28c28;
  --nightjar-orange-soft:rgba(242,140,40,.22);
  --nightjar-orange-warning:rgba(242,140,40,.26);
}
.stApp {background:var(--nightjar-bg);} 
.block-container {padding-top:1.25rem !important; padding-bottom:0.7rem !important;}
h1 {font-size:1.55rem !important; margin-bottom:0.05rem !important;}
a, a:visited {color:var(--nightjar-orange) !important;}
a:hover, p:hover, span:hover, label:hover, div:hover {text-decoration-color:var(--nightjar-orange) !important;}
[data-testid='stSidebar'] {background:#252631;}
[data-testid='stSidebar'] img {margin-top:0.2rem;margin-bottom:0.45rem;}
.nightjar-side-title {font-size:1.45rem;font-weight:800;line-height:1.15;margin:0.25rem 0 0.15rem 0;color:white;}
.nightjar-side-caption {font-size:0.82rem;line-height:1.25;color:rgba(255,255,255,.72);margin-bottom:.65rem;}
[data-testid='stMetric'] {background:var(--nightjar-panel);border:1px solid var(--nightjar-line);padding:9px;border-radius:10px;}
button:hover, button:focus {border-color:var(--nightjar-orange) !important;color:var(--nightjar-orange) !important;box-shadow:0 0 0 1px var(--nightjar-orange) !important;}
.stTabs [data-baseweb='tab-list'] {gap:0.25rem;margin-top:0.05rem;}
.stTabs [data-baseweb='tab'] {height:2rem;padding:0.25rem 0.7rem;border-radius:8px 8px 0 0;color:rgba(255,255,255,.82) !important;}
.stTabs [aria-selected='true'] {color:var(--nightjar-orange) !important;border-bottom:3px solid var(--nightjar-orange) !important;}
.stTabs [data-baseweb='tab']:hover {color:var(--nightjar-orange) !important;}
.stTabs [data-baseweb='tab-highlight'] {background-color:var(--nightjar-orange) !important;}
[data-baseweb='checkbox'] span:first-child,
[data-baseweb='radio'] span:first-child {border-color:var(--nightjar-orange) !important;}
[data-baseweb='checkbox'] span:first-child:hover,
[data-baseweb='radio'] span:first-child:hover {box-shadow:0 0 0 3px var(--nightjar-orange-soft) !important;}
.stCheckbox [data-testid='stTickBar'],
[data-baseweb='checkbox'] [aria-checked='true'],
[data-baseweb='radio'] [aria-checked='true'] {background-color:var(--nightjar-orange) !important;border-color:var(--nightjar-orange) !important;}
/* Multiselect selected pills and clear/focus controls */
[data-baseweb='tag'] {background-color:var(--nightjar-orange) !important;color:white !important;border-color:var(--nightjar-orange) !important;}
[data-baseweb='tag'] span {color:white !important;}
[data-baseweb='tag'] svg {color:white !important;fill:white !important;}
[data-baseweb='select'] {background-color:var(--nightjar-control) !important;}
[data-baseweb='select'] div {border-color:transparent !important;}
[data-baseweb='select']:hover, [data-baseweb='select'] div:hover {border-color:var(--nightjar-orange) !important;}
[data-baseweb='select'] svg:hover, [data-baseweb='select'] svg {color:var(--nightjar-orange) !important;fill:var(--nightjar-orange) !important;}
[data-baseweb='popover'] li:hover {background-color:var(--nightjar-orange-soft) !important;color:var(--nightjar-orange) !important;}
input:focus, textarea:focus,
[data-baseweb='select'] div:focus-within,
[data-baseweb='input'] input:focus,
[data-baseweb='base-input']:focus-within {border-color:var(--nightjar-orange) !important;box-shadow:0 0 0 1px var(--nightjar-orange) !important;}
/* Warning/info boxes use Nightjar orange rather than default red/yellow/olive. */
[data-testid='stAlert'] {background-color:var(--nightjar-orange-warning) !important;border:1px solid var(--nightjar-orange) !important;border-radius:10px !important;color:white !important;}
[data-testid='stAlert'] * {color:white !important;}
[data-testid='stAlert'] svg {fill:var(--nightjar-orange) !important;color:var(--nightjar-orange) !important;}
hr, [data-testid='stHeader'], [data-testid='stDecoration'] {border-color:var(--nightjar-orange) !important;background-color:transparent !important;}
::selection {background:var(--nightjar-orange-soft);}
</style>
"""

def read_bytes(src):
    if src is None: return b""
    if isinstance(src, (str, Path)): return Path(src).read_bytes()
    src.seek(0); return src.read()

def decode(src):
    raw = read_bytes(src)
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try: return raw.decode(enc)
        except UnicodeDecodeError: pass
    return raw.decode("utf-8", errors="replace")

def norm(v): return re.sub(r"[^a-z0-9]+", " ", str(v).strip().lower()).strip()

def is_bad_vmg_name(name):
    n = norm(name)
    raw = str(name).lower()
    return any(x in raw for x in ["%", "pct"]) or n in {"vmg pc", "vmg percent", "targ vmg", "target vmg"}

def round_numeric_df(df, decimals=2):
    if df is None or not isinstance(df, pd.DataFrame):
        return df
    out = df.copy()
    num_cols = out.select_dtypes(include=np.number).columns
    if len(num_cols):
        out[num_cols] = out[num_cols].round(decimals)
    return out


def optimise_dtypes(df):
    """Reduce memory use for large season logs without changing visible values."""
    if df is None or df.empty:
        return df
    out = df.copy()
    for c in out.select_dtypes(include=["float64"]).columns:
        out[c] = pd.to_numeric(out[c], downcast="float")
    for c in out.select_dtypes(include=["int64", "int32"]).columns:
        out[c] = pd.to_numeric(out[c], downcast="integer")
    for c in ("Boat", "Sail"):
        if c in out.columns:
            try:
                out[c] = out[c].astype("category")
            except Exception:
                pass
    return out


def downsample_rows(df, max_points=10000):
    """Return at most max_points rows, preserving row order by regular stepping."""
    if df is None or df.empty:
        return df
    max_points = max(500, int(max_points or 10000))
    if len(df) <= max_points:
        return df
    step = max(1, math.ceil(len(df) / max_points))
    return df.iloc[::step].copy()


def local_cache_path_for(path):
    p = Path(path)
    stat = p.stat()
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", p.stem)
    return p.with_name(f".{safe}_{stat.st_size}_{stat.st_mtime_ns}_nightjar_074.parquet")


@st.cache_data(show_spinner=False, max_entries=4)
def parse_log_cached_bytes(raw, name="uploaded-log"):
    return optimise_dtypes(parse_log(io.BytesIO(raw)))


@st.cache_data(show_spinner=False, max_entries=8)
def parse_events_cached(raw):
    return parse_events(io.BytesIO(raw))


@st.cache_data(show_spinner=False, max_entries=8)
def parse_event_list_cached(raw):
    return parse_event_list(io.BytesIO(raw))


@st.cache_data(show_spinner=False, max_entries=8)
def parse_polar_cached(raw):
    return parse_polar(io.BytesIO(raw))


@st.cache_data(show_spinner=False, max_entries=8)
def parse_sails_cached(raw):
    return parse_sails(io.BytesIO(raw))


def load_log_fast(src):
    """Load local logs via disk cache; uploaded logs via Streamlit cache."""
    if isinstance(src, (str, Path)):
        p = Path(src)
        cache = local_cache_path_for(p)
        pickle_cache = cache.with_suffix(".pkl")
        if cache.exists() and cache.stat().st_mtime_ns >= p.stat().st_mtime_ns:
            try:
                return pd.read_parquet(cache)
            except Exception:
                pass
        if pickle_cache.exists() and pickle_cache.stat().st_mtime_ns >= p.stat().st_mtime_ns:
            try:
                return pd.read_pickle(pickle_cache)
            except Exception:
                pass
        df = optimise_dtypes(parse_log(p))
        try:
            df.to_parquet(cache, index=False)
        except Exception:
            try:
                df.to_pickle(pickle_cache)
            except Exception:
                pass
        return df
    raw = read_bytes(src)
    return parse_log_cached_bytes(raw, getattr(src, "name", "uploaded-log"))


def load_events_fast(src):
    return parse_events_cached(read_bytes(src)) if src else pd.DataFrame()


def load_event_list_fast(src):
    return parse_event_list_cached(read_bytes(src)) if src else pd.DataFrame(columns=["date", "type", "event"])


def load_polar_fast(src):
    return parse_polar_cached(read_bytes(src)) if src else None


def load_sails_fast(src):
    return parse_sails_cached(read_bytes(src)) if src else pd.DataFrame()

def detect_columns(df):
    cols = {norm(c): c for c in df.columns}; out = {}
    raw_exact = {str(c).strip().lower(): c for c in df.columns}
    for key, aliases in ALIASES.items():
        out[key] = next((raw_exact[str(a).strip().lower()] for a in aliases if str(a).strip().lower() in raw_exact), None)
        if out[key] is None:
            out[key] = next((cols[norm(a)] for a in aliases if norm(a) in cols), None)
        if out[key] is None:
            out[key] = next((orig for n, orig in cols.items() if any(n.startswith(norm(a)) for a in aliases)), None)

    # VMG and VMC are different measurements. Never map VMC as VMG.
    for candidate in ("vmg", "velocity made good", "vmg kt", "vmg knots", "vmg value", "vmg kts"):
        if candidate in raw_exact and not is_bad_vmg_name(raw_exact[candidate]):
            out["vmg"] = raw_exact[candidate]
            break
    if out.get("vmg") and is_bad_vmg_name(out["vmg"]):
        out["vmg"] = None

    # VMG percentage is separate; VMC percentage is not accepted.
    # Undo any fuzzy prefix match that incorrectly treated the plain VMG
    # channel as VMG_PCT (normalising "VMG%" produces the prefix "vmg").
    if out.get("vmg_pct") and not is_bad_vmg_name(out["vmg_pct"]):
        out["vmg_pct"] = None
    for candidate in ("vmg%", "vmg %", "vmg pc", "vmg percent", "vmg pct"):
        if candidate in raw_exact:
            out["vmg_pct"] = raw_exact[candidate]
            break
    if out.get("vmg_pct") is None:
        pct_candidates = [c for c in df.columns if "vmg" in norm(c) and is_bad_vmg_name(c)]
        if pct_candidates:
            out["vmg_pct"] = pct_candidates[0]

    return out

def ensure_vmg(df):
    """Add a standard VMG column when absent, using BSP × cos(TWA).

    VMC is never used. TWA is normalised to -180°..180°, giving positive VMG
    upwind, approximately zero on a beam reach and negative VMG downwind.
    Genuine logged VMG is retained unchanged.
    """
    if df is None or df.empty:
        return df
    mapping = detect_columns(df)
    if mapping.get("vmg"):
        return df
    bsp_col, twa_col = mapping.get("bsp"), mapping.get("twa")
    if not bsp_col or not twa_col:
        return df
    out = df.copy()
    bsp_values = pd.to_numeric(out[bsp_col], errors="coerce")
    twa_values = signed_twa(pd.to_numeric(out[twa_col], errors="coerce"))
    out["VMG"] = bsp_values * np.cos(np.deg2rad(twa_values))
    return out


def excel_dt(s):
    n = pd.to_numeric(s, errors="coerce")
    converted = pd.Timestamp("1899-12-30") + pd.to_timedelta(n, unit="D")
    parsed = pd.to_datetime(s, errors="coerce", dayfirst=True)
    return converted.where(n.between(20000, 80000), parsed)

def parse_sparse(text):
    lines = [x for x in text.splitlines() if x.strip()]
    names = next(csv.reader([lines[0]])); ids = next(csv.reader([lines[1]]))
    lookup = {i.strip(): n.lstrip("!").strip() for n, i in zip(names, ids) if i.strip().lstrip("-").isdigit()}
    rec = []
    for line in lines[3:]:
        f = next(csv.reader([line]))
        if len(f) < 2: continue
        row = {"Boat": f[0], "Utc": f[1]}
        for i in range(2, len(f)-1, 2):
            if f[i].strip() in lookup: row[lookup[f[i].strip()]] = f[i+1].strip()
        rec.append(row)
    df = pd.DataFrame(rec)
    if "Boat" in df.columns:
        df = df[df["Boat"].astype(str).str.strip().eq("0")].copy()
    df["Utc"] = excel_dt(df["Utc"])
    for c in df.columns:
        if c not in ("Boat", "Utc"):
            x = pd.to_numeric(df[c], errors="coerce")
            if x.notna().sum() >= max(1, int(.6 * df[c].notna().sum())): df[c] = x
    return ensure_vmg(df.sort_values("Utc").reset_index(drop=True))

def parse_log(src):
    text = decode(src); lines = [x for x in text.splitlines() if x.strip()]
    if not lines: raise ValueError("The log file is empty")
    if lines[0].startswith("!") and len(lines) > 2 and lines[1].lower().startswith("!boat"):
        return parse_sparse(text)
    df = pd.read_csv(io.StringIO(text), low_memory=False, on_bad_lines="warn")
    if "Boat" in df.columns:
        df = df[df["Boat"].astype(str).str.strip().eq("0")].copy()
    m = detect_columns(df)
    if m.get("timestamp"):
        df[m["timestamp"]] = excel_dt(df[m["timestamp"]]); df = df.sort_values(m["timestamp"])
    for c in df.columns:
        if c != m.get("timestamp") and df[c].dtype == object:
            x = pd.to_numeric(df[c], errors="coerce")
            if x.notna().sum() >= max(1, int(.8 * df[c].notna().sum())): df[c] = x
    return ensure_vmg(df.reset_index(drop=True))

@dataclass
class Polar:
    long: pd.DataFrame
    tws: list[float]

def parse_polar(src):
    rows = []
    for line in decode(src).splitlines():
        line = line.strip()
        if not line or line.startswith(("!", "#")): continue
        try: v = [float(x) for x in re.split(r"[\t,; ]+", line) if x]
        except ValueError: continue
        for i in range(1, len(v)-1, 2):
            if 0 <= v[i] <= 180 and v[i+1] >= 0:
                rows.append({"TWS": v[0], "TWA": v[i], "Target BSP": v[i+1]})
    long = pd.DataFrame(rows).drop_duplicates(["TWS", "TWA"])
    if long.empty: raise ValueError("No polar triplets found")
    return Polar(long.sort_values(["TWS", "TWA"]), sorted(long.TWS.unique().tolist()))


def target_bsp_from_polar(polar, tws_values, twa_values):
    """Interpolate target BSP for each TWS/TWA pair from the uploaded polar.

    Interpolation is linear first across TWA on each bounding wind-speed curve,
    then between those two TWS curves. Values outside the polar's TWS or TWA
    envelope remain unavailable rather than being extrapolated.
    """
    tws = pd.to_numeric(tws_values, errors="coerce").to_numpy(dtype=float)
    twa = signed_twa(pd.to_numeric(twa_values, errors="coerce")).abs().to_numpy(dtype=float)
    result = np.full(len(tws), np.nan, dtype=float)
    if polar is None or polar.long is None or polar.long.empty:
        return pd.Series(result, index=tws_values.index, dtype=float)

    curves = {}
    for wind, group in polar.long.groupby("TWS", sort=True):
        curve = group[["TWA", "Target BSP"]].copy()
        curve["TWA"] = pd.to_numeric(curve["TWA"], errors="coerce")
        curve["Target BSP"] = pd.to_numeric(curve["Target BSP"], errors="coerce")
        curve = curve.dropna().groupby("TWA", as_index=False)["Target BSP"].mean().sort_values("TWA")
        if not curve.empty:
            curves[float(wind)] = (curve["TWA"].to_numpy(dtype=float), curve["Target BSP"].to_numpy(dtype=float))
    winds = np.array(sorted(curves), dtype=float)
    if not len(winds):
        return pd.Series(result, index=tws_values.index, dtype=float)

    valid = np.isfinite(tws) & np.isfinite(twa) & (tws >= winds[0]) & (tws <= winds[-1])
    if not valid.any():
        return pd.Series(result, index=tws_values.index, dtype=float)

    upper = np.searchsorted(winds, tws, side="left")
    upper = np.clip(upper, 0, len(winds) - 1)
    lower = np.maximum(upper - 1, 0)
    exact = valid & np.isclose(tws, winds[upper], rtol=0.0, atol=1e-9)
    lower[exact] = upper[exact]

    for low_i, high_i in set(zip(lower[valid].tolist(), upper[valid].tolist())):
        mask = valid & (lower == low_i) & (upper == high_i)
        low_w, high_w = winds[low_i], winds[high_i]
        low_angles, low_speeds = curves[low_w]
        low_target = np.interp(twa[mask], low_angles, low_speeds, left=np.nan, right=np.nan)
        if low_i == high_i:
            result[mask] = low_target
            continue
        high_angles, high_speeds = curves[high_w]
        high_target = np.interp(twa[mask], high_angles, high_speeds, left=np.nan, right=np.nan)
        weight = (tws[mask] - low_w) / (high_w - low_w)
        result[mask] = low_target + weight * (high_target - low_target)
    return pd.Series(result, index=tws_values.index, dtype=float)


def ensure_vmg_pct(df, polar):
    """Create or complete VMG_PCT from actual VMG and the uploaded target polar.

    Target BSP is interpolated at every record's TWS and absolute TWA, then
    converted to target VMG. VMG_PCT is the magnitude of actual VMG divided by
    target VMG, multiplied by 100. Existing logged VMG percentage values are
    retained; only missing values are filled. Near a 90-degree beam reach,
    target VMG approaches zero, so the percentage is intentionally left blank.
    """
    if df is None or df.empty or polar is None:
        return df
    mapping = detect_columns(df)
    vmg_col, tws_col, twa_col = mapping.get("vmg"), mapping.get("tws"), mapping.get("twa")
    if not vmg_col or not tws_col or not twa_col:
        return df

    out = df.copy()
    actual_vmg = pd.to_numeric(out[vmg_col], errors="coerce")
    twa_abs = signed_twa(pd.to_numeric(out[twa_col], errors="coerce")).abs()
    target_bsp = target_bsp_from_polar(polar, out[tws_col], out[twa_col])
    target_vmg = target_bsp * np.cos(np.deg2rad(twa_abs))
    denominator = target_vmg.abs().where(target_vmg.abs() >= 0.05)
    calculated = actual_vmg.abs().div(denominator).mul(100.0)
    calculated = calculated.replace([np.inf, -np.inf], np.nan)

    existing_col = mapping.get("vmg_pct")
    if existing_col and existing_col in out.columns:
        existing = pd.to_numeric(out[existing_col], errors="coerce")
        out[existing_col] = existing.where(existing.notna(), calculated)
    else:
        out["VMG_PCT"] = calculated
    return out


def parse_event_list(src):
    """Parse the Nightjar Event List file.

    Current format:
        [Date],[Event Type],[Event Name]

    Example:
        20260801,Inshore,Cowes Week Race 1
        20260802,Offshore,Offshore Race

    Start times are intentionally not parsed from this file. Race-start timing is taken
    from the Expedition Events file by locating GUN entries.
    """
    rows = []
    if not src:
        return pd.DataFrame(columns=["date", "type", "event"])
    for line in decode(src).splitlines():
        if not line.strip():
            continue
        parts = [p.strip().strip('"') for p in line.split(",")]
        if len(parts) < 3:
            # Need date, event type and event name.
            continue
        try:
            event_date = pd.to_datetime(parts[0], format="%Y%m%d").date()
        except Exception:
            continue

        # Correct Nightjar format is [Date],[Event Type],[Event Name].
        event_type_raw = parts[1].strip()
        event_name = parts[2].strip() if len(parts) > 2 and parts[2].strip() else "Event"
        event_type_norm = event_type_raw.lower()
        if event_type_norm in {"inshore", "offshore"}:
            event_type = event_type_raw.title()
        else:
            # Keep unrecognised values visible rather than silently discarding them.
            event_type = event_type_raw.title() if event_type_raw else "Unknown"

        rows.append({
            "date": event_date,
            "type": event_type,
            "event": event_name,
        })
    return pd.DataFrame(rows)

def parse_events(src):
    if not src: return pd.DataFrame()
    rows = list(csv.reader(io.StringIO(decode(src))))
    if not rows: return pd.DataFrame()
    h, w = rows[0], len(rows[0]); clean = []
    for r in rows[1:]:
        if len(r) > w: r = r[:w-1] + [", ".join(r[w-1:])]
        clean.append(r + [""] * max(0, w-len(r)))
    df = pd.DataFrame(clean, columns=h)
    if "Time" in df: df["Time"] = pd.to_datetime(df.Time, errors="coerce", dayfirst=True)
    return df

def parse_sails(src):
    rows = []; root = ET.fromstring(read_bytes(src))
    for e in root.findall(".//element"):
        if e.get("type") != "Sail": continue
        c = e.find("colour"); rgb = tuple(int(c.get(k, "0")) for k in ("r", "g", "b")) if c is not None else (255,255,255)
        op = e.find("shapeopacity"); lw = e.find("linewidth")
        opacity = float(op.get("val", "40"))/100 if op is not None else .4
        width = float(lw.get("val", "3")) if lw is not None else 3
        for order, p in enumerate(e.findall("./bezierpoints/point"), 1):
            rows.append({"sail": e.get("name"), "order": order, "TWS": float(p.get("tws")), "TWA": float(p.get("twa")), "rgb": rgb, "opacity": opacity, "width": width})
    return pd.DataFrame(rows)

def local(upload, key):
    if upload is not None: return upload
    p = DATA_DIR / DEFAULT_FILES[key]
    return p if p.exists() else None

def signed_twa(s):
    x = pd.to_numeric(s, errors="coerce"); return ((x + 180) % 360) - 180

def point_filter(df, twa_col, selection):
    if not twa_col or selection == "All": return df
    a = signed_twa(df[twa_col]).abs(); return df[a <= 90] if selection.startswith("Upwind") else df[a > 90]

def average_with_ranges(df, ts, columns, seconds, tolerances=None, signed_twa_col=None):
    """Averaging with duplicate-column protection and non-inplace masks."""
    if seconds <= 1 or not ts or ts not in df or not pd.api.types.is_datetime64_any_dtype(df[ts]):
        return df.copy(), "raw"
    tolerances = tolerances or {}
    clean_columns = []
    for c in columns:
        if c and c in df.columns and c not in clean_columns and c != ts:
            clean_columns.append(c)
    cols = [ts] + clean_columns
    d = df[cols].dropna(subset=[ts]).copy()
    if signed_twa_col and signed_twa_col in d:
        d[signed_twa_col] = signed_twa(d[signed_twa_col])
    for c in clean_columns:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    value_cols = [c for c in clean_columns if c in d]
    if not value_cols:
        return df.copy(), "raw"
    rs = d.set_index(ts).sort_index()[value_cols]
    means = rs.resample(f"{int(seconds)}s").mean()
    ranges = rs.resample(f"{int(seconds)}s").agg(lambda x: x.max() - x.min())
    keep = pd.Series(True, index=means.index)
    for col, tol in tolerances.items():
        if col in ranges.columns and tol is not None:
            comparison = pd.to_numeric(ranges[col], errors="coerce") <= float(tol)
            keep = keep & comparison.fillna(False)
    out = means.loc[keep].dropna(how="all").reset_index()
    return out, f"{seconds}s average"

def half_polar_sailing_plot(df, m, polar, target, y_range=None):
    """Custom half-polar plot with 0° TWA at top, 180° at bottom, angles increasing clockwise.

    Plotly's native polar sector can visually clip the 0-180 sector in unexpected ways.
    This function draws the half-polar in Cartesian coordinates so the full 0-180 display range is always visible.
    """
    bsp, twa, tws, awa, vmg = [m.get(k) for k in ("bsp", "twa", "tws", "awa", "vmg")]
    fig = go.Figure()
    r_min, r_max = (y_range if y_range else (0, None))
    if r_max is None:
        candidates = []
        if bsp and bsp in df:
            candidates.append(pd.to_numeric(df[bsp], errors="coerce").max())
        if polar is not None and not polar.long.empty:
            candidates.append(polar.long["Target BSP"].max())
        r_max = float(np.nanmax(candidates)) if candidates else 10.0
    r_max = max(float(r_max), 1.0)
    r_min = float(r_min or 0.0)

    # Draw radial grid arcs for the right-hand semicircle.
    grid_rs = np.linspace(r_min, r_max, 7)
    theta_grid = np.linspace(0, 180, 181)
    for r in grid_rs:
        xg = r * np.sin(np.deg2rad(theta_grid))
        yg = r * np.cos(np.deg2rad(theta_grid))
        fig.add_trace(go.Scatter(x=xg, y=yg, mode="lines", line=dict(color="rgba(242,140,40,.22)", width=1), hoverinfo="skip", showlegend=False))
        if r > 0:
            fig.add_annotation(x=r, y=0, text=f"{r:.0f}", showarrow=False, font=dict(color="white", size=11), xanchor="left")

    # Draw angle spokes and labels.
    for ang in [0, 30, 60, 90, 120, 150, 180]:
        xs = [0, r_max * np.sin(np.deg2rad(ang))]
        ys = [0, r_max * np.cos(np.deg2rad(ang))]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color="rgba(242,140,40,.45)", width=1), hoverinfo="skip", showlegend=False))
        fig.add_annotation(x=1.04*r_max*np.sin(np.deg2rad(ang)), y=1.04*r_max*np.cos(np.deg2rad(ang)), text=str(ang), showarrow=False, font=dict(color="white", size=11))

    if bsp and twa and not df.empty:
        d = df.dropna(subset=[bsp, twa]).copy()
        d["_theta"] = signed_twa(d[twa]).abs().clip(0, 180)
        d["_r"] = pd.to_numeric(d[bsp], errors="coerce")
        d = d.dropna(subset=["_theta", "_r"])
        d = d[(d["_r"] >= r_min) & (d["_r"] <= r_max)]
        if len(d) > 12000:
            d = d.sample(12000, random_state=42)
        d["_x"] = d["_r"] * np.sin(np.deg2rad(d["_theta"]))
        d["_y"] = d["_r"] * np.cos(np.deg2rad(d["_theta"]))
        d["_vmg_hover"] = pd.to_numeric(d[vmg], errors="coerce") if vmg and vmg in d else d["_r"] * np.cos(np.deg2rad(d["_theta"]))
        d["_tws_hover"] = pd.to_numeric(d[tws], errors="coerce") if tws and tws in d else np.nan
        marker = dict(size=5, opacity=.65, color=d[tws] if tws in d else "#00a6a6", colorscale="Turbo", showscale=tws in d, colorbar=dict(title="TWS kt") if tws in d else None)
        fig.add_trace(go.Scatter(x=d["_x"], y=d["_y"], mode="markers", name="Actual", marker=marker, customdata=np.column_stack([d["_theta"], d["_r"], d["_vmg_hover"], d["_tws_hover"]]), hovertemplate="TWA: %{customdata[0]:.1f}°<br>BSP: %{customdata[1]:.2f} kt<br>VMG: %{customdata[2]:.2f} kt<br>TWS: %{customdata[3]:.2f} kt<extra></extra>"))

    if polar and target is not None:
        w = min(polar.tws, key=lambda x: abs(x-target))
        c = polar.long[polar.long.TWS == w].sort_values("TWA").copy()
        c = c[(c["Target BSP"] >= r_min) & (c["Target BSP"] <= r_max)]
        x = c["Target BSP"] * np.sin(np.deg2rad(c["TWA"]))
        y = c["Target BSP"] * np.cos(np.deg2rad(c["TWA"]))
        c["Target VMG"] = c["Target BSP"] * np.cos(np.deg2rad(c["TWA"]))
        c["Target TWS"] = float(w)
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=f"Target {w:g} kt", line=dict(color="#f28c28", width=4), hovertemplate="TWA: %{customdata[0]:.1f}°<br>Target BSP: %{customdata[1]:.2f} kt<br>Target VMG: %{customdata[2]:.2f} kt<br>TWS: %{customdata[3]:.2f} kt<extra></extra>", customdata=np.column_stack([c["TWA"], c["Target BSP"], c["Target VMG"], c["Target TWS"]])))

    fig.update_layout(template="plotly_dark", height=690, title="Actual boat speed and target polar - half polar", xaxis=dict(title="", visible=False, range=[-0.08*r_max, 1.12*r_max], scaleanchor="y", scaleratio=1), yaxis=dict(title="", visible=False, range=[-1.12*r_max, 1.12*r_max]), margin=dict(t=80,b=55), legend=dict(orientation="h", y=-.08), annotations=list(fig.layout.annotations) + [dict(x=0, y=1.18*r_max, text="0° TWA", showarrow=False, font=dict(color="white", size=12)), dict(x=0, y=-1.18*r_max, text="180° TWA", showarrow=False, font=dict(color="white", size=12)), dict(x=1.14*r_max, y=0, text="90°", showarrow=False, font=dict(color="white", size=12))])
    return fig

def polar_plot(df, m, polar, target, half, plot_space, y_range=None):
    bsp, twa, tws, awa, vmg = [m.get(k) for k in ("bsp", "twa", "tws", "awa", "vmg")]
    d = df.copy(); fig = go.Figure()
    if half and plot_space == "Polar":
        return half_polar_sailing_plot(df, m, polar, target, y_range)
    if bsp and twa and not d.empty:
        d = d.dropna(subset=[bsp, twa]).copy(); d["Angle"] = signed_twa(d[twa]); d["Plot angle"] = d.Angle.abs() if half else d.Angle
        plot_limit = int(st.session_state.get("nightjar_max_plot_points", 12000))
        if len(d) > plot_limit: d = d.sample(plot_limit, random_state=42)
        d["_vmg_hover"] = pd.to_numeric(d[vmg], errors="coerce") if vmg and vmg in d else pd.to_numeric(d[bsp], errors="coerce") * np.cos(np.deg2rad(d["Angle"]))
        d["_tws_hover"] = pd.to_numeric(d[tws], errors="coerce") if tws and tws in d else np.nan
        hover_data = np.column_stack([d["_vmg_hover"], d["_tws_hover"]])
        marker = dict(size=5, opacity=.65, color=d[tws] if tws in d else "#00a6a6", colorscale="Turbo", showscale=tws in d, colorbar=dict(title="TWS kt") if tws in d else None)
        if plot_space == "Cartesian":
            fig.add_trace(go.Scatter(x=d["Plot angle"], y=d[bsp], mode="markers", name="Actual", marker=marker, customdata=hover_data, hovertemplate="TWA: %{x:.1f}°<br>BSP: %{y:.2f} kt<br>VMG: %{customdata[0]:.2f} kt<br>TWS: %{customdata[1]:.2f} kt<extra></extra>"))
        else:
            fig.add_trace(go.Scatterpolar(r=d[bsp], theta=d["Plot angle"], mode="markers", name="Actual", marker=marker, customdata=hover_data, hovertemplate="TWA: %{theta:.1f}°<br>BSP: %{r:.2f} kt<br>VMG: %{customdata[0]:.2f} kt<br>TWS: %{customdata[1]:.2f} kt<extra></extra>"))
    if polar and target is not None:
        w = min(polar.tws, key=lambda x: abs(x-target)); c = polar.long[polar.long.TWS == w].sort_values("TWA")
        theta, r = (c.TWA, c["Target BSP"]) if half else (np.r_[-c.TWA.to_numpy()[::-1], c.TWA], np.r_[c["Target BSP"].to_numpy()[::-1], c["Target BSP"]])
        target_vmg = np.asarray(r, dtype=float) * np.cos(np.deg2rad(np.asarray(theta, dtype=float)))
        target_hover = np.column_stack([target_vmg, np.full(len(np.asarray(r)), float(w))])
        if plot_space == "Cartesian":
            fig.add_trace(go.Scatter(x=theta, y=r, mode="lines", name=f"Target {w:g} kt", line=dict(color="#f28c28", width=4), customdata=target_hover, hovertemplate="TWA: %{x:.1f}°<br>Target BSP: %{y:.2f} kt<br>Target VMG: %{customdata[0]:.2f} kt<br>TWS: %{customdata[1]:.2f} kt<extra></extra>"))
        else:
            fig.add_trace(go.Scatterpolar(r=r, theta=theta, mode="lines", name=f"Target {w:g} kt", line=dict(color="#f28c28", width=4), customdata=target_hover, hovertemplate="TWA: %{theta:.1f}°<br>Target BSP: %{r:.2f} kt<br>Target VMG: %{customdata[0]:.2f} kt<br>TWS: %{customdata[1]:.2f} kt<extra></extra>"))
    if plot_space == "Cartesian":
        fig.update_layout(template="plotly_dark", height=690, title="Actual boat speed and target polar - cartesian", xaxis_title="TWA (°)", yaxis_title="Boat speed (kt)", legend=dict(orientation="h", y=-.12))
        if half: fig.update_xaxes(range=[0,180])
        if y_range: fig.update_yaxes(range=y_range)
    else:
        pol = dict(angularaxis=dict(direction="clockwise", rotation=90), radialaxis=dict(title="Boat speed (kt)", tickfont=dict(family="Arial Black", size=14, color="white"), gridcolor="rgba(255,255,255,.5)"))
        if half: pol["sector"] = [0,180]
        if y_range: pol["radialaxis"].update(range=y_range)
        fig.update_layout(template="plotly_dark", height=690, title="Actual boat speed and target polar", polar=pol, legend=dict(orientation="h", y=-.08), margin=dict(t=80,b=55))
    return fig

def find_gun_events(events):
    """Return Expedition event rows whose Type or Comment indicate a GUN/start signal."""
    if events is None or events.empty or "Time" not in events.columns:
        return pd.DataFrame()
    df = events.copy()
    text_cols = [c for c in ["Type", "Comment"] if c in df.columns]
    if not text_cols:
        return pd.DataFrame()
    mask = pd.Series(False, index=df.index)
    for c in text_cols:
        mask |= df[c].astype(str).str.contains("gun", case=False, na=False)
    guns = df.loc[mask].copy()
    guns = guns.dropna(subset=["Time"]).sort_values("Time")
    return guns


def apply_gun_filter_for_dates(data, ts_col, events, dates):
    """For selected event dates, remove data before GUN-5min where a gun is available."""
    if not ts_col or data.empty:
        return data, []
    guns = find_gun_events(events)
    warnings = []
    if guns.empty:
        return data, ["No GUN entries were found in the Expedition events file. Please filter by time manually."]
    out_parts = []
    for dte in dates:
        day_data = data[pd.to_datetime(data[ts_col]).dt.date == dte].copy()
        day_guns = guns[pd.to_datetime(guns["Time"]).dt.date == dte]
        if day_guns.empty:
            warnings.append(f"No GUN entry found for {dte}. Please filter this event manually if required.")
            out_parts.append(day_data)
        else:
            gun_time = pd.Timestamp(day_guns.iloc[0]["Time"])
            start_time = gun_time - pd.to_timedelta(5, unit="min")
            out_parts.append(day_data[day_data[ts_col] >= start_time])
    if not out_parts:
        return data.iloc[0:0].copy(), warnings
    return pd.concat(out_parts).sort_values(ts_col), warnings


def safe_mean(df, col):
    if not col or col not in df or df.empty:
        return np.nan
    return pd.to_numeric(df[col], errors="coerce").mean()

def safe_mean_abs(df, col):
    if not col or col not in df or df.empty:
        return np.nan
    return pd.to_numeric(df[col], errors="coerce").abs().mean()


def make_event_summary(filtered, event_list, events, mapping, polar=None):
    ts, twa, tws, awa, bsp, vmg, vmg_pct = [mapping.get(k) for k in ("timestamp", "twa", "tws", "awa", "bsp", "vmg", "vmg_pct")]
    rows = []
    polar_rows = []
    gun_rows = []
    if filtered.empty or not ts:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    guns = find_gun_events(events)
    if event_list is None or event_list.empty:
        tmp = pd.DataFrame({"date": sorted(pd.to_datetime(filtered[ts]).dt.date.dropna().unique()), "event": "Selected data", "type": "Unknown"})
        event_iter = tmp.to_dict("records")
    else:
        event_iter = event_list.to_dict("records")
    polar_winds = polar.tws if polar is not None else []
    for ev in event_iter:
        dte = ev.get("date")
        name = ev.get("event", str(dte))
        sub = filtered[pd.to_datetime(filtered[ts]).dt.date == dte].copy()
        if sub.empty:
            continue
        abs_twa = signed_twa(sub[twa]).abs() if twa and twa in sub else pd.Series(index=sub.index, dtype=float)
        up = sub[abs_twa < 60]
        down = sub[abs_twa > 120]
        gun_txt = ""
        if not guns.empty:
            day_gun = guns[pd.to_datetime(guns["Time"]).dt.date == dte]
            if not day_gun.empty:
                gun_txt = pd.to_datetime(day_gun.iloc[0]["Time"]).strftime("%H:%M:%S")
                gun_rows.append({"Event": name, "Date": dte, "GUN time": gun_txt, "Type": day_gun.iloc[0].get("Type", ""), "Comment": day_gun.iloc[0].get("Comment", "")})
        uw_vmg_pct = safe_mean(up, vmg_pct)
        dw_vmg_pct = safe_mean(down, vmg_pct)
        rows.append({
            "Event": name,
            "Type": ev.get("type", "Unknown"),
            "Date": dte,
            "Samples": len(sub),
            "Avg TWS": safe_mean(sub, tws),
            "UW BSP": safe_mean(up, bsp),
            "UW VMG": safe_mean(up, vmg),
            "UW VMG%": uw_vmg_pct,
            "DW BSP": safe_mean(down, bsp),
            "DW VMG": safe_mean(down, vmg),
            "DW VMG%": dw_vmg_pct,
            "GUN": gun_txt or "Not found",
        })
        if polar_winds and tws and twa:
            for wind in polar_winds:
                band = sub[pd.to_numeric(sub[tws], errors="coerce").between(wind-1, wind+1)].copy()
                if band.empty:
                    continue
                band_abs = signed_twa(band[twa]).abs()
                for mode, mode_df in [("Upwind |TWA|<60°", band[band_abs < 60]), ("Downwind |TWA|>120°", band[band_abs > 120])]:
                    if mode_df.empty:
                        continue
                    polar_rows.append({
                        "Event": name,
                        "Polar TWS": wind,
                        "Mode": mode,
                        "Samples": len(mode_df),
                        "TWA": safe_mean(mode_df.assign(_abs_twa=signed_twa(mode_df[twa]).abs()), "_abs_twa"),
                        "AWA": safe_mean_abs(mode_df, awa),
                        "BSP": safe_mean(mode_df, bsp),
                        "VMG": safe_mean(mode_df, vmg),
                        "VMG%": safe_mean(mode_df, vmg_pct),
                    })
    return round_numeric_df(pd.DataFrame(rows)), round_numeric_df(pd.DataFrame(polar_rows)), pd.DataFrame(gun_rows)


def read_debrief_file(uploaded):
    if uploaded is None:
        return ""
    name = uploaded.name.lower()
    raw = uploaded.read()
    if name.endswith(".docx"):
        try:
            from docx import Document
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                tmp.write(raw)
                tmp_path = tmp.name
            doc = Document(tmp_path)
            return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as exc:
            return f"Could not read DOCX debrief notes: {exc}"
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")

def sail_fig(sails):
    fig = go.Figure()
    for sail, g in sails.sort_values(["sail", "order"]).groupby("sail"):
        f = g.iloc[0]; r,gc,b = f.rgb; x = g.TWA.tolist() + [g.TWA.iloc[0]]; y = g.TWS.tolist() + [g.TWS.iloc[0]]
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=sail, fill="toself", fillcolor=f"rgba({r},{gc},{b},{f.opacity})", line=dict(color=f"rgb({r},{gc},{b})", width=f.width)))
    fig.update_layout(template="plotly_dark", height=600, title="Sail crossover chart", xaxis_title="TWA (°)", yaxis_title="TWS (kt)", legend=dict(orientation="h", y=-.12)); return fig

def _password_config():
    """Return the configured SHA-256 password digest without exposing the secret."""
    try:
        configured_hash = str(st.secrets.get("APP_PASSWORD_SHA256", "")).strip().lower()
        configured_plain = str(st.secrets.get("APP_PASSWORD", ""))
    except Exception:
        configured_hash, configured_plain = "", ""
    configured_hash = configured_hash or os.environ.get("NIGHTJAR_APP_PASSWORD_SHA256", "").strip().lower()
    configured_plain = configured_plain or os.environ.get("NIGHTJAR_APP_PASSWORD", "")
    if configured_hash:
        return configured_hash
    if configured_plain:
        return hashlib.sha256(configured_plain.encode("utf-8")).hexdigest()
    return ""


def require_password():
    """Render a session-scoped password gate and return True after sign-in."""
    if st.session_state.get("nightjar_authenticated", False):
        return True
    expected_hash = _password_config()
    st.title(APP_TITLE)
    st.caption(f"Version {APP_VERSION} · Authorised access only")
    if not expected_hash:
        st.error("App password is not configured. Add APP_PASSWORD_SHA256 (recommended) or APP_PASSWORD to Streamlit secrets, then restart the app.")
        return False
    with st.form("nightjar_login", clear_on_submit=True):
        entered = st.text_input("Password", type="password", placeholder="Enter the app password")
        submitted = st.form_submit_button("Sign in", type="primary")
    if submitted:
        entered_hash = hashlib.sha256(entered.encode("utf-8")).hexdigest()
        if hmac.compare_digest(entered_hash, expected_hash):
            st.session_state["nightjar_authenticated"] = True
            st.session_state.pop("nightjar_login_failed", None)
            st.rerun()
        else:
            st.session_state["nightjar_login_failed"] = True
    if st.session_state.get("nightjar_login_failed"):
        st.error("Incorrect password.")
    return False


def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="🧭", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    if not require_password():
        st.stop()
    st.sidebar.markdown(
        f"<div class='nightjar-side-title'>{APP_TITLE}</div>"
        f"<div class='nightjar-side-caption'>Archambault A31 racing yacht performance review<br>Version {APP_VERSION}</div>",
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Sign out", key="nightjar_sign_out"):
        st.session_state["nightjar_authenticated"] = False
        st.rerun()
    logo = DATA_DIR / DEFAULT_FILES["logo"]
    if logo.exists(): st.sidebar.image(str(logo), width="stretch")
    st.sidebar.header("Input files")
    defs = [("log","Expedition log",["csv","txt"]),("polar","Target polar",["txt","csv","pol"]),("events","Expedition events",["csv","txt"]),("event_list","Event list",["txt","csv"]),("tests","Expedition tests",["csv"]),("sail_chart","Sail selection chart",["xml"]),("debrief","Debrief notes",["txt","md","docx"])]
    ups = {k: st.sidebar.file_uploader(n, type=t, key=f"file_{k}") for k,n,t in defs}; src = {k: (v if k == "debrief" else local(v,k)) for k,v in ups.items()}
    if not src["log"]: st.info("Upload a log or place the reference files in the data folder beside app_0.7.4.py"); st.stop()
    try: df = load_log_fast(src["log"])
    except Exception as e: st.error(f"Could not read log: {e}"); st.stop()
    events = load_events_fast(src["events"])
    event_list = load_event_list_fast(src["event_list"])
    polar = load_polar_fast(src["polar"])
    df = ensure_vmg_pct(df, polar)
    m = detect_columns(df)
    st.sidebar.subheader("Column mapping")
    for k in ("timestamp","bsp","twa","tws","awa","vmg","vmg_pct","heel","drift","lat","lon"):
        opts = [None] + list(df.columns); cur = m.get(k)
        m[k] = st.sidebar.selectbox(k.upper(), opts, index=opts.index(cur) if cur in opts else 0, format_func=lambda x:"Not mapped" if x is None else str(x), key=f"map_{k}")
    ts,bsp,twa,tws,vmg,vmg_pct,heel,drift,awa = [m.get(k) for k in ("timestamp","bsp","twa","tws","vmg","vmg_pct","heel","drift","awa")]
    filtered = df.copy()
    selected_events = []
    selected_event_dates = []
    performance_mode = True
    max_plot_points = 10000
    if ts and pd.api.types.is_datetime64_any_dtype(filtered[ts]):
        good = filtered[ts].dropna()
        if not good.empty:
            st.sidebar.subheader("Event, date and time filter")
            with st.sidebar.form("nightjar_filter_form"):
                performance_mode = st.checkbox("Performance mode", value=True, key="perf_mode")
                max_plot_points = st.number_input("Maximum plotted points", min_value=1000, max_value=50000, value=10000, step=1000, key="max_plot_points")
                filtered_event_list = event_list.copy()
                if not filtered_event_list.empty and "type" in filtered_event_list.columns:
                    event_types = sorted([x for x in filtered_event_list["type"].dropna().unique().tolist() if x])
                    selected_types = st.multiselect("Event type", event_types, default=event_types, key="side_event_type_filter")
                    if selected_types:
                        filtered_event_list = filtered_event_list[filtered_event_list["type"].isin(selected_types)]
                if not filtered_event_list.empty:
                    event_options = filtered_event_list["event"].tolist()
                    selected_events = st.multiselect("Events", event_options, default=event_options[:1], key="side_event_multiselect")
                else:
                    selected_events = []
                if not selected_events:
                    dates = st.date_input("Date range", value=(good.min().date(), good.max().date()), min_value=good.min().date(), max_value=good.max().date(), key="side_date_range")
                else:
                    dates = None
                start_t = st.time_input("Start time", value=good.min().time().replace(microsecond=0), key="side_start_time")
                end_t = st.time_input("End time", value=good.max().time().replace(microsecond=0), key="side_end_time")
                st.form_submit_button("Apply filters")

            if selected_events:
                selected_rows = filtered_event_list[filtered_event_list["event"].isin(selected_events)]
                selected_event_dates = selected_rows["date"].tolist()
                filtered = filtered[pd.to_datetime(filtered[ts]).dt.date.isin(selected_event_dates)]
                filtered, gun_warnings = apply_gun_filter_for_dates(filtered, ts, events, selected_event_dates)
                for msg in gun_warnings:
                    st.sidebar.warning(msg)
                t = pd.to_datetime(filtered[ts]).dt.time
                filtered = filtered[(t >= start_t) & (t <= end_t)]
            else:
                if isinstance(dates, tuple) and len(dates) == 2:
                    start = pd.Timestamp.combine(dates[0], start_t); end = pd.Timestamp.combine(dates[1], end_t)
                    if end < start: st.sidebar.warning("End time is before start time; no time filter applied.")
                    else: filtered = filtered[filtered[ts].between(start,end)]
    st.session_state["nightjar_max_plot_points"] = int(max_plot_points)
    st.session_state["nightjar_performance_mode"] = bool(performance_mode)
    debrief_text = read_debrief_file(src.get("debrief"))
    ov,summary,po,gps,var,files = st.tabs(["Overview","Event summary","Polar analysis","GPS track","Variable plot","Files and sail chart"])
    with ov:
        ms = st.columns(5); ms[0].metric("Rows", f"{len(filtered):,}"); ms[1].metric("Mean BSP", f"{filtered[bsp].mean():.2f} kt" if bsp else "n/a"); ms[2].metric("Mean TWS", f"{filtered[tws].mean():.1f} kt" if tws else "n/a"); ms[3].metric("Mean VMG", f"{filtered[vmg].mean():.2f} kt" if vmg else "n/a"); ms[4].metric("Channels", len(df.columns))
        if ts:
            cols = [c for c in (bsp,tws,vmg,vmg_pct,heel,twa) if c]
            if cols:
                overview_plot_df = downsample_rows(filtered, max_plot_points) if performance_mode else filtered
                long = overview_plot_df[[ts]+cols].melt(ts, var_name="Channel", value_name="Value").dropna(); fig = px.line(long, x=ts, y="Value", color="Channel", title="Selected time series including VMG and TWA"); fig.update_layout(template="plotly_dark", height=430); st.plotly_chart(fig, width="stretch")
        st.dataframe(round_numeric_df(filtered.head(500)), width="stretch", height=310)
    with summary:
        st.subheader("Event summary")
        summary_df, polar_summary_df, gun_df = make_event_summary(filtered, event_list if selected_events else pd.DataFrame(), events, m, polar)
        if summary_df.empty:
            st.info("No event summary is available for the currently selected data.")
        else:
            st.caption("Note: Upwind values use records with |TWA| < 60°. Downwind values use records with |TWA| > 120°. Reaching data from 60° to 120° TWA is excluded from the upwind/downwind BSP, VMG and VMG% values.")
            st.dataframe(round_numeric_df(summary_df), width="stretch", hide_index=True)
        st.subheader("Performance by polar windspeed")
        if polar_summary_df.empty:
            st.info("No polar windspeed summary is available. Check that TWS, TWA and the polar file are mapped/loaded.")
        else:
            st.dataframe(round_numeric_df(polar_summary_df.sort_values(["Event", "Polar TWS", "Mode"])), width="stretch", hide_index=True)
        st.subheader("Start / GUN information")
        if gun_df.empty:
            st.warning("No GUN entries were found in the Expedition events file for the selected events. Filter by time manually if required.")
        else:
            st.dataframe(gun_df, width="stretch", hide_index=True)
        st.subheader("Debrief notes")
        if debrief_text:
            st.text_area("Debrief notes", debrief_text, height=320, key="debrief_notes_view")
        else:
            st.info("Upload a .txt, .md or .docx debrief notes file in the sidebar to view it here.")

    with po:
        c1,c2,c3,c4 = st.columns(4)
        with c1: point = st.radio("Point of sail", ["All","Upwind (0 to 90°)","Downwind (90 to 180°)"], key="polar_point")
        with c2: layout = st.radio("Polar layout", ["Full polar","Half polar (absolute TWA)"], key="polar_layout")
        with c3: plot_space = st.radio("Plot space", ["Polar","Cartesian"], key="polar_space")
        target = None
        if polar:
            default = min(polar.tws, key=lambda x: abs(x-(float(filtered[tws].median()) if tws else 10)))
            with c4: target = st.select_slider("Target polar TWS / bin centre", options=polar.tws, value=default, key="polar_target_tws")
        p1,p2,p3,p4 = st.columns(4)
        with p1: tol = st.number_input("TWS bin tolerance ± (kt)", min_value=.1, value=1.0, step=.1, disabled=not bool(tws and polar), key="polar_tws_tol")
        with p2: use_all = st.checkbox("Show all wind speeds", value=False, key="polar_show_all_winds")
        with p3: yr_min = st.number_input("Y / radial min", value=0.0, step=.5, key="polar_ymin")
        with p4: yr_max = st.number_input("Y / radial max", value=12.0, step=.5, key="polar_ymax")
        a1,a2,a3 = st.columns(3)
        with a1: avg_sec = st.number_input("Time averaging window (s)", min_value=1, value=1, step=1, key="polar_avg_sec")
        with a2: max_tws_var = st.number_input("Max TWS variation in window", min_value=0.0, value=99.0, step=.5, key="polar_tws_var")
        with a3: max_bsp_var = st.number_input("Max BSP variation in window", min_value=0.0, value=99.0, step=.5, key="polar_bsp_var")
        local_data = point_filter(filtered, twa, point)
        if tws and polar and not use_all: local_data = local_data[local_data[tws].between(target-tol, target+tol)]
        avg_cols = [c for c in [bsp,twa,tws,awa,vmg,vmg_pct,heel,drift,m.get("lat"),m.get("lon")] if c]
        local_data, avg_note = average_with_ranges(local_data, ts, avg_cols, int(avg_sec), {tws:max_tws_var,bsp:max_bsp_var}, signed_twa_col=twa)
        st.session_state["nightjar_avg_settings"] = {"seconds":int(avg_sec), "max_tws":max_tws_var, "max_bsp":max_bsp_var}
        st.caption(f"Plotting {len(local_data):,} records | {avg_note}. Half polar uses 0° to 180°.")
        if bsp and twa: st.plotly_chart(polar_plot(local_data, m, polar, target, layout.startswith("Half"), plot_space, (yr_min,yr_max)), width="stretch")
    with gps:
        lat, lon = m.get("lat"), m.get("lon")
        if lat and lon and filtered[[lat, lon]].dropna().shape[0] > 1:
            settings = st.session_state.get("nightjar_avg_settings", {"seconds": 1, "max_tws": 99.0, "max_bsp": 99.0})
            gps_cols = filtered.select_dtypes(include=np.number).columns.tolist()
            gps_base, avg_note = average_with_ranges(
                filtered,
                ts,
                [lat, lon] + gps_cols,
                int(settings["seconds"]),
                {tws: settings["max_tws"], bsp: settings["max_bsp"]},
                signed_twa_col=twa,
            )
            d = gps_base.dropna(subset=[lat, lon]).copy()
            if ts and ts in d:
                d["Time"] = pd.to_datetime(d[ts], errors="coerce").dt.round("s").dt.strftime("%d-%b-%Y %H:%M:%S")
            if len(d) > 10000:
                d = d.iloc[::math.ceil(len(d) / 10000)]

            nums = d.select_dtypes(include=np.number).columns.tolist()
            default_colour = vmg if vmg in nums else (bsp if bsp in nums else (nums[0] if nums else None))
            if not nums:
                st.warning("No numeric channels are available to colour the GPS track.")
                st.stop()

            g1, g2, g3, g4 = st.columns(4)
            with g1:
                colour = st.selectbox("Colour track by", nums, index=nums.index(default_colour) if default_colour in nums else 0, key="gps_colour_by")
            with g2:
                abs_colour = st.checkbox("Use absolute colour values", key="gps_abs_colour_values")
            colour_plot = f"abs({colour})" if abs_colour else colour
            if abs_colour:
                d[colour_plot] = d[colour].abs()
            vals = pd.to_numeric(d[colour_plot], errors="coerce").dropna() if colour_plot in d else pd.Series(dtype=float)
            if "gps_colour_last_field" not in st.session_state or st.session_state["gps_colour_last_field"] != colour_plot:
                st.session_state["gps_colour_last_field"] = colour_plot
                st.session_state["gps_colour_min"] = float(vals.quantile(.02)) if not vals.empty else 0.0
                st.session_state["gps_colour_max"] = float(vals.quantile(.98)) if not vals.empty else 1.0
            if st.button("Auto scale GPS colour to plotted data", key="gps_auto_colour_scale"):
                st.session_state["gps_colour_min"] = float(vals.min()) if not vals.empty else 0.0
                st.session_state["gps_colour_max"] = float(vals.max()) if not vals.empty else 1.0
            if st.session_state.get("gps_colour_max", 1.0) <= st.session_state.get("gps_colour_min", 0.0):
                st.session_state["gps_colour_max"] = st.session_state.get("gps_colour_min", 0.0) + 0.001
            with g3:
                cmin = st.number_input("Colour scale min", key="gps_colour_min")
            with g4:
                cmax = st.number_input("Colour scale max", key="gps_colour_max")

            hover_cols = [c for c in ("Time" if ts else None, twa, tws, awa, heel, vmg, vmg_pct, drift, bsp) if c and c in d]
            hover_text = []
            for _, row in d.iterrows():
                parts = []
                for col in hover_cols:
                    val = row[col]
                    if isinstance(val, (float, np.floating)):
                        parts.append(f"{col}: {val:.2f}")
                    else:
                        parts.append(f"{col}: {val}")
                hover_text.append("<br>".join(parts))

            centre = {"lat": float(d[lat].mean()), "lon": float(d[lon].mean())}

            # Use pure graph_objects Scattermapbox for both the line and points.
            # This deliberately avoids Plotly Express map figures and avoids copying any mapbox layout object,
            # because copied mapbox layout objects were causing the browser-side 'No valid mapbox style found' error.
            fig = go.Figure()
            fig.add_trace(go.Scattermap(
                lat=d[lat],
                lon=d[lon],
                mode="lines",
                name="Track line",
                line=dict(color="rgba(242,140,40,0.58)", width=2),
                hoverinfo="skip",
            ))
            fig.add_trace(go.Scattermap(
                lat=d[lat],
                lon=d[lon],
                mode="markers",
                name=colour_plot,
                text=hover_text,
                hovertemplate="%{text}<extra></extra>",
                marker=dict(
                    size=8,
                    color=d[colour_plot],
                    colorscale="Turbo",
                    cmin=cmin,
                    cmax=cmax,
                    colorbar=dict(title=colour_plot),
                    opacity=0.82,
                ),
            ))
            fig.update_layout(
                map=dict(
                    style="open-street-map",
                    center=centre,
                    zoom=10,
                ),
                template="plotly_dark",
                height=675,
                margin=dict(l=0, r=0, t=35, b=0),
                title=f"GPS track coloured by {colour_plot} ({avg_note})",
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Latitude and longitude are not available")
        if not events.empty:
            st.dataframe(round_numeric_df(events), width="stretch", height=240)

    with var:
        nums = filtered.select_dtypes(include=np.number).columns.tolist()
        if len(nums) < 2: st.info("At least two numeric variables are required")
        else:
            v1,v2,v3,v4 = st.columns(4)
            with v1: x = st.selectbox("Angular / X variable", nums, index=nums.index(twa) if twa in nums else 0, key="var_x"); absx = st.checkbox("Use absolute X values", key="var_abs_x_values")
            with v2: y = st.selectbox("Radial / Y variable", nums, index=nums.index(bsp) if bsp in nums else min(1,len(nums)-1), key="var_y"); absy = st.checkbox("Use absolute Y values", key="var_abs_y_values")
            with v3: colour = st.selectbox("Colour", ["None"]+nums, index=(["None"]+nums).index(tws) if tws in nums else 0, key="var_colour"); absc = st.checkbox("Use absolute colour values", key="var_abs_colour_values")
            with v4: kind = st.radio("Plot type", ["Cartesian","Polar"], key="var_plot_type")
            w1,w2,w3,w4 = st.columns(4)
            with w1: vavg = st.number_input("Variable time average (s)", min_value=1, value=1, step=1, key="var_avg_sec")
            with w2: x_tol = st.number_input("Max X variation in window", min_value=0.0, value=99.0, step=.5, key="var_x_tol")
            with w3: y_tol = st.number_input("Max Y variation in window", min_value=0.0, value=99.0, step=.5, key="var_y_tol")
            with w4: c_tol = st.number_input("Max colour variation in window", min_value=0.0, value=99.0, step=.5, disabled=colour=="None", key="var_colour_tol")
            avg_columns = [x,y] + ([] if colour=="None" else [colour]) + ([tws] if tws else [])
            tolerances = {x:x_tol, y:y_tol}
            if colour != "None": tolerances[colour] = c_tol
            vd, avg_note = average_with_ranges(filtered, ts, avg_columns, int(vavg), tolerances, signed_twa_col=x if x==twa else None)
            xn = f"abs({x})" if absx else x; yn = f"abs({y})" if absy else y; cn = f"abs({colour})" if absc and colour!="None" else colour
            if absx: vd[xn] = vd[x].abs()
            if absy: vd[yn] = vd[y].abs()
            if colour != "None" and absc: vd[cn] = vd[colour].abs()
            cl1,cl2 = st.columns(2); colour_range = None
            if colour != "None":
                vals = pd.to_numeric(vd[cn], errors="coerce").dropna()
                if "var_colour_last_field" not in st.session_state or st.session_state["var_colour_last_field"] != cn:
                    st.session_state["var_colour_last_field"] = cn
                    st.session_state["var_colour_min"] = float(vals.quantile(.02)) if not vals.empty else 0.0
                    st.session_state["var_colour_max"] = float(vals.quantile(.98)) if not vals.empty else 1.0
                if st.button("Auto scale variable colour to plotted data", key="var_auto_colour_scale"):
                    st.session_state["var_colour_min"] = float(vals.min()) if not vals.empty else 0.0
                    st.session_state["var_colour_max"] = float(vals.max()) if not vals.empty else 1.0
                if st.session_state.get("var_colour_max", 1.0) <= st.session_state.get("var_colour_min", 0.0):
                    st.session_state["var_colour_max"] = st.session_state.get("var_colour_min", 0.0) + 0.001
                with cl1: vmin = st.number_input("Variable colour scale min", key="var_colour_min")
                with cl2: vmax = st.number_input("Variable colour scale max", key="var_colour_max")
                colour_range = (vmin,vmax)
            if tws and tws in vd:
                q1,q2,q3 = st.columns(3)
                with q1: usebin = st.checkbox("Filter variable plot by TWS bin", key="var_tws_bin_enable")
                with q2: center = st.number_input("Variable plot TWS centre", value=float(vd[tws].median()), step=.5, disabled=not usebin, key="var_tws_center")
                with q3: tolerance = st.number_input("Variable plot tolerance ±", min_value=.1, value=1.0, step=.1, disabled=not usebin, key="var_tws_tolerance")
                if usebin: vd = vd[vd[tws].between(center-tolerance, center+tolerance)]
            needed = [xn,yn] + ([] if colour=="None" else [cn]); vd = vd.dropna(subset=needed)
            if performance_mode and len(vd) > max_plot_points: vd = vd.sample(max_plot_points, random_state=42)
            if kind == "Cartesian": fig = px.scatter(vd, x=xn, y=yn, color=None if colour=="None" else cn, opacity=.62, color_continuous_scale="Turbo", range_color=colour_range)
            else:
                marker = dict(size=6, opacity=.62, color=vd[cn] if colour!="None" else "#00a6a6", colorscale="Turbo", showscale=colour!="None", colorbar=dict(title=cn) if colour!="None" else None)
                if colour_range: marker.update(cmin=colour_range[0], cmax=colour_range[1])
                fig = go.Figure(go.Scatterpolar(theta=vd[xn], r=vd[yn], mode="markers", marker=marker, hovertemplate=f"{xn}: %{{theta:.2f}}<br>{yn}: %{{r:.2f}}<extra></extra>")); fig.update_layout(polar=dict(angularaxis=dict(direction="clockwise", rotation=90)))
            fig.update_layout(template="plotly_dark", height=635, title=f"{yn} against {xn} ({avg_note})"); st.plotly_chart(fig, width="stretch"); st.caption(f"Displaying {len(vd):,} records")
    with files:
        if src["sail_chart"]:
            try: sails = load_sails_fast(src["sail_chart"]); st.plotly_chart(sail_fig(sails), width="stretch"); st.dataframe(round_numeric_df(sails), width="stretch", height=270)
            except Exception as e: st.warning(f"Sail chart could not be parsed: {e}")
        st.download_button("Download filtered log CSV", round_numeric_df(filtered).to_csv(index=False).encode(), "nightjar_filtered_log_0.7.4.csv", "text/csv", key="download_filtered")
        session = {"version":APP_VERSION, "created_utc":datetime.now(UTC).isoformat().replace("+00:00", "Z"), "rows":len(filtered), "mapping":m}
        st.download_button("Download session settings", json.dumps(session,indent=2).encode(), "nightjar_session_0.7.4.json", "application/json", key="download_session")
if __name__ == "__main__": main()
