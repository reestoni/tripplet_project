# ui/screen_air_supply.py
"""Air Supply Network Calculator for TrippleT.

Graph:  Source → Pipe segments → Y-Splits → Jets
Solver: bottom-up flow, top-down cumulative ΔP + inlet pressure at every jet.

DB tables (auto-created):
    tblAirNetwork      — network metadata (name, description, created_by)
    tblAirNetworkData  — serialised graph JSON per network

Usage in main.py:
    from ui.screen_air_supply import AirSupplyScreen
    screen = AirSupplyScreen(
        on_back_home=self._go_home,
        jets_loader=self._load_jets_data,
        username=self._username,
    )
"""

from __future__ import annotations

import copy
import json
import math
import uuid
from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush, QColor, QFont, QFontMetrics, QPainter, QPen, QPolygonF,
)
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDoubleSpinBox, QFrame,
    QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMessageBox, QPushButton, QSizePolicy, QSpinBox,
    QSplitter, QStackedWidget, QTabBar, QTabWidget,
    QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
)

from ui.widgets.header import HeaderBar
from ui.widgets.footer import FooterBar
from ui.theme import get_accent, DARK, LIGHT_BG, CARD_BG, TEXT

# ---------------------------------------------------------------------------
# Physics
# ---------------------------------------------------------------------------

RHO0  = 1.293      # kg/m³  air at 0 °C / 1013 mbar
MU    = 1.82e-5    # Pa·s
P_ATM = 101325.0   # Pa

DN_STANDARDS = [6, 8, 10, 13, 16, 20, 25, 32, 40, 50, 63, 80, 100]


def _flow_nozzle_nl_s(d_mm: float, n_holes: int,
                      p_bar_g: float, cd: float = 0.65) -> float:
    """Normalised flow [Nl/s] through a nozzle (orifice equation)."""
    d_m   = d_mm / 1000.0
    area  = math.pi / 4.0 * d_m ** 2
    p_abs = p_bar_g * 1e5 + P_ATM
    rho   = RHO0 * p_abs / P_ATM
    dp    = p_bar_g * 1e5
    q_act = cd * area * math.sqrt(max(0.0, 2.0 * dp / rho))
    return q_act * (p_abs / P_ATM) * n_holes


def _darcy_dp(flow_nl_s: float, d_mm: float,
              L_m: float, p_bar_g: float) -> float:
    """Pressure drop [bar] via Darcy-Weisbach."""
    if d_mm <= 0 or L_m <= 0 or flow_nl_s <= 0:
        return 0.0
    d_m   = d_mm / 1000.0
    A     = math.pi / 4.0 * d_m ** 2
    p_abs = p_bar_g * 1e5 + P_ATM
    rho   = RHO0 * p_abs / P_ATM
    q_act = flow_nl_s * P_ATM / p_abs   # Nl/s → actual m³/s at pressure
    v     = q_act / A
    Re    = rho * v * d_m / MU
    if Re < 1:
        return 0.0
    f = (64.0 / Re if Re < 2300
         else 0.25 / math.log10(max(1e-10, 5.74 / Re ** 0.9)) ** 2)
    return f * (L_m / d_m) * 0.5 * rho * v * v / 1e5


def _operating_cost(flow_nl_s: float, p_bar_g: float,
                    hours_day: float, days_year: float,
                    price_chf_kwh: float, efficiency: float) -> Dict:
    """Compute annual compressor operating cost.

    Isothermal compression power:
        P [W] = Q_atm [m³/s] × P_atm [Pa] × ln(p_abs / P_atm)
    where Q_atm = flow_nl_s / 1000  (Nl/s → m³/s;  1 Nl = 0.001 m³)

    Returns dict with keys: power_kw, hours_year, energy_kwh, cost_chf.
    """
    if flow_nl_s <= 0 or p_bar_g <= 0 or efficiency <= 0:
        return {"power_kw": 0.0, "hours_year": 0.0,
                "energy_kwh": 0.0, "cost_chf": 0.0}
    p_abs      = p_bar_g * 1e5 + P_ATM
    q_atm      = flow_nl_s / 1000.0          # Nl/s → m³/s at NTP
    p_iso      = q_atm * P_ATM * math.log(p_abs / P_ATM)   # W isothermal
    p_real     = p_iso / efficiency           # W actual shaft power
    power_kw   = p_real / 1000.0
    hours_year = hours_day * days_year
    energy_kwh = power_kw * hours_year
    cost_chf   = energy_kwh * price_chf_kwh
    return {
        "power_kw":   power_kw,
        "hours_year": hours_year,
        "energy_kwh": energy_kwh,
        "cost_chf":   cost_chf,
    }


def _recommend_dn(flow_nl_s: float, p_bar_g: float,
                  v_target: float = 25.0) -> int:
    if flow_nl_s <= 0:
        return 6
    p_abs = p_bar_g * 1e5 + P_ATM
    q_act = flow_nl_s * P_ATM / p_abs   # Nl/s → actual m³/s
    d_min = math.sqrt(4.0 * q_act / (math.pi * v_target)) * 1000.0
    for dn in DN_STANDARDS:
        if dn >= d_min:
            return dn
    return int(math.ceil(d_min / 5.0) * 5)


def _fitting_equiv_length(d_mm: float, bends_90: int, bends_45: int) -> float:
    """Equivalent pipe length [m] for fittings (based on L/D ratios).

    Typical L/D values (smooth bend, turbulent flow):
      90° elbow : L/D ≈ 30
      45° elbow : L/D ≈ 16
    """
    if d_mm <= 0:
        return 0.0
    d_m = d_mm / 1000.0
    return (bends_90 * 30 + bends_45 * 16) * d_m


def _borda_carnot_dp(flow_nl_s: float,
                     d_in_mm: float, d_out_mm: float,
                     p_bar_g: float) -> float:
    """Pressure drop [bar] at a sudden contraction/expansion (Borda-Carnot).

    Expansion (d_in < d_out): Borda-Carnot  ΔP = ½ρ(v1-v2)²
    Contraction (d_in > d_out): loss coeff  ΔP = 0.5 · ½ρv2²
    """
    if d_in_mm <= 0 or d_out_mm <= 0 or flow_nl_s <= 0:
        return 0.0
    p_abs  = p_bar_g * 1e5 + P_ATM
    rho    = RHO0 * p_abs / P_ATM
    q_act  = flow_nl_s * P_ATM / p_abs   # Nl/s → actual m³/s
    A_in   = math.pi / 4.0 * (d_in_mm  / 1000.0) ** 2
    A_out  = math.pi / 4.0 * (d_out_mm / 1000.0) ** 2
    v_in   = q_act / A_in  if A_in  > 0 else 0.0
    v_out  = q_act / A_out if A_out > 0 else 0.0
    if d_in_mm < d_out_mm:
        # Sudden expansion
        dp_Pa = 0.5 * rho * (v_in - v_out) ** 2
    else:
        # Sudden contraction (loss coeff ≈ 0.5)
        dp_Pa = 0.5 * 0.5 * rho * v_out ** 2
    return dp_Pa / 1e5


# ---------------------------------------------------------------------------
# Node model
# ---------------------------------------------------------------------------

NODE_SOURCE  = "source"
NODE_SEGMENT = "segment"
NODE_SPLIT   = "split"
NODE_JET     = "jet"
NODE_REDUCER = "reducer"

_NODE_COLORS = {
    NODE_SOURCE:  "#1D3557",
    NODE_SEGMENT: "#457B9D",
    NODE_SPLIT:   "#E9C46A",
    NODE_JET:     "#39A650",
    NODE_REDUCER: "#E76F51",
}
_NODE_SIZE = {
    NODE_SOURCE:  (110, 54),
    NODE_SEGMENT: (110, 44),
    NODE_SPLIT:   (72, 40),
    NODE_JET:     (110, 54),
    NODE_REDUCER: (100, 44),
}


class Node:
    def __init__(self, kind: str, x: float = 100.0, y: float = 100.0):
        self.id   = str(uuid.uuid4())[:8]
        self.kind = kind
        self.x    = x
        self.y    = y
        # Segment
        self.seg_length   = 5.0
        self.seg_diam     = 0.0   # mm  (0=auto)
        self.seg_pressure = 4.0   # bar_g – computed top-down, not user-set
        self.seg_bends_90 = 0     # number of 90° elbows
        self.seg_bends_45 = 0     # number of 45° elbows
        # Reducer
        self.red_d_in     = 25.0  # mm inlet diameter
        self.red_d_out    = 13.0  # mm outlet diameter
        self.red_pressure = 4.0   # bar_g – computed top-down, not user-set
        # Source
        self.source_pressure = 6.0  # bar_g – compressor outlet pressure (user-set)
        # Jet
        self.nozzle_db_jet:  Optional[Dict] = None
        self.nozzle_name     = ""
        self.nozzle_hole_d   = 1.0
        self.nozzle_n_holes  = 1
        self.nozzle_count    = 1
        self.nozzle_pressure = 4.0
        self.nozzle_cd       = 0.65
        # Computed
        self.result_flow_nl_s  = 0.0
        self.result_v          = 0.0   # inlet velocity
        self.result_v_out      = 0.0   # outlet velocity (reducer only)
        self.result_dp         = 0.0
        self.result_dp_cum     = 0.0
        self.result_p_inlet    = 0.0
        self.result_p_required = 0.0
        self.result_dn_rec     = 0

    # ── serialise ────────────────────────────────────────────────────
    def to_dict(self) -> Dict:
        d = {k: v for k, v in self.__dict__.items()
             if not k.startswith("result_")}
        d["_custom_name"] = getattr(self, "_custom_name", "")
        if self.nozzle_db_jet:
            d["nozzle_db_jet_id"]   = self.nozzle_db_jet.get("ID")
            d["nozzle_db_jet_name"] = self.nozzle_db_jet.get("Jet", "")
        d.pop("nozzle_db_jet", None)
        return d

    @classmethod
    def from_dict(cls, d: Dict, jets_by_id: Dict) -> "Node":
        n = cls(d["kind"], d.get("x", 100), d.get("y", 100))
        n.id = d.get("id", n.id)
        for a in ("seg_length", "seg_diam", "seg_pressure",
                  "seg_bends_90", "seg_bends_45",
                  "red_d_in", "red_d_out", "red_pressure",
                  "source_pressure",
                  "nozzle_name", "nozzle_hole_d", "nozzle_n_holes",
                  "nozzle_count", "nozzle_pressure", "nozzle_cd",
                  "_custom_name"):
            if a in d:
                setattr(n, a, d[a])
        jid = d.get("nozzle_db_jet_id")
        if jid is not None:
            n.nozzle_db_jet = jets_by_id.get(int(jid))
        return n

    # ── display ──────────────────────────────────────────────────────
    def label(self) -> str:
        cn = getattr(self, "_custom_name", "")
        if self.kind == NODE_SOURCE:  return cn or "Source"
        if self.kind == NODE_SPLIT:   return cn or "Y-Split"
        if self.kind == NODE_SEGMENT:
            if cn: return cn
            if self.seg_diam > 0:
                diam_str = f"ø{int(self.seg_diam)} mm"
            else:
                # Show recommended diameter from solver if available, else "auto"
                if self.result_dn_rec:
                    diam_str = f"ø{self.result_dn_rec} mm (rec.)"
                else:
                    diam_str = "ø auto"
            return f"Pipe  {self.seg_length:.0f} m\n{diam_str}"
        if self.kind == NODE_REDUCER:
            if cn: return cn
            return f"Reducer\nø{int(self.red_d_in)}→ø{int(self.red_d_out)}mm"
        if self.kind == NODE_JET:
            name = ((self.nozzle_db_jet.get("Jet", "") if self.nozzle_db_jet
                     else self.nozzle_name) or cn or "Jet")
            return f"{name} ×{self.nozzle_count}"
        return self.kind

    def width(self)  -> int: return _NODE_SIZE[self.kind][0]
    def height(self) -> int: return _NODE_SIZE[self.kind][1]
    def rect(self)   -> QRectF:
        w, h = self.width(), self.height()
        return QRectF(self.x - w/2, self.y - h/2, w, h)
    def center(self) -> QPointF:
        return QPointF(self.x, self.y)


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

class NetworkGraph:
    def __init__(self):
        self.nodes: Dict[str, Node]       = {}
        self.edges: List[Tuple[str, str]] = []

    def add_node(self, n: Node):         self.nodes[n.id] = n
    def remove_node(self, nid: str):
        self.nodes.pop(nid, None)
        self.edges = [(a, b) for a, b in self.edges if a != nid and b != nid]
    def add_edge(self, a: str, b: str):
        if (a, b) not in self.edges: self.edges.append((a, b))
    def remove_edge(self, a: str, b: str):
        self.edges = [(x, y) for x, y in self.edges if not (x == a and y == b)]
    def children(self, nid: str) -> List[str]:
        return [b for a, b in self.edges if a == nid]
    def parents(self, nid: str)  -> List[str]:
        return [a for a, b in self.edges if b == nid]

    # ── serialise ────────────────────────────────────────────────────
    def to_json(self) -> str:
        return json.dumps({
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": list(self.edges),
        })

    @classmethod
    def from_json(cls, raw: str, jets_by_id: Dict) -> "NetworkGraph":
        g    = cls()
        data = json.loads(raw)
        for nd in data.get("nodes", []):
            g.nodes[nd["id"]] = Node.from_dict(nd, jets_by_id)
        # Deduplicate edges on load
        seen = set()
        for e in data.get("edges", []):
            t = (str(e[0]), str(e[1]))
            if t not in seen:
                seen.add(t)
                g.edges.append(t)
        return g

    def validate(self) -> List[str]:
        """Return list of warning strings for graph issues."""
        warnings = []
        for nid in self.nodes:
            parents = self.parents(nid)
            if len(parents) > 1:
                n = self.nodes[nid]
                warnings.append(
                    f"Node '{n.label().split(chr(10))[0]}' has {len(parents)} "
                    f"incoming connections — expected 1.")
        return warnings

    # ── solver ───────────────────────────────────────────────────────
    def solve(self):
        """Iterative solver (5 passes).

        The user sets the *desired pressure at the jet*.  The pipe network
        adds losses on top, so the compressor must supply:
            p_source = p_jet + ΣΔP(path)

        Each iteration:
          1. bottom-up: compute flow at every node using jet set-pressure
          2. top-down:  compute ΔP per segment and cumulative ΔP per path
          3. store result_p_required on each segment =
                 max jet set-pressure downstream + remaining cumulative loss
        After convergence, result_p_inlet on a jet = its set pressure
        (by definition), and the Source panel shows the required inlet
        pressure including all losses.
        """
        if not self.nodes:
            return

        # ── topological sort (Kahn) ───────────────────────────────────
        in_deg = {nid: 0 for nid in self.nodes}
        for a, b in self.edges:
            in_deg[b] = in_deg.get(b, 0) + 1
        queue = [nid for nid, d in in_deg.items() if d == 0]
        topo: List[str] = []
        while queue:
            nid = queue.pop(0)
            topo.append(nid)
            for c in self.children(nid):
                in_deg[c] -= 1
                if in_deg[c] == 0:
                    queue.append(c)

        # ── helper: get jet geometry ──────────────────────────────────
        def _jet_geom(node: Node):
            d, nh = node.nozzle_hole_d, node.nozzle_n_holes
            if node.nozzle_db_jet:
                try:
                    d  = float(str(node.nozzle_db_jet.get("Luftbohrung") or d)
                               .replace(",", "."))
                    nh = int(node.nozzle_db_jet.get("LuftlochAnzahl") or nh)
                except Exception:
                    pass
            return d, nh

        # ── iterative solve ───────────────────────────────────────────
        # Find source pressure (set by user on the Source node)
        src_nodes = [n for n in self.nodes.values() if n.kind == NODE_SOURCE]
        p_source = src_nodes[0].source_pressure if src_nodes else 6.0

        for _iter in range(5):

            # 1. Bottom-up: flow.
            #    Jet flow uses nozzle_pressure (desired jet inlet pressure).
            flow: Dict[str, float] = {}
            for nid in reversed(topo):
                node = self.nodes[nid]
                if node.kind == NODE_JET:
                    d, nh = _jet_geom(node)
                    flow[nid] = (_flow_nozzle_nl_s(
                        d, nh, node.nozzle_pressure, node.nozzle_cd)
                        * node.nozzle_count)
                else:
                    flow[nid] = sum(flow.get(c, 0.0)
                                    for c in self.children(nid))
                node.result_flow_nl_s = flow[nid]

            # 2. Top-down: distribute source pressure, compute ΔP per node.
            #    p_inlet[nid] = local pressure available at node inlet
            #                 = p_source − cumulative ΔP from source to here
            cum_dp:  Dict[str, float] = {}   # cumulative ΔP source→node
            p_inlet: Dict[str, float] = {}   # actual pressure at node inlet
            p_req:   Dict[str, float] = {}   # required pressure (bottom-up, for display)

            for nid in topo:
                node = self.nodes[nid]
                pars = self.parents(nid)
                par_dp    = max((cum_dp.get(p, 0.0)  for p in pars), default=0.0)
                par_preq  = max((p_req.get(p, 0.0)   for p in pars), default=0.0)

                if node.kind == NODE_SEGMENT:
                    q     = node.result_flow_nl_s
                    # Local pressure = source pressure minus losses upstream
                    p_op  = max(p_source - par_dp, 0.1)
                    node.seg_pressure = p_op   # store for results table / optimizer
                    dn    = _recommend_dn(q, p_op)
                    node.result_dn_rec = dn
                    d_use = node.seg_diam if node.seg_diam > 0 else dn
                    p_abs = p_op * 1e5 + P_ATM
                    q_act = q * P_ATM / p_abs
                    A     = math.pi / 4.0 * (d_use / 1000.0) ** 2
                    node.result_v     = q_act / A if A > 0 else 0.0
                    node.result_v_out = node.result_v
                    L_eq  = node.seg_length + _fitting_equiv_length(
                        d_use, node.seg_bends_90, node.seg_bends_45)
                    node.result_dp    = _darcy_dp(q, d_use, L_eq, p_op)
                    node.result_dp_cum = par_dp + node.result_dp
                    node.result_p_inlet = p_op
                    child_preq = max(
                        (p_req.get(c, 0.0) for c in self.children(nid)),
                        default=0.0)
                    node.result_p_required = child_preq + node.result_dp
                    cum_dp[nid] = node.result_dp_cum
                    p_inlet[nid] = p_op - node.result_dp
                    p_req[nid]   = node.result_p_required

                elif node.kind == NODE_REDUCER:
                    q      = node.result_flow_nl_s
                    p_op   = max(p_source - par_dp, 0.1)
                    node.red_pressure = p_op   # store for results table / optimizer
                    p_abs  = p_op * 1e5 + P_ATM
                    q_act  = q / (p_abs / P_ATM)
                    A_in   = math.pi / 4.0 * (node.red_d_in  / 1000.0) ** 2
                    A_out  = math.pi / 4.0 * (node.red_d_out / 1000.0) ** 2
                    node.result_v     = q_act / A_in  if A_in  > 0 else 0.0
                    node.result_v_out = q_act / A_out if A_out > 0 else 0.0
                    node.result_dn_rec = 0
                    node.result_dp = _borda_carnot_dp(
                        q, node.red_d_in, node.red_d_out, p_op)
                    node.result_dp_cum  = par_dp + node.result_dp
                    node.result_p_inlet = p_op
                    child_preq = max(
                        (p_req.get(c, 0.0) for c in self.children(nid)),
                        default=0.0)
                    node.result_p_required = child_preq + node.result_dp
                    cum_dp[nid] = node.result_dp_cum
                    p_inlet[nid] = p_op - node.result_dp
                    p_req[nid]   = node.result_p_required

                elif node.kind == NODE_JET:
                    node.result_v          = 0.0
                    node.result_dp         = 0.0
                    node.result_dn_rec     = 0
                    node.result_dp_cum     = par_dp
                    node.result_p_inlet    = max(p_source - par_dp, 0.0)
                    node.result_p_required = node.nozzle_pressure
                    cum_dp[nid] = par_dp
                    p_inlet[nid] = node.result_p_inlet
                    p_req[nid]  = node.nozzle_pressure

                else:   # SOURCE, SPLIT
                    node.result_v = node.result_dp = 0.0
                    node.result_dn_rec   = 0
                    node.result_dp_cum   = par_dp
                    node.result_p_inlet  = p_source
                    child_preq = max(
                        (p_req.get(c, 0.0) for c in self.children(nid)),
                        default=0.0)
                    node.result_p_required = child_preq
                    cum_dp[nid]  = par_dp
                    p_inlet[nid] = p_source
                    p_req[nid]   = child_preq


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

_TABLES_ENSURED = False


def _ensure_tables():
    global _TABLES_ENSURED
    if _TABLES_ENSURED:
        return
    try:
        from db.connection import get_connection
        with get_connection() as cn:
            cur = cn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tblAirNetwork (
                    ID          INT AUTO_INCREMENT PRIMARY KEY,
                    Name        VARCHAR(120) NOT NULL,
                    Description TEXT,
                    CreatedBy   VARCHAR(20),
                    CreatedAt   DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UpdatedAt   DATETIME DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tblAirNetworkData (
                    ID        INT AUTO_INCREMENT PRIMARY KEY,
                    NetworkID INT NOT NULL,
                    GraphJSON LONGTEXT NOT NULL,
                    SavedAt   DATETIME DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_airnet
                        FOREIGN KEY (NetworkID)
                        REFERENCES tblAirNetwork(ID)
                        ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
        _TABLES_ENSURED = True
    except Exception as e:
        print(f"[AirSupply] Could not ensure tables: {e}")


def db_save_network(name: str, description: str, graph: NetworkGraph,
                    username: str, network_id: Optional[int] = None) -> int:
    _ensure_tables()
    from db.connection import get_connection
    gj = graph.to_json()
    with get_connection() as cn:
        cur = cn.cursor()
        if network_id:
            cur.execute(
                "UPDATE tblAirNetwork SET Name=%s, Description=%s, UpdatedAt=NOW() "
                "WHERE ID=%s", (name, description, network_id))
            cur.execute("DELETE FROM tblAirNetworkData WHERE NetworkID=%s",
                        (network_id,))
        else:
            cur.execute(
                "INSERT INTO tblAirNetwork (Name,Description,CreatedBy) "
                "VALUES (%s,%s,%s)", (name, description, username))
            network_id = cur.lastrowid
        cur.execute(
            "INSERT INTO tblAirNetworkData (NetworkID,GraphJSON) VALUES (%s,%s)",
            (network_id, gj))
    return network_id


def db_list_networks() -> List[Dict]:
    _ensure_tables()
    try:
        from db.connection import fetch_all
        return fetch_all(
            "SELECT ID,Name,Description,CreatedBy,UpdatedAt "
            "FROM tblAirNetwork ORDER BY UpdatedAt DESC")
    except Exception:
        return []


def db_load_network(network_id: int, jets_by_id: Dict) -> Optional[NetworkGraph]:
    _ensure_tables()
    try:
        from db.connection import fetch_all
        rows = fetch_all(
            "SELECT GraphJSON FROM tblAirNetworkData WHERE NetworkID=%s "
            "ORDER BY SavedAt DESC LIMIT 1", (network_id,))
        if not rows:
            return None
        return NetworkGraph.from_json(rows[0]["GraphJSON"], jets_by_id)
    except Exception as e:
        print(f"[AirSupply] Load error: {e}")
        return None


def db_delete_network(network_id: int):
    try:
        from db.connection import execute
        execute("DELETE FROM tblAirNetwork WHERE ID=%s", (network_id,))
    except Exception as e:
        print(f"[AirSupply] Delete error: {e}")


# ---------------------------------------------------------------------------
# Save / Load dialog
# ---------------------------------------------------------------------------

class SaveLoadDialog(QDialog):
    def __init__(self, graph: NetworkGraph, username: str,
                 current_id: Optional[int], parent=None):
        super().__init__(parent)
        self._graph      = graph
        self._username   = username
        self._current_id = current_id
        self._networks: List[Dict] = []
        self._mode       = "save"
        self._chosen_id: Optional[int] = None
        self._was_load   = False

        self.setWindowTitle("Networks — Save / Load")
        self.setMinimumSize(620, 440)
        self._build()
        self._refresh_list()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        # Toggle
        tog = QHBoxLayout()
        self._btn_save_mode = QPushButton("Save")
        self._btn_load_mode = QPushButton("Load")
        for b in (self._btn_save_mode, self._btn_load_mode):
            b.setFixedHeight(30)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            tog.addWidget(b)
        self._btn_save_mode.clicked.connect(lambda: self._set_mode("save"))
        self._btn_load_mode.clicked.connect(lambda: self._set_mode("load"))
        lay.addLayout(tog)

        # Network table
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ["ID", "Name", "Created by", "Last saved"])
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setColumnWidth(0, 40)
        self._table.setColumnWidth(2, 90)
        self._table.setColumnWidth(3, 135)
        self._table.setStyleSheet(
            "QTableWidget { font-size: 12px; }"
            f"QHeaderView::section {{ background: {DARK}; color: white; "
            "font-size: 11px; padding: 4px; border: none; }}")
        lay.addWidget(self._table)

        # Save-only fields
        self._save_w = QWidget()
        sg = QGridLayout(self._save_w)
        sg.setSpacing(6)
        sg.addWidget(QLabel("Name:"), 0, 0)
        self._le_name = QLineEdit()
        self._le_name.setPlaceholderText("e.g. Machine A — Hall 2")
        sg.addWidget(self._le_name, 0, 1)
        sg.addWidget(QLabel("Description:"), 1, 0)
        self._te_desc = QTextEdit()
        self._te_desc.setFixedHeight(56)
        sg.addWidget(self._te_desc, 1, 1)
        lay.addWidget(self._save_w)

        # Action buttons
        btn_row = QHBoxLayout()
        accent  = get_accent()
        self._btn_action = QPushButton("Save")
        self._btn_action.setFixedHeight(34)
        self._btn_action.setStyleSheet(
            f"background:{accent}; color:white; border-radius:4px; "
            "border:none; font-size:13px; font-weight:600;")
        self._btn_action.clicked.connect(self._do_action)
        btn_del = QPushButton("Delete selected")
        btn_del.setFixedHeight(34)
        btn_del.clicked.connect(self._do_delete)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(34)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_action)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        lay.addLayout(btn_row)

        self._set_mode("save")

    def _set_mode(self, mode: str):
        self._mode = mode
        accent = get_accent()
        a = (f"background:{accent}; color:white; border-radius:4px; "
             "border:none; font-weight:600;")
        i = ("background:#e8e8e8; color:#444; border-radius:4px; "
             "border:none; font-weight:400;")
        self._btn_save_mode.setStyleSheet(a if mode == "save" else i)
        self._btn_load_mode.setStyleSheet(a if mode == "load" else i)
        self._save_w.setVisible(mode == "save")
        self._btn_action.setText("Save" if mode == "save" else "Load selected")

    def _refresh_list(self):
        self._networks = db_list_networks()
        self._table.setRowCount(len(self._networks))
        for ri, row in enumerate(self._networks):
            updated = str(row.get("UpdatedAt") or "")[:16]
            for ci, val in enumerate([
                str(row.get("ID", "")), str(row.get("Name", "")),
                str(row.get("CreatedBy", "")), updated,
            ]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                self._table.setItem(ri, ci, item)
            if row.get("ID") == self._current_id:
                self._table.selectRow(ri)
                self._le_name.setText(str(row.get("Name", "")))
                self._te_desc.setPlainText(str(row.get("Description", "")))

    def _selected_row(self) -> Optional[Dict]:
        ri = self._table.currentRow()
        return self._networks[ri] if 0 <= ri < len(self._networks) else None

    def _do_action(self):
        if self._mode == "save":
            name = self._le_name.text().strip()
            if not name:
                QMessageBox.warning(self, "Name required",
                                    "Please enter a network name.")
                return
            desc = self._te_desc.toPlainText().strip()
            sel  = self._selected_row()
            nid  = sel.get("ID") if sel else None
            try:
                nid = db_save_network(name, desc, self._graph,
                                      self._username, nid)
                self._chosen_id = nid
                QMessageBox.information(self, "Saved",
                                        f"Network '{name}' saved (ID {nid}).")
                self._refresh_list()
            except Exception as e:
                QMessageBox.critical(self, "Save failed", str(e))
        else:
            sel = self._selected_row()
            if not sel:
                QMessageBox.warning(self, "Nothing selected",
                                    "Please select a network to load.")
                return
            self._chosen_id = sel.get("ID")
            self._was_load  = True
            self.accept()

    def _do_delete(self):
        sel = self._selected_row()
        if not sel:
            return
        if QMessageBox.question(
            self, "Delete", f"Delete '{sel.get('Name')}'?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            db_delete_network(sel["ID"])
            if sel.get("ID") == self._current_id:
                self._current_id = None
            self._refresh_list()

    @property
    def chosen_network_id(self) -> Optional[int]:
        return self._chosen_id

    @property
    def was_load(self) -> bool:
        return self._was_load


# ---------------------------------------------------------------------------
# Canvas
# ---------------------------------------------------------------------------

GRID = 20


class NetworkCanvas(QWidget):
    selectionChanged = Signal(object)
    graphChanged     = Signal()
    undoRequested    = Signal()    # Ctrl+Z → main screen handles it
    saveRequested    = Signal()    # Ctrl+S → main screen handles it

    def __init__(self, graph: NetworkGraph, parent=None):
        super().__init__(parent)
        self.graph          = graph
        self._drag_node:    Optional[Node]  = None
        self._drag_off:     QPointF         = QPointF()
        self._drag_start:   Optional[QPointF] = None   # for undo snap
        self._selected:     Optional[Node]  = None
        self._connecting:   bool            = False
        self._connect_from: Optional[Node]  = None
        self._zoom:         float           = 1.0
        self._offset:       QPointF         = QPointF(0, 0)
        self._pan_origin:   Optional[QPointF] = None
        self._pan_start_x   = 0.0
        self._pan_start_y   = 0.0
        self._dbl_click_node: Optional[Node] = None  # for rename
        self._hover_edge: Optional[Tuple[str,str]] = None  # edge highlight
        self._changed_nodes: Dict[str, str] = {}  # node_id → change badge text

        self.setMinimumSize(600, 500)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def _to_canvas(self, p: QPointF) -> QPointF:
        return QPointF((p.x() - self._offset.x()) / self._zoom,
                       (p.y() - self._offset.y()) / self._zoom)

    def _snap(self, v: float) -> float:
        return round(v / GRID) * GRID

    def _node_at(self, cp: QPointF) -> Optional[Node]:
        for n in reversed(list(self.graph.nodes.values())):
            if n.rect().contains(cp):
                return n
        return None

    def _edge_at(self, cp: QPointF, tol: float = 10.0) -> Optional[Tuple[str,str]]:
        """Return edge (a_id, b_id) if cp is within tol px of the L-shaped edge."""
        for a_id, b_id in self.graph.edges:
            a = self.graph.nodes.get(a_id)
            b = self.graph.nodes.get(b_id)
            if not a or not b:
                continue
            mx = (a.x + b.x) / 2
            # Three segments: (ax,ay)→(mx,ay), (mx,ay)→(mx,by), (mx,by)→(bx,by)
            segs = [
                (QPointF(a.x,a.y), QPointF(mx, a.y)),
                (QPointF(mx, a.y), QPointF(mx, b.y)),
                (QPointF(mx, b.y), QPointF(b.x, b.y)),
            ]
            for p1, p2 in segs:
                if self._pt_seg_dist(cp, p1, p2) < tol:
                    return (a_id, b_id)
        return None

    @staticmethod
    def _pt_seg_dist(p: QPointF, a: QPointF, b: QPointF) -> float:
        dx, dy = b.x()-a.x(), b.y()-a.y()
        if dx == 0 and dy == 0:
            return math.hypot(p.x()-a.x(), p.y()-a.y())
        t = max(0.0, min(1.0, ((p.x()-a.x())*dx+(p.y()-a.y())*dy)/(dx*dx+dy*dy)))
        return math.hypot(p.x()-a.x()-t*dx, p.y()-a.y()-t*dy)

    def select(self, node: Optional[Node]):
        self._selected = node
        self.selectionChanged.emit(node)
        self.update()

    def set_connect_mode(self, active: bool):
        self._connect_from = None
        self._connecting   = active
        self.setCursor(Qt.CrossCursor if active else Qt.ArrowCursor)

    def fit_to_screen(self):
        """Zoom and pan so all nodes are visible with padding."""
        if not self.graph.nodes:
            return
        xs = [n.x for n in self.graph.nodes.values()]
        ys = [n.y for n in self.graph.nodes.values()]
        pad = 60
        x_min, x_max = min(xs) - pad, max(xs) + pad
        y_min, y_max = min(ys) - pad, max(ys) + pad
        cw, ch = self.width(), self.height()
        if cw <= 0 or ch <= 0:
            return
        z = min(cw / max(x_max - x_min, 1),
                ch / max(y_max - y_min, 1))
        z = max(0.3, min(3.0, z))
        self._zoom = z
        self._offset = QPointF(
            cw/2 - z*(x_min+x_max)/2,
            ch/2 - z*(y_min+y_max)/2,
        )
        self.update()

    def start_rename(self, node: Node):
        """Show inline QLineEdit over the node for renaming."""
        from PySide6.QtWidgets import QLineEdit as _QLE
        r = node.rect()
        # Convert canvas rect to widget coords
        wx = r.x() * self._zoom + self._offset.x()
        wy = r.y() * self._zoom + self._offset.y()
        ww = r.width()  * self._zoom
        wh = r.height() * self._zoom
        le = _QLE(self)
        # Current name (first line only for multiline labels)
        cur = node.label().split("\n")[0]
        if node.kind in (NODE_SEGMENT, NODE_REDUCER):
            # For pipes/reducers, rename is a custom name override
            cur = getattr(node, "_custom_name", "") or ""
        le.setText(cur)
        le.setGeometry(int(wx)+2, int(wy)+2, max(int(ww)-4, 80), 24)
        le.setStyleSheet(
            "background:white; border:2px solid #39A650; "
            "border-radius:3px; font-size:12px; padding:1px 4px;")
        le.selectAll()
        le.show()
        le.setFocus()

        def _commit():
            txt = le.text().strip()
            if txt:
                node._custom_name = txt
                # For jet/source: update nozzle_name too
                if node.kind == NODE_JET:
                    node.nozzle_name = txt
                    node.nozzle_db_jet = None
                elif node.kind == NODE_SOURCE:
                    node._custom_name = txt
            le.deleteLater()
            self.update()
            self.graphChanged.emit()

        le.returnPressed.connect(_commit)
        le.editingFinished.connect(_commit)

    # ── mouse ─────────────────────────────────────────────────────────
    def mousePressEvent(self, ev):
        cp   = self._to_canvas(ev.position())
        node = self._node_at(cp)

        if ev.button() == Qt.MiddleButton:
            self._pan_origin  = ev.position()
            self._pan_start_x = self._offset.x()
            self._pan_start_y = self._offset.y()
            self.setCursor(Qt.ClosedHandCursor)
            return

        if ev.button() == Qt.RightButton:
            if node:
                self.select(node)
                self._show_node_menu(node, ev.globalPosition().toPoint())
            else:
                edge = self._edge_at(cp)
                if edge:
                    self._show_edge_menu(edge, ev.globalPosition().toPoint())
            return

        if ev.button() == Qt.LeftButton:
            if self._connecting:
                if node:
                    if self._connect_from is None:
                        self._connect_from = node
                    elif self._connect_from.id != node.id:
                        self.graph.add_edge(self._connect_from.id, node.id)
                        self._connect_from = None
                        self._connecting   = False
                        self.setCursor(Qt.ArrowCursor)
                        self.graph.solve()
                        self.graphChanged.emit()
                        self.update()
            else:
                self.select(node)
                if node:
                    self._drag_node  = node
                    self._drag_start = QPointF(node.x, node.y)
                    self._drag_off   = QPointF(cp.x() - node.x,
                                               cp.y() - node.y)
                else:
                    self._pan_origin  = ev.position()
                    self._pan_start_x = self._offset.x()
                    self._pan_start_y = self._offset.y()
                    self.setCursor(Qt.ClosedHandCursor)

    def mouseDoubleClickEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            cp   = self._to_canvas(ev.position())
            node = self._node_at(cp)
            if node:
                self.start_rename(node)

    def mouseMoveEvent(self, ev):
        if self._pan_origin is not None:
            dx = ev.position().x() - self._pan_origin.x()
            dy = ev.position().y() - self._pan_origin.y()
            self._offset = QPointF(self._pan_start_x + dx,
                                   self._pan_start_y + dy)
            self.update()
            return
        if self._drag_node:
            cp = self._to_canvas(ev.position())
            self._drag_node.x = self._snap(cp.x() - self._drag_off.x())
            self._drag_node.y = self._snap(cp.y() - self._drag_off.y())
            self.update()
            return
        # Hover: highlight edge under cursor when no node is hovered
        cp   = self._to_canvas(ev.position())
        node = self._node_at(cp)
        if not node and not self._connecting:
            new_hover = self._edge_at(cp)
            if new_hover != self._hover_edge:
                self._hover_edge = new_hover
                self.setCursor(Qt.PointingHandCursor if new_hover
                               else Qt.ArrowCursor)
                self.update()
        elif node and self._hover_edge:
            self._hover_edge = None
            self.setCursor(Qt.ArrowCursor)
            self.update()

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MiddleButton:
            self._pan_origin = None
            self.setCursor(Qt.ArrowCursor)
        if ev.button() == Qt.LeftButton:
            if self._pan_origin is not None and self._drag_node is None:
                self._pan_origin = None
                self.setCursor(Qt.ArrowCursor)
            if self._drag_node:
                # Push move to undo if position changed
                if self._drag_start:
                    old = self._drag_start
                    new = QPointF(self._drag_node.x, self._drag_node.y)
                    if abs(old.x()-new.x()) > 1 or abs(old.y()-new.y()) > 1:
                        self.graphChanged.emit()
                self._drag_start = None
                self._drag_node  = None
                self.graph.solve()
                self.graphChanged.emit()

    def wheelEvent(self, ev):
        f = 1.12 if ev.angleDelta().y() > 0 else 1 / 1.12
        c = ev.position()
        self._offset = QPointF(
            c.x() - f * (c.x() - self._offset.x()),
            c.y() - f * (c.y() - self._offset.y()))
        self._zoom = max(0.3, min(3.0, self._zoom * f))
        self.update()

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key_Delete and self._selected:
            nid = self._selected.id
            self.select(None)
            self.graph.remove_node(nid)
            self.graph.solve()
            self.graphChanged.emit()
            self.update()
        elif ev.modifiers() == Qt.ControlModifier and ev.key() == Qt.Key_Z:
            self.undoRequested.emit()
        elif ev.modifiers() == Qt.ControlModifier and ev.key() == Qt.Key_S:
            self.saveRequested.emit()

    # ── context menus ─────────────────────────────────────────────────
    def _show_node_menu(self, node: Node, gpos):
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu{background:#fff;border:1px solid #ddd;border-radius:4px;}"
            "QMenu::item{padding:6px 20px;font-size:12px;}"
            "QMenu::item:selected{background:#f0f7ff;color:#1D3557;}")
        a_rename = menu.addAction("✏️  Rename")
        a_dup    = menu.addAction("⧉  Duplicate")
        menu.addSeparator()
        a_del    = menu.addAction("🗑  Delete")
        action = menu.exec(gpos)
        if action == a_rename:
            self.start_rename(node)
        elif action == a_dup:
            self._duplicate_node(node)
        elif action == a_del:
            nid = node.id
            self.select(None)
            self.graph.remove_node(nid)
            self.graph.solve()
            self.graphChanged.emit()
            self.update()

    def _show_edge_menu(self, edge: Tuple[str,str], gpos):
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu{background:#fff;border:1px solid #ddd;border-radius:4px;}"
            "QMenu::item{padding:6px 20px;font-size:12px;}"
            "QMenu::item:selected{background:#fff0f0;color:#c62828;}")
        a_del = menu.addAction("🗑  Delete connection")
        action = menu.exec(gpos)
        if action == a_del:
            self.graph.remove_edge(edge[0], edge[1])
            self.graph.solve()
            self.graphChanged.emit()
            self.update()

    def _duplicate_node(self, node: Node):
        import copy
        new_node = copy.deepcopy(node)
        new_node.id = str(uuid.uuid4())[:8]
        new_node.x  = node.x + 40
        new_node.y  = node.y + 40
        # Reset computed results
        for attr in ("result_flow_nl_s","result_v","result_v_out",
                     "result_dp","result_dp_cum","result_p_inlet",
                     "result_p_required","result_dn_rec"):
            setattr(new_node, attr, 0.0 if attr != "result_dn_rec" else 0)
        self.graph.add_node(new_node)
        self.select(new_node)
        self.graph.solve()
        self.graphChanged.emit()
        self.update()

    # ── paint ─────────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#f0f2f5"))

        gstep = int(GRID * self._zoom)
        if gstep > 8:
            p.setPen(QPen(QColor("#d0d4da"), 1))
            ox = int(self._offset.x()) % gstep
            oy = int(self._offset.y()) % gstep
            for gx in range(ox, self.width(), gstep):
                for gy in range(oy, self.height(), gstep):
                    p.drawPoint(gx, gy)

        p.save()
        p.translate(self._offset)
        p.scale(self._zoom, self._zoom)
        for a_id, b_id in self.graph.edges:
            a = self.graph.nodes.get(a_id)
            b = self.graph.nodes.get(b_id)
            if a and b:
                self._draw_edge(p, a, b)
        for node in self.graph.nodes.values():
            self._draw_node(p, node)
        p.restore()
        self._draw_legend(p)
        p.end()

    def _draw_edge(self, p: QPainter, a: Node, b: Node):
        mx = (a.x + b.x) / 2

        # Hover highlight
        is_hover = (self._hover_edge == (a.id, b.id))

        # Color by velocity of the downstream node
        # Green: 20–30 m/s  |  Orange: 15–20 or 30–35 m/s  |  Red: outside
        v = b.result_v if b.kind in (NODE_SEGMENT, NODE_REDUCER) else 0.0
        if v <= 0:
            edge_color = QColor("#455a64")
        elif 20.0 <= v <= 30.0:
            edge_color = QColor("#2e7d32")   # green — optimal
        elif (15.0 <= v < 20.0) or (30.0 < v <= 35.0):
            edge_color = QColor("#e65100")   # orange — acceptable
        else:
            edge_color = QColor("#c62828")   # red — too slow or too fast

        # Hover: thicker line + dashed delete hint
        lw = 3.5 if is_hover else 2.0
        pen = QPen(edge_color, lw)
        if is_hover:
            pen.setStyle(Qt.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        pts = [QPointF(a.x, a.y), QPointF(mx, a.y),
               QPointF(mx, b.y),  QPointF(b.x, b.y)]
        for i in range(3):
            p.drawLine(pts[i], pts[i+1])

        # Arrow
        ang = math.atan2(b.y - a.y, b.x - a.x)
        sz, tip = 8, QPointF(b.x, b.y)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(edge_color))
        p.drawPolygon(QPolygonF([
            tip,
            QPointF(tip.x() - sz*math.cos(ang-0.4),
                    tip.y() - sz*math.sin(ang-0.4)),
            QPointF(tip.x() - sz*math.cos(ang+0.4),
                    tip.y() - sz*math.sin(ang+0.4)),
        ]))

        # Hover label "Right-click to delete"
        if is_hover:
            hint = "Right-click to delete"
            p.setFont(QFont("Arial", 7))
            fw = QFontMetrics(p.font()).horizontalAdvance(hint) + 8
            fh = 14
            fx = (a.x + b.x) / 2 - fw / 2
            fy = (a.y + b.y) / 2 - fh - 4
            p.setBrush(QBrush(QColor("#263238")))
            p.drawRoundedRect(QRectF(fx, fy, fw, fh), 3, 3)
            p.setPen(QPen(Qt.white, 1))
            p.drawText(QRectF(fx, fy, fw, fh), Qt.AlignCenter, hint)
            p.setPen(QPen(edge_color.darker(130), 1))

        # Flow label
        if b.result_flow_nl_s > 0 and not is_hover:
            lbl = f"{b.result_flow_nl_s * 60:.1f} Nl/min"
            p.setFont(QFont("Arial", 8))
            fm  = QFontMetrics(p.font())
            tw  = fm.horizontalAdvance(lbl)
            p.setPen(QPen(edge_color.darker(130), 1))
            p.drawText(QRectF(mx - tw/2 - 2, (a.y+b.y)/2 - 12, tw+4, 13),
                       Qt.AlignCenter, lbl)

    def _draw_node(self, p: QPainter, node: Node):
        accent = get_accent()
        color  = QColor(_NODE_COLORS.get(node.kind, "#607d8b"))
        r      = node.rect()
        is_sel = self._selected and self._selected.id == node.id

        # Shadow
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 35)))
        p.drawRoundedRect(QRectF(r.x()+3, r.y()+3, r.width(), r.height()), 6, 6)

        # Body
        p.setBrush(QBrush(color))
        p.setPen(QPen(QColor(accent), 3) if is_sel
                 else QPen(color.darker(130), 1))
        p.drawRoundedRect(r, 6, 6)

        # Changed-node gold ring (optimization highlight)
        change_badge = self._changed_nodes.get(node.id, "")
        if change_badge:
            p.setPen(QPen(QColor("#FFD600"), 3))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r.adjusted(-2, -2, 2, 2), 8, 8)
            # Change badge top-left
            p.setFont(QFont("Arial", 7, QFont.Bold))
            bw = QFontMetrics(p.font()).horizontalAdvance(change_badge) + 8
            bh = 13
            br = QRectF(r.left(), r.top() - bh - 1, bw, bh)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor("#FFD600")))
            p.drawRoundedRect(br, 3, 3)
            p.setPen(QPen(QColor("#1D3557"), 1))
            p.drawText(br, Qt.AlignCenter, change_badge)

        # Label area — jet and source leave room for inlet strip
        lbl_rect = (QRectF(r.x()+2, r.y()+2, r.width()-4, r.height()-18)
                    if node.kind in (NODE_JET, NODE_SOURCE)
                    else r.adjusted(2, 2, -2, -2))
        p.setPen(QPen(Qt.white, 1))
        p.setFont(QFont("Arial", 8, QFont.Bold))
        p.drawText(lbl_rect, Qt.AlignCenter | Qt.TextWordWrap, node.label())

        # Flow badge (top-right)
        if node.result_flow_nl_s > 0:
            bt = f"{node.result_flow_nl_s * 60:.1f} Nl/m"
            p.setFont(QFont("Arial", 7))
            bw = QFontMetrics(p.font()).horizontalAdvance(bt) + 6
            bh = 13
            br = QRectF(r.right()-bw-2, r.top()-bh/2, bw, bh)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor("#263238")))
            p.drawRoundedRect(br, 3, 3)
            p.setPen(QPen(Qt.white, 1))
            p.drawText(br, Qt.AlignCenter, bt)

        # Multi-parent warning (physics error: flow would be double-counted)
        if len(self.graph.parents(node.id)) > 1:
            wr = QRectF(r.right()-6, r.top()-6, 16, 16)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor("#ff6f00")))
            p.drawEllipse(wr)
            p.setPen(QPen(Qt.white, 1))
            p.setFont(QFont("Arial", 8, QFont.Bold))
            p.drawText(wr, Qt.AlignCenter, "2")

        # Source: required pressure + flow badge
        if node.kind == NODE_SOURCE:
            preq = node.result_p_required
            flow = node.result_flow_nl_s
            if preq > 0 or flow > 0:
                lines = []
                if preq > 0:
                    lines.append(f"≥ {preq:.2f} bar")
                if flow > 0:
                    lines.append(f"{flow*60:.1f} Nl/min")
                strip = QRectF(r.x()+1, r.bottom()-17, r.width()-2, 16)
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(QColor("#0d2137")))
                p.drawRoundedRect(strip, 4, 4)
                p.setPen(QPen(Qt.white, 1))
                p.setFont(QFont("Arial", 7, QFont.Bold))
                p.drawText(strip, Qt.AlignCenter, "  ".join(lines))
        if node.kind == NODE_SEGMENT:
            d_use = node.seg_diam if node.seg_diam > 0 else node.result_dn_rec
            warn  = node.result_v > 0 and not (15.0 <= node.result_v <= 35.0)
            if d_use > 0:
                star = "★" if node.seg_diam == 0 else ""
                dn_t = f"ø{int(d_use)}mm{star}"
                p.setFont(QFont("Arial", 7, QFont.Bold))
                bw = QFontMetrics(p.font()).horizontalAdvance(dn_t) + 8
                bh = 13
                br = QRectF(r.center().x()-bw/2, r.bottom()-bh/2, bw, bh)
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(QColor("#e53935") if warn else QColor("#1D3557")))
                p.drawRoundedRect(br, 3, 3)
                p.setPen(QPen(Qt.white, 1))
                p.drawText(br, Qt.AlignCenter, dn_t)
            if warn:
                wr = QRectF(r.left()-6, r.top()-6, 14, 14)
                p.setPen(Qt.NoPen); p.setBrush(QBrush(QColor("#e53935")))
                p.drawEllipse(wr)
                p.setPen(QPen(Qt.white, 1))
                p.setFont(QFont("Arial", 9, QFont.Bold))
                p.drawText(wr, Qt.AlignCenter, "!")

        # Reducer: trapezoid overlay + ΔP badge
        if node.kind == NODE_REDUCER:
            inset = 10
            trap = QPolygonF([
                QPointF(r.left(),  r.top()),
                QPointF(r.right(), r.top()    + inset),
                QPointF(r.right(), r.bottom() - inset),
                QPointF(r.left(),  r.bottom()),
            ])
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor("#E76F51")))
            p.drawPolygon(trap)
            if is_sel:
                p.setPen(QPen(QColor(accent), 3))
                p.setBrush(Qt.NoBrush)
                p.drawPolygon(trap)
            p.setPen(QPen(Qt.white, 1))
            p.setFont(QFont("Arial", 8, QFont.Bold))
            p.drawText(r.adjusted(2, 2, -2, -2),
                       Qt.AlignCenter | Qt.TextWordWrap, node.label())
            dp = node.result_dp
            if dp > 0:
                bt = f"ΔP {dp:.4f} bar"
                p.setFont(QFont("Arial", 7))
                bw = QFontMetrics(p.font()).horizontalAdvance(bt) + 8
                bh = 13
                br = QRectF(r.center().x()-bw/2, r.bottom()-bh/2, bw, bh)
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(QColor("#bf360c")))
                p.drawRoundedRect(br, 3, 3)
                p.setPen(QPen(Qt.white, 1))
                p.drawText(br, Qt.AlignCenter, bt)

        # Jet: inlet strip — shows set pressure + cumulative loss info
        if node.kind == NODE_JET:
            dp_cum  = node.result_dp_cum
            p_set   = node.nozzle_pressure
            p_avail = node.result_p_inlet   # actual pressure arriving at jet
            ok      = p_avail >= p_set - 0.001
            strip   = QRectF(r.x()+1, r.bottom()-17, r.width()-2, 16)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor("#1b5e20") if ok else QColor("#b71c1c")))
            p.drawRoundedRect(strip, 4, 4)
            p.setPen(QPen(Qt.white, 1))
            p.setFont(QFont("Arial", 7))
            txt = (f"{p_avail:.2f} bar (need {p_set:.2f})  ✓"
                   if ok else
                   f"⚠ {p_avail:.2f} bar < {p_set:.2f} bar needed")
            p.drawText(strip, Qt.AlignCenter, txt)

    def _draw_legend(self, p: QPainter):
        items = [
            (NODE_SOURCE,  "Source"),
            (NODE_SEGMENT, "Pipe  (★=auto ø)"),
            (NODE_SPLIT,   "Y-Split"),
            (NODE_REDUCER, "Reducer  (Borda-Carnot ΔP)"),
            (NODE_JET,     "Jet  (strip=set pressure)"),
        ]
        x, y = 12, self.height() - 12 - (len(items) + 3) * 18
        for kind, lbl in items:
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(_NODE_COLORS[kind])))
            p.drawRoundedRect(QRectF(x, y, 14, 12), 2, 2)
            p.setPen(QPen(QColor("#37474f"), 1))
            p.setFont(QFont("Arial", 9))
            p.drawText(x+18, y+10, lbl)
            y += 18
        # Velocity color guide
        y += 4
        p.setFont(QFont("Arial", 9))
        for col, lbl in [("#2e7d32", "20–30 m/s  optimal"),
                          ("#e65100", "15–20 / 30–35 m/s  acceptable"),
                          ("#c62828", "< 15 or > 35 m/s  out of range")]:
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(col)))
            p.drawRoundedRect(QRectF(x, y, 14, 4), 1, 1)
            p.setPen(QPen(QColor("#37474f"), 1))
            p.drawText(x+18, y+5, lbl)
            y += 14


# ---------------------------------------------------------------------------
# Node property panel
# ---------------------------------------------------------------------------

class NodePropertyPanel(QWidget):
    nodeChanged    = Signal()
    opcostChanged  = Signal(float, float, float, float)  # hours, days, price, eta

    def __init__(self, jets: List[Dict], parent=None):
        super().__init__(parent)
        self._node: Optional[Node] = None
        self._jets  = jets

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("Node Properties")
        title.setStyleSheet(
            f"background:{DARK}; color:white; font-size:13px; "
            "font-weight:600; padding:6px 12px;")
        layout.addWidget(title)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack, 1)

        empty = QLabel("Select a node\nto edit its properties.")
        empty.setAlignment(Qt.AlignCenter)
        empty.setStyleSheet("color:#aaa; font-size:12px; padding:30px;")
        self._stack.addWidget(empty)                     # 0
        self._stack.addWidget(self._build_seg_page())    # 1
        self._stack.addWidget(self._build_jet_page())    # 2
        self._stack.addWidget(self._build_src_page())    # 3
        self._stack.addWidget(self._build_reducer_page()) # 4

    # ── helpers ───────────────────────────────────────────────────────
    def _sec(self, title: str) -> QGroupBox:
        gb = QGroupBox(title)
        gb.setStyleSheet(
            "QGroupBox{font-size:12px;font-weight:600;color:#333;"
            "border:1px solid #d0d0d0;border-radius:4px;margin-top:6px;"
            "padding-top:6px;}"
            "QGroupBox::title{subcontrol-origin:margin;left:8px;padding:0 4px;}")
        return gb

    def _lbl(self, txt: str) -> QLabel:
        l = QLabel(txt)
        l.setMinimumWidth(160)
        l.setWordWrap(True)
        l.setStyleSheet("color:#555;font-size:11px;")
        return l

    def _val_lbl(self) -> QLabel:
        l = QLabel("—")
        l.setStyleSheet(
            f"color:{get_accent()};font-size:11px;font-weight:600;")
        return l

    # ── segment page ──────────────────────────────────────────────────
    def _build_seg_page(self) -> QWidget:
        w = QWidget(); w.setStyleSheet(f"background:{CARD_BG};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14,14,14,14); lay.setSpacing(10)

        gb = self._sec("Pipe Segment")
        g  = QGridLayout(gb); g.setSpacing(6)

        self._seg_len = QDoubleSpinBox()
        self._seg_len.setRange(0.1,9999); self._seg_len.setSuffix(" m")
        self._seg_len.setDecimals(1); self._seg_len.setValue(5.0)
        self._seg_len.valueChanged.connect(self._on_seg)

        self._seg_diam = QDoubleSpinBox()
        self._seg_diam.setRange(0,200); self._seg_diam.setDecimals(0)
        self._seg_diam.setSpecialValueText("Auto (recommended)")
        self._seg_diam.setSuffix(" mm")
        self._seg_diam.valueChanged.connect(self._on_seg)

        for row,(lbl,w2) in enumerate([
            ("Length",                  self._seg_len),
            ("Inner diam. (0=auto)",    self._seg_diam),
        ]):
            g.addWidget(self._lbl(lbl), row, 0)
            g.addWidget(w2, row, 1)
        lay.addWidget(gb)

        fit_gb = self._sec("Fittings (equivalent length)")
        fit_g  = QGridLayout(fit_gb); fit_g.setSpacing(6)
        self._seg_b90 = QSpinBox(); self._seg_b90.setRange(0, 50)
        self._seg_b90.setSuffix(" ×"); self._seg_b90.setValue(0)
        self._seg_b90.valueChanged.connect(self._on_seg)
        self._seg_b45 = QSpinBox(); self._seg_b45.setRange(0, 50)
        self._seg_b45.setSuffix(" ×"); self._seg_b45.setValue(0)
        self._seg_b45.valueChanged.connect(self._on_seg)
        self._seg_leq_lbl = QLabel("L_eq: —")
        self._seg_leq_lbl.setStyleSheet(
            f"color:{get_accent()}; font-size:11px; font-weight:600;")
        for row,(lbl,w2) in enumerate([
            ("90° elbows  (L/D=30)", self._seg_b90),
            ("45° elbows  (L/D=16)", self._seg_b45),
        ]):
            fit_g.addWidget(self._lbl(lbl), row, 0)
            fit_g.addWidget(w2, row, 1)
        fit_g.addWidget(self._lbl("Effective length"), 2, 0)
        fit_g.addWidget(self._seg_leq_lbl, 2, 1)
        lay.addWidget(fit_gb)

        res_gb = self._sec("Computed results")
        rg = QGridLayout(res_gb); rg.setSpacing(4)
        self._sr: Dict[str,QLabel] = {}
        for row,key in enumerate([
            "Inlet pressure (computed)",
            "Rec. inner diameter",
            "Velocity",
            "Segment ΔP",
            "Cumulative ΔP (source→here)",
            "Total flow",
        ]):
            lk = self._lbl(key+":")
            lv = self._val_lbl()
            rg.addWidget(lk, row, 0); rg.addWidget(lv, row, 1)
            self._sr[key] = lv
        lay.addWidget(res_gb)
        lay.addStretch()
        return w

    # ── jet page ──────────────────────────────────────────────────────
    def _build_jet_page(self) -> QWidget:
        w = QWidget(); w.setStyleSheet(f"background:{CARD_BG};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14,14,14,14); lay.setSpacing(8)

        tog = QHBoxLayout()
        self._nz_db_btn  = QPushButton("From DB")
        self._nz_gen_btn = QPushButton("Generic")
        for b in (self._nz_db_btn, self._nz_gen_btn):
            b.setFixedHeight(28)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            tog.addWidget(b)
        self._nz_db_btn.clicked.connect(lambda: self._nz_mode("db"))
        self._nz_gen_btn.clicked.connect(lambda: self._nz_mode("generic"))
        lay.addLayout(tog)

        self._nz_db_gb = self._sec("Jet from Database")
        dbg = QGridLayout(self._nz_db_gb); dbg.setSpacing(6)
        self._nz_cb = QComboBox()
        self._nz_cb.setStyleSheet("QComboBox{font-size:12px;}")
        self._nz_cb.currentIndexChanged.connect(self._on_nz_db)
        self._nz_db_info = QLabel("—")
        self._nz_db_info.setStyleSheet("color:#666;font-size:11px;")
        dbg.addWidget(self._lbl("Jet type"), 0, 0)
        dbg.addWidget(self._nz_cb, 0, 1)
        dbg.addWidget(self._nz_db_info, 1, 0, 1, 2)
        lay.addWidget(self._nz_db_gb)

        self._nz_gen_gb = self._sec("Generic Jet")
        gg = QGridLayout(self._nz_gen_gb); gg.setSpacing(6)
        self._nz_name   = QLineEdit(); self._nz_name.setPlaceholderText("Name")
        self._nz_name.textChanged.connect(self._on_nz)
        self._nz_hole_d = QDoubleSpinBox()
        self._nz_hole_d.setRange(0.1,20); self._nz_hole_d.setSuffix(" mm")
        self._nz_hole_d.setDecimals(2); self._nz_hole_d.setValue(1.0)
        self._nz_hole_d.valueChanged.connect(self._on_nz)
        self._nz_holes  = QSpinBox()
        self._nz_holes.setRange(1,50); self._nz_holes.setValue(1)
        self._nz_holes.valueChanged.connect(self._on_nz)
        for row,(lbl,w2) in enumerate([
            ("Name", self._nz_name),
            ("Hole diameter", self._nz_hole_d),
            ("No. of holes",  self._nz_holes),
        ]):
            gg.addWidget(self._lbl(lbl), row, 0); gg.addWidget(w2, row, 1)
        lay.addWidget(self._nz_gen_gb)

        com_gb = self._sec("Common")
        cg = QGridLayout(com_gb); cg.setSpacing(6)
        self._nz_count = QSpinBox(); self._nz_count.setRange(1,9999)
        self._nz_count.setValue(1); self._nz_count.valueChanged.connect(self._on_nz)
        self._nz_press = QDoubleSpinBox()
        self._nz_press.setRange(0.1,20); self._nz_press.setSuffix(" bar")
        self._nz_press.setDecimals(2); self._nz_press.setValue(4.0)
        self._nz_press.valueChanged.connect(self._on_nz)
        self._nz_cd = QDoubleSpinBox()
        self._nz_cd.setRange(0.3,1.0); self._nz_cd.setDecimals(2)
        self._nz_cd.setSingleStep(0.05); self._nz_cd.setValue(0.65)
        self._nz_cd.valueChanged.connect(self._on_nz)
        for row,(lbl,w2) in enumerate([
            ("Count (# jets)",       self._nz_count),
            ("Set pressure",         self._nz_press),
            ("Discharge coeff. Cd",  self._nz_cd),
        ]):
            cg.addWidget(self._lbl(lbl), row, 0); cg.addWidget(w2, row, 1)
        lay.addWidget(com_gb)

        res_gb = self._sec("Computed results")
        rg = QGridLayout(res_gb); rg.setSpacing(4)
        self._jr: Dict[str,QLabel] = {}
        for row,key in enumerate([
            "Flow (total)",
            "Inlet pressure (set)",
            "Required extra pressure (line losses)",
        ]):
            lk = self._lbl(key+":"); lv = self._val_lbl()
            rg.addWidget(lk, row, 0); rg.addWidget(lv, row, 1)
            self._jr[key] = lv
        lay.addWidget(res_gb)
        lay.addStretch()
        return w

    # ── source page ───────────────────────────────────────────────────
    def _build_src_page(self) -> QWidget:
        w = QWidget(); w.setStyleSheet(f"background:{CARD_BG};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14,14,14,14); lay.setSpacing(10)

        info = QLabel("Source node — compressor / main air inlet.\n"
                      "Set the compressor outlet pressure here; pipe pressures\n"
                      "are computed automatically (top-down).")
        info.setWordWrap(True)
        info.setStyleSheet("color:#666;font-size:11px;padding:0 0 4px 0;")
        lay.addWidget(info)

        src_gb = self._sec("Compressor")
        sg = QGridLayout(src_gb); sg.setSpacing(6)
        self._src_press = QDoubleSpinBox()
        self._src_press.setRange(0.5, 20.0)
        self._src_press.setSuffix(" bar")
        self._src_press.setDecimals(2)
        self._src_press.setValue(6.0)
        self._src_press.valueChanged.connect(self._on_src_press)
        sg.addWidget(self._lbl("Compressor pressure"), 0, 0)
        sg.addWidget(self._src_press, 0, 1)
        lay.addWidget(src_gb)

        accent = get_accent()
        def _kpi(title, unit):
            f = QFrame()
            f.setStyleSheet(
                "QFrame{background:#f4f8ff;border:1px solid #d0ddf0;"
                "border-radius:6px;}")
            fl = QVBoxLayout(f)
            fl.setContentsMargins(10,8,10,8); fl.setSpacing(2)
            t = QLabel(title); t.setWordWrap(True)
            t.setStyleSheet("color:#666;font-size:10px;border:none;background:transparent;")
            v = QLabel("—")
            v.setStyleSheet(
                f"color:{accent};font-size:18px;font-weight:700;"
                "border:none;background:transparent;")
            u = QLabel(unit)
            u.setStyleSheet("color:#999;font-size:10px;border:none;background:transparent;")
            fl.addWidget(t); fl.addWidget(v); fl.addWidget(u)
            return f, v

        r1 = QHBoxLayout(); r1.setSpacing(8)
        kf1, self._sv_nlmin = _kpi("Total flow demand", "Nl/min")
        kf2, self._sv_m3h   = _kpi("Total flow demand", "m³/h")
        r1.addWidget(kf1,1); r1.addWidget(kf2,1); lay.addLayout(r1)

        r2 = QHBoxLayout(); r2.setSpacing(8)
        kf3, self._sv_res   = _kpi("Min. compressor output\n(+20% reserve)","m³/h")
        kf4, self._sv_press = _kpi("Required working pressure","bar")
        r2.addWidget(kf3,1); r2.addWidget(kf4,1); lay.addLayout(r2)

        det = self._sec("Network summary")
        dg  = QGridLayout(det); dg.setSpacing(5)
        dg.setColumnMinimumWidth(0,200)
        self._slbls: Dict[str,QLabel] = {}
        sv = f"color:{accent};font-size:11px;font-weight:600;"
        for row,(key,lbl) in enumerate([
            ("n_jets",     "Active jet nodes"),
            ("n_segs",     "Pipe segments"),
            ("tank",       "Rec. receiver tank (V=Q×6)"),
        ]):
            lk = self._lbl(lbl+":"); lv = QLabel("—"); lv.setStyleSheet(sv)
            dg.addWidget(lk,row,0); dg.addWidget(lv,row,1)
            self._slbls[key] = lv
        lay.addWidget(det)

        self._src_guide = QLabel()
        self._src_guide.setWordWrap(True)
        self._src_guide.setStyleSheet(
            "color:#444;font-size:11px;padding:6px 8px;"
            "background:#fffbea;border:1px solid #ffe082;border-radius:4px;")
        lay.addWidget(self._src_guide)

        # ── Operating cost section ────────────────────────────────────
        cost_gb = self._sec("Operating Cost (electricity)")
        cg = QGridLayout(cost_gb); cg.setSpacing(6)
        cg.setColumnMinimumWidth(0, 180)

        self._oc_hours   = QDoubleSpinBox()
        self._oc_hours.setRange(0.1, 24); self._oc_hours.setValue(16)
        self._oc_hours.setSuffix(" h/day"); self._oc_hours.setDecimals(1)
        self._oc_hours.valueChanged.connect(self._upd_opcost)

        self._oc_days    = QDoubleSpinBox()
        self._oc_days.setRange(1, 365); self._oc_days.setValue(250)
        self._oc_days.setSuffix(" days/yr"); self._oc_days.setDecimals(0)
        self._oc_days.valueChanged.connect(self._upd_opcost)

        self._oc_price   = QDoubleSpinBox()
        self._oc_price.setRange(0.01, 5.0); self._oc_price.setValue(0.22)
        self._oc_price.setSuffix(" CHF/kWh"); self._oc_price.setDecimals(3)
        self._oc_price.valueChanged.connect(self._upd_opcost)

        self._oc_eta     = QDoubleSpinBox()
        self._oc_eta.setRange(0.1, 1.0); self._oc_eta.setValue(0.70)
        self._oc_eta.setSuffix("  (η)"); self._oc_eta.setDecimals(2)
        self._oc_eta.setSingleStep(0.05)
        self._oc_eta.valueChanged.connect(self._upd_opcost)

        for row, (lbl, w2) in enumerate([
            ("Operating hours",        self._oc_hours),
            ("Operating days / year",  self._oc_days),
            ("Electricity price",      self._oc_price),
            ("Compressor efficiency η", self._oc_eta),
        ]):
            lk = QLabel(lbl); lk.setStyleSheet("color:#555;font-size:11px;")
            cg.addWidget(lk, row, 0); cg.addWidget(w2, row, 1)
        lay.addWidget(cost_gb)

        # Cost result KPIs
        cost_res_gb = self._sec("Annual Cost")
        crg = QGridLayout(cost_res_gb); crg.setSpacing(4)
        crg.setColumnMinimumWidth(0, 180)
        self._oc_res: Dict[str, QLabel] = {}
        for row, key in enumerate(["Compressor power", "Operating hours/year",
                                    "Energy consumption", "Annual cost"]):
            lk = QLabel(key+":"); lk.setStyleSheet("color:#555;font-size:11px;")
            lv = QLabel("—")
            lv.setStyleSheet(
                f"color:{get_accent()};font-size:11px;font-weight:600;")
            crg.addWidget(lk, row, 0); crg.addWidget(lv, row, 1)
            self._oc_res[key] = lv
        # Big cost label
        self._oc_total = QLabel("—")
        self._oc_total.setStyleSheet(
            f"color:{get_accent()};font-size:20px;font-weight:700;"
            "padding:4px 0;")
        crg.addWidget(self._oc_total, len(self._oc_res), 0, 1, 2)
        # Nm³ cost label
        self._oc_nm3 = QLabel("—")
        self._oc_nm3.setStyleSheet(
            "color:#555;font-size:11px;font-style:italic;padding:0;")
        crg.addWidget(self._oc_nm3, len(self._oc_res) + 1, 0, 1, 2)
        lay.addWidget(cost_res_gb)
        lay.addStretch()
        return w

    # ── reducer page ──────────────────────────────────────────────────
    def _build_reducer_page(self) -> QWidget:
        w = QWidget(); w.setStyleSheet(f"background:{CARD_BG};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14,14,14,14); lay.setSpacing(10)

        gb = self._sec("Reducer / Expander")
        g  = QGridLayout(gb); g.setSpacing(6)

        note = QLabel(
            "Pressure loss calculated via Borda-Carnot.\n"
            "Contraction (d_in > d_out): coeff = 0.5\n"
            "Expansion   (d_in < d_out): (v_in − v_out)²"
        )
        note.setStyleSheet("color:#666; font-size:10px;")
        note.setWordWrap(True)
        g.addWidget(note, 0, 0, 1, 2)

        self._red_d_in = QDoubleSpinBox()
        self._red_d_in.setRange(1,200); self._red_d_in.setSuffix(" mm")
        self._red_d_in.setDecimals(0); self._red_d_in.setValue(25.0)
        self._red_d_in.valueChanged.connect(self._on_red)

        self._red_d_out = QDoubleSpinBox()
        self._red_d_out.setRange(1,200); self._red_d_out.setSuffix(" mm")
        self._red_d_out.setDecimals(0); self._red_d_out.setValue(13.0)
        self._red_d_out.valueChanged.connect(self._on_red)

        for row,(lbl,w2) in enumerate([
            ("Inlet diameter",    self._red_d_in),
            ("Outlet diameter",   self._red_d_out),
        ], start=1):
            g.addWidget(self._lbl(lbl), row, 0)
            g.addWidget(w2, row, 1)
        lay.addWidget(gb)

        res_gb = self._sec("Computed results")
        rg = QGridLayout(res_gb); rg.setSpacing(4)
        self._rr: Dict[str,QLabel] = {}
        for row,key in enumerate([
            "Velocity (inlet)",
            "Velocity (outlet)",
            "Pressure drop (ΔP)",
            "Cumulative ΔP (source→here)",
            "Total flow",
        ]):
            lk = self._lbl(key+":"); lv = self._val_lbl()
            rg.addWidget(lk, row, 0); rg.addWidget(lv, row, 1)
            self._rr[key] = lv
        lay.addWidget(res_gb)
        lay.addStretch()
        return w

    # ── public API ────────────────────────────────────────────────────
    def set_jets(self, jets: List[Dict]):
        self._jets = jets
        self._refresh_combo()

    def _refresh_combo(self):
        self._nz_cb.blockSignals(True)
        self._nz_cb.clear()
        self._nz_cb.addItem("— select —", None)
        for jet in self._jets:
            self._nz_cb.addItem(
                str(jet.get("Jet") or f"ID {jet.get('ID')}"), jet)
        self._nz_cb.blockSignals(False)

    def load_node(self, node: Optional[Node]):
        self._node = node
        if node is None or node.kind == NODE_SPLIT:
            self._stack.setCurrentIndex(0)
            return
        if node.kind == NODE_SOURCE:
            self._stack.setCurrentIndex(3)
            self._src_press.blockSignals(True)
            self._src_press.setValue(getattr(node, "source_pressure", 6.0))
            self._src_press.blockSignals(False)
            return
        if node.kind == NODE_REDUCER:
            self._stack.setCurrentIndex(4)
            for w in (self._red_d_in, self._red_d_out):
                w.blockSignals(True)
            self._red_d_in.setValue(node.red_d_in)
            self._red_d_out.setValue(node.red_d_out)
            for w in (self._red_d_in, self._red_d_out):
                w.blockSignals(False)
            self._upd_reducer(node)
            return
        if node.kind == NODE_SEGMENT:
            self._stack.setCurrentIndex(1)
            for w in (self._seg_len, self._seg_diam,
                      self._seg_b90, self._seg_b45):
                w.blockSignals(True)
            self._seg_len.setValue(node.seg_length)
            self._seg_diam.setValue(node.seg_diam)
            self._seg_b90.setValue(node.seg_bends_90)
            self._seg_b45.setValue(node.seg_bends_45)
            for w in (self._seg_len, self._seg_diam,
                      self._seg_b90, self._seg_b45):
                w.blockSignals(False)
            self._upd_seg(node)
        elif node.kind == NODE_JET:
            self._stack.setCurrentIndex(2)
            self._refresh_combo()
            self._nz_mode("db" if node.nozzle_db_jet else "generic", emit=False)
            if node.nozzle_db_jet:
                jid = node.nozzle_db_jet.get("ID")
                for i in range(self._nz_cb.count()):
                    d = self._nz_cb.itemData(i)
                    if d and d.get("ID") == jid:
                        self._nz_cb.blockSignals(True)
                        self._nz_cb.setCurrentIndex(i)
                        self._nz_cb.blockSignals(False)
                        self._upd_nz_info(d)
                        break
            for w in (self._nz_name, self._nz_hole_d, self._nz_holes,
                      self._nz_count, self._nz_press, self._nz_cd):
                w.blockSignals(True)
            self._nz_name.setText(node.nozzle_name)
            self._nz_hole_d.setValue(node.nozzle_hole_d)
            self._nz_holes.setValue(node.nozzle_n_holes)
            self._nz_count.setValue(node.nozzle_count)
            self._nz_press.setValue(node.nozzle_pressure)
            self._nz_cd.setValue(node.nozzle_cd)
            for w in (self._nz_name, self._nz_hole_d, self._nz_holes,
                      self._nz_count, self._nz_press, self._nz_cd):
                w.blockSignals(False)
            self._upd_jet(node)

    def refresh_results(self, node: Optional[Node], graph: "NetworkGraph"):
        if node is None or self._node is None or node.id != self._node.id:
            return
        if node.kind == NODE_SEGMENT: self._upd_seg(node)
        elif node.kind == NODE_JET:   self._upd_jet(node)
        elif node.kind == NODE_REDUCER: self._upd_reducer(node)
        elif node.kind == NODE_SOURCE: self.update_source(graph)

    def update_source(self, graph: "NetworkGraph"):
        srcs_all = [n for n in graph.nodes.values() if n.kind == NODE_SOURCE]
        if srcs_all and self._node and self._node.kind == NODE_SOURCE:
            self._src_press.blockSignals(True)
            self._src_press.setValue(srcs_all[0].source_pressure)
            self._src_press.blockSignals(False)
        jets  = [n for n in graph.nodes.values() if n.kind == NODE_JET]
        segs  = [n for n in graph.nodes.values() if n.kind == NODE_SEGMENT]
        srcs  = [n for n in graph.nodes.values() if n.kind == NODE_SOURCE]
        total = sum(n.result_flow_nl_s for n in jets)
        nl    = total * 60.0
        m3h   = total * 3.6
        res   = m3h * 1.2
        # Required compressor pressure = source node's result_p_required
        # (= max jet pressure + all line losses on the critical path)
        req_p = max((n.result_p_required for n in srcs), default=0.0)
        if req_p == 0.0:
            # Fallback if no source node: max jet pressure + worst segment ΔP
            prs  = [n.nozzle_pressure for n in jets]
            req_p = max(prs) if prs else 0.0
            req_p += max((n.result_dp_cum for n in jets), default=0.0)
        tank  = res * 6
        accent = get_accent()
        sbig   = (f"color:{accent};font-size:18px;font-weight:700;"
                  "border:none;background:transparent;")
        sv     = f"color:{accent};font-size:11px;font-weight:600;"
        self._sv_nlmin.setText(f"{nl:.1f}");    self._sv_nlmin.setStyleSheet(sbig)
        self._sv_m3h.setText(f"{m3h:.2f}");     self._sv_m3h.setStyleSheet(sbig)
        self._sv_res.setText(f"{res:.2f}");      self._sv_res.setStyleSheet(sbig)
        self._sv_press.setText(f"{req_p:.2f}");  self._sv_press.setStyleSheet(sbig)
        self._slbls["n_jets"].setText(str(len(jets)));  self._slbls["n_jets"].setStyleSheet(sv)
        self._slbls["n_segs"].setText(str(len(segs)));  self._slbls["n_segs"].setStyleSheet(sv)
        self._slbls["tank"].setText(f"≥{tank:.0f} l" if tank>0 else "—")
        self._slbls["tank"].setStyleSheet(sv)
        worst_dp = max((n.result_dp_cum for n in jets), default=0.0)
        set_p = max((n.source_pressure for n in srcs), default=6.0)
        margin = set_p - req_p
        if res > 0:
            if margin >= 0:
                guide = (
                    f"✅  Compressor set to {set_p:.2f} bar — sufficient "
                    f"(margin: {margin:.3f} bar).\n"
                    f"Required: ≥{req_p:.2f} bar  |  Line losses: {worst_dp:.3f} bar (worst path).\n"
                    f"Flow: ≥{res:.1f} m³/h  |  Receiver: ≥{tank:.0f} l.")
            else:
                guide = (
                    f"⚠️  Compressor set to {set_p:.2f} bar — INSUFFICIENT!\n"
                    f"Required: ≥{req_p:.2f} bar  (deficit: {-margin:.3f} bar).\n"
                    f"Line losses: {worst_dp:.3f} bar (worst path).\n"
                    f"Increase compressor pressure on the Source node.")
        else:
            guide = "Add jet nodes to compute compressor requirements."
        self._src_guide.setText(guide)
        self._src_guide.setStyleSheet(
            "color:#1a5c1a;font-size:11px;padding:6px 8px;"
            "background:#e8f5e9;border:1px solid #a5d6a7;border-radius:4px;"
            if margin >= 0 and res > 0 else
            "color:#b45309;font-size:11px;padding:6px 8px;"
            "background:#fff3e0;border:1px solid #ffb74d;border-radius:4px;"
            if res > 0 else
            "color:#444;font-size:11px;padding:6px 8px;"
            "background:#fffbea;border:1px solid #ffe082;border-radius:4px;")
        # Store for op-cost recalc
        self._oc_flow_nl_s = total
        self._oc_req_p     = req_p
        self._upd_opcost()

    def _upd_opcost(self):
        """Recompute operating cost whenever inputs or network changes."""
        flow  = getattr(self, "_oc_flow_nl_s", 0.0)
        req_p = getattr(self, "_oc_req_p",     0.0)
        # Notify optimization panel of updated cost params
        self.opcostChanged.emit(
            self._oc_hours.value(), self._oc_days.value(),
            self._oc_price.value(), self._oc_eta.value())
        if flow <= 0 or req_p <= 0:
            for lv in self._oc_res.values():
                lv.setText("—")
            self._oc_total.setText("—")
            return
        try:
            r = _operating_cost(
                flow_nl_s     = flow,
                p_bar_g       = req_p,
                hours_day     = self._oc_hours.value(),
                days_year     = self._oc_days.value(),
                price_chf_kwh = self._oc_price.value(),
                efficiency    = self._oc_eta.value(),
            )
        except Exception:
            return
        accent = get_accent()
        sv = f"color:{accent};font-size:11px;font-weight:600;"
        self._oc_res["Compressor power"].setText(f"{r['power_kw']:.3f} kW")
        self._oc_res["Compressor power"].setStyleSheet(sv)
        self._oc_res["Operating hours/year"].setText(f"{r['hours_year']:.0f} h")
        self._oc_res["Operating hours/year"].setStyleSheet(sv)
        self._oc_res["Energy consumption"].setText(f"{r['energy_kwh']:,.0f} kWh/yr")
        self._oc_res["Energy consumption"].setStyleSheet(sv)
        self._oc_res["Annual cost"].setText(f"CHF {r['cost_chf']:,.2f}")
        self._oc_res["Annual cost"].setStyleSheet(sv)
        self._oc_total.setText(f"CHF {r['cost_chf']:,.0f} / year")
        # Nm³ cost: CHF / Nm³ compressed air
        nm3_per_year = flow * r["hours_year"] * 3600.0 / 1000.0
        if nm3_per_year > 0:
            nm3_cost = r["cost_chf"] / nm3_per_year
            self._oc_nm3.setText(
                f"≈ CHF {nm3_cost:.4f} per Nm³  "
                f"({nm3_per_year:,.0f} Nm³/year compressed)")
        else:
            self._oc_nm3.setText("—")

    # ── internal ──────────────────────────────────────────────────────
    def _upd_seg(self, n: Node):
        accent  = get_accent()
        ok_s    = f"color:{accent};font-size:11px;font-weight:600;"
        warn_s  = "color:#e53935;font-size:11px;font-weight:600;"
        dn = n.result_dn_rec
        d_use = n.seg_diam if n.seg_diam > 0 else dn
        L_eq  = n.seg_length + _fitting_equiv_length(
            d_use, n.seg_bends_90, n.seg_bends_45)
        self._seg_leq_lbl.setText(f"{L_eq:.2f} m")
        self._sr["Inlet pressure (computed)"].setText(
            f"{n.result_p_inlet:.2f} bar" if n.result_p_inlet else "—")
        self._sr["Rec. inner diameter"].setText(f"ø{dn} mm" if dn else "—")
        self._sr["Velocity"].setText(f"{n.result_v:.2f} m/s" if n.result_v else "—")
        self._sr["Velocity"].setStyleSheet(warn_s if n.result_v > 0 and not (15.0 <= n.result_v <= 35.0) else ok_s)
        self._sr["Segment ΔP"].setText(f"{n.result_dp:.4f} bar" if n.result_dp else "—")
        self._sr["Cumulative ΔP (source→here)"].setText(
            f"{n.result_dp_cum:.4f} bar" if n.result_dp_cum else "—")
        self._sr["Cumulative ΔP (source→here)"].setStyleSheet(
            warn_s if n.result_dp_cum > 0.5 else ok_s)
        self._sr["Total flow"].setText(
            f"{n.result_flow_nl_s*60:.2f} Nl/min" if n.result_flow_nl_s else "—")

    def _upd_reducer(self, n: Node):
        accent = get_accent()
        ok_s   = f"color:{accent};font-size:11px;font-weight:600;"
        warn_s = "color:#e53935;font-size:11px;font-weight:600;"
        self._rr["Velocity (inlet)"].setText(
            f"{n.result_v:.2f} m/s" if n.result_v else "—")
        self._rr["Velocity (outlet)"].setText(
            f"{n.result_v_out:.2f} m/s" if n.result_v_out else "—")
        self._rr["Velocity (outlet)"].setStyleSheet(
            warn_s if n.result_v_out > 0 and not (15.0 <= n.result_v_out <= 35.0) else ok_s)
        self._rr["Pressure drop (ΔP)"].setText(
            f"{n.result_dp:.4f} bar" if n.result_dp else "—")
        self._rr["Cumulative ΔP (source→here)"].setText(
            f"{n.result_dp_cum:.4f} bar" if n.result_dp_cum else "—")
        self._rr["Cumulative ΔP (source→here)"].setStyleSheet(
            warn_s if n.result_dp_cum > 0.5 else ok_s)
        self._rr["Total flow"].setText(
            f"{n.result_flow_nl_s*60:.2f} Nl/min" if n.result_flow_nl_s else "—")

    def _upd_jet(self, n: Node):
        accent = get_accent()
        ok_s   = f"color:{accent};font-size:11px;font-weight:600;"
        warn_s = "color:#e53935;font-size:11px;font-weight:600;"
        self._jr["Flow (total)"].setText(
            f"{n.result_flow_nl_s*60:.2f} Nl/min" if n.result_flow_nl_s else "—")
        actual  = n.result_p_inlet
        desired = n.nozzle_pressure
        sufficient = actual >= desired - 0.001
        self._jr["Inlet pressure (set)"].setText(
            f"desired {desired:.3f} bar  |  actual {actual:.3f} bar  "
            + ("✓" if sufficient else "⚠ INSUFFICIENT"))
        self._jr["Inlet pressure (set)"].setStyleSheet(
            ok_s if sufficient else warn_s)
        dp = n.result_dp_cum
        self._jr["Required extra pressure (line losses)"].setText(
            f"+{dp:.4f} bar line losses"
            if dp > 0.001 else "Negligible (direct connection)")
        self._jr["Required extra pressure (line losses)"].setStyleSheet(
            warn_s if dp > 0.3 else ok_s)

    def _nz_mode(self, mode: str, emit: bool = True):
        self._cur_nz_mode = mode
        accent = get_accent()
        a = (f"background:{accent};color:#fff;border-radius:4px;"
             "border:none;font-weight:600;")
        i = ("background:#e8e8e8;color:#555;border-radius:4px;"
             "border:none;font-weight:400;")
        self._nz_db_btn.setStyleSheet(a  if mode == "db"      else i)
        self._nz_gen_btn.setStyleSheet(a if mode == "generic" else i)
        self._nz_db_gb.setVisible( mode == "db")
        self._nz_gen_gb.setVisible(mode == "generic")
        if emit: self._on_nz()

    def _on_nz_db(self, idx: int):
        jet = self._nz_cb.itemData(idx)
        self._upd_nz_info(jet)
        if self._node and self._node.kind == NODE_JET:
            self._node.nozzle_db_jet = jet
            if jet:
                try: self._node.nozzle_hole_d = float(
                    str(jet.get("Luftbohrung") or "1").replace(",","."))
                except Exception: pass
                try: self._node.nozzle_n_holes = int(
                    jet.get("LuftlochAnzahl") or 1)
                except Exception: pass
            self.nodeChanged.emit()

    def _upd_nz_info(self, jet: Optional[Dict]):
        if not jet:
            self._nz_db_info.setText("—"); return
        try:
            d  = float(str(jet.get("Luftbohrung") or "?").replace(",","."))
            nh = int(jet.get("LuftlochAnzahl") or 1)
            self._nz_db_info.setText(f"Ø{d:.3f}mm · {nh} hole(s)")
        except Exception:
            self._nz_db_info.setText(str(jet.get("Jet","—")))

    def _on_seg(self):
        if not self._node or self._node.kind != NODE_SEGMENT: return
        self._node.seg_length   = self._seg_len.value()
        self._node.seg_diam     = self._seg_diam.value()
        self._node.seg_bends_90 = self._seg_b90.value()
        self._node.seg_bends_45 = self._seg_b45.value()
        self.nodeChanged.emit()

    def _on_red(self):
        if not self._node or self._node.kind != NODE_REDUCER: return
        self._node.red_d_in  = self._red_d_in.value()
        self._node.red_d_out = self._red_d_out.value()
        self.nodeChanged.emit()

    def _on_src_press(self):
        if not self._node or self._node.kind != NODE_SOURCE: return
        self._node.source_pressure = self._src_press.value()
        self.nodeChanged.emit()

    def _on_nz(self):
        if not self._node or self._node.kind != NODE_JET: return
        n = self._node
        if getattr(self, "_cur_nz_mode", "db") == "generic":
            n.nozzle_db_jet  = None
            n.nozzle_name    = self._nz_name.text()
            n.nozzle_hole_d  = self._nz_hole_d.value()
            n.nozzle_n_holes = self._nz_holes.value()
        n.nozzle_count    = self._nz_count.value()
        n.nozzle_pressure = self._nz_press.value()
        n.nozzle_cd       = self._nz_cd.value()
        self.nodeChanged.emit()


# ---------------------------------------------------------------------------
# Results table
# ---------------------------------------------------------------------------

class ResultsTable(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8,8,8,8); lay.setSpacing(4)

        title = QLabel("Segment overview")
        title.setStyleSheet(f"color:{DARK};font-size:13px;font-weight:700;")
        lay.addWidget(title)

        cols = ["Segment","Length (m)","Press. (bar)","Flow (Nl/min)",
                "Rec.ø (mm)","Man.ø (mm)","Velocity (m/s)",
                "Seg.ΔP (bar)","Cum.ΔP (bar)","Status"]
        self._tbl = QTableWidget(0, len(cols))
        self._tbl.setHorizontalHeaderLabels(cols)
        self._tbl.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents)
        self._tbl.horizontalHeader().setStretchLastSection(True)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.setStyleSheet(
            "QTableWidget{font-size:11px;border:none;}"
            f"QHeaderView::section{{background:{DARK};color:white;"
            "font-weight:600;font-size:11px;padding:4px;border:none;}}")
        lay.addWidget(self._tbl)

        self._sum = QLabel()
        self._sum.setStyleSheet("font-size:12px;color:#444;padding:2px;")
        lay.addWidget(self._sum)

    def refresh(self, graph: NetworkGraph):
        segs  = [n for n in graph.nodes.values()
                 if n.kind in (NODE_SEGMENT, NODE_REDUCER)]
        jets  = [n for n in graph.nodes.values() if n.kind == NODE_JET]
        self._tbl.setRowCount(len(segs))
        accent = get_accent()
        for ri, n in enumerate(segs):
            is_red = n.kind == NODE_REDUCER
            d_use   = (n.seg_diam if n.seg_diam > 0 else n.result_dn_rec
                       ) if not is_red else n.red_d_in
            vel_ok  = n.result_v == 0 or (15.0 <= n.result_v <= 35.0)
            dp_ok   = n.result_dp_cum <= 0.5
            ok      = vel_ok and dp_ok
            status  = "OK" if ok else ("⚠ Velocity" if not vel_ok
                                        else "⚠ High ΔP")
            rec_dn  = (f"ø{n.result_dn_rec}mm" if n.result_dn_rec else "—"
                       ) if not is_red else f"ø{int(n.red_d_out)}mm out"
            man_dn  = (f"ø{int(n.seg_diam)}mm" if n.seg_diam > 0 else "auto"
                       ) if not is_red else f"ø{int(n.red_d_in)}mm in"
            vals = [
                n.label().replace("\n"," "),
                f"{n.seg_length:.1f}" if not is_red else "—",
                f"{n.seg_pressure:.2f}" if not is_red else f"{n.red_pressure:.2f}",
                f"{n.result_flow_nl_s*60:.2f}",
                rec_dn, man_dn,
                f"{n.result_v:.2f}",
                f"{n.result_dp:.4f}",
                f"{n.result_dp_cum:.4f}",
                status,
            ]
            for ci, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                if ci == 9:
                    item.setForeground(
                        QColor(accent) if ok else QColor("#e53935"))
                self._tbl.setItem(ri, ci, item)

        total_q   = sum(n.result_flow_nl_s for n in jets) * 60
        total_dp  = sum(n.result_dp for n in segs)
        worst_dp  = max((n.result_dp_cum for n in jets), default=0.0)
        self._sum.setText(
            f"Total flow: <b>{total_q:.1f} Nl/min</b>  |  "
            f"Total pipe ΔP: <b>{total_dp:.4f} bar</b>  |  "
            f"Worst jet cum. ΔP: <b>{worst_dp:.4f} bar</b>  |  "
            f"Jets: {len(jets)}  Segments: {len(segs)}")


# ---------------------------------------------------------------------------
# Optimization engine
# ---------------------------------------------------------------------------

def _optimize_graph(graph: NetworkGraph) -> Tuple[NetworkGraph, List[Dict]]:
    """Return (optimized_graph, diff_list).

    Rules applied (only free parameters — never touches lengths or pressures):
      • Segment: if velocity outside 15–35 m/s → set seg_diam to recommended DN
                 (uses v_target=25 m/s as centre of green zone)
      • Reducer:  if outlet velocity outside 15–35 m/s → nudge d_out to next
                 standard DN that brings v_out into 20–30 m/s
    Each change produces one diff entry:
      {node_id, label, param, old_val, new_val, reason}
    """
    opt = copy.deepcopy(graph)
    opt.solve()

    diffs: List[Dict] = []

    for nid, node in opt.nodes.items():
        if node.kind == NODE_SEGMENT:
            v = node.result_v
            if v > 0 and not (15.0 <= v <= 35.0):
                old_d = int(node.seg_diam) if node.seg_diam > 0 else node.result_dn_rec
                # Pick the DN that gives ~25 m/s
                new_dn = _recommend_dn(node.result_flow_nl_s,
                                       node.seg_pressure, v_target=25.0)
                if new_dn != old_d:
                    node.seg_diam = float(new_dn)
                    direction = "too fast" if v > 35.0 else "too slow"
                    diffs.append({
                        "node_id":  nid,
                        "label":    node.label().replace("\n", " "),
                        "param":    "Pipe diameter",
                        "old_val":  f"ø{old_d} mm",
                        "new_val":  f"ø{new_dn} mm",
                        "reason":   f"v = {v:.1f} m/s ({direction})",
                    })

        elif node.kind == NODE_REDUCER:
            v_out = node.result_v_out
            if v_out > 0 and not (15.0 <= v_out <= 35.0):
                old_d_out = int(node.red_d_out)
                # Find the smallest standard DN that gives v_out ≈ 20–30 m/s
                q   = node.result_flow_nl_s
                p   = node.red_pressure
                p_a = p * 1e5 + P_ATM
                q_a = q * P_ATM / p_a
                # target area for 25 m/s
                A_target = q_a / 25.0
                d_target_mm = math.sqrt(4.0 * A_target / math.pi) * 1000.0
                new_d_out = old_d_out
                for dn in DN_STANDARDS:
                    A = math.pi / 4.0 * (dn / 1000.0) ** 2
                    v_test = q_a / A if A > 0 else 0.0
                    if 15.0 <= v_test <= 35.0:
                        new_d_out = dn
                        break
                if new_d_out != old_d_out:
                    node.red_d_out = float(new_d_out)
                    direction = "too fast" if v_out > 35.0 else "too slow"
                    diffs.append({
                        "node_id":  nid,
                        "label":    node.label().replace("\n", " "),
                        "param":    "Reducer outlet ø",
                        "old_val":  f"ø{old_d_out} mm",
                        "new_val":  f"ø{new_d_out} mm",
                        "reason":   f"v_out = {v_out:.1f} m/s ({direction})",
                    })

    # Re-solve once with all fixes applied
    opt.solve()

    # Second pass: flag remaining ΔP warnings (length is fixed → info only)
    for nid, node in opt.nodes.items():
        if node.kind in (NODE_SEGMENT, NODE_REDUCER):
            if node.result_dp_cum > 0.3:
                diffs.append({
                    "node_id":  nid,
                    "label":    node.label().replace("\n", " "),
                    "param":    "⚠ Cum. ΔP (info)",
                    "old_val":  "—",
                    "new_val":  f"{node.result_dp_cum:.4f} bar",
                    "reason":   "Exceeds 0.3 bar — shorten pipe or increase DN",
                })

    return opt, diffs


# ---------------------------------------------------------------------------
# Optimization panel  (read-only canvas + diff table + cost comparison)
# ---------------------------------------------------------------------------

class OptimizationPanel(QWidget):
    """Panel showing optimized network canvas + change table + cost comparison.

    Layout:
        [Dark header bar]
        [Cost comparison strip]
        [QSplitter horizontal]
            left:  read-only optimized canvas (changed nodes highlighted gold)
            right: "What needs to change" diff table
    """

    def __init__(self, jets: List[Dict], parent=None):
        super().__init__(parent)
        self._jets = jets
        self._opt_graph: Optional[NetworkGraph] = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Header bar ────────────────────────────────────────────────
        hdr = QFrame()
        hdr.setFixedHeight(32)
        hdr.setStyleSheet("background:#1D3557;border-top:2px solid #39A650;")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 0, 12, 0); hl.setSpacing(8)
        lbl = QLabel("🔧  Optimized Network  —  gold ring = changed element")
        lbl.setStyleSheet("color:white;font-size:12px;font-weight:600;")
        hl.addWidget(lbl); hl.addStretch()
        self._lbl_status = QLabel("")
        self._lbl_status.setStyleSheet(
            "color:#a8d5b5;font-size:11px;font-style:italic;")
        hl.addWidget(self._lbl_status)
        lay.addWidget(hdr)

        # ── Cost comparison strip ─────────────────────────────────────
        cost_strip = QFrame()
        cost_strip.setFixedHeight(56)
        cost_strip.setStyleSheet(
            "background:#f0f7f0;border-bottom:1px solid #c8e6c9;")
        cl = QHBoxLayout(cost_strip)
        cl.setContentsMargins(16, 6, 16, 6); cl.setSpacing(0)

        def _cost_kpi(title, attr):
            f = QFrame()
            f.setStyleSheet(
                "QFrame{background:transparent;border:none;}")
            fl = QVBoxLayout(f)
            fl.setContentsMargins(0, 0, 0, 0); fl.setSpacing(0)
            t = QLabel(title)
            t.setStyleSheet("color:#555;font-size:10px;")
            v = QLabel("—")
            v.setStyleSheet("color:#1D3557;font-size:15px;font-weight:700;")
            fl.addWidget(t); fl.addWidget(v)
            setattr(self, attr, v)
            return f

        cl.addWidget(_cost_kpi("Current  (annual)", "_cc_current"))
        self._cc_arrow = QLabel("  →  ")
        self._cc_arrow.setStyleSheet(
            "color:#39A650;font-size:18px;font-weight:700;")
        cl.addWidget(self._cc_arrow)
        cl.addWidget(_cost_kpi("Optimized  (annual)", "_cc_optimized"))
        cl.addSpacing(24)

        sep = QFrame(); sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color:#c8e6c9;")
        cl.addWidget(sep)
        cl.addSpacing(24)

        cl.addWidget(_cost_kpi("Savings / year", "_cc_savings"))
        cl.addSpacing(24)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet("color:#c8e6c9;")
        cl.addWidget(sep2)
        cl.addSpacing(24)

        cl.addWidget(_cost_kpi("Cost per Nm³  (current)", "_cc_nm3_curr"))
        cl.addSpacing(12)
        cl.addWidget(_cost_kpi("Cost per Nm³  (optimized)", "_cc_nm3_opt"))
        cl.addStretch()

        self._cc_note = QLabel("(Set operating cost parameters in Source node)")
        self._cc_note.setStyleSheet("color:#888;font-size:10px;font-style:italic;")
        cl.addWidget(self._cc_note)

        lay.addWidget(cost_strip)

        # ── Splitter: canvas left, diff table right ───────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle{background:#ddd;width:1px;}")

        self._opt_canvas = NetworkCanvas(NetworkGraph())
        self._opt_canvas.setEnabled(False)
        self._opt_canvas.setStyleSheet("background:#f8fbf8;")
        splitter.addWidget(self._opt_canvas)

        diff_wrap = QWidget()
        dw_lay = QVBoxLayout(diff_wrap)
        dw_lay.setContentsMargins(8, 8, 8, 8); dw_lay.setSpacing(4)

        diff_title = QLabel("What needs to change")
        diff_title.setStyleSheet(f"color:{DARK};font-size:13px;font-weight:700;")
        dw_lay.addWidget(diff_title)

        cols = ["Node", "Parameter", "Current", "→ Optimized", "Reason"]
        self._diff_tbl = QTableWidget(0, len(cols))
        self._diff_tbl.setHorizontalHeaderLabels(cols)
        self._diff_tbl.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents)
        self._diff_tbl.horizontalHeader().setStretchLastSection(True)
        self._diff_tbl.verticalHeader().setVisible(False)
        self._diff_tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._diff_tbl.setAlternatingRowColors(True)
        self._diff_tbl.setStyleSheet(
            "QTableWidget{font-size:11px;border:none;}"
            "QHeaderView::section{background:#39A650;color:white;"
            "font-weight:600;font-size:11px;padding:4px;border:none;}")
        dw_lay.addWidget(self._diff_tbl)

        self._lbl_all_ok = QLabel(
            "✅  No changes needed — network is already optimal.")
        self._lbl_all_ok.setStyleSheet(
            "color:#2e7d32;font-size:13px;font-weight:600;padding:12px;")
        self._lbl_all_ok.setAlignment(Qt.AlignCenter)
        self._lbl_all_ok.hide()
        dw_lay.addWidget(self._lbl_all_ok)

        splitter.addWidget(diff_wrap)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        lay.addWidget(splitter, 1)

        # Operating cost params — read from source panel if available
        # Defaults match the source panel defaults
        self._op_hours:    float = 16.0
        self._op_days:     float = 250.0
        self._op_price:    float = 0.22
        self._op_eta:      float = 0.70

    def set_opcost_params(self, hours: float, days: float,
                          price: float, eta: float):
        """Called by AirSupplyScreen to keep cost params in sync."""
        self._op_hours = hours
        self._op_days  = days
        self._op_price = price
        self._op_eta   = eta

    def refresh(self, graph: NetworkGraph):
        """Run optimizer on graph and update the panel."""
        opt_graph, diffs = _optimize_graph(graph)
        self._opt_graph = opt_graph

        # Build changed-nodes dict: node_id → badge text
        changed: Dict[str, str] = {}
        for d in diffs:
            if "info" not in d["param"]:
                badge = f"{d['old_val']}→{d['new_val']}"
                changed[d["node_id"]] = badge
        self._opt_canvas._changed_nodes = changed

        # Update canvas
        self._opt_canvas.graph = opt_graph
        self._opt_canvas.fit_to_screen()
        self._opt_canvas.update()

        # Status label
        n_fixes = len(changed)
        n_info  = len(diffs) - n_fixes
        parts = []
        if n_fixes:
            parts.append(f"{n_fixes} fix{'es' if n_fixes > 1 else ''} applied")
        if n_info:
            parts.append(f"{n_info} info item{'s' if n_info > 1 else ''}")
        self._lbl_status.setText("  |  ".join(parts) if parts else "All OK")

        # Diff table
        self._diff_tbl.setRowCount(len(diffs))
        if not diffs:
            self._diff_tbl.hide()
            self._lbl_all_ok.show()
        else:
            self._lbl_all_ok.hide()
            self._diff_tbl.show()
            for ri, d in enumerate(diffs):
                is_info = "info" in d["param"]
                bg = QColor("#fff8e1") if is_info else QColor("#e8f5e9")
                vals = [d["label"], d["param"],
                        d["old_val"], d["new_val"], d["reason"]]
                for ci, v in enumerate(vals):
                    item = QTableWidgetItem(v)
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setBackground(QBrush(bg))
                    if ci == 3 and not is_info:
                        item.setForeground(QColor("#2e7d32"))
                        font = item.font(); font.setBold(True)
                        item.setFont(font)
                    self._diff_tbl.setItem(ri, ci, item)

        # ── Cost comparison ───────────────────────────────────────────
        self._update_cost_strip(graph, opt_graph)

    def _update_cost_strip(self, orig: NetworkGraph, opt: NetworkGraph):
        """Compute and display annual cost for original and optimized graph."""
        def _get_cost(g: NetworkGraph):
            jets = [n for n in g.nodes.values() if n.kind == NODE_JET]
            srcs = [n for n in g.nodes.values() if n.kind == NODE_SOURCE]
            total_nl_s = sum(n.result_flow_nl_s for n in jets)
            req_p = max((n.result_p_required for n in srcs), default=0.0)
            if req_p == 0.0:
                prs = [n.nozzle_pressure for n in jets]
                req_p = (max(prs) if prs else 0.0)
                req_p += max((n.result_dp_cum for n in jets), default=0.0)
            if total_nl_s <= 0 or req_p <= 0:
                return None, total_nl_s, req_p
            r = _operating_cost(
                flow_nl_s     = total_nl_s,
                p_bar_g       = req_p,
                hours_day     = self._op_hours,
                days_year     = self._op_days,
                price_chf_kwh = self._op_price,
                efficiency    = self._op_eta,
            )
            return r, total_nl_s, req_p

        r_orig, flow_orig, _ = _get_cost(orig)
        r_opt,  flow_opt,  _ = _get_cost(opt)

        def _nm3_cost(r, flow_nl_s):
            """CHF per Nm³ compressed air."""
            if r is None or flow_nl_s <= 0 or r["hours_year"] <= 0:
                return None
            nm3_per_year = flow_nl_s * r["hours_year"] * 3600.0 / 1000.0
            return r["cost_chf"] / nm3_per_year if nm3_per_year > 0 else None

        no_data = r_orig is None and r_opt is None
        self._cc_note.setVisible(no_data)

        def _fmt_chf(r):
            return f"CHF {r['cost_chf']:,.0f}" if r else "—"

        def _fmt_nm3(r, flow):
            v = _nm3_cost(r, flow)
            return f"CHF {v:.4f}/Nm³" if v is not None else "—"

        self._cc_current.setText(_fmt_chf(r_orig))
        self._cc_optimized.setText(_fmt_chf(r_opt))
        self._cc_nm3_curr.setText(_fmt_nm3(r_orig, flow_orig))
        self._cc_nm3_opt.setText(_fmt_nm3(r_opt,  flow_opt))

        if r_orig and r_opt:
            savings = r_orig["cost_chf"] - r_opt["cost_chf"]
            if savings > 0.5:
                self._cc_savings.setText(f"CHF {savings:,.0f} 🎉")
                self._cc_savings.setStyleSheet(
                    "color:#2e7d32;font-size:15px;font-weight:700;")
            elif savings < -0.5:
                self._cc_savings.setText(f"CHF {abs(savings):,.0f} more")
                self._cc_savings.setStyleSheet(
                    "color:#e53935;font-size:15px;font-weight:700;")
            else:
                self._cc_savings.setText("No difference")
                self._cc_savings.setStyleSheet(
                    "color:#555;font-size:15px;font-weight:700;")
        else:
            self._cc_savings.setText("—")
            self._cc_savings.setStyleSheet(
                "color:#555;font-size:15px;font-weight:700;")

    def get_opt_graph(self) -> Optional[NetworkGraph]:
        return self._opt_graph


# ---------------------------------------------------------------------------
# Main screen
# ---------------------------------------------------------------------------

class AirSupplyScreen(QWidget):
    def __init__(
        self,
        on_back_home: Optional[Callable[[], None]] = None,
        jets_loader:  Optional[Callable[[], List[Dict]]] = None,
        username:     str = "",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._on_back_home = on_back_home
        self._jets_loader  = jets_loader
        self._username     = username
        self._jets: List[Dict]      = []
        self._jets_by_id: Dict[int,Dict] = {}
        self._undo_stack: List[str] = []   # JSON snapshots, max 10

        # Multi-tab: each tab has its own graph, canvas, results table
        # _tabs = list of dicts: {graph, canvas, results_tbl, net_id, net_name}
        self._tabs: List[Dict] = []
        self._cur_tab_idx: int = 0

        self._build_ui()
        self._load_jets()
        try:
            _ensure_tables()
        except Exception as e:
            print(f"[AirSupply] Table setup skipped: {e}")
        self._add_tab(example=True)

    # ── UI ────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        hdr = HeaderBar(title="Air Supply Network Calculator", show_home=True)
        hdr.connect_home(self._go_home)
        root.addWidget(hdr, 0)

        # Toolbar
        tb = QFrame(); tb.setFixedHeight(42)
        tb.setStyleSheet(
            f"background:{CARD_BG};border-bottom:1px solid #cfcfcf;")
        tl = QHBoxLayout(tb)
        tl.setContentsMargins(12,4,12,4); tl.setSpacing(6)
        accent = get_accent()

        def _btn(lbl, cb, color=None):
            b = QPushButton(lbl); b.setFixedHeight(30)
            if color:
                b.setStyleSheet(
                    f"QPushButton{{background:{color};color:white;"
                    "border-radius:3px;font-size:12px;padding:0 10px;border:none;}}"
                    f"QPushButton:hover{{background:{color}cc;}}")
            else:
                b.setStyleSheet(
                    "QPushButton{border:1px solid #ccc;border-radius:3px;"
                    "font-size:12px;padding:0 10px;background:white;}"
                    "QPushButton:hover{background:#f0f0f0;}")
            b.clicked.connect(cb); return b

        def _sep():
            l = QLabel("|"); l.setStyleSheet("color:#ccc;"); return l

        tl.addWidget(_btn("+ Source",   lambda: self._add_node(NODE_SOURCE)))
        tl.addWidget(_btn("+ Pipe",     lambda: self._add_node(NODE_SEGMENT)))
        tl.addWidget(_btn("+ Y-Split",  lambda: self._add_node(NODE_SPLIT)))
        tl.addWidget(_btn("+ Reducer",  lambda: self._add_node(NODE_REDUCER)))
        tl.addWidget(_btn("+ Jet",      lambda: self._add_node(NODE_JET)))
        tl.addWidget(_sep())
        self._btn_conn = _btn("Connect nodes", self._start_connect, "#457B9D")
        tl.addWidget(self._btn_conn)
        tl.addWidget(_btn("Delete (Del)", self._delete_selected))
        tl.addWidget(_sep())
        tl.addWidget(_btn("Clear all",  self._clear_all))
        tl.addWidget(_btn("Example",    self._add_example_network))
        tl.addWidget(_btn("⊞ Fit",      self._fit_to_screen))
        tl.addWidget(_sep())
        tl.addWidget(_btn("💾 Save / Load", self._open_save_load))
        tl.addWidget(_sep())
        tl.addWidget(_btn("📄 PDF",    self._export_pdf))
        tl.addWidget(_btn("📊 Excel",  self._export_excel))
        tl.addWidget(_sep())
        self._btn_optimize = _btn("🔧 Optimize", self._toggle_optimize, "#2e7d32")
        tl.addWidget(self._btn_optimize)
        tl.addStretch()
        self._lbl_net = QLabel("")
        self._lbl_net.setStyleSheet("color:#666;font-size:11px;font-style:italic;")
        tl.addWidget(self._lbl_net)
        tl.addWidget(_btn("Recalculate", self._recalculate, accent))
        root.addWidget(tb, 0)

        # Tab bar for multiple networks
        self._tab_widget = QTabWidget()
        self._tab_widget.setTabsClosable(True)
        self._tab_widget.setMovable(True)
        self._tab_widget.setStyleSheet(
            "QTabWidget::pane{border:none;}"
            f"QTabBar::tab{{background:#e8e8e8;color:#555;padding:4px 14px;"
            "border-radius:3px 3px 0 0;font-size:12px;margin-right:2px;}}"
            f"QTabBar::tab:selected{{background:{accent};color:white;font-weight:600;}}"
            "QTabBar::tab:hover{background:#d0d0d0;}")
        self._tab_widget.tabCloseRequested.connect(self._close_tab)
        self._tab_widget.currentChanged.connect(self._on_tab_changed)
        self._tab_widget.tabBarDoubleClicked.connect(self._rename_tab)

        # "+" button to add new tab
        self._btn_add_tab = QPushButton("+")
        self._btn_add_tab.setFixedSize(28, 28)
        self._btn_add_tab.setStyleSheet(
            f"QPushButton{{background:{accent};color:white;border:none;"
            "border-radius:3px;font-size:16px;font-weight:bold;}}"
            f"QPushButton:hover{{background:{accent}cc;}}")
        self._btn_add_tab.clicked.connect(lambda: self._add_tab())
        self._tab_widget.setCornerWidget(self._btn_add_tab)

        # Right panel (shared across tabs)
        self._panel = NodePropertyPanel(self._jets)
        self._panel.nodeChanged.connect(self._on_node)
        self._panel.opcostChanged.connect(self._on_opcost_changed)
        self._panel.setFixedWidth(400)

        tab_splitter = QSplitter(Qt.Horizontal)
        tab_splitter.setStyleSheet(
            "QSplitter::handle{background:#ddd;width:1px;}")
        tab_splitter.addWidget(self._tab_widget)
        tab_splitter.addWidget(self._panel)
        tab_splitter.setStretchFactor(0, 1)
        tab_splitter.setStretchFactor(1, 0)

        root.addWidget(tab_splitter, 1)
        root.addWidget(FooterBar(), 0)

    # ── tab management ────────────────────────────────────────────────
    @property
    def _graph(self) -> NetworkGraph:
        return self._tabs[self._cur_tab_idx]["graph"] if self._tabs else NetworkGraph()

    @property
    def _canvas(self) -> "NetworkCanvas":
        return self._tabs[self._cur_tab_idx]["canvas"] if self._tabs else None

    @property
    def _res_tbl(self) -> "ResultsTable":
        return self._tabs[self._cur_tab_idx]["res_tbl"] if self._tabs else None

    @property
    def _opt_panel(self) -> "OptimizationPanel":
        return self._tabs[self._cur_tab_idx].get("opt_panel") if self._tabs else None

    @property
    def _net_id(self) -> Optional[int]:
        return self._tabs[self._cur_tab_idx]["net_id"] if self._tabs else None

    @_net_id.setter
    def _net_id(self, v):
        if self._tabs: self._tabs[self._cur_tab_idx]["net_id"] = v

    @property
    def _net_name(self) -> str:
        return self._tabs[self._cur_tab_idx]["net_name"] if self._tabs else ""

    @_net_name.setter
    def _net_name(self, v):
        if self._tabs: self._tabs[self._cur_tab_idx]["net_name"] = v

    def _add_tab(self, example: bool = False,
                 graph: Optional[NetworkGraph] = None,
                 name: str = ""):
        """Create a new tab with its own canvas + results table."""
        g = graph or NetworkGraph()
        tab_name = name or f"Network {len(self._tabs)+1}"

        canvas = NetworkCanvas(g)
        canvas.selectionChanged.connect(self._on_sel)
        canvas.graphChanged.connect(self._on_graph)
        canvas.undoRequested.connect(self._undo)
        canvas.saveRequested.connect(self._open_save_load)

        res_tbl = ResultsTable()
        res_tbl.setMaximumHeight(200)

        opt_panel = OptimizationPanel(self._jets)
        opt_panel.hide()

        # Layout: canvas top, results table middle, optimization panel bottom
        container = QWidget()
        vl = QVBoxLayout(container)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        top_splitter = QSplitter(Qt.Vertical)
        top_splitter.setStyleSheet("QSplitter::handle{background:#ddd;height:1px;}")
        top_splitter.addWidget(canvas)
        top_splitter.addWidget(res_tbl)
        top_splitter.setStretchFactor(0, 3)
        top_splitter.setStretchFactor(1, 1)

        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.setStyleSheet("QSplitter::handle{background:#39A650;height:2px;}")
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(opt_panel)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 1)
        vl.addWidget(main_splitter)

        tab_data = {
            "graph":     g,
            "canvas":    canvas,
            "res_tbl":   res_tbl,
            "opt_panel": opt_panel,
            "net_id":    None,
            "net_name":  tab_name,
        }
        self._tabs.append(tab_data)
        idx = self._tab_widget.addTab(container, tab_name)
        self._tab_widget.setCurrentIndex(idx)
        # Tab rename on double-click
        self._tab_widget.tabBar().setTabToolTip(idx, "Double-click to rename")

        if example:
            self._cur_tab_idx = idx
            self._add_example_network()
        else:
            g.solve()
            res_tbl.refresh(g)

    def _close_tab(self, idx: int):
        if len(self._tabs) <= 1:
            QMessageBox.information(self, "Cannot close",
                                    "At least one network tab must remain.")
            return
        self._tabs.pop(idx)
        self._tab_widget.removeTab(idx)

    def _on_tab_changed(self, idx: int):
        if idx < 0 or idx >= len(self._tabs):
            return
        self._cur_tab_idx = idx
        self._undo_stack.clear()
        self._panel.load_node(None)
        net = self._tabs[idx]["net_name"]
        self._lbl_net.setText(f"  {net}" if net else "")

    # ── toolbar ───────────────────────────────────────────────────────
    # ── undo ──────────────────────────────────────────────────────────
    def _push_undo(self):
        snap = self._graph.to_json()
        if self._undo_stack and self._undo_stack[-1] == snap:
            return
        self._undo_stack.append(snap)
        if len(self._undo_stack) > 10:
            self._undo_stack.pop(0)

    def _undo(self):
        if not self._undo_stack:
            return
        snap = self._undo_stack.pop()
        self._graph = NetworkGraph.from_json(snap, self._jets_by_id)
        self._canvas.graph = self._graph
        self._canvas.select(None)
        self._graph.solve()
        self._canvas.update()
        self._res_tbl.refresh(self._graph)

    # ── fit to screen ─────────────────────────────────────────────────
    def _fit_to_screen(self):
        self._canvas.fit_to_screen()

    def _add_node(self, kind: str):
        self._push_undo()
        cx  = self._canvas.width()  / 2
        cy  = self._canvas.height() / 2
        off = len(self._graph.nodes) * 30 % 200
        n   = Node(kind,
                   x=(cx - self._canvas._offset.x()) / self._canvas._zoom + off,
                   y=(cy - self._canvas._offset.y()) / self._canvas._zoom + off)
        self._graph.add_node(n)
        self._canvas.select(n)
        self._canvas.update()

    def _start_connect(self):
        self._canvas.set_connect_mode(True)
        self._btn_conn.setStyleSheet(
            "QPushButton{background:#e53935;color:white;border-radius:3px;"
            "font-size:12px;padding:0 10px;border:none;}")
        QTimer.singleShot(8000, self._cancel_connect)

    def _cancel_connect(self):
        self._canvas.set_connect_mode(False)
        self._btn_conn.setStyleSheet(
            "QPushButton{background:#457B9D;color:white;border-radius:3px;"
            "font-size:12px;padding:0 10px;border:none;}")

    def _delete_selected(self):
        if self._canvas._selected:
            self._push_undo()
            nid = self._canvas._selected.id
            self._canvas.select(None)
            self._graph.remove_node(nid)
            self._graph.solve()
            self._canvas.update()
            self._res_tbl.refresh(self._graph)

    def _clear_all(self):
        if QMessageBox.question(self,"Clear","Remove all nodes?",
                                QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            self._push_undo()
            self._graph.nodes.clear(); self._graph.edges.clear()
            self._canvas.select(None); self._canvas.update()
            self._res_tbl.refresh(self._graph)

    def _recalculate(self):
        self._graph.solve(); self._canvas.update()
        self._res_tbl.refresh(self._graph)
        sel = self._canvas._selected
        if sel: self._panel.refresh_results(sel, self._graph)
        if self._opt_panel and self._opt_panel.isVisible():
            self._opt_panel.refresh(self._graph)
        # Warn about graph topology issues
        warnings = self._graph.validate()
        if warnings:
            QMessageBox.warning(self, "Network issues",
                                "⚠️  Physics may be incorrect:\n\n" +
                                "\n".join(f"• {w}" for w in warnings) +
                                "\n\nRight-click connections to remove duplicates.")

    def _open_save_load(self):
        dlg = SaveLoadDialog(self._graph, self._username, self._net_id, self)
        dlg.exec()
        if dlg.was_load and dlg.chosen_network_id:
            g = db_load_network(dlg.chosen_network_id, self._jets_by_id)
            if g:
                # Update current tab's graph
                tab = self._tabs[self._cur_tab_idx]
                tab["graph"] = g
                tab["canvas"].graph = g
                tab["net_id"] = dlg.chosen_network_id
                for row in db_list_networks():
                    if row.get("ID") == dlg.chosen_network_id:
                        tab["net_name"] = str(row.get("Name", ""))
                        self._tab_widget.setTabText(
                            self._cur_tab_idx, tab["net_name"])
                        self._lbl_net.setText(f"  {tab['net_name']}")
                        break
                g.solve()
                tab["canvas"].select(None)
                tab["canvas"].update()
                tab["res_tbl"].refresh(g)
        elif dlg.chosen_network_id and not dlg.was_load:
            self._tabs[self._cur_tab_idx]["net_id"] = dlg.chosen_network_id

    def _add_example_network(self):
        if self._graph.nodes: return
        def _n(kind, x, y, **kw):
            node = Node(kind, x, y)
            for k,v in kw.items(): setattr(node, k, v)
            self._graph.add_node(node); return node
        src = _n(NODE_SOURCE,  100, 200)
        s1  = _n(NODE_SEGMENT, 250, 200, seg_length=10.0, seg_pressure=5.0)
        sp1 = _n(NODE_SPLIT,   400, 200)
        s2  = _n(NODE_SEGMENT, 520, 120, seg_length=5.0,  seg_pressure=5.0)
        s3  = _n(NODE_SEGMENT, 520, 280, seg_length=5.0,  seg_pressure=5.0)
        sp2 = _n(NODE_SPLIT,   660, 120)
        j1  = _n(NODE_JET, 780, 80,  nozzle_name="P142-1",
                 nozzle_hole_d=1.0, nozzle_n_holes=1,
                 nozzle_count=4, nozzle_pressure=4.5)
        j2  = _n(NODE_JET, 780, 160, nozzle_name="P142-2",
                 nozzle_hole_d=1.2, nozzle_n_holes=2,
                 nozzle_count=4, nozzle_pressure=4.5)
        j3  = _n(NODE_JET, 660, 280, nozzle_name="Generic",
                 nozzle_hole_d=0.8, nozzle_n_holes=1,
                 nozzle_count=8, nozzle_pressure=5.0)
        for a,b in [(src,s1),(s1,sp1),(sp1,s2),(sp1,s3),
                     (s2,sp2),(sp2,j1),(sp2,j2),(s3,j3)]:
            self._graph.add_edge(a.id, b.id)
        self._graph.solve()
        self._canvas.update()
        self._res_tbl.refresh(self._graph)

    # ── signals ───────────────────────────────────────────────────────
    def _on_sel(self, node: Optional[Node]):
        self._panel.load_node(node)
        if node and node.kind == NODE_SOURCE:
            self._panel.update_source(self._graph)

    def _on_node(self):
        self._push_undo()
        self._graph.solve(); self._canvas.update()
        self._res_tbl.refresh(self._graph)
        sel = self._canvas._selected
        if sel: self._panel.refresh_results(sel, self._graph)

    def _on_graph(self):
        self._push_undo()
        self._graph.solve()
        self._res_tbl.refresh(self._graph)
        sel = self._canvas._selected
        if sel: self._panel.refresh_results(sel, self._graph)
        if self._opt_panel and self._opt_panel.isVisible():
            self._opt_panel.refresh(self._graph)

    def _on_opcost_changed(self, hours: float, days: float,
                            price: float, eta: float):
        """Keep all opt panels in sync with source node cost params."""
        for tab in self._tabs:
            p = tab.get("opt_panel")
            if p:
                p.set_opcost_params(hours, days, price, eta)
                if p.isVisible():
                    p.refresh(tab["graph"])

    # ── jets ──────────────────────────────────────────────────────────
    def _load_jets(self):
        if not callable(self._jets_loader): return
        try: self._jets = self._jets_loader() or []
        except Exception: self._jets = []
        self._jets_by_id = {int(j["ID"]): j for j in self._jets
                             if j.get("ID") is not None}
        self._panel.set_jets(self._jets)

    # ── optimize ──────────────────────────────────────────────────────
    def _toggle_optimize(self):
        panel = self._opt_panel
        if panel is None:
            return
        if panel.isVisible():
            panel.hide()
            self._btn_optimize.setStyleSheet(
                "QPushButton{background:#2e7d32;color:white;border-radius:3px;"
                "font-size:12px;padding:0 10px;border:none;}"
                "QPushButton:hover{background:#1b5e20;}")
            self._btn_optimize.setText("🔧 Optimize")
        else:
            panel.refresh(self._graph)
            panel.show()
            self._btn_optimize.setStyleSheet(
                "QPushButton{background:#1b5e20;color:#a8d5b5;border-radius:3px;"
                "font-size:12px;padding:0 10px;border:1px solid #a8d5b5;}"
                "QPushButton:hover{background:#2e7d32;color:white;}")
            self._btn_optimize.setText("🔧 Optimize  ✕")

    # ── export ────────────────────────────────────────────────────────
    def _export_pdf(self):
        from PySide6.QtWidgets import QFileDialog
        default = f"AirSupply_{self._net_name or 'Network'}.pdf".replace(" ", "_")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PDF", default, "PDF Files (*.pdf)")
        if not path:
            return
        try:
            # Include optimization diff if panel is open or there are warnings
            _, diffs = _optimize_graph(self._graph)
            _generate_air_supply_pdf(path, self._graph,
                                     self._net_name or "Air Supply Network",
                                     self._username,
                                     opt_diffs=diffs if diffs else None)
            QMessageBox.information(self, "PDF exported",
                                    f"Saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "PDF failed", str(e))

    def _export_excel(self):
        from PySide6.QtWidgets import QFileDialog
        default = f"AirSupply_{self._net_name or 'Network'}.xlsx".replace(" ", "_")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Excel", default, "Excel Files (*.xlsx)")
        if not path:
            return
        try:
            _generate_air_supply_excel(path, self._graph,
                                       self._net_name or "Air Supply Network")
            QMessageBox.information(self, "Excel exported",
                                    f"Saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Excel failed", str(e))

    # ── navigation ────────────────────────────────────────────────────
    def _rename_tab(self, idx: int):
        from PySide6.QtWidgets import QInputDialog
        old = self._tab_widget.tabText(idx)
        new_name, ok = QInputDialog.getText(
            self, "Rename network", "Network name:", text=old)
        if ok and new_name.strip():
            new_name = new_name.strip()
            self._tab_widget.setTabText(idx, new_name)
            if idx < len(self._tabs):
                self._tabs[idx]["net_name"] = new_name

    def _go_home(self):
        if callable(self._on_back_home): self._on_back_home()

    def showEvent(self, event):
        super().showEvent(event)
        self._load_jets()


# ---------------------------------------------------------------------------
# PDF export
# ---------------------------------------------------------------------------

def _generate_air_supply_pdf(path: str, graph: NetworkGraph,
                              title: str, created_by: str = "",
                              opt_diffs: Optional[List[Dict]] = None):
    """Generate a Heberlein-style A4 PDF report for the air supply network.

    If opt_diffs is provided and non-empty, an extra page with optimization
    recommendations is appended.
    """
    import datetime, os
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm, mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable, Image as RLImage,
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
    from reportlab.graphics.shapes import (
        Drawing, Line, Rect, String, Polygon, PolyLine, Circle,
    )

    # ── Colours ───────────────────────────────────────────────────────
    HEB_GREEN = colors.HexColor("#39A650")
    HEB_DARK  = colors.HexColor("#1D3557")
    HEB_BLUE  = colors.HexColor("#457B9D")
    ROW_LIGHT = colors.HexColor("#F2F9F3")
    GREY_TEXT = colors.HexColor("#555555")
    WHITE     = colors.white
    WARN_RED  = colors.HexColor("#e53935")
    ORANGE    = colors.HexColor("#E76F51")

    PW, PH = A4
    margin = 1.8 * cm
    CW     = PW - 2 * margin   # content width

    date_str = datetime.date.today().strftime("%d.%m.%Y")

    # ── Styles ────────────────────────────────────────────────────────
    def _s(name, **kw):
        return ParagraphStyle(name, **kw)

    s_title  = _s("title",  fontSize=16, fontName="Helvetica-Bold",
                  textColor=HEB_DARK, spaceAfter=4, spaceBefore=0)
    s_h1     = _s("h1",     fontSize=11, fontName="Helvetica-Bold",
                  textColor=HEB_DARK, spaceBefore=6, spaceAfter=3)
    s_normal = _s("normal", fontSize=9,  fontName="Helvetica",
                  textColor=GREY_TEXT, leading=14)
    s_small  = _s("small",  fontSize=8,  fontName="Helvetica",
                  textColor=GREY_TEXT)
    s_footer = _s("footer", fontSize=7.5, fontName="Helvetica",
                  textColor=GREY_TEXT)
    s_bold   = _s("bold",   fontSize=9,  fontName="Helvetica-Bold",
                  textColor=HEB_DARK)
    s_kpi_v  = _s("kpiv",   fontSize=15, fontName="Helvetica-Bold",
                  textColor=HEB_GREEN, spaceAfter=0)
    s_kpi_l  = _s("kpil",   fontSize=7.5, fontName="Helvetica",
                  textColor=GREY_TEXT, spaceAfter=0)

    # ── Compute summary ───────────────────────────────────────────────
    jets  = [n for n in graph.nodes.values() if n.kind == NODE_JET]
    segs  = [n for n in graph.nodes.values()
             if n.kind in (NODE_SEGMENT, NODE_REDUCER)]
    srcs  = [n for n in graph.nodes.values() if n.kind == NODE_SOURCE]

    total_nl_s   = sum(n.result_flow_nl_s for n in jets)
    total_nl_min = total_nl_s * 60.0
    total_m3h    = total_nl_s * 3.6
    total_m3h_r  = total_m3h * 1.2
    req_p        = max((n.result_p_required for n in srcs), default=0.0)
    if req_p == 0.0:
        req_p = (max((n.nozzle_pressure for n in jets), default=0.0)
                 + max((n.result_dp_cum for n in jets), default=0.0))
    tank_l       = total_m3h_r * 6
    worst_dp     = max((n.result_dp_cum for n in jets), default=0.0)
    total_dp     = sum(n.result_dp for n in segs)

    # ── Logo helper ───────────────────────────────────────────────────
    def _logo_row():
        try:
            from ui.pathutil import resource_path
            logo_l = resource_path("assets/images/heb_logo.png")
            logo_r = resource_path("assets/images/header_logo_big.png")
        except Exception:
            logo_l = logo_r = None
        cells = []
        if logo_l and os.path.exists(logo_l):
            cells.append(RLImage(logo_l, width=6.5*cm, height=2.0*cm,
                                 kind="proportional"))
        else:
            cells.append(Paragraph("<b>HEBERLEIN</b>",
                                   _s("lg", fontSize=14,
                                      fontName="Helvetica-Bold",
                                      textColor=HEB_GREEN)))
        if logo_r and os.path.exists(logo_r):
            cells.append(RLImage(logo_r, width=2.0*cm, height=1.4*cm,
                                 kind="proportional"))
        else:
            cells.append("")
        t = Table([cells], colWidths=[CW * 0.6, CW * 0.4])
        t.setStyle(TableStyle([
            ("ALIGN",  (1, 0), (1, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return t

    # ── Section table helper ──────────────────────────────────────────
    def _sec_table(header, rows, col_widths=None):
        cw = col_widths or [CW * 0.55, CW * 0.45]
        data = [[Paragraph(f"<b>{header}</b>",
                           _s("th", fontSize=9, fontName="Helvetica-Bold",
                              textColor=WHITE)), ""]]
        for label, value in rows:
            data.append([Paragraph(str(label), s_normal),
                         Paragraph(str(value), s_normal)])
        ts = TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), HEB_GREEN),
            ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
            ("SPAN",          (0, 0), (-1, 0)),
            ("TOPPADDING",    (0, 0), (-1, 0), 5),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
            ("LEFTPADDING",   (0, 0), (-1, 0), 8),
            ("FONTSIZE",      (0, 1), (-1, -1), 9),
            ("TOPPADDING",    (0, 1), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            ("LEFTPADDING",   (0, 1), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 1), (-1, -1), 8),
            ("LINEBELOW",     (0, 1), (-1, -2), 0.4,
             colors.HexColor("#E0E0E0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, ROW_LIGHT]),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ])
        t = Table(data, colWidths=cw)
        t.setStyle(ts)
        return t

    # ── KPI row ───────────────────────────────────────────────────────
    def _kpi_table():
        kpis = [
            ("Total flow demand", f"{total_nl_min:.1f}", "Nl/min"),
            ("Total flow demand", f"{total_m3h:.2f}",   "m³/h"),
            ("Min. compressor\n(+20% reserve)", f"{total_m3h_r:.2f}", "m³/h"),
            ("Required pressure\n(incl. losses)", f"{req_p:.2f}", "bar"),
        ]
        cells = []
        for lbl, val, unit in kpis:
            inner = Table(
                [[Paragraph(lbl,  s_kpi_l)],
                 [Paragraph(val,  s_kpi_v)],
                 [Paragraph(unit, s_kpi_l)]],
                colWidths=[CW / 4 - 4*mm]
            )
            inner.setStyle(TableStyle([
                ("BOX",        (0,0), (-1,-1), 0.8,
                 colors.HexColor("#D0DDF0")),
                ("BACKGROUND", (0,0), (-1,-1),
                 colors.HexColor("#F4F8FF")),
                ("TOPPADDING",    (0,0), (-1,-1), 4),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                ("LEFTPADDING",   (0,0), (-1,-1), 6),
                ("RIGHTPADDING",  (0,0), (-1,-1), 6),
            ]))
            cells.append(inner)
        t = Table([cells],
                  colWidths=[CW / 4] * 4,
                  rowHeights=[None])
        t.setStyle(TableStyle([
            ("VALIGN",       (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING",  (0,0), (-1,-1), 2),
            ("RIGHTPADDING", (0,0), (-1,-1), 2),
        ]))
        return t

    # ── Network drawing (vector) ──────────────────────────────────────
    def _network_drawing(w, h):
        """Render the network graph as a ReportLab Drawing."""
        import math as _math
        d = Drawing(w, h)

        if not graph.nodes:
            d.add(String(w/2, h/2, "No nodes",
                         fontSize=10, textAnchor="middle",
                         fillColor=colors.HexColor("#aaaaaa")))
            return d

        # Compute bounding box
        xs = [n.x for n in graph.nodes.values()]
        ys = [n.y for n in graph.nodes.values()]
        pad = 40
        x0, x1 = min(xs)-pad, max(xs)+pad
        y0, y1 = min(ys)-pad, max(ys)+pad
        sx = w / max(x1-x0, 1)
        sy = h / max(y1-y0, 1)
        sc = min(sx, sy)

        def tx(x): return (x - x0) * sc
        def ty(y): return h - (y - y0) * sc   # flip Y for PDF

        NODE_C = {
            NODE_SOURCE:  colors.HexColor("#1D3557"),
            NODE_SEGMENT: colors.HexColor("#457B9D"),
            NODE_SPLIT:   colors.HexColor("#E9C46A"),
            NODE_JET:     colors.HexColor("#39A650"),
            NODE_REDUCER: colors.HexColor("#E76F51"),
        }

        # Draw edges first.
        # Routing: exit right edge of source node → turn at fixed x near
        # source → go vertical to target row → go horizontal to target.
        # Using the source node's right edge as the turn x prevents multiple
        # outgoing edges from the same node from overlapping each other.
        for a_id, b_id in graph.edges:
            a = graph.nodes.get(a_id)
            b = graph.nodes.get(b_id)
            if not a or not b:
                continue
            ax, ay = tx(a.x), ty(a.y)
            bx, by = tx(b.x), ty(b.y)
            a_hw = a.width()  * sc * 0.8 / 2
            b_hw = b.width()  * sc * 0.8 / 2
            # Exit from right edge of a, enter from left edge of b
            x_exit  = ax + a_hw          # start of horizontal run
            x_enter = bx - b_hw          # end of horizontal run
            # Turn point: fixed at 60% between exit and enter so vertical
            # segments from the same source are all at the same x, but
            # different enough from source right edge to look clean.
            x_turn  = x_exit + (x_enter - x_exit) * 0.18
            v = b.result_v if b.kind in (NODE_SEGMENT, NODE_REDUCER) else 0.0
            if   v <= 0:                          ec = colors.HexColor("#455a64")
            elif 20.0 <= v <= 30.0:              ec = colors.HexColor("#2e7d32")
            elif (15.0 <= v < 20.0) or (30.0 < v <= 35.0): ec = colors.HexColor("#e65100")
            else:                                 ec = colors.HexColor("#c62828")
            # 3-segment orthogonal route: horizontal → vertical → horizontal
            segs_to_draw = []
            if abs(ay - by) < 2:
                # Same row: straight horizontal line
                segs_to_draw = [((x_exit, ay), (x_enter, by))]
            else:
                segs_to_draw = [
                    ((x_exit,  ay), (x_turn, ay)),
                    ((x_turn,  ay), (x_turn, by)),
                    ((x_turn,  by), (x_enter, by)),
                ]
            for p1, p2 in segs_to_draw:
                d.add(Line(p1[0], p1[1], p2[0], p2[1],
                           strokeColor=ec, strokeWidth=1.4))

        # Draw nodes
        for node in graph.nodes.values():
            cx, cy = tx(node.x), ty(node.y)
            nw = node.width()  * sc * 0.8
            nh = node.height() * sc * 0.8
            nc = NODE_C.get(node.kind, colors.grey)
            x1n = cx - nw/2
            y1n = cy - nh/2

            if node.kind == NODE_REDUCER:
                # Trapezoid
                inset = nh * 0.25
                pts = [x1n, cy+nh/2,
                       x1n+nw, cy+nh/2-inset,
                       x1n+nw, cy-nh/2+inset,
                       x1n, cy-nh/2]
                d.add(Polygon(pts, fillColor=nc, strokeColor=nc.clone(),
                              strokeWidth=0.5))
            else:
                d.add(Rect(x1n, y1n, nw, nh,
                           rx=3, ry=3,
                           fillColor=nc, strokeColor=nc,
                           strokeWidth=0.5))

            # Determine whether this node has a bottom strip (Jet or Source).
            # Strip occupies the bottom 30% of the node box.
            # In ReportLab coords: y1n = bottom edge, y1n+nh = top edge.
            has_strip = (
                (node.kind == NODE_JET and node.result_dp_cum > 0) or
                (node.kind == NODE_SOURCE and req_p > 0)
            )
            strip_h   = nh * 0.30   # height of bottom info strip
            # Text area: full node if no strip, upper 70% if strip present
            txt_area_bot = y1n + (strip_h if has_strip else 0)
            txt_area_top = y1n + nh
            txt_cy       = (txt_area_bot + txt_area_top) / 2   # vertical centre

            # Label — support two-line labels (split on \n)
            raw_lbl = node.label()
            lbl_parts = raw_lbl.split("\n")
            longest = max(lbl_parts, key=len)
            fs = max(5, min(8, int(nw / max(len(longest)*0.55, 1))))
            line_h = fs * 1.35
            for li, part in enumerate(lbl_parts):
                y_off = (len(lbl_parts) - 1) / 2 * line_h - li * line_h
                d.add(String(cx, txt_cy + y_off - fs * 0.35,
                             part.strip(),
                             fontSize=fs, fontName="Helvetica-Bold",
                             fillColor=colors.white,
                             textAnchor="middle"))

            # Bottom strip — drawn AFTER label so it sits on top of node rect
            if node.kind == NODE_JET and node.result_dp_cum > 0:
                ok  = node.result_dp_cum < 0.3
                sc2 = colors.HexColor("#1b5e20") if ok else colors.HexColor("#b71c1c")
                d.add(Rect(x1n+1, y1n, nw-2, strip_h,
                           fillColor=sc2, strokeColor=sc2, strokeWidth=0))
                strip_txt = f"{node.nozzle_pressure:.2f} bar"
                d.add(String(cx, y1n + strip_h * 0.28,
                             strip_txt,
                             fontSize=max(4, fs-1), fontName="Helvetica",
                             fillColor=colors.white, textAnchor="middle"))

            if node.kind == NODE_SOURCE and req_p > 0:
                d.add(Rect(x1n+1, y1n, nw-2, strip_h,
                           fillColor=colors.HexColor("#0d2137"),
                           strokeColor=colors.HexColor("#0d2137"),
                           strokeWidth=0))
                sp_txt = f">= {req_p:.2f} bar"
                d.add(String(cx, y1n + strip_h * 0.28,
                             sp_txt,
                             fontSize=max(4, fs-1), fontName="Helvetica-Bold",
                             fillColor=colors.white, textAnchor="middle"))

        return d

    # ── Segment results table ─────────────────────────────────────────
    def _seg_results_table():
        hdr = ["Segment", "Length\n(m)", "Press.\n(bar)",
               "Flow\n(Nl/min)", "Rec.ø\n(mm)", "Velocity\n(m/s)",
               "Seg.ΔP\n(bar)", "Cum.ΔP\n(bar)", "Status"]
        col_w = [3.2*cm, 1.5*cm, 1.5*cm, 1.8*cm,
                 1.5*cm, 1.8*cm, 1.8*cm, 1.8*cm, 1.8*cm]
        data = [[Paragraph(f"<b>{h}</b>",
                           _s(f"h{i}", fontSize=8, fontName="Helvetica-Bold",
                              textColor=WHITE, leading=10))
                 for i, h in enumerate(hdr)]]
        for n in segs:
            is_red = n.kind == NODE_REDUCER
            ok  = (n.result_v == 0 or (15.0 <= n.result_v <= 35.0)) and n.result_dp_cum <= 0.3
            st  = "OK" if ok else ("⚠ v" if not (n.result_v == 0 or (15.0 <= n.result_v <= 35.0)) else "⚠ ΔP")
            rec = (f"ø{n.result_dn_rec}" if n.result_dn_rec else "—"
                   ) if not is_red else f"ø{int(n.red_d_out)}"
            row = [
                Paragraph(n.label().replace("\n"," "), s_small),
                Paragraph(f"{n.seg_length:.1f}" if not is_red else "—", s_small),
                Paragraph(f"{n.seg_pressure:.2f}" if not is_red
                          else f"{n.red_pressure:.2f}", s_small),
                Paragraph(f"{n.result_flow_nl_s*60:.2f}", s_small),
                Paragraph(rec, s_small),
                Paragraph(f"{n.result_v:.2f}", s_small),
                Paragraph(f"{n.result_dp:.4f}", s_small),
                Paragraph(f"{n.result_dp_cum:.4f}", s_small),
                Paragraph(st, _s("st", fontSize=8, fontName="Helvetica-Bold",
                                 textColor=HEB_GREEN if ok else WARN_RED)),
            ]
            data.append(row)
        ts = TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), HEB_GREEN),
            ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
            ("FONTSIZE",      (0,1), (-1,-1), 8),
            ("TOPPADDING",    (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("LEFTPADDING",   (0,0), (-1,-1), 4),
            ("RIGHTPADDING",  (0,0), (-1,-1), 4),
            ("LINEBELOW",     (0,1), (-1,-2), 0.3, colors.HexColor("#E0E0E0")),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, ROW_LIGHT]),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#E0E0E0")),
        ])
        t = Table(data, colWidths=col_w)
        t.setStyle(ts)
        return t

    # ── Jet results table ─────────────────────────────────────────────
    def _jet_results_table():
        hdr = ["Jet", "Count", "Set pressure\n(bar)",
               "Hole ø\n(mm)", "Flow\n(Nl/min)",
               "Cum.ΔP\n(bar)", "Status"]
        col_w = [3.5*cm, 1.4*cm, 2.2*cm, 1.6*cm,
                 2.0*cm, 1.8*cm, 1.8*cm]
        data = [[Paragraph(f"<b>{h}</b>",
                           _s(f"jh{i}", fontSize=8, fontName="Helvetica-Bold",
                              textColor=WHITE, leading=10))
                 for i, h in enumerate(hdr)]]
        for n in jets:
            ok  = n.result_dp_cum <= 0.3
            st  = "OK" if ok else "⚠ ΔP"
            try:
                d_mm = float(str(n.nozzle_db_jet.get("Luftbohrung", n.nozzle_hole_d)
                                 if n.nozzle_db_jet else n.nozzle_hole_d)
                             .replace(",", "."))
            except Exception:
                d_mm = n.nozzle_hole_d
            name = ((n.nozzle_db_jet.get("Jet","") if n.nozzle_db_jet
                     else n.nozzle_name) or "Jet")
            row = [
                Paragraph(name, s_small),
                Paragraph(str(n.nozzle_count), s_small),
                Paragraph(f"{n.nozzle_pressure:.2f}", s_small),
                Paragraph(f"{d_mm:.3f}", s_small),
                Paragraph(f"{n.result_flow_nl_s*60:.2f}", s_small),
                Paragraph(f"{n.result_dp_cum:.4f}", s_small),
                Paragraph(st, _s("jst", fontSize=8, fontName="Helvetica-Bold",
                                 textColor=HEB_GREEN if ok else WARN_RED)),
            ]
            data.append(row)
        ts = TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), HEB_DARK),
            ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
            ("FONTSIZE",      (0,1), (-1,-1), 8),
            ("TOPPADDING",    (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("LEFTPADDING",   (0,0), (-1,-1), 4),
            ("RIGHTPADDING",  (0,0), (-1,-1), 4),
            ("LINEBELOW",     (0,1), (-1,-2), 0.3, colors.HexColor("#E0E0E0")),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, ROW_LIGHT]),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#E0E0E0")),
        ])
        t = Table(data, colWidths=col_w)
        t.setStyle(ts)
        return t

    # ── Page header/footer callbacks ──────────────────────────────────
    def _on_page(canvas_obj, doc):
        canvas_obj.saveState()
        import os, pathlib
        # ── Logos in header ───────────────────────────────────────────
        try:
            from ui.pathutil import resource_path as _rp
            logo_l = _rp("assets/images/heb_logo.png")
            logo_r = _rp("assets/images/header_logo_big.png")
        except Exception:
            logo_l = logo_r = None
            try:
                _base = pathlib.Path(__file__).resolve().parents[1]
                logo_l = str(_base / "assets" / "images" / "heb_logo.png")
                logo_r = str(_base / "assets" / "images" / "header_logo_big.png")
            except Exception:
                pass
        if logo_l and os.path.exists(str(logo_l)):
            canvas_obj.drawImage(str(logo_l), margin, PH - 2.5*cm,
                                 width=5.5*cm, height=1.8*cm,
                                 preserveAspectRatio=True, mask="auto")
        else:
            canvas_obj.setFont("Helvetica-Bold", 13)
            canvas_obj.setFillColor(HEB_GREEN)
            canvas_obj.drawString(margin, PH - 1.8*cm, "HEBERLEIN")
        if logo_r and os.path.exists(str(logo_r)):
            canvas_obj.drawImage(str(logo_r), PW - margin - 2.0*cm, PH - 2.4*cm,
                                 width=2.0*cm, height=1.4*cm,
                                 preserveAspectRatio=True, mask="auto")
        # ── Green separator line ──────────────────────────────────────
        canvas_obj.setStrokeColor(HEB_GREEN)
        canvas_obj.setLineWidth(1.5)
        canvas_obj.line(margin, PH - 2.7*cm, PW - margin, PH - 2.7*cm)
        # ── Footer ────────────────────────────────────────────────────
        canvas_obj.setFont("Helvetica", 7.5)
        canvas_obj.setFillColor(GREY_TEXT)
        canvas_obj.drawString(margin, 1.2*cm,
                              f"Air Supply Network — {title}  |  {date_str}"
                              + (f"  |  {created_by}" if created_by else ""))
        canvas_obj.drawRightString(PW - margin, 1.2*cm,
                                   f"Page {doc.page}")
        canvas_obj.setStrokeColor(colors.HexColor("#E0E0E0"))
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(margin, 1.6*cm, PW - margin, 1.6*cm)
        canvas_obj.restoreState()

    # ── Landscape page callback (Page 2 — Network Diagram) ───────────
    from reportlab.lib.pagesizes import landscape as _landscape
    PW_L, PH_L = _landscape(A4)   # 841.9 × 595.3 pt
    CW_L = PW_L - 2 * margin

    def _on_page_landscape(canvas_obj, doc):
        """Header/footer for the landscape diagram page."""
        canvas_obj.saveState()
        import os, pathlib
        try:
            from ui.pathutil import resource_path as _rp
            logo_l = _rp("assets/images/heb_logo.png")
            logo_r = _rp("assets/images/header_logo_big.png")
        except Exception:
            logo_l = logo_r = None
            try:
                _base = pathlib.Path(__file__).resolve().parents[1]
                logo_l = str(_base / "assets" / "images" / "heb_logo.png")
                logo_r = str(_base / "assets" / "images" / "header_logo_big.png")
            except Exception:
                pass
        if logo_l and os.path.exists(str(logo_l)):
            canvas_obj.drawImage(str(logo_l), margin, PH_L - 2.5*cm,
                                 width=5.5*cm, height=1.8*cm,
                                 preserveAspectRatio=True, mask="auto")
        else:
            canvas_obj.setFont("Helvetica-Bold", 13)
            canvas_obj.setFillColor(HEB_GREEN)
            canvas_obj.drawString(margin, PH_L - 1.8*cm, "HEBERLEIN")
        if logo_r and os.path.exists(str(logo_r)):
            canvas_obj.drawImage(str(logo_r), PW_L - margin - 2.0*cm, PH_L - 2.4*cm,
                                 width=2.0*cm, height=1.4*cm,
                                 preserveAspectRatio=True, mask="auto")
        canvas_obj.setStrokeColor(HEB_GREEN)
        canvas_obj.setLineWidth(1.5)
        canvas_obj.line(margin, PH_L - 2.7*cm, PW_L - margin, PH_L - 2.7*cm)
        canvas_obj.setFont("Helvetica", 7.5)
        canvas_obj.setFillColor(GREY_TEXT)
        canvas_obj.drawString(margin, 1.2*cm,
                              f"Air Supply Network — {title}  |  {date_str}"
                              + (f"  |  {created_by}" if created_by else ""))
        canvas_obj.drawRightString(PW_L - margin, 1.2*cm,
                                   f"Page {doc.page}")
        canvas_obj.setStrokeColor(colors.HexColor("#E0E0E0"))
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(margin, 1.6*cm, PW_L - margin, 1.6*cm)
        canvas_obj.restoreState()

    # ── Landscape diagram — drawn directly on canvas via _on_page_landscape ──
    # Avoids Flowable height miscalculation: diagram is painted in the page
    # callback so we control exact coordinates without ReportLab's flow engine.

    leg_items = [
        ("#1D3557", "Source"),
        ("#457B9D", "Pipe"),
        ("#E9C46A", "Y-Split"),
        ("#E76F51", "Reducer"),
        ("#39A650", "Jet"),
        ("#2e7d32", "20–30 m/s  optimal"),
        ("#e65100", "15–20 / 30–35 m/s  acceptable"),
        ("#c62828", "< 15 or > 35 m/s  out of range"),
    ]

    # Fixed geometry for the landscape diagram page (all in pt):
    # Header separator is at PH_L - 2.7cm; we start content 0.45cm below that.
    _L_top   = PH_L - 3.15*cm  # y of top content edge (below header separator + gap)
    _L_bot   = 2.2*cm           # y of bottom content edge (above footer line)
    _leg_h_L = 0.9*cm           # legend strip height
    _title_h = 0.85*cm          # title + HR combined height
    _net_w_L = PW_L - 2 * margin
    _net_y_L = _L_bot + _leg_h_L                   # diagram bottom y
    _net_h_L = _L_top - _title_h - _net_y_L        # diagram height

    def _draw_diagram_on_canvas(canvas_obj):
        """Draw network diagram + legend directly onto the landscape canvas."""
        canvas_obj.saveState()
        # Title — sits 0.45cm below the green header separator line
        canvas_obj.setFont("Helvetica-Bold", 14)
        canvas_obj.setFillColor(HEB_DARK)
        canvas_obj.drawString(margin, _L_top - 0.02*cm,
                              f"{title} — Network Diagram")
        # HR under title
        canvas_obj.setStrokeColor(HEB_GREEN)
        canvas_obj.setLineWidth(1.0)
        canvas_obj.line(margin, _L_top - 0.55*cm, PW_L - margin, _L_top - 0.55*cm)
        # Network drawing
        drawing = _network_drawing(_net_w_L, _net_h_L)
        drawing.drawOn(canvas_obj, margin, _net_y_L)
        # Legend strip
        canvas_obj.setFillColor(colors.HexColor("#F8F8F8"))
        canvas_obj.setStrokeColor(colors.HexColor("#E0E0E0"))
        canvas_obj.setLineWidth(0.3)
        canvas_obj.rect(margin, _L_bot, _net_w_L, _leg_h_L, fill=1)
        item_w = _net_w_L / len(leg_items)
        canvas_obj.setFont("Helvetica", 7.5)
        for i, (col, lbl) in enumerate(leg_items):
            x = margin + i * item_w + 6
            canvas_obj.setFillColor(colors.HexColor(col))
            canvas_obj.rect(x, _L_bot + _leg_h_L * 0.28, 8, 8, fill=1, stroke=0)
            canvas_obj.setFillColor(colors.HexColor("#555555"))
            canvas_obj.drawString(x + 12, _L_bot + _leg_h_L * 0.26, lbl)
        canvas_obj.restoreState()

    # Patch the landscape page callback to also draw the diagram
    _orig_on_landscape = _on_page_landscape

    def _on_page_landscape(canvas_obj, doc):  # noqa: F811
        _orig_on_landscape(canvas_obj, doc)
        _draw_diagram_on_canvas(canvas_obj)

    # ── Build story ───────────────────────────────────────────────────
    # Page 1 uses portrait A4; Page 2 uses landscape A4.
    # ReportLab's SimpleDocTemplate doesn't support mixed page sizes,
    # so we use BaseDocTemplate with two PageTemplates.
    from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, NextPageTemplate

    # Frame sits between footer top (1.9cm) and header separator (PH-2.9cm)
    _p_frame_y  = 1.9 * cm
    _p_frame_h  = PH - 2.9*cm - _p_frame_y
    portrait_frame = Frame(
        margin, _p_frame_y,
        PW - 2*margin, _p_frame_h,
        topPadding=4, bottomPadding=4, leftPadding=0, rightPadding=0,
        id="portrait",
    )
    # Landscape frame: content drawn entirely via canvas callback, so frame
    # can be a minimal 1pt stub — avoids any flowable sizing conflicts.
    landscape_frame = Frame(
        margin, PH_L / 2,
        PW_L - 2*margin, 1,
        topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0,
        id="landscape",
    )

    doc = BaseDocTemplate(
        path,
        pageTemplates=[
            PageTemplate(id="portrait",  frames=[portrait_frame],
                         onPage=_on_page,           pagesize=A4),
            PageTemplate(id="landscape", frames=[landscape_frame],
                         onPage=_on_page_landscape, pagesize=_landscape(A4)),
        ],
        title=f"Air Supply Network — {title}",
        author="Heberlein Technology AG",
    )

    story = []

    # ── Page 1: title + KPIs + summary + tables ───────────────────────
    story.append(Paragraph(title, s_title))
    story.append(HRFlowable(width=CW, thickness=1.0,
                             color=HEB_GREEN, spaceAfter=4))

    story.append(Paragraph("Compressor Requirement", s_h1))
    story.append(_kpi_table())
    story.append(Spacer(1, 3*mm))

    summary_rows = [
        ("Active jet nodes",          str(len(jets))),
        ("Pipe / reducer segments",   str(len(segs))),
        ("Total pipe ΔP",             f"{total_dp:.4f} bar"),
        ("Worst jet cumulative ΔP",   f"{worst_dp:.4f} bar"),
        ("Recommended receiver tank", f"≥ {tank_l:.0f} l  (rule of thumb: V=Q×6)"),
        ("Compressor delivery",       f"≥ {total_m3h_r:.2f} m³/h at ≥ {req_p:.2f} bar"),
    ]
    if total_nl_s > 0 and req_p > 0:
        oc = _operating_cost(total_nl_s, req_p, 16, 250, 0.22, 0.70)
        summary_rows.append(
            ("Est. annual electricity cost",
             f"CHF {oc['cost_chf']:,.0f}/yr  "
             f"({oc['power_kw']:.3f} kW × {oc['hours_year']:.0f} h × 0.22 CHF/kWh, η=0.70)"))
    story.append(_sec_table("Network Summary", summary_rows))
    story.append(Spacer(1, 4*mm))

    if segs:
        story.append(Paragraph("Pipe Segments & Reducers", s_h1))
        story.append(_seg_results_table())
        story.append(Spacer(1, 5*mm))

    if jets:
        story.append(Paragraph("Jet Nodes", s_h1))
        story.append(_jet_results_table())
        story.append(Spacer(1, 5*mm))

    story.append(HRFlowable(width=CW, thickness=0.3,
                             color=colors.HexColor("#E0E0E0"), spaceAfter=4))
    story.append(Paragraph(
        "Physics: Pipe ΔP via Darcy-Weisbach (smooth pipe). "
        "Reducer ΔP via Borda-Carnot. "
        "Fitting equivalent lengths: 90° elbow L/D=30, 45° elbow L/D=16. "
        "Flow normalised to NTP (0°C, 1013 mbar). "
        "Discharge coefficient Cd=0.65 (sharp-edged orifice, unless overridden).",
        _s("fn", fontSize=7, fontName="Helvetica", textColor=GREY_TEXT, leading=10)))

    # ── Page 2: landscape network diagram ────────────────────────────
    story.append(NextPageTemplate("landscape"))
    story.append(PageBreak())
    story.append(Spacer(1, 1))   # placeholder — diagram drawn by page callback

    # ── Page 3 (optional): Optimization Recommendations ──────────────
    if opt_diffs:
        story.append(NextPageTemplate("portrait"))
        story.append(PageBreak())

        story.append(Paragraph("Optimization Recommendations", s_h1))
        story.append(Spacer(1, 3*mm))
        story.append(Paragraph(
            "The following changes are recommended to bring all pipe segments "
            "into the optimal velocity range (20–30 m/s). "
            "Items marked ⚠ are informational (pipe length is fixed).",
            _s("intro", fontSize=9, fontName="Helvetica",
               textColor=GREY_TEXT, leading=13)))
        story.append(Spacer(1, 4*mm))

        opt_hdr = ["Node", "Parameter", "Current", "→ Recommended", "Reason"]
        opt_rows = [[Paragraph(h, _s(f"oh{i}", fontSize=9,
                                     fontName="Helvetica-Bold",
                                     textColor=WHITE))
                     for i, h in enumerate(opt_hdr)]]
        for d in opt_diffs:
            is_info = "info" in d["param"]
            row_color = colors.HexColor("#fff8e1") if is_info else colors.HexColor("#e8f5e9")
            new_style = _s("nv", fontSize=9, fontName="Helvetica-Bold",
                           textColor=colors.HexColor("#2e7d32") if not is_info
                           else GREY_TEXT)
            opt_rows.append([
                Paragraph(d["label"],   _s("oc", fontSize=9, fontName="Helvetica", textColor=HEB_DARK)),
                Paragraph(d["param"],   _s("oc", fontSize=9, fontName="Helvetica", textColor=GREY_TEXT)),
                Paragraph(d["old_val"], _s("oc", fontSize=9, fontName="Helvetica", textColor=GREY_TEXT)),
                Paragraph(d["new_val"], new_style),
                Paragraph(d["reason"],  _s("oc", fontSize=9, fontName="Helvetica", textColor=GREY_TEXT)),
            ])

        opt_col_w = [CW * f for f in (0.22, 0.18, 0.14, 0.18, 0.28)]
        opt_tbl = Table(opt_rows, colWidths=opt_col_w, repeatRows=1)
        opt_style = TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), HEB_GREEN),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.HexColor("#e8f5e9"), colors.HexColor("#f5fff7")]),
            ("GRID",          (0, 0), (-1, -1), 0.25, colors.HexColor("#c8e6c9")),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
        # Colour info rows distinctly
        for ri, d in enumerate(opt_diffs, 1):
            if "info" in d["param"]:
                opt_style.add("BACKGROUND", (0, ri), (-1, ri),
                              colors.HexColor("#fff8e1"))
        opt_tbl.setStyle(opt_style)
        story.append(opt_tbl)
        story.append(Spacer(1, 6*mm))
        story.append(Paragraph(
            "Note: only pipe diameters are adjusted automatically. "
            "Pipe lengths, operating pressures, and network topology "
            "remain unchanged — these are determined by the physical installation.",
            _s("fn2", fontSize=7, fontName="Helvetica-Oblique",
               textColor=GREY_TEXT, leading=10)))

    doc.build(story)


# ---------------------------------------------------------------------------
# Excel export
# ---------------------------------------------------------------------------

def _generate_air_supply_excel(path: str, graph: NetworkGraph, title: str):
    """Generate an Excel workbook with network summary + segment + jet sheets."""
    try:
        import openpyxl
        from openpyxl.styles import (
            Font, PatternFill, Alignment, Border, Side, numbers,
        )
        from openpyxl.utils import get_column_letter
    except ImportError:
        raise RuntimeError("openpyxl not installed. Run: pip install openpyxl")

    import datetime

    GREEN  = "FF39A650"
    DARK   = "FF1D3557"
    LIGHT  = "FFF2F9F3"
    ORANGE = "FFE76F51"
    RED    = "FFe53935"
    WHITE  = "FFFFFFFF"
    GREY   = "FF555555"

    wb = openpyxl.Workbook()

    def _hdr_font(color=WHITE, sz=10, bold=True):
        return Font(name="Calibri", size=sz, bold=bold, color=color)

    def _fill(hex_color):
        return PatternFill("solid", fgColor=hex_color)

    def _border():
        s = Side(style="thin", color="FFE0E0E0")
        return Border(left=s, right=s, top=s, bottom=s)

    def _col_widths(ws, widths):
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w

    def _auto_width(ws):
        for col in ws.columns:
            max_len = max((len(str(c.value or "")) for c in col), default=8)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)

    # ── Sheet 1: Summary ─────────────────────────────────────────────
    ws = wb.active
    ws.title = "Summary"
    jets = [n for n in graph.nodes.values() if n.kind == NODE_JET]
    segs = [n for n in graph.nodes.values()
            if n.kind in (NODE_SEGMENT, NODE_REDUCER)]
    srcs = [n for n in graph.nodes.values() if n.kind == NODE_SOURCE]

    total_nl_s   = sum(n.result_flow_nl_s for n in jets)
    total_nl_min = total_nl_s * 60.0
    total_m3h    = total_nl_s * 3.6
    total_m3h_r  = total_m3h * 1.2
    req_p        = max((n.result_p_required for n in srcs), default=0.0)
    if req_p == 0.0:
        req_p = (max((n.nozzle_pressure for n in jets), default=0.0)
                 + max((n.result_dp_cum for n in jets), default=0.0))
    tank_l  = total_m3h_r * 6
    worst_dp = max((n.result_dp_cum for n in jets), default=0.0)
    total_dp = sum(n.result_dp for n in segs)

    # Title row
    ws["A1"] = title
    ws["A1"].font = Font(name="Calibri", size=14, bold=True, color=DARK)
    ws["A2"] = f"Generated: {datetime.date.today().strftime('%d.%m.%Y')}"
    ws["A2"].font = Font(name="Calibri", size=9, color=GREY)
    ws.merge_cells("A1:D1")
    ws.merge_cells("A2:D2")
    ws.row_dimensions[3].height = 6

    # Section header helper
    def _sh(ws, row, label):
        ws.cell(row=row, column=1, value=label).font = _hdr_font()
        ws.cell(row=row, column=1).fill = _fill(GREEN)
        ws.merge_cells(start_row=row, start_column=1,
                       end_row=row, end_column=2)

    def _row(ws, r, label, value, unit=""):
        ws.cell(row=r, column=1, value=label).font = Font(
            name="Calibri", size=9, color=GREY)
        ws.cell(row=r, column=2, value=value).font = Font(
            name="Calibri", size=9, bold=True, color=DARK)
        if unit:
            ws.cell(row=r, column=3, value=unit).font = Font(
                name="Calibri", size=9, color=GREY)

    r = 4
    _sh(ws, r, "Compressor Requirement"); r += 1
    _row(ws, r, "Total flow demand", round(total_nl_min, 2), "Nl/min"); r += 1
    _row(ws, r, "Total flow demand", round(total_m3h, 3),   "m³/h");   r += 1
    _row(ws, r, "Min. compressor output (+20%)", round(total_m3h_r, 3), "m³/h"); r += 1
    _row(ws, r, "Required working pressure", round(req_p, 3), "bar"); r += 1
    _row(ws, r, "Recommended receiver tank", round(tank_l, 0), "l"); r += 2

    _sh(ws, r, "Network Summary"); r += 1
    _row(ws, r, "Jet nodes",           len(jets)); r += 1
    _row(ws, r, "Pipe/reducer nodes",  len(segs)); r += 1
    _row(ws, r, "Total pipe ΔP",       round(total_dp, 5),   "bar"); r += 1
    _row(ws, r, "Worst jet cum. ΔP",   round(worst_dp, 5),   "bar"); r += 1

    _col_widths(ws, [30, 18, 10])

    # ── Sheet 2: Segments ─────────────────────────────────────────────
    ws2 = wb.create_sheet("Segments")
    hdr = ["Segment", "Type", "Length (m)", "Pressure (bar)",
           "Flow (Nl/min)", "Rec. ø (mm)", "Velocity (m/s)",
           "Seg. ΔP (bar)", "Cum. ΔP (bar)", "Bends 90°", "Bends 45°", "Status"]
    for ci, h in enumerate(hdr, 1):
        c = ws2.cell(row=1, column=ci, value=h)
        c.font = _hdr_font()
        c.fill = _fill(GREEN)
        c.alignment = Alignment(horizontal="center", vertical="center",
                                wrap_text=True)
        c.border = _border()
    ws2.row_dimensions[1].height = 30

    for ri, n in enumerate(segs, 2):
        is_red = n.kind == NODE_REDUCER
        ok = (15.0 <= n.result_v <= 35.0 or n.result_v == 0) and n.result_dp_cum <= 0.3
        vals = [
            n.label().replace("\n"," "),
            "Reducer" if is_red else "Pipe",
            n.seg_length if not is_red else None,
            round(n.seg_pressure if not is_red else n.red_pressure, 3),
            round(n.result_flow_nl_s * 60, 3),
            n.result_dn_rec if not is_red else int(n.red_d_out),
            round(n.result_v, 3),
            round(n.result_dp, 5),
            round(n.result_dp_cum, 5),
            n.seg_bends_90 if not is_red else None,
            n.seg_bends_45 if not is_red else None,
            "OK" if ok else "WARNING",
        ]
        bg = LIGHT if ri % 2 == 0 else WHITE
        for ci, v in enumerate(vals, 1):
            c = ws2.cell(row=ri, column=ci, value=v)
            c.font = Font(name="Calibri", size=9,
                          color=(RED if (ci == 12 and not ok) else GREY))
            c.fill = _fill(bg)
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = _border()
    _auto_width(ws2)

    # ── Sheet 3: Jets ─────────────────────────────────────────────────
    ws3 = wb.create_sheet("Jets")
    hdr3 = ["Jet name", "Count", "Set pressure (bar)",
            "Hole ø (mm)", "No. of holes", "Cd",
            "Flow total (Nl/min)", "Cum. ΔP (bar)", "Status"]
    for ci, h in enumerate(hdr3, 1):
        c = ws3.cell(row=1, column=ci, value=h)
        c.font = _hdr_font()
        c.fill = _fill(DARK)
        c.alignment = Alignment(horizontal="center", vertical="center",
                                wrap_text=True)
        c.border = _border()
    ws3.row_dimensions[1].height = 30

    for ri, n in enumerate(jets, 2):
        ok = n.result_dp_cum <= 0.3
        try:
            d_mm = float(str(n.nozzle_db_jet.get("Luftbohrung", n.nozzle_hole_d)
                             if n.nozzle_db_jet else n.nozzle_hole_d)
                         .replace(",", "."))
            n_holes = int(n.nozzle_db_jet.get("LuftlochAnzahl", n.nozzle_n_holes)
                          if n.nozzle_db_jet else n.nozzle_n_holes)
        except Exception:
            d_mm, n_holes = n.nozzle_hole_d, n.nozzle_n_holes
        name = ((n.nozzle_db_jet.get("Jet","") if n.nozzle_db_jet
                 else n.nozzle_name) or "Jet")
        vals3 = [
            name, n.nozzle_count,
            round(n.nozzle_pressure, 3),
            round(d_mm, 4), n_holes,
            round(n.nozzle_cd, 3),
            round(n.result_flow_nl_s * 60, 3),
            round(n.result_dp_cum, 5),
            "OK" if ok else "WARNING",
        ]
        bg = LIGHT if ri % 2 == 0 else WHITE
        for ci, v in enumerate(vals3, 1):
            c = ws3.cell(row=ri, column=ci, value=v)
            c.font = Font(name="Calibri", size=9,
                          color=(RED if (ci == 9 and not ok) else GREY))
            c.fill = _fill(bg)
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = _border()
    _auto_width(ws3)

    wb.save(path)