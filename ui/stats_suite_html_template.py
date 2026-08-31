"""stats_suite_html_template.py - HTML/JS for the Statistics Suite dashboard
(ui/screen_stats_suite.py). Same delivery mechanism as Smart Chart
(QWebEngineView + QWebChannel + Plotly loaded from CDN, see
ui/report_html_template.py), but a new, much smaller template: aggregate
count charts (bar/stacked-bar/KPI) instead of per-trial X/Y scatter plots, so
none of Smart Chart's drag-gridline/3D/image-block machinery applies here.

Cards live on a GridStack.js dashboard grid (CDN-loaded like Plotly) - drag by
the card header to place a card anywhere, including a different row (other
cards reflow around it); drag its corner to resize. GridStack owns both
concerns in one system (chosen over a plain flex/SortableJS combo, which can
only reorder a linear sequence and can't pin a card to a specific row/column
independent of that sequence). Position/size (grid x/y/w/h, 12-column grid)
are part of the per-user autosave, same as the blocks themselves.

Placeholders (replaced once in ui/screen_stats_suite.py, same `.replace()`
style as report_html_template.py): {accent_color}, {accent_tint},
{accent_gridline}, {entity_labels_json}, {group_by_labels_json},
{group_by_entity_restrictions_json}, {time_granularity_labels_json}.
"""

_STATS_HTML_TEMPLATE = r"""
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<link href="https://cdn.jsdelivr.net/npm/gridstack@10.1.2/dist/gridstack.min.css" rel="stylesheet"/>
<script src="https://cdn.jsdelivr.net/npm/gridstack@10.1.2/dist/gridstack-all.js"></script>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; font-family: "Segoe UI", Arial, sans-serif; background: #F4F6F5; color: #2b2b2b; }

  #filterbar {
    display: flex; flex-wrap: wrap; align-items: flex-end; gap: 16px;
    padding: 14px 20px; background: white; border-bottom: 1px solid {accent_gridline};
  }
  .filter-group { display: flex; flex-direction: column; gap: 4px; }
  .filter-group-label {
    display: flex; align-items: center; gap: 6px; font-size: 11px; color: #666;
    font-weight: 600; text-transform: uppercase;
  }
  .filter-clear {
    border: none; background: transparent; color: #aaa; font-size: 12px; cursor: pointer;
    line-height: 1; padding: 0 2px; border-radius: 3px; text-transform: none; font-weight: 400;
  }
  .filter-clear:hover { background: rgba(0,0,0,0.08); color: #c0392b; }
  .filter-group select { min-width: 150px; }
  select, input[type=date] {
    border: 1px solid {accent_gridline}; border-radius: 4px; padding: 4px 6px; font-size: 12px;
    background: white; color: #2b2b2b;
  }

  #toolbar {
    display: flex; align-items: center; gap: 12px; padding: 10px 20px;
  }
  .btn-primary, .btn-secondary {
    border: none; border-radius: 4px; padding: 7px 14px; font-size: 12px; font-weight: 600;
    cursor: pointer;
  }
  .btn-primary { background: {accent_color}; color: white; }
  .btn-primary:hover { filter: brightness(0.93); }
  .btn-secondary { background: white; border: 1px solid {accent_gridline}; color: #444; }
  .btn-secondary:hover { background: {accent_tint}; }
  #save_status { font-size: 11px; color: #8a938c; }

  #add_panel {
    display: flex; align-items: flex-end; gap: 12px; padding: 12px 20px; margin: 0 20px 12px 20px;
    background: white; border: 1px solid {accent_gridline}; border-radius: 6px;
  }
  .hidden { display: none; }

  #grid { margin: 4px 20px 24px 20px; }
  .grid-stack-item-content { overflow: hidden; }
  .card {
    background: white; border: 1px solid {accent_gridline}; border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06); overflow: hidden; display: flex; flex-direction: column;
    height: 100%;
  }
  .card-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 12px; background: {accent_tint}; border-bottom: 1px solid {accent_gridline};
    cursor: move; user-select: none; flex: none;
  }
  .card-title { font-size: 13px; font-weight: 600; color: #2b2b2b; }
  .card-remove {
    border: none; background: transparent; color: #888; font-size: 15px; cursor: pointer;
    line-height: 1; padding: 2px 6px; border-radius: 4px;
  }
  .card-remove:hover { background: rgba(0,0,0,0.08); color: #c0392b; }
  .card-body { flex: 1 1 auto; min-height: 0; position: relative; overflow: hidden; }
  .chart-loading, .chart-error, .chart-empty {
    position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
    font-size: 12px; text-align: center; padding: 20px;
  }
  .chart-loading { color: #999; }
  .chart-error { color: #c0392b; }
  .chart-empty { color: #999; }
  .kpi-value { font-size: 48px; font-weight: 700; color: {accent_color}; }
  .kpi-wrap { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; }
  .kpi-label { font-size: 12px; color: #888; margin-top: 6px; }

  #empty_state { padding: 60px 20px; text-align: center; color: #999; font-size: 13px; }
</style>

<div id="filterbar">
  <div class="filter-group">
    <div class="filter-group-label">Machine <button class="filter-clear" data-clear="machines" title="Clear this filter">✕</button></div>
    <select id="f_machines" multiple size="4"></select>
  </div>
  <div class="filter-group">
    <div class="filter-group-label">Product Group <button class="filter-clear" data-clear="productgroups" title="Clear this filter">✕</button></div>
    <select id="f_productgroups" multiple size="4"></select>
  </div>
  <div class="filter-group">
    <div class="filter-group-label">Order Type <button class="filter-clear" data-clear="ordertypes" title="Clear this filter">✕</button></div>
    <select id="f_ordertypes" multiple size="4"></select>
  </div>
  <div class="filter-group">
    <div class="filter-group-label" title="Only affects Trials cards - Experiments/Trial Series cards ignore this filter, same as the Lab Machine group-by option">Lab Machine <button class="filter-clear" data-clear="labmachines" title="Clear this filter">✕</button></div>
    <select id="f_labmachines" multiple size="4"></select>
  </div>
  <div class="filter-group">
    <div class="filter-group-label">Date range <button class="filter-clear" data-clear="daterange" title="Clear this filter">✕</button></div>
    <div style="display:flex; gap:6px;">
      <input type="date" id="f_datefrom">
      <input type="date" id="f_dateto">
    </div>
  </div>
  <button class="btn-secondary" id="btn_clear_filters">Clear all filters</button>
</div>

<div id="toolbar">
  <button class="btn-primary" id="btn_add_chart">+ Add chart</button>
  <span id="save_status"></span>
</div>

<div id="add_panel" class="hidden">
  <div class="filter-group">
    <label>Entity</label>
    <select id="a_entity"></select>
  </div>
  <div class="filter-group">
    <label>Group by</label>
    <select id="a_groupby"></select>
  </div>
  <div class="filter-group">
    <label>Time granularity</label>
    <select id="a_granularity"></select>
  </div>
  <button class="btn-primary" id="btn_confirm_add">Add</button>
  <button class="btn-secondary" id="btn_cancel_add">Cancel</button>
</div>

<div id="grid"></div>
<div id="empty_state" class="hidden">No charts yet — click "+ Add chart" above to build your dashboard.</div>

<script>
const ENTITY_LABELS = {entity_labels_json};
const GROUP_BY_LABELS = {group_by_labels_json};
const GROUP_BY_ENTITY_RESTRICTIONS = {group_by_entity_restrictions_json};
const TIME_GRANULARITY_LABELS = {time_granularity_labels_json};
const ACCENT = "{accent_color}";
const PALETTE = [ACCENT, "#E0A030", "#4C78A8", "#B279A2", "#F58518", "#54A24B", "#E45756", "#72B7B2", "#EECA3B", "#9D755D"];

let bridge = null;
let filterOptions = { machines: [], productGroups: [], orderTypes: [], labMachines: [] };
let filters = { machines: [], productGroups: [], orderTypes: [], labMachines: [], dateFrom: "", dateTo: "" };
let blocks = []; // [{clientId, entity, groupBy, timeGranularity, gridX, gridY, gridW, gridH}]
let nextClientId = -1;
let optionsLoaded = false;
let dashboardLoaded = false;

const DEFAULT_W = 4, DEFAULT_H = 5, MIN_W = 2, MIN_H = 3;
const grid = GridStack.init({
  column: 12, cellHeight: 70, margin: 8, handle: ".card-header", float: false,
}, "#grid");
grid.on("change", function (event, items) {
  (items || []).forEach(function (item) {
    const clientId = parseInt(item.el.dataset.clientId, 10);
    const b = blocks.find(function (x) { return x.clientId === clientId; });
    if (!b) return;
    b.gridX = item.x; b.gridY = item.y; b.gridW = item.w; b.gridH = item.h;
    const chartEl = document.getElementById("chart_" + clientId);
    if (chartEl && window.Plotly) {
      try { Plotly.Plots.resize(chartEl); } catch (e) { /* not a plotly div (KPI/empty/error) */ }
    }
  });
  saveDashboardDebounced();
});

function debounce(fn, ms) {
  let t;
  return function () {
    const args = arguments;
    clearTimeout(t);
    t = setTimeout(function () { fn.apply(null, args); }, ms);
  };
}

new QWebChannel(qt.webChannelTransport, function (channel) {
  bridge = channel.objects.bridge;
  bridge.loadFilterOptions();
  bridge.loadDashboard();
});

// ---- bootstrap ----------------------------------------------------------
// Data pushed from Python (_StatsSuiteBridge._run_js) arrives as literal JS
// values embedded directly in the call (json.dumps(...) produces valid JS
// literal syntax) - no JSON.parse needed here, same convention as
// receiveQueryResult() in report_html_template.py. JSON.parse/stringify are
// only used for the JS->Python direction (bridge.runChartQuery/saveDashboard
// take a real `str` Slot argument).
function receiveFilterOptions(options) {
  filterOptions = options;
  optionsLoaded = true;
  tryInitialRender();
}

function receiveDashboard(loadedBlocks, loadedFilters) {
  blocks = (loadedBlocks || []).map(function (b) {
    b.clientId = nextClientId--;
    return b;
  });
  if (loadedFilters) filters = loadedFilters;
  dashboardLoaded = true;
  tryInitialRender();
}

function tryInitialRender() {
  if (!optionsLoaded || !dashboardLoaded) return;
  populateAddPanelSelects();
  renderFilterBar();
  rebuildGrid();
  refreshAllCharts();
}

// ---- filter bar -----------------------------------------------------------
function fillMultiSelect(sel, items, selectedIds) {
  sel.innerHTML = "";
  items.forEach(function (it) {
    const opt = document.createElement("option");
    opt.value = it.id;
    opt.textContent = it.name;
    if (selectedIds && selectedIds.indexOf(it.id) !== -1) opt.selected = true;
    sel.appendChild(opt);
  });
}

function renderFilterBar() {
  fillMultiSelect(document.getElementById("f_machines"), filterOptions.machines, filters.machines);
  fillMultiSelect(document.getElementById("f_productgroups"), filterOptions.productGroups, filters.productGroups);
  fillMultiSelect(document.getElementById("f_ordertypes"), filterOptions.orderTypes, filters.orderTypes);
  fillMultiSelect(document.getElementById("f_labmachines"), filterOptions.labMachines, filters.labMachines);
  document.getElementById("f_datefrom").value = filters.dateFrom || "";
  document.getElementById("f_dateto").value = filters.dateTo || "";
}

function selectedIntValues(sel) {
  return Array.from(sel.selectedOptions).map(function (o) { return parseInt(o.value, 10); });
}

// Lab Machine options are plain strings (see fetch_filter_options() - no
// numeric id, the display name doubles as its own id), unlike the other
// filters' DB-table ids - selectedIntValues() would parseInt() them to NaN.
function selectedStringValues(sel) {
  return Array.from(sel.selectedOptions).map(function (o) { return o.value; });
}

const onFilterChanged = debounce(function () {
  filters = {
    machines: selectedIntValues(document.getElementById("f_machines")),
    productGroups: selectedIntValues(document.getElementById("f_productgroups")),
    orderTypes: selectedIntValues(document.getElementById("f_ordertypes")),
    labMachines: selectedStringValues(document.getElementById("f_labmachines")),
    dateFrom: document.getElementById("f_datefrom").value || "",
    dateTo: document.getElementById("f_dateto").value || "",
  };
  refreshAllCharts();
  saveDashboardDebounced();
}, 350);

["f_machines", "f_productgroups", "f_ordertypes", "f_labmachines"].forEach(function (id) {
  document.getElementById(id).addEventListener("change", onFilterChanged);
});
["f_datefrom", "f_dateto"].forEach(function (id) {
  document.getElementById(id).addEventListener("change", onFilterChanged);
});
document.getElementById("btn_clear_filters").addEventListener("click", function () {
  document.getElementById("f_machines").selectedIndex = -1;
  document.getElementById("f_productgroups").selectedIndex = -1;
  document.getElementById("f_ordertypes").selectedIndex = -1;
  document.getElementById("f_labmachines").selectedIndex = -1;
  document.getElementById("f_datefrom").value = "";
  document.getElementById("f_dateto").value = "";
  onFilterChanged();
});

// Per-filter reset (the "✕" next to each filter group's label) - clears
// just that one filter, leaving the others (e.g. a still-useful Machine
// selection) untouched instead of forcing "Clear all filters".
function clearFilterGroup(name) {
  if (name === "machines") {
    document.getElementById("f_machines").selectedIndex = -1;
  } else if (name === "productgroups") {
    document.getElementById("f_productgroups").selectedIndex = -1;
  } else if (name === "ordertypes") {
    document.getElementById("f_ordertypes").selectedIndex = -1;
  } else if (name === "labmachines") {
    document.getElementById("f_labmachines").selectedIndex = -1;
  } else if (name === "daterange") {
    document.getElementById("f_datefrom").value = "";
    document.getElementById("f_dateto").value = "";
  }
  onFilterChanged();
}

document.querySelectorAll(".filter-clear").forEach(function (btn) {
  btn.addEventListener("click", function () { clearFilterGroup(btn.dataset.clear); });
});

// ---- add-chart panel --------------------------------------------------
function fillLabelSelect(sel, labelsMap, includeNone, noneLabel) {
  sel.innerHTML = "";
  if (includeNone) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = noneLabel;
    sel.appendChild(opt);
  }
  Object.keys(labelsMap).forEach(function (key) {
    const opt = document.createElement("option");
    opt.value = key;
    opt.textContent = labelsMap[key];
    sel.appendChild(opt);
  });
}

// Some group-by dimensions only make sense for one entity (e.g. "Lab
// Machine" - a trial can be measured on several lab machines at once, which
// would multiply an Experiment's/TrialSeries' own row count in a way none
// of the other dimensions do, see GROUP_BY_ENTITY_RESTRICTIONS). The
// add-panel's Group-by list is filtered to whatever the currently selected
// Entity actually supports, refreshed on every Entity change.
function applicableGroupByLabels(entity) {
  const result = {};
  Object.keys(GROUP_BY_LABELS).forEach(function (key) {
    const restriction = GROUP_BY_ENTITY_RESTRICTIONS[key];
    if (!restriction || restriction.indexOf(entity) !== -1) {
      result[key] = GROUP_BY_LABELS[key];
    }
  });
  return result;
}

function refreshGroupBySelect() {
  const entity = document.getElementById("a_entity").value;
  fillLabelSelect(document.getElementById("a_groupby"), applicableGroupByLabels(entity), true, "(none)");
}

function populateAddPanelSelects() {
  fillLabelSelect(document.getElementById("a_entity"), ENTITY_LABELS, false, "");
  refreshGroupBySelect();
  fillLabelSelect(document.getElementById("a_granularity"), TIME_GRANULARITY_LABELS, true, "(none)");
}

document.getElementById("a_entity").addEventListener("change", refreshGroupBySelect);

document.getElementById("btn_add_chart").addEventListener("click", function () {
  document.getElementById("add_panel").classList.remove("hidden");
});
document.getElementById("btn_cancel_add").addEventListener("click", function () {
  document.getElementById("add_panel").classList.add("hidden");
});
document.getElementById("btn_confirm_add").addEventListener("click", function () {
  const entity = document.getElementById("a_entity").value;
  const groupBy = document.getElementById("a_groupby").value || null;
  const timeGranularity = document.getElementById("a_granularity").value || null;
  addBlock(entity, groupBy, timeGranularity);
  document.getElementById("add_panel").classList.add("hidden");
});

// ---- blocks / grid ------------------------------------------------------
function blockTitle(b) {
  let t = ENTITY_LABELS[b.entity] || b.entity;
  if (b.groupBy) t += " by " + GROUP_BY_LABELS[b.groupBy];
  if (b.timeGranularity) t += " — per " + TIME_GRANULARITY_LABELS[b.timeGranularity].toLowerCase();
  return t;
}

function addBlock(entity, groupBy, timeGranularity) {
  const b = {
    clientId: nextClientId--, entity: entity, groupBy: groupBy, timeGranularity: timeGranularity,
    gridW: DEFAULT_W, gridH: DEFAULT_H,
  };
  blocks.push(b);
  grid.addWidget(createCardElement(b), { w: b.gridW, h: b.gridH, autoPosition: true });
  document.getElementById("empty_state").classList.add("hidden");
  runCardQuery(b);
  saveDashboardDebounced();
}

function removeBlock(clientId) {
  blocks = blocks.filter(function (b) { return b.clientId !== clientId; });
  const el = document.getElementById("card_" + clientId);
  if (el) grid.removeWidget(el);
  document.getElementById("empty_state").classList.toggle("hidden", blocks.length > 0);
  saveDashboardDebounced();
}

// Existing cards (already-rendered Plotly charts) must NOT be recreated when
// another chart is added/removed - only rebuildGrid() (full bootstrap on
// page load) tears everything down and rebuilds from scratch.
// addBlock()/removeBlock() add/remove exactly one widget so unrelated cards
// keep their live Plotly instance instead of getting stuck on "Loading..."
// forever (they'd never get re-queried otherwise).
function createCardElement(b) {
  const item = document.createElement("div");
  item.className = "grid-stack-item";
  item.id = "card_" + b.clientId;
  item.dataset.clientId = b.clientId;
  item.setAttribute("gs-w", b.gridW || DEFAULT_W);
  item.setAttribute("gs-h", b.gridH || DEFAULT_H);
  item.setAttribute("gs-min-w", MIN_W);
  item.setAttribute("gs-min-h", MIN_H);
  if (b.gridX != null) item.setAttribute("gs-x", b.gridX);
  if (b.gridY != null) item.setAttribute("gs-y", b.gridY);
  item.innerHTML =
    '<div class="grid-stack-item-content"><div class="card">' +
    '<div class="card-header">' +
    '<span class="card-title">' + blockTitle(b) + "</span>" +
    '<button class="card-remove" title="Remove chart" onclick="removeBlock(' + b.clientId + ')">✕</button>' +
    "</div>" +
    '<div class="card-body" id="chart_' + b.clientId + '"><div class="chart-loading">Loading…</div></div>' +
    "</div></div>";
  return item;
}

function rebuildGrid() {
  grid.removeAll();
  document.getElementById("empty_state").classList.toggle("hidden", blocks.length > 0);
  blocks.forEach(function (b) {
    const opts = { w: b.gridW || DEFAULT_W, h: b.gridH || DEFAULT_H };
    if (b.gridX != null && b.gridY != null) {
      opts.x = b.gridX; opts.y = b.gridY; opts.autoPosition = false;
    } else {
      opts.autoPosition = true;
    }
    grid.addWidget(createCardElement(b), opts);
  });
}

// ---- data fetch / render --------------------------------------------------
function runCardQuery(b) {
  const cfg = {
    clientId: b.clientId,
    entity: b.entity,
    groupBy: b.groupBy,
    timeGranularity: b.timeGranularity,
    filters: filters,
  };
  bridge.runChartQuery(JSON.stringify(cfg));
}

function refreshAllCharts() {
  blocks.forEach(runCardQuery);
}

function receiveChartData(clientId, rows, errorMsg) {
  const el = document.getElementById("chart_" + clientId);
  if (!el) return;
  if (errorMsg) {
    el.innerHTML = '<div class="chart-error">' + errorMsg + "</div>";
    return;
  }
  const b = blocks.find(function (x) { return x.clientId === clientId; });
  if (!b) return;
  renderChart(el, b, rows);
}

function baseLayout(xTitle, yTitle) {
  return {
    margin: { l: 50, r: 16, t: 10, b: 60 },
    xaxis: { title: xTitle, type: "category" },
    yaxis: { title: yTitle, rangemode: "tozero" },
    font: { size: 11 },
    showlegend: false,
  };
}

function renderChart(el, b, rows) {
  if (!rows || rows.length === 0) {
    el.innerHTML = '<div class="chart-empty">No matching data for the current filters.</div>';
    return;
  }
  el.innerHTML = "";

  if (!b.groupBy && !b.timeGranularity) {
    const cnt = rows[0].Cnt || 0;
    el.innerHTML =
      '<div class="kpi-wrap"><div class="kpi-value">' + cnt + '</div>' +
      '<div class="kpi-label">' + ENTITY_LABELS[b.entity] + " (current filters)</div></div>";
    return;
  }

  if (!b.timeGranularity) {
    // pure category breakdown, already sorted by count desc from the backend
    const x = rows.map(function (r) { return r.Category; });
    const y = rows.map(function (r) { return r.Cnt; });
    Plotly.newPlot(el, [{ x: x, y: y, type: "bar", marker: { color: ACCENT } }],
      baseLayout(GROUP_BY_LABELS[b.groupBy], "Count"), { responsive: true, displaylogo: false });
    return;
  }

  if (!b.groupBy) {
    const x = rows.map(function (r) { return r.Period; });
    const y = rows.map(function (r) { return r.Cnt; });
    Plotly.newPlot(el, [{ x: x, y: y, type: "bar", marker: { color: ACCENT } }],
      baseLayout(TIME_GRANULARITY_LABELS[b.timeGranularity], "Count"), { responsive: true, displaylogo: false });
    return;
  }

  // both set: stacked bar, one trace per category, x = sorted unique periods
  const periods = Array.from(new Set(rows.map(function (r) { return r.Period; }))).sort();
  const categories = Array.from(new Set(rows.map(function (r) { return r.Category; })));
  const traces = categories.map(function (cat, i) {
    const byPeriod = {};
    rows.filter(function (r) { return r.Category === cat; }).forEach(function (r) { byPeriod[r.Period] = r.Cnt; });
    return {
      x: periods,
      y: periods.map(function (p) { return byPeriod[p] || 0; }),
      type: "bar",
      name: cat,
      marker: { color: PALETTE[i % PALETTE.length] },
    };
  });
  const layout = baseLayout(TIME_GRANULARITY_LABELS[b.timeGranularity], "Count");
  layout.barmode = "stack";
  layout.showlegend = true;
  layout.legend = { orientation: "h", y: -0.25 };
  Plotly.newPlot(el, traces, layout, { responsive: true, displaylogo: false });
}

// ---- persistence ------------------------------------------------------
const saveDashboardDebounced = debounce(function () {
  const payload = {
    blocks: blocks.map(function (b) {
      return {
        entity: b.entity, groupBy: b.groupBy, timeGranularity: b.timeGranularity,
        gridX: b.gridX != null ? b.gridX : null, gridY: b.gridY != null ? b.gridY : null,
        gridW: b.gridW || null, gridH: b.gridH || null,
      };
    }),
    filters: filters,
  };
  bridge.saveDashboard(JSON.stringify(payload));
}, 500);

function receiveSaveResult(success, message) {
  const el = document.getElementById("save_status");
  el.textContent = success ? "Saved" : ("Save failed: " + message);
  el.style.color = success ? "#8a938c" : "#c0392b";
  setTimeout(function () { if (el.textContent === "Saved") el.textContent = ""; }, 2000);
}
</script>
"""
