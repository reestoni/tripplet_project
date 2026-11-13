"""air_network.py - Air Supply Network Calculator, the computing part without Qt (2026-11-13, moved out of
ui/screen_air_supply.py for the web version; the desktop screen uses it).

Graph:  Source → Pipe segments / Reducers → Y-Splits → Jets
Solver: bottom-up flow, top-down cumulative ΔP + inlet pressure at every jet (NetworkGraph.solve).
Optimiser (optimize_graph), operating cost, network summaries, saved networks (tblAirNetwork /
tblAirNetworkData), PDF and Excel reports (path or binary file object).
"""
from __future__ import annotations

import copy
import json
import math
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

ENSURE_TABLES = True     # the web sets this to False (never creates tables)
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
    # rect() / center() (Qt geometry) are added by ui/screen_air_supply.py


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
    """The desktop creates the two tables on first use (as before 2026-11-13); the web only checks them
    (tables_available) and never creates anything."""
    global _TABLES_ENSURED
    if _TABLES_ENSURED or not ENSURE_TABLES:
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


optimize_graph = _optimize_graph
operating_cost = _operating_cost
NODE_KINDS = (NODE_SOURCE, NODE_SEGMENT, NODE_SPLIT, NODE_REDUCER, NODE_JET)
V_MIN, V_MAX, DP_WARN, DP_INFO = 15.0, 35.0, 0.5, 0.3
OPCOST_DEFAULTS = {"hours": 16.0, "days": 250.0, "price": 0.22, "eta": 0.70}


def tables_available() -> bool:
    try:
        from db.connection import table_exists
        return bool(table_exists("tblAirNetwork") and table_exists("tblAirNetworkData"))
    except Exception:
        return False


def example_network() -> NetworkGraph:
    """The "Example" network of the toolbar."""
    g = NetworkGraph()

    def _n(kind, x, y, **kw):
        node = Node(kind, x, y)
        for k, v in kw.items():
            setattr(node, k, v)
        g.add_node(node)
        return node
    src = _n(NODE_SOURCE, 100, 200)
    s1 = _n(NODE_SEGMENT, 250, 200, seg_length=10.0, seg_pressure=5.0)
    sp1 = _n(NODE_SPLIT, 400, 200)
    s2 = _n(NODE_SEGMENT, 520, 120, seg_length=5.0, seg_pressure=5.0)
    s3 = _n(NODE_SEGMENT, 520, 280, seg_length=5.0, seg_pressure=5.0)
    sp2 = _n(NODE_SPLIT, 660, 120)
    j1 = _n(NODE_JET, 780, 80, nozzle_name="P142-1", nozzle_hole_d=1.0, nozzle_n_holes=1, nozzle_count=4, nozzle_pressure=4.5)
    j2 = _n(NODE_JET, 780, 160, nozzle_name="P142-2", nozzle_hole_d=1.2, nozzle_n_holes=2, nozzle_count=4, nozzle_pressure=4.5)
    j3 = _n(NODE_JET, 660, 280, nozzle_name="Generic", nozzle_hole_d=0.8, nozzle_n_holes=1, nozzle_count=8, nozzle_pressure=5.0)
    for a, b in [(src, s1), (s1, sp1), (sp1, s2), (sp1, s3), (s2, sp2), (sp2, j1), (sp2, j2), (s3, j3)]:
        g.add_edge(a.id, b.id)
    g.solve()
    return g


def required_pressure(graph: NetworkGraph) -> float:
    """Required compressor pressure = the source's result_p_required (max jet pressure + losses on the
    critical path); without a source: max jet pressure + worst cumulative ΔP."""
    jets = [n for n in graph.nodes.values() if n.kind == NODE_JET]
    srcs = [n for n in graph.nodes.values() if n.kind == NODE_SOURCE]
    req_p = max((n.result_p_required for n in srcs), default=0.0)
    if req_p == 0.0:
        prs = [n.nozzle_pressure for n in jets]
        req_p = (max(prs) if prs else 0.0) + max((n.result_dp_cum for n in jets), default=0.0)
    return req_p


def opcost_view(flow_nl_s: float, req_p: float, params: Dict[str, float]) -> Optional[Dict[str, float]]:
    """Operating cost + CHF per Nm³ (None without flow or pressure)."""
    if flow_nl_s <= 0 or req_p <= 0:
        return None
    r = _operating_cost(flow_nl_s, req_p, params["hours"], params["days"], params["price"], params["eta"])
    nm3 = flow_nl_s * r["hours_year"] * 3600.0 / 1000.0
    return {**r, "nm3_year": nm3, "chf_per_nm3": r["cost_chf"] / nm3 if nm3 > 0 else None}


def source_summary(graph: NetworkGraph, params: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """What the Source panel shows: demand, compressor size, required pressure, receiver, the guidance
    (status ok / insufficient / no jets) and the operating cost."""
    jets = [n for n in graph.nodes.values() if n.kind == NODE_JET]
    segs = [n for n in graph.nodes.values() if n.kind == NODE_SEGMENT]
    srcs = [n for n in graph.nodes.values() if n.kind == NODE_SOURCE]
    total = sum(n.result_flow_nl_s for n in jets)
    m3h = total * 3.6
    res = m3h * 1.2
    req_p = required_pressure(graph)
    set_p = max((n.source_pressure for n in srcs), default=6.0)
    worst_dp = max((n.result_dp_cum for n in jets), default=0.0)
    return {"flow_nl_min": total * 60.0, "flow_m3h": m3h, "reserve_m3h": res, "req_p": req_p, "set_p": set_p,
            "margin": set_p - req_p, "tank_l": res * 6, "worst_dp": worst_dp, "n_jets": len(jets),
            "n_segs": len(segs), "status": "none" if res <= 0 else ("ok" if set_p - req_p >= 0 else "low"),
            "opcost": opcost_view(total, req_p, params or OPCOST_DEFAULTS)}


def node_view(n: Node) -> Dict[str, Any]:
    """Computed values of one node as the property panel shows them (+ warnings)."""
    out: Dict[str, Any] = {"flow_nl_min": n.result_flow_nl_s * 60, "dp": n.result_dp, "dp_cum": n.result_dp_cum,
                           "p_inlet": n.result_p_inlet, "dn_rec": n.result_dn_rec, "v": n.result_v, "v_out": n.result_v_out}
    if n.kind == NODE_SEGMENT:
        d_use = n.seg_diam if n.seg_diam > 0 else n.result_dn_rec
        out["l_eq"] = n.seg_length + _fitting_equiv_length(d_use, n.seg_bends_90, n.seg_bends_45)
        out["v_warn"] = n.result_v > 0 and not (V_MIN <= n.result_v <= V_MAX)
        out["dp_warn"] = n.result_dp_cum > DP_WARN
    elif n.kind == NODE_REDUCER:
        out["v_warn"] = n.result_v_out > 0 and not (V_MIN <= n.result_v_out <= V_MAX)
        out["dp_warn"] = n.result_dp_cum > DP_WARN
    elif n.kind == NODE_JET:
        out["sufficient"] = n.result_p_inlet >= n.nozzle_pressure - 0.001
        out["dp_warn"] = n.result_dp_cum > DP_INFO
    out["label"] = n.label()
    return out


def results_rows(graph: NetworkGraph) -> Dict[str, Any]:
    """The "Segment overview" table + its summary line."""
    segs = [n for n in graph.nodes.values() if n.kind in (NODE_SEGMENT, NODE_REDUCER)]
    jets = [n for n in graph.nodes.values() if n.kind == NODE_JET]
    rows = []
    for n in segs:
        is_red = n.kind == NODE_REDUCER
        vel_ok = n.result_v == 0 or (V_MIN <= n.result_v <= V_MAX)
        dp_ok = n.result_dp_cum <= DP_WARN
        rows.append({"id": n.id, "label": n.label().replace("\n", " "), "kind": n.kind,
                     "length": None if is_red else n.seg_length,
                     "pressure": n.red_pressure if is_red else n.seg_pressure,
                     "flow_nl_min": n.result_flow_nl_s * 60,
                     "rec": (f"ø{int(n.red_d_out)}mm out" if is_red else (f"ø{n.result_dn_rec}mm" if n.result_dn_rec else "—")),
                     "man": (f"ø{int(n.red_d_in)}mm in" if is_red else (f"ø{int(n.seg_diam)}mm" if n.seg_diam > 0 else "auto")),
                     "v": n.result_v, "dp": n.result_dp, "dp_cum": n.result_dp_cum,
                     "status": "ok" if vel_ok and dp_ok else ("velocity" if not vel_ok else "dp")})
    return {"rows": rows, "total_flow_nl_min": sum(n.result_flow_nl_s for n in jets) * 60,
            "total_dp": sum(n.result_dp for n in segs), "worst_dp": max((n.result_dp_cum for n in jets), default=0.0),
            "n_jets": len(jets), "n_segs": len(segs)}


def cost_compare(orig: NetworkGraph, opt: NetworkGraph, params: Dict[str, float]) -> Dict[str, Any]:
    """Cost strip of the optimisation: current vs optimised annual cost and CHF / Nm³."""
    def view(g):
        jets = [n for n in g.nodes.values() if n.kind == NODE_JET]
        return opcost_view(sum(n.result_flow_nl_s for n in jets), required_pressure(g), params)
    a, b = view(orig), view(opt)
    return {"current": a, "optimized": b,
            "savings": (a["cost_chf"] - b["cost_chf"]) if a and b else None}


# ---------------------------------------------------------------------------
# PDF export
# ---------------------------------------------------------------------------

def generate_pdf(path: str, graph: NetworkGraph,
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

def generate_excel(path: str, graph: NetworkGraph, title: str):
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
