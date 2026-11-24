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

AUTO SPEED (Nutzerwunsch 2026-11-23: "TrippleT soll den Speed selbst berechnen"): with two sensors and their distance no
speed is typed. The box then reads at a FIXED rate (AUTO_RATE_MAX per channel, less with 4 channels); every BLOCK_S
second the delay between the sensors gives the real speed, and with it each sensor's samples are resampled to exactly
0.25 mm (np.interp, position carried over from block to block) - so the analysis and the saved TDMS look like any
YarnScope file, even if the machine speed drifts. A block without a reliable match takes the last speed (none yet:
skipped). The saved file states the mean measured speed; "TrippleT.AutoSpeed" = 1, "SampleRateHz" = the fixed rate.

BOOKMARKS ("Merken", Nutzerwunsch 2026-11-24): while tuning a jet the user clicks "Merken" - no input - and the last
bookmark length (default 100 m, BOOKMARK_RANGE) of every sensor is copied out of a rolling buffer (BUFFER_M, already at
0.25 mm in auto-speed mode, at the box rate otherwise) into memory with knots/m + CV of that stretch. Nothing is written.
ui/yarnscope/live_trial.py later turns a bookmark into a new trial (copy of a template trial + the user's jet / pressure /
OF / speed) and, only if asked, writes the bookmark as that trial's TDMS. Bookmarks stay until the next live start.

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
AUTO_RATE_MAX = 80_000.0             # per channel in auto-speed mode: >= 1 point / 0.25 mm up to ~1'200 m/min
BLOCK_S = 1.0                         # auto speed: one speed value (and resampling step) per second
SAVE_LIMIT_M = 5000.0                 # = the longest normal measurement (sensor_measure.LENGTH_RANGE)
CHUNK_S = 0.25                        # read from the box in quarter seconds
MAX_ROWS = 2000                       # dashboard history kept in memory
BOOKMARK_M = 100.0                    # default length of a bookmark
BOOKMARK_RANGE = (5.0, 300.0)
BUFFER_M = BOOKMARK_RANGE[1]          # rolling buffer per sensor (float32, ~5 MB per axis at 300 m)
MAX_BOOKMARKS = 20

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
                 kind: str = "dty", user: Optional[Dict[str, Any]] = None, auto_speed: bool = False):
        self.sensors = sm._sensors(head_name, connector, second)
        n_ch = sum(h.n_axes for h, _c in self.sensors)
        try:
            w = float(window_m)
        except (TypeError, ValueError):
            w = WINDOW_M
        self.window_m = min(max(w, WINDOW_RANGE[0]), WINDOW_RANGE[1])
        self.distance_mm = float(distance_mm) if distance_mm not in (None, "") and float(distance_mm) > 0 else None
        self.auto_speed = bool(auto_speed)
        self._speeds: List[float] = []
        self._meters_auto = 0.0
        if self.auto_speed:
            if len(self.sensors) < 2 or not self.distance_mm:
                raise sm.MeasureError("auto_needs_two", "auto speed needs a second sensor and the distance")
            self.rate = min(AUTO_RATE_MAX, 0.95 * sm.MAX_AGGREGATE_RATE / n_ch)
            self.speed = 0.0                  # = the last measured speed while running
        else:
            self.speed, _len, self.rate = sm.check_plan(speed_m_min, self.window_m, n_ch)
        self.box, self.kind, self.user = box, kind, user or {}
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
        # rolling buffer for bookmarks: [(axes per sensor (float32), points, speed m/min)], newest last
        self._tail: List[tuple] = []
        self._tail_pts = 0
        self._tail_lock = threading.Lock()
        self.bookmarks: List[Dict[str, Any]] = []      # meta + "_axes" (not in view())
        self._bm_seq = 0

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
        if self.auto_speed:
            return self._meters_auto
        r = self.actual_rate or self.rate
        return self.samples / r * self.speed / 60.0 if r else 0.0

    def view(self, since: int = 0) -> Dict[str, Any]:
        rows = [r for r in self.rows if r["i"] >= since]
        return {"state": self.state, "error": self.error, "rows": rows, "n_rows": len(self.rows),
                "meters": round(self.meters(), 1), "seconds": round(time.time() - self.started_at, 1) if self.started_at else 0,
                "speed": self.speed, "auto_speed": self.auto_speed, "window_m": self.window_m,
                "rate": round(self.actual_rate or 0, 1),
                "sensors": [{"head": h.name, "connector": c, "axes": h.n_axes} for h, c in self.sensors],
                "distance_mm": self.distance_mm, "save": self.save, "save_stopped": self.save_stopped,
                "files": list(self.files), "name": self.name, "kind": self.kind,
                "user": self.user.get("username") or self.user.get("id"),
                "bookmarks": [self.bookmark_meta(b) for b in self.bookmarks],
                "bookmark_range": list(BOOKMARK_RANGE), "bookmark_m": BOOKMARK_M}

    # ------------------------------------------------------------------------------------------ bookmarks
    def _pts_per_m(self) -> float:
        """Points per metre of the buffered signal: 4000 in auto-speed mode (resampled to 0.25 mm), else rate / speed."""
        if self.auto_speed:
            return 1000.0 / sm.SPACING_MM
        r = self.actual_rate or self.rate
        return r / (self.speed / 60.0) if self.speed else 1000.0 / sm.SPACING_MM

    def _buffer(self, axes_per_sensor: List[List[np.ndarray]], speed: float) -> None:
        """Appends one piece (already in um) to the rolling buffer and drops the oldest beyond BUFFER_M."""
        n = len(axes_per_sensor[0][0])
        if not n:
            return
        piece = [[np.asarray(a, dtype=np.float32) for a in axes] for axes in axes_per_sensor]
        limit = int(BUFFER_M * self._pts_per_m()) + 1
        with self._tail_lock:
            self._tail.append((piece, n, float(speed or 0.0)))
            self._tail_pts += n
            while self._tail and self._tail_pts - self._tail[0][1] >= limit:
                self._tail_pts -= self._tail.pop(0)[1]

    @staticmethod
    def bookmark_meta(b: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in b.items() if not k.startswith("_")}

    def bookmark(self, length_m: Any = None, label: Any = None) -> Dict[str, Any]:
        """Merken: copies the last length_m metres of every sensor (default BOOKMARK_M) with knots/m + CV of that
        stretch. Takes what is there if less was measured (at least BOOKMARK_RANGE[0])."""
        from ui.yarnscope import sensor_pair
        from ui.yarnscope.dty_analysis import analyze_series
        try:
            want = float(length_m) if length_m not in (None, "") else BOOKMARK_M
        except (TypeError, ValueError):
            raise sm.MeasureError("bad_length", f"length {length_m!r}", lo=BOOKMARK_RANGE[0], hi=BOOKMARK_RANGE[1])
        if not (BOOKMARK_RANGE[0] <= want <= BOOKMARK_RANGE[1]):
            raise sm.MeasureError("bad_length", f"length {want}", lo=BOOKMARK_RANGE[0], hi=BOOKMARK_RANGE[1])
        if len(self.bookmarks) >= MAX_BOOKMARKS:
            raise sm.MeasureError("too_many_bookmarks", "too many bookmarks", n=MAX_BOOKMARKS)
        ppm = self._pts_per_m()
        need = int(round(want * ppm))
        with self._tail_lock:
            pieces = list(self._tail)
        have = sum(n for _p, n, _v in pieces)
        if have < BOOKMARK_RANGE[0] * ppm:
            raise sm.MeasureError("too_short", "not enough measured yet", m=BOOKMARK_RANGE[0])
        take, got, speeds = [], 0, []
        for piece, n, v in reversed(pieces):
            take.append(piece)
            speeds.append((n, v))
            got += n
            if got >= need:
                break
        take.reverse()
        axes = []
        for j in range(len(self.sensors)):
            cat = [np.concatenate([p[j][a] for p in take]) for a in range(len(take[0][j]))]
            axes.append([x[-need:] if len(x) > need else x for x in cat])
        pts = len(axes[0][0])
        wv = [(n, v) for n, v in speeds if v]
        speed = sum(n * v for n, v in wv) / sum(n for n, _v in wv) if wv else self.speed
        sens = []
        for ax in axes:
            y = sensor_pair.combined([np.asarray(a, dtype=float) for a in ax])
            try:
                r = analyze_series(y, sm.SPACING_MM, 3)
                sens.append({"fpm": _num(r.get("knots_per_m"), 1),
                             "cv": _num((r.get("ol_period_mm_stats") or {}).get("cv"), 1),
                             "mean_um": _num(float(np.mean(y)), 1)})
            except Exception:  # noqa: BLE001 - e.g. no yarn
                sens.append({"fpm": None, "cv": None, "mean_um": _num(float(np.mean(y)), 1)})
        self._bm_seq += 1
        b = {"id": self._bm_seq, "at": _dt.datetime.now().isoformat(timespec="seconds"),
             "at_m": round(self.meters(), 1), "length_m": round(pts / ppm, 1), "speed": _num(speed, 1),
             "sensors": sens, "label": str(label or "")[:60], "trial": None, "file": None,
             "_axes": axes, "_ppm": ppm}
        self.bookmarks.append(b)
        return self.bookmark_meta(b)

    def find_bookmark(self, bid: Any) -> Dict[str, Any]:
        b = next((x for x in self.bookmarks if str(x["id"]) == str(bid)), None)
        if b is None:
            raise sm.MeasureError("no_bookmark", f"bookmark {bid!r}", id=str(bid))
        return b

    def label_bookmark(self, bid: Any, label: Any) -> Dict[str, Any]:
        b = self.find_bookmark(bid)
        b["label"] = str(label or "")[:60]
        return self.bookmark_meta(b)

    def delete_bookmark(self, bid: Any) -> None:
        self.bookmarks.remove(self.find_bookmark(bid))

    def bookmark_tdms(self, b: Dict[str, Any], paths: List[Path], label: Any, **more: Any) -> None:
        """Writes the bookmark's signals as TDMS (one file per sensor; sensor_measure.write_tdms layout). label = one
        name for all files (a trial: same name in the sub-folder) or a list, one per file."""
        labels = list(label) if isinstance(label, (list, tuple)) else [label] * len(paths)
        axes, ppm = b["_axes"], b["_ppm"]
        speed = float(b["speed"] or self.speed or 0.0)
        length = len(axes[0][0]) / ppm
        rate = speed / 60.0 * ppm if speed else (self.actual_rate or self.rate)
        for i, ((h, c), p) in enumerate(zip(self.sensors, paths)):
            pair = {}
            if len(paths) > 1:
                pair = dict(PairFile=paths[1 - i].name, PairConnector=self.sensors[1 - i][1],
                            PairRole="main" if i == 0 else "second", PairDistanceMm=self.distance_mm)
            extra = sm._extra(self.box_info, self.actual_rate or self.rate, h, c, self.box, self.kind, self.user, None,
                              Live=1, Bookmark=b["id"], BookmarkAt=b["at"], AutoSpeed=1 if self.auto_speed else None,
                              **pair, **more)
            sm.write_tdms(p, labels[i], [np.asarray(a, dtype=np.float64) for a in axes[i]], round(speed, 1),
                          round(length, 1), rate, extra)

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
        auto = {}
        if self.auto_speed:
            mean_v = float(np.mean(self._speeds)) if self._speeds else 0.0
            auto = dict(AutoSpeed=1, SampleRateHz=round(self.actual_rate or self.rate, 3),
                        MeasuredSpeedMean=round(mean_v, 2))
        for i, (w, (h, c)) in enumerate(zip(self._writers, self.sensors)):
            if self.auto_speed:              # resampled to 0.25 mm: length from the points, rate from the mean speed
                length = w.points * sm.SPACING_MM / 1000.0
                file_speed = round(auto["MeasuredSpeedMean"], 1)
                file_rate = file_speed / 60.0 / (sm.SPACING_MM / 1000.0) if file_speed else (self.actual_rate or self.rate)
            else:
                length = w.points * sm.SPACING_MM / 1000.0 if not self.actual_rate else \
                    w.points / self.actual_rate * self.speed / 60.0
                file_speed, file_rate = self.speed, self.actual_rate or self.rate
            extra = sm._extra(self.box_info, self.actual_rate or self.rate, h, c, self.box, self.kind, self.user,
                              None, Manual=1, Live=1, LiveWindowM=self.window_m, **auto)
            if len(self._writers) > 1:
                extra.update(PairFile=names[1 - i], PairConnector=self.sensors[1 - i][1],
                             PairRole="main" if i == 0 else "second", PairDistanceMm=self.distance_mm,
                             PairSpeed=(last or {}).get("speed"))
            try:
                self.files.append(w.close(file_speed, length, file_rate, {k: v for k, v in extra.items()}).name)
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
                    if self.auto_speed:              # resampling + windows + files: in the analysis thread
                        if self.actual_rate is None:
                            self.actual_rate = actual
                        self.samples += volts.shape[1]
                        self._q.put([[h.to_um(volts[s + i], i) for i in range(k)]
                                     for (h, _c), (s, k) in zip(self.sensors, split)])
                        return
                    if self.actual_rate is None:
                        self.actual_rate = actual
                        win = int(round(self.window_m / (self.speed / 60.0) * actual))
                        if self.save:
                            self._open_writers(actual)
                    axes = [[h.to_um(volts[s + i], i) for i in range(k)] for (h, _c), (s, k) in zip(self.sensors, split)]
                    self.samples += volts.shape[1]
                    self._buffer(axes, self.speed)
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
        if self.auto_speed:
            self._analyse_auto()
            return
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
                ok = bool(r["ok"])
                d = r["lag"] / rate if ok and r["lag"] else None
                row.update(corr=_num(r["corr"], 3), delay_ms=_num(d * 1000.0 if d else None, 3),
                           speed=_num(sensor_pair.speed_m_min(self.distance_mm, d) if d and self.distance_mm else None, 1),
                           distance_from_speed_mm=_num(self.speed / 60.0 * abs(d) * 1000.0 if d else None, 1))
            self.rows.append(row)
            if len(self.rows) > MAX_ROWS:
                del self.rows[: len(self.rows) - MAX_ROWS]
            i += 1


    # ------------------------------------------------------------------------------------- auto speed
    def _analyse_auto(self) -> None:
        """Raw chunks at the fixed rate -> per BLOCK_S: delay -> speed -> resample to 0.25 mm -> windows + files."""
        from ui.yarnscope import sensor_pair
        ns = len(self.sensors)
        raw: List[List[List[np.ndarray]]] = [[] for _ in range(ns)]          # per sensor: chunks (list of axes)
        have = 0
        pos = [0.0] * ns                    # position (mm) of the next raw sample, per sensor
        nxt = [0.0] * ns                    # next 0.25 mm grid point not yet produced
        win_pts = int(round(self.window_m * 1000.0 / sm.SPACING_MM))
        out: List[List[List[np.ndarray]]] = [[] for _ in range(ns)]          # resampled, not yet in a window
        out_n = 0
        block_v: List[tuple] = []                                            # (speed, corr) of the window's blocks
        i_row = 0
        last_v: Optional[float] = None
        while True:
            item = self._q.get()
            done = item is None
            if not done:
                for j in range(ns):
                    raw[j].append(item[j])
                have += len(item[0][0])
            rate = self.actual_rate or self.rate
            block = int(BLOCK_S * rate)
            while have >= block or (done and have >= max(256, block // 4)):
                n = min(block, have)
                blk = []
                for j in range(ns):
                    cat = [np.concatenate([c[a] for c in raw[j]]) for a in range(len(raw[j][0]))]
                    blk.append([x[:n] for x in cat])
                    raw[j] = [[x[n:] for x in cat]]
                have -= n
                r = sensor_pair.find_delay(sensor_pair.combined(blk[0]), sensor_pair.combined(blk[1]), sm.SPACING_MM,
                                           max_lag=int(sensor_pair.DEFAULT_MAX_DELAY_S * rate))
                ok = bool(r["ok"]) and bool(r["lag"])   # either direction
                v = sensor_pair.speed_m_min(self.distance_mm, r["lag"] / rate) if ok else None
                if v is not None and not (sm.SPEED_RANGE[0] <= v <= sm.SPEED_RANGE[1]):
                    v = None
                if v is not None:
                    last_v = v
                    self._speeds.append(v)
                    self.speed = round(v, 1)
                use_v = v if v is not None else last_v
                if use_v is None:                       # no speed yet: these samples cannot be placed in metres
                    continue
                step = use_v / 60.0 / rate * 1000.0     # mm per raw sample
                self._meters_auto += n * step / 1000.0
                block_v.append((v if v is not None else float("nan"),
                                r["corr"] if r["corr"] is not None else float("nan")))
                res = []
                for j in range(ns):
                    p = pos[j] + np.arange(n) * step
                    g = np.arange(nxt[j], p[-1] + 1e-9, sm.SPACING_MM)
                    res.append([np.interp(g, p, x) for x in blk[j]])
                    pos[j] = p[-1] + step
                    if len(g):
                        nxt[j] = g[-1] + sm.SPACING_MM
                k = min(len(res[j][0]) for j in range(ns))
                res = [[x[:k] for x in res[j]] for j in range(ns)]
                self._buffer(res, use_v)
                if self.save and not self._writers and not self.save_stopped:
                    self._open_writers(rate)
                if self._writers:
                    if self.meters() > SAVE_LIMIT_M:
                        self.save_stopped = True
                        self._close_writers()
                    else:
                        for w, ax in zip(self._writers, res):
                            w.write(ax)
                for j in range(ns):
                    out[j].append(res[j])
                out_n += k
                while out_n >= win_pts:
                    wins = []
                    for j in range(ns):
                        cat = [np.concatenate([c[a] for c in out[j]]) for a in range(len(out[j][0]))]
                        wins.append([x[:win_pts] for x in cat])
                        out[j] = [[x[win_pts:] for x in cat]]
                    out_n -= win_pts
                    self._row_auto(i_row, wins, block_v)
                    block_v = []
                    i_row += 1
            if done:
                return

    def _row_auto(self, i: int, wins, block_v) -> None:
        from ui.yarnscope import sensor_pair
        from ui.yarnscope.dty_analysis import analyze_series
        row: Dict[str, Any] = {"i": i, "from_m": round(i * self.window_m, 1), "to_m": round((i + 1) * self.window_m, 1),
                               "t": round(time.time() - (self.started_at or time.time()), 1), "sensors": []}
        for axes in wins:
            y = sensor_pair.combined(axes)
            try:
                r = analyze_series(np.asarray(y, dtype=float), sm.SPACING_MM, 3)
                row["sensors"].append({"fpm": _num(r.get("knots_per_m"), 1),
                                       "cv": _num((r.get("ol_period_mm_stats") or {}).get("cv"), 1),
                                       "mean_um": _num(float(np.mean(y)), 1)})
            except Exception:  # noqa: BLE001
                row["sensors"].append({"fpm": None, "cv": None, "mean_um": _num(float(np.mean(y)), 1)})
        vs = [v for v, _c in block_v if np.isfinite(v)]
        cs = [c for _v, c in block_v if np.isfinite(c)]
        mv = float(np.mean(vs)) if vs else None
        row.update(speed=_num(mv, 1), corr=_num(float(np.mean(cs)) if cs else None, 3),
                   speed_min=_num(min(vs) if vs else None, 1), speed_max=_num(max(vs) if vs else None, 1),
                   delay_ms=_num(self.distance_mm / 1000.0 / (mv / 60.0) * 1000.0 if mv else None, 3))
        self.rows.append(row)
        if len(self.rows) > MAX_ROWS:
            del self.rows[: len(self.rows) - MAX_ROWS]


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
