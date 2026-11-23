"""sensor_measure.py - YarnScope measurement straight from TrippleT (Nutzerwunsch 2026-11-20, feasibility for F&E).

Replaces the external program "Sensoft ATY" (Sensoptic, LabVIEW) for recording: the yarn sensor hangs on an NI
USB-6211 box ("Dev1" / "Dev2", one per user laptop) - Sensoft only reads one or two analogue inputs at a fixed rate
and saves calibrated µm values as TDMS. Found out with the user on 2026-11-20 (Sensoft 2.1.2.2):
- inputs per connector of the box: C1 = X ai1 / Y ai9, C2 = X ai4 / Y ai12; RSE, +-10 V (all Sensoft configs)
- calibration per sensor head: C:\\ProgramData\\Sensoptic\\Sensoft\\Config Data\\<HEAD>.dat,
  µm = DCX_COEFF[0] + DCX_COEFF[1] * V (DCY_COEFF for the second axis of a 2-axis head)
- rate = speed / 0.25 mm (the box rounds it: 50'800 asked -> 50'890.6 Hz; Sensoft has the same)
- Sensoft's "zeroing" does not change the saved values (probe without yarn: TrippleT -53.3 / 521.6 µm,
  Sensoft -53.8 / 521.6 µm, same noise) - zero_check() here only shows the sensor's empty value.
- TDMS layout: group "Rohdaten", "<name> (x-Achse)" [+ "(y-Achse)"] float64 with NI_ArrayColumn, an empty
  channel of 10 spaces, then the Parameter / Wert / Einheit table (Messung, Geschwindigkeit W2, Messabstand,
  Messfrequenz, Messlänge total). File name "<series>_<trial no>_<DDMMYY>_<HHMM>.tdms" -> the YarnScope tabs and
  the automatic analysis (tripplet_web app/yarnscope_auto.py) find it like a Sensoft file.
Extra file properties "TrippleT.*" (actual rate, head, box serial, trial, user, empty value) - readers ignore them.

Which sensor heads exist: the heads named in the user's own Sensoft configurations ("Default config*.ini" in
...\\LabVIEW Data\\Sensoft\\Config Data\\Configurations ATY, env TRIPPLET_SENSOFT_DIR = the "Sensoft" folder),
each with the connector it was used on. Measuring speed: the trial's winder speed (default_speed(), editable).

nidaqmx is imported only when measuring (pip nidaqmx, needs the NI-DAQmx driver). Without it list_boxes() raises
MeasureError("no_nidaqmx"); the rest of TrippleT does not care. Tests use a fake Daq (tests/test_sensor_measure.py).
Qt-free: used by the desktop dialog (ui/widgets/sensor_measure_dialog.py) and tripplet_web app/sensor_api.py.
"""
from __future__ import annotations

import datetime as _dt
import os
import re
import shutil
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

ENV_CAL_DIR = "TRIPPLET_SENSOR_CAL_DIR"
DEFAULT_CAL_DIR = r"C:\ProgramData\Sensoptic\Sensoft\Config Data"
ENV_SENSOFT_DIR = "TRIPPLET_SENSOFT_DIR"

CONNECTORS: Dict[str, Tuple[str, str]] = {"C1": ("ai1", "ai9"), "C2": ("ai4", "ai12")}
SPACING_MM = 0.25
V_MIN, V_MAX = -10.0, 10.0
MAX_AGGREGATE_RATE = 250_000.0          # USB-6211
SPEED_RANGE = (1.0, 3000.0)             # m/min
LENGTH_RANGE = (1.0, 5000.0)            # m
DEFAULT_LENGTH_M = 100.0
EMPTY_CHANNEL = " " * 10
GROUP = "Rohdaten"
KINDS = ("dty", "aty")
REPLACED_DIR = "_replaced"

_lock = threading.Lock()


class MeasureError(Exception):
    """code = message key for the web (<area>.err.<code>), vars = values for the text, detail = English text."""

    def __init__(self, code: str, detail: str = "", **vars: Any):
        super().__init__(detail or code)
        self.code, self.detail, self.vars = code, detail or code, vars


# ---------------------------------------------------------------------------------------------------- calibration
@dataclass
class Head:
    name: str                                  # e.g. "PXL_3_121_W" (= file name without .dat)
    title: str = ""                            # first line of the file
    date: str = ""
    axes: List[Tuple[float, float]] = field(default_factory=list)   # [(a, b)] µm = a + b*V, X first

    @property
    def n_axes(self) -> int:
        return len(self.axes)

    @property
    def label(self) -> str:
        parts = self.name.split("_")
        base = f"{parts[0]} {parts[1]}-{parts[2]}" if len(parts) >= 3 else self.name
        return f"{base} ({self.n_axes}-axis)"

    def to_um(self, volts: np.ndarray, axis: int) -> np.ndarray:
        a, b = self.axes[axis]
        return a + b * np.asarray(volts, dtype=float)


def cal_dir() -> Path:
    return Path(os.environ.get(ENV_CAL_DIR) or DEFAULT_CAL_DIR)


def _num(s: str) -> Optional[float]:
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def parse_calibration(text: str, name: str) -> Head:
    """A Sensoptic calibration file (*.dat): title, date, DCX_COEFF [+ DCY_COEFF]."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    head = Head(name=name, title=(lines[0].lstrip("* ").strip() if lines else ""),
                date=(lines[1].split()[0] if len(lines) > 1 and lines[1].split() else ""))
    coeff = {}
    for ln in lines:
        parts = ln.split()
        if parts and parts[0] in ("DCX_COEFF", "DCY_COEFF") and len(parts) >= 3:
            a, b = _num(parts[1]), _num(parts[2])
            if a is not None and b is not None:
                coeff[parts[0]] = (a, b)
    if "DCX_COEFF" in coeff:
        head.axes.append(coeff["DCX_COEFF"])
        if "DCY_COEFF" in coeff:
            head.axes.append(coeff["DCY_COEFF"])
    return head


def load_head(name: str, folder: Optional[Path] = None) -> Head:
    if not re.fullmatch(r"[A-Za-z0-9_.\-]+", name or ""):
        raise MeasureError("head_missing", f"bad head name {name!r}", head=name)
    p = Path(folder or cal_dir()) / f"{name}.dat"
    if not p.is_file():
        raise MeasureError("head_missing", f"calibration file {p} not found", head=name)
    head = parse_calibration(p.read_text(encoding="latin-1"), name)
    if not head.axes:
        raise MeasureError("head_missing", f"no DCX_COEFF in {p}", head=name)
    return head


# ---------------------------------------------------------------------------------------- Sensoft configurations
def sensoft_dir() -> Optional[Path]:
    """...\\LabVIEW Data\\Sensoft of this user (env TRIPPLET_SENSOFT_DIR, else Documents / OneDrive documents)."""
    env = os.environ.get(ENV_SENSOFT_DIR)
    if env:
        return Path(env)
    home = Path.home()
    cands = [home / "Documents", home / "Dokumente"]
    try:
        for d in home.iterdir():
            if d.is_dir() and d.name.lower().startswith("onedrive"):
                cands += [d / "Dokumente", d / "Documents"]
    except OSError:
        pass
    for c in cands:
        p = c / "LabVIEW Data" / "Sensoft"
        if p.is_dir():
            return p
    return None


def parse_sensoft_config(text: str) -> List[Dict[str, str]]:
    """[{head, connector, box, active}] of one Sensoft configuration (*.ini) - every head, active or not."""
    vals = {}
    for ln in text.splitlines():
        if "=" in ln:
            k, v = ln.split("=", 1)
            vals[k.strip()] = v.strip().strip('"')
    out = []
    for i in range(8):
        name = vals.get(f"Boxes 0.Heads {i}.Name")
        inp = vals.get(f"Boxes 0.Heads {i}.Channel inputs 0", "")
        if not name:
            continue
        m = re.match(r"([^/]+)/(ai\d+)", inp)
        conn = next((c for c, (x, _y) in CONNECTORS.items() if m and m.group(2) == x), None)
        if conn:
            out.append({"head": name, "connector": conn, "box": m.group(1),
                        "active": vals.get(f"Boxes 0.Heads {i}.Active", "TRUE").upper() == "TRUE"})
    return out


def sensor_presets(folder: Optional[Path] = None, cal_folder: Optional[Path] = None) -> List[Dict[str, Any]]:
    """The sensors this user works with: (head, connector) from the Sensoft configurations, with calibration.
    [{key, head, connector, axes, label, title, date}] - heads without a calibration file are left out.
    Order: the active heads of the most recently changed configuration first (= what Sensoft used last), then
    the rest by number of axes and name."""
    base = folder or sensoft_dir()
    seen: Dict[Tuple[str, str], Dict[str, Any]] = {}
    first: List[Tuple[str, str]] = []
    if base:
        cfg = Path(base) / "Config Data" / "Configurations ATY"
        files = sorted(cfg.glob("*.ini"), key=lambda p: p.stat().st_mtime, reverse=True) if cfg.is_dir() else []
        for n, f in enumerate(files):
            try:
                rows = parse_sensoft_config(f.read_text(encoding="latin-1"))
            except OSError:
                continue
            if n == 0:
                first = [(r["head"], r["connector"]) for r in rows if r.get("active")]
            for r in rows:
                k = (r["head"], r["connector"])
                if k in seen:
                    continue
                try:
                    h = load_head(r["head"], cal_folder)
                except MeasureError:
                    continue
                seen[k] = {"key": f"{h.name}@{r['connector']}", "head": h.name, "connector": r["connector"],
                           "axes": h.n_axes, "label": f"{h.label} – {r['connector']}", "title": h.title,
                           "date": h.date}
    rank = {k: i for i, k in enumerate(first)}
    return sorted(seen.values(), key=lambda p: (rank.get((p["head"], p["connector"]), len(rank)), -p["axes"],
                                                p["head"], p["connector"]))


def channels_for(head: Head, connector: str) -> List[str]:
    if connector not in CONNECTORS:
        raise MeasureError("bad_connector", f"connector {connector!r}", connector=connector)
    return list(CONNECTORS[connector][:head.n_axes])


# ------------------------------------------------------------------------------------------------------- the box
class Daq:
    """Access to the NI box. NidaqmxDaq = the real one; tests replace it."""

    def boxes(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def read(self, box: str, channels: Sequence[str], rate: float, n: int,
             progress: Optional[Callable[[int, int], None]] = None,
             cancel: Optional[Callable[[], bool]] = None) -> Tuple[float, np.ndarray]:
        """(actual rate, volts [len(channels), n])."""
        raise NotImplementedError

    def actual_rate(self, box: str, channels: Sequence[str], rate: float) -> float:
        return rate

    def stream(self, box: str, channels: Sequence[str], rate: float,
               on_chunk: Callable[[np.ndarray, float], None], should_stop: Callable[[], bool],
               chunk_s: float = 0.25) -> float:
        """Continuous reading until should_stop(): on_chunk(volts [len(channels), k], actual rate) about every
        chunk_s seconds (YarnScope Live, ui/yarnscope/sensor_live.py). Returns the actual rate."""
        raise NotImplementedError


def _nidaqmx():
    try:
        import nidaqmx  # noqa: F401
        import nidaqmx.system  # noqa: F401
        return nidaqmx
    except ImportError as e:
        raise MeasureError("no_nidaqmx", f"Python package nidaqmx missing: {e}")


class NidaqmxDaq(Daq):
    def boxes(self) -> List[Dict[str, Any]]:
        nidaqmx = _nidaqmx()
        try:
            devs = list(nidaqmx.system.System.local().devices)
        except Exception as e:                       # driver not installed / not running
            raise MeasureError("no_driver", f"NI-DAQmx driver: {e}")
        out = []
        for d in devs:
            try:
                out.append({"name": d.name, "product": d.product_type, "serial": f"{d.serial_num:X}",
                            "simulated": bool(d.is_simulated)})
            except Exception:
                continue
        return out

    def _task(self, box, channels, rate, n, continuous: bool = False):
        nidaqmx = _nidaqmx()
        from nidaqmx.constants import AcquisitionType, TerminalConfiguration
        task = nidaqmx.Task()
        try:
            for ch in channels:
                task.ai_channels.add_ai_voltage_chan(f"{box}/{ch}", terminal_config=TerminalConfiguration.RSE,
                                                     min_val=V_MIN, max_val=V_MAX)
            mode = AcquisitionType.CONTINUOUS if continuous else AcquisitionType.FINITE
            task.timing.cfg_samp_clk_timing(rate, sample_mode=mode, samps_per_chan=max(2, n))
            if continuous:                           # 20 s of room: the analysis may pause the reading a little
                task.in_stream.input_buf_size = int(max(n, rate * 20))
        except Exception:
            task.close()
            raise
        return task

    def stream(self, box, channels, rate, on_chunk, should_stop, chunk_s=0.25):
        try:
            task = self._task(box, channels, rate, int(rate * 20), continuous=True)
        except MeasureError:
            raise
        except Exception as e:
            raise MeasureError("daq_error", str(e))
        try:
            actual = float(task.timing.samp_clk_rate)
            k = max(500, int(actual * chunk_s))
            task.start()
            while not should_stop():
                data = task.read(number_of_samples_per_channel=k, timeout=chunk_s + 10)
                on_chunk(np.asarray(data, dtype=float).reshape(len(channels), -1), actual)
            return actual
        except MeasureError:
            raise
        except Exception as e:
            raise MeasureError("daq_error", str(e))
        finally:
            task.close()

    def actual_rate(self, box, channels, rate):
        try:
            task = self._task(box, channels, rate, 1000)
        except MeasureError:
            raise
        except Exception as e:
            raise MeasureError("daq_error", str(e))
        try:
            return float(task.timing.samp_clk_rate)
        finally:
            task.close()

    def read(self, box, channels, rate, n, progress=None, cancel=None):
        try:
            task = self._task(box, channels, rate, n)
        except MeasureError:
            raise
        except Exception as e:
            raise MeasureError("daq_error", str(e))
        try:
            actual = float(task.timing.samp_clk_rate)
            chunk = max(1000, int(actual / 4))           # ~0.25 s per read -> progress + cancel
            out = np.empty((len(channels), n))
            got = 0
            task.start()
            while got < n:
                if cancel and cancel():
                    raise MeasureError("cancelled", "cancelled")
                k = min(chunk, n - got)
                data = task.read(number_of_samples_per_channel=k, timeout=k / actual + 10)
                arr = np.asarray(data, dtype=float).reshape(len(channels), -1)
                out[:, got:got + arr.shape[1]] = arr
                got += arr.shape[1]
                if progress:
                    progress(got, n)
            return actual, out
        except MeasureError:
            raise
        except Exception as e:
            raise MeasureError("daq_error", str(e))
        finally:
            task.close()


_daq: Daq = NidaqmxDaq()


def set_daq(daq: Optional[Daq]) -> None:
    """Tests: a fake box (None = the real one again)."""
    global _daq
    _daq = daq or NidaqmxDaq()


def list_boxes() -> List[Dict[str, Any]]:
    return _daq.boxes()


def _check_box(box: str) -> Dict[str, Any]:
    for b in list_boxes():
        if b["name"] == box:
            return b
    raise MeasureError("box_missing", f"box {box!r} not connected", box=box)


# ------------------------------------------------------------------------------------------------------ planning
def default_speed(trial: Dict[str, Any]) -> Optional[float]:
    """Measuring speed [m/min] proposed for a trial = its WINDER speed (Nutzerangabe 2026-11-20), the same rule as
    the process schema (ui/dty_stations.speeds): Winder = Speed Shaft 2 x (1 - Winder % / 100); no Winder % ->
    Speed Shaft 2. Checked on prod: 466 V68-V70 800 m/min, 4.5 % -> 764 = the speed of the Sensoft files.
    ATY machines (Shaft2Speed, no winder %) get no proposal - the measured speed there was different (441 V7:
    460 vs 512 m/min); the user types it."""
    from ui import dty_stations as ds

    def _f(key):
        try:
            v = trial.get(key)
            return float(v) if v not in (None, "") else None
        except (TypeError, ValueError):
            return None
    lw2 = _f("SpeedShaft2")
    if not lw2 or lw2 <= 0:
        return None
    w = ds.speeds(lw2, winder=_f("Winder")).get("winder")
    v = w if w is not None else lw2
    return round(v, 1) if v > 0 else None


def nominal_rate(speed_m_min: float) -> float:
    return speed_m_min / 60.0 / (SPACING_MM / 1000.0)


def check_plan(speed_m_min: Any, length_m: Any, n_channels: int) -> Tuple[float, float, float]:
    """(speed, length, nominal rate) or MeasureError bad_speed / bad_length / rate_too_high."""
    try:
        v = float(speed_m_min)
    except (TypeError, ValueError):
        raise MeasureError("bad_speed", "speed missing", lo=SPEED_RANGE[0], hi=SPEED_RANGE[1])
    if not SPEED_RANGE[0] <= v <= SPEED_RANGE[1]:
        raise MeasureError("bad_speed", f"speed {v}", lo=SPEED_RANGE[0], hi=SPEED_RANGE[1])
    try:
        length = float(length_m)
    except (TypeError, ValueError):
        raise MeasureError("bad_length", "length missing", lo=LENGTH_RANGE[0], hi=LENGTH_RANGE[1])
    if not LENGTH_RANGE[0] <= length <= LENGTH_RANGE[1]:
        raise MeasureError("bad_length", f"length {length}", lo=LENGTH_RANGE[0], hi=LENGTH_RANGE[1])
    rate = nominal_rate(v)
    if rate * n_channels > MAX_AGGREGATE_RATE:
        raise MeasureError("rate_too_high", f"{rate:.0f} Hz x {n_channels}",
                           max_speed=round(MAX_AGGREGATE_RATE / n_channels * SPACING_MM / 1000 * 60))
    return v, length, rate


def samples_for(length_m: float, speed_m_min: float, actual_rate: float) -> int:
    """Points for the length at the box's real rate (time based, like Sensoft: 100 m at 762 m/min -> ~400'700)."""
    return int(round(length_m / (speed_m_min / 60.0) * actual_rate))


def _fmt(v: float) -> str:
    return f"{v:.0f}" if abs(v - round(v)) < 1e-9 else f"{v:g}"


def file_name(series_id: int, vno: int, when: Optional[_dt.datetime] = None) -> str:
    when = when or _dt.datetime.now()
    return f"{int(series_id)}_{int(vno)}_{when:%d%m%y_%H%M}.tdms"


def tdms_folder(kind: str) -> Path:
    from ui.yarnscope import aty_service, dty_service
    if kind not in KINDS:
        raise MeasureError("bad_kind", f"kind {kind!r}")
    return Path((dty_service if kind == "dty" else aty_service).tdms_base())


def existing_file(series_id: int, vno: int, kind: str) -> Optional[Path]:
    from ui.yarnscope import aty_service, dty_service
    svc = dty_service if kind == "dty" else aty_service
    return svc.find_tdms(int(series_id), int(vno), tdms_folder(kind))


# --------------------------------------------------------------------------------------------------------- TDMS
def write_tdms(path: Path, label: str, axes_um: Sequence[np.ndarray], speed_m_min: float, length_m: float,
               rate_hz: float, extra: Optional[Dict[str, Any]] = None) -> Path:
    """TDMS in Sensoft's layout (see module doc). Written to <path>.part first, then renamed - the automatic
    analysis only takes *.tdms."""
    from nptdms import ChannelObject, GroupObject, RootObject, TdmsWriter
    path = Path(path)
    props: Dict[str, Any] = {"name": path.stem}
    for k, v in (extra or {}).items():
        if v is not None:
            props[f"TrippleT.{k}"] = v if isinstance(v, (int, float, str)) else str(v)
    objs = [RootObject(properties=props), GroupObject(GROUP)]
    for i, (arr, ax) in enumerate(zip(axes_um, ("x", "y"))):
        objs.append(ChannelObject(GROUP, f"{label} ({ax}-Achse)", np.asarray(arr, dtype=np.float64),
                                  properties={"NI_ArrayColumn": i}))
    objs.append(ChannelObject(GROUP, EMPTY_CHANNEL, np.array([], dtype=np.float64)))
    table = [("Messung", label, ""), ("Geschwindigkeit W2", _fmt(speed_m_min), "m/min"),
             ("Messabstand", _fmt(SPACING_MM), "mm"), ("Messfrequenz", _fmt(round(rate_hz)), "Hz"),
             ("Messlänge total", _fmt(length_m), "m")]
    for i, name in enumerate(("Parameter", "Wert", "Einheit")):
        objs.append(ChannelObject(GROUP, name, [row[i] for row in table]))
    tmp = path.with_name(path.name + ".part")
    with TdmsWriter(str(tmp)) as w:
        w.write_segment(objs)
    os.replace(tmp, path)
    return path


# ------------------------------------------------------------------------------------------------------ measuring
def zero_check(box: str, head_name: str, connector: str, seconds: float = 1.0) -> Dict[str, Any]:
    """Empty value of the sensor (no yarn): mean / std per axis in µm and V. Saves nothing (Sensoft's zeroing
    does not change the data either)."""
    head = load_head(head_name)
    chans = channels_for(head, connector)
    _check_box(box)
    rate = 10_000.0
    with _measuring():
        actual, volts = _daq.read(box, chans, rate, int(rate * max(0.2, min(float(seconds), 10.0))))
    axes = []
    for i, v in enumerate(volts):
        um = head.to_um(v, i)
        axes.append({"axis": "xy"[i], "mean_um": round(float(um.mean()), 2), "std_um": round(float(um.std()), 2),
                     "mean_v": round(float(np.mean(v)), 4), "connector": connector})
    return {"axes": axes, "rate": actual, "head": head.name, "connector": connector, "box": box,
            "at": _dt.datetime.now().isoformat(timespec="seconds")}


class _measuring:
    """One measurement per process (the box can only do one anyway)."""

    def __enter__(self):
        if not _lock.acquire(blocking=False):
            raise MeasureError("busy", "a measurement is running")
        return self

    def __exit__(self, *exc):
        _lock.release()
        return False


def _sensors(head_name: str, connector: str, second: Any) -> List[Tuple[Head, str]]:
    """[(head, connector)] - the main sensor and, if given, a second one on the OTHER connector of the same box."""
    out = [(load_head(head_name), connector)]
    if second:
        h2, c2 = (second.get("head_name") or second.get("head"), second.get("connector")) if isinstance(second, dict) \
            else (second[0], second[1])
        if c2 == connector:
            raise MeasureError("same_connector", f"both sensors on {c2}", connector=c2)
        out.append((load_head(h2), c2))
    for h, c in out:
        channels_for(h, c)                       # unknown connector -> bad_connector
    return out


def _record(box: str, sensors: List[Tuple[Head, str]], v: float, length: float, rate: float,
            progress: Optional[Callable[[int, int], None]], cancel: Optional[Callable[[], bool]]):
    """(box info, actual rate, points, [[µm per axis] per sensor]) - ONE task for all channels of all sensors, so the
    samples of the two sensors are taken at the same instants (needed for the delay / speed, sensor_pair.py)."""
    chans, split = [], []
    for h, c in sensors:
        cs = channels_for(h, c)
        split.append((len(chans), len(cs)))
        chans += cs
    b = _check_box(box)
    with _measuring():
        actual = _daq.actual_rate(box, chans, rate)
        n = samples_for(length, v, actual)
        actual, volts = _daq.read(box, chans, rate, n, progress=progress, cancel=cancel)
    axes = [[h.to_um(volts[s + i], i) for i in range(k)] for (h, _c), (s, k) in zip(sensors, split)]
    return b, actual, n, axes


def _extra(b: Dict[str, Any], actual: float, head: Head, connector: str, box: str, kind: str,
           user: Optional[Dict[str, Any]], zero: Optional[Dict[str, Any]], **more: Any) -> Dict[str, Any]:
    extra = {"ActualRateHz": round(actual, 3), "Head": head.name, "HeadTitle": head.title, "HeadCalDate": head.date,
             "Connector": connector, "Box": box, "BoxSerial": b.get("serial"), "BoxProduct": b.get("product"),
             "Kind": kind, "User": (user or {}).get("username") or (user or {}).get("id"),
             "MeasuredAt": _dt.datetime.now().isoformat(timespec="seconds"), **more}
    if zero:
        for ax in zero.get("axes") or []:
            if ax.get("connector") in (None, connector):
                extra[f"Empty{ax.get('axis', '').upper()}_um"] = ax.get("mean_um")
    return extra


def _stats(axes_um) -> List[Dict[str, Any]]:
    return [{"axis": "xy"[i], "mean_um": round(float(a.mean()), 1), "std_um": round(float(a.std()), 1)}
            for i, a in enumerate(axes_um)]


def _result(path: Path, n: int, actual: float, v: float, length: float, axes_um, kind: str, **more: Any):
    return {"file": path.name, "path": str(path), "points": int(n), "rate": round(actual, 1), "speed": v,
            "length": length, "axes": _stats(axes_um), "kind": kind, **more}


def _pair(axes, actual: float, v: float, distance_mm: Any) -> Optional[Dict[str, Any]]:
    """Delay / speed / same knots of the two sensors (None with one sensor). Never breaks a measurement."""
    if len(axes) < 2:
        return None
    try:
        from ui.yarnscope import sensor_pair
        d = float(distance_mm) if distance_mm not in (None, "") and float(distance_mm) > 0 else None
        return sensor_pair.pair_report(axes[0], axes[1], actual, SPACING_MM, distance_mm=d, nominal_speed=v)
    except Exception as e:  # noqa: BLE001 - the files are saved anyway
        return {"error": str(e)[:300], "reliable": False}


def _free_path(folder: Path, label: str, when: _dt.datetime) -> Path:
    path = folder / f"{label}_{when:%d%m%y_%H%M}.tdms"
    return path if not path.exists() else folder / f"{label}_{when:%d%m%y_%H%M%S}.tdms"


def measure(*, series_id: int, trial_id: int, vno: int, box: str, head_name: str, connector: str,
            speed_m_min: Any, length_m: Any, kind: str = "dty", replace: bool = False,
            user: Optional[Dict[str, Any]] = None, zero: Optional[Dict[str, Any]] = None,
            second: Any = None, distance_mm: Any = None,
            progress: Optional[Callable[[int, int], None]] = None,
            cancel: Optional[Callable[[], bool]] = None, now: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """Measure one trial and save the TDMS into the DTY / ATY folder. Returns {file, path, points, rate, ...}.
    An existing file of the trial: MeasureError("exists") unless replace - then it is moved to _replaced/
    (never deleted).
    second = {"head_name", "connector"} of a second sensor on the other connector (Nutzerwunsch 2026-11-23): both are
    read in one task; the main sensor's file is the trial's file as always, the second one goes with the same name
    into the sub-folder _<connector> (e.g. _C2 - never seen by the automatic analysis / the tabs). distance_mm =
    distance between the sensors -> result["pair"] with the measured speed (sensor_pair.pair_report)."""
    sensors = _sensors(head_name, connector, second)
    v, length, rate = check_plan(speed_m_min, length_m, sum(h.n_axes for h, _c in sensors))
    folder = tdms_folder(kind)
    if not folder.is_dir():
        raise MeasureError("folder_missing", f"{folder} not reachable", folder=str(folder))
    old = existing_file(series_id, vno, kind)
    if old is not None and not replace:
        raise MeasureError("exists", f"{old.name} exists", file=old.name)
    b, actual, n, axes = _record(box, sensors, v, length, rate, progress, cancel)
    moved = None
    if old is not None:
        dest = old.parent / REPLACED_DIR
        dest.mkdir(exist_ok=True)
        moved = dest / old.name
        if moved.exists():
            moved = dest / f"{old.stem}_{_dt.datetime.now():%H%M%S}{old.suffix}"
        shutil.move(str(old), str(moved))
    when = now or _dt.datetime.now()
    label = f"{int(series_id)}_{int(vno)}"
    path = folder / file_name(series_id, vno, when)
    trial = dict(TrialID=int(trial_id), SeriesID=int(series_id))
    pair = _pair(axes, actual, v, distance_mm)
    paths = [path]
    if len(sensors) > 1:
        sub = folder / f"_{sensors[1][1]}"
        sub.mkdir(exist_ok=True)
        paths.append(_free_path(sub, label, when))
    pair_props = _pair_props(sensors, paths, distance_mm, pair)
    for i, ((h, c), p) in enumerate(zip(sensors, paths)):
        write_tdms(p, label, axes[i], v, length, rate,
                   _extra(b, actual, h, c, box, kind, user, zero, **trial, **pair_props[i]))
    res = _result(path, n, actual, v, length, axes[0], kind, replaced=moved.name if moved else None)
    return _with_second(res, sensors, paths, axes, pair)


def _pair_props(sensors, paths, distance_mm, pair) -> List[Dict[str, Any]]:
    """TDMS properties that tie the two files of a simultaneous measurement together."""
    if len(sensors) < 2:
        return [{}]
    common = {"PairDistanceMm": float(distance_mm) if distance_mm not in (None, "") else None,
              "PairDelayMs": (pair or {}).get("delay_ms"), "PairSpeed": (pair or {}).get("speed"),
              "PairCorr": (pair or {}).get("corr")}
    return [dict(common, PairFile=paths[1 - i].name, PairConnector=sensors[1 - i][1],
                 PairRole="main" if i == 0 else "second") for i in range(2)]


def _with_second(res: Dict[str, Any], sensors, paths, axes, pair) -> Dict[str, Any]:
    if len(sensors) > 1:
        res["second"] = {"file": paths[1].name, "path": str(paths[1]), "connector": sensors[1][1],
                         "head": sensors[1][0].name, "axes": _stats(axes[1])}
        res["pair"] = pair
    return res


# Free measurement (TDMS Inspector, Nutzerwunsch 2026-11-23): own name + speed, no series / trial / DB. The file goes
# to the sub-folder _manual of the DTY / ATY folder - the automatic analysis and the YarnScope tabs only look at the
# folder itself, so "466_5" typed here never lands on a real trial.
MANUAL_DIR = "_manual"
NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\- ]{0,59}")


def check_name(name: Any) -> str:
    n = str(name or "").strip()
    if not NAME_RE.fullmatch(n):
        raise MeasureError("bad_name", f"name {n!r}", name=n)
    return n


def manual_folder(kind: str) -> Path:
    return tdms_folder(kind) / MANUAL_DIR


def next_name(name: str) -> str:
    """"99999_34" -> "99999_35" (last number counted up, digits kept); no number at the end -> name + "_2"."""
    m = re.search(r"(\d+)$", name or "")
    if not m:
        return f"{name}_2" if name else ""
    num = m.group(1)
    return name[:m.start()] + str(int(num) + 1).zfill(len(num))


def measure_free(*, name: Any, box: str, head_name: str, connector: str, speed_m_min: Any, length_m: Any,
                 kind: str = "dty", user: Optional[Dict[str, Any]] = None, zero: Optional[Dict[str, Any]] = None,
                 second: Any = None, distance_mm: Any = None,
                 progress: Optional[Callable[[int, int], None]] = None,
                 cancel: Optional[Callable[[], bool]] = None, now: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """Measure with a free name and speed -> <DTY|ATY folder>/_manual/<name>_<DDMMYY>_<HHMM>.tdms. Same recording
    and TDMS as measure(); a file of the same name and minute gets the seconds added (never overwritten).
    With a second sensor both files go to _manual with the connector in the name: <name>_C1_… and <name>_C2_…"""
    label = check_name(name)
    sensors = _sensors(head_name, connector, second)
    v, length, rate = check_plan(speed_m_min, length_m, sum(h.n_axes for h, _c in sensors))
    base = tdms_folder(kind)
    if not base.is_dir():
        raise MeasureError("folder_missing", f"{base} not reachable", folder=str(base))
    folder = base / MANUAL_DIR
    folder.mkdir(exist_ok=True)
    b, actual, n, axes = _record(box, sensors, v, length, rate, progress, cancel)
    when = now or _dt.datetime.now()
    labels = [label] if len(sensors) == 1 else [f"{label}_{c}" for _h, c in sensors]
    paths = [_free_path(folder, lb, when) for lb in labels]
    pair = _pair(axes, actual, v, distance_mm)
    pair_props = _pair_props(sensors, paths, distance_mm, pair)
    for i, ((h, c), p) in enumerate(zip(sensors, paths)):
        write_tdms(p, labels[i], axes[i], v, length, rate, _extra(b, actual, h, c, box, kind, user, zero, Manual=1,
                                                                  **pair_props[i]))
    res = _result(paths[0], n, actual, v, length, axes[0], kind, name=label, next_name=next_name(label))
    return _with_second(res, sensors, paths, axes, pair)


# --------------------------------------------------------------------------------------------------- trial list
def trials_for(series_id: int) -> List[Dict[str, Any]]:
    """Trials of a series that can be measured (no reference samples), with the proposed speed and the
    existing DTY / ATY file. [{trial_id, vno, speed, dty, aty}]"""
    from db.connection import fetch_all
    from db.trial_reference import IS_REFERENCE_COL, has_reference_columns
    ref = f", {IS_REFERENCE_COL} AS isref" if has_reference_columns() else ""
    rows = fetch_all(f"SELECT ID, Versuchsnummer, SpeedShaft2, Winder{ref} FROM tblTrial WHERE TrialSeriesID = ? "
                     f"ORDER BY Versuchsnummer", [int(series_id)])
    names: Dict[str, List[str]] = {}
    for k in KINDS:                                # each folder listed once (5'000 files on the share)
        prefix = f"{int(series_id)}_"
        try:
            with os.scandir(tdms_folder(k)) as it:
                names[k] = sorted(e.name for e in it if e.name.lower().endswith(".tdms") and e.name.startswith(prefix))
        except OSError:
            names[k] = []
    out = []
    for r in rows:
        if r.get("isref"):
            continue
        vno = int(r.get("Versuchsnummer") or 0)
        files = {k: next((n for n in names[k] if n.startswith(f"{int(series_id)}_{vno}_")), None) for k in KINDS}
        out.append({"trial_id": int(r["ID"]), "vno": vno, "speed": default_speed(r), **files})
    return out
