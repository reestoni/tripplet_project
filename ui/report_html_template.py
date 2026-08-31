"""report_html_template.py - HTML/JS-Template fuer den ReportScreen "Smart Chart" Builder.

Ausgelagert aus ui/screen_report.py (reiner Code-Move, keine
Verhaltensaenderung). Reiner String-Konstante (kein Python-Code) - das
Plotly-basierte Chart-UI, das per QWebEngineView/QWebChannel im ReportScreen
eingebettet wird. Platzhalter wie {data_json} werden von _ReportBridge in
screen_report.py per .replace() befuellt (kein Python-.format()/f-string,
daher keine Escaping-Fallstricke bei den vielen literalen { } in CSS/JS).
"""

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TrippleT Smart Chart</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:'Segoe UI',Arial,sans-serif; background:#f5f6fa; overflow:hidden; height:100vh; display:flex; flex-direction:column; }

  /* ── Global Toolbar ── */
  #global-toolbar {
    display:flex; align-items:center; gap:12px; flex-wrap:wrap; flex-shrink:0;
    padding:8px 12px; background:#fff; border-bottom:1px solid #e0e0e0;
    box-shadow:0 1px 3px rgba(0,0,0,0.06);
  }
  #global-toolbar label { font-size:12px; color:#565656; white-space:nowrap; }
  #global-toolbar input[type=number] {
    width:60px; font-size:12px; padding:3px 6px;
    border:1px solid #c8c8c8; border-radius:3px; background:#fafafa; outline:none;
  }
  #global-toolbar input:focus { border-color:#39A650; }
  .tb-sep { width:1px; height:20px; background:#e0e0e0; flex-shrink:0; }
  #series-list { display:flex; gap:6px; align-items:center; flex-wrap:wrap; }
  .series-pill { display:flex; align-items:center; gap:5px; font-size:11px; padding:3px 8px; border-radius:12px; border:1px solid #c8c8c8; background:#fafafa; color:#333; white-space:nowrap; }
  .series-pill .pill-color { width:12px; height:12px; border-radius:50%; flex-shrink:0; cursor:pointer; border:1px solid rgba(0,0,0,0.15); }
  .series-pill .pill-remove { cursor:pointer; color:#aaa; font-size:13px; line-height:1; margin-left:2px; }
  .series-pill .pill-remove:hover { color:#c0392b; }

  .btn-toolbar {
    font-size:11px; font-weight:600; padding:3px 10px;
    border:1px solid #c8c8c8; border-radius:3px; background:#fafafa; cursor:pointer; color:#565656;
    outline:none; transition:all 0.15s; font-family:inherit; white-space:nowrap;
  }
  .btn-toolbar:hover { border-color:#39A650; color:#1D6B32; background:#f0faf0; }
  .btn-toolbar.active { border-color:#39A650; background:#39A650; color:#fff; }

  /* ── Main layout ── */
  #main-layout { display:flex; flex:1; min-height:0; }

  /* ── SQL Builder Panel ── */
  #builder-panel {
    width:320px; min-width:280px; max-width:380px;
    background:#fff; border-right:1px solid #e0e0e0;
    display:flex; flex-direction:column; flex-shrink:0;
    overflow:hidden;
    /* Smooth slide + fade */
    transition:
      width      0.35s cubic-bezier(0.4, 0, 0.2, 1),
      opacity    0.3s  cubic-bezier(0.4, 0, 0.2, 1),
      min-width  0.35s cubic-bezier(0.4, 0, 0.2, 1),
      border-width 0.35s ease;
    opacity:1;
  }
  #builder-panel.hidden {
    width:0 !important;
    min-width:0 !important;
    opacity:0;
    border-right-width:0;
    pointer-events:none;
  }

  /* ── Builder Toggle Arrow ── */
  #builder-arrow {
    display:none; /* nur in visual mode */
    position:absolute; left:0; top:50%; transform:translateY(-50%);
    z-index:20; width:20px; height:52px;
    background:linear-gradient(160deg, #1D3557 60%, #2c5f8a);
    border-radius:0 8px 8px 0;
    cursor:pointer; align-items:center; justify-content:center;
    box-shadow:3px 0 10px rgba(29,53,87,0.25);
    transition:
      background   0.2s ease,
      box-shadow   0.2s ease,
      transform    0.2s ease;
    flex-shrink:0;
  }
  #builder-arrow:hover {
    background:linear-gradient(160deg, #2c4f7a 60%, #3a7ab8);
    box-shadow:4px 0 16px rgba(29,53,87,0.38);
    transform:translateY(-50%) scaleX(1.15);
  }
  #builder-arrow:active { transform:translateY(-50%) scaleX(0.95); }
  #builder-arrow svg {
    transition:transform 0.3s cubic-bezier(0.4,0,0.2,1);
  }
  #builder-arrow.open svg { transform:scaleX(-1); }
  #charts-wrapper { position:relative; flex:1; overflow-y:auto; padding:12px; }
  .builder-header {
    padding:10px 14px; background:#2c3e50; color:#fff;
    font-size:12px; font-weight:700; letter-spacing:1px; text-transform:uppercase;
    display:flex; align-items:center; justify-content:space-between; flex-shrink:0;
  }
  .builder-body { flex:1; overflow-y:auto; padding:12px; display:flex; flex-direction:column; gap:10px; }
  .builder-section { display:flex; flex-direction:column; gap:6px; }
  .builder-section-title { font-size:10px; font-weight:700; color:#7a9ab5; text-transform:uppercase; letter-spacing:1px; }

  .builder-select, .builder-input {
    width:100%; font-size:11px; padding:5px 8px;
    border:1px solid #d0d0d0; border-radius:4px; background:#fafafa;
    color:#1a1a2e; outline:none; font-family:inherit;
  }
  .builder-select:focus, .builder-input:focus { border-color:#39A650; }

  /* Filter rows */
  #filter-rows { display:flex; flex-direction:column; gap:6px; }
  .filter-row {
    display:grid; grid-template-columns:1fr 80px 1fr 24px;
    gap:4px; align-items:start;
  }
  .filter-row select, .filter-row input {
    font-size:11px; padding:4px 6px; border:1px solid #d0d0d0;
    border-radius:4px; background:#fafafa; outline:none; font-family:inherit; width:100%;
  }
  .filter-row select:focus, .filter-row input:focus { border-color:#39A650; }
  .filter-row-remove {
    width:22px; height:22px; border:none; background:none;
    color:#ccc; font-size:16px; cursor:pointer; line-height:1;
    display:flex; align-items:center; justify-content:center; border-radius:3px;
    padding:0;
  }
  .filter-row-remove:hover { color:#c0392b; background:#fef0f0; }

  .btn-add-filter {
    font-size:11px; padding:4px 10px; border:1px dashed #c8c8c8;
    border-radius:4px; background:none; cursor:pointer; color:#888;
    text-align:left; font-family:inherit; transition:all 0.15s;
  }
  .btn-add-filter:hover { border-color:#39A650; color:#1D6B32; }

  .btn-run {
    font-size:12px; font-weight:700; padding:7px 14px;
    border:none; border-radius:4px; background:#39A650; color:#fff;
    cursor:pointer; font-family:inherit; transition:background 0.15s;
    display:flex; align-items:center; justify-content:center; gap:6px;
  }
  .btn-run:hover { background:#2d8a40; }
  .btn-run:disabled { background:#aaa; cursor:default; }

  .builder-divider { height:1px; background:#f0f0f0; margin:2px 0; }

  /* ── Builder Tabs ── */
  .builder-tabs {
    display:flex; gap:0; border-bottom:2px solid #e0e0e0; margin-bottom:8px; flex-shrink:0;
  }
  .builder-tab {
    font-size:11px; font-weight:600; padding:5px 14px; cursor:pointer;
    border:none; background:none; color:#888; border-bottom:2px solid transparent;
    margin-bottom:-2px; transition:all 0.15s; font-family:inherit; outline:none;
  }
  .builder-tab.active { color:#1D3557; border-bottom-color:#1D3557; }
  .builder-tab:hover:not(.active) { color:#565656; }
  .builder-tab-panel { display:none; flex-direction:column; gap:10px; flex:1; }
  .builder-tab-panel.active { display:flex; }

  /* ── Advanced Filter Rows ── */
  .adv-filter-row {
    display:grid; grid-template-columns:auto 1fr 70px 1fr 22px;
    gap:4px; align-items:start; font-size:11px;
  }
  .adv-filter-row .adv-connector {
    font-size:9px; font-weight:700; color:#7a9ab5; padding:5px 2px 0;
    text-transform:uppercase; white-space:nowrap;
  }
  .adv-filter-row select, .adv-filter-row input {
    font-size:11px; padding:4px 6px; border:1px solid #d0d0d0;
    border-radius:4px; background:#fafafa; outline:none; font-family:inherit; width:100%;
  }
  .adv-filter-row select:focus, .adv-filter-row input:focus { border-color:#1D3557; }
  .adv-field-select { font-size:11px; padding:4px 6px; border:1px solid #d0d0d0; border-radius:4px; background:#fafafa; outline:none; font-family:inherit; width:100%; }
  .adv-preview {
    font-size:9px; color:#7a9ab5; font-family:monospace;
    background:#f0f4ff; border:1px solid #d8e4f8; border-radius:3px;
    padding:4px 8px; margin-top:2px; word-break:break-all; white-space:pre-wrap;
  }

  /* Result info */
  #result-info {
    font-size:10px; color:#888; padding:4px 0;
    border-top:1px solid #f0f0f0; margin-top:4px; flex-shrink:0; padding:6px 12px;
  }

  /* ── Charts area ── */
  #charts-area { flex:1; overflow-y:auto; padding:12px; }
  #charts-wrapper { flex:1; overflow-y:auto; padding:12px; display:flex; flex-direction:column; }
  #grid { display:grid; gap:14px; }
  .chart-card {
    background:#fff; border:1px solid #e0e0e0; border-radius:6px;
    box-shadow:0 1px 4px rgba(0,0,0,0.07); display:flex; flex-direction:column; height:612px;
  }
  .chart-card.note-expanded { height:auto; min-height:612px; }
  .image-card {
    background:#fff; border:1px solid #e0e0e0; border-radius:6px;
    box-shadow:0 1px 4px rgba(0,0,0,0.07); display:flex; flex-direction:column; margin-bottom:12px;
  }
  .image-card .img-toolbar {
    display:flex; align-items:center; gap:6px; padding:6px 10px;
    border-bottom:1px solid #f0f0f0; background:#fafafa; border-radius:6px 6px 0 0; flex-shrink:0;
  }
  .image-card .img-title { font-size:11px; font-weight:600; color:#1D3557; flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .image-card .img-body { padding:10px; }
  .image-card .img-body img { width:100%; border-radius:4px; border:1px solid #e8e8e8; display:block; }
  .image-card.half-width { width:50%; }
  .chart-toolbar {
    display:flex; align-items:center; gap:10px;
    padding:7px 10px 5px 10px; border-bottom:1px solid #f0f0f0; flex-shrink:0; flex-wrap:wrap;
  }
  .chart-toolbar label { font-size:11px; color:#565656; white-space:nowrap; }
  .chart-toolbar select {
    font-size:11px; padding:2px 6px; border:1px solid #c8c8c8;
    border-radius:3px; background:#fafafa; color:#1a1a2e; cursor:pointer; outline:none;
  }
  .chart-toolbar select:focus { border-color:#39A650; }
  .btn-custom, .btn-3d {
    font-size:11px; padding:2px 8px; border:1px solid #c8c8c8;
    border-radius:3px; background:#fafafa; cursor:pointer; color:#565656;
    white-space:nowrap; outline:none; transition:all 0.15s;
  }
  .btn-custom:hover { border-color:#39A650; color:#1D6B32; background:#f0faf0; }
  .btn-3d { font-weight:600; }
  .btn-3d.active { border-color:#1D6B32; color:#fff; background:#39A650; }
  .btn-3d:hover:not(.active) { border-color:#39A650; color:#1D6B32; background:#f0faf0; }
  .z-controls { display:none; align-items:center; gap:6px; }
  .z-controls.visible { display:flex; }
  .chart-plot { flex:1; min-height:0; }
  .btn-copy { font-size:11px; padding:2px 8px; border:1px solid #c8c8c8; border-radius:3px; background:#fafafa; cursor:pointer; color:#565656; white-space:nowrap; outline:none; transition:all 0.15s; font-family:inherit; }
  .btn-copy:hover { border-color:#4A90D9; color:#2060a0; background:#f0f4ff; }
  .btn-copy.copied { border-color:#39A650; background:#39A650; color:#fff; }
  #no-data { display:none; text-align:center; color:#888; font-size:1.1rem; padding:60px; }

  /* ── Drill-Down Breadcrumb ── */
  #drilldown-bar {
    display:none; align-items:center; gap:6px; flex-wrap:wrap; flex-shrink:0;
    padding:5px 12px; background:#fff8ee; border-bottom:1px solid #f0d080;
    font-size:11px; color:#7a6000;
  }
  #drilldown-bar.visible { display:flex; }
  .drill-crumb {
    display:flex; align-items:center; gap:4px; cursor:pointer;
    padding:2px 8px; border-radius:10px; border:1px solid #e0c060;
    background:#fffbe8; color:#7a5500; white-space:nowrap; transition:all 0.15s;
  }
  .drill-crumb:hover { background:#ffefc0; border-color:#c8a000; }
  .drill-crumb.home { background:#fff3cd; font-weight:700; }
  .drill-crumb-sep { color:#c8a000; font-size:10px; }
  .drill-current { font-weight:700; color:#7a5500; padding:2px 4px; }
  .chart-plot.drillable { cursor:zoom-in; }

  /* ── Drag & Drop ── */
  .drag-handle {
    cursor:grab; color:#c0c8d8; font-size:14px; padding:0 5px 0 2px;
    user-select:none; flex-shrink:0; transition:color 0.15s;
    display:flex; align-items:center; line-height:1;
  }
  .drag-handle:hover { color:#1D3557; }
  .drag-handle:active { cursor:grabbing; }
  .chart-card.drag-over {
    outline:2px dashed #1D3557;
    background:linear-gradient(135deg,#eef4fb,#f5f8ff);
  }
  .chart-card.dragging {
    opacity:0.45; transform:scale(0.98);
    box-shadow:0 8px 32px rgba(29,53,87,0.18);
    transition:opacity 0.15s, transform 0.15s;
  }
  .chart-card { transition:transform 0.22s cubic-bezier(0.4,0,0.2,1), opacity 0.22s ease; }

  /* ── Drill-Down Animationen ── */
  @keyframes drillIn {
    from { opacity:0; transform:scale(0.96) translateY(6px); }
    to   { opacity:1; transform:scale(1)    translateY(0); }
  }
  @keyframes drillOut {
    from { opacity:1; transform:scale(1)    translateY(0); }
    to   { opacity:0; transform:scale(0.96) translateY(-6px); }
  }
  @keyframes drillBack {
    from { opacity:0; transform:scale(0.97) translateX(-12px); }
    to   { opacity:1; transform:scale(1)    translateX(0); }
  }
  @keyframes drillBackOut {
    from { opacity:1; transform:scale(1)    translateX(0); }
    to   { opacity:0; transform:scale(0.97) translateX(12px); }
  }
  @keyframes slideDownIn {
    from { opacity:0; transform:translateY(-100%); }
    to   { opacity:1; transform:translateY(0); }
  }
  .chart-card.drill-in  { animation: drillIn     0.22s cubic-bezier(0.22,1,0.36,1) both; }
  .chart-card.drill-out { animation: drillOut     0.18s ease-in both; pointer-events:none; }
  .chart-card.drill-back-in  { animation: drillBack    0.22s cubic-bezier(0.22,1,0.36,1) both; }
  .chart-card.drill-back-out { animation: drillBackOut 0.18s ease-in both; pointer-events:none; }
  #drilldown-bar.visible { animation: slideDownIn 0.2s ease both; }

  /* ── Chart Expand ── */
  .chart-card.expanded {
    position:fixed !important;
    top:0; left:0; right:0; bottom:0;
    width:100vw !important; height:100vh !important;
    z-index:9999; background:#fff;
    border-radius:0 !important; box-shadow:none !important;
    display:flex; flex-direction:column;
  }
  .chart-card.expanded .chart-plot { flex:1; height:auto !important; min-height:0 !important; }
  .btn-expand { font-size:13px; padding:2px 6px; border:none; background:none; cursor:pointer; color:#bbb; border-radius:3px; transition:color 0.15s; }
  .btn-expand:hover { color:#1D3557; }

  /* ── Chart Expand ── */
  .chart-card.expanded {
    position:fixed !important;
    top:0; left:0; right:0; bottom:0;
    width:100vw !important; height:100vh !important;
    z-index:9999; background:#fff;
    border-radius:0 !important; box-shadow:none !important;
    display:flex; flex-direction:column;
  }
  .chart-card.expanded .chart-plot { flex:1; height:auto !important; min-height:0 !important; }
  .btn-expand { font-size:13px; padding:2px 6px; border:none; background:none; cursor:pointer; color:#bbb; border-radius:3px; transition:color 0.15s; }
  .btn-expand:hover { color:#1D3557; }

  /* ── Mode Toggle ── */
  .builder-mode-toggle {
    display:flex; gap:0; background:#e8edf2; border-radius:6px;
    padding:3px; margin-bottom:8px; flex-shrink:0;
  }
  .builder-mode-btn {
    flex:1; padding:5px 8px; border:none; border-radius:4px;
    font-size:11px; font-weight:600; cursor:pointer; transition:all 0.15s;
    background:none; color:#7a9ab5; font-family:inherit;
  }
  .builder-mode-btn.active {
    background:#fff; color:#1D3557;
    box-shadow:0 1px 3px rgba(0,0,0,0.15);
  }

  /* ── Block Selector ── */


  /* ── Free Query Builder ── */
  .fqb-section { display:flex; flex-direction:column; gap:6px; }
  .fqb-section-title { font-size:10px; font-weight:700; color:#7a9ab5; text-transform:uppercase; letter-spacing:1px; }
  .fqb-table-pill {
    display:flex; align-items:center; gap:5px; padding:3px 8px;
    border:1px solid #d0d0d0; border-radius:12px; background:#f0f4ff;
    font-size:11px; color:#1D3557; cursor:default;
  }
  .fqb-table-pill .fqb-rm { cursor:pointer; color:#aaa; font-size:13px; margin-left:2px; }
  .fqb-table-pill .fqb-rm:hover { color:#c0392b; }
  .fqb-axis-row { display:grid; grid-template-columns:50px 1fr; gap:4px; align-items:center; font-size:11px; }
  .fqb-axis-row label { color:#565656; font-weight:600; }
  .fqb-select { font-size:11px; padding:4px 6px; border:1px solid #b0bec8; border-radius:4px; background:#f0f4f8; outline:none; font-family:inherit; width:100%; }
  .fqb-select:focus { border-color:#1D3557; }
  .fqb-preview { font-size:9px; color:#7a9ab5; font-family:monospace; background:#f0f4ff; border:1px solid #d8e4f8; border-radius:3px; padding:4px 8px; margin-top:4px; white-space:pre-wrap; word-break:break-all; }
  #fqb-join-pills { display:flex; flex-wrap:wrap; gap:4px; min-height:20px; }

  /* ── Query Templates ── */
  .qtpl-list { display:flex; flex-direction:column; gap:5px; max-height:300px; overflow-y:auto; padding:2px 0; }
  .qtpl-item {
    display:flex; align-items:center; gap:8px; padding:8px 11px;
    border:1px solid #e0e0e0; border-radius:5px; cursor:pointer;
    background:#fafafa; transition:all 0.15s;
  }
  .qtpl-item:hover { border-color:#1D3557; background:#eef2ff; }
  .qtpl-item.selected { border-color:#1D3557; background:#dce8f5; }
  .qtpl-badge {
    font-size:9px; font-weight:700; padding:2px 6px; border-radius:8px;
    white-space:nowrap; flex-shrink:0; text-transform:uppercase; letter-spacing:0.5px;
  }
  .qtpl-badge.lvl1 { background:#e8f4fd; color:#1D3557; border:1px solid #b8d8f0; }
  .qtpl-badge.lvl2 { background:#e8f5ee; color:#1D6B32; border:1px solid #b0ddb8; }
  .qtpl-badge.lvl3 { background:#fff3cd; color:#856404; border:1px solid #ffd666; }
  .qtpl-name { font-size:12px; font-weight:600; color:#1a1a2e; flex:1; }
  .qtpl-desc { font-size:10px; color:#888; }
  .qtpl-meta { font-size:9px; color:#aaa; margin-top:1px; }
  .qtpl-actions { display:flex; gap:4px; flex-shrink:0; }
  .qtpl-btn { font-size:10px; padding:2px 7px; border-radius:3px; border:1px solid #ddd; background:none; cursor:pointer; color:#666; transition:all 0.15s; }
  .qtpl-btn:hover { border-color:#1D3557; color:#1D3557; background:#eef2ff; }
  .qtpl-btn.certify { border-color:#e0a800; color:#856404; }
  .qtpl-btn.certify:hover { background:#fff3cd; }
  .qtpl-btn.del { border-color:#f0c0c0; color:#c0392b; }
  .qtpl-btn.del:hover { background:#fef0f0; }
  .qtpl-save-row { display:flex; flex-direction:column; gap:6px; margin-top:10px; padding-top:10px; border-top:1px solid #f0f0f0; }
  .qtpl-save-row label { font-size:11px; color:#565656; }
  .qtpl-save-row input, .qtpl-save-row select { font-size:11px; padding:4px 8px; border:1px solid #d0d0d0; border-radius:4px; outline:none; font-family:inherit; }
  .qtpl-save-row input:focus, .qtpl-save-row select:focus { border-color:#1D3557; }
  .qtpl-filter-row { display:flex; gap:6px; align-items:center; flex-wrap:wrap; }

  /* ── Template Modal ── */
  .template-list { display:flex; flex-direction:column; gap:6px; max-height:320px; overflow-y:auto; padding:2px 0; }
  .template-item {
    display:flex; align-items:center; gap:10px; padding:9px 12px;
    border:1px solid #e0e0e0; border-radius:5px; cursor:pointer;
    background:#fafafa; transition:all 0.15s;
  }
  .template-item:hover { border-color:#1D3557; background:#eef2ff; }
  .template-item.selected { border-color:#1D3557; background:#dce8f5; }
  .template-item.is-default .tpl-name::after { content:' ★'; color:#e0a800; font-size:10px; }
  .tpl-name { font-size:12px; font-weight:600; color:#1a1a2e; flex:1; }
  .tpl-desc { font-size:10px; color:#888; white-space:nowrap; }
  .tpl-blocks { font-size:10px; color:#7a9ab5; margin-top:2px; }
  .tpl-del { font-size:12px; color:#ccc; cursor:pointer; padding:2px 5px; border-radius:3px; border:none; background:none; }
  .tpl-del:hover { color:#c0392b; background:#fef0f0; }
  .modal-save-tpl { display:flex; flex-direction:column; gap:8px; margin-top:10px; padding-top:10px; border-top:1px solid #f0f0f0; }
  .modal-save-tpl label { font-size:11px; color:#565656; }
  .modal-save-tpl input { font-size:12px; padding:5px 8px; border:1px solid #d0d0d0; border-radius:4px; outline:none; font-family:inherit; }
  .modal-save-tpl input:focus { border-color:#1D3557; }

  /* ── Chart-Typ-Dropdown ── */
  .sel-ctype {
    font-size:11px; padding:2px 6px; border:1px solid #c8c8c8;
    border-radius:3px; background:#fafafa; color:#1a1a2e; cursor:pointer;
    outline:none; font-family:inherit; min-width:110px;
  }
  .sel-ctype:focus { border-color:#1D3557; }

  /* Infobox */
  .infobox { background:linear-gradient(135deg,#eef4fb 0%,#e8f5ee 100%); border:1px solid #d0e4f0; border-radius:8px; padding:16px 18px; color:#2c3e50; display:flex; flex-direction:column; gap:10px; height:100%; box-sizing:border-box; overflow-y:auto; }
  .infobox-title { font-size:11px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:#7a9ab5; border-bottom:1px solid #cde0ee; padding-bottom:8px; }
  .infobox-row { display:flex; flex-direction:column; gap:3px; }
  .infobox-row-label { font-size:9px; color:#8aabbc; text-transform:uppercase; letter-spacing:1px; }
  .infobox-row-value { font-size:12px; color:#2c3e50; font-weight:500; line-height:1.4; }
  .infobox-dims { display:flex; flex-direction:column; gap:8px; margin-top:2px; }
  .infobox-dim { display:flex; flex-direction:column; align-items:flex-start; }
  .infobox-dim-label { font-size:9px; color:#8aabbc; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px; }
  .infobox-dim-values { display:flex; gap:5px; flex-wrap:wrap; }
  .infobox-tag { font-size:10px; padding:3px 9px; border-radius:12px; cursor:pointer; background:#fff; color:#4a6b80; white-space:nowrap; border:1px solid #c5d9e8; transition:all 0.15s; user-select:none; }
  .infobox-tag:hover { background:#d8eef8; border-color:#7ab3cc; color:#2c3e50; }
  .infobox-tag.active { background:#39A650; border-color:#2d8a40; color:#fff; font-weight:600; }
  .infobox-series-pill { display:flex; align-items:center; gap:6px; font-size:11px; color:#2c3e50; }
  .infobox-series-dot { width:10px; height:10px; border-radius:50%; flex-shrink:0; border:1px solid rgba(0,0,0,0.15); }
  .infobox-badge { display:inline-flex; align-items:center; justify-content:center; width:26px; height:26px; border-radius:50%; background:#d0e8d8; font-size:12px; font-weight:700; color:#1D6B32; }
  .infobox-n { display:flex; align-items:center; gap:8px; margin-top:auto; padding-top:8px; border-top:1px solid #cde0ee; }
  .infobox-n-label { font-size:10px; color:#8aabbc; }

  /* Modals */
  /* Legend order modal */
  .leg-row { display:flex; align-items:center; gap:8px; padding:6px 10px;
             background:#f8f8f8; border:1px solid #e0e0e0; border-radius:6px;
             cursor:grab; user-select:none; }
  .leg-row:active { cursor:grabbing; }
  .leg-row.drag-over { border-color:#39A650; background:#f0faf0; }
  .leg-handle { color:#bbb; font-size:16px; cursor:grab; }
  .leg-color-btn { width:24px; height:24px; border-radius:4px; border:2px solid #ccc;
                   cursor:pointer; flex-shrink:0; }
  .leg-color-btn:hover { border-color:#39A650; }
  .leg-name { flex:1; font-size:12px; color:#333; }
  .leg-arrows { display:flex; flex-direction:column; gap:1px; }
  .leg-arrow { background:none; border:none; cursor:pointer; font-size:10px;
               color:#888; padding:0; line-height:1; }
  .leg-arrow:hover { color:#39A650; }
  .modal-backdrop { display:none; position:fixed; inset:0; background:rgba(0,0,0,0.35); z-index:1000; align-items:center; justify-content:center; }
  .modal-backdrop.open { display:flex; }
  .modal { background:#fff; border-radius:8px; padding:20px 24px; box-shadow:0 8px 32px rgba(0,0,0,0.18); min-width:460px; max-width:600px; width:92%; display:flex; flex-direction:column; gap:12px; }
  .modal h3 { font-size:13px; color:#1D6B32; font-weight:700; margin:0; }
  .modal-search { width:100%; font-size:12px; padding:6px 10px; border:1px solid #c8c8c8; border-radius:4px; outline:none; }
  .modal-search:focus { border-color:#39A650; }
  .modal-list { max-height:280px; overflow-y:auto; border:1px solid #e0e0e0; border-radius:4px; }
  .modal-list-item { padding:8px 12px; cursor:pointer; font-size:12px; border-bottom:1px solid #f0f0f0; display:flex; align-items:center; gap:10px; transition:background 0.1s; }
  .modal-list-item:last-child { border-bottom:none; }
  .modal-list-item:hover { background:#f0faf0; }
  .modal-list-item.selected { background:#e8f5e9; }
  .modal-item-id { font-size:10px; color:#aaa; white-space:nowrap; }
  .modal-item-name { flex:1; }
  .modal-color-row { display:flex; align-items:center; gap:10px; font-size:12px; color:#565656; }
  .modal-color-row input[type=color] { width:36px; height:28px; border:1px solid #c8c8c8; border-radius:3px; cursor:pointer; padding:2px; }
  .modal-footer { display:flex; justify-content:flex-end; gap:8px; }
  .btn-ok { font-size:12px; padding:5px 18px; border:none; border-radius:4px; background:#39A650; color:#fff; cursor:pointer; font-weight:600; }
  .btn-ok:hover { background:#2d8a40; }
  .btn-ok:disabled { background:#aaa; cursor:default; }
  .btn-cancel { font-size:12px; padding:5px 14px; border:1px solid #c8c8c8; border-radius:4px; background:#fafafa; cursor:pointer; color:#565656; }
  .btn-cancel:hover { background:#f0f0f0; }
  .btn-secondary { font-size:12px; padding:5px 14px; border:1px solid #1D3557; border-radius:4px; background:#fff; cursor:pointer; color:#1D3557; }
  .btn-secondary:hover { background:#eef2f7; }
  .modal-cf label { font-size:11px; color:#565656; display:block; margin-bottom:4px; margin-top:10px; }
  .modal-cf select { width:100%; font-size:12px; padding:5px 8px; border:1px solid #c8c8c8; border-radius:4px; background:#fafafa; outline:none; }
  .modal-cf select:focus { border-color:#39A650; }
  .modal-hint { font-size:10px; color:#aaa; margin-top:6px; }

  /* Save/Open Report */
  .report-modal-list { max-height:300px; overflow-y:auto; border:1px solid #e0e0e0; border-radius:4px; }
  .report-list-item { padding:9px 12px; cursor:pointer; font-size:12px; border-bottom:1px solid #f0f0f0; display:flex; align-items:center; gap:10px; transition:background 0.1s; }
  .report-list-item:last-child { border-bottom:none; }
  .report-list-item:hover { background:#f0faf0; }
  .report-list-item.selected { background:#e8f5e9; }
  .report-list-item .rli-title { flex:1; font-weight:600; color:#2c3e50; }
  .report-list-item .rli-meta { font-size:10px; color:#aaa; white-space:nowrap; }
  .report-list-item .rli-del { color:#ddd; font-size:16px; cursor:pointer; padding:0 4px; }
  .report-list-item .rli-del:hover { color:#c0392b; }
  .modal-form-row { display:flex; flex-direction:column; gap:4px; }
  .modal-form-row label { font-size:11px; color:#565656; font-weight:600; }
  .modal-form-row input, .modal-form-row textarea, .modal-form-row select {
    font-size:12px; padding:5px 8px; border:1px solid #c8c8c8;
    border-radius:4px; outline:none; font-family:inherit;
  }
  .modal-form-row input:focus, .modal-form-row textarea:focus { border-color:#39A650; }
  .modal-form-row textarea { resize:vertical; min-height:60px; }
  .modal-grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:10px; }

  /* Note widget per chart */
  .note-bar {
    border-top:1px solid #f0f0f0; padding:6px 10px;
    background:#fffef5; display:none; flex-direction:column; gap:4px; flex-shrink:0;
  }
  .note-bar.visible { display:flex; }
  .note-bar textarea {
    font-size:11px; padding:5px 8px; border:1px solid #e0d88a;
    border-radius:4px; outline:none; font-family:inherit; resize:vertical; min-height:48px;
    background:#fffef5; color:#333;
  }
  .note-bar textarea:focus { border-color:#c8b000; }
  .note-bar-title input {
    font-size:11px; padding:3px 7px; border:1px solid #e0d88a;
    border-radius:4px; outline:none; font-family:inherit; background:#fffef5; width:200px;
  }
  .btn-note { font-size:11px; padding:2px 7px; border:1px solid #c8c8c8; border-radius:3px; background:#fafafa; cursor:pointer; color:#888; outline:none; font-family:inherit; }
  .btn-note.active { border-color:#c8b000; background:#fffde0; color:#7a6000; }
  .btn-note:hover { border-color:#c8b000; color:#7a6000; }

  /* Manual gridlines widget per chart */
  .gridline-bar {
    border-top:1px solid #f0f0f0; padding:6px 10px;
    background:#fdf3f2; display:none; align-items:center; gap:6px; flex-shrink:0;
  }
  .gridline-bar.visible { display:flex; }
  .gridline-bar label { font-size:10px; color:#888; white-space:nowrap; }
  .gridline-bar input {
    font-size:11px; padding:3px 7px; border:1px solid #e0a8a2;
    border-radius:4px; outline:none; font-family:inherit; background:#fdf3f2; color:#333; flex:1;
  }
  .gridline-bar input:focus { border-color:#c85a4a; }
  .btn-gridline { font-size:11px; font-weight:600; padding:2px 8px; border:1px solid #c8c8c8; border-radius:3px; background:#fafafa; cursor:pointer; color:#a03a2c; outline:none; font-family:inherit; white-space:nowrap; }
  .btn-gridline.active { border-color:#c85a4a; background:#fdf0ee; color:#a03a2c; }
  .btn-gridline:hover { border-color:#c85a4a; background:#fdf0ee; color:#a03a2c; }
</style>
</head>
<body>

<!-- Global Toolbar -->
<div id="global-toolbar">
  <label>Charts:</label>
  <input id="inp-count" type="number" min="1" value="9">
  <div class="tb-sep"></div>
  <button id="btn-sd" class="btn-toolbar active" title="Toggle Standard Deviation bars">± SD</button>
  <button id="btn-minmax" class="btn-toolbar" title="Toggle Min/Max markers">↕ Min/Max</button>
  <button id="btn-legend-order" class="btn-toolbar" title="Legend order &amp; colours">🎨 Legend</button>
  <div class="tb-sep"></div>
  <button id="btn-toggle-builder" class="btn-toolbar" title="Toggle SQL Builder" style="display:none">⚙ Filter</button>
  <div class="tb-sep" id="sep-builder" style="display:none"></div>
  <div id="series-list"></div>
  <button id="btn-pick-series" class="btn-toolbar" style="font-weight:600;">📊 Series</button>
  <button id="btn-add-series" class="btn-toolbar">+ Compare</button>
  <button id="btn-add-image" class="btn-toolbar">🖼 + Image</button>
  <div class="tb-sep"></div>
  <button id="btn-global-note" class="btn-toolbar" title="Toggle global report note">📝 Note</button>
  <button id="btn-templates" class="btn-toolbar" title="Layout Templates">📋 Templates</button>
  <button id="btn-save-report" class="btn-toolbar" title="Save Report">💾 Save</button>
  <button id="btn-open-report" class="btn-toolbar" title="Open Report">📂 Open</button>
  <button id="btn-export-pdf" class="btn-toolbar" title="Export as PDF">📄 PDF</button>
  <span id="report-title-display" style="font-size:11px;color:#39A650;font-weight:600;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"></span>
</div>

<!-- Drill-Down Breadcrumb Bar -->
<div id="drilldown-bar">
  <span style="font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#c8a000;margin-right:4px;">DRILL</span>
  <div id="drilldown-crumbs" style="display:flex;align-items:center;gap:4px;flex-wrap:wrap;"></div>
</div>

<div id="main-layout">

  <!-- SQL Builder Panel (only in visual mode) -->
  <div id="builder-panel" class="hidden">
    <div class="builder-header">
      <span>🔍 Visual SQL Builder</span>
      <span id="builder-result-count" style="font-size:10px;font-weight:normal;opacity:0.7;"></span>
    </div>
    <div class="builder-body">

      <!-- Mode Toggle (nur im Visual Mode sichtbar) -->
      <div class="builder-mode-toggle" id="builder-mode-toggle" style="display:none;">
        <button class="builder-mode-btn active" id="btn-mode-trial" onclick="_setBuilderMode('trial')">📊 Trial Data</button>
        <button class="builder-mode-btn" id="btn-mode-free" onclick="_setBuilderMode('free')">🔓 Free Query</button>
      </div>

      <!-- ═══ TRIAL DATA PANEL ═══ -->
      <div id="panel-trial-mode">

        <!-- Group By -->
        <div class="builder-section" id="builder-groupby-section" style="flex-shrink:0;">
          <div class="builder-section-title">Group by (Legend)</div>
          <select class="builder-select" id="b-groupby">
            <option value="jet">Jet</option>
          </select>
        </div>

        <div class="builder-divider" id="builder-groupby-divider" style="flex-shrink:0;"></div>

        <!-- Filter Tabs -->
        <div class="builder-tabs" style="flex-shrink:0;">
          <button class="builder-tab active" id="tab-simple">Simple</button>
          <button class="builder-tab" id="tab-advanced">Advanced</button>
        </div>

        <!-- Simple Tab -->
        <div class="builder-tab-panel active" id="panel-simple">
          <div class="builder-section">
            <div id="filter-rows"></div>
            <button class="btn-add-filter" id="btn-add-filter">+ Add Filter</button>
          </div>
        </div>

        <!-- Advanced Tab -->
        <div class="builder-tab-panel" id="panel-advanced">
          <div class="builder-section">
            <div id="adv-filter-rows" style="display:flex;flex-direction:column;gap:5px;"></div>
            <button class="btn-add-filter" id="btn-add-adv-filter">+ Add Condition</button>
          </div>
          <div class="adv-preview" id="adv-preview" style="display:none;"></div>
        </div>

        <!-- Trial Series -->
        <div class="builder-divider" style="flex-shrink:0;margin-top:4px;"></div>
        <div class="builder-section" id="builder-series-section" style="flex-shrink:0;">
          <div class="builder-section-title">Trial Series</div>
          <select class="builder-select" id="b-series" size="5" multiple style="height:105px;">
            <option value="">Loading...</option>
          </select>
          <div style="font-size:10px;color:#aaa;margin-top:3px;">Hold Ctrl to select multiple</div>
        </div>

      </div>

      <!-- ═══ FREE QUERY PANEL ═══ -->
      <div id="panel-free-mode" style="display:none;flex-direction:column;gap:10px;">

      <!-- Block Selector -->
        <div class="fqb-section" style="flex-shrink:0;">
          <div class="fqb-section-title">Configure Chart</div>
          <select class="builder-select" id="fqb-block-selector">
            <option value="0">Chart 1</option>
          </select>
        </div>

      <!-- Free Query Tab (content) -->
      <div id="panel-free">
        <div class="fqb-section">
          <div class="fqb-section-title">Chart Title</div>
          <input type="text" id="fqb-chart-title" placeholder="e.g. Jet Geometry Overview"
            style="width:100%;font-size:11px;padding:5px 8px;border:1px solid #d0d0d0;border-radius:4px;background:#fafafa;outline:none;font-family:inherit;box-sizing:border-box;">
        </div>
        <div class="fqb-section">
          <div class="fqb-section-title">Chart Type</div>
          <select class="fqb-select" id="fqb-chart-type">
            <option value="scatter">◉ Scatter</option>
            <option value="bar">▦ Bar</option>
            <option value="stack">▦ Stacked Bar</option>
            <option value="line">╱ Line</option>
            <option value="box">⊡ Box Plot</option>
            <option value="heat">⊞ Heatmap</option>
            <option value="3d">◈ 3D</option>
          </select>
        </div>
        <div class="fqb-section">
          <div class="fqb-section-title">Base Table</div>
          <select class="fqb-select" id="fqb-base-table">
            <option value="">— Select table —</option>
          </select>
        </div>
        <div class="fqb-section" id="fqb-join-section" style="display:none;">
          <div class="fqb-section-title">Add Tables (JOIN)</div>
          <div style="display:flex;gap:4px;">
            <select class="fqb-select" id="fqb-join-select" style="flex:1;"><option value="">— Available tables —</option></select>
            <button class="btn-add-filter" id="btn-fqb-add-join" style="white-space:nowrap;padding:4px 8px;">+ Join</button>
          </div>
          <div id="fqb-join-pills"></div>
        </div>
        <div class="fqb-section" id="fqb-axes-section" style="display:none;">
          <div class="fqb-section-title">Axes &amp; Fields</div>
          <div class="fqb-axis-row"><label>X</label><select class="fqb-select" id="fqb-x"></select></div>
          <div class="fqb-axis-row"><label>Y</label><select class="fqb-select" id="fqb-y"></select></div>
          <div class="fqb-axis-row" id="fqb-row-z" style="display:none;"><label>Z</label><select class="fqb-select" id="fqb-z"><option value="">— none —</option></select></div>
          <div class="fqb-axis-row" id="fqb-row-color"><label>Color</label><select class="fqb-select" id="fqb-color"><option value="">— none —</option></select></div>
          <div class="fqb-axis-row" id="fqb-row-label"><label>Label</label><select class="fqb-select" id="fqb-label"><option value="">— none —</option></select></div>
        </div>
        <div class="fqb-section" id="fqb-filter-section" style="display:none;">
          <div class="fqb-section-title">Where</div>
          <div id="fqb-filter-rows" style="display:flex;flex-direction:column;gap:5px;"></div>
          <button class="btn-add-filter" id="btn-fqb-add-filter">+ Add Filter</button>
        </div>
        <div class="fqb-section" id="fqb-groupby-section" style="display:none;">
          <div class="fqb-section-title">Group By (Legend)</div>
          <select class="fqb-select" id="fqb-groupby">
            <option value="">— none —</option>
          </select>
        </div>
        <div class="fqb-section" id="fqb-series-section" style="display:none;">
          <div class="fqb-section-title">Trial Series (optional)</div>
          <select class="fqb-select" id="fqb-series-sel" size="4" multiple style="height:88px;">
            <option value="">Loading...</option>
          </select>
          <div style="font-size:10px;color:#aaa;margin-top:3px;">Hold Ctrl for multiple</div>
        </div>
        <div class="fqb-section" id="fqb-limit-section" style="display:none;">
          <div class="fqb-section-title">Limit</div>
          <input type="number" id="fqb-limit" value="500" min="1" max="5000" class="fqb-select" style="width:100px;">
        </div>
        <div class="fqb-preview" id="fqb-sql-preview" style="display:none;"></div>
      </div><!-- end panel-free -->

      </div><!-- end panel-free-mode -->

    </div>

    <div style="padding:10px 12px;border-top:1px solid #f0f0f0;flex-shrink:0;display:flex;gap:6px;">
      <button class="btn-run" id="btn-run-query" style="flex:1;">▶ Run Query</button>
      <button class="btn-run" id="btn-query-templates" style="background:#1D3557;flex-shrink:0;padding:7px 10px;" title="Query Templates">📋</button>
    </div>
    <div id="result-info"></div>
  </div>

  <!-- Charts wrapper (right side of main-layout) -->
  <div id="charts-wrapper" style="flex:1;display:flex;flex-direction:column;min-width:0;position:relative;">
    <!-- Builder Toggle Arrow (visual mode only) -->
    <div id="builder-arrow" title="Toggle SQL Builder">
      <svg id="builder-arrow-svg" width="10" height="16" viewBox="0 0 10 16" fill="none">
        <polyline points="7,2 2,8 7,14" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </div>
    <div id="global-note-bar" style="display:none;margin-bottom:10px;background:#fffef5;border:1px solid #e0d88a;border-radius:6px;padding:10px 14px;flex-direction:column;gap:6px;">
      <div style="display:flex;align-items:center;gap:8px;">
        <span style="font-size:11px;font-weight:700;color:#7a6000;">📝 Report Note</span>
        <button id="btn-hide-global-note" style="margin-left:auto;font-size:11px;padding:1px 8px;border:1px solid #e0d88a;border-radius:3px;background:none;cursor:pointer;color:#aaa;">✕</button>
      </div>
      <textarea id="global-note-text" rows="3" placeholder="Overall observations, conclusions, recommendations..." style="font-size:12px;padding:6px 9px;border:1px solid #e0d88a;border-radius:4px;outline:none;font-family:inherit;background:#fffef5;color:#333;resize:vertical;width:100%;box-sizing:border-box;"></textarea>
    </div>
    <div id="grid"></div>
    <div id="no-data">No data available for this Trial Series.</div>
  </div>

</div>

<!-- Add Series Modal -->
<div class="modal-backdrop" id="modal-legend-order">
  <div class="modal" style="min-width:480px;max-width:560px;">
    <h3>🎨 Legend — Order &amp; Colours</h3>
    <p style="font-size:11px;color:#888;margin:0;">Drag rows or use ↑↓ to reorder. Click colour to change. Resets on next query.</p>
    <div id="legend-order-list" style="display:flex;flex-direction:column;gap:6px;max-height:340px;overflow-y:auto;padding:4px 0;"></div>
    <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:4px;">
      <button class="btn-cancel" id="legend-order-reset">↺ Reset</button>
      <button class="btn-cancel" id="legend-order-cancel">Cancel</button>
      <button class="btn-ok" id="legend-order-apply">Apply</button>
    </div>
  </div>
</div>

<div class="modal-backdrop" id="modal-series">
  <div class="modal">
    <h3>Add Trial Series for Comparison</h3>
    <input class="modal-search" id="series-search" type="text" placeholder="Search by name or ID...">
    <div class="modal-list" id="series-list-modal"></div>
    <div class="modal-color-row" id="series-color-row">
      <label>Color for this series:</label>
      <input type="color" id="series-color-pick" value="#39A650">
    </div>
    <div class="modal-footer">
      <button class="btn-cancel" id="series-modal-cancel">Cancel</button>
      <button class="btn-ok" id="series-modal-ok" disabled>Add Series</button>
    </div>
  </div>
</div>

<!-- Save Report Modal -->
<div class="modal-backdrop" id="modal-save-report">
  <div class="modal" style="min-width:480px;">
    <h3>💾 Save Report</h3>
    <div class="modal-form-row">
      <label>Report Title *</label>
      <input type="text" id="save-title" placeholder="e.g. X60.112 Stability Analysis Q2 2026" maxlength="200">
    </div>
    <div class="modal-grid-2">
      <div class="modal-form-row">
        <label>Author</label>
        <input type="text" id="save-author" maxlength="100">
      </div>
      <div class="modal-form-row">
        <label>Infobox in Report</label>
        <select id="save-infobox">
          <option value="left">Show — left panel</option>
          <option value="top">Show — top bar</option>
          <option value="none">Hide</option>
        </select>
      </div>
    </div>
    <div class="modal-form-row">
      <label>Global Note / Summary</label>
      <textarea id="save-global-note" placeholder="Overall observations, conclusions..."></textarea>
    </div>
    <div id="save-report-id" style="display:none;"></div>
    <div class="modal-footer">
      <button class="btn-cancel" id="save-report-cancel">Cancel</button>
      <button class="btn-secondary" id="save-report-new" style="display:none;" title="Save as a new separate report (keeps the existing one)">Save as New</button>
      <button class="btn-ok" id="save-report-ok">Save Report</button>
    </div>
  </div>
</div>

<!-- Open Report Modal -->
<div class="modal-backdrop" id="modal-open-report">
  <div class="modal" style="min-width:560px;">
    <h3>📂 Open Report</h3>
    <input class="modal-search" id="report-search" type="text" placeholder="Search by title or author...">
    <div class="report-modal-list" id="report-list-container">
      <div style="padding:20px;text-align:center;color:#aaa;font-size:12px;">Loading...</div>
    </div>
    <div class="modal-footer">
      <button class="btn-cancel" id="open-report-cancel">Cancel</button>
      <button class="btn-ok" id="open-report-ok" disabled>Open Selected</button>
    </div>
  </div>
</div>

<!-- Custom Field Modal -->
<div class="modal-backdrop" id="modal-cf">
  <div class="modal modal-cf">
    <h3>⚙ Custom Field</h3>
    <label>Table</label>
    <select id="modal-table">{table_options}</select>
    <label>Field</label>
    <select id="modal-field"><option value="">— Select table —</option></select>
    <div class="modal-hint" id="modal-hint"></div>
    <div class="modal-footer">
      <button class="btn-cancel" id="modal-cancel">Cancel</button>
      <button class="btn-ok" id="modal-ok">Apply</button>
    </div>
  </div>
</div>

<!-- Query Templates Modal -->
<div class="modal-backdrop" id="modal-query-templates">
  <div class="modal" style="min-width:560px;max-width:680px;">
    <h3>📋 Query Templates</h3>

    <!-- Filter Tabs -->
    <div style="display:flex;gap:6px;margin-bottom:10px;flex-wrap:wrap;">
      <button class="qtpl-btn" id="qtpl-tab-all" style="border-color:#1D3557;color:#1D3557;">All</button>
      <button class="qtpl-btn" id="qtpl-tab-1">👤 Personal</button>
      <button class="qtpl-btn" id="qtpl-tab-2">👥 Shared</button>
      <button class="qtpl-btn" id="qtpl-tab-3">⭐ Certified</button>
    </div>

    <div class="qtpl-list" id="qtpl-list-container">
      <div style="padding:20px;text-align:center;color:#aaa;font-size:12px;">Loading...</div>
    </div>

    <!-- Save current query as template -->
    <div class="qtpl-save-row" id="qtpl-save-section">
      <label>💾 Save current query as template:</label>
      <input type="text" id="qtpl-name" placeholder="Template name...">
      <input type="text" id="qtpl-desc" placeholder="Description (optional)">
      <div class="qtpl-filter-row">
        <select id="qtpl-level">
          <option value="1">👤 Personal (only me)</option>
          <option value="2">👥 Shared (all users)</option>
        </select>
        <button class="btn-ok" id="btn-qtpl-save" style="padding:4px 14px;">Save</button>
      </div>
    </div>

    <div class="modal-footer">
      <button class="btn-cancel" id="qtpl-modal-cancel">Close</button>
      <button class="btn-ok" id="btn-qtpl-apply" disabled>Apply Template</button>
    </div>
  </div>
</div>

<!-- Layout Templates Modal -->
<div class="modal-backdrop" id="modal-templates">
  <div class="modal" style="min-width:520px;">
    <h3>📋 Layout Templates</h3>
    <div class="template-list" id="template-list-container">
      <div style="padding:20px;text-align:center;color:#aaa;font-size:12px;">Loading...</div>
    </div>
    <div class="modal-save-tpl">
      <label>💾 Save current layout as new template:</label>
      <div style="display:flex;gap:8px;align-items:center;">
        <input type="text" id="tpl-save-name" placeholder="Template name..." style="flex:1;">
        <input type="text" id="tpl-save-desc" placeholder="Description (optional)" style="flex:1.5;">
        <button class="btn-ok" id="btn-tpl-save-new" style="white-space:nowrap;">+ Save new</button>
        <button class="btn-ok" id="btn-tpl-overwrite" style="white-space:nowrap;background:#e0a800;border-color:#c89000;display:none;">↺ Overwrite</button>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn-cancel" id="tpl-modal-cancel">Close</button>
      <button class="btn-ok" id="btn-tpl-apply" disabled>Apply Template</button>
    </div>
  </div>
</div>

<!-- PDF Export Modal -->
<div class="modal-backdrop" id="modal-pdf-export">
  <div class="modal" style="min-width:400px;">
    <h3>📄 PDF Export</h3>
    <div class="modal-form-row">
      <label>Report Title</label>
      <input type="text" id="pdf-export-title" placeholder="e.g. X60.112 Stability Analysis" maxlength="200"
        style="width:100%;font-size:12px;padding:5px 8px;border:1px solid #d0d0d0;border-radius:4px;background:#fafafa;outline:none;font-family:inherit;">
    </div>
    <div class="modal-form-row">
      <label>Layout Template</label>
      <select id="pdf-template-select" style="width:100%;font-size:12px;padding:5px 8px;border:1px solid #d0d0d0;border-radius:4px;background:#fafafa;outline:none;">
        <option value="">— Lädt... —</option>
      </select>
    </div>
    <div id="pdf-template-desc" style="font-size:10px;color:#888;margin-top:4px;min-height:16px;"></div>
    <div class="modal-footer">
      <button class="btn-cancel" id="pdf-export-cancel">Cancel</button>
      <button class="btn-ok" id="pdf-export-ok">Export</button>
    </div>
  </div>
</div>

<script>
window.onerror=function(msg,src,line,col){if(typeof _bridge!=='undefined')_bridge.jsError('L'+line+':C'+col+' '+msg);return false;};
var DATA          = {data_json};
var CURRENT_USER  = {current_user_json};
var IS_SUPERUSER  = {is_superuser_json};
var Y_AXES        = {y_axes_json};
var X_AXES        = {x_axes_json};
var G_AXES        = {g_axes_json};
var TBL_COLS      = {tbl_cols_json};
var INFOBOX       = {infobox_json};
var PRIMARY_PK    = {primary_series_pk};
var IS_VISUAL     = {is_visual_mode};  // true = Visual SQL mode
var INITIAL_REPORT_ID = {initial_report_id_json};  // gesetzt, wenn ueber das
  // "Go!"-Dropdown in Show Experiment direkt ein bestimmter Report geoeffnet
  // werden soll (siehe screen_show_experiment.py/screen_report.py::load_series())

var PALETTE = ['#39A650','#565656','#1D6B32','#8C8C8C','#6DBF7E','#2E2E2E','#A8D5A2','#B0A070','#0A3D1F','#C8C8C8'];
var SERIES_COLORS = ['#39A650','#39A650','#4A90D9','#D4A017','#8B2FC9','#C0392B'];
var COMPARE_COLORS = ['#6ECF8A','#F4A7B9','#74B9E8','#E8C84A','#C3A0E8'];
function _reassignCompareColors(){
  // Wenn nur 1 Series: Originalfarbe (#39A650) behalten
  if(SERIES_REGISTRY.length <= 1){
    if(SERIES_REGISTRY.length === 1) SERIES_REGISTRY[0].color = '#39A650';
    return;
  }
  // Ab 2 Series: alle auf COMPARE_COLORS umstellen
  SERIES_REGISTRY.forEach(function(s, i){
    s.color = COMPARE_COLORS[i % COMPARE_COLORS.length];
  });
}

function _nextCompareColor(){
  var used = SERIES_REGISTRY.map(function(s){return s.color;});
  for(var i=0;i<COMPARE_COLORS.length;i++){
    if(used.indexOf(COMPARE_COLORS[i])===-1) return COMPARE_COLORS[i];
  }
  return COMPARE_COLORS[SERIES_REGISTRY.length % COMPARE_COLORS.length];
}
function getColor(i){return PALETTE[i%PALETTE.length];}
function _textColorFor(hexColor){
  // Luminanz berechnen → dunkel oder hell?
  var r=parseInt(hexColor.slice(1,3),16)/255;
  var g=parseInt(hexColor.slice(3,5),16)/255;
  var b=parseInt(hexColor.slice(5,7),16)/255;
  var lum=0.299*r+0.587*g+0.114*b;
  return lum>0.55?'#1a1a2e':'#ffffff';
}
function hexRgb(h){return[parseInt(h.slice(1,3),16)/255,parseInt(h.slice(3,5),16)/255,parseInt(h.slice(5,7),16)/255];}

// ── Drill-Down ────────────────────────────────────────────────────────────────
// Stack entries: {xKey, xTitle, filterField, filterValue, filterLabel}
var _drillStack = [];

function _getSubAxisKey(xKey){
  var ax = X_AXES.find(function(a){return a.key===xKey;});
  if(!ax || !ax.sub_axis_id) return null;
  var sub = X_AXES.find(function(a){return a.id===ax.sub_axis_id;});
  return sub ? sub.key : null;
}

function _drillDown(chartIdx, clickedXValue, clickedJetKey){
  var state  = getState(chartIdx);
  var xKey   = state.xField;

  // Wenn bereits auf Trial-Ebene — kein weiterer Drill möglich
  if(xKey === 'trial_nr') return;

  var xDef  = X_AXES.find(function(a){return a.key===xKey;})||{title:xKey,unit:''};

  // Jet-Namen aus jetKey extrahieren (raw jet_name in DATA)
  var jetName = null;
  if(clickedJetKey){
    var parts = clickedJetKey.split('::');
    jetName = parts.length > 1 ? parts[1] : parts[0];
  }

  var label = xDef.title + ': ' + clickedXValue + (xDef.unit?' '+xDef.unit:'');
  if(jetName) label += ' · ' + jetName;

  // Root-States merken (beim ersten Drill)
  if(_drillStack.length === 0){
    var total0 = Math.max(1,parseInt(document.getElementById('inp-count').value)||1);
    for(var i0=0;i0<total0;i0++){
      _drillRootStates[i0] = (chartStates[i0]||{}).xField || null;
    }
  }

  _drillStack.push({
    xKey:        xKey,
    xTitle:      xDef.title,
    filterField: xKey,
    filterValue: clickedXValue,
    jetName:     jetName,
    filterLabel: label,
    prevFilters: JSON.parse(JSON.stringify(_drillFilters)),
  });

  // Filter: genau dieser X-Wert UND dieser Jet
  _drillFilters[xKey] = clickedXValue;
  if(jetName) _drillFilters['__drill_jet'] = jetName;

  // Alle Charts auf trial_nr umschalten
  var total = Math.max(1,parseInt(document.getElementById('inp-count').value)||1);
  syncNotesToState();
  for(var i=0;i<total;i++){
    var s=getState(i);
    if(s.blockType==='image') continue;
    s.xField='trial_nr';
    chartStates[i]=s;
  }
  _renderBreadcrumb();
  rebuildGrid();
}


function _drillUpTo(stackIdx){
  // stackIdx = -1 → ganz nach oben (Root)
  if(stackIdx < 0){
    _drillStack = [];
    _drillFilters = {};
  } else {
    // Auf Ebene stackIdx zurückgehen: Stack auf stackIdx Einträge kürzen
    // und Filter auf den Zustand VOR diesem Eintrag zurücksetzen
    _drillFilters = JSON.parse(JSON.stringify(_drillStack[stackIdx].prevFilters));
    _drillStack = _drillStack.slice(0, stackIdx);
  }

  // X-Achse aller Charts: falls Stack leer → Original-X, sonst Sub-Achse des letzten Eintrags
  var total = Math.max(1,parseInt(document.getElementById('inp-count').value)||1);
  syncNotesToState();
  var targetXKey = null;
  if(_drillStack.length === 0){
    targetXKey = null; // jeder Chart behält seine eigene ursprüngliche xField — wird nicht überschrieben
  } else {
    var last = _drillStack[_drillStack.length-1];
    targetXKey = _getSubAxisKey(last.filterField);
  }

  // Zurück zum Root — Original-X aller Charts wiederherstellen
  for(var i=0;i<total;i++){
    if(!chartStates[i] || chartStates[i].blockType==='image') continue;
    if(_drillStack.length === 0){
      // Root: Original-xField zurück
      if(_drillRootStates[i]) chartStates[i].xField = _drillRootStates[i];
    } else {
      // Partial drill-up: immer noch auf trial_nr (wir sind noch im Drill)
      chartStates[i].xField = 'trial_nr';
    }
  }

  _renderBreadcrumb();
  _animatedRebuild('back');
}

function _animatedRebuild(direction){
  rebuildGrid();
}

function _renderBreadcrumb(){
  var bar    = document.getElementById('drilldown-bar');
  var crumbs = document.getElementById('drilldown-crumbs');
  if(!bar || !crumbs) return;
  crumbs.innerHTML = '';

  if(_drillStack.length === 0){
    bar.classList.remove('visible');
    return;
  }
  bar.classList.add('visible');

  // 🏠 Home
  var home = document.createElement('span');
  home.className = 'drill-crumb home';
  home.textContent = '🏠 Reset';
  home.title = 'Back to overview';
  home.addEventListener('click', function(){ _drillUpTo(-1); });
  crumbs.appendChild(home);

  // Zwischenschritte
  _drillStack.forEach(function(entry, i){
    var sep = document.createElement('span');
    sep.className = 'drill-crumb-sep';
    sep.textContent = '›';
    crumbs.appendChild(sep);

    var crumb = document.createElement('span');
    crumb.className = 'drill-crumb';
    crumb.textContent = entry.filterLabel;
    crumb.title = 'Back to: ' + entry.filterLabel;
    (function(idx){ crumb.addEventListener('click', function(){ _drillUpTo(idx); }); })(i);
    crumbs.appendChild(crumb);
  });

  // Aktuelles Level anzeigen
  var last   = _drillStack[_drillStack.length-1];
  var subKey = _getSubAxisKey(last.filterField);
  if(subKey){
    var subDef = X_AXES.find(function(a){return a.key===subKey;})||{title:subKey};
    var sep2   = document.createElement('span');
    sep2.className = 'drill-crumb-sep'; sep2.textContent = '›';
    crumbs.appendChild(sep2);
    var curr = document.createElement('span');
    curr.className = 'drill-current';
    curr.textContent = subDef.title;
    crumbs.appendChild(curr);
  }
}

// Aktive Drill-Filter (xKey → value), für Datenfiltierung
var _drillFilters = {};
// Ursprüngliche xField-Werte je Chart (für Reset)
var _drillRootStates = {};

var SERIES_REGISTRY = [{pk:PRIMARY_PK, name:INFOBOX.series_name||('Series '+PRIMARY_PK), color:'#39A650', data:DATA, machine:INFOBOX.machine||'', material:INFOBOX.material||''}];

// ── SQL Builder ───────────────────────────────────────────────────────────────
var _allSeriesForBuilder = [];

// Filter field definitions
var FILTER_FIELDS = [
  {key:'jet',          label:'Jet',               type:'lookup'},
  {key:'yarn',         label:'Yarn',              type:'lookup'},
  {key:'machine',      label:'Machine',           type:'lookup'},
  {key:'air_pressure', label:'Air Pressure (bar)',type:'numeric'},
  {key:'overfeed',     label:'Overfeed (%)',      type:'numeric'},
  {key:'speed',        label:'Speed (m/min)',     type:'numeric'},
  {key:'jet_plate',    label:'Jet Plate Number',  type:'numeric'},
];
var _lookupCache = {};
var _pendingSelects = {};

function populateValueSelect(sel, values){
  sel.innerHTML = values.map(function(v){
    return '<option value="'+v+'">'+v+'</option>';
  }).join('');
}

function receiveFilterValues(fieldKey, values){
  _lookupCache[fieldKey] = values;
  (_pendingSelects[fieldKey]||[]).forEach(function(sel){
    if(sel.parentNode) populateValueSelect(sel, values);
  });
  _pendingSelects[fieldKey] = [];
}

function initBuilder(){
  if(!IS_VISUAL){
    // Sicherheit: Panel und Pfeil in Series-Mode komplett versteckt
    var p=document.getElementById('builder-panel');
    var a=document.getElementById('builder-arrow');
    if(p) p.classList.add('hidden');
    if(a) a.style.display='none';
    return;
  }

  // Pfeil-Button sichtbar, Panel ist per default offen
  var arrow = document.getElementById('builder-arrow');
  if(arrow){
    arrow.style.display = 'flex';
    arrow.classList.add('open'); // default: offen
  }
  // Panel öffnen
  var panel = document.getElementById('builder-panel');
  if(panel) panel.classList.remove('hidden');

  // Alter toggle-builder Button ausblenden (Pfeil übernimmt)
  document.getElementById('btn-toggle-builder').style.display='none';
  document.getElementById('sep-builder').style.display='none';

  // In Visual-Mode: "Compare" ausblenden, Series-Picker bleibt
  document.getElementById('btn-add-series').style.display='none';

  if(_bridge){
    _bridge.getSeriesList();
    FILTER_FIELDS.filter(function(f){return f.type==='lookup';}).forEach(function(f){
      _bridge.getFilterValues(f.key);
    });
  }
  document.getElementById('btn-add-filter').addEventListener('click', function(){ addFilterRow(); });
  document.getElementById('btn-run-query').addEventListener('click', runQuery);
  document.getElementById('btn-query-templates').addEventListener('click', openQueryTemplatesModal);
  initFilterTabs();
  initFreeQueryTab();
  _populateGroupBy();

  if(IS_VISUAL){
    // Mode Toggle einblenden
    var toggle = document.getElementById('builder-mode-toggle');
    if(toggle) toggle.style.display='flex';
    // Standard: Trial Mode
    _setBuilderMode('trial');
  }

  // Pfeil-Button Toggle
  function _toggleBuilder(){
    var panel  = document.getElementById('builder-panel');
    var hidden = panel.classList.toggle('hidden');
    arrow.classList.toggle('open', !hidden);
  }
  arrow.addEventListener('click', _toggleBuilder);
  addFilterRow();
}

var _filterCount = 0;
function addFilterRow(prefill){
  var row = document.createElement('div');
  row.className = 'filter-row';
  row.id = 'frow_'+(++_filterCount);

  var selField = document.createElement('select');
  selField.innerHTML = FILTER_FIELDS.map(function(f){
    return '<option value="'+f.key+'">'+f.label+'</option>';
  }).join('');

  var selOp = document.createElement('select');

  var valContainer = document.createElement('div');
  valContainer.style.cssText = 'flex:1;min-width:0;';

  function updateRow(){
    var fdef = FILTER_FIELDS.find(function(f){return f.key===selField.value;})||FILTER_FIELDS[0];
    var ops  = fdef.type==='numeric' ? ['=','!=','>','<','>=','<='] : ['=','!='];
    selOp.innerHTML = ops.map(function(o){return'<option value="'+o+'">'+o+'</option>';}).join('');
    valContainer.innerHTML='';
    if(fdef.type==='numeric'){
      var inp=document.createElement('input');
      inp.type='number'; inp.step='any'; inp.placeholder='Value';
      inp.className='filter-value-widget';
      inp.style.cssText='width:100%;font-size:11px;padding:4px 6px;border:1px solid #d0d0d0;border-radius:4px;background:#fafafa;outline:none;font-family:inherit;';
      valContainer.appendChild(inp);
    } else {
      var sel=document.createElement('select');
      sel.className='filter-value-widget';
      sel.multiple=true;
      sel.size=4;
      sel.style.cssText='width:100%;font-size:11px;padding:2px 4px;border:1px solid #d0d0d0;border-radius:4px;background:#fafafa;outline:none;font-family:inherit;';
      sel.title='Hold Ctrl to select multiple';
      if(_lookupCache[fdef.key]&&_lookupCache[fdef.key].length){
        populateValueSelect(sel, _lookupCache[fdef.key]);
      } else {
        sel.innerHTML='<option value="">Loading...</option>';
        _pendingSelects[fdef.key]=_pendingSelects[fdef.key]||[];
        _pendingSelects[fdef.key].push(sel);
        if(_bridge) _bridge.getFilterValues(fdef.key);
      }
      // hint label
      var hint=document.createElement('div');
      hint.style.cssText='font-size:9px;color:#aaa;margin-top:2px;';
      hint.textContent='Ctrl+Click for multiple';
      valContainer.appendChild(sel);
      valContainer.appendChild(hint);
    }
  }

  selField.addEventListener('change', updateRow);
  var btnRm=document.createElement('button');
  btnRm.className='filter-row-remove'; btnRm.textContent='×';
  btnRm.addEventListener('click',function(){document.getElementById('filter-rows').removeChild(row);});

  row.appendChild(selField);
  row.appendChild(selOp);
  row.appendChild(valContainer);
  row.appendChild(btnRm);
  document.getElementById('filter-rows').appendChild(row);
  updateRow();
  // Vorausgefüllte Werte setzen falls vorhanden
  if(prefill){
    selField.value = prefill.filterKey || selField.value;
    updateRow(); // Neu rendern mit richtigem Feld
    if(prefill.op && selOp) selOp.value = prefill.op;
    setTimeout(function(){
      var w = row.querySelector('.filter-value-widget');
      if(!w) return;
      if(prefill.values && w.tagName==='SELECT'){
        for(var i=0;i<w.options.length;i++){
          w.options[i].selected = prefill.values.indexOf(w.options[i].value)!==-1;
        }
      } else if(prefill.value !== undefined){
        w.value = prefill.value;
      }
    }, 100);
  }
}

function getFilters(){
  var rows=document.getElementById('filter-rows').querySelectorAll('.filter-row');
  var filters=[];
  rows.forEach(function(row){
    var selField=row.querySelector('select');
    var selOp=row.querySelectorAll('select')[1];
    var widget=row.querySelector('.filter-value-widget');
    if(!widget)return;
    var fdef=FILTER_FIELDS.find(function(f){return f.key===selField.value;})||FILTER_FIELDS[0];
    // For multi-select, collect all selected values
    if(fdef.type==='lookup' && widget.tagName==='SELECT'){
      var selected=[];
      for(var oi=0;oi<widget.options.length;oi++){
        if(widget.options[oi].selected&&widget.options[oi].value)
          selected.push(widget.options[oi].value);
      }
      if(selected.length===0)return;
      filters.push({filterKey:fdef.key, type:fdef.type, op:'IN', values:selected});
    } else {
      if(!widget.value||!widget.value.trim())return;
      filters.push({filterKey:fdef.key, type:fdef.type, op:selOp?selOp.value:'=', value:widget.value.trim()});
    }
  });
  return filters;
}

function getSelectedSeries(){
  var sel=document.getElementById('b-series'),pks=[];
  for(var i=0;i<sel.options.length;i++){if(sel.options[i].selected&&sel.options[i].value)pks.push(parseInt(sel.options[i].value));}
  return pks;
}

function runQuery(){
  var btn=document.getElementById('btn-run-query');
  btn.disabled=true; btn.textContent='⏳ Running...';
  if(_builderMode==='free'||_activeFilterTab==='free'){
    var cfg=getFreeQueryConfig();
    if(!cfg.baseTable||!cfg.xField||!cfg.yField){
      btn.disabled=false;btn.textContent='▶ Run Query';
      alert('Please select Base Table, X and Y fields.');
      return;
    }
    cfg._blockIdx = _activeFqbBlockIdx;
    _saveFqbStateForBlock(_activeFqbBlockIdx);
    if(_bridge) _bridge.runFreeQuery(JSON.stringify(cfg));
    return;
  }
  var simpleFilters = _activeFilterTab==='advanced' ? [] : getFilters();
  var advFilters    = _activeFilterTab==='advanced' ? getAdvFilters() : [];
  if(_bridge) _bridge.runVisualQuery(
    JSON.stringify(getSelectedSeries()),
    document.getElementById('b-groupby').value,
    JSON.stringify(simpleFilters),
    JSON.stringify(advFilters)
  );
}

function getFreeQuerySeriesPKs(){
  var sel = document.getElementById('fqb-series-sel');
  if(!sel) return [];
  var pks=[];
  for(var i=0;i<sel.options.length;i++){
    if(sel.options[i].selected&&sel.options[i].value) pks.push(parseInt(sel.options[i].value));
  }
  return pks;
}

function receiveQueryResult(data, resultCount){
  _resetLegendOverrides();
  SERIES_REGISTRY=[{pk:0,name:'Query Result',color:'#39A650',data:data,machine:'',material:''}];
  document.getElementById('result-info').textContent=resultCount+' rows found';
  var btn=document.getElementById('btn-run-query');btn.disabled=false;btn.textContent='▶ Run Query';
  renderSeriesPills();buildInfobox();refreshAllCharts();
}

function receiveFreeQueryResult(rows, resultCount, cfg){
  // Free Query: Scatter/Bar mit X/Y/Color aus freien Feldern
  document.getElementById('result-info').textContent=resultCount+' rows';
  var btn=document.getElementById('btn-run-query');btn.disabled=false;btn.textContent='▶ Run Query';
  // Achsentitel aus cfg extrahieren (table::field → field)
  function _fqbLabel(fieldStr){
    if(!fieldStr) return '';
    var p=fieldStr.split('::');
    return p.length>1 ? p[1] : fieldStr;
  }
  _fqbXTitle     = _fqbLabel(cfg.xField);
  _fqbYTitle     = _fqbLabel(cfg.yField);
  _fqbColorTitle = _fqbLabel(cfg.colorField);
  _fqbLabelTitle = _fqbLabel(cfg.labelField);
  if(!rows||!rows.length){ refreshAllCharts(); return; }
  // Chart direkt als Scatter aufbauen
  var xKey   = '__fqb_x';
  var yKey   = '__fqb_y';
  var colorKey = cfg.colorField ? '__fqb_color' : null;
  var labelKey = cfg.labelField ? '__fqb_label' : null;
  // Daten normalisieren
  var data = rows.map(function(r){
    // jet_name = Color-Feld für Legende, Label separat für Punkt-Beschriftung
    var d = {trial_id:0, trial_nr:0,
             jet_name: colorKey ? (r['__fqb_color']||'?') : (labelKey ? '' : '?')};
    var _rawX=r['__fqb_x']; var _numX=parseFloat(_rawX); d[xKey]=isNaN(_numX)?(_rawX||''):_numX;
    d[yKey]   = parseFloat(r['__fqb_y']);
    if(colorKey) d[colorKey] = r['__fqb_color']||'';
    if(labelKey) d[labelKey] = r['__fqb_label']||'';
    return d;
  });
  // Daten im Block-State speichern
  var blockIdx = (cfg._blockIdx !== undefined) ? parseInt(cfg._blockIdx) : _activeFqbBlockIdx;
  if(!_blockFqbStates[blockIdx]) _blockFqbStates[blockIdx] = {};
  _blockFqbStates[blockIdx].data   = data;
  _blockFqbStates[blockIdx].xKey      = xKey;
  _blockFqbStates[blockIdx].yKey      = yKey;
  _blockFqbStates[blockIdx].xTitle    = _fqbXTitle;
  _blockFqbStates[blockIdx].yTitle    = _fqbYTitle;
  _blockFqbStates[blockIdx].chartTitle = cfg.chartTitle || '';
  // Chart-State für diesen Block setzen (Chart-Typ beibehalten)
  var s = getState(blockIdx);
  if(s.blockType !== 'image'){
    // Chart-Typ aus FQB übernehmen
    var fqbType = cfg.chartType || 'scatter';
    s.chartType = fqbType;
    s.xField = xKey;
    s.yKey   = yKey;
    // Z-Feld für 3D/Heatmap
    if(cfg.zField && (fqbType==='3d'||fqbType==='heat')){
      s.zField = '__fqb_z';
    }
    chartStates[blockIdx] = s;
  }
  // SERIES_REGISTRY temporär auf diesen Block setzen und nur diesen Chart rendern
  SERIES_REGISTRY = [{pk:0, name:'Free Query', color:'#39A650', data:data, machine:'', material:''}];
  renderSeriesPills(); buildInfobox();
  // Nur den aktiven Block neu rendern
  if(document.getElementById('chart_'+blockIdx)){
    updateChart(blockIdx);
  } else {
    rebuildGrid();
  }
}

function populateBuilderSeriesList(list){
  _allSeriesForBuilder=list;
  var sel=document.getElementById('b-series');
  sel.innerHTML=list.map(function(s){return'<option value="'+s.pk+'">'+s.name+'</option>';}).join('');
}

// ── Slicer ────────────────────────────────────────────────────────────────────
var slicerState = {air_pressure:[],overfeed:[],speed:[],jet_name:[],yarn_name:[],machine_name:[]};
function slicerMatch(d){
  var fields=['air_pressure','overfeed','speed'];
  for(var i=0;i<fields.length;i++){
    var f=fields[i],sel=slicerState[f];
    if(sel.length===0)continue;
    if(sel.indexOf(String(d[f]))===-1)return false;
  }
  if(slicerState.jet_name.length>0&&slicerState.jet_name.indexOf(d.real_jet||d.jet_name||'Unknown')===-1)return false;
  if(slicerState.yarn_name.length>0&&slicerState.yarn_name.indexOf(d.yarn_name||'Unknown')===-1)return false;
  if(slicerState.machine_name.length>0&&slicerState.machine_name.indexOf(d.machine_name||'')===-1)return false;
  // Drill-Down Filter
  for(var dk in _drillFilters){
    if(!_drillFilters.hasOwnProperty(dk))continue;
    var dv=_drillFilters[dk];
    if(dv===null||dv===undefined)continue;
    if(dk === '__drill_jet'){
      // Jet-Filter: gegen jet_name in DATA-Row prüfen
      if(String(d.jet_name||'Unknown') !== String(dv)) return false;
    } else {
      if(String(d[dk])!==String(dv))return false;
    }
  }
  return true;
}

// ── Drill-Down: Trial-Level Traces (kein Aggregat) ───────────────────────────
function buildTraces2dDrill(yKey){
  // Zeigt jeden gefilterten Versuch als eigenen Balken (x = Versuchsnummer)
  var rows = [];
  SERIES_REGISTRY.forEach(function(s){
    s.data.forEach(function(d){
      if(!slicerMatch(d)) return;
      var yVal = d[yKey];
      if(yVal === null || yVal === undefined || yVal === 0) return;
      var jet = SERIES_REGISTRY.length > 1 ? s.pk + '::' + (d.jet_name||'Unknown') : (d.jet_name||'Unknown');
      rows.push({jet: jet, trial_nr: d.trial_nr, yVal: yVal, row: d});
    });
  });
  if(rows.length === 0) return [];

  var jetGroups = {};
  rows.forEach(function(r){
    if(!jetGroups[r.jet]) jetGroups[r.jet] = [];
    jetGroups[r.jet].push(r);
  });

  var yDef = (typeof Y_AXES !== 'undefined') ? (Y_AXES.find(function(a){return a.key===yKey;})||{unit:'',title:yKey}) : {unit:'',title:yKey};

  return Object.keys(jetGroups).map(function(jet){
    var pts = jetGroups[jet].sort(function(a,b){ return a.trial_nr - b.trial_nr; });
    var col = getJetColor(jet);
    return {
      type: 'bar',
      name: getLegendLabel(jet),
      x: pts.map(function(p){ return 'V' + p.trial_nr; }),
      y: pts.map(function(p){ return p.yVal; }),
      text: pts.map(function(p){ return p.yVal.toFixed(2); }),
      textposition: 'inside',
      insidetextanchor: 'middle',
      textfont: { size: 11, color: _textColorFor(col) },
      hovertext: pts.map(function(p){
        var d = p.row;
        var lines = ['<b>V' + p.trial_nr + '</b>'];
        lines.push(yDef.title + ': <b>' + p.yVal.toFixed(3) + '</b>' + (yDef.unit ? ' ' + yDef.unit : ''));
        if(d.jet_name)     lines.push('Jet: ' + d.jet_name);
        if(d.air_pressure) lines.push('Air: ' + d.air_pressure + ' bar');
        if(d.overfeed)     lines.push('OF: ' + d.overfeed + ' %');
        if(d.speed)        lines.push('Speed: ' + d.speed + ' m/min');
        if(d.yarn_name)    lines.push('Yarn: ' + d.yarn_name);
        return lines.join('<br>');
      }),
      hoverinfo: 'text',
      marker: { color: col, line: { color: 'rgba(0,0,0,0.12)', width: 1 } },
      showlegend: true,
    };
  });
}

// ── Aggregation ───────────────────────────────────────────────────────────────
function aggregate2d(xField,yKey){
  var aggMap={};
  SERIES_REGISTRY.forEach(function(s){
    s.data.forEach(function(d){
      if(!slicerMatch(d))return;
      var jet=SERIES_REGISTRY.length>1?s.pk+'::'+(d.jet_name||'Unknown'):(d.jet_name||'Unknown');
      var xVal=d[xField],yVal=d[yKey];
      if(xVal===null||xVal===undefined||xVal==='')return;
      if(yVal===null||yVal===undefined||yVal===0)return;
      var key=jet+'||'+xVal;
      if(!aggMap[key])aggMap[key]={jet:jet,x:xVal,vals:[],n:0};
      aggMap[key].vals.push(yVal);aggMap[key].n++;
    });
  });
  var result=Object.values(aggMap).filter(function(a){return a.n>0;}).map(function(a){
    var n=a.n,sum=a.vals.reduce(function(s,v){return s+v;},0),avg=sum/n,sd=0;
    if(n>1){var sq=a.vals.reduce(function(s,v){return s+(v-avg)*(v-avg);},0);sd=Math.sqrt(sq/(n-1));}
    var mn=Math.min.apply(null,a.vals),mx=Math.max.apply(null,a.vals);
    return{jet:a.jet,x:a.x,z:avg,sd:sd,n:n,min:mn,max:mx};
  });
  _lastMaxN=result.reduce(function(m,d){return Math.max(m,d.n);},1);
  return result;
}

function aggregate3d(xField,zField,yKey){
  var aggMap={};
  SERIES_REGISTRY.forEach(function(s){
    s.data.forEach(function(d){
      if(!slicerMatch(d))return;
      var jet=SERIES_REGISTRY.length>1?s.pk+'::'+(d.jet_name||'Unknown'):(d.jet_name||'Unknown');
      var xVal=d[xField],zVal=d[zField],yVal=d[yKey];
      if(xVal===null||xVal===undefined||zVal===null||zVal===undefined)return;
      if(yVal===null||yVal===undefined||yVal===0)return;
      var key=jet+'||'+xVal+'||'+zVal;
      if(!aggMap[key])aggMap[key]={jet:jet,x:xVal,z:zVal,vals:[],n:0};
      aggMap[key].vals.push(yVal);aggMap[key].n++;
    });
  });
  return Object.values(aggMap).filter(function(a){return a.n>0;}).map(function(a){
    var n=a.n,sum=a.vals.reduce(function(s,v){return s+v;},0),avg=sum/n,sd=0;
    if(n>1){var sq=a.vals.reduce(function(s,v){return s+(v-avg)*(v-avg);},0);sd=Math.sqrt(sq/(n-1));}
    return{jet:a.jet,x:a.x,z:a.z,y:avg,sd:sd,n:n};
  });
}

// ── Jet helpers ───────────────────────────────────────────────────────────────
// ── Legend order + colour overrides (session-only, reset on next query) ────────
var _jetOrderOverride = [];   // [] = use natural order
var _jetColorOverride = {};   // {jetKey: '#rrggbb'}

function _resetLegendOverrides(){
  _jetOrderOverride = [];
  _jetColorOverride = {};
}

function getAllJetNames(){
  var names=[];
  SERIES_REGISTRY.forEach(function(s){
    s.data.forEach(function(d){
      var j=SERIES_REGISTRY.length>1?s.pk+'::'+(d.jet_name||'Unknown'):(d.jet_name||'Unknown');
      if(names.indexOf(j)===-1)names.push(j);
    });
  });
  // Apply order override: keep only names present, then append any new ones
  if(_jetOrderOverride.length){
    var ordered=_jetOrderOverride.filter(function(k){return names.indexOf(k)!==-1;});
    names.forEach(function(k){if(ordered.indexOf(k)===-1)ordered.push(k);});
    return ordered;
  }
  return names;
}
function getJetColor(jetKey){
  // Colour override (set via Legend modal) takes priority
  if(_jetColorOverride[jetKey]) return _jetColorOverride[jetKey];

  // Position-based colour: index in getAllJetNames() determines colour
  // → Position 1 always green, position 2 always grey, etc.
  // Use a temporary list without override to avoid recursion
  var allJets=[];
  SERIES_REGISTRY.forEach(function(s){
    s.data.forEach(function(d){
      var j=SERIES_REGISTRY.length>1?s.pk+'::'+(d.jet_name||'Unknown'):(d.jet_name||'Unknown');
      if(allJets.indexOf(j)===-1)allJets.push(j);
    });
  });
  // Apply order override if set
  if(_jetOrderOverride.length){
    var ordered=_jetOrderOverride.filter(function(k){return allJets.indexOf(k)!==-1;});
    allJets.forEach(function(k){if(ordered.indexOf(k)===-1)ordered.push(k);});
    allJets=ordered;
  }
  var posIdx=allJets.indexOf(jetKey);
  if(posIdx<0)posIdx=0;

  if(SERIES_REGISTRY.length===1){
    // Single series: position in ordered list → PALETTE colour
    return getColor(posIdx);
  }

  // Multiple series: use series colour as base, position within series for lightness
  var parts=jetKey.split('::'),seriesPk=parts.length>1?parseInt(parts[0]):SERIES_REGISTRY[0].pk;
  var sIdx=SERIES_REGISTRY.findIndex(function(s){return s.pk===seriesPk;});
  if(sIdx<0)sIdx=0;
  var series=SERIES_REGISTRY[sIdx];
  var rgb=hexRgb(series.color);
  var steps=[1.0, 0.72, 0.50, 0.35, 0.85, 0.62];
  var f=steps[posIdx%steps.length];
  var mix=0.92;
  var r=Math.round(Math.min(255,(rgb[0]*255*f)*mix + 255*(1-mix)));
  var g=Math.round(Math.min(255,(rgb[1]*255*f)*mix + 255*(1-mix)));
  var b=Math.round(Math.min(255,(rgb[2]*255*f)*mix + 255*(1-mix)));
  return 'rgb('+r+','+g+','+b+')';
}
function getLegendLabel(jetKey){
  if(SERIES_REGISTRY.length===1)return jetKey;
  var parts=jetKey.split('::'),spk=parseInt(parts[0]),jname=parts[1];
  var series=SERIES_REGISTRY.find(function(s){return s.pk===spk;});
  return jname+' ['+(series?series.name:spk)+']';
}

// ── Y/X title helpers ─────────────────────────────────────────────────────────
// FQB: aktiver Block-Index
var _activeFqbBlockIdx = 0;
var _expandedChartIdx = null;

function _expandChart(idx){
  _expandedChartIdx = idx;
  var total=Math.max(1,parseInt(document.getElementById('inp-count').value)||1);
  for(var i=0;i<total;i++){
    var el=document.getElementById('chart_'+i);
    var card=el?el.closest('.chart-card'):null;
    if(!card) card=document.getElementById('image-card-'+i);
    if(!card) continue;
    if(i===idx){ card.classList.add('expanded'); (function(ci){setTimeout(function(){Plotly.relayout('chart_'+ci,{autosize:true});},50);})(i); }
    else { card.style.display='none'; }
  }
  var infoSlot=document.getElementById('infobox-slot');
  if(infoSlot) infoSlot.style.display='none';
}

function _collapseChart(){
  if(_expandedChartIdx===null) return;
  var total=Math.max(1,parseInt(document.getElementById('inp-count').value)||1);
  for(var i=0;i<total;i++){
    var el=document.getElementById('chart_'+i);
    var card=el?el.closest('.chart-card'):null;
    if(!card) card=document.getElementById('image-card-'+i);
    if(!card) continue;
    card.classList.remove('expanded');
    card.style.display='';
  }
  var infoSlot=document.getElementById('infobox-slot');
  if(infoSlot) infoSlot.style.display='';
  _expandedChartIdx=null;
  // Plotly muss die neue (kleinere) Grösse kennen
  setTimeout(function(){
    var total=Math.max(1,parseInt(document.getElementById('inp-count').value)||1);
    for(var i=0;i<total;i++){
      var el=document.getElementById('chart_'+i);
      if(el) Plotly.relayout(el, {autosize:true});
    }
  }, 50);
}

var _expandedChartIdx = null;

function _expandChart(idx){
  _expandedChartIdx = idx;
  var total=Math.max(1,parseInt(document.getElementById('inp-count').value)||1);
  for(var i=0;i<total;i++){
    var el=document.getElementById('chart_'+i);
    var card=el?el.closest('.chart-card'):null;
    if(!card){card=document.getElementById('image-card-'+i);}
    if(!card) continue;
    if(i===idx){ card.classList.add('expanded'); setTimeout(function(ci){return function(){Plotly.relayout('chart_'+ci,{autosize:true});};}(i),50); }
    else { card.style.display='none'; }
  }
  var infoSlot=document.getElementById('infobox-slot');
  if(infoSlot) infoSlot.style.display='none';
}

function _collapseChart(){
  if(_expandedChartIdx===null) return;
  var total=Math.max(1,parseInt(document.getElementById('inp-count').value)||1);
  for(var i=0;i<total;i++){
    var el=document.getElementById('chart_'+i);
    var card=el?el.closest('.chart-card'):null;
    if(!card){card=document.getElementById('image-card-'+i);}
    if(!card) continue;
    card.classList.remove('expanded');
    card.style.display='';
  }
  var infoSlot=document.getElementById('infobox-slot');
  if(infoSlot) infoSlot.style.display='';
  _expandedChartIdx=null;
  // Plotly muss die neue (kleinere) Grösse kennen
  setTimeout(function(){
    var total=Math.max(1,parseInt(document.getElementById('inp-count').value)||1);
    for(var i=0;i<total;i++){
      var el=document.getElementById('chart_'+i);
      if(el) Plotly.relayout(el, {autosize:true});
    }
  }, 50);
}
// Pro Block: {fqbConfig, fqbData}
var _blockFqbStates = {};

function _syncFqbBlockSelector(){
  var sel = document.getElementById('fqb-block-selector');
  if(!sel) return;
  var total = Math.max(1, parseInt(document.getElementById('inp-count').value)||1);
  var cur = _activeFqbBlockIdx;
  sel.innerHTML = '';
  for(var i=0; i<total; i++){
    var opt = document.createElement('option');
    opt.value = i;
    opt.textContent = 'Chart ' + (i+1);
    if(i===cur) opt.selected = true;
    sel.appendChild(opt);
  }
}

function _saveFqbStateForBlock(idx){
  // Aktuellen Builder-State für Block speichern
  var cfg = getFreeQueryConfig ? getFreeQueryConfig() : null;
  if(!cfg||!cfg.baseTable) return;
  if(!_blockFqbStates[idx]) _blockFqbStates[idx] = {};
  _blockFqbStates[idx].config = cfg;
}

function _loadFqbStateForBlock(idx){
  var state = _blockFqbStates[idx];
  if(!state||!state.config) return;
  var cfg = state.config;
  // Base Table
  var bt = document.getElementById('fqb-base-table');
  if(bt && cfg.baseTable) bt.value = cfg.baseTable;
  // Trigger change um JOINs + Felder zu laden
  if(bt) bt.dispatchEvent(new Event('change'));
  // Nach kurzer Verzögerung Rest setzen
  setTimeout(function(){
    // Joins neu aufbauen
    _fqbActiveTables = [cfg.baseTable];
    (cfg.joinTables||[]).forEach(function(jt){ _fqbActiveTables.push(jt); });
    _fqbRenderJoinPills();
    _fqbUpdateJoinSelect();
    _fqbUpdateAxes();
    // Achsen setzen
    setTimeout(function(){
      var fx=document.getElementById('fqb-x'),fy=document.getElementById('fqb-y'),
          fc=document.getElementById('fqb-color'),fl=document.getElementById('fqb-label');
      var fct=document.getElementById('fqb-chart-type');
      if(fct&&cfg.chartType) fct.value=cfg.chartType;
      _fqbUpdateFieldVisibility();
      var ftitle=document.getElementById('fqb-chart-title');
      if(ftitle) ftitle.value=cfg.chartTitle||'';
      var gbEl=document.getElementById('fqb-groupby');
      if(gbEl&&cfg.groupBy) gbEl.value=cfg.groupBy;
      var seSel=document.getElementById('fqb-series-sel');
      if(seSel&&cfg.seriesPKs&&cfg.seriesPKs.length){
        for(var si=0;si<seSel.options.length;si++){
          seSel.options[si].selected=cfg.seriesPKs.indexOf(parseInt(seSel.options[si].value))!==-1;
        }
      }
      if(fx&&cfg.xField) fx.value=cfg.xField;
      if(fy&&cfg.yField) fy.value=cfg.yField;
      var fz=document.getElementById('fqb-z');
      if(fz) fz.value=cfg.zField||'';
      if(fc) fc.value=cfg.colorField||'';
      if(fl) fl.value=cfg.labelField||'';
      // Filter neu aufbauen
      document.getElementById('fqb-filter-rows').innerHTML='';
      _fqbFilterCnt=0;
      (cfg.filters||[]).forEach(function(f){ _fqbAddFilterRow(f); });
      // Limit
      var lim=document.getElementById('fqb-limit');
      if(lim) lim.value=cfg.limit||500;
      _fqbUpdatePreview();
    }, 150);
  }, 100);
}

// FQB Achsentitel (gesetzt von receiveFreeQueryResult)
var _fqbXTitle = '', _fqbYTitle = '', _fqbColorTitle = '', _fqbLabelTitle = '', _fqbChartTitle = '';

function getYTitle(yKey){
  if(yKey==='__fqb_y') return _fqbYTitle || '__fqb_y';
  if(yKey==='__fqb_x') return _fqbXTitle || '__fqb_x';
  for(var i=0;i<Y_AXES.length;i++){if(Y_AXES[i].key===yKey){var y=Y_AXES[i];return y.unit?y.title+' ('+y.unit+')':y.title;}}
  if(yKey.indexOf('free:')===0){var p=yKey.split(':');return p[2]+' ('+p[1]+')';}
  return yKey;
}
function getYTitleShort(yKey){
  if(yKey==='__fqb_y') return _fqbYTitle || '__fqb_y';
  if(yKey==='__fqb_x') return _fqbXTitle || '__fqb_x';
  for(var i=0;i<Y_AXES.length;i++){if(Y_AXES[i].key===yKey)return Y_AXES[i].title;}
  if(yKey.indexOf('free:')===0){var p=yKey.split(':');return p[2];}
  return yKey;
}

// ── 2D Traces ─────────────────────────────────────────────────────────────────
var showSD=true, showMinMax=false, selectedJet=null, _lastNJets=1, _lastMaxN=1;

function buildTraces2d(xField,yKey){
  var xAxisDef=X_AXES.filter(function(a){return a.key===xField;})[0]||X_AXES[0];
  var aggData=aggregate2d(xField,yKey);
  var allJets=getAllJetNames();
  var activeJets=allJets.filter(function(j){return aggData.some(function(d){return d.jet===j;});});
  _lastNJets=activeJets.length;
  var hasHL=selectedJet!==null;
  return activeJets.map(function(jet){
    var pts=aggData.filter(function(d){return d.jet===jet;}).sort(function(a,b){var na=parseFloat(a.x),nb=parseFloat(b.x);return(!isNaN(na)&&!isNaN(nb))?na-nb:String(a.x).localeCompare(String(b.x));});
    var isHL=!hasHL||jet===selectedJet;
    var col=getJetColor(jet);
    var _nX=aggData.map(function(d){return d.x;}).filter(function(v,i,a){return a.indexOf(v)===i;}).length;
    var _bargap=_lastNJets<=2?0.65:_lastNJets<=4?0.55:_lastNJets<=6?0.35:0.20;
    var _bgap=_lastNJets<=2?0.25:_lastNJets<=4?0.15:0.08;
    var _chartEl=document.getElementById('chart_0');
    var _chartW=(_chartEl?_chartEl.offsetWidth:700)-72;
    var _groupW=_nX>0?_chartW*(1-_bargap)/_nX:_chartW;
    var _barW=_lastNJets>0?_groupW*(1-_bgap)/_lastNJets:_groupW;
    // Textstufen: >=52 horizontal+n | >=32 vertikal+n | >=18 vertikal ohne n | <18 nichts
    var _textMode=_barW>=52?'h_n':_barW>=32?'v_n':_barW>=18?'v':'none';
    var _textAngle=(_textMode==='v_n'||_textMode==='v')?-90:0;
    return{
      type:'bar',name:getLegendLabel(jet),
      x:pts.map(function(d){return String(d.x);}),
      y:pts.map(function(d){return d.z;}),
      text:pts.map(function(d){
        if(_textMode==='none')return '';
        var val=d.z.toFixed(1);
        if(_textMode==='h_n')return val+(d.n>1?'<br>(n='+d.n+')':'');
        if(_textMode==='v_n')return val+(d.n>1?' ('+d.n+')':'');
        return val;
      }),
      textposition:_textMode==='none'?'none':'inside',
      insidetextanchor:'middle',
      textangle:_textAngle,
      textfont:{size:_barW>60?13:_barW>45?11:_barW>32?10:9,color:isHL?_textColorFor(getJetColor(jet)):'rgba(0,0,0,0)'},
      hovertext:pts.map(function(d){return'<b>'+getLegendLabel(jet)+'</b><br>'+xAxisDef.title+': '+d.x+'<br>Ø: '+d.z.toFixed(2)+(d.n>1?'<br>n='+d.n:'')+(d.sd>0?'<br>SD='+d.sd.toFixed(2):'');}),
      hoverinfo:'text',opacity:isHL?1:0.6,
      showlegend:true,
      marker:{color:col,line:{color:'rgba(0,0,0,0.12)',width:isHL?1:0}},
      error_y:{
        type:'data',
        array:     showMinMax ? pts.map(function(d){return d.max-d.z;}) : pts.map(function(d){return d.sd;}),
        arrayminus:showMinMax ? pts.map(function(d){return d.z-d.min;}) : pts.map(function(d){return d.sd;}),
        visible:isHL&&(showMinMax||(showSD&&_lastMaxN>1)),
        color:'rgba(0,0,0,0.75)',thickness:3,width:12,symmetric:!showMinMax,
      },
    };
  });
}

// ── 3D Traces ─────────────────────────────────────────────────────────────────
function makeBar3d(cx,cy,h,hwx,hwy,color,name,ht,lg,sl,dimmed){
  var op=dimmed?0.2:0.85,x0=cx-hwx,x1=cx+hwx,y0=cy-hwy,y1=cy+hwy;
  var xs=[x0,x1,x1,x0,x0,x1,x1,x0],ys=[y0,y0,y1,y1,y0,y0,y1,y1],zs=[0,0,0,0,h,h,h,h];
  return{type:'mesh3d',x:xs,y:ys,z:zs,i:[0,0,4,4,0,0,1,1,2,2,3,3],j:[1,2,5,6,4,5,5,6,6,7,7,4],k:[2,3,6,7,5,1,6,2,7,3,4,0],color:color,opacity:op,flatshading:true,lighting:{ambient:0.7,diffuse:0.5},lightposition:{x:1000,y:500,z:2000},name:name,legendgroup:lg,showlegend:sl,hovertext:ht,hoverinfo:'text',hoverlabel:{bgcolor:'white',bordercolor:color,font:{size:11}}};
}
function buildTraces3d(xField,zField,yKey){
  var xAxisDef=X_AXES.filter(function(a){return a.key===xField;})[0]||X_AXES[0];
  var zAxisDef=X_AXES.filter(function(a){return a.key===zField;})[0]||X_AXES[0];
  var aggData=aggregate3d(xField,zField,yKey);if(!aggData.length)return[];
  var allJets=getAllJetNames(),activeJets=allJets.filter(function(j){return aggData.some(function(d){return d.jet===j;});}),nJets=activeJets.length,hasHL=selectedJet!==null;
  var allX=aggData.map(function(d){return d.x;}),allZ=aggData.map(function(d){return d.z;});
  function uniq(v){return v.filter(function(x,i,a){return a.indexOf(x)===i;}).sort(function(a,b){return a-b;});}
  function minStep(u){if(u.length<2)return Math.max(Math.abs(u[0]||1)*0.02,0.01);var s=Infinity;for(var i=1;i<u.length;i++)s=Math.min(s,u[i]-u[i-1]);return s;}
  var xStep=minStep(uniq(allX)),zStep=minStep(uniq(allZ)),nE=Math.max(nJets,1);
  var gx=xStep*0.20,gz=zStep*0.20,hwx=gx/(2*nE),hwy=gz/(2*nE),offR=gx/nE;
  function getOff(ji){if(nJets<=1)return{dx:0,dy:0};var a=(2*Math.PI*ji)/nJets;return{dx:Math.cos(a)*offR,dy:Math.sin(a)*offR*0.6};}
  var traces=[],shown={};
  aggData.forEach(function(d){
    var ji=activeJets.indexOf(d.jet);if(ji<0)return;
    var color=getJetColor(d.jet),off=getOff(ji),isHL=!hasHL||d.jet===selectedJet,showL=!shown[d.jet];shown[d.jet]=true;
    var ht='<b>'+getLegendLabel(d.jet)+'</b><br>'+xAxisDef.title+': '+d.x+'<br>'+zAxisDef.title+': '+d.z+'<br>Ø '+getYTitle(yKey)+': '+d.y.toFixed(2)+(d.n>1?'<br>n='+d.n:'')+(d.sd>0?'<br>SD='+d.sd.toFixed(2):'');
    traces.push(makeBar3d(d.x+off.dx,d.z+off.dy,d.y,hwx*0.45,hwy*0.45,color,getLegendLabel(d.jet),ht,d.jet,showL,!isHL));
  });
  return traces;
}

// ── Rohdaten (für Box + Scatter) ─────────────────────────────────────────────
function getRawData(xField,yKey){
  var out=[];
  SERIES_REGISTRY.forEach(function(s){
    s.data.forEach(function(d){
      if(!slicerMatch(d))return;
      var xVal=d[xField],yVal=d[yKey];
      if(xVal===null||xVal===undefined||xVal==='')return;
      if(yVal===null||yVal===undefined)return;
      var jet=SERIES_REGISTRY.length>1?s.pk+'::'+(d.jet_name||'Unknown'):(d.jet_name||'Unknown');
      out.push({jet:jet,x:xVal,y:yVal,trial_nr:d.trial_nr,'__fqb_label':d['__fqb_label']||'','__fqb_color':d['__fqb_color']||''});
    });
  });
  return out;
}

// ── Stacked Bar ───────────────────────────────────────────────────────────────
function buildTracesStacked(xField,yKey){
  var aggData=aggregate2d(xField,yKey);
  var allJets=getAllJetNames();
  var activeJets=allJets.filter(function(j){return aggData.some(function(d){return d.jet===j;});});
  _lastNJets=activeJets.length;
  var hasHL=selectedJet!==null;
  return activeJets.map(function(jet){
    var pts=aggData.filter(function(d){return d.jet===jet;}).sort(function(a,b){var na=parseFloat(a.x),nb=parseFloat(b.x);return(!isNaN(na)&&!isNaN(nb))?na-nb:String(a.x).localeCompare(String(b.x));});
    var isHL=!hasHL||jet===selectedJet;
    var col=getJetColor(jet);
    return{
      type:'bar',name:getLegendLabel(jet),
      x:pts.map(function(d){return String(d.x);}),
      y:pts.map(function(d){return d.z;}),
      text:pts.map(function(d){return d.z.toFixed(1);}),
      textposition:'inside',insidetextanchor:'middle',
      textfont:{size:10,color:'#fff'},
      hovertext:pts.map(function(d){return'<b>'+getLegendLabel(jet)+'</b><br>Ø: '+d.z.toFixed(2)+(d.n>1?'<br>n='+d.n:'');}),
      hoverinfo:'text',opacity:isHL?1:0.6,
      marker:{color:col,line:{color:'rgba(0,0,0,0.1)',width:0.5}},
    };
  });
}

// ── Line ──────────────────────────────────────────────────────────────────────
function buildTracesLine(xField,yKey){
  var aggData=aggregate2d(xField,yKey);
  var allJets=getAllJetNames();
  var activeJets=allJets.filter(function(j){return aggData.some(function(d){return d.jet===j;});});
  _lastNJets=activeJets.length;
  var hasHL=selectedJet!==null;
  return activeJets.map(function(jet){
    var pts=aggData.filter(function(d){return d.jet===jet;}).sort(function(a,b){return parseFloat(a.x)-parseFloat(b.x)||String(a.x).localeCompare(String(b.x));});
    var isHL=!hasHL||jet===selectedJet;
    var col=getJetColor(jet);
    return{
      type:'scatter',mode:'lines+markers',name:getLegendLabel(jet),
      x:pts.map(function(d){return d.x;}),
      y:pts.map(function(d){return d.z;}),
      line:{color:col,width:isHL?2:1},
      marker:{color:col,size:isHL?6:4,line:{color:'rgba(0,0,0,0.2)',width:1}},
      hovertext:pts.map(function(d){return'<b>'+getLegendLabel(jet)+'</b><br>Ø: '+d.z.toFixed(2)+(d.n>1?'<br>n='+d.n:'')+(d.sd>0?'<br>SD='+d.sd.toFixed(2):'');}),
      hoverinfo:'text',opacity:isHL?1:0.6,
      error_y:{
        type:'data',
        array:     showMinMax ? pts.map(function(d){return d.max-d.z;}) : pts.map(function(d){return d.sd;}),
        arrayminus:showMinMax ? pts.map(function(d){return d.z-d.min;}) : pts.map(function(d){return d.sd;}),
        visible:isHL&&(showMinMax||(showSD&&_lastMaxN>1)),
        color:col,thickness:2,width:8,symmetric:!showMinMax,
      },
    };
  });
}

// ── Scatter ───────────────────────────────────────────────────────────────────
function buildTracesScatter(xField,yKey){
  var raw=getRawData(xField,yKey);
  var allJets=getAllJetNames();
  var activeJets=allJets.filter(function(j){return raw.some(function(d){return d.jet===j;});});
  _lastNJets=activeJets.length;
  var hasHL=selectedJet!==null;
  var isFqb = xField==='__fqb_x';
  var xAxisDef = isFqb ? {title:_fqbXTitle} : (X_AXES.filter(function(a){return a.key===xField;})[0]||X_AXES[0]);
  return activeJets.map(function(jet){
    var pts=raw.filter(function(d){return d.jet===jet;});
    var isHL=!hasHL||jet===selectedJet;
    var col=getJetColor(jet);
    return{
      type:'scatter',mode:'markers',name:getLegendLabel(jet),
      x:pts.map(function(d){return d.x;}),
      y:pts.map(function(d){return d.y;}),
      text:isFqb&&_fqbLabelTitle?pts.map(function(d){return d['__fqb_label']||'';}):[],
      mode:(isFqb&&_fqbLabelTitle)?'markers+text':'markers',
      textposition:'top center',
      textfont:{size:9,color:'#555'},
      marker:{color:isFqb&&_fqbColorTitle?pts.map(function(d,i){
        // Farbe nach Color-Feld
        var cv=d['__fqb_color']||'';
        var ci=activeJets.indexOf(cv);
        return ci>=0?getJetColor(cv):col;
      }):col,size:isHL?7:5,opacity:isHL?0.85:0.55,line:{color:'rgba(0,0,0,0.15)',width:1}},
      hovertext:pts.map(function(d){
        var ht='<b>'+(d['__fqb_label']||d.jet_name||getLegendLabel(jet))+'</b>';
        ht+='<br>'+xAxisDef.title+': '+(d.x!==null&&d.x!==undefined?d.x:'—');
        ht+='<br>'+_fqbYTitle+': '+(d.y!==null&&d.y!==undefined?d.y.toFixed?d.y.toFixed(3):d.y:'—');
        if(_fqbColorTitle&&d['__fqb_color']) ht+='<br>'+_fqbColorTitle+': '+d['__fqb_color'];
        return ht;
      }),
      hoverinfo:'text',
    };
  });
}

// ── Box Plot ──────────────────────────────────────────────────────────────────
function buildTracesBox(xField,yKey){
  var raw=getRawData(xField,yKey);
  var allJets=getAllJetNames();
  var activeJets=allJets.filter(function(j){return raw.some(function(d){return d.jet===j;});});
  _lastNJets=activeJets.length;
  var hasHL=selectedJet!==null;
  return activeJets.map(function(jet){
    var pts=raw.filter(function(d){return d.jet===jet;});
    var isHL=!hasHL||jet===selectedJet;
    var col=getJetColor(jet);
    return{
      type:'box',name:getLegendLabel(jet),
      x:pts.map(function(d){return String(d.x);}),
      y:pts.map(function(d){return d.y;}),
      boxpoints:'outliers',
      marker:{color:col,size:4,opacity:isHL?0.7:0.45},
      line:{color:col,width:isHL?1.5:0.8},
      fillcolor:isHL?col.replace('rgb','rgba').replace(')',',0.25)'):'rgba(200,200,200,0.1)',
      opacity:isHL?1:0.6,
      hoverinfo:'y+name',
    };
  });
}

// ── Heatmap ───────────────────────────────────────────────────────────────────
function buildTracesHeatmap(xField,yKey){
  var aggData=aggregate2d(xField,yKey);
  var allJets=getAllJetNames();
  var activeJets=allJets.filter(function(j){return aggData.some(function(d){return d.jet===j;});});
  var allX=aggData.map(function(d){return d.x;}).filter(function(v,i,a){return a.indexOf(v)===i;}).sort(function(a,b){return parseFloat(a)-parseFloat(b)||String(a).localeCompare(String(b));});
  var z=activeJets.map(function(jet){
    return allX.map(function(x){
      var pt=aggData.find(function(d){return d.jet===jet&&String(d.x)===String(x);});
      return pt?pt.z:null;
    });
  });
  var text=activeJets.map(function(jet){
    return allX.map(function(x){
      var pt=aggData.find(function(d){return d.jet===jet&&String(d.x)===String(x);});
      return pt?pt.z.toFixed(1):'';
    });
  });
  return[{
    type:'heatmap',
    x:allX.map(String),
    y:activeJets.map(getLegendLabel),
    z:z,
    text:text,
    texttemplate:'%{text}',
    colorscale:[['0','#eef4fb'],['0.5','#39A650'],['1','#1D3557']],
    colorbar:{thickness:12,len:0.8,tickfont:{size:10}},
    hoverongaps:false,
    hovertemplate:'<b>%{y}</b><br>X: %{x}<br>Ø: %{z:.2f}<extra></extra>',
    showscale:true,
  }];
}

// ── Layouts für neue Typen ────────────────────────────────────────────────────
function makeLayoutStacked(xField,yKey,nJets){
  var base=makeLayout2d(xField,yKey,nJets);
  base.barmode='stack';
  return base;
}
function makeLayoutLine(xField,yKey){
  var xDef=X_AXES.filter(function(a){return a.key===xField;})[0]||X_AXES[0];
  var xTitle=xDef.unit?xDef.title+' ('+xDef.unit+')':xDef.title;
  return{
    title:{text:'<b>'+getYTitleShort(yKey)+'</b>',font:{size:13,color:'#2c3e50'},x:0.5,pad:{b:4}},
    xaxis:{title:{text:xTitle,font:{size:11}},tickfont:{size:10},gridcolor:'#eeeeee',type:'category',autorange:true,categoryorder:'array'},
    yaxis:{title:{text:getYTitle(yKey),font:{size:11}},tickfont:{size:10},gridcolor:'#eeeeee',rangemode:'tozero',zeroline:true,zerolinecolor:'#ccc'},
    legend:{orientation:'h',x:0.5,y:-0.18,xanchor:'center',yanchor:'top',font:{size:13},bgcolor:'rgba(0,0,0,0)',borderwidth:0},
    showlegend:true,plot_bgcolor:'#fff',paper_bgcolor:'#fff',
    font:{family:'Segoe UI,Arial,sans-serif',size:11,color:'#1a1a2e'},margin:{l:60,r:12,t:44,b:110}};
}
function makeLayoutScatter(xField,yKey){
  var layout=makeLayoutLine(xField,yKey);
  layout.yaxis.rangemode='normal';
  if(xField==='__fqb_x'){
    layout.xaxis.title={text:_fqbXTitle,font:{size:11}};
    var t=_fqbChartTitle||_fqbYTitle;
    if(layout.title) layout.title.text='<b>'+t+'</b>';
  }
  return layout;
}
function makeLayoutBox(xField,yKey){
  var layout=makeLayoutLine(xField,yKey);
  layout.boxmode='group';
  layout.yaxis.rangemode='normal';
  return layout;
}
function makeLayoutHeatmap(xField,yKey){
  var xDef=X_AXES.filter(function(a){return a.key===xField;})[0]||X_AXES[0];
  var xTitle=xDef.unit?xDef.title+' ('+xDef.unit+')':xDef.title;
  return{
    title:{text:'<b>'+getYTitleShort(yKey)+'</b>',font:{size:13,color:'#2c3e50'},x:0.5,pad:{b:4}},
    xaxis:{title:{text:xTitle,font:{size:11}},tickfont:{size:10},type:'category',autorange:true},
    yaxis:{title:{text:'',font:{size:11}},tickfont:{size:10},automargin:true},
    plot_bgcolor:'#fff',paper_bgcolor:'#fff',
    font:{family:'Segoe UI,Arial,sans-serif',size:11,color:'#1a1a2e'},margin:{l:120,r:12,t:44,b:80}};
}

// ── Chart-Typ-Konfiguration ───────────────────────────────────────────────────
var CHART_TYPES=[
  {key:'bar',    label:'▬',  title:'Grouped Bar'},
  {key:'stack',  label:'▦',  title:'Stacked Bar'},
  {key:'line',   label:'╱',  title:'Line'},
  {key:'scatter',label:'◉',  title:'Scatter'},
  {key:'box',    label:'⊡',  title:'Box Plot'},
  {key:'heat',   label:'⊞',  title:'Heatmap'},
  {key:'3d',     label:'◈',  title:'3D Surface'},
];

function _isDrillActive(){
  return _drillStack.length > 0;
}

function buildTracesForType(chartType,xField,zField,yKey){
  // Im Drill-Down: immer trial-level Balken (ausser 3D/scatter/heatmap)
  if(_isDrillActive() && chartType !== '3d' && chartType !== 'scatter' && chartType !== 'heat'){
    return buildTraces2dDrill(yKey);
  }
  if(chartType==='bar')     return buildTraces2d(xField,yKey);
  if(chartType==='stack')   return buildTracesStacked(xField,yKey);
  if(chartType==='line')    return buildTracesLine(xField,yKey);
  if(chartType==='scatter') return buildTracesScatter(xField,yKey);
  if(chartType==='box')     return buildTracesBox(xField,yKey);
  if(chartType==='heat')    return buildTracesHeatmap(xField,yKey);
  if(chartType==='3d')      return buildTraces3d(xField,zField,yKey);
  return buildTraces2d(xField,yKey);
}
function makeLayoutForType(chartType,xField,zField,yKey,nJets){
  // Im Drill-Down: Layout mit "Versuch" als X-Titel
  if(_isDrillActive() && chartType !== '3d' && chartType !== 'scatter' && chartType !== 'heat'){
    var drillLast = _drillStack[_drillStack.length-1];
    var drillXDef = X_AXES.find(function(a){return a.key===drillLast.filterField;})||{title:drillLast.filterField,unit:''};
    var drillLabel = drillXDef.title + ': ' + drillLast.filterValue + (drillXDef.unit?' '+drillXDef.unit:'');
    var layout = makeLayout2d('trial_nr', yKey, nJets);
    layout.xaxis = layout.xaxis || {};
    layout.xaxis.title = { text: 'Versuch', font:{size:12} };
    layout.xaxis.type = 'category';
    layout.annotations = layout.annotations || [];
    layout.annotations.push({
      text: '🔍 ' + drillLabel,
      xref:'paper', yref:'paper',
      x:0, y:1.08, xanchor:'left', yanchor:'bottom',
      showarrow:false,
      font:{size:11, color:'#7a5500'},
      bgcolor:'#fff3cd', bordercolor:'#c8a000', borderwidth:1, borderpad:3,
    });
    return layout;
  }
  if(chartType==='bar')     return makeLayout2d(xField,yKey,nJets);
  if(chartType==='stack')   return makeLayoutStacked(xField,yKey,nJets);
  if(chartType==='line')    return makeLayoutLine(xField,yKey);
  if(chartType==='scatter') return makeLayoutScatter(xField,yKey);
  if(chartType==='box')     return makeLayoutBox(xField,yKey);
  if(chartType==='heat')    return makeLayoutHeatmap(xField,yKey);
  if(chartType==='3d')      return makeLayout3d(xField,zField,yKey);
  return makeLayout2d(xField,yKey,nJets);
}

// ── Layout ────────────────────────────────────────────────────────────────────
function makeLayout2d(xField,yKey,nJets){
  var xDef=X_AXES.filter(function(a){return a.key===xField;})[0]||X_AXES[0];
  var xTitle=xDef.unit?xDef.title+' ('+xDef.unit+')':xDef.title;
  var n=nJets||1,bargap=n<=2?0.65:n<=4?0.55:n<=6?0.35:0.20,bgap=n<=2?0.25:n<=4?0.15:0.08;
  return{barmode:'group',bargap:bargap,bargroupgap:bgap,
    title:{text:'<b>'+getYTitleShort(yKey)+'</b>',font:{size:13,color:'#2c3e50'},x:0.5,pad:{b:4}},
    xaxis:{title:{text:xTitle,font:{size:11}},tickfont:{size:10},gridcolor:'#eeeeee',type:'category',autorange:true,categoryorder:'array'},
    yaxis:{title:{text:getYTitle(yKey),font:{size:11}},tickfont:{size:10},gridcolor:'#eeeeee',rangemode:'tozero',zeroline:true,zerolinecolor:'#ccc'},
    legend:{orientation:'h',x:0.5,y:-0.18,xanchor:'center',yanchor:'top',font:{size:13},bgcolor:'rgba(0,0,0,0)',borderwidth:0,itemwidth:30,tracegroupgap:5},
    showlegend:true,
    plot_bgcolor:'#fff',paper_bgcolor:'#fff',font:{family:'Segoe UI,Arial,sans-serif',size:11,color:'#1a1a2e'},margin:{l:60,r:12,t:44,b:110}};
}
function makeLayout3d(xField,zField,yKey){
  var xDef=X_AXES.filter(function(a){return a.key===xField;})[0]||X_AXES[0],zDef=X_AXES.filter(function(a){return a.key===zField;})[0]||X_AXES[0];
  var x3T=xDef.unit?xDef.title+' ('+xDef.unit+')':xDef.title,z3T=zDef.unit?zDef.title+' ('+zDef.unit+')':zDef.title;
  return{scene:{xaxis:{title:{text:x3T,font:{size:11}},backgroundcolor:'#eef2ff',gridcolor:'#c8d0e0',showbackground:true},yaxis:{title:{text:z3T,font:{size:11}},backgroundcolor:'#eef2ff',gridcolor:'#c8d0e0',showbackground:true},zaxis:{title:{text:getYTitle(yKey),font:{size:11}},backgroundcolor:'#e8f0f8',gridcolor:'#b2c8e0',showbackground:true,rangemode:'tozero'},camera:{eye:{x:1.6,y:-1.6,z:1.1}},aspectmode:'auto'},
    legend:{title:{text:'<b>Jet</b>',font:{size:13}},font:{size:12},bgcolor:'rgba(0,0,0,0)',borderwidth:0},
    paper_bgcolor:'#f5f6fa',font:{family:'Segoe UI,Arial,sans-serif',size:11,color:'#1a1a2e'},margin:{l:0,r:0,t:16,b:0}};
}

// ── Multi-Y: Wrapper für mehrere Y-Reihen ──────────────────────────────────────

function _shiftTraceColor(t, yIdx, tIdx){
  // Y-Key 0: keine Änderung (normale Farben)
  // Y-Key 1+: COMPARE_COLORS als Basis, Jets innerhalb durch Helligkeit staffeln
  // — exakt gleiche Logik wie getJetColor bei mehreren Series
  var baseColor = COMPARE_COLORS[yIdx % COMPARE_COLORS.length];
  var hex = baseColor.replace('#','');
  if(hex.length===3) hex=hex[0]+hex[0]+hex[1]+hex[1]+hex[2]+hex[2];
  var r=parseInt(hex.substr(0,2),16)/255;
  var g=parseInt(hex.substr(2,2),16)/255;
  var b=parseInt(hex.substr(4,2),16)/255;
  // Jets innerhalb durch Helligkeit staffeln (wie getJetColor bei mehreren Series)
  var steps=[1.0,0.72,0.50,0.35,0.85,0.62];
  var f=steps[tIdx%steps.length];
  var mix=0.92;
  var nr=Math.round(Math.min(255,(r*255*f)*mix+255*(1-mix)));
  var ng=Math.round(Math.min(255,(g*255*f)*mix+255*(1-mix)));
  var nb=Math.round(Math.min(255,(b*255*f)*mix+255*(1-mix)));
  return '#'+nr.toString(16).padStart(2,'0')+ng.toString(16).padStart(2,'0')+nb.toString(16).padStart(2,'0');
}

function buildTracesForKeys(chartType, xField, zField, yKeys){
  if(!yKeys||yKeys.length<=1) return buildTracesForType(chartType,xField,zField,yKeys?yKeys[0]:'');
  if(chartType==='3d'||chartType==='scatter'||chartType==='heat'){
    return buildTracesForType(chartType,xField,zField,yKeys[0]);
  }

  // Erst alle Traces pro yKey aufbauen
  var tracesByYKey = [];
  yKeys.forEach(function(yKey, yIdx){
    var traces = buildTracesForType(chartType, xField, zField, yKey);
    var shortTitle = getYTitleShort(yKey);
    tracesByYKey.push({yKey: yKey, shortTitle: shortTitle, yIdx: yIdx, traces: traces});
  });

  // Reihenfolge: Jets als äussere Schleife, yKeys als innere
  var allJetNames = [];
  tracesByYKey.forEach(function(g){
    g.traces.forEach(function(t){
      var name = t.name||'';
      if(allJetNames.indexOf(name) === -1) allJetNames.push(name);
    });
  });

  var allTraces = [];
  allJetNames.forEach(function(jetName, tIdx){
    tracesByYKey.forEach(function(g){
      var t = g.traces.find(function(tr){ return tr.name === jetName; });
      if(!t) return;
      t = JSON.parse(JSON.stringify(t));
      t.name = g.shortTitle + ' · ' + jetName;
      t.legendgroup = g.yKey;
      t.legendgrouptitle = {text: g.shortTitle, font:{size:11, color:'#555'}};
      // Y-Key > 0: Farbe aus Series-Farbe ableiten mit Farbton-Verschiebung
      if(g.yIdx > 0){
        var col = _shiftTraceColor(t, g.yIdx, tIdx);
        t.marker = t.marker || {};
        t.marker.color = col;
        if(t.textfont) t.textfont.color = _textColorFor(col);
      }
      allTraces.push(t);
    });
  });
  return allTraces;
}

function makeLayoutForKeys(chartType, xField, zField, yKeys, nJets){
  if(!yKeys||yKeys.length<=1) return makeLayoutForType(chartType,xField,zField,yKeys?yKeys[0]:'',nJets);
  if(chartType==='3d'||chartType==='scatter'||chartType==='heat'){
    return makeLayoutForType(chartType,xField,zField,yKeys[0],nJets);
  }
  var layout=makeLayoutForType(chartType,xField,zField,yKeys[0],nJets);
  // Titel: alle Y-Keys zusammenfassen
  var titles=yKeys.map(function(k){return getYTitleShort(k);});
  layout.title={text:'<b>'+titles.join(' vs. ')+'</b>',font:{size:13,color:'#2c3e50'},x:0.5,pad:{b:4}};
  if(layout.yaxis) layout.yaxis.title={text:titles.join(' / '),font:{size:11}};
  // Legende: horizontal mit Gruppen nebeneinander, nicht untereinander stapeln
  // entrywidth begrenzt Spaltenbreite damit Einträge nebeneinander statt untereinander
  var nSeries = (typeof SERIES_REGISTRY !== 'undefined') ? SERIES_REGISTRY.length : 1;
  var nEntries = yKeys.length * Math.max(1, nSeries);
  layout.legend = {
    orientation: 'h',
    x: 0.5, y: -0.12,
    xanchor: 'center', yanchor: 'top',
    font: {size: 11},
    bgcolor: 'rgba(0,0,0,0)',
    borderwidth: 0,
    tracegroupgap: 30,
    entrywidth: 120,
    entrywidthmode: 'pixels',
  };
  // Margin unten: bei vielen Einträgen etwas mehr Platz
  var rows = Math.ceil(nEntries / 4);
  layout.margin = layout.margin || {};
  layout.margin.b = Math.max(80, 40 + rows * 22);
  return layout;
}

// ── Chart state ───────────────────────────────────────────────────────────────
var X_DEFAULT=X_AXES[0]?X_AXES[0].key:'air_pressure';
var Y_DEFAULTS=['titer','fpm','fpm_dtyomat','fpm_cv','cv_fp_dtyomat','elongation','elongation_cv','tenacity','tenacity_cv'];
var chartStates={};
function getState(idx){
  var def={xField:X_DEFAULT,zField:X_DEFAULT,yKey:Y_DEFAULTS[idx]||Y_AXES[0].key,yKeys:null,mode:'2d',chartType:'bar'};
  var s=chartStates[idx]||def;
  // Rückwärtskompatibilität: yKeys aus yKey ableiten falls nicht gesetzt
  if(!s.yKeys||!s.yKeys.length) s.yKeys=[s.yKey||(Y_DEFAULTS[idx]||Y_AXES[0].key)];
  return s;
}
// Parsed eine "5, 10, 15"-artige Eingabe zu einer Liste gültiger Zahlen
// (nicht-numerische/leere Teile werden stillschweigend übersprungen, damit
// man während des Tippens nicht ständig Fehler sieht).
function _parseGridlineValues(raw){
  if(!raw) return [];
  return String(raw).split(',').map(function(v){return parseFloat(v.trim());}).filter(function(v){return !isNaN(v);});
}
function _buildGridlineShapes(vals){
  return vals.map(function(v){
    return{type:'line',xref:'paper',x0:0,x1:1,yref:'y',y0:v,y1:v,
      line:{color:'#c85a4a',width:1.5,dash:'dash'},_gl:true};
  });
}
// Wertlabel links neben der y-Achse (ausserhalb des Plot-Bereichs, auf Hoehe
// der Linie) - direkt neben den Achsen-Ticks, dadurch sofort lesbar ohne dem
// eigentlichen Kurven-/Balkenbereich im Weg zu stehen.
function _buildGridlineAnnotations(vals){
  return vals.map(function(v){ return _oneGridlineAnnotation(v, false); });
}
function _oneGridlineAnnotation(v, preview){
  return{xref:'paper',x:0,xanchor:'right',yref:'y',y:v,yanchor:'middle',xshift:-45,
    text:String(Math.round(v*100)/100),showarrow:false,
    font:{size:9,color:'#c85a4a'},opacity:preview?0.7:1,
    bgcolor:'rgba(255,255,255,0.85)',borderpad:1,_gl:true};
}
// Andere, nicht von uns gesetzte shapes/annotations (z.B. die Drill-Down-
// Breadcrumb-Annotation) unangetastet lassen, wenn während des Draggens per
// Plotly.relayout nur die Gridline-Elemente ersetzt werden.
function _nonGridline(arr){
  return (arr||[]).filter(function(x){return !x || !x._gl;});
}
// Ermittelt einen festen y-Achsen-Bereich rein aus den Trace-Daten (inkl.
// Fehlerbalken-Spitzen), damit eine manuelle Gitternetzlinie (die weit
// ausserhalb der eigentlichen Daten liegen kann, z.B. y=100 bei Werten um 10)
// die automatische Skalierung des restlichen Charts NICHT verändert - Plotly
// bezieht Shapes sonst in die Autorange-Berechnung mit ein.
function _computeDataYRange(traces, rangemode){
  var vals=[];
  traces.forEach(function(t){
    (t.y||[]).forEach(function(v,i){
      if(typeof v!=='number'||!isFinite(v)) return;
      vals.push(v);
      var ey=t.error_y;
      if(ey&&ey.visible!==false){
        var up=Array.isArray(ey.array)?ey.array[i]:null;
        var dn=Array.isArray(ey.arrayminus)?ey.arrayminus[i]:up;
        if(typeof up==='number'&&isFinite(up)) vals.push(v+up);
        if(typeof dn==='number'&&isFinite(dn)) vals.push(v-dn);
      }
    });
  });
  if(!vals.length) return null;
  var mn=Math.min.apply(null,vals), mx=Math.max.apply(null,vals);
  if(rangemode==='tozero'){
    mn=Math.min(0,mn);
    var top=Math.max(mx,0.0001);
    return [mn, top*1.08];
  }
  var span=mx-mn; if(span<=0) span=Math.abs(mx)||1;
  var pad=span*0.08;
  return [mn-pad, mx+pad];
}
// Macht manuelle Gitternetzlinien per Maus vertikal verschiebbar — bewusst
// kein Plotlys eingebautes shapes[i].editable (das erlaubt auch Endpunkte
// einzeln zu ziehen, wodurch aus der horizontalen Linie eine schräge würde,
// und würde x0/x1 aus der paper-Vollbreite herausziehen). Stattdessen eigene
// Pixel<->Wert-Umrechnung über die internen Plotly-Achsenfunktionen
// (ax.d2p/p2d), die die einzige Möglichkeit sind, exakt eine y-Verschiebung
// zuzulassen ohne den Rest des Charts (Zoom, Balken, Achsenbereich) anzufassen.
function _exitGridlinePlacement(el){
  el._gridlinePlacing = false;
  el.style.cursor = '';
  var card = el.closest('.chart-card');
  var btn = card && card.querySelector('.btn-gridline');
  if(btn) btn.classList.remove('active');
}
// Startet den "auf die Grafik klicken, um dort eine Linie zu setzen"-Modus
// (vom "± Line"-Button ausgelöst) — Cursor wird zum Fadenkreuz, eine
// gestrichelte Vorschaulinie folgt der Maus live mit, der nächste Klick auf
// die Zeichenfläche committet den Wert. Ohne diesen Modus würde ein Klick auf
// den Chart nur Plotlys eingebauten Zoom-Drag auslösen — genau das Problem,
// das der Nutzer gemeldet hat ("ich kann nur reinzoomen").
function _startGridlinePlacement(el, idx){
  el._gridlinePlacing = true;
  el.style.cursor = 'crosshair';
  var card = el.closest('.chart-card');
  var btn = card && card.querySelector('.btn-gridline');
  if(btn) btn.classList.add('active');
  var bar = document.getElementById('gridline_bar_'+idx);
  if(bar) bar.classList.add('visible');
}
function _bindGridlineDrag(el, idx){
  if(el._gridlineDragBound) return;
  el._gridlineDragBound = true;
  var TOL = 6; // px Fangradius um eine Linie
  var dragging = null; // {i, vals}
  function _yRelFromEvent(ev){
    var fl = el._fullLayout; if(!fl || !fl.yaxis || !fl._size) return null;
    var rect = el.getBoundingClientRect();
    return {fl:fl, yRel: ev.clientY - rect.top - fl._size.t};
  }
  function _hitTest(clientY){
    var fl = el._fullLayout; if(!fl || !fl.yaxis || !fl._size) return null;
    var s = getState(idx);
    var vals = _parseGridlineValues(s.gridlinesY);
    if(!vals.length) return null;
    var rect = el.getBoundingClientRect();
    var yRel = clientY - rect.top - fl._size.t;
    for(var i=0;i<vals.length;i++){
      if(Math.abs(fl.yaxis.d2p(vals[i]) - yRel) <= TOL) return {i:i, vals:vals};
    }
    return null;
  }
  function _renderShapes(vals, previewVal){
    var baseShapes = _nonGridline(el.layout && el.layout.shapes);
    var baseAnnos  = _nonGridline(el.layout && el.layout.annotations);
    var shapes = baseShapes.concat(_buildGridlineShapes(vals));
    var annos  = baseAnnos.concat(_buildGridlineAnnotations(vals));
    if(previewVal!=null){
      var pShape=_buildGridlineShapes([previewVal])[0];
      pShape.line={color:'#c85a4a',width:1,dash:'dot'};
      shapes=shapes.concat([pShape]);
      annos=annos.concat([_oneGridlineAnnotation(previewVal, true)]);
    }
    var update={shapes:shapes, annotations:annos};
    // Auch fuer die Live-Vorschau der allerersten Linie (noch nichts committed,
    // updateChart() hat den Rand deshalb noch nicht vergroessert) sicherstellen,
    // dass links genug Platz fuer das Wertlabel ist - sonst wird die Zahl beim
    // Platzieren abgeschnitten, bevor ueberhaupt eine Linie gesetzt wurde.
    if((vals.length || previewVal!=null)){
      var curL=(el.layout && el.layout.margin && el.layout.margin.l)||60;
      if(curL<95) update['margin.l']=95;
    }
    Plotly.relayout(el, update);
  }
  el.addEventListener('mousedown', function(ev){
    if(el._gridlinePlacing){
      var info=_yRelFromEvent(ev); if(!info) return;
      var newVal=Math.round(info.fl.yaxis.p2d(info.yRel)*100)/100;
      var s=getState(idx);
      var vals=_parseGridlineValues(s.gridlinesY);
      vals.push(newVal);
      s.gridlinesY=vals.join(', ');
      s.gridlinesVisible=true;
      chartStates[idx]=s;
      var inp=document.getElementById('gridline_input_'+idx);
      if(inp) inp.value=s.gridlinesY;
      _exitGridlinePlacement(el);
      updateChart(idx);
      ev.preventDefault(); ev.stopPropagation();
      return;
    }
    var hit = _hitTest(ev.clientY);
    if(!hit) return;
    dragging = hit;
    el.style.cursor = 'ns-resize';
    ev.preventDefault(); ev.stopPropagation();
  }, true);
  el.addEventListener('mousemove', function(ev){
    if(dragging) return;
    if(el._gridlinePlacing){
      el.style.cursor='crosshair';
      var info=_yRelFromEvent(ev); if(!info) return;
      var previewVal=Math.round(info.fl.yaxis.p2d(info.yRel)*100)/100;
      var s=getState(idx);
      _renderShapes(_parseGridlineValues(s.gridlinesY), previewVal);
      return;
    }
    var hit = _hitTest(ev.clientY);
    el.style.cursor = hit ? 'ns-resize' : '';
  });
  document.addEventListener('keydown', function(ev){
    if(ev.key==='Escape' && el._gridlinePlacing){
      _exitGridlinePlacement(el);
      _renderShapes(_parseGridlineValues(getState(idx).gridlinesY), null);
    }
  });
  document.addEventListener('mousemove', function(ev){
    if(!dragging) return;
    var info=_yRelFromEvent(ev); if(!info) return;
    dragging.vals[dragging.i] = info.fl.yaxis.p2d(info.yRel);
    _renderShapes(dragging.vals, null);
  });
  document.addEventListener('mouseup', function(){
    if(!dragging) return;
    var finalVals = dragging.vals.map(function(v){ return Math.round(v*100)/100; });
    dragging = null;
    el.style.cursor = '';
    var s = getState(idx);
    s.gridlinesY = finalVals.join(', ');
    chartStates[idx] = s;
    var inp = document.getElementById('gridline_input_'+idx);
    if(inp) inp.value = s.gridlinesY;
    _renderShapes(finalVals, null);
  });
}
function _updateSdButton(){
  var btn=document.getElementById('btn-sd');
  var btnMM=document.getElementById('btn-minmax');
  if(!btn)return;
  // Immer aktiv lassen — ausgrauen ist verwirrend auch wenn n=1
  btn.style.opacity='';btn.style.pointerEvents='';btn.title='Toggle Standard Deviation bars';
  if(btnMM){btnMM.style.opacity='';btnMM.style.pointerEvents='';btnMM.title='Toggle Min/Max markers';}
}
function updateChart(idx){
  var s=getState(idx),el=document.getElementById('chart_'+idx);if(!el)return;
  // FQB-Daten für diesen Block laden falls vorhanden
  var _bfs=_blockFqbStates[idx];
  if(_bfs&&_bfs.data&&_bfs.data.length){
    SERIES_REGISTRY=[{pk:0,name:'Free Query',color:'#39A650',data:_bfs.data,machine:'',material:''}];
    _fqbXTitle=_bfs.xTitle||'';_fqbYTitle=_bfs.yTitle||'';
    _fqbChartTitle=_bfs.chartTitle||'';
  } else {
    _fqbChartTitle='';
  }
  var ct=s.chartType||'bar';
  var dmb=ct==='3d';
  var yKeys=s.yKeys&&s.yKeys.length?s.yKeys:[s.yKey||(Y_AXES[0]?Y_AXES[0].key:'titer')];
  var traces=buildTracesForKeys(ct,s.xField,s.zField,yKeys);
  var layout=makeLayoutForKeys(ct,s.xField,s.zField,yKeys,_lastNJets);
  // FQB Chart-Titel überschreiben falls gesetzt
  if(_fqbChartTitle && s.xField && s.xField.indexOf('__fqb')===0){
    if(layout.title) layout.title.text='<b>'+_fqbChartTitle+'</b>';
    else layout.title={text:'<b>'+_fqbChartTitle+'</b>'};
  }
  // Kategoriewerte explizit aus Traces ableiten → kein Achsen-Caching
  if(ct!=='3d' && ct!=='heat' && layout.xaxis){
    var xVals=[];
    traces.forEach(function(t){(t.x||[]).forEach(function(v){if(xVals.indexOf(String(v))===-1)xVals.push(String(v));});});
    // Prüfen ob alle Werte numerisch sind
    var _allNum = xVals.length>0 && xVals.every(function(v){return !isNaN(parseFloat(v))&&isFinite(v);});
    xVals.sort(function(a,b){var na=parseFloat(a),nb=parseFloat(b);return(!isNaN(na)&&!isNaN(nb))?na-nb:String(a).localeCompare(String(b));});
    if(_allNum){
      // Numerische X-Werte: type 'category' mit categoryarray → normale Sortierung
      layout.xaxis.type='category';
      layout.xaxis.categoryarray=xVals;
      layout.xaxis.categoryorder='array';
      layout.xaxis.autorange=true;
      delete layout.xaxis.range;
    } else {
      // String-X-Werte: type 'category', kein autorange, kein range — Plotly skaliert selbst
      layout.xaxis.type='category';
      layout.xaxis.categoryarray=xVals;
      layout.xaxis.categoryorder='array';
      delete layout.xaxis.autorange;
      delete layout.xaxis.range;
    }
  }
  // Manuelle Gitternetzlinien (y-Achse) zusätzlich zum automatischen Grid von
  // Plotly einzeichnen — als feste Referenzlinien bei vom Nutzer eingegebenen
  // Werten, nicht als Ersatz für die automatische Achsenskalierung. Sobald
  // Shapes im Spiel sind, bezieht Plotly sie sonst in die Autorange-Berechnung
  // mit ein (eine Linie bei y=100 würde den ganzen Chart neu skalieren, auch
  // wenn die echten Daten z.B. nur bis 10 gehen) — deshalb Range explizit aus
  // den reinen Trace-Daten fixieren, sobald mind. eine Gridline aktiv ist.
  if(ct!=='3d' && ct!=='heat' && layout.yaxis){
    var glVals=_parseGridlineValues(s.gridlinesY);
    if(glVals.length){
      var _fixedRange=_computeDataYRange(traces, layout.yaxis.rangemode);
      if(_fixedRange){ layout.yaxis.range=_fixedRange; layout.yaxis.autorange=false; }
      layout.shapes=(layout.shapes||[]).concat(_buildGridlineShapes(glVals));
      layout.annotations=(layout.annotations||[]).concat(_buildGridlineAnnotations(glVals));
      // Zusaetzlicher Platz links, damit die Wertlabel nicht mit den normalen
      // y-Achsen-Ticks kollidieren.
      layout.margin=layout.margin||{}; layout.margin.l=Math.max(layout.margin.l||60, 95);
    }
  }
  // Plotly.react ignoriert categoryarray beim allerersten Render eines DOM-Elements
  // (kein _fullLayout vorhanden) → newPlot für Erstrender, react für Updates
  var cfg={responsive:true,displayModeBar:dmb,displaylogo:false};
  // Debug: log wenn Traces leer oder X-Werte fehlen
  if(!traces.length || (traces[0] && !traces[0].x.length)){
    console.warn('[SmartChart] updateChart idx='+idx+' — keine Trace-Daten. xField='+(chartStates[idx]||{}).xField+' traces='+traces.length+(traces[0]?' x-len='+traces[0].x.length:''));
  }
  if(el._fullLayout){
    Plotly.react(el,traces,layout,cfg);
  } else {
    Plotly.newPlot(el,traces,layout,cfg);
  }
  _updateSdButton();
  if(ct!=='3d' && ct!=='heat') _bindGridlineDrag(el,idx);
  // Balken breiter machen, wenn eine Reihe (Legende) aus-/eingeblendet wird:
  // bargap/bargroupgap wurden oben anhand ALLER Jets berechnet, nicht nur der
  // aktuell sichtbaren. Beim Legend-Klick nur bei tatsächlicher Trace-Zahl neu
  // rechnen und per Plotly.relayout anwenden (kein kompletter Re-Render nötig).
  if(layout.barmode&&!el._smartChartLegendBound){
    el._smartChartLegendBound=true;
    el.on('plotly_legendclick',function(ev){
      setTimeout(function(){
        try{
          var gd=el;
          var visCount=(gd.data||[]).filter(function(t){return t.visible!==false&&t.visible!=='legendonly';}).length;
          // Nach dem Klick ist der geklickte Trace noch nicht in gd.data aktualisiert -
          // ev.data zeigt den Zielzustand direkt an.
          if(ev&&typeof ev.curveNumber==='number'&&ev.data&&ev.data[ev.curveNumber]){
            var willBeHidden=ev.data[ev.curveNumber].visible!=='legendonly';
            visCount=willBeHidden?visCount-1:visCount+1;
          }
          visCount=Math.max(1,visCount);
          var newBargap=visCount<=2?0.65:visCount<=4?0.55:visCount<=6?0.35:0.20;
          var newBgap=visCount<=2?0.25:visCount<=4?0.15:0.08;
          Plotly.relayout(gd,{bargap:newBargap,bargroupgap:newBgap});
        }catch(e){}
      },0);
      return true; // Standard-Toggle-Verhalten von Plotly beibehalten
    });
  }
}
function refreshAllCharts(){
  var total=Math.max(1,parseInt(document.getElementById('inp-count').value)||1);
  for(var i=0;i<total;i++){if(document.getElementById('chart_'+i))updateChart(i);}
  if(typeof renderInfobox==='function') renderInfobox();
}

// ── Series pills ──────────────────────────────────────────────────────────────
function renderSeriesPills(){
  var container=document.getElementById('series-list');container.innerHTML='';
  SERIES_REGISTRY.forEach(function(s,idx){
    var pill=document.createElement('div');pill.className='series-pill';
    var dot=document.createElement('div');dot.className='pill-color';dot.style.background=s.color;dot.title='Click to change color';
    var picker=document.createElement('input');picker.type='color';picker.value=s.color;picker.style.cssText='position:absolute;opacity:0;width:0;height:0;pointer-events:none;';
    dot.addEventListener('click',function(){picker.click();});
    picker.addEventListener('input',function(){s.color=picker.value;dot.style.background=s.color;});
    picker.addEventListener('change',function(){s.color=picker.value;dot.style.background=s.color;refreshAllCharts();});
    var name=document.createElement('span');name.textContent=s.name;name.title=s.name;
    pill.appendChild(dot);pill.appendChild(picker);pill.appendChild(name);
    if(idx>0){var rm=document.createElement('span');rm.className='pill-remove';rm.textContent='×';rm.addEventListener('click',function(){SERIES_REGISTRY.splice(idx,1);_reassignCompareColors();renderSeriesPills();buildInfobox();refreshAllCharts();});pill.appendChild(rm);}
    container.appendChild(pill);
  });
}

// ── Series Picker (primary series wählen) ────────────────────────────────────
var _pickSeriesCallback = null;
function rgbToHex(rgb){
  // converts "rgb(r,g,b)" or "#rrggbb" to "#rrggbb"
  if(!rgb) return '#39A650';
  if(rgb.startsWith('#')) return rgb;
  var m=rgb.match(/\d+/g);
  if(!m||m.length<3) return '#39A650';
  return '#'+[m[0],m[1],m[2]].map(function(x){
    return ('0'+parseInt(x).toString(16)).slice(-2);
  }).join('');
}

function openLegendOrderModal(){
  var jets = getAllJetNames();
  if(!jets.length){ alert('Run a query first.'); return; }
  var list = document.getElementById('legend-order-list');
  list.innerHTML = '';
  var _dragSrc = null;

  // Compute positional colour based on current row order in the modal
  function _posColor(posIdx, jetKey){
    if(_jetColorOverride[jetKey]) return _jetColorOverride[jetKey];
    if(SERIES_REGISTRY.length === 1){
      return getColor(posIdx);
    }
    var parts=jetKey.split('::'),seriesPk=parts.length>1?parseInt(parts[0]):SERIES_REGISTRY[0].pk;
    var sIdx=SERIES_REGISTRY.findIndex(function(s){return s.pk===seriesPk;});
    if(sIdx<0)sIdx=0;
    var rgb=hexRgb(SERIES_REGISTRY[sIdx].color);
    var steps=[1.0, 0.72, 0.50, 0.35, 0.85, 0.62];
    var f=steps[posIdx%steps.length], mix=0.92;
    var r=Math.round(Math.min(255,(rgb[0]*255*f)*mix+255*(1-mix)));
    var g=Math.round(Math.min(255,(rgb[1]*255*f)*mix+255*(1-mix)));
    var b=Math.round(Math.min(255,(rgb[2]*255*f)*mix+255*(1-mix)));
    return 'rgb('+r+','+g+','+b+')';
  }

  // Refresh all colour buttons based on current row positions
  function _refreshColors(){
    var rows = list.querySelectorAll('.leg-row');
    rows.forEach(function(row, i){
      var btn = row.querySelector('.leg-color-btn');
      if(!_jetColorOverride[row.dataset.jetkey]){
        btn.value = rgbToHex(_posColor(i, row.dataset.jetkey));
      }
    });
  }

  jets.forEach(function(key, i){
    var row = document.createElement('div');
    row.className = 'leg-row';
    row.draggable = true;
    row.dataset.jetkey = key;

    // Colour based on position (not jet name)
    var curColor = _jetColorOverride[key] || _posColor(i, key);

    // Handle
    var handle = document.createElement('span');
    handle.className = 'leg-handle'; handle.textContent = '⠿';

    // Colour button
    var colBtn = document.createElement('input');
    colBtn.type = 'color';
    colBtn.className = 'leg-color-btn';
    colBtn.value = rgbToHex(curColor);
    colBtn.title = 'Change colour (overrides position colour)';
    colBtn.style.cssText = 'width:28px;height:28px;border-radius:4px;border:2px solid #ccc;cursor:pointer;padding:0;';
    // When user picks a colour manually, mark it as override
    colBtn.addEventListener('change', function(){
      _jetColorOverride[key] = colBtn.value;
    });

    // Name
    var name = document.createElement('span');
    name.className = 'leg-name';
    name.textContent = key.indexOf('::') > -1 ? key.split('::')[1] + ' [' + key.split('::')[0] + ']' : key;

    // Up/Down arrows
    var arrows = document.createElement('div');
    arrows.className = 'leg-arrows';
    var up = document.createElement('button');
    up.className = 'leg-arrow'; up.textContent = '▲'; up.title = 'Move up';
    var dn = document.createElement('button');
    dn.className = 'leg-arrow'; dn.textContent = '▼'; dn.title = 'Move down';
    up.onclick = function(){
      var prev = row.previousElementSibling;
      if(prev){ list.insertBefore(row, prev); _refreshColors(); }
    };
    dn.onclick = function(){
      var next = row.nextElementSibling;
      if(next){ list.insertBefore(next, row); _refreshColors(); }
    };
    arrows.appendChild(up); arrows.appendChild(dn);

    // Drag & drop
    row.addEventListener('dragstart', function(e){
      _dragSrc = row;
      e.dataTransfer.effectAllowed = 'move';
      row.style.opacity = '0.5';
    });
    row.addEventListener('dragend', function(){
      row.style.opacity = '1';
      list.querySelectorAll('.leg-row').forEach(function(r){ r.classList.remove('drag-over'); });
      _refreshColors();
    });
    row.addEventListener('dragover', function(e){
      e.preventDefault(); e.dataTransfer.dropEffect = 'move';
      row.classList.add('drag-over');
    });
    row.addEventListener('dragleave', function(){ row.classList.remove('drag-over'); });
    row.addEventListener('drop', function(e){
      e.preventDefault();
      row.classList.remove('drag-over');
      if(_dragSrc && _dragSrc !== row){
        list.insertBefore(_dragSrc, row);
      }
    });

    row.appendChild(handle);
    row.appendChild(colBtn);
    row.appendChild(name);
    row.appendChild(arrows);
    list.appendChild(row);
  });

  document.getElementById('modal-legend-order').classList.add('open');
}

function openPickSeriesModal(){
  // Nutzt dasselbe Modal wie Add Series, aber ersetzt die primäre Series
  _selectedSeriesPk = null;
  document.getElementById('series-modal-ok').disabled = true;
  document.getElementById('series-search').value = '';
  // Farbe fix auf primäre Farbe
  var colorPick = document.getElementById('series-color-pick');
  var colorRow  = document.getElementById('series-color-row');
  if(colorPick) colorPick.value = '#39A650';
  if(colorRow)  colorRow.style.display = 'none'; // Farbe nicht relevant für primäre Series
  // Titel ändern
  var h3 = document.querySelector('#modal-series h3');
  if(h3) h3.textContent = '📊 Select Trial Series';
  if(_allSeriesList.length === 0 && _bridge) _bridge.getSeriesList();
  else renderSeriesListModal(_allSeriesList);
  document.getElementById('modal-series').classList.add('open');
  _seriesModalMode = 'pick';
}

// ── Add Series Modal ──────────────────────────────────────────────────────────
var _allSeriesList=[],_selectedSeriesPk=null;
function openAddSeriesModal(){
  _selectedSeriesPk=null;document.getElementById('series-modal-ok').disabled=true;
  document.getElementById('series-search').value='';
  // Farbe automatisch aus COMPARE_COLORS — kein Picker nötig
  var autoColor=_nextCompareColor();
  document.getElementById('series-color-pick').value=autoColor;
  var cr=document.getElementById('series-color-row');
  if(cr) cr.style.display='none';
  _seriesModalMode = 'compare';
  if(_allSeriesList.length===0&&_bridge)_bridge.getSeriesList();else renderSeriesListModal(_allSeriesList);
  document.getElementById('modal-series').classList.add('open');
}
function renderSeriesListModal(list){
  _allSeriesList=list;
  var search=(document.getElementById('series-search').value||'').toLowerCase();
  var container=document.getElementById('series-list-modal');container.innerHTML='';
  var loaded=SERIES_REGISTRY.map(function(s){return s.pk;});
  var filtered=list.filter(function(s){return(!search||(s.name||'').toLowerCase().indexOf(search)!==-1||String(s.pk).indexOf(search)!==-1)&&loaded.indexOf(s.pk)===-1;});
  if(!filtered.length){container.innerHTML='<div style="padding:16px;text-align:center;color:#aaa;font-size:12px;">No series found</div>';return;}
  filtered.slice(0,80).forEach(function(s){
    var item=document.createElement('div');item.className='modal-list-item'+(s.pk===_selectedSeriesPk?' selected':'');
    item.innerHTML='<span class="modal-item-id">#'+s.pk+'</span><span class="modal-item-name">'+s.name+'</span>';
    item.addEventListener('click',function(){_selectedSeriesPk=s.pk;container.querySelectorAll('.modal-list-item').forEach(function(el){el.classList.remove('selected');});item.classList.add('selected');document.getElementById('series-modal-ok').disabled=false;});
    container.appendChild(item);
  });
}
document.getElementById('series-search').addEventListener('input',function(){renderSeriesListModal(_allSeriesList);});

var _seriesModalMode = 'compare'; // 'compare' oder 'pick'

document.getElementById('series-modal-ok').addEventListener('click',function(){
  if(!_selectedSeriesPk) return;
  document.getElementById('modal-series').classList.remove('open');
  _resetSeriesModal();
  if(_seriesModalMode === 'pick'){
    // Primary Series ersetzen
    SERIES_REGISTRY = [{pk:_selectedSeriesPk, name:'Loading...', color:'#39A650', data:[], machine:'', material:''}];
    rebuildGrid(); renderSeriesPills();
    if(_bridge) _bridge.loadSeriesData(String(_selectedSeriesPk), '#39A650');
  } else {
    // Compare: zur bestehenden Registry hinzufügen
    var color = _nextCompareColor();
    if(_bridge) _bridge.loadSeriesData(String(_selectedSeriesPk), color);
  }
});

function _resetSeriesModal(){
  var h3 = document.querySelector('#modal-series h3');
  if(h3) h3.textContent = 'Add Trial Series for Comparison';
  var cr = document.getElementById('series-color-row');
  if(cr) cr.style.display = 'none'; // immer versteckt
  _seriesModalMode = 'compare';
}

document.getElementById('series-modal-cancel').addEventListener('click',function(){
  document.getElementById('modal-series').classList.remove('open');
  _resetSeriesModal();
});
document.getElementById('modal-series').addEventListener('click',function(e){
  if(e.target===this){ this.classList.remove('open'); _resetSeriesModal(); }
});

function receiveSeriesList(list){
  // Absteigend nach ID sortieren (neueste zuerst)
  list.sort(function(a,b){return b.pk-a.pk;});
  _allSeriesList=list;
  if(document.getElementById('modal-series').classList.contains('open'))renderSeriesListModal(list);
  if(IS_VISUAL)populateBuilderSeriesList(list);
}
function receiveSeriesData(pk,name,color,data,meta){
  var existing=SERIES_REGISTRY.findIndex(function(s){return s.pk===pk;});
  var entry={pk:pk,name:name,color:color,data:data,machine:(meta&&meta.machine)||'',material:(meta&&meta.material)||''};
  if(existing>=0){
    SERIES_REGISTRY[existing]=entry;
  } else {
    SERIES_REGISTRY=SERIES_REGISTRY.filter(function(s){return s.pk!==pk;});
    SERIES_REGISTRY.push(entry);
  }
  // Update INFOBOX if this is the primary series (first in registry or replaces it)
  if(SERIES_REGISTRY.length===1 || SERIES_REGISTRY[0].pk===pk){
    if(meta){
      INFOBOX.series_name   = name;
      INFOBOX.machine       = meta.machine   || '';
      INFOBOX.material      = meta.material  || '';
    }
    // Rebuild dimension slicers from actual data
    var aps=[],ofs=[],sps=[],jets=[];
    data.forEach(function(d){
      if(d.air_pressure!==null&&d.air_pressure!==undefined&&aps.indexOf(d.air_pressure)===-1)aps.push(d.air_pressure);
      if(d.overfeed!==null&&d.overfeed!==undefined&&ofs.indexOf(d.overfeed)===-1)ofs.push(d.overfeed);
      if(d.speed!==null&&d.speed!==undefined&&sps.indexOf(d.speed)===-1)sps.push(d.speed);
      if(d.jet_name&&jets.indexOf(d.jet_name)===-1)jets.push(d.jet_name);
    });
    INFOBOX.air_pressures = aps.sort(function(a,b){return a-b;});
    INFOBOX.overfeeds     = ofs.sort(function(a,b){return a-b;});
    INFOBOX.speeds        = sps.sort(function(a,b){return a-b;});
    INFOBOX.jets          = jets.sort();
    INFOBOX.n_trials      = data.length;
  }
  _reassignCompareColors(); // ERST Farben setzen, dann Charts rendern
  var hasNotes=Object.keys(chartStates).some(function(k){return chartStates[k].noteText||chartStates[k].noteVisible;});
  if(hasNotes){ rebuildGrid(); } else { refreshAllCharts(); }
  renderSeriesPills(); buildInfobox();
}

// ── Custom Field Modal ────────────────────────────────────────────────────────
var _modalCallback=null;
function openModal(cb){_modalCallback=cb;var f=document.getElementById('modal-field');f.innerHTML='<option value="">— Select table —</option>';document.getElementById('modal-hint').textContent='';var t=document.getElementById('modal-table');if(t.value)loadFields(t.value);document.getElementById('modal-cf').classList.add('open');}
function loadFields(tbl){var f=document.getElementById('modal-field'),cols=TBL_COLS[tbl]||[];f.innerHTML=cols.length?cols.map(function(c){return'<option value="'+c+'">'+c+'</option>';}).join(''):'<option value="">No fields found</option>';document.getElementById('modal-hint').textContent=cols.length?cols.length+' fields available':'';}
document.getElementById('modal-table').addEventListener('change',function(){loadFields(this.value);});
document.getElementById('modal-cancel').addEventListener('click',function(){document.getElementById('modal-cf').classList.remove('open');_modalCallback=null;});
document.getElementById('modal-ok').addEventListener('click',function(){var tbl=document.getElementById('modal-table').value,fld=document.getElementById('modal-field').value;if(!tbl||!fld)return;document.getElementById('modal-cf').classList.remove('open');if(_modalCallback){var key='free:'+tbl+':'+fld;_modalCallback(key,fld+' ('+tbl+')');}  _modalCallback=null;});
document.getElementById('modal-cf').addEventListener('click',function(e){if(e.target===this){this.classList.remove('open');_modalCallback=null;}});

// ── Infobox ───────────────────────────────────────────────────────────────────
function buildInfobox(){
  var el=document.getElementById('infobox-slot');if(!el)return;
  function el_(t,c,tx){var e=document.createElement(t);if(c)e.className=c;if(tx)e.textContent=tx;return e;}
  function makeRow(l,v){if(!v)return null;var r=el_('div','infobox-row');r.appendChild(el_('div','infobox-row-label',l));r.appendChild(el_('div','infobox-row-value',v));return r;}
  function makeSlicerGroup(label,vals,slicerKey,fmt){
    if(!vals||!vals.length)return null;
    var group=el_('div','infobox-dim'),lbl=el_('div','infobox-dim-label',label),values=el_('div','infobox-dim-values');
    group.appendChild(lbl);group.appendChild(values);
    vals.forEach(function(val){
      var tag=el_('span','infobox-tag',fmt?fmt(val):String(val));tag.dataset.val=String(val);
      var sel=slicerState[slicerKey];if(sel.indexOf(String(val))!==-1)tag.classList.add('active');
      tag.addEventListener('click',function(){var idx=sel.indexOf(tag.dataset.val);if(idx===-1){sel.push(tag.dataset.val);tag.classList.add('active');}else{sel.splice(idx,1);tag.classList.remove('active');}buildInfobox();refreshAllCharts();});
      values.appendChild(tag);
    });
    return group;
  }
  function mergeVals(field){var all=[];SERIES_REGISTRY.forEach(function(s){s.data.forEach(function(d){var v=d[field];if(v!==null&&v!==undefined&&v!==0&&all.indexOf(v)===-1)all.push(v);});});return all.sort(function(a,b){return a-b;});}
  function mergeJets(){var all=[];SERIES_REGISTRY.forEach(function(s){s.data.forEach(function(d){var j=d.real_jet||d.jet_name||'Unknown';if(all.indexOf(j)===-1)all.push(j);});});return all.sort();}
  function mergeYarns(){var all=[];SERIES_REGISTRY.forEach(function(s){s.data.forEach(function(d){if(!d.yarn_name)return;var y=d.yarn_name;if(all.indexOf(y)===-1)all.push(y);});});return all.sort();}

  var box=el_('div','infobox');
  box.appendChild(el_('div','infobox-title','Trial Series'));
  box.appendChild(el_('div','infobox-row-label','Series'));
  SERIES_REGISTRY.forEach(function(s){
    var block=el_('div','');block.style.cssText='border-left:3px solid '+s.color+';padding:6px 0 6px 10px;margin:4px 0;';
    var nameRow=el_('div','infobox-series-pill'),dot=el_('div','infobox-series-dot');dot.style.background=s.color;
    var nameSpan=el_('span','');nameSpan.textContent=s.name;nameSpan.style.cssText='font-weight:600;font-size:11px;color:#2c3e50;';
    nameRow.appendChild(dot);nameRow.appendChild(nameSpan);block.appendChild(nameRow);
    if(s.machine){var mRow=el_('div','');mRow.style.cssText='font-size:10px;color:#7a9ab5;margin-top:3px;';mRow.textContent='Machine: '+s.machine;block.appendChild(mRow);}
    if(s.material){var matRow=el_('div','');matRow.style.cssText='font-size:10px;color:#7a9ab5;margin-top:2px;';matRow.textContent='Material: '+s.material;block.appendChild(matRow);}
    box.appendChild(block);
  });
  var dims=el_('div','infobox-dims'),g;
  function mergeMachines(){var all=[];SERIES_REGISTRY.forEach(function(s){s.data.forEach(function(d){var m=d.machine_name||'';if(m&&all.indexOf(m)===-1)all.push(m);});});return all.sort();}
  if((g=makeSlicerGroup('Air Pressure',mergeVals('air_pressure'),'air_pressure',function(v){return v+' bar';})))dims.appendChild(g);
  if((g=makeSlicerGroup('Overfeed',mergeVals('overfeed'),'overfeed',function(v){return v+' %';})))dims.appendChild(g);
  if((g=makeSlicerGroup('Speed',mergeVals('speed'),'speed',function(v){return v+' m/min';})))dims.appendChild(g);
  if((g=makeSlicerGroup('Machine',mergeMachines(),'machine_name',null)))dims.appendChild(g);
  if((g=makeSlicerGroup('Jet',  mergeJets(),  'jet_name',  null))) dims.appendChild(g);
  if((g=makeSlicerGroup('Yarn', mergeYarns(), 'yarn_name', null))) dims.appendChild(g);
  box.appendChild(dims);
  // Total trials
  var total=SERIES_REGISTRY.reduce(function(s,r){return s+r.data.length;},0);
  // Gefilterte trials (nach aktiven Slicern)
  var filtered=SERIES_REGISTRY.reduce(function(s,r){return s+r.data.filter(slicerMatch).length;},0);
  var nRow=el_('div','infobox-n');
  nRow.appendChild(el_('span','infobox-badge',String(total)));
  nRow.appendChild(el_('span','infobox-n-label','Total trials'));
  if(filtered<total){
    var sep=el_('div','');sep.style.cssText='width:1px;height:16px;background:#cde0ee;margin:0 4px;';
    var badge2=el_('span','infobox-badge','');
    badge2.textContent=String(filtered);
    badge2.style.cssText+='background:#d0e8ff;color:#1D3557;';
    var lbl2=el_('span','infobox-n-label','Shown (filtered)');
    nRow.appendChild(sep);nRow.appendChild(badge2);nRow.appendChild(lbl2);
  }
  box.appendChild(nRow);
  el.innerHTML='';el.appendChild(box);
}

document.addEventListener('keydown',function(e){
  if(e.key==='Escape'&&_expandedChartIdx!==null) _collapseChart();
});

// ── QWebChannel ───────────────────────────────────────────────────────────────
var _bridge=null;
document.addEventListener('keydown',function(e){
  if(e.key==='Escape'&&_expandedChartIdx!==null) _collapseChart();
});

new QWebChannel(qt.webChannelTransport,function(channel){
  _bridge=channel.objects.bridge;
  _bridge.getSeriesList();
  _bridge.getLayoutTemplates();
  if(IS_VISUAL)initBuilder();
  if(INITIAL_REPORT_ID) _bridge.loadReport(String(INITIAL_REPORT_ID));
});
function receiveFreeFieldData(chartIdx,yKey,values){DATA.forEach(function(d){var v=values[d.trial_id];d[yKey]=(v!==undefined&&v!==null)?v:null;});updateChart(chartIdx);}

// ── Layout Templates ─────────────────────────────────────────────────────────
var _allTemplates = [], _selectedTemplateId = null;

function openTemplatesModal(){
  _selectedTemplateId = null;
  document.getElementById('btn-tpl-apply').disabled = true;
  document.getElementById('tpl-save-name').value = '';
  document.getElementById('tpl-save-desc').value = '';
  var owb=document.getElementById('btn-tpl-overwrite');if(owb)owb.style.display='none';
  document.getElementById('template-list-container').innerHTML =
    '<div style="padding:20px;text-align:center;color:#aaa;font-size:12px;">Loading...</div>';
  document.getElementById('modal-templates').classList.add('open');
  if(_bridge) _bridge.getLayoutTemplates();
}

function receiveLayoutTemplates(templates){
  _allTemplates = templates;
  // Default-Template anwenden sobald Templates ankommen (async nach init)
  // inp-count existiert = init() ist durch
  if(document.getElementById('inp-count')) applyDefaultTemplate();
  var container = document.getElementById('template-list-container');
  if(!container) return;
  container.innerHTML = '';
  if(!templates.length){
    container.innerHTML = '<div style="padding:16px;text-align:center;color:#aaa;font-size:12px;">No templates found</div>';
    return;
  }
  templates.forEach(function(tpl){
    var item = document.createElement('div');
    item.className = 'template-item' + (tpl.isDefault?' is-default':'');
    item.dataset.id = tpl.id;

    var info = document.createElement('div');info.style.flex='1';
    var name = document.createElement('div');name.className='tpl-name';name.textContent=tpl.name;
    var desc = document.createElement('div');desc.className='tpl-blocks';
    // Blöcke als kompakte Vorschau
    if(tpl.blocks && tpl.blocks.length){
      desc.textContent = tpl.blocks.map(function(b){
        var xDef=X_AXES.find(function(a){return a.key===b.xKey;})||{title:b.xKey||'?'};
        var yDef=Y_AXES.find(function(a){return a.key===b.yKey;})||{title:b.yKey||'?'};
        return (b.chartType||'bar').toUpperCase()+': '+xDef.title+' / '+yDef.title;
      }).join('  •  ');
    }
    info.appendChild(name);
    if(tpl.description){var d2=document.createElement('div');d2.className='tpl-desc';d2.textContent=tpl.description;info.appendChild(d2);}
    info.appendChild(desc);

    var btnDel = document.createElement('button');
    btnDel.className='tpl-del';btnDel.textContent='✕';btnDel.title='Delete template';
    btnDel.addEventListener('click',function(e){
      e.stopPropagation();
      if(!confirm('Delete template "'+tpl.name+'"?')) return;
      if(_bridge) _bridge.deleteLayoutTemplate(String(tpl.id));
    });

    item.appendChild(info);
    if(!tpl.isDefault) item.appendChild(btnDel); // Standard nicht löschbar
    item.addEventListener('click',function(){
      container.querySelectorAll('.template-item').forEach(function(el){el.classList.remove('selected');});
      item.classList.add('selected');
      _selectedTemplateId = tpl.id;
      document.getElementById('btn-tpl-apply').disabled = false;
      // Overwrite-Button: fuer nicht-default Templates immer, fuer das
      // Standard-Template nur fuer Superuser (Backend erzwingt das ohnehin
      // nochmal serverseitig, siehe overwriteLayoutTemplate).
      var owBtn=document.getElementById('btn-tpl-overwrite');
      if(owBtn) owBtn.style.display=(tpl.isDefault && !IS_SUPERUSER)?'none':'';
      // Name/Desc vorausfüllen
      var nameInp=document.getElementById('tpl-save-name');
      var descInp=document.getElementById('tpl-save-desc');
      if(nameInp) nameInp.value=tpl.name;
      if(descInp) descInp.value=tpl.description||'';
    });
    // Doppelklick = sofort anwenden
    item.addEventListener('dblclick',function(){ applyTemplate(tpl); document.getElementById('modal-templates').classList.remove('open'); });
    container.appendChild(item);
  });
}

function applyTemplate(tpl){
  if(!tpl || !tpl.blocks || !tpl.blocks.length) return;
  syncNotesToState();
  chartStates = {};
  tpl.blocks.forEach(function(b, i){
    chartStates[i] = {
      blockType: 'chart',
      chartType: b.chartType || 'bar',
      xField:    b.xKey     || X_DEFAULT,
      yKey:      b.yKey     || (Y_AXES[0]?Y_AXES[0].key:'titer'),
      yKeys:     b.yKeys    || [b.yKey || (Y_AXES[0]?Y_AXES[0].key:'titer')],
      zField:    b.zKey     || X_DEFAULT,
      mode:      b.chartType==='3d'?'3d':'2d',
      noteTitle: '', noteText: '', noteVisible: false,
    };
  });
  document.getElementById('inp-count').value = tpl.blocks.length;
  rebuildGrid();
}

document.getElementById('btn-templates').addEventListener('click', openTemplatesModal);
document.getElementById('tpl-modal-cancel').addEventListener('click',function(){
  document.getElementById('modal-templates').classList.remove('open');
});
document.getElementById('modal-templates').addEventListener('click',function(e){
  if(e.target===this) this.classList.remove('open');
});
document.getElementById('btn-tpl-apply').addEventListener('click',function(){
  var tpl=_allTemplates.find(function(t){return t.id===_selectedTemplateId;});
  if(tpl){ applyTemplate(tpl); document.getElementById('modal-templates').classList.remove('open'); }
});
document.getElementById('btn-tpl-overwrite').addEventListener('click',function(){
  if(!_selectedTemplateId) return;
  var name=document.getElementById('tpl-save-name').value.trim();
  var desc=document.getElementById('tpl-save-desc').value.trim();
  if(!name){ document.getElementById('tpl-save-name').style.borderColor='#e74c3c'; return; }
  document.getElementById('tpl-save-name').style.borderColor='';
  syncNotesToState();
  var total=Math.max(1,parseInt(document.getElementById('inp-count').value)||1);
  var blocks=[];
  for(var i=0;i<total;i++){
    var s=getState(i);
    if(s.blockType==='image') continue;
    blocks.push({chartType:s.chartType||'bar',xKey:s.xField||X_DEFAULT,yKey:s.yKey||(Y_AXES[0]?Y_AXES[0].key:'titer'),yKeys:s.yKeys||[s.yKey||(Y_AXES[0]?Y_AXES[0].key:'titer')],zKey:s.zField||X_DEFAULT});
  }
  if(!blocks.length) return;
  var payload={id:_selectedTemplateId,name:name,description:desc,blocks:blocks};
  if(_bridge) _bridge.overwriteLayoutTemplate(JSON.stringify(payload));
});

document.getElementById('btn-tpl-save-new').addEventListener('click',function(){
  var name=document.getElementById('tpl-save-name').value.trim();
  if(!name){ document.getElementById('tpl-save-name').style.borderColor='#e74c3c'; return; }
  document.getElementById('tpl-save-name').style.borderColor='';
  var desc=document.getElementById('tpl-save-desc').value.trim();
  syncNotesToState();
  var total=Math.max(1,parseInt(document.getElementById('inp-count').value)||1);
  var blocks=[];
  for(var i=0;i<total;i++){
    var s=getState(i);
    if(s.blockType==='image') continue;
    blocks.push({chartType:s.chartType||'bar',xKey:s.xField||X_DEFAULT,yKey:s.yKey||(Y_AXES[0]?Y_AXES[0].key:'titer'),yKeys:s.yKeys||[s.yKey||(Y_AXES[0]?Y_AXES[0].key:'titer')],zKey:s.zField||X_DEFAULT});
  }
  if(!blocks.length) return;
  var payload={name:name,description:desc,createdBy:CURRENT_USER||'',blocks:blocks};
  if(_bridge) _bridge.saveLayoutTemplate(JSON.stringify(payload));
});

function receiveLayoutTemplateSaved(success, message){
  if(success){
    document.getElementById('tpl-save-name').value='';
    document.getElementById('tpl-save-desc').value='';
    var owb=document.getElementById('btn-tpl-overwrite');if(owb)owb.style.display='none';
    _selectedTemplateId=null;
    document.getElementById('btn-tpl-apply').disabled=true;
    if(_bridge) _bridge.getLayoutTemplates();
  } else {
    alert('Save failed: '+message);
  }
}

function receiveLayoutTemplateDeleted(success, id){
  if(success && _bridge) _bridge.getLayoutTemplates();
}

// Default-Template beim Start anwenden (nur wenn chartStates leer)
function applyDefaultTemplate(){
  if(Object.keys(chartStates).length>0) return; // bereits konfiguriert
  var def=_allTemplates.find(function(t){return t.isDefault;});
  if(def) applyTemplate(def);
}

// ── Free Query Builder ───────────────────────────────────────────────────────
var _fqbTables      = [];   // [{tableName, displayLabel}]
var _fqbJoinPaths   = {};   // {fromTable: [{toTable, joinSQL}]}
var _fqbActiveTables= [];   // [tableName] — Basistabelle + gejointen Tabellen
var _fqbColumns     = {};   // {tableName: [colName]}
var _fqbFilterCount = 0;

// Welche Felder pro Chart-Typ sichtbar sind
var FQB_CHART_FIELDS = {
  scatter: {z:false, color:true,  label:true,  xLabel:'X',          yLabel:'Y'},
  bar:     {z:false, color:true,  label:false, xLabel:'X (Kategorie)', yLabel:'Y (Wert)'},
  stack:   {z:false, color:true,  label:false, xLabel:'X (Kategorie)', yLabel:'Y (Wert)'},
  line:    {z:false, color:true,  label:false, xLabel:'X',          yLabel:'Y'},
  box:     {z:false, color:false, label:false, xLabel:'X (Kategorie)', yLabel:'Y (Wert)'},
  heat:    {z:true,  color:false, label:false, xLabel:'X',          yLabel:'Y'},
  '3d':    {z:true,  color:true,  label:false, xLabel:'X',          yLabel:'Y'},
};

function _fqbUpdateFieldVisibility(){
  var ct = document.getElementById('fqb-chart-type');
  if(!ct) return;
  var type = ct.value || 'scatter';
  var cfg  = FQB_CHART_FIELDS[type] || FQB_CHART_FIELDS.scatter;
  // Z-Feld
  var rowZ = document.getElementById('fqb-row-z');
  if(rowZ) rowZ.style.display = cfg.z ? '' : 'none';
  // Color
  var rowC = document.getElementById('fqb-row-color');
  if(rowC) rowC.style.display = cfg.color ? '' : 'none';
  // Label
  var rowL = document.getElementById('fqb-row-label');
  if(rowL) rowL.style.display = cfg.label ? '' : 'none';
  // X/Y Labels anpassen
  var axRows = document.querySelectorAll('#fqb-axes-section .fqb-axis-row');
  axRows.forEach(function(row){
    var lbl = row.querySelector('label');
    var sel = row.querySelector('select');
    if(!lbl||!sel) return;
    if(sel.id==='fqb-x') lbl.textContent = cfg.xLabel;
    if(sel.id==='fqb-y') lbl.textContent = cfg.yLabel;
  });
  // Z-Achsen-Label
  if(cfg.z){
    var rowZlbl = document.querySelector('#fqb-row-z label');
    if(rowZlbl) rowZlbl.textContent = type==='heat' ? 'Value' : 'Z';
  }
}

function initFreeQueryTab(){
  // Block-Selector EventListener
  var blockSel = document.getElementById('fqb-block-selector');
  if(blockSel){
    blockSel.addEventListener('change', function(){
      // State des aktuellen Blocks speichern
      _saveFqbStateForBlock(_activeFqbBlockIdx);
      // Neuen Block laden
      _activeFqbBlockIdx = parseInt(this.value)||0;
      _loadFqbStateForBlock(_activeFqbBlockIdx);
    });
  }

  // Chart-Typ Change
  var ctSel = document.getElementById('fqb-chart-type');
  if(ctSel){
    ctSel.addEventListener('change', function(){
      _fqbUpdateFieldVisibility();
      _fqbUpdatePreview();
    });
    _fqbUpdateFieldVisibility(); // Initial
  }

  // tab-free wird nicht mehr als Tab verwendet — Mode Toggle übernimmt
  var _tabFreeEl = document.getElementById('tab-free');
  if(_tabFreeEl) _tabFreeEl.addEventListener('click', function(){
    _activeFilterTab = 'free';
    if(_fqbTables.length===0 && _bridge) _bridge.getFreeQueryMeta();
  });

  document.getElementById('fqb-base-table').addEventListener('change', function(){
    var tbl = this.value;
    _fqbActiveTables = tbl ? [tbl] : [];
    _fqbUpdateJoinSelect();
    _fqbUpdateAxes();
    _fqbUpdatePreview();
    document.getElementById('fqb-join-section').style.display    = tbl ? '' : 'none';
    document.getElementById('fqb-axes-section').style.display    = tbl ? '' : 'none';
    document.getElementById('fqb-filter-section').style.display  = tbl ? '' : 'none';
    document.getElementById('fqb-groupby-section').style.display = tbl ? '' : 'none';
    document.getElementById('fqb-series-section').style.display  = tbl ? '' : 'none';
    document.getElementById('fqb-limit-section').style.display   = tbl ? '' : 'none';
    document.getElementById('fqb-join-pills').innerHTML = '';
  });

  document.getElementById('btn-fqb-add-join').addEventListener('click', function(){
    var sel = document.getElementById('fqb-join-select');
    var tbl = sel.value;
    if(!tbl || _fqbActiveTables.indexOf(tbl)!==-1) return;
    _fqbActiveTables.push(tbl);
    _fqbRenderJoinPills();
    _fqbUpdateJoinSelect();
    _fqbUpdateAxes();
    _fqbUpdatePreview();
    sel.value = '';
  });

  document.getElementById('btn-fqb-add-filter').addEventListener('click', function(){
    _fqbAddFilterRow();
  });
}

function receiveFreeQueryMeta(tables, joinPaths, columns){
  _fqbTables    = tables;
  _fqbJoinPaths = joinPaths;
  _fqbColumns   = columns;
  // Group By Dropdown im Free Tab befüllen
  var gbSel = document.getElementById('fqb-groupby');
  if(gbSel && G_AXES && G_AXES.length){
    gbSel.innerHTML = '<option value="">— none —</option>' +
      G_AXES.map(function(g){return'<option value="'+g.key+'">'+g.title+'</option>';}).join('');
  }
  // Trial Series im Free Tab befüllen
  var seSel = document.getElementById('fqb-series-sel');
  if(seSel && _allSeriesForBuilder && _allSeriesForBuilder.length){
    seSel.innerHTML = _allSeriesForBuilder.map(function(s){
      return'<option value="'+s.pk+'">'+s.name+'</option>';
    }).join('');
  }


  var sel = document.getElementById('fqb-base-table');
  sel.innerHTML = '<option value="">— Select table —</option>' +
    tables.map(function(t){
      return '<option value="'+t.tableName+'">'+t.displayLabel+'</option>';
    }).join('');
}

function _fqbUpdateJoinSelect(){
  var sel = document.getElementById('fqb-join-select');

  // Erreichbare Tabellen: aus JoinPaths von allen aktiven Tabellen
  var reachable = [];
  _fqbActiveTables.forEach(function(tbl){
    var paths = _fqbJoinPaths[tbl] || [];
    paths.forEach(function(p){
      if(_fqbActiveTables.indexOf(p.toTable)===-1 &&
         reachable.indexOf(p.toTable)===-1){
        reachable.push(p.toTable);
      }
    });
  });
  sel.innerHTML = '<option value="">— Available tables —</option>' +
    reachable.map(function(t){
      var meta = _fqbTables.find(function(x){return x.tableName===t;});
      var label = meta ? meta.displayLabel : t;
      return '<option value="'+t+'">'+label+'</option>';
    }).join('');
}

function _fqbRenderJoinPills(){
  var container = document.getElementById('fqb-join-pills');
  container.innerHTML = '';
  // Nur gejointen Tabellen (ohne Basistabelle)
  _fqbActiveTables.slice(1).forEach(function(tbl){
    var meta = _fqbTables.find(function(x){return x.tableName===tbl;});
    var label = meta ? meta.displayLabel : tbl;
    var pill = document.createElement('span');
    pill.className = 'fqb-table-pill';
    pill.innerHTML = label + '<span class="fqb-rm" data-tbl="'+tbl+'">×</span>';
    pill.querySelector('.fqb-rm').addEventListener('click', function(){
      var t = this.dataset.tbl;
      _fqbActiveTables = _fqbActiveTables.filter(function(x){return x!==t;});
      _fqbRenderJoinPills();
      _fqbUpdateJoinSelect();
      _fqbUpdateAxes();
      _fqbUpdatePreview();
    });
    container.appendChild(pill);
  });
}

function _fqbGetAllColumns(){
  // Alle Spalten aller aktiven Tabellen als [{table, col, label}]
  var result = [];
  _fqbActiveTables.forEach(function(tbl){
    var cols = _fqbColumns[tbl] || [];
    var meta = _fqbTables.find(function(x){return x.tableName===tbl;});
    var tblLabel = meta ? meta.displayLabel : tbl;
    cols.forEach(function(col){
      result.push({table:tbl, col:col, label:tblLabel+'.'+col, value:tbl+'::'+col});
    });
  });
  return result;
}

function _fqbUpdateAxes(){
  var cols = _fqbGetAllColumns();
  var opts = '<option value="">— none —</option>' +
    cols.map(function(c){return'<option value="'+c.value+'">'+c.label+'</option>';}).join('');
  var optsReq = cols.map(function(c){return'<option value="'+c.value+'">'+c.label+'</option>';}).join('');
  document.getElementById('fqb-x').innerHTML     = optsReq;
  document.getElementById('fqb-y').innerHTML     = optsReq;
  var fqbZ = document.getElementById('fqb-z');
  if(fqbZ) fqbZ.innerHTML = opts;
  document.getElementById('fqb-color').innerHTML = opts;
  document.getElementById('fqb-label').innerHTML = opts;
  _fqbUpdateFieldVisibility();
  // Filter-Felder aktualisieren
  _fqbUpdateFilterFields();
}

function _fqbUpdateFilterFields(){
  // Bestehende Filter-Rows neu befüllen mit aktuellen Feldern
  var opts = _fqbGetAllColumns().map(function(c){
    return '<option value="'+c.value+'">'+c.label+'</option>';
  }).join('');
  document.querySelectorAll('#fqb-filter-rows .fqb-field-sel').forEach(function(sel){
    var cur = sel.value;
    sel.innerHTML = '<option value="">— Field —</option>'+opts;
    if(cur) sel.value = cur;
  });
}

var _fqbFilterCnt = 0;
function _fqbAddFilterRow(prefill){
  var container = document.getElementById('fqb-filter-rows');
  var isFirst   = container.children.length===0;
  var cols      = _fqbGetAllColumns();
  var rowIdx    = ++_fqbFilterCnt;

  var row = document.createElement('div');
  row.className='adv-filter-row'; row.id='fqbrow_'+rowIdx;

  var conn=document.createElement('div');conn.className='adv-connector';
  conn.textContent=isFirst?'WHERE':'AND';

  var selField=document.createElement('select');
  selField.className='adv-field-select fqb-field-sel';
  selField.innerHTML='<option value="">— Field —</option>'+
    cols.map(function(c){return'<option value="'+c.value+'">'+c.label+'</option>';}).join('');

  var selOp=document.createElement('select');
  selOp.style.cssText='font-size:11px;padding:4px;border:1px solid #d0d0d0;border-radius:4px;background:#fafafa;outline:none;font-family:inherit;width:100%;';
  selOp.innerHTML=['=','!=','>','<','>=','<=','LIKE','NOT LIKE','IS NULL','IS NOT NULL'].map(function(o){
    return'<option value="'+o+'">'+o+'</option>';
  }).join('');

  var inp=document.createElement('input');
  inp.type='text';inp.placeholder='Value...';
  inp.style.cssText='width:100%;font-size:11px;padding:4px 6px;border:1px solid #d0d0d0;border-radius:4px;background:#fafafa;outline:none;font-family:inherit;';
  inp.addEventListener('input',_fqbUpdatePreview);

  selOp.addEventListener('change',function(){
    inp.style.display=(this.value==='IS NULL'||this.value==='IS NOT NULL')?'none':'';
    _fqbUpdatePreview();
  });
  selField.addEventListener('change',_fqbUpdatePreview);

  var btnRm=document.createElement('button');
  btnRm.style.cssText='width:22px;height:22px;border:none;background:none;color:#ccc;font-size:16px;cursor:pointer;padding:0;border-radius:3px;';
  btnRm.textContent='×';
  btnRm.addEventListener('click',function(){
    container.removeChild(row);
    Array.from(container.children).forEach(function(r,i){
      var c2=r.querySelector('.adv-connector');if(c2)c2.textContent=i===0?'WHERE':'AND';
    });
    _fqbUpdatePreview();
  });

  row.appendChild(conn);row.appendChild(selField);row.appendChild(selOp);row.appendChild(inp);row.appendChild(btnRm);
  container.appendChild(row);

  if(prefill){
    selField.value=prefill.field||'';
    if(prefill.op) selOp.value=prefill.op;
    if(prefill.value) inp.value=prefill.value;
    if(prefill.op==='IS NULL'||prefill.op==='IS NOT NULL') inp.style.display='none';
  }
  _fqbUpdatePreview();
}

function _fqbGetFilters(){
  var result=[];
  document.querySelectorAll('#fqb-filter-rows .adv-filter-row').forEach(function(row){
    var f=row.querySelector('.fqb-field-sel');
    var o=row.querySelector('select:not(.fqb-field-sel)');
    var v=row.querySelector('input');
    if(!f||!f.value) return;
    var parts=f.value.split('::');
    var op=o?o.value:'=';
    if(op==='IS NULL'||op==='IS NOT NULL'){result.push({table:parts[0],field:parts[1],op:op,value:null});return;}
    if(!v||!v.value.trim()) return;
    result.push({table:parts[0],field:parts[1],op:op,value:v.value.trim()});
  });
  return result;
}

function _fqbUpdatePreview(){
  var preview=document.getElementById('fqb-sql-preview');
  if(!preview) return;
  var base=document.getElementById('fqb-base-table').value;
  if(!base){preview.style.display='none';return;}
  var xVal=document.getElementById('fqb-x').value;
  var yVal=document.getElementById('fqb-y').value;
  var colorVal=document.getElementById('fqb-color').value;
  var filters=_fqbGetFilters();
  var limit=document.getElementById('fqb-limit').value||500;
  var lines=['SELECT'];
  var selCols=[];
  if(xVal) selCols.push(xVal.replace('::','.'));
  if(yVal) selCols.push(yVal.replace('::','.'));
  if(colorVal) selCols.push(colorVal.replace('::','.'));
  lines.push('  '+(selCols.length?selCols.join(', '):'*'));
  lines.push('FROM '+base);
  _fqbActiveTables.slice(1).forEach(function(tbl){
    var path=(_fqbJoinPaths[base]||[]).find(function(p){return p.toTable===tbl;}) ||
             (_fqbJoinPaths[_fqbActiveTables[0]]||[]).find(function(p){return p.toTable===tbl;});
    if(path) lines.push(path.joinSQL);
  });
  if(filters.length){
    filters.forEach(function(f,i){
      var prefix=i===0?'WHERE':'AND  ';
      var expr=f.table+'.'+f.field+' '+f.op+((f.op==='IS NULL'||f.op==='IS NOT NULL')?'':' '+f.value);
      lines.push(prefix+' '+expr);
    });
  }
  lines.push('LIMIT '+limit);
  preview.style.display='block';
  preview.textContent=lines.join(String.fromCharCode(10));
}

function getFreeQueryConfig(){
  var xVal=document.getElementById('fqb-x').value;
  var yVal=document.getElementById('fqb-y').value;
  var colorVal=document.getElementById('fqb-color').value;
  var labelVal=document.getElementById('fqb-label').value;
  var ctEl=document.getElementById('fqb-chart-type');
  var zEl =document.getElementById('fqb-z');
  var titleEl=document.getElementById('fqb-chart-title');
  var gbEl=document.getElementById('fqb-groupby');
  var seSel=document.getElementById('fqb-series-sel');
  var seriesPKs=[];
  if(seSel){for(var i=0;i<seSel.options.length;i++){if(seSel.options[i].selected&&seSel.options[i].value)seriesPKs.push(parseInt(seSel.options[i].value));}}
  return {baseTable:    document.getElementById('fqb-base-table').value,
    joinTables:   _fqbActiveTables.slice(1),
    chartType:    ctEl ? ctEl.value : 'scatter',
    chartTitle:   titleEl ? titleEl.value.trim() : '',
    xField:       xVal,
    yField:       yVal,
    zField:       zEl ? zEl.value : '',
    colorField:   colorVal,
    labelField:   labelVal,
    groupBy:      gbEl ? gbEl.value : '',
    seriesPKs:    seriesPKs,
    filters:      _fqbGetFilters(),
    limit:        parseInt(document.getElementById('fqb-limit').value)||500,
  };
}

// ── Advanced Filter ──────────────────────────────────────────────────────────
var _advFields = [];
var _advFilterCount = 0;
var _activeFilterTab = 'simple';

var _builderMode = 'trial'; // 'trial' | 'free'

function _setBuilderMode(mode){
  _builderMode = mode;
  // Toggle Buttons
  document.getElementById('btn-mode-trial').classList.toggle('active', mode==='trial');
  document.getElementById('btn-mode-free').classList.toggle('active',  mode==='free');
  // Panels
  document.getElementById('panel-trial-mode').style.display = mode==='trial' ? '' : 'none';
  document.getElementById('panel-free-mode').style.display  = mode==='free'  ? 'flex' : 'none';
  // Block-Selector ist im Free Panel — automatisch sichtbar wenn Panel sichtbar
  // activeFilterTab
  _activeFilterTab = mode==='free' ? 'free' : 'simple';
  if(mode==='free' && _fqbTables.length===0 && _bridge) _bridge.getFreeQueryMeta();
  // Block-Selector aktualisieren
  _syncFqbBlockSelector();
  // Grid neu bauen damit Toolbars korrekt sind
  rebuildGrid();
}

function _fqbPopulateAxesFromTrialData(){
  // X-Achsen aus X_AXES
  var xSel = document.getElementById('fqb-x');
  var ySel = document.getElementById('fqb-y');
  if(!xSel||!ySel) return;
  var xOpts = X_AXES.map(function(a){
    var l=a.unit?a.title+' ('+a.unit+')':a.title;
    return '<option value="'+a.key+'">'+l+'</option>';
  }).join('');
  var yOpts = Y_AXES.map(function(a){
    var l=a.unit?a.title+' ('+a.unit+')':a.title;
    return '<option value="'+a.key+'">'+l+'</option>';
  }).join('');
  xSel.innerHTML = xOpts;
  ySel.innerHTML = yOpts;
  // Color + Label aus G_AXES
  var colorSel = document.getElementById('fqb-color');
  var labelSel = document.getElementById('fqb-label');
  var gOpts = '<option value="">— none —</option>'+
    G_AXES.map(function(g){return'<option value="'+g.key+'">'+g.title+'</option>';}).join('');
  if(colorSel) colorSel.innerHTML = gOpts;
  if(labelSel) labelSel.innerHTML = gOpts;
  // Group By
  var gbSel = document.getElementById('fqb-groupby');
  if(gbSel && G_AXES.length){
    gbSel.innerHTML = '<option value="">— none —</option>'+
      G_AXES.map(function(g){return'<option value="'+g.key+'">'+g.title+'</option>';}).join('');
  }
  _fqbUpdateFieldVisibility();
}

function _populateGroupBy(){
  var sel = document.getElementById('b-groupby');
  if(!sel) return;
  var current = sel.value;
  // Komplett aus G_AXES (DB) — keine Hardcodes
  if(G_AXES && G_AXES.length){
    sel.innerHTML = G_AXES.map(function(g){
      return '<option value="'+g.key+'"'+(g.key===current?' selected':'')+'>'+g.title+'</option>';
    }).join('');
  }
}

function initFilterTabs(){
  document.getElementById('tab-simple').addEventListener('click', function(){
    _activeFilterTab='simple';
    this.classList.add('active');
    document.getElementById('tab-advanced').classList.remove('active');
    document.getElementById('panel-simple').classList.add('active');
    document.getElementById('panel-advanced').classList.remove('active');
  });
  document.getElementById('tab-advanced').addEventListener('click', function(){
    _activeFilterTab='advanced';
    this.classList.add('active');
    document.getElementById('tab-simple').classList.remove('active');
    document.getElementById('panel-advanced').classList.add('active');
    document.getElementById('panel-simple').classList.remove('active');
    if(_advFields.length===0 && _bridge) _bridge.getAdvancedFilterFields();
  });
  document.getElementById('btn-add-adv-filter').addEventListener('click', function(){ addAdvFilterRow(); });
  // tab-free existiert nicht mehr in den Tabs — wird über Mode Toggle gesteuert
  var tabFree = document.getElementById('tab-free');
  if(tabFree) tabFree.style.display='none';
}

function receiveAdvancedFilterFields(fields){
  _advFields = fields;
  var container = document.getElementById('adv-filter-rows');
  if(container && container.children.length===0) addAdvFilterRow();
  _updateAdvPreview();
}

function receiveAdvancedFieldValues(tableField, values){
  _advFields.forEach(function(f){
    if((f.table+'::'+f.field)===tableField) f.lookupVals=values;
  });
  document.querySelectorAll('[data-lookup="'+tableField+'"]').forEach(function(sel){
    var prev = Array.from(sel.selectedOptions).map(function(o){return o.value;});
    sel.innerHTML = values.map(function(v){
      return '<option value="'+v+'"'+(prev.indexOf(v)!==-1?' selected':'')+'>'+v+'</option>';
    }).join('');
  });
}

function addAdvFilterRow(prefill){
  var container = document.getElementById('adv-filter-rows');
  if(!container) return;
  var isFirst = container.children.length===0;
  var rowIdx  = ++_advFilterCount;

  var row = document.createElement('div');
  row.className='adv-filter-row'; row.id='advrow_'+rowIdx;

  var conn = document.createElement('div');
  conn.className='adv-connector';
  conn.textContent = isFirst ? 'WHERE' : 'AND';

  var selField = document.createElement('select');
  selField.className='adv-field-select';
  selField.innerHTML='<option value="">— Field —</option>'+
    _advFields.map(function(f){
      return '<option value="'+f.table+'::'+f.field+'">'+f.label+'</option>';
    }).join('');

  var selOp = document.createElement('select');
  selOp.style.cssText='font-size:11px;padding:4px;border:1px solid #d0d0d0;border-radius:4px;background:#fafafa;outline:none;font-family:inherit;width:100%;';

  var valWrap = document.createElement('div');
  valWrap.style.cssText='min-width:0;';

  function getOpsForType(type){
    if(type==='numeric') return ['=','!=','>','<','>=','<=','IS NULL'];
    if(type==='lookup')  return ['=','!=','IN','IS NULL'];
    return ['=','!=','LIKE','IS NULL'];
  }

  function buildValueWidget(fdef, op){
    valWrap.innerHTML='';
    if(op==='IS NULL'){
      var s=document.createElement('span');
      s.style.cssText='font-size:10px;color:#aaa;padding:5px 4px;display:block;';
      s.textContent='(no value)'; valWrap.appendChild(s); return;
    }
    if(fdef && (fdef.type==='lookup') && op!=='LIKE'){
      var sel=document.createElement('select');
      sel.multiple=true; sel.size=3;
      sel.style.cssText='width:100%;font-size:11px;padding:2px 4px;border:1px solid #d0d0d0;border-radius:4px;background:#fafafa;outline:none;font-family:inherit;';
      sel.dataset.lookup=fdef.table+'::'+fdef.field;
      if(fdef.lookupVals && fdef.lookupVals.length){
        sel.innerHTML=fdef.lookupVals.map(function(v){return'<option value="'+v+'">'+v+'</option>';}).join('');
      } else {
        sel.innerHTML='<option>Loading...</option>';
        if(_bridge) _bridge.getAdvancedFieldValues(fdef.table,fdef.field);
      }
      sel.addEventListener('change',_updateAdvPreview);
      valWrap.appendChild(sel);
    } else {
      var inp=document.createElement('input');
      inp.type=(fdef&&fdef.type==='numeric')?'number':'text';
      inp.step='any'; inp.placeholder='Value...';
      inp.style.cssText='width:100%;font-size:11px;padding:4px 6px;border:1px solid #d0d0d0;border-radius:4px;background:#fafafa;outline:none;font-family:inherit;';
      inp.addEventListener('input',_updateAdvPreview);
      valWrap.appendChild(inp);
    }
  }

  function refreshRow(){
    var parts=(selField.value||'').split('::');
    var fdef=_advFields.find(function(f){return f.table===parts[0]&&f.field===parts[1];})||null;
    var ops=getOpsForType(fdef?fdef.type:'text');
    selOp.innerHTML=ops.map(function(o){return'<option value="'+o+'">'+o+'</option>';}).join('');
    buildValueWidget(fdef, selOp.value);
    _updateAdvPreview();
  }

  selField.addEventListener('change', refreshRow);
  selOp.addEventListener('change', function(){
    var parts=(selField.value||'').split('::');
    var fdef=_advFields.find(function(f){return f.table===parts[0]&&f.field===parts[1];})||null;
    buildValueWidget(fdef,selOp.value);
    _updateAdvPreview();
  });

  var btnRm=document.createElement('button');
  btnRm.style.cssText='width:22px;height:22px;border:none;background:none;color:#ccc;font-size:16px;cursor:pointer;padding:0;border-radius:3px;';
  btnRm.textContent='×';
  btnRm.addEventListener('click',function(){
    container.removeChild(row);
    // WHERE/AND Labels neu setzen
    Array.from(container.children).forEach(function(r,i){
      var c2=r.querySelector('.adv-connector');
      if(c2) c2.textContent=i===0?'WHERE':'AND';
    });
    _updateAdvPreview();
  });

  row.appendChild(conn); row.appendChild(selField); row.appendChild(selOp);
  row.appendChild(valWrap); row.appendChild(btnRm);
  container.appendChild(row);

  // Prefill
  if(prefill){
    var matchField=_advFields.find(function(f){return f.table===prefill.table&&f.field===prefill.field;});
    if(matchField) selField.value=prefill.table+'::'+prefill.field;
    refreshRow();
    if(prefill.op) selOp.value=prefill.op;
    setTimeout(function(){
      buildValueWidget(matchField||null,selOp.value);
      setTimeout(function(){
        var w=valWrap.querySelector('input,select');
        if(!w) return;
        if(prefill.values && w.tagName==='SELECT'){
          Array.from(w.options).forEach(function(o){o.selected=prefill.values.indexOf(o.value)!==-1;});
        } else if(prefill.value!==undefined){ w.value=prefill.value; }
        _updateAdvPreview();
      },120);
    },50);
  } else {
    refreshRow();
  }
}

function getAdvFilters(){
  var rows=document.querySelectorAll('#adv-filter-rows .adv-filter-row');
  var result=[];
  rows.forEach(function(row){
    var selField=row.querySelector('.adv-field-select');
    var selOp=row.querySelector('select:not(.adv-field-select)');
    if(!selField||!selField.value) return;
    var parts=selField.value.split('::');
    var table=parts[0],field=parts[1];
    var op=selOp?selOp.value:'=';
    if(op==='IS NULL'){ result.push({table,field,op,value:null,values:[]}); return; }
    var w=row.querySelector('.filter-value-widget, input, select:not(.adv-field-select):not([data-lookup])');
    // Lookup multi-select
    var lookup=row.querySelector('[data-lookup]');
    if(lookup){
      var vals=Array.from(lookup.selectedOptions).map(function(o){return o.value;}).filter(Boolean);
      if(!vals.length) return;
      result.push({table,field,op:'IN',value:null,values:vals});
    } else {
      var inp=row.querySelector('input');
      if(!inp||!inp.value.trim()) return;
      result.push({table,field,op,value:inp.value.trim(),values:[]});
    }
  });
  return result;
}

function _updateAdvPreview(){
  var preview=document.getElementById('adv-preview');
  if(!preview) return;
  var filters=getAdvFilters();
  if(!filters.length){ preview.style.display='none'; return; }
  preview.style.display='block';
  preview.textContent=filters.map(function(f,i){
    var prefix=i===0?'WHERE':'AND  ';
    if(f.op==='IS NULL') return prefix+f.table+'.'+f.field+' IS NULL';
    if(f.op==='IN') return prefix+f.table+'.'+f.field+' IN ('+f.values.join(', ')+')';
    return prefix+f.table+'.'+f.field+' '+f.op+' '+f.value;
  }).join(String.fromCharCode(10));
}

// ── Query Templates ──────────────────────────────────────────────────────────
var _allQueryTemplates = [], _selectedQTplId = null, _qtplTabFilter = 0;
var IS_SUPERUSER = false; // wird vom Bridge gesetzt

function openQueryTemplatesModal(){
  _selectedQTplId = null;
  document.getElementById('btn-qtpl-apply').disabled = true;
  document.getElementById('qtpl-name').value = '';
  document.getElementById('qtpl-desc').value = '';
  document.getElementById('modal-query-templates').classList.add('open');
  if(_bridge){ _bridge.getQueryTemplates(); _bridge.checkSuperuser(); }
}

function receiveQueryTemplates(templates){
  _allQueryTemplates = templates;
  _renderQTplList();
}

function receiveIsSuperuser(val){
  IS_SUPERUSER = !!val;
  // Superuser darf Level 3 Option anbieten
  var lvlSel = document.getElementById('qtpl-level');
  if(lvlSel && IS_SUPERUSER){
    if(!lvlSel.querySelector('option[value="3"]')){
      var opt = document.createElement('option');
      opt.value='3'; opt.textContent='⭐ Certified (superuser only)';
      lvlSel.appendChild(opt);
    }
  }
  _renderQTplList(); // re-render mit Superuser-Buttons
}

function _renderQTplList(){
  var container = document.getElementById('qtpl-list-container');
  if(!container) return;
  container.innerHTML = '';

  var filtered = _allQueryTemplates.filter(function(t){
    if(_qtplTabFilter === 0) return true;
    return t.visibilityLevel === _qtplTabFilter;
  });

  if(!filtered.length){
    container.innerHTML = '<div style="padding:16px;text-align:center;color:#aaa;font-size:12px;">No templates found</div>';
    return;
  }

  var levelLabel = ['','👤 Personal','👥 Shared','⭐ Certified'];
  var levelClass = ['','lvl1','lvl2','lvl3'];

  filtered.forEach(function(tpl){
    var item = document.createElement('div');
    item.className = 'qtpl-item';
    item.dataset.id = tpl.id;

    var badge = document.createElement('span');
    badge.className = 'qtpl-badge ' + (levelClass[tpl.visibilityLevel]||'lvl1');
    badge.textContent = levelLabel[tpl.visibilityLevel]||'Personal';

    var info = document.createElement('div');info.style.flex='1';info.style.minWidth='0';
    var name = document.createElement('div');name.className='qtpl-name';name.textContent=tpl.name;
    var meta = document.createElement('div');meta.className='qtpl-meta';
    meta.textContent = 'By '+tpl.createdBy + (tpl.certifiedBy?' • ⭐ '+tpl.certifiedBy:'');
    if(tpl.description){var desc=document.createElement('div');desc.className='qtpl-desc';desc.textContent=tpl.description;info.appendChild(desc);}
    info.appendChild(name);info.appendChild(meta);

    var actions = document.createElement('div');actions.className='qtpl-actions';

    // Certify Button (nur Superuser, nur Level 2)
    if(IS_SUPERUSER && tpl.visibilityLevel === 2){
      var btnCert = document.createElement('button');
      btnCert.className='qtpl-btn certify';btnCert.textContent='⭐ Certify';
      btnCert.addEventListener('click',function(e){
        e.stopPropagation();
        if(confirm('Certify "'+tpl.name+'" as Level 3?'))
          if(_bridge) _bridge.certifyQueryTemplate(String(tpl.id));
      });
      actions.appendChild(btnCert);
    }

    // Delete Button (eigene oder Superuser)
    var currentUser = CURRENT_USER || '';
    if(tpl.createdBy === currentUser || IS_SUPERUSER){
      var btnDel = document.createElement('button');
      btnDel.className='qtpl-btn del';btnDel.textContent='✕';
      btnDel.addEventListener('click',function(e){
        e.stopPropagation();
        if(confirm('Delete "'+tpl.name+'"?'))
          if(_bridge) _bridge.deleteQueryTemplate(String(tpl.id));
      });
      actions.appendChild(btnDel);
    }

    item.appendChild(badge);item.appendChild(info);item.appendChild(actions);
    item.addEventListener('click',function(){
      container.querySelectorAll('.qtpl-item').forEach(function(el){el.classList.remove('selected');});
      item.classList.add('selected');
      _selectedQTplId = tpl.id;
      document.getElementById('btn-qtpl-apply').disabled = false;
    });
    item.addEventListener('dblclick',function(){
      _applyQueryTemplate(tpl);
      document.getElementById('modal-query-templates').classList.remove('open');
    });
    container.appendChild(item);
  });
}

function _applyQueryTemplate(tpl){
  // GroupBy setzen
  var gb = document.getElementById('b-groupby');
  if(gb && tpl.groupBy) gb.value = tpl.groupBy;

  // Series setzen
  var ser = document.getElementById('b-series');
  if(ser && tpl.seriesPKs && tpl.seriesPKs.length){
    for(var i=0;i<ser.options.length;i++){
      ser.options[i].selected = tpl.seriesPKs.indexOf(parseInt(ser.options[i].value)) !== -1;
    }
  }

  // Filter-Rows neu aufbauen
  document.getElementById('filter-rows').innerHTML = '';
  _filterCount = 0;
  if(tpl.filters && tpl.filters.length){
    tpl.filters.forEach(function(f){
      addFilterRow(f);
    });
  } else {
    addFilterRow();
  }

  runQuery();
}

// Tab-Buttons
['all','1','2','3'].forEach(function(tab){
  var btn = document.getElementById('qtpl-tab-'+(tab==='all'?'all':tab));
  if(!btn) return;
  btn.addEventListener('click',function(){
    _qtplTabFilter = tab==='all' ? 0 : parseInt(tab);
    document.querySelectorAll('[id^="qtpl-tab-"]').forEach(function(b){
      b.style.borderColor=''; b.style.color='';
    });
    this.style.borderColor='#1D3557'; this.style.color='#1D3557';
    _renderQTplList();
  });
});

document.getElementById('btn-qtpl-apply').addEventListener('click',function(){
  var tpl = _allQueryTemplates.find(function(t){return t.id===_selectedQTplId;});
  if(tpl){ _applyQueryTemplate(tpl); document.getElementById('modal-query-templates').classList.remove('open'); }
});

document.getElementById('btn-qtpl-save').addEventListener('click',function(){
  var name = document.getElementById('qtpl-name').value.trim();
  if(!name){ document.getElementById('qtpl-name').style.borderColor='#e74c3c'; return; }
  document.getElementById('qtpl-name').style.borderColor='';
  var level = parseInt(document.getElementById('qtpl-level').value)||1;
  var payload = {
    name:        name,
    description: document.getElementById('qtpl-desc').value.trim(),
    visibilityLevel: level,
    groupBy:     document.getElementById('b-groupby').value,
    filters:     getFilters(),
    seriesPKs:   getSelectedSeries(),
    createdBy:   CURRENT_USER||'',
  };
  if(_bridge) _bridge.saveQueryTemplate(JSON.stringify(payload));
});

document.getElementById('qtpl-modal-cancel').addEventListener('click',function(){
  document.getElementById('modal-query-templates').classList.remove('open');
});
document.getElementById('modal-query-templates').addEventListener('click',function(e){
  if(e.target===this) this.classList.remove('open');
});

function receiveQueryTemplateSaved(success, message){
  if(success){
    document.getElementById('qtpl-name').value='';
    document.getElementById('qtpl-desc').value='';
    if(_bridge) _bridge.getQueryTemplates();
  } else { alert('Save failed: '+message); }
}
function receiveQueryTemplateDeleted(success){
  if(success && _bridge) _bridge.getQueryTemplates();
}
function receiveQueryTemplateCertified(success){
  if(success && _bridge) _bridge.getQueryTemplates();
}

// ── PDF Template (global, called by Bridge) ───────────────────────────────
var _pdfTemplates = [];
function receivePdfTemplates(templates){
  _pdfTemplates = templates;
  var sel = document.getElementById('pdf-template-select');
  if(!sel) return;
  sel.innerHTML = templates.map(function(t){
    return '<option value="'+(t.id||'')+'"'+(t.isDefault?' selected':'')+'>'+t.name+'</option>';
  }).join('');
  updatePdfTemplateDesc();
}
function updatePdfTemplateDesc(){
  var sel  = document.getElementById('pdf-template-select');
  var desc = document.getElementById('pdf-template-desc');
  if(!sel||!desc) return;
  var found = _pdfTemplates.find(function(t){ return String(t.id)===String(sel.value); });
  desc.textContent = found ? (found.description||'') : '';
}

// ── Grid ──────────────────────────────────────────────────────────────────────
function buildYOptions(currentKey){
  var opts=Y_AXES.map(function(y){var label=y.unit?y.title+' ('+y.unit+')':y.title;return'<option value="'+y.key+'"'+(y.key===currentKey?' selected':'')+'>'+label+'</option>';}).join('');
  if(currentKey&&currentKey.indexOf('free:')===0)opts+='<option value="'+currentKey+'" selected>⚙ '+getYTitle(currentKey)+'</option>';
  return opts;
}
// Jet Air Consumption (Kalibrier-Messung): X-Achse ist bei dieser Y-Achse
// IMMER Air Pressure (Jet Cal) - fest, keine Auswahl. Trial-basierte
// X-Achsen (Overfeed, Speed, Trial Number, ...) ergeben fuer diese Daten
// keinen Sinn, da es keinen Trial-Bezug gibt.
var JET_AIR_Y_KEY = 'jet_air_consumption';
var JET_AIR_X_KEY = 'jetcal_pressure';
function _xAxisChoicesFor(yKey){
  if(yKey===JET_AIR_Y_KEY) return X_AXES.filter(function(a){return a.key===JET_AIR_X_KEY;});
  return X_AXES;
}
function _xAxisOptionsHtmlFor(yKey, selectedKey){
  var choices=_xAxisChoicesFor(yKey);
  // Falls die aktuell gewaehlte X-Achse in der eingeschraenkten Liste nicht
  // vorkommt (z.B. beim Wechsel AUF Jet Air Consumption), erste (bzw. einzige) Option nehmen.
  var validKey=choices.some(function(a){return a.key===selectedKey;})?selectedKey:(choices[0]?choices[0].key:selectedKey);
  return {
    html: choices.map(function(a){var l=a.unit?a.title+' ('+a.unit+')':a.title;return'<option value="'+a.key+'"'+(a.key===validKey?' selected':'')+'>'+l+'</option>';}).join(''),
    key: validKey,
  };
}
function _renderYPills(idx, pillsDiv){
  if(!pillsDiv) return;
  var s=getState(idx);
  var yKeys=s.yKeys&&s.yKeys.length?s.yKeys:[s.yKey||Y_AXES[0].key];
  pillsDiv.innerHTML='';
  if(yKeys.length<=1){ pillsDiv.style.display='none'; return; }
  pillsDiv.style.display='flex';
  yKeys.forEach(function(yKey,ki){
    var pill=document.createElement('span');
    pill.className='series-pill';
    pill.style.cssText='background:#e8f5e9;border-color:#81c784;color:#1b5e20;font-size:11px;cursor:default;';
    pill.textContent=getYTitleShort(yKey);
    // ✕ Button — nicht beim letzten/ersten
    if(yKeys.length>1){
      var rm=document.createElement('span');
      rm.textContent=' ✕';
      rm.style.cssText='cursor:pointer;color:#888;font-size:10px;margin-left:2px;';
      rm.title='Remove this Y-series';
      (function(k){
        rm.addEventListener('click',function(e){
          e.stopPropagation();
          var st=getState(idx);
          st.yKeys=st.yKeys.filter(function(y){return y!==k;});
          if(!st.yKeys.length) st.yKeys=[st.yKey||Y_AXES[0].key];
          st.yKey=st.yKeys[0];
          chartStates[idx]=st;
          _renderYPills(idx,pillsDiv);
          updateChart(idx);
        });
      })(yKey);
      pill.appendChild(rm);
    }
    pillsDiv.appendChild(pill);
  });
}

function rebuildGrid(){
  var total=Math.max(1,parseInt(document.getElementById('inp-count').value)||1);
  // Scroll-Position und Fullscreen-Zustand merken — nach rebuild wiederherstellen
  var _wasExpanded = _expandedChartIdx;
  var _scrollContainer = document.getElementById('charts-wrapper');
  var _scrollY = _scrollContainer ? _scrollContainer.scrollTop : (window.scrollY || 0);
  // Block-Selector aktualisieren
  _syncFqbBlockSelector();
  var grid=document.getElementById('grid');
  // Ursprüngliche X-Felder für Drill-Down-Reset merken (nur wenn Stack leer)
  if(_drillStack.length === 0){
    for(var _ri=0;_ri<total;_ri++){
      var _rs=getState(_ri);
      if(_rs.blockType!=='image') _drillRootStates[_ri]=_rs.xField;
    }
  }
  grid.style.gridTemplateColumns='1fr 1fr';
  grid.innerHTML='<div class="chart-card" id="infobox-slot" style="padding:0;overflow:hidden;"></div>';
  buildInfobox();
  for(var i=0;i<total;i++){
    (function(idx){
      var state=getState(idx);
      // Image block
      if(state.blockType==='image'){
        var imgCard=buildImageCard(idx,state);
        grid.appendChild(imgCard);
        return;
      }
      var card=document.createElement('div');card.className='chart-card';
      var pillsDiv=null; // wird im else-Block (simple mode) gesetzt
      card.draggable=true;
      card.dataset.blockIdx=String(idx);
      var toolbar=document.createElement('div');toolbar.className='chart-toolbar';
      var curType=state.chartType||'bar';
      // Drag Handle
      var dragHandle=document.createElement('span');
      dragHandle.className='drag-handle';
      dragHandle.title='Drag to reorder';
      dragHandle.innerHTML='&#x2807;'; // ⠷ dots
      dragHandle.addEventListener('mousedown',function(){card.draggable=true;});

      // Chart-Typ-Dropdown
      var selCtype=document.createElement('select');
      selCtype.className='sel-ctype';
      CHART_TYPES.forEach(function(ct){
        var o=document.createElement('option');
        o.value=ct.key; o.textContent=ct.label+' '+ct.title;
        if(ct.key===curType) o.selected=true;
        selCtype.appendChild(o);
      });
      selCtype.addEventListener('change',function(){
        var s=getState(idx);s.chartType=this.value;
        s.mode=this.value==='3d'?'3d':'2d';
        chartStates[idx]=s;
        zControls.className='z-controls'+(this.value==='3d'?' visible':'');
        updateChart(idx);
      });

      var lblX=document.createElement('label');lblX.textContent='X:';
      var selX=document.createElement('select');
      var _xOptsInit=_xAxisOptionsHtmlFor(state.yKey, state.xField);
      selX.innerHTML=_xOptsInit.html;
      selX.disabled=(state.yKey===JET_AIR_Y_KEY);
      if(_xOptsInit.key!==state.xField){state.xField=_xOptsInit.key;chartStates[idx]=state;}
      var zControls=document.createElement('div');zControls.className='z-controls'+(curType==='3d'?' visible':'');
      var lblZ=document.createElement('label');lblZ.textContent='Z:';
      var selZ=document.createElement('select');selZ.innerHTML=X_AXES.map(function(a){var l=a.unit?a.title+' ('+a.unit+')':a.title;return'<option value="'+a.key+'"'+(a.key===state.zField?' selected':'')+'>'+l+'</option>';}).join('');
      zControls.appendChild(lblZ);zControls.appendChild(selZ);
      var lblY=document.createElement('label');lblY.textContent='Y:';
      var selY=document.createElement('select');selY.innerHTML=buildYOptions(state.yKey);
      var btnCustom=document.createElement('button');btnCustom.className='btn-custom';btnCustom.textContent='⚙ Custom';
      var btnCopy=document.createElement('button');btnCopy.className='btn-copy';btnCopy.textContent='⎘ Copy';
      btnCopy.addEventListener('click',function(){
        var chartEl=document.getElementById('chart_'+idx);if(!chartEl)return;btnCopy.textContent='...';
        Plotly.toImage(chartEl,{format:'png',width:1400,height:620,scale:2}).then(function(dataUrl){
          var b64=dataUrl.split(',')[1];if(_bridge){_bridge.copyImageToClipboard(b64);btnCopy.textContent='✓ Copied!';btnCopy.classList.add('copied');setTimeout(function(){btnCopy.textContent='⎘ Copy';btnCopy.classList.remove('copied');},2000);}
        });
      });
      // Note toggle button
      var btnNote=document.createElement('button');
      btnNote.className='btn-note';btnNote.textContent='📝';btnNote.title='Toggle note';
      // Manual gridlines toggle button — beschrifteter Text statt reines Icon
      // (ein 14px-Symbol ging in der ohnehin vollen Toolbar unter, siehe
      // Nutzer-Feedback "ich verstehe nicht wie ich eine Gitternetzlinie
      // einfuegen kann" trotz technisch korrekt sichtbarem Button). Gleiches
      // Muster wie der benachbarte "+ Y"-Button (btn-custom, kurzer Text).
      var btnGrid=document.createElement('button');
      btnGrid.className='btn-gridline';btnGrid.textContent='± Line';btnGrid.title='Click, then click on the chart to place a horizontal reference line (drag it afterwards to move it, Esc to cancel)';
      toolbar.appendChild(dragHandle);

      var _hasFqb = IS_VISUAL && _builderMode === 'free';
      if(_hasFqb){
        // ── Free Query Block: nur Focus-Button ──
        var btnFocus=document.createElement('button');
        btnFocus.className='btn-toolbar';
        btnFocus.style.cssText='font-weight:600;color:#1D3557;font-size:11px;';
        btnFocus.textContent='⚙ Chart '+(idx+1);
        btnFocus.title='Configure in SQL Builder (Free)';
        btnFocus.addEventListener('click',function(e){
          e.stopPropagation();
          var panel=document.getElementById('builder-panel');
          if(panel&&panel.classList.contains('hidden')){
            panel.classList.remove('hidden');
            var arrow=document.getElementById('builder-arrow');
            if(arrow) arrow.classList.add('open');
          }
          document.getElementById('tab-free').click();
          var bsel=document.getElementById('fqb-block-selector');
          if(bsel){
            _saveFqbStateForBlock(_activeFqbBlockIdx);
            bsel.value=idx;
            _activeFqbBlockIdx=idx;
            _loadFqbStateForBlock(idx);
          }
        });
        toolbar.appendChild(btnFocus);
      } else {
        // ── Simple/Advanced/Series-Mode: volle Toolbar ──
        toolbar.appendChild(selCtype);toolbar.appendChild(lblX);toolbar.appendChild(selX);
        var btnXAll=document.createElement('button');
        btnXAll.className='btn-toolbar';
        btnXAll.textContent='→ All';
        btnXAll.title='Diese X-Achse auf alle Charts anwenden';
        btnXAll.style.cssText='font-size:10px;padding:2px 6px;color:#1D6B32;';
        btnXAll.addEventListener('click',function(e){
          e.stopPropagation();
          var xVal=selX.value;
          var total=Math.max(1,parseInt(document.getElementById('inp-count').value)||1);
          syncNotesToState();
          for(var j=0;j<total;j++){
            if(j===idx) continue;
            var s=getState(j);
            if(s.blockType==='image') continue;
            s.xField=xVal;
            chartStates[j]=s;
          }
          rebuildGrid();
        });
        toolbar.appendChild(btnXAll);
        toolbar.appendChild(zControls);toolbar.appendChild(lblY);toolbar.appendChild(selY);
        toolbar.appendChild(btnCustom);
        // + Y Button für zusätzliche Y-Reihen
        var btnAddY=document.createElement('button');
        btnAddY.className='btn-custom';
        btnAddY.textContent='+ Y';
        btnAddY.title='Add another Y series';
        btnAddY.style.cssText='font-weight:600;color:#1D6B32;';
        toolbar.appendChild(btnAddY);
        // Pills-Zeile für aktive Y-Keys (unter Toolbar, bei >1 Y-Keys sichtbar)
        var pillsDiv=document.createElement('div');
        pillsDiv.className='y-pills-row';
        pillsDiv.style.cssText='display:none;flex-wrap:wrap;gap:4px;padding:3px 8px 2px 8px;min-height:0;';
        // pillsDiv wird nach toolbar in card eingefügt (siehe unten bei card.appendChild)
        _renderYPills(idx, pillsDiv);
        // Event-Handler (innerhalb else-Block, damit btnAddY/pillsDiv verfügbar)
        selX.addEventListener('change',function(){
          var s=getState(idx);
          var newKey=selX.value;
          var oldKey=s.xField;
          s.xField=newKey;
          chartStates[idx]=s;
          // If switching to/from a is_group_by axis, re-run the query
          // so Python fetches the correct group_label values
          var newDef=X_AXES.find(function(a){return a.key===newKey;})||{};
          var oldDef=X_AXES.find(function(a){return a.key===oldKey;})||{};
          if(newDef.is_group_by || oldDef.is_group_by){
            runQuery();
          } else {
            updateChart(idx);
          }
        });
        selZ.addEventListener('change',function(){var s=getState(idx);s.zField=selZ.value;chartStates[idx]=s;updateChart(idx);});
        selY.addEventListener('change',function(){
          var s=getState(idx);
          s.yKeys=[selY.value];s.yKey=selY.value;
          // Jet Air Consumption: X-Achse fix auf Air Pressure (Jet Cal)
          // setzen und sperren (bzw. beim Wechsel weg davon wieder freigeben).
          var _xOpts=_xAxisOptionsHtmlFor(s.yKey, s.xField);
          selX.innerHTML=_xOpts.html;
          selX.disabled=(s.yKey===JET_AIR_Y_KEY);
          s.xField=_xOpts.key;
          chartStates[idx]=s;
          _renderYPills(idx,pillsDiv);
          updateChart(idx);
        });
        btnCustom.addEventListener('click',function(){
          openModal(function(key,label){
            var ex=selY.querySelector('option[value^="free:"]');if(ex)selY.removeChild(ex);
            var opt=document.createElement('option');opt.value=key;opt.textContent='⚙ '+label;selY.appendChild(opt);selY.value=key;
            var s=getState(idx);s.yKeys=[key];s.yKey=key;chartStates[idx]=s;
            _renderYPills(idx,pillsDiv);
            var parts=key.split(':');if(_bridge)_bridge.loadFreeField(parts[1]||'',parts[2]||'',parts[3]||'',String(idx),key);else updateChart(idx);
          });
        });
        btnAddY.addEventListener('click',function(e){
          e.stopPropagation();
          // Bestehendes Popup entfernen
          var existing = document.getElementById('_ykey_popup');
          if(existing){ existing.remove(); return; }

          var popup = document.createElement('div');
          popup.id = '_ykey_popup';
          popup.style.cssText = 'position:absolute;z-index:9999;background:#fff;border:1px solid #c8c8c8;border-radius:6px;box-shadow:0 4px 16px rgba(0,0,0,0.15);min-width:220px;max-height:320px;overflow-y:auto;padding:4px 0;';

          // Position unter dem Button
          var rect = btnAddY.getBoundingClientRect();
          var wrapRect = (document.getElementById('charts-wrapper')||document.body).getBoundingClientRect();
          popup.style.top = (rect.bottom - wrapRect.top + 4) + 'px';
          popup.style.left = (rect.left - wrapRect.left) + 'px';

          // Aktuell gewählte yKeys
          var s = getState(idx);
          var currentKeys = s.yKeys || [s.yKey];

          // Vordefinierte Y-Achsen
          Y_AXES.forEach(function(axis){
            var item = document.createElement('div');
            var alreadyAdded = currentKeys.indexOf(axis.key) !== -1;
            item.style.cssText = 'padding:7px 14px;cursor:'+(alreadyAdded?'default':'pointer')+';font-size:12px;color:'+(alreadyAdded?'#aaa':'#222')+';white-space:nowrap;display:flex;align-items:center;gap:6px;';
            item.textContent = (alreadyAdded ? '✓ ' : '') + axis.title + (axis.unit ? ' ('+axis.unit+')' : '');
            if(!alreadyAdded){
              item.addEventListener('mouseenter', function(){ item.style.background='#f0faf0'; });
              item.addEventListener('mouseleave', function(){ item.style.background=''; });
              item.addEventListener('click', function(){
                popup.remove();
                var st = getState(idx);
                if(!st.yKeys||!st.yKeys.length) st.yKeys=[st.yKey||Y_AXES[0].key];
                if(st.yKeys.indexOf(axis.key)===-1){
                  st.yKeys = st.yKeys.concat([axis.key]);
                  st.yKey = st.yKeys[0];
                  chartStates[idx] = st;
                  _renderYPills(idx, pillsDiv);
                  updateChart(idx);
                }
              });
            }
            popup.appendChild(item);
          });

          // Separator + Custom
          var sep = document.createElement('div');
          sep.style.cssText = 'border-top:1px solid #eee;margin:4px 0;';
          popup.appendChild(sep);
          var customItem = document.createElement('div');
          customItem.style.cssText = 'padding:7px 14px;cursor:pointer;font-size:12px;color:#1D6B32;font-weight:600;white-space:nowrap;';
          customItem.textContent = '⚙ Custom Field...';
          customItem.addEventListener('mouseenter', function(){ customItem.style.background='#f0faf0'; });
          customItem.addEventListener('mouseleave', function(){ customItem.style.background=''; });
          customItem.addEventListener('click', function(){
            popup.remove();
            openModal(function(key,label){
              var st=getState(idx);
              if(!st.yKeys||!st.yKeys.length) st.yKeys=[st.yKey||Y_AXES[0].key];
              if(st.yKeys.indexOf(key)===-1){
                st.yKeys=st.yKeys.concat([key]);
                st.yKey=st.yKeys[0];
                chartStates[idx]=st;
                _renderYPills(idx,pillsDiv);
                var parts=key.split(':');
                if(_bridge) _bridge.loadFreeField(parts[1]||'',parts[2]||'',parts[3]||'',String(idx),key);
                else updateChart(idx);
              }
            });
          });
          popup.appendChild(customItem);

          // Popup in charts-wrapper einfügen
          var wrapper = document.getElementById('charts-wrapper') || document.body;
          wrapper.appendChild(popup);

          // Klick ausserhalb schliesst Popup
          function _closePopup(ev){
            if(!popup.contains(ev.target)){
              popup.remove();
              document.removeEventListener('click', _closePopup, true);
            }
          }
          setTimeout(function(){ document.addEventListener('click', _closePopup, true); }, 10);
        });
      } // end else (simple/advanced mode)

      var cBtnUp=document.createElement('button');
      cBtnUp.className='btn-toolbar';cBtnUp.style.cssText='font-size:11px;padding:2px 6px;';cBtnUp.textContent='↑';cBtnUp.title='Move up';
      cBtnUp.addEventListener('mousedown',function(e){e.preventDefault();e.stopPropagation();moveBlock(idx,-1);});
      cBtnUp.addEventListener('click',function(e){e.stopPropagation();});
      var cBtnDn=document.createElement('button');
      cBtnDn.className='btn-toolbar';cBtnDn.style.cssText='font-size:11px;padding:2px 6px;';cBtnDn.textContent='↓';cBtnDn.title='Move down';
      cBtnDn.addEventListener('mousedown',function(e){e.preventDefault();e.stopPropagation();moveBlock(idx,1);});
      cBtnDn.addEventListener('click',function(e){e.stopPropagation();});
      var btnExpand=document.createElement('button');
      btnExpand.className='btn-expand';
      btnExpand.textContent='⛶';
      btnExpand.title='Expand';
      (function(i,btn){
        btn.addEventListener('click',function(e){
          e.stopPropagation();
          if(_expandedChartIdx===i){ _collapseChart(); btn.textContent='⛶'; btn.title='Expand'; }
          else { _expandChart(i); btn.textContent='✕'; btn.title='Close'; }
        });
      })(idx,btnExpand);
      toolbar.appendChild(cBtnUp);toolbar.appendChild(cBtnDn);toolbar.appendChild(btnExpand);toolbar.appendChild(btnCopy);toolbar.appendChild(btnGrid);toolbar.appendChild(btnNote);

      var plotDiv=document.createElement('div');
      var hasSub = state.xField !== 'trial_nr';  // drillable wenn nicht bereits auf Trial-Ebene
      plotDiv.className='chart-plot'+(hasSub?' drillable':'');
      plotDiv.id='chart_'+idx;

      // Note bar
      var noteBar=document.createElement('div');noteBar.className='note-bar';noteBar.id='note_bar_'+idx;
      var noteTitleRow=document.createElement('div');noteTitleRow.className='note-bar-title';
      noteTitleRow.style.cssText='display:flex;align-items:center;gap:6px;';
      var noteTitleLbl=document.createElement('span');noteTitleLbl.style.cssText='font-size:10px;color:#888;white-space:nowrap;';noteTitleLbl.textContent='Note title:';
      var noteTitleInp=document.createElement('input');noteTitleInp.type='text';noteTitleInp.placeholder='e.g. Observation, Conclusion...';noteTitleInp.id='note_title_'+idx;
      noteTitleRow.appendChild(noteTitleLbl);noteTitleRow.appendChild(noteTitleInp);
      var noteTa=document.createElement('textarea');
      noteTa.placeholder='Add a note for this chart...';noteTa.id='note_text_'+idx;
      noteBar.appendChild(noteTitleRow);noteBar.appendChild(noteTa);
      // Restore note state from chartStates
      if(state.noteText)  { noteTa.value       = state.noteText; }
      if(state.noteTitle) { noteTitleInp.value  = state.noteTitle; }
      if(state.noteVisible){
        noteBar.classList.add('visible');
        btnNote.classList.add('active');
        card.classList.add('note-expanded');
      }

      btnNote.addEventListener('mousedown',function(e){
        e.preventDefault(); e.stopPropagation();
        var visible=noteBar.classList.toggle('visible');
        btnNote.classList.toggle('active',visible);
        card.classList.toggle('note-expanded',visible);
        var s=getState(idx);s.noteVisible=visible;chartStates[idx]=s;
        if(visible){
          setTimeout(function(){noteTa.focus();},50);
          var plt=document.getElementById('chart_'+idx);
          if(plt&&plt.layout) setTimeout(function(){Plotly.relayout(plt,{autosize:true});},100);
        } else {
          var plt2=document.getElementById('chart_'+idx);
          if(plt2&&plt2.layout) setTimeout(function(){Plotly.relayout(plt2,{autosize:true});},50);
        }
      });
      btnNote.addEventListener('click',function(e){e.stopPropagation();});

      // Gridline bar (manual reference lines on the y-axis)
      var gridlineBar=document.createElement('div');gridlineBar.className='gridline-bar';gridlineBar.id='gridline_bar_'+idx;
      var glLbl=document.createElement('label');glLbl.textContent='Gridlines (y):';
      var glInp=document.createElement('input');glInp.type='text';glInp.placeholder='e.g. 5, 10, 15';glInp.id='gridline_input_'+idx;
      gridlineBar.appendChild(glLbl);gridlineBar.appendChild(glInp);
      if(state.gridlinesY) glInp.value=state.gridlinesY;
      if(state.gridlinesVisible){
        gridlineBar.classList.add('visible');
        btnGrid.classList.add('active');
      }
      glInp.addEventListener('input',function(){
        var s=getState(idx);s.gridlinesY=glInp.value;chartStates[idx]=s;
        updateChart(idx);
      });
      btnGrid.addEventListener('mousedown',function(e){
        e.preventDefault(); e.stopPropagation();
        var chartEl=document.getElementById('chart_'+idx);
        // Klick auf den Button startet direkt den "auf die Grafik klicken"-Modus
        // (siehe _startGridlinePlacement) - ein zweiter Klick auf den Button
        // waehrend des Modus bricht ihn ab, statt eine neue Linie zu platzieren.
        if(chartEl && chartEl._gridlinePlacing){ _exitGridlinePlacement(chartEl); return; }
        if(chartEl) _startGridlinePlacement(chartEl, idx);
        gridlineBar.classList.add('visible');
        var s=getState(idx);s.gridlinesVisible=true;chartStates[idx]=s;
      });
      btnGrid.addEventListener('click',function(e){e.stopPropagation();});

      card.appendChild(toolbar);card.appendChild(pillsDiv||document.createElement('div'));card.appendChild(plotDiv);card.appendChild(noteBar);card.appendChild(gridlineBar);grid.appendChild(card);
      var _ct=state.chartType||'bar';
      var _yKeys=state.yKeys&&state.yKeys.length?state.yKeys:[state.yKey||Y_AXES[0].key];
      var _initTraces=buildTracesForKeys(_ct,state.xField,state.zField,_yKeys);
      var _initLayout=makeLayoutForKeys(_ct,state.xField,state.zField,_yKeys,_lastNJets);
      if(_ct!=='3d' && _ct!=='heat' && _initLayout.xaxis){
        var _initXVals=[];
        _initTraces.forEach(function(t){(t.x||[]).forEach(function(v){if(_initXVals.indexOf(String(v))===-1)_initXVals.push(String(v));});});
        var _allNumInit=_initXVals.length>0&&_initXVals.every(function(v){return !isNaN(parseFloat(v))&&isFinite(v);});
        _initXVals.sort(function(a,b){var na=parseFloat(a),nb=parseFloat(b);return(!isNaN(na)&&!isNaN(nb))?na-nb:String(a).localeCompare(String(b));});
        _initLayout.xaxis.type='category';
        _initLayout.xaxis.categoryarray=_initXVals;
        _initLayout.xaxis.categoryorder='array';
        if(_allNumInit){ _initLayout.xaxis.autorange=true; delete _initLayout.xaxis.range; }
        else { delete _initLayout.xaxis.autorange; delete _initLayout.xaxis.range; }
      }
      // Manuelle Gitternetzlinien (aus einem geladenen Report) müssen auch beim
      // allerersten Rendern hier greifen, nicht erst nach der ersten Interaktion
      // - sonst fehlen sie beim Öffnen eines gespeicherten Reports komplett bis
      // irgendein anderer Toolbar-Klick updateChart() ausloest.
      if(_ct!=='3d' && _ct!=='heat' && _initLayout.yaxis){
        var _initGlVals=_parseGridlineValues(state.gridlinesY);
        if(_initGlVals.length){
          var _initFixedRange=_computeDataYRange(_initTraces, _initLayout.yaxis.rangemode);
          if(_initFixedRange){ _initLayout.yaxis.range=_initFixedRange; _initLayout.yaxis.autorange=false; }
          _initLayout.shapes=(_initLayout.shapes||[]).concat(_buildGridlineShapes(_initGlVals));
          _initLayout.annotations=(_initLayout.annotations||[]).concat(_buildGridlineAnnotations(_initGlVals));
          _initLayout.margin=_initLayout.margin||{}; _initLayout.margin.l=Math.max(_initLayout.margin.l||60, 95);
        }
      }
      Plotly.newPlot('chart_'+idx,_initTraces,_initLayout,{responsive:true,displayModeBar:_ct==='3d',displaylogo:false});
      // Gridline-Klick/Drag-Bindung muss auch fuer den allerersten Chart-Render
      // erfolgen - updateChart() (das dies sonst am Ende macht) wird erst bei
      // der naechsten Interaktion aufgerufen, ohne diese Zeile bliebe der
      // "± Line"-Button beim frisch geoeffneten Report komplett wirkungslos
      // (Klick auf die Grafik loeste dann nur Plotlys normalen Zoom aus).
      if(_ct!=='3d' && _ct!=='heat') _bindGridlineDrag(document.getElementById('chart_'+idx), idx);
      document.getElementById('chart_'+idx).on('plotly_click',function(evtData){
        if(!evtData||!evtData.points||!evtData.points.length)return;
        var cj=evtData.points[0].data.name,jetKey=getAllJetNames().find(function(j){return getLegendLabel(j)===cj;})||cj;
        selectedJet=(selectedJet===jetKey)?null:jetKey;refreshAllCharts();
      });
      // Drill-Down: Doppelklick auf Balken
      document.getElementById('chart_'+idx).on('plotly_doubleclick',function(){
        // Plotly feuert plotly_doubleclick ohne Punktinfo — wir merken uns den letzten Klick
        return false; // Standard-Plotly-Zoom unterdrücken
      });
      document.getElementById('chart_'+idx).on('plotly_click',function(evtData2){
        if(!evtData2||!evtData2.points||!evtData2.points.length)return;
        var pt   = evtData2.points[0];
        var xVal = pt.x !== undefined ? pt.x : null;
        if(xVal === null) return;
        var s2   = getState(idx);
        // Kein weiterer Drill wenn bereits auf Trial-Ebene
        if(s2.xField === 'trial_nr') return;
        // JetKey aus Legend-Label zurückbauen
        var legendName = pt.data ? pt.data.name : null;
        var jetKey = legendName ? (getAllJetNames().find(function(j){ return getLegendLabel(j)===legendName; })||legendName) : null;
        // Doppelklick-Erkennung: zwei Klicks innerhalb 400ms auf denselben Wert + Jet
        var now = Date.now();
        var last = document.getElementById('chart_'+idx)._lastClick;
        if(last && now - last.time < 400 && String(last.x) === String(xVal) && String(last.jet) === String(jetKey)){
          document.getElementById('chart_'+idx)._lastClick = null;
          _drillDown(idx, xVal, jetKey);
        } else {
          document.getElementById('chart_'+idx)._lastClick = {time: now, x: xVal, jet: jetKey};
        }
      });
    })(i);
  }
  // Scroll-Position und Fullscreen-Zustand nach rebuild wiederherstellen.
  // Plotly rendert asynchron und verändert danach die DOM-Höhe — deshalb
  // mehrfach wiederherstellen: nach erstem rAF, nach zweitem rAF, und nach 120ms.
  function _restoreScroll(){
    if(_wasExpanded !== null) _expandChart(_wasExpanded);
    var sc = document.getElementById('charts-wrapper');
    if(sc) sc.scrollTop = _scrollY;
    else window.scrollTo(0, _scrollY);
  }
  requestAnimationFrame(function(){
    _restoreScroll();
    requestAnimationFrame(function(){
      _restoreScroll();
    });
  });
  setTimeout(_restoreScroll, 120);
}

// ── PDF Export ────────────────────────────────────────────────────────────────
function exportPdf(){
  var btn=document.getElementById('btn-export-pdf');
  btn.disabled=true; btn.textContent='Preparing...';
  var total=Math.max(1,parseInt(document.getElementById('inp-count').value)||1);
  for(var _i=0;_i<total;_i++){
    var _s=getState(_i);
    var _ta=document.getElementById('note_text_'+_i);
    var _ti=document.getElementById('note_title_'+_i);
    var _nb=document.getElementById('note_bar_'+_i);
    _s.noteText   =_ta  ?(_ta.value||'') :(_s.noteText||'');
    _s.noteTitle  =_ti  ?(_ti.value||'') :(_s.noteTitle||'');
    _s.noteVisible=_nb  ?_nb.classList.contains('visible'):(_s.noteVisible||false);
    chartStates[_i]=_s;
  }
  var chartImages=[];

  function captureNext(idx){
    if(idx>=total){ sendToPython(chartImages); return; }
    var s=getState(idx);
    // Image block — no Plotly rendering needed
    if(s.blockType==='image'){
      chartImages.push({
        blockType:  'image',
        index:      idx,
        b64:        s.imageData ? s.imageData.split(',')[1] : null,
        mimeType:   s.imageData ? (s.imageData.split(';')[0].split(':')[1]||'image/png') : 'image/png',
        imageTitle: s.imageTitle||'',
        imageWidth: s.imageWidth||'full',
        noteTitle:  s.noteTitle||'',
        noteText:   s.noteText||'',
        noteVisible:!!s.noteVisible,
      });
      captureNext(idx+1);
      return;
    }
    // Chart block
    var el=document.getElementById('chart_'+idx);
    if(!el||!el.layout){ chartImages.push(null); captureNext(idx+1); return; }
    Plotly.toImage(el,{format:'png',width:900,height:480,scale:2}).then(function(dataUrl){
      var xDef=X_AXES.find(function(a){return a.key===s.xField;})||{title:s.xField,unit:''};
      chartImages.push({
        blockType:  'chart',
        index:      idx,
        b64:        dataUrl.split(',')[1],
        title:      (s.yKeys&&s.yKeys.length>1)?s.yKeys.map(function(k){return getYTitleShort(k);}).join(' vs. '):getYTitleShort(s.yKey),
        yLabel:     (s.yKeys&&s.yKeys.length>1)?s.yKeys.map(function(k){return getYTitle(k);}).join(' / '):getYTitle(s.yKey),
        xLabel:     xDef.title+(xDef.unit?' ('+xDef.unit+')':''),
        noteTitle:  s.noteTitle||'',
        noteText:   s.noteText||'',
        noteVisible:!!s.noteVisible,
      });
      captureNext(idx+1);
    }).catch(function(){ chartImages.push(null); captureNext(idx+1); });
  }

  function sendToPython(images){
    var infoboxSetting = document.getElementById('save-infobox') ? document.getElementById('save-infobox').value : 'left';
    var payload = {
      reportTitle:     ((document.getElementById('pdf-export-title')&&document.getElementById('pdf-export-title').value.trim())||_currentReportTitle||document.getElementById('save-title').value||'SmartChart Report').trim(),
      author:          (document.getElementById('save-author').value||'').trim(),
      reportId:        _currentReportId,
      sourceType:      IS_VISUAL ? 'Visual SQL' : 'Trial Series',
      globalNote:      (document.getElementById('global-note-text').value||'').trim(),
      showInfobox:     infoboxSetting !== 'none',
      infoboxPosition: infoboxSetting,
      infobox: (function(){
        // Use first series in registry for infobox data (may have been updated by receiveSeriesData)
        var s0 = SERIES_REGISTRY[0] || {};
        // Merge: prefer INFOBOX fields if updated, fallback to registry
        var aps=[],ofs=[],sps=[],jets=[];
        SERIES_REGISTRY.forEach(function(s){
          (s.data||[]).forEach(function(d){
            if(!slicerMatch(d)) return;
            if(d.air_pressure!=null&&aps.indexOf(d.air_pressure)===-1)aps.push(d.air_pressure);
            if(d.overfeed!=null&&ofs.indexOf(d.overfeed)===-1)ofs.push(d.overfeed);
            if(d.speed!=null&&sps.indexOf(d.speed)===-1)sps.push(d.speed);
            if(d.jet_name&&jets.indexOf(d.jet_name)===-1)jets.push(d.jet_name);
          });
        });
        var totalTrials=SERIES_REGISTRY.reduce(function(s,r){return s+r.data.filter(slicerMatch).length;},0);
        return {seriesName:   INFOBOX.series_name || s0.name || '',
          machine:      INFOBOX.machine     || s0.machine   || '',
          material:     INFOBOX.material    || s0.material  || '',
          airPressures: aps.sort(function(a,b){return a-b;}),
          overfeeds:    ofs.sort(function(a,b){return a-b;}),
          speeds:       sps.sort(function(a,b){return a-b;}),
          jets:         jets.sort(),
          nTrials:      totalTrials,
        };
      })(),
      charts: images,
      pdfTemplateId: (function(){ var s=document.getElementById('pdf-template-select'); return s&&s.value?parseInt(s.value)||null:null; })(),
    };
    if(_bridge) _bridge.exportPdf(JSON.stringify(payload));
    btn.disabled=false; btn.textContent='PDF done!';
    setTimeout(function(){btn.textContent='📄 PDF';},3000);
  }

  captureNext(0);
}

function receivePdfResult(success, path){
  var btn=document.getElementById('btn-export-pdf');
  if(success){
    btn.textContent='\u2713 PDF saved!';
    setTimeout(function(){btn.textContent='📄 PDF';},3000);
  } else {
    alert('PDF export failed: '+path);
    btn.textContent='📄 PDF';
  }
}


// ── Image Block ───────────────────────────────────────────────────────────────
function receiveImage(insertAfterIdx, dataUrl, title, width){
  // Find highest sortOrder and insert after insertAfterIdx
  var total = Math.max(1,parseInt(document.getElementById('inp-count').value)||1);
  var newIdx = total; // append at end by default
  // Shift states above insertion point up by 1
  var newStates = {};
  for(var i=0;i<total;i++){
    if(i <= insertAfterIdx){
      newStates[i] = chartStates[i] || getState(i);
    } else {
      newStates[i+1] = chartStates[i] || getState(i);
    }
  }
  newIdx = insertAfterIdx + 1;
  newStates[newIdx] = {
    blockType:   'image',
    imageData:   dataUrl,
    imageTitle:  title || '',
    imageWidth:  width || 'full',
    noteTitle:   '',
    noteText:    '',
    noteVisible: false,
  };
  chartStates = newStates;
  document.getElementById('inp-count').value = total + 1;
  rebuildGrid();
}

function buildImageCard(idx, state){
  var card = document.createElement('div');
  card.className = 'image-card' + (state.imageWidth==='half' ? ' half-width' : '');
  card.id = 'image-card-'+idx;
  card.draggable=true;
  card.dataset.blockIdx=String(idx);

  // Toolbar
  var tb = document.createElement('div'); tb.className='img-toolbar';
  // Drag Handle
  var imgDragHandle=document.createElement('span');
  imgDragHandle.className='drag-handle';imgDragHandle.title='Drag to reorder';
  imgDragHandle.innerHTML='&#x2807;';
  tb.appendChild(imgDragHandle);
  var titleSpan = document.createElement('span'); titleSpan.className='img-title';
  titleSpan.textContent = state.imageTitle || ('Image '+(idx+1));

  var btnWidth = document.createElement('button');
  btnWidth.className='btn-toolbar'; btnWidth.style.fontSize='10px'; btnWidth.style.padding='2px 7px';
  btnWidth.textContent = state.imageWidth==='half' ? '½ → Full' : 'Full → ½';
  btnWidth.addEventListener('click', function(){
    var s=getState(idx);
    s.imageWidth = s.imageWidth==='half' ? 'full' : 'half';
    chartStates[idx]=s;
    rebuildGrid();
  });

  var btnNote = document.createElement('button');
  btnNote.className='btn-note'; btnNote.textContent='📝'; btnNote.title='Toggle note';

  var btnDel = document.createElement('button');
  btnDel.className='btn-toolbar'; btnDel.style.fontSize='10px'; btnDel.style.padding='2px 7px'; btnDel.style.color='#c0392b';
  btnDel.textContent='✕ Remove';
  btnDel.addEventListener('mousedown', function(e){
    e.preventDefault(); e.stopPropagation();
    var total=Math.max(1,parseInt(document.getElementById('inp-count').value)||1);
    var newStates={};
    var ni=0;
    for(var i=0;i<total;i++){
      if(i===idx) continue;
      newStates[ni++]=chartStates[i]||getState(i);
    }
    chartStates=newStates;
    document.getElementById('inp-count').value=total-1;
    rebuildGrid();
  });

  var btnUp=document.createElement('button');
  btnUp.className='btn-toolbar';btnUp.style.cssText='font-size:11px;padding:2px 6px;';btnUp.textContent='↑';btnUp.title='Move up';
  btnUp.addEventListener('mousedown',function(e){e.preventDefault();e.stopPropagation();moveBlock(idx,-1);});
  btnUp.addEventListener('click',function(e){e.stopPropagation();});
  var btnDn=document.createElement('button');
  btnDn.className='btn-toolbar';btnDn.style.cssText='font-size:11px;padding:2px 6px;';btnDn.textContent='↓';btnDn.title='Move down';
  btnDn.addEventListener('mousedown',function(e){e.preventDefault();e.stopPropagation();moveBlock(idx,1);});
  btnDn.addEventListener('click',function(e){e.stopPropagation();});
  tb.appendChild(titleSpan);tb.appendChild(btnUp);tb.appendChild(btnDn);tb.appendChild(btnWidth);tb.appendChild(btnNote);tb.appendChild(btnDel);
  card.appendChild(tb);

  // Image
  var body = document.createElement('div'); body.className='img-body';
  if(state.imageData){
    var img = document.createElement('img');
    img.src = state.imageData;
    body.appendChild(img);
  }
  card.appendChild(body);

  // Note bar (same pattern as chart)
  var noteBar = document.createElement('div'); noteBar.className='note-bar'; noteBar.id='note_bar_'+idx;
  var noteTitleRow=document.createElement('div'); noteTitleRow.style.cssText='display:flex;align-items:center;gap:6px;';
  var noteTitleLbl=document.createElement('span'); noteTitleLbl.style.cssText='font-size:10px;color:#888;white-space:nowrap;'; noteTitleLbl.textContent='Note title:';
  var noteTitleInp=document.createElement('input'); noteTitleInp.type='text'; noteTitleInp.placeholder='e.g. Observation...'; noteTitleInp.id='note_title_'+idx;
  noteTitleRow.appendChild(noteTitleLbl); noteTitleRow.appendChild(noteTitleInp);
  var noteTa=document.createElement('textarea'); noteTa.placeholder='Add a note for this image...'; noteTa.id='note_text_'+idx;
  noteBar.appendChild(noteTitleRow); noteBar.appendChild(noteTa);
  if(state.noteText)   noteTa.value=state.noteText;
  if(state.noteTitle)  noteTitleInp.value=state.noteTitle;
  if(state.noteVisible){ noteBar.classList.add('visible'); btnNote.classList.add('active'); }
  btnNote.addEventListener('mousedown',function(e){
    e.preventDefault(); e.stopPropagation();
    var visible=noteBar.classList.toggle('visible');
    btnNote.classList.toggle('active',visible);
    var s=getState(idx); s.noteVisible=visible; chartStates[idx]=s;
    if(visible) setTimeout(function(){noteTa.focus();},50);
  });
  btnNote.addEventListener('click',function(e){e.stopPropagation();});
  noteTa.addEventListener('input',function(){var s=getState(idx);s.noteText=noteTa.value;chartStates[idx]=s;});
  noteTitleInp.addEventListener('input',function(){var s=getState(idx);s.noteTitle=noteTitleInp.value;chartStates[idx]=s;});
  card.appendChild(noteBar);
  return card;
}


// ── Move block up/down ────────────────────────────────────────────────────────
function moveBlock(idx, direction){
  var total=Math.max(1,parseInt(document.getElementById('inp-count').value)||1);
  var swapIdx = idx + direction; // -1=up, +1=down
  if(swapIdx<0 || swapIdx>=total) return;
  syncNotesToState();
  var a = chartStates[idx]    || getState(idx);
  var b = chartStates[swapIdx]|| getState(swapIdx);
  chartStates[idx]     = b;
  chartStates[swapIdx] = a;
  rebuildGrid();
}

// ── Drag & Drop Logik ────────────────────────────────────────────────────────
var _dragSrcIdx = null;

function _initDragDrop(){
  var grid = document.getElementById('grid');
  if(!grid) return;

  grid.addEventListener('dragstart', function(e){
    var card = e.target.closest('[data-block-idx]');
    if(!card) return;
    _dragSrcIdx = parseInt(card.dataset.blockIdx);
    card.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(_dragSrcIdx));
  });

  grid.addEventListener('dragend', function(e){
    var card = e.target.closest('[data-block-idx]');
    if(card) card.classList.remove('dragging');
    // Alle drag-over entfernen
    grid.querySelectorAll('.drag-over').forEach(function(el){ el.classList.remove('drag-over'); });
    _dragSrcIdx = null;
  });

  grid.addEventListener('dragover', function(e){
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    var card = e.target.closest('[data-block-idx]');
    grid.querySelectorAll('.drag-over').forEach(function(el){ el.classList.remove('drag-over'); });
    if(card && parseInt(card.dataset.blockIdx) !== _dragSrcIdx) card.classList.add('drag-over');
  });

  grid.addEventListener('dragleave', function(e){
    var card = e.target.closest('[data-block-idx]');
    if(card) card.classList.remove('drag-over');
  });

  grid.addEventListener('drop', function(e){
    e.preventDefault();
    var card = e.target.closest('[data-block-idx]');
    if(!card || _dragSrcIdx === null) return;
    var dstIdx = parseInt(card.dataset.blockIdx);
    card.classList.remove('drag-over');
    if(dstIdx === _dragSrcIdx) return;

    syncNotesToState();
    var total = Math.max(1,parseInt(document.getElementById('inp-count').value)||1);

    // Reorder: Src aus Array rausnehmen, vor/nach Dst einfügen
    var order = [];
    for(var i=0;i<total;i++) order.push(i);
    order.splice(order.indexOf(_dragSrcIdx), 1);
    var dstPos = order.indexOf(dstIdx);
    // Einfügen nach Dst wenn Src von links kommt, davor wenn von rechts
    if(_dragSrcIdx < dstIdx) dstPos += 1;
    order.splice(dstPos, 0, _dragSrcIdx);

    var newStates = {};
    order.forEach(function(oldIdx, newIdx){
      newStates[newIdx] = chartStates[oldIdx] || getState(oldIdx);
    });
    chartStates = newStates;
    rebuildGrid();
  });
}

function init(){
  if(!IS_VISUAL&&(!DATA||DATA.length===0)){document.getElementById('grid').style.display='none';document.getElementById('no-data').style.display='block';return;}
  renderSeriesPills();
  var inp=document.getElementById('inp-count');
  inp.addEventListener('change',rebuildGrid);
  inp.addEventListener('keyup',function(e){if(e.key==='Enter')rebuildGrid();});
  document.getElementById('btn-sd').addEventListener('click',function(){
    showSD=!showSD;
    if(showSD) showMinMax=false;
    this.classList.toggle('active',showSD);
    var mm=document.getElementById('btn-minmax');if(mm)mm.classList.toggle('active',showMinMax);
    refreshAllCharts();
  });
  document.getElementById('btn-minmax').addEventListener('click',function(){
    showMinMax=!showMinMax;
    if(showMinMax) showSD=false;
    this.classList.toggle('active',showMinMax);
    var sd=document.getElementById('btn-sd');if(sd)sd.classList.toggle('active',showSD);
    refreshAllCharts();
  });
  // Legend order & colour modal
  document.getElementById('btn-legend-order').addEventListener('click', openLegendOrderModal);
  document.getElementById('legend-order-cancel').addEventListener('click', function(){
    document.getElementById('modal-legend-order').classList.remove('open');
  });
  document.getElementById('legend-order-reset').addEventListener('click', function(){
    _resetLegendOverrides();
    document.getElementById('modal-legend-order').classList.remove('open');
    refreshAllCharts();
  });
  document.getElementById('legend-order-apply').addEventListener('click', function(){
    // Read order + colours from modal rows
    var rows = document.querySelectorAll('#legend-order-list .leg-row');
    _jetOrderOverride = [];
    rows.forEach(function(row){
      var key = row.dataset.jetkey;
      var col = row.querySelector('.leg-color-btn').style.backgroundColor;
      _jetOrderOverride.push(key);
      if(col) _jetColorOverride[key] = rgbToHex(col);
    });
    document.getElementById('modal-legend-order').classList.remove('open');
    refreshAllCharts();
  });

  // Series Picker: immer sichtbar
  document.getElementById('btn-pick-series').addEventListener('click', openPickSeriesModal);
  // Add Series (Vergleich): nur in Series-Mode
  if(!IS_VISUAL){
    document.getElementById('btn-add-series').style.display=''; // explizit sichtbar
    document.getElementById('btn-add-series').addEventListener('click', openAddSeriesModal);
  } else {
    document.getElementById('btn-add-series').style.display='none';
  }
  document.getElementById('btn-save-report').addEventListener('click', openSaveModal);
  document.getElementById('btn-open-report').addEventListener('click', openOpenModal);
  document.getElementById('btn-export-pdf').addEventListener('click', openPdfExportModal);

  // ── PDF Export Modal ──────────────────────────────────────────────────────
  function openPdfExportModal(){
    document.getElementById('modal-pdf-export').classList.add('open');
    var titleInp = document.getElementById('pdf-export-title');
    if(titleInp){
      titleInp.value = _currentReportTitle || (document.getElementById('save-title')?document.getElementById('save-title').value.trim():'');
      setTimeout(function(){ titleInp.focus(); titleInp.select(); }, 80);
    }
    var sel = document.getElementById('pdf-template-select');
    sel.innerHTML = '<option value="">— Loading… —</option>';
    document.getElementById('pdf-template-desc').textContent = '';
    if(_bridge) _bridge.getPdfTemplates();
  }

  document.getElementById('pdf-template-select').addEventListener('change', updatePdfTemplateDesc);

  document.getElementById('pdf-export-cancel').addEventListener('click', function(){
    document.getElementById('modal-pdf-export').classList.remove('open');
  });

  document.getElementById('pdf-export-ok').addEventListener('click', function(){
    document.getElementById('modal-pdf-export').classList.remove('open');
    exportPdf();
  });

  document.getElementById('btn-add-image').addEventListener('click', function(){
    var total=Math.max(1,parseInt(document.getElementById('inp-count').value)||1);
    // Insert after last block by default
    if(_bridge) _bridge.addImage(String(total-1), 'full');
  });

  document.getElementById('btn-global-note').addEventListener('click',function(){
    var bar=document.getElementById('global-note-bar');
    var visible=bar.style.display==='flex';
    bar.style.display=visible?'none':'flex';
    this.classList.toggle('active',!visible);
  });
  document.getElementById('btn-hide-global-note').addEventListener('click',function(){
    document.getElementById('global-note-bar').style.display='none';
    document.getElementById('btn-global-note').classList.remove('active');
  });
  document.getElementById('global-note-text').addEventListener('input',function(){
    var sm=document.getElementById('save-global-note');
    if(sm) sm.value=this.value;
  });

  // Drag & Drop initialisieren
  _initDragDrop();
  // Default-Template anwenden falls bereits geladen, sonst macht receiveLayoutTemplates es
  if(_allTemplates.length > 0){
    applyDefaultTemplate(); // setzt chartStates, ruft rebuildGrid intern auf
  } else {
    rebuildGrid(); // Fallback: leeres Grid bis Templates ankommen
  }
}

// ── Report State ──────────────────────────────────────────────────────────────
var _currentReportId  = null;
var _currentReportTitle = '';

function getCurrentReportData() {
  syncNotesToState();
  var total = Math.max(1,parseInt(document.getElementById('inp-count').value)||1);
  var seriesState = SERIES_REGISTRY.map(function(s){return{pk:s.pk,name:s.name,color:s.color};});
  var infoboxEl = document.getElementById('save-infobox');
  var infoboxVal = infoboxEl ? infoboxEl.value : 'left';

  // Build blocks from chartStates
  var blocks = [];
  for(var i=0;i<total;i++){
    var s = getState(i);
    if(s.blockType === 'image'){
      blocks.push({
        blockType:  'image',
        sortOrder:  i,
        imageData:  s.imageData  || null,
        imageTitle: s.imageTitle || '',
        imageWidth: s.imageWidth || 'full',
        noteTitle:  s.noteTitle  || '',
        noteText:   s.noteText   || '',
        noteVisible:!!s.noteVisible,
      });
    } else {
      var _bfsCfg = (_blockFqbStates[i]&&_blockFqbStates[i].config) ? _blockFqbStates[i].config : null;
      blocks.push({
        blockType:   'chart',
        sortOrder:   i,
        chartIndex:  i,
        xField:      s.xField     || X_DEFAULT,
        yKey:        s.yKey       || (Y_AXES[0]?Y_AXES[0].key:'titer'),
        zField:      s.zField     || X_DEFAULT,
        chartMode:   s.mode       || '2d',
        chartType:   s.chartType  || 'bar',
        noteTitle:   s.noteTitle  || '',
        noteText:    s.noteText   || '',
        noteVisible: !!s.noteVisible,
        gridlinesY:      s.gridlinesY   || '',
        gridlinesVisible:!!s.gridlinesVisible,
        fqbConfig:   _bfsCfg,
      });
    }
  }

  var queryConfig = IS_VISUAL ? {
    groupBy:    document.getElementById('b-groupby')?document.getElementById('b-groupby').value:'jet',
    filters:    getFilters(),
    seriesPKs:  getSelectedSeries(),
    showSD:     showSD,
    showMinMax: showMinMax,
    series:     seriesState,
    chartCount: total,
  } : {
    seriesPK:   PRIMARY_PK,
    showSD:     showSD,
    showMinMax: showMinMax,
    series:     seriesState,
    chartCount: total,
  };

  return {id:              _currentReportId,
    title:           document.getElementById('save-title')?document.getElementById('save-title').value.trim():'',
    author:          document.getElementById('save-author')?document.getElementById('save-author').value.trim():'',
    sourceType:      IS_VISUAL ? 'visual' : 'series',
    seriesPK:        IS_VISUAL ? null : PRIMARY_PK,
    queryConfig:     queryConfig,
    globalNote:      (document.getElementById('global-note-text')?document.getElementById('global-note-text').value:'').trim(),
    showInfobox:     infoboxVal !== 'none',
    infoboxPosition: infoboxVal === 'none' ? 'left' : infoboxVal,
    blocks:          blocks,
    slicerState:     JSON.parse(JSON.stringify(slicerState)),
  };
}

// ── Save Modal ────────────────────────────────────────────────────────────────
function syncNotesToState(){
  // Sync all note DOM values into chartStates before save
  var total=Math.max(1,parseInt(document.getElementById('inp-count').value)||1);
  for(var _i=0;_i<total;_i++){
    var _s=getState(_i);
    var _ta=document.getElementById('note_text_'+_i);
    var _ti=document.getElementById('note_title_'+_i);
    var _nb=document.getElementById('note_bar_'+_i);
    if(_ta) _s.noteText   = _ta.value||'';
    if(_ti) _s.noteTitle  = _ti.value||'';
    if(_nb) _s.noteVisible= _nb.classList.contains('visible');
    chartStates[_i]=_s;
  }
  // Sync global note
  var gnEl=document.getElementById('global-note-text');
  var smEl=document.getElementById('save-global-note');
  if(gnEl && smEl) smEl.value=gnEl.value;
}

function openSaveModal(){
  syncNotesToState();
  if(!document.getElementById('save-author').value){
    document.getElementById('save-author').value = CURRENT_USER;
  }
  if(_currentReportTitle) document.getElementById('save-title').value = _currentReportTitle;
  // "Save as New" only makes sense when an existing report is loaded
  var newBtn = document.getElementById('save-report-new');
  if(newBtn) newBtn.style.display = _currentReportId ? 'inline-block' : 'none';
  var okBtn = document.getElementById('save-report-ok');
  if(okBtn) okBtn.textContent = _currentReportId ? 'Update Report' : 'Save Report';
  document.getElementById('modal-save-report').classList.add('open');
  document.getElementById('save-title').focus();
}

document.getElementById('save-report-cancel').addEventListener('click',function(){
  document.getElementById('modal-save-report').classList.remove('open');
});

document.getElementById('save-report-new').addEventListener('click',function(){
  var title = document.getElementById('save-title').value.trim();
  if(!title){ document.getElementById('save-title').style.borderColor='#e74c3c'; return; }
  document.getElementById('save-title').style.borderColor='';
  syncNotesToState();
  var data = getCurrentReportData();
  data.title = title;
  data.id = null;  // force INSERT — new report independent of current one
  if(_bridge) _bridge.saveReport(JSON.stringify(data));
  document.getElementById('modal-save-report').classList.remove('open');
});

document.getElementById('save-report-ok').addEventListener('click',function(){
  var title = document.getElementById('save-title').value.trim();
  if(!title){ document.getElementById('save-title').style.borderColor='#e74c3c'; return; }
  document.getElementById('save-title').style.borderColor='';
  syncNotesToState();
  var data = getCurrentReportData();
  data.title = title;
  if(_bridge) _bridge.saveReport(JSON.stringify(data));
  document.getElementById('modal-save-report').classList.remove('open');
});

document.getElementById('modal-save-report').addEventListener('click',function(e){
  if(e.target===this)this.classList.remove('open');
});

function receiveSaveResult(reportId, success, message, forked){
  if(success){
    _currentReportId    = reportId;
    _currentReportTitle = document.getElementById('save-title').value.trim();
    document.getElementById('report-title-display').textContent = _currentReportTitle;
    // Brief flash on save button
    var btn=document.getElementById('btn-save-report');
    btn.textContent='✓ Saved!';btn.classList.add('active');
    setTimeout(function(){btn.textContent='💾 Save';btn.classList.remove('active');},2000);
    if(forked){
      // Nicht der Autor des geladenen Reports - Backend hat automatisch eine
      // neue, unabhaengige Kopie angelegt (siehe screen_report.py::saveReport()).
      if(document.getElementById('save-author')) document.getElementById('save-author').value = CURRENT_USER;
      alert(message);
    }
  } else {
    alert('Save failed: ' + message);
  }
}

// ── Open Modal ────────────────────────────────────────────────────────────────
var _allReports = [], _selectedReportId = null;

function openOpenModal(){
  _selectedReportId = null;
  document.getElementById('open-report-ok').disabled = true;
  document.getElementById('report-search').value = '';
  document.getElementById('report-list-container').innerHTML =
    '<div style="padding:20px;text-align:center;color:#aaa;font-size:12px;">Loading...</div>';
  if(_bridge) _bridge.loadReportList();
  document.getElementById('modal-open-report').classList.add('open');
}

document.getElementById('report-search').addEventListener('input',function(){
  renderReportList(_allReports);
});

document.getElementById('open-report-cancel').addEventListener('click',function(){
  document.getElementById('modal-open-report').classList.remove('open');
});

document.getElementById('open-report-ok').addEventListener('click',function(){
  if(!_selectedReportId) return;
  document.getElementById('modal-open-report').classList.remove('open');
  if(_bridge) _bridge.loadReport(String(_selectedReportId));
});

document.getElementById('modal-open-report').addEventListener('click',function(e){
  if(e.target===this)this.classList.remove('open');
});

function receiveReportList(reports){
  _allReports = reports;
  renderReportList(reports);
}

function renderReportList(reports){
  var search = (document.getElementById('report-search').value||'').toLowerCase();
  var container = document.getElementById('report-list-container');
  var filtered = reports.filter(function(r){
    return !search || r.title.toLowerCase().indexOf(search)!==-1 || r.author.toLowerCase().indexOf(search)!==-1;
  });
  if(!filtered.length){
    container.innerHTML='<div style="padding:20px;text-align:center;color:#aaa;font-size:12px;">No reports found</div>';
    return;
  }
  container.innerHTML='';
  filtered.forEach(function(r){
    var item=document.createElement('div');item.className='report-list-item'+(r.id===_selectedReportId?' selected':'');
    var typeIcon = r.sourceType==='series' ? '📊' : '🔍';
    item.innerHTML=(
      '<span style="font-size:14px;">'+typeIcon+'</span>'
      +'<span class="rli-title">'+r.title+'</span>'
      +'<span class="rli-meta">'+r.author+' · '+r.updated+'</span>'
      +'<span class="rli-del" data-id="'+r.id+'" title="Delete">🗑</span>'
    );
    item.addEventListener('click',function(e){
      if(e.target.classList.contains('rli-del')){
        if(confirm('Delete report "'+r.title+'"?')){
          if(_bridge) _bridge.deleteReport(String(r.id));
        }
        return;
      }
      _selectedReportId=r.id;
      container.querySelectorAll('.report-list-item').forEach(function(el){el.classList.remove('selected');});
      item.classList.add('selected');
      document.getElementById('open-report-ok').disabled=false;
    });
    container.appendChild(item);
  });
}

function receiveDeleteResult(reportId){
  _allReports=_allReports.filter(function(r){return r.id!==reportId;});
  renderReportList(_allReports);
  if(_currentReportId===reportId){
    _currentReportId=null;_currentReportTitle='';
    document.getElementById('report-title-display').textContent='';
  }
}

function receiveReport(report){
  _currentReportId    = report.id;
  _currentReportTitle = report.title;
  document.getElementById('report-title-display').textContent = report.title;
  document.getElementById('save-title').value  = report.title;
  document.getElementById('save-author').value = report.author;
  var infoboxVal = report.showInfobox ? (report.infoboxPosition||'left') : 'none';
  var infoboxEl = document.getElementById('save-infobox');
  if(infoboxEl) infoboxEl.value = infoboxVal;

  // Restore global note
  if(report.globalNote){
    var smEl=document.getElementById('save-global-note');
    var gnEl=document.getElementById('global-note-text');
    var gnBar=document.getElementById('global-note-bar');
    var gnBtn=document.getElementById('btn-global-note');
    if(smEl) smEl.value=report.globalNote;
    if(gnEl) gnEl.value=report.globalNote;
    if(gnBar) gnBar.style.display='flex';
    if(gnBtn) gnBtn.classList.add('active');
  }

  // Restore from blocks
  var blocks = report.blocks || [];
  var qc = report.queryConfig || {};

  // Chart count = total blocks
  var total = blocks.length || (qc.chartCount || 9);
  document.getElementById('inp-count').value = total;

  // SD toggle
  if(qc.showSD !== undefined){
    showSD = qc.showSD;
    var sdBtn=document.getElementById('btn-sd');
    if(sdBtn) sdBtn.classList.toggle('active', showSD);
  }
  if(qc.showMinMax !== undefined){
    showMinMax = qc.showMinMax;
    var mmBtn=document.getElementById('btn-minmax');
    if(mmBtn) mmBtn.classList.toggle('active', showMinMax);
  }

  // Rebuild chartStates from blocks
  console.log('receiveReport blocks='+blocks.length+' first='+JSON.stringify(blocks[0]));
  chartStates = {};
  blocks.forEach(function(b, idx){
    var sortIdx = b.sortOrder != null ? b.sortOrder : idx;
    if(b.blockType === 'image'){
      chartStates[sortIdx] = {
        blockType:   'image',
        imageData:   b.imageData  || null,
        imageTitle:  b.imageTitle || '',
        imageWidth:  b.imageWidth || 'full',
        noteTitle:   b.noteTitle  || '',
        noteText:    b.noteText   || '',
        noteVisible: !!b.noteVisible,
      };
    } else {
      chartStates[sortIdx] = {
        blockType:   'chart',
        xField:      b.xField    || X_DEFAULT,
        yKey:        b.yKey      || (Y_AXES[0]?Y_AXES[0].key:'titer'),
        zField:      b.zField    || X_DEFAULT,
        mode:        b.chartMode || '2d',
        chartType:   b.chartType || (b.chartMode==='3d'?'3d':'bar'),
        noteTitle:   b.noteTitle || '',
        noteText:    b.noteText  || '',
        noteVisible: !!b.noteVisible,
        gridlinesY:      b.gridlinesY   || '',
        gridlinesVisible:!!b.gridlinesVisible,
      };
      // FQB Config wiederherstellen
      if(b.fqbConfig){
        if(!_blockFqbStates[sortIdx]) _blockFqbStates[sortIdx]={};
        _blockFqbStates[sortIdx].config = b.fqbConfig;
      }
    }
  });
  // FQB Queries für alle Blocks ausführen die eine Config haben
  if(IS_VISUAL){
    Object.keys(_blockFqbStates).forEach(function(idxStr){
      var idx = parseInt(idxStr);
      var bfs = _blockFqbStates[idx];
      if(bfs && bfs.config && bfs.config.baseTable && bfs.config.xField && bfs.config.yField){
        var cfg = bfs.config;
        cfg._blockIdx = idx;
        if(_bridge) _bridge.runFreeQuery(JSON.stringify(cfg));
      }
    });
  }

  // Restore slicer filter state
  if(report.slicerState){
    var ss=report.slicerState;
    Object.keys(slicerState).forEach(function(k){
      slicerState[k]=(ss[k]&&Array.isArray(ss[k]))?ss[k].map(String):[];
    });
  }

  // Restore series colors
  if(qc.series && qc.series.length){
    SERIES_REGISTRY.forEach(function(s){
      var saved=qc.series.find(function(x){return x.pk===s.pk;});
      if(saved) s.color=saved.color;
    });
  }

  // ── Series mode: reset registry + reload series data ──────────────────────
  if(report.sourceType==='series' && report.queryConfig && report.queryConfig.seriesPK){
    var spk    = parseInt(report.queryConfig.seriesPK);
    var scolor = (qc.series&&qc.series[0]) ? qc.series[0].color : '#39A650';
    var sname  = (qc.series&&qc.series[0]) ? qc.series[0].name  : ('Series '+spk);
    // Clear registry — replace with placeholder until data arrives
    SERIES_REGISTRY = [{pk:spk, name:sname, color:scolor, data:[], machine:'', material:''}];
    rebuildGrid();
    renderSeriesPills();
    if(_bridge) _bridge.loadSeriesData(String(spk), scolor);

  // ── Visual SQL mode: reset registry + re-run query ────────────────────────
  } else if(report.sourceType==='visual' && IS_VISUAL && report.queryConfig){
    var qc = report.queryConfig;
    SERIES_REGISTRY = [{pk:0, name:'Loading...', color:'#39A650', data:[], machine:'', material:''}];
    if(qc.groupBy && document.getElementById('b-groupby'))
      document.getElementById('b-groupby').value = qc.groupBy;
    if(document.getElementById('b-series')){
      var bsel=document.getElementById('b-series');
      for(var i=0;i<bsel.options.length;i++){
        bsel.options[i].selected=(qc.seriesPKs||[]).indexOf(parseInt(bsel.options[i].value))!==-1;
      }
    }
    rebuildGrid();
    renderSeriesPills();
    if(_bridge && qc.filters !== undefined){
      var btn=document.getElementById('btn-run-query');
      if(btn){btn.disabled=true;btn.textContent='⏳ Loading...';}
      _bridge.runVisualQuery(
        JSON.stringify(qc.seriesPKs||[]),
        qc.groupBy||'jet',
        JSON.stringify(qc.filters||[])
      );
    }
  } else {
    rebuildGrid();
  }
}

init();
</script>
</body>
</html>
"""
