from __future__ import annotations
import csv, gc, hashlib, hmac, io, json, math, os, re
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

APP_TITLE, APP_VERSION = "Nightjar Data Analysis", "0.7.8.1"
DEFAULT_FILES = {
    "log":"logfile.csv",
    "polar":"Polar.txt",
    "events":"EventData.csv",
    "event_list":"EventList.txt",
    "tests":"TestData.csv",
    "sail_chart":"SailChart.xml",
    "logo":"Logo.jpg",
}

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path("/Data")
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


def dataframe_memory_mb(df):
    """Deep DataFrame footprint in MiB, without copying its data."""
    if df is None: return 0.0
    return float(df.memory_usage(index=True, deep=True).sum()) / (1024.0 * 1024.0)


def optimise_dtypes(df):
    """Reduce memory in place; do not duplicate the full log."""
    if df is None or df.empty: return df
    for c in list(df.select_dtypes(include=["float64"]).columns):
        df[c] = pd.to_numeric(df[c], downcast="float")
    for c in list(df.select_dtypes(include=["int64", "int32"]).columns):
        df[c] = pd.to_numeric(df[c], downcast="integer")
    for c in ("Boat", "Sail"):
        if c in df.columns:
            try: df[c] = df[c].astype("category")
            except Exception: pass
    return df


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
    return p.with_name(f".{safe}_{stat.st_size}_{stat.st_mtime_ns}_nightjar_077.parquet")


@st.cache_data(show_spinner=False, max_entries=8)
def parse_events_cached(raw): return parse_events(io.BytesIO(raw))

@st.cache_data(show_spinner=False, max_entries=8)
def parse_event_list_cached(raw): return parse_event_list(io.BytesIO(raw))

@st.cache_data(show_spinner=False, max_entries=8)
def parse_polar_cached(raw): return parse_polar(io.BytesIO(raw))

@st.cache_data(show_spinner=False, max_entries=8)
def parse_sails_cached(raw): return parse_sails(io.BytesIO(raw))


@st.cache_resource(show_spinner=False, max_entries=1)
def load_local_log_resource(path_string, file_size, modified_ns):
    """Hold one shared local log between reruns, without cache_data copies."""
    p = Path(path_string); cache = local_cache_path_for(p)
    if cache.exists() and cache.stat().st_mtime_ns >= modified_ns:
        try: return optimise_dtypes(pd.read_parquet(cache))
        except Exception: pass
    df = optimise_dtypes(parse_log(p))
    # Arrow conversion can spike RAM, so only write modest caches by default.
    max_cache_mb = float(os.environ.get("NIGHTJAR_PARQUET_CACHE_MAX_MB", "0"))
    if dataframe_memory_mb(df) <= max_cache_mb:
        try: df.to_parquet(cache, index=False, compression="zstd")
        except Exception: pass
    gc.collect(); return df


def load_log_fast(src):
    """Load a local log once; parse uploads directly without copying bytes."""
    if isinstance(src, (str, Path)):
        p=Path(src); stat=p.stat()
        return load_local_log_resource(str(p.resolve()), stat.st_size, stat.st_mtime_ns)
    try: src.seek(0)
    except Exception: pass
    return optimise_dtypes(parse_log(src))


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
    """Add float32 VMG in place, without copying the full frame."""
    if df is None or df.empty: return df
    mapping=detect_columns(df)
    if mapping.get("vmg"): return df
    bsp_col,twa_col=mapping.get("bsp"),mapping.get("twa")
    if not bsp_col or not twa_col: return df
    bsp=pd.to_numeric(df[bsp_col],errors="coerce").to_numpy(dtype=np.float32,copy=False)
    twa=pd.to_numeric(df[twa_col],errors="coerce").to_numpy(dtype=np.float32,copy=False)
    twa=((twa+np.float32(180.0))%np.float32(360.0))-np.float32(180.0)
    df["VMG"]=(bsp*np.cos(np.deg2rad(twa))).astype(np.float32,copy=False)
    return df


def excel_dt(s):
    """Convert timestamps with one full conversion array, not two."""
    sample=s.dropna().head(200)
    numeric_sample=pd.to_numeric(sample,errors="coerce").to_numpy(dtype=float,na_value=np.nan)
    if len(sample) and np.isfinite(numeric_sample).mean() >= 0.8:
        return pd.Timestamp("1899-12-30") + pd.to_timedelta(pd.to_numeric(s,errors="coerce"),unit="D")
    return pd.to_datetime(s,errors="coerce",dayfirst=True)


def _process_log_chunk(df):
    """Normalise one bounded log chunk without retaining parser temporaries."""
    if df is None or df.empty:
        return pd.DataFrame()
    if "Boat" in df.columns:
        boat = df["Boat"].astype(str).str.strip().eq("0")
        if not boat.all():
            df = df.loc[boat].copy()
        del boat
    if df.empty:
        return df
    mapping = detect_columns(df)
    timestamp = mapping.get("timestamp")
    if timestamp:
        df[timestamp] = excel_dt(df[timestamp])
    for column in list(df.columns):
        dtype = df[column].dtype
        if column == timestamp or not (
            pd.api.types.is_object_dtype(dtype)
            or pd.api.types.is_string_dtype(dtype)
        ):
            continue
        sample = df[column].dropna().head(500)
        numeric_sample = pd.to_numeric(sample, errors="coerce").to_numpy(
            dtype=float, na_value=np.nan
        )
        if not sample.empty and np.isfinite(numeric_sample).mean() >= 0.8:
            df[column] = pd.to_numeric(df[column], errors="coerce", downcast="float")
    optimise_dtypes(df)
    ensure_vmg(df)
    df.index = pd.RangeIndex(len(df))
    return df


def _rss_mb():
    """Return current resident memory on Linux, without requiring psutil."""
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        pages = int(Path("/proc/self/statm").read_text().split()[1])
        return pages * page_size / (1024.0 * 1024.0)
    except Exception:
        return 0.0


class _BoundedLogCollector:
    """Collect sequential chunks and thin uniformly before RAM becomes unsafe.

    The app's interactive views require a pandas DataFrame. When the complete
    log cannot safely fit, retained records are deterministically decimated
    across the whole timeline. This preserves date/time coverage while keeping
    the resident process below the configured Railway memory ceiling.
    """
    def __init__(self):
        self.limit_mb = float(os.environ.get("NIGHTJAR_MEMORY_LIMIT_MB", "750"))
        self.frame_budget_mb = float(os.environ.get("NIGHTJAR_LOG_FRAME_BUDGET_MB", "140"))
        self.headroom_mb = float(os.environ.get("NIGHTJAR_MEMORY_HEADROOM_MB", "180"))
        self.chunks = []
        self.input_rows = 0
        self.stride = 1

    def _stored_mb(self):
        return sum(dataframe_memory_mb(c) for c in self.chunks)

    def _thin_once(self):
        thinned = []
        for chunk in self.chunks:
            if not chunk.empty:
                smaller = chunk.iloc[::2].copy()
                optimise_dtypes(smaller)
                thinned.append(smaller)
            del chunk
        self.chunks = thinned
        self.stride *= 2
        gc.collect()

    def add(self, chunk):
        if chunk is None or chunk.empty:
            return
        chunk = _process_log_chunk(chunk)
        source_rows = len(chunk)
        if not source_rows:
            return
        start_row = self.input_rows
        self.input_rows += source_rows
        # Select against a global row number so chunk boundaries do not bias
        # the retained timeline.
        offset = (-start_row) % self.stride
        kept = chunk.iloc[offset::self.stride].copy()
        del chunk
        if not kept.empty:
            optimise_dtypes(kept)
            self.chunks.append(kept)
        while self.chunks and (
            self._stored_mb() > self.frame_budget_mb
            or (_rss_mb() and _rss_mb() > self.limit_mb - self.headroom_mb)
        ):
            self._thin_once()

    def finish(self):
        if not self.chunks:
            raise ValueError("The log file is empty")
        # Leave room for concat to allocate its output alongside the chunks.
        while self._stored_mb() > self.frame_budget_mb * 0.72:
            self._thin_once()
        df = pd.concat(self.chunks, ignore_index=True, sort=False, copy=False)
        self.chunks.clear()
        optimise_dtypes(df)
        mapping = detect_columns(df)
        timestamp = mapping.get("timestamp")
        if timestamp and not df[timestamp].is_monotonic_increasing:
            df.sort_values(timestamp, inplace=True, kind="stable", ignore_index=True)
        ensure_vmg(df)
        df.attrs["nightjar_source_rows"] = int(self.input_rows)
        df.attrs["nightjar_retained_rows"] = int(len(df))
        df.attrs["nightjar_sampling_stride"] = int(self.stride)
        df.attrs["nightjar_memory_budget_mb"] = float(self.frame_budget_mb)
        gc.collect()
        return df


def _text_stream(src):
    """Open a text CSV stream and report whether this function must close it."""
    if isinstance(src, (str, Path)):
        return Path(src).open("r", encoding="utf-8-sig", errors="replace", newline=""), True
    try:
        src.seek(0)
    except Exception:
        pass
    if isinstance(src, io.TextIOBase):
        return src, False
    return io.TextIOWrapper(src, encoding="utf-8-sig", errors="replace", newline=""), False


def parse_sparse_stream(src, chunk_rows=None):
    """Parse a multi-section sparse Expedition log one bounded block at a time."""
    chunk_rows = max(5000, int(chunk_rows or os.environ.get("NIGHTJAR_LOG_CHUNK_ROWS", "25000")))
    collector = _BoundedLogCollector()
    handle, close_handle = _text_stream(src)
    reader = csv.reader(handle)
    names = None
    lookup = {}
    records = []
    try:
        for fields in reader:
            if not fields or not any(str(v).strip() for v in fields):
                continue
            first = fields[0].strip().casefold()
            second = fields[1].strip() if len(fields) > 1 else ""
            if first == "!boat" and second.casefold() == "utc":
                names = fields
                lookup = {}
                continue
            if first == "!boat" and second.lstrip("+-").isdigit():
                if names and len(names) == len(fields):
                    lookup = {
                        channel_id.strip(): name.lstrip("!").strip()
                        for name, channel_id in zip(names, fields)
                        if channel_id.strip().lstrip("+-").isdigit()
                    }
                continue
            if fields[0].lstrip().startswith("!") or len(fields) < 2:
                continue
            row = {"Boat": fields[0], "Utc": fields[1]}
            for pos in range(2, len(fields) - 1, 2):
                channel = lookup.get(fields[pos].strip())
                if channel:
                    row[channel] = fields[pos + 1].strip()
            records.append(row)
            if len(records) >= chunk_rows:
                collector.add(pd.DataFrame.from_records(records))
                records.clear()
        if records:
            collector.add(pd.DataFrame.from_records(records))
            records.clear()
    finally:
        if close_handle:
            handle.close()
        elif isinstance(handle, io.TextIOWrapper):
            # Keep an uploaded binary object open for Streamlit reruns.
            try:
                handle.detach()
            except Exception:
                pass
    return collector.finish()


def _source_prefix(src, size=65536):
    if isinstance(src, (str, Path)):
        with Path(src).open("rb") as handle:
            return handle.read(size)
    try:
        position = src.tell()
    except Exception:
        position = 0
    try:
        src.seek(0)
        prefix = src.read(size)
    finally:
        try:
            src.seek(position)
        except Exception:
            pass
    return prefix.encode("utf-8", errors="replace") if isinstance(prefix, str) else prefix


def _is_sparse_log(src):
    prefix = _source_prefix(src)
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            preview = prefix.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    lines = [line for line in preview.splitlines() if line.strip()][:2]
    return len(lines) == 2 and lines[0].startswith("!") and lines[1].lower().startswith("!boat")


def parse_standard_stream(src, chunk_rows=None):
    """Read a conventional CSV sequentially and retain a RAM-bounded frame."""
    chunk_rows = max(5000, int(chunk_rows or os.environ.get("NIGHTJAR_LOG_CHUNK_ROWS", "25000")))
    collector = _BoundedLogCollector()
    kwargs = dict(chunksize=chunk_rows, low_memory=True, on_bad_lines="warn")
    if isinstance(src, (str, Path)):
        kwargs["memory_map"] = True
    try:
        iterator = pd.read_csv(src, dtype_backend="pyarrow", **kwargs)
    except (TypeError, ImportError, ValueError):
        try:
            src.seek(0)
        except Exception:
            pass
        iterator = pd.read_csv(src, **kwargs)
    for chunk in iterator:
        collector.add(chunk)
    return collector.finish()


def parse_log(src):
    """Sequential, memory-bounded log loader used by Nightjar 0.7.7."""
    if _is_sparse_log(src):
        return parse_sparse_stream(src)
    try:
        if not isinstance(src, (str, Path)):
            src.seek(0)
    except Exception:
        pass
    return parse_standard_stream(src)


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
    """Create/fill float32 VMG_PCT in bounded blocks, in place."""
    if df is None or df.empty or polar is None: return df
    mapping=detect_columns(df); vmg_col,tws_col,twa_col=mapping.get("vmg"),mapping.get("tws"),mapping.get("twa")
    if not vmg_col or not tws_col or not twa_col: return df
    existing_col=mapping.get("vmg_pct")
    if existing_col and existing_col in df.columns:
        output=pd.to_numeric(df[existing_col],errors="coerce").to_numpy(dtype=np.float32,na_value=np.nan,copy=True)
    else:
        existing_col="VMG_PCT"; output=np.full(len(df),np.nan,dtype=np.float32)
    block_rows=max(10000,int(os.environ.get("NIGHTJAR_CALC_BLOCK_ROWS","50000")))
    for row_start in range(0,len(df),block_rows):
        row_stop=min(row_start+block_rows,len(df)); missing=~np.isfinite(output[row_start:row_stop])
        if not missing.any(): continue
        block=df.iloc[row_start:row_stop]
        actual=pd.to_numeric(block[vmg_col],errors="coerce").to_numpy(dtype=np.float32,copy=False)
        twa=pd.to_numeric(block[twa_col],errors="coerce").to_numpy(dtype=np.float32,copy=False)
        target_bsp=target_bsp_from_polar(polar,block[tws_col],block[twa_col]).to_numpy(dtype=np.float32,copy=False)
        twa_abs=np.abs(((twa+180.0)%360.0)-180.0); denominator=np.abs(target_bsp*np.cos(np.deg2rad(twa_abs)))
        calculated=np.full(len(block),np.nan,dtype=np.float32)
        valid=np.isfinite(actual)&np.isfinite(denominator)&(denominator>=0.05)
        calculated[valid]=np.abs(actual[valid])/denominator[valid]*100.0
        output[row_start:row_stop][missing]=calculated[missing]
        del block,actual,twa,target_bsp,twa_abs,denominator,calculated,valid
    df[existing_col]=output; gc.collect(); return df


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
    """Return signed TWA using NumPy, including Arrow-backed pandas columns."""
    numeric = pd.to_numeric(s, errors="coerce")
    values = numeric.to_numpy(dtype=np.float32, na_value=np.nan, copy=False)
    signed = ((values + np.float32(180.0)) % np.float32(360.0)) - np.float32(180.0)
    if isinstance(s, pd.Series):
        return pd.Series(signed, index=s.index, name=s.name, dtype=np.float32)
    return signed

def point_filter(df, twa_col, selection):
    if not twa_col or selection == "All": return df
    a = signed_twa(df[twa_col]).abs(); return df[a <= 90] if selection.startswith("Upwind") else df[a > 90]

def average_with_ranges(df, ts, columns, seconds, tolerances=None, signed_twa_col=None):
    """Return only requested channels, using one compact grouped aggregation.

    The raw path is also column-limited. This prevents plotting pages from retaining
    a shallow view of every channel in a wide log.
    """
    tolerances = tolerances or {}
    clean_columns = []
    for c in columns:
        if c and c in df.columns and c not in clean_columns and c != ts:
            clean_columns.append(c)
    raw_columns = ([ts] if ts and ts in df.columns else []) + clean_columns
    if not raw_columns:
        return df.iloc[:, 0:0].copy(deep=False), "raw"
    if seconds <= 1 or not ts or ts not in df or not pd.api.types.is_datetime64_any_dtype(df[ts]):
        return df.loc[:, raw_columns].copy(deep=False), "raw"

    valid_time = df[ts].notna()
    d = df.loc[valid_time, raw_columns].copy()
    del valid_time
    for c in clean_columns:
        d[c] = pd.to_numeric(d[c], errors="coerce", downcast="float")
    if signed_twa_col and signed_twa_col in d:
        d[signed_twa_col] = signed_twa(d[signed_twa_col])
    if not clean_columns:
        return df.loc[:, raw_columns].copy(deep=False), "raw"
    if not d[ts].is_monotonic_increasing:
        d.sort_values(ts, inplace=True, kind="stable")

    grouped = d.set_index(ts)[clean_columns].resample(f"{int(seconds)}s").agg(["mean", "min", "max"])
    means = grouped.xs("mean", axis=1, level=1)
    minima = grouped.xs("min", axis=1, level=1)
    maxima = grouped.xs("max", axis=1, level=1)
    keep = np.ones(len(means), dtype=bool)
    for col, tol in tolerances.items():
        if col in means.columns and tol is not None:
            span = (maxima[col] - minima[col]).to_numpy(dtype=np.float32, na_value=np.nan)
            keep &= np.isfinite(span) & (span <= float(tol))
    out = means.iloc[np.flatnonzero(keep)].dropna(how="all").reset_index()
    optimise_dtypes(out)
    del d, grouped, means, minima, maxima, keep
    gc.collect()
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
        radial = pd.to_numeric(df[bsp], errors="coerce").to_numpy(dtype=np.float32, na_value=np.nan)
        angle_valid = pd.to_numeric(df[twa], errors="coerce").notna().to_numpy()
        valid_positions = np.flatnonzero(angle_valid & np.isfinite(radial) & (radial >= r_min) & (radial <= r_max))
        plot_limit = int(st.session_state.get("nightjar_max_plot_points", 12000))
        if len(valid_positions) > plot_limit:
            valid_positions = np.sort(np.random.default_rng(42).choice(valid_positions, plot_limit, replace=False))
        plot_columns = [c for c in (bsp, twa, tws, vmg) if c and c in df.columns]
        d = df.iloc[valid_positions].loc[:, plot_columns].copy()
        del radial, angle_valid, valid_positions
        d["_theta"] = signed_twa(d[twa]).abs().clip(0, 180)
        d["_r"] = pd.to_numeric(d[bsp], errors="coerce", downcast="float")
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
    fig = go.Figure()
    if half and plot_space == "Polar":
        return half_polar_sailing_plot(df, m, polar, target, y_range)
    if bsp and twa and not df.empty:
        valid_positions = np.flatnonzero(df[bsp].notna().to_numpy() & df[twa].notna().to_numpy())
        plot_limit = int(st.session_state.get("nightjar_max_plot_points", 12000))
        if len(valid_positions) > plot_limit:
            valid_positions = np.sort(np.random.default_rng(42).choice(valid_positions, plot_limit, replace=False))
        plot_columns = [c for c in (bsp, twa, tws, vmg) if c and c in df.columns]
        d = df.iloc[valid_positions].loc[:, plot_columns].copy()
        del valid_positions
        d["Angle"] = signed_twa(d[twa]); d["Plot angle"] = d.Angle.abs() if half else d.Angle
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
    st.sidebar.markdown("""
    <style>
    [data-testid="stMetric"]{background:rgba(242,140,40,.12);border:1px solid #f28c28;border-radius:8px;padding:0.25rem 0.5rem;}
    [data-testid="stMetricLabel"]{font-size:0.75rem;}
    [data-testid="stMetricValue"]{font-size:1rem;color:#f28c28;}
    </style>
    """, unsafe_allow_html=True)
    memory_placeholder = st.sidebar.empty()
    memory_placeholder.metric("Process memory", f"{_rss_mb():.0f} MiB")
    logo = DATA_DIR / DEFAULT_FILES["logo"]
    if logo.exists(): st.sidebar.image(str(logo), width="stretch")
    st.sidebar.header("Event filter")
    st.sidebar.caption("Filters are applied before file processing and plotting.")
    st.sidebar.header("Input files")
    defs = [("log","Expedition log",["csv","txt"]),("polar","Target polar",["txt","csv","pol"]),("events","Expedition events",["csv","txt"]),("event_list","Event list",["txt","csv"]),("tests","Expedition tests",["csv"]),("sail_chart","Sail selection chart",["xml"]),("debrief","Debrief notes",["txt","md","docx"])]
    ups = {k: st.sidebar.file_uploader(n, type=t, key=f"file_{k}") for k,n,t in defs}; src = {k: (v if k == "debrief" else local(v,k)) for k,v in ups.items()}
    if not src["log"]: st.info("Upload a log or place the reference files in the data folder in the /Data volume"); st.stop()
    try: df = load_log_fast(src["log"])
    except Exception as e: st.error(f"Could not read log: {e}"); st.stop()
    source_rows = int(df.attrs.get("nightjar_source_rows", len(df)))
    sampling_stride = int(df.attrs.get("nightjar_sampling_stride", 1))
    if sampling_stride > 1:
        st.warning(
            f"Memory-safe sequential loading retained {len(df):,} of "
            f"{source_rows:,} data rows (approximately every {sampling_stride:,}th row). "
            "Date/time coverage is preserved, but summaries use the retained sample."
        )
    memory_placeholder.metric("Process memory", f"{_rss_mb():.0f} MiB")
    events = load_events_fast(src["events"])
    event_list = load_event_list_fast(src["event_list"])
    polar = load_polar_fast(src["polar"])
    df = ensure_vmg_pct(df, polar)
    # Resolve saved mappings before rendering the filter. The mapping controls are
    # deliberately rendered afterwards so they appear below the event filter.
    m = detect_columns(df)
    mapping_keys = ("timestamp","bsp","twa","tws","awa","vmg","vmg_pct","heel","drift","lat","lon")
    for k in mapping_keys:
        saved = st.session_state.get(f"map_{k}", m.get(k))
        m[k] = saved if saved is None or saved in df.columns else m.get(k)
    ts,bsp,twa,tws,vmg,vmg_pct,heel,drift,awa = [m.get(k) for k in ("timestamp","bsp","twa","tws","vmg","vmg_pct","heel","drift","awa")]
    filtered = df
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
                st.caption("Performance mode limits figures to approximately 10,000 plotted points per chart to reduce browser and server memory usage.")
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
                start_t = st.time_input("Start time", value=time(0, 0), key="side_start_time")
                end_t = st.time_input("End time", value=time(23, 59), key="side_end_time")
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

    st.sidebar.subheader("Column mapping")
    for k in mapping_keys:
        opts = [None] + list(df.columns); cur = m.get(k)
        m[k] = st.sidebar.selectbox(k.upper(), opts, index=opts.index(cur) if cur in opts else 0, format_func=lambda x:"Not mapped" if x is None else str(x), key=f"map_{k}")
    ts,bsp,twa,tws,vmg,vmg_pct,heel,drift,awa = [m.get(k) for k in ("timestamp","bsp","twa","tws","vmg","vmg_pct","heel","drift","awa")]
    st.session_state["nightjar_max_plot_points"] = int(max_plot_points)
    st.session_state["nightjar_performance_mode"] = bool(performance_mode)

    debrief_text = read_debrief_file(src.get("debrief"))
    # A single active page is executed per rerun. Streamlit tabs execute every tab,
    # including hidden plotting code, which was the main source of temporary RAM growth.
    page_names = ["Overview","Event summary","Polar analysis","GPS track","Variable plot","Files and sail chart"]
    st.markdown("""<style>div[role="radiogroup"] label{padding:10px 18px;border:1px solid #f28c28;border-radius:8px;background:rgba(242,140,40,0.12);margin-right:6px;cursor:pointer;} div[role="radiogroup"] label:hover{background:rgba(242,140,40,0.2);} </style>""", unsafe_allow_html=True)
    active_page = st.radio("Analysis page", page_names, horizontal=True, label_visibility="collapsed", key="nightjar_active_page")
    previous_page = st.session_state.get("nightjar_previous_page")
    if previous_page != active_page:
        st.session_state["nightjar_previous_page"] = active_page
        gc.collect()
    if active_page == "Overview":
        ms = st.columns(5); ms[0].metric("Rows", f"{len(filtered):,}"); ms[1].metric("Mean BSP", f"{filtered[bsp].mean():.2f} kt" if bsp else "n/a"); ms[2].metric("Mean TWS", f"{filtered[tws].mean():.1f} kt" if tws else "n/a"); ms[3].metric("Mean VMG", f"{filtered[vmg].mean():.2f} kt" if vmg else "n/a"); ms[4].metric("Channels", len(df.columns))
        if ts:
            cols = [c for c in (bsp,tws,vmg,vmg_pct,heel,twa) if c]
            if cols:
                overview_plot_df = downsample_rows(filtered, max_plot_points) if performance_mode else filtered
                long = overview_plot_df[[ts]+cols].melt(ts, var_name="Channel", value_name="Value").dropna(); fig = px.line(long, x=ts, y="Value", color="Channel", title="Selected time series including VMG and TWA"); fig.update_layout(template="plotly_dark", height=430); st.plotly_chart(fig, width="stretch")
        st.dataframe(round_numeric_df(filtered.head(500)), width="stretch", height=310)
    if active_page == "Event summary":
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

    if active_page == "Polar analysis":
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
        avg_cols = [c for c in [bsp,twa,tws,awa,vmg,vmg_pct,heel,drift,m.get("lat"),m.get("lon")] if c]
        polar_cols = []
        for c in ([ts] if ts else []) + avg_cols:
            if c and c in filtered.columns and c not in polar_cols:
                polar_cols.append(c)
        local_data = point_filter(filtered.loc[:, polar_cols], twa, point)
        if tws and polar and not use_all: local_data = local_data[local_data[tws].between(target-tol, target+tol)]
        local_data, avg_note = average_with_ranges(local_data, ts, avg_cols, int(avg_sec), {tws:max_tws_var,bsp:max_bsp_var}, signed_twa_col=twa)
        st.session_state["nightjar_avg_settings"] = {"seconds":int(avg_sec), "max_tws":max_tws_var, "max_bsp":max_bsp_var}
        st.caption(f"Plotting {len(local_data):,} records | {avg_note}. Half polar uses 0° to 180°.")
        if bsp and twa: st.plotly_chart(polar_plot(local_data, m, polar, target, layout.startswith("Half"), plot_space, (yr_min,yr_max)), width="stretch")
    if active_page == "GPS track":
        lat, lon = m.get("lat"), m.get("lon")
        if lat and lon and int((filtered[lat].notna() & filtered[lon].notna()).sum()) > 1:
            settings = st.session_state.get("nightjar_avg_settings", {"seconds": 1, "max_tws": 99.0, "max_bsp": 99.0})
            nums = filtered.select_dtypes(include=np.number).columns.tolist()
            default_colour = vmg if vmg in nums else (bsp if bsp in nums else (nums[0] if nums else None))
            if not nums:
                st.warning("No numeric channels are available to colour the GPS track.")
            else:
                g1, g2, g3, g4 = st.columns(4)
                with g1:
                    colour = st.selectbox("Colour track by", nums, index=nums.index(default_colour) if default_colour in nums else 0, key="gps_colour_by")
                with g2:
                    abs_colour = st.checkbox("Use absolute colour values", key="gps_abs_colour_values")

                # Average only the selected colour and hover channels, rather than every
                # numeric log channel. This is substantially smaller for wide Expedition logs.
                gps_columns = []
                for c in (lat, lon, colour, twa, tws, awa, heel, vmg, vmg_pct, drift, bsp):
                    if c and c in filtered.columns and c not in gps_columns:
                        gps_columns.append(c)
                gps_base, avg_note = average_with_ranges(
                    filtered,
                    ts,
                    gps_columns,
                    int(settings["seconds"]),
                    {tws: settings["max_tws"], bsp: settings["max_bsp"]},
                    signed_twa_col=twa,
                )
                valid_positions = np.flatnonzero(gps_base[lat].notna().to_numpy() & gps_base[lon].notna().to_numpy())
                gps_limit = min(10000, int(max_plot_points))
                if len(valid_positions) > gps_limit:
                    valid_positions = valid_positions[::math.ceil(len(valid_positions) / gps_limit)]
                d = gps_base.iloc[valid_positions].copy()
                del gps_base, valid_positions
                if ts and ts in d:
                    d["Time"] = pd.to_datetime(d[ts], errors="coerce").dt.round("s").dt.strftime("%d-%b-%Y %H:%M:%S")
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

    if active_page == "Variable plot":
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
    if active_page == "Files and sail chart":
        if src["sail_chart"]:
            try: sails = load_sails_fast(src["sail_chart"]); st.plotly_chart(sail_fig(sails), width="stretch"); st.dataframe(round_numeric_df(sails), width="stretch", height=270)
            except Exception as e: st.warning(f"Sail chart could not be parsed: {e}")
        download_limit_mb = float(os.environ.get("NIGHTJAR_MAX_IN_MEMORY_DOWNLOAD_MB", "32"))
        filtered_mb = dataframe_memory_mb(filtered)
        if filtered_mb <= download_limit_mb:
            st.download_button("Download filtered log CSV", filtered.to_csv(index=False).encode("utf-8"), "nightjar_filtered_log_0.7.8.1.csv", "text/csv", key="download_filtered")
        else:
            st.info(f"CSV download is disabled for this {filtered_mb:.0f} MiB selection to protect server memory. Narrow the filter, or raise NIGHTJAR_MAX_IN_MEMORY_DOWNLOAD_MB if Railway has sufficient RAM.")
        session = {"version":APP_VERSION, "created_utc":datetime.now(UTC).isoformat().replace("+00:00", "Z"), "rows":len(filtered), "mapping":m}
        st.download_button("Download session settings", json.dumps(session,indent=2).encode(), "nightjar_session_0.7.8.1.json", "application/json", key="download_session")
    # Refresh after the active page has been built so the sidebar reports the
    # process resident set, including the current plot's temporary objects.
    gc.collect()
    memory_placeholder.metric("Process memory", f"{_rss_mb():.0f} MiB")

if __name__ == "__main__": main()
