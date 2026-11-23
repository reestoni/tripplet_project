"""sensor_live.py - "YarnScope Live": continuous measurement with a small dashboard (Nutzerwunsch 2026-11-23).

Start / stop by hand, no fixed length. Every WINDOW_M metres (default 30 m) one row:
  - knots/m and CV (start-to-start spacing) of that window per sensor - the YarnScope detection itself
    (dty_analysis.analyze_series, ~0.3 s for 30 m; the full analysis with all values is not needed here),
  - with a second sensor on the other connector: delay, match and - with the distance - the measured speed
    (sensor_pair.find_delay; both sensors are read in ONE task, so the delay is real).
Optionally saved while measuring ("save" ticked): the TDMS is written piece by piece (one segment per chunk, no
2 GB in memory for half an hour) to <DTY|ATY folder>/_manual/<name>[_C1|_C2]_<DDMMYY_HHMM>.tdms(.part while running),
same layout as Sensoft/measure_free; the parameter table comes as the last segment at stop. Saving ends by itself
after SAVE_LIMIT_M (the display goes on).

One live session per process (the box can do one thing at a time; sensor_measure._measuring is held while it
runs). Qt-free: the desktop window (ui/widgets/sensor_live_window.py) and tripplet_web app/sensor_live_api.py poll
state(). Tests: tests/test_sensor_live.py with a fake streaming box.
"""
from __future__ import annotations

import datetime as _dt
import os
import queue
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from ui.yarnscope import sensor_measure as sm

WINDOW_M = 30.0
WINDOW_RANGE = (5.0, 500.0)
SAVE_LIMIT_M = 5000.0                 # = the longest normal measurement (sensor_measure.LENGTH_RANGE)
CHUNK_S = 0.25                        # read from the box in quarter seconds
MAX_ROWS = 2000                       # dashboard history kept in memory

_lock = threading.Lock()
_current: Optional["LiveSession"] = None


class _Writer:
    """One TDMS written in segments (sensor_measure.write_tdms layout, but appended chunk by chunk)."""

    def __init__(self, path: Path, label: str, n_axes: int, props: Dict[str, Any]):
        from nptdms import GroupObject, RootObject, TdmsWriter
        self.path, self.label, self.n_axes = Path(path), label, n_axes
        self.part = self.path.with_name(self.path.name + ".part")
        self._w = TdmsWriter(str(self.part))
        self._w.__enter__()
        self._root = RootObject(properties={"name": self.path.stem, **props})
        self._group = GroupObject(sm.GROUP)
        self._first = True
        self.points = 0

    def write(self, axes_um: List[np.ndarray]) -> None:
        from nptdms import ChannelObject
        objs = [self._root, self._group] if self._first else []
        for i, (arr, ax) in enumerate(zip(axes_um, ("x", "y"))):
            objs.append(ChannelObject(sm.GROUP, f"{self.label} ({ax}-Achse)", np.asarray(arr, dtype=np.float64),
                                      properties={"NI_ArrayColumn": i} if self._first else {}))
        self._w.write_segment(objs)
        self._first = False
        self.points += len(axes_um[0])

    def close(self, speed: float, length_m: float, rate: float, extra: Dict[str, Any]) -> Path:
        from nptdms import ChannelObject, RootObject
        props = {f"TrippleT.{k}": v for k, v in extra.items() if v is not None}
        table = [("Messung", self.label, ""), ("Geschwindigkeit W2", sm._fmt(speed), "m/min"),
                 ("Messabstand", sm._fmt(sm.SPACING_MM), "mm"), ("Messfrequenz", sm._fmt(round(rate)), "Hz"),
                 ("Messlänge total", sm._fmt(round(length_m, 1)), "m")]
        objs = [RootObject(properties=props), ChannelObject(sm.GROUP, sm.EMPTY_CHANNEL, np.array([], dtype=np.float64))]
        objs += [ChannelObject(sm.GROUP, nm, [row[i] for row in table]) for i, nm in enumerate(("Parameter", "Wert", "Einheit"))]
        self._w.write_segment(objs)
        self._w.__exit__(None, None, None)
        os.replace(self.part, self.path)
        return self.path

    def abort(self) -> None:
        try:
            self._w.__exit__(None, None, None)
        except Exception:
            pass


class LiveSession:
    def __init__(self, *, box: str, head_name: str, connector: str, speed_m_min: Any, second: Any = None,
                 distance_mm: Any = None, window_m: Any = WINDOW_M, save: bool = True, name: Any = "live",
                 kind: str = "dty", user: Optional[Dict[str, Any]] = None):
        self.sensors = sm._sensors(head_name, connector, second)
        n_ch = sum(h.n_axes for h, _c in self.sensors)
        try:
            w = float(window_m)
        except (TypeError, ValueError):
            w = WINDOW_M
        self.window_m = min(max(w, WINDOW_RANGE[0]), WINDOW_RANGE[1])
        self.speed, _len, self.rate = sm.check_plan(speed_m_min, self.window_m, n_ch)
        self.box, self.kind, self.user = box, kind, user or {}
        self.distance_mm = float(distance_mm) if distance_mm not in (None, "") and float(distance_mm) > 0 else None
        self.save = bool(save)
        self.name = sm.check_name(name) if self.save else str(name or "live")
        self.started_at: Optional[float] = None
        self.actual_rate: Optional[float] = None
        self.samples = 0
        self.rows: List[Dict[str, Any]] = []
        self.state = "new"                    # new / running / stopping / done / error
        self.error: Optional[Dict[str, Any]] = None
        self.files: List[str] = []
        self.save_stopped = False
        self._stop = threading.Event()
        self._q: "queue.Queue" = queue.Queue()
        self._threads: List[threading.Thread] = []
        self._writers: List[_Writer] = []

    # ------------------------------------------------------------------------------------------- public
    def start(self) -> None:
        if sm.tdms_folder(self.kind) and self.save and not sm.tdms_folder(self.kind).is_dir():
            folder = sm.tdms_folder(self.kind)
            raise sm.MeasureError("folder_missing", f"{folder} not reachable", folder=str(folder))
        self.box_info = sm._check_box(self.box)
        self.state = "running"
        self.started_at = time.time()
        t1 = threading.Thread(target=self._acquire, name="yarnscope-live-daq", daemon=True)
        t2 = threading.Thread(target=self._analyse, name="yarnscope-live-analysis", daemon=True)
        self._threads = [t1, t2]
        t2.start()
        t1.start()

    def stop(self, wait: float = 20.0) -> None:
        self._stop.set()
        if self.state == "running":
            self.state = "stopping"
        for t in self._threads:
            t.join(wait)

    def meters(self) -> float:
        r = self.actual_rate or self.rate
        return self.samples / r * self.speed / 60.0 if r else 0.0

    def view(self, since: int = 0) -> Dict[str, Any]:
        rows = [r for r in self.rows if r["i"] >= since]
        return {"state": self.state, "error": self.error, "rows": rows, "n_rows": len(self.rows),
                "meters": round(self.meters(), 1), "seconds": round(time.time() - self.started_at, 1) if self.started_at else 0,
                "speed": self.speed, "window_m": self.window_m, "rate": round(self.actual_rate or 0, 1),
                "sensors": [{"head": h.name, "connector": c, "axes": h.n_axes} for h, c in self.sensors],
                "distance_mm": self.distance_mm, "save": self.save, "save_stopped": self.save_stopped,
                "files": list(self.files), "name": self.name, "kind": self.kind,
                "user": self.user.get("username") or self.user.get("id")}

    # ------------------------------------------------------------------------------------------ threads
    def _open_writers(self, actual: float) -> None:
        folder = sm.tdms_folder(self.kind) / sm.MANUAL_DIR
        folder.mkdir(exist_ok=True)
        when = _dt.datetime.now()
        labels = [self.name] if len(self.sensors) == 1 else [f"{self.name}_{c}" for _h, c in self.sensors]
        for (h, c), lb in zip(self.sensors, labels):
            path = sm._free_path(folder, lb, when)
            self._writers.append(_Writer(path, lb, h.n_axes, {}))

    def _close_writers(self) -> None:
        if not self._writers:
            return
        last = next((r for r in reversed(self.rows) if r.get("speed")), None)
        names = [w.path.name for w in self._writers]
        for i, (w, (h, c)) in enumerate(zip(self._writers, self.sensors)):
            length = w.points * sm.SPACING_MM / 1000.0 if not self.actual_rate else \
                w.points / self.actual_rate * self.speed / 60.0
            extra = sm._extra(self.box_info, self.actual_rate or self.rate, h, c, self.box, self.kind, self.user,
                              None, Manual=1, Live=1, LiveWindowM=self.window_m)
            if len(self._writers) > 1:
                extra.update(PairFile=names[1 - i], PairConnector=self.sensors[1 - i][1],
                             PairRole="main" if i == 0 else "second", PairDistanceMm=self.distance_mm,
                             PairSpeed=(last or {}).get("speed"))
            try:
                self.files.append(w.close(self.speed, length, self.actual_rate or self.rate,
                                          {k: v for k, v in extra.items()}).name)
            except Exception as e:  # noqa: BLE001
                self.error = {"code": "save_failed", "detail": str(e)[:300], "vars": {"detail": str(e)[:300]}}
        self._writers = []

    def _acquire(self) -> None:
        chans, split = [], []
        for h, c in self.sensors:
            cs = sm.channels_for(h, c)
            split.append((len(chans), len(cs)))
            chans += cs
        buf: List[List[np.ndarray]] = [[] for _ in self.sensors]
        have = 0
        win = None
        try:
            with sm._measuring():
                def on_chunk(volts: np.ndarray, actual: float) -> None:
                    nonlocal have, win
                    if self.actual_rate is None:
                        self.actual_rate = actual
                        win = int(round(self.window_m / (self.speed / 60.0) * actual))
                        if self.save:
                            self._open_writers(actual)
                    axes = [[h.to_um(volts[s + i], i) for i in range(k)] for (h, _c), (s, k) in zip(self.sensors, split)]
                    self.samples += volts.shape[1]
                    if self._writers:
                        if self.meters() > SAVE_LIMIT_M:
                            self.save_stopped = True
                            self._close_writers()
                        else:
                            for w, ax in zip(self._writers, axes):
                                w.write(ax)
                    for j, ax in enumerate(axes):
                        buf[j].append(ax)
                    have += volts.shape[1]
                    while win and have >= win:
                        out = []
                        for j in range(len(self.sensors)):
                            cat = [np.concatenate([c[i] for c in buf[j]]) for i in range(len(buf[j][0]))]
                            out.append([a[:win] for a in cat])
                            buf[j] = [[a[win:] for a in cat]]
                        have -= win
                        self._q.put(out)

                sm._daq.stream(self.box, chans, self.rate, on_chunk, self._stop.is_set, CHUNK_S)
        except Exception as e:  # noqa: BLE001 - shown on the dashboard
            self.error = {"code": getattr(e, "code", "daq_error"), "detail": getattr(e, "detail", str(e))[:300],
                          "vars": getattr(e, "vars", {"detail": str(e)[:300]})}
            for w in self._writers:
                w.abort()
            self._writers = []
        finally:
            self._q.put(None)
            for t in self._threads[1:]:
                t.join(30)
            if self._writers:
                self._close_writers()
            self.state = "error" if self.error and self.state != "stopping" else "done"

    def _analyse(self) -> None:
        from ui.yarnscope import sensor_pair
        from ui.yarnscope.dty_analysis import analyze_series
        i = 0
        while True:
            item = self._q.get()
            if item is None:
                return
            rate = self.actual_rate or self.rate
            row: Dict[str, Any] = {"i": i, "from_m": round(i * self.window_m, 1), "to_m": round((i + 1) * self.window_m, 1),
                                   "t": round(time.time() - (self.started_at or time.time()), 1), "sensors": []}
            sigs = []
            for axes in item:
                y = sensor_pair.combined(axes)
                sigs.append(y)
                try:
                    r = analyze_series(np.asarray(y, dtype=float), sm.SPACING_MM, 3)
                    cv = (r.get("ol_period_mm_stats") or {}).get("cv")
                    row["sensors"].append({"fpm": _num(r.get("knots_per_m"), 1), "cv": _num(cv, 1),
                                           "mean_um": _num(float(np.mean(y)), 1)})
                except Exception:  # noqa: BLE001 - e.g. no yarn in the sensor
                    row["sensors"].append({"fpm": None, "cv": None, "mean_um": _num(float(np.mean(y)), 1)})
            if len(sigs) == 2:
                r = sensor_pair.find_delay(sigs[0], sigs[1], sm.SPACING_MM,
                                           max_lag=int(sensor_pair.DEFAULT_MAX_DELAY_S * rate))
                ok = r["corr"] is not None and r["corr"] >= sensor_pair.MIN_CORR
                d = r["lag"] / rate if ok and r["lag"] else None
                row.update(corr=_num(r["corr"], 3), delay_ms=_num(d * 1000.0 if d else None, 3),
                           speed=_num(sensor_pair.speed_m_min(self.distance_mm, d) if d and self.distance_mm else None, 1),
                           distance_from_speed_mm=_num(self.speed / 60.0 * d * 1000.0 if d else None, 1))
            self.rows.append(row)
            if len(self.rows) > MAX_ROWS:
                del self.rows[: len(self.rows) - MAX_ROWS]
            i += 1


def _num(v: Any, digits: int) -> Optional[float]:
    try:
        f = float(v)
        return round(f, digits) if np.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def start(**kw: Any) -> LiveSession:
    """Starts THE live session of this process. busy while one runs (or any other measurement)."""
    global _current
    with _lock:
        if _current is not None and _current.state in ("running", "stopping"):
            raise sm.MeasureError("busy", "a live measurement is running")
        s = LiveSession(**kw)
        s.start()
        _current = s
        return s


def current() -> Optional[LiveSession]:
    return _current


def stop() -> Optional[LiveSession]:
    s = _current
    if s is not None and s.state in ("running", "stopping"):
        s.stop()
    return s
