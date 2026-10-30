# ui/smart_dashboard_html.py
"""Web page of the Smart Chart dashboard (ui/smart_dashboard.py): page
canvas with visuals, Visualizations pane (types + wells) and Fields pane
(all tables, collapsible, drag & drop) - modelled on Power BI.
The page owns the layout (spec); Python computes every visual
(ui/smart_dashboard_engine.py) and sends results back via renderResults().
Raw string on purpose: backslashes in the JS stay as they are."""

DASHBOARD_HTML = r"""<!doctype html><html><head><meta charset="utf-8">
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<style>
*{box-sizing:border-box}
html,body{margin:0;height:100%;font-family:'Segoe UI',Inter,sans-serif;color:#1C2321;background:#F4F6F3;font-size:13px}
#app{display:flex;height:100%}
#canvas{flex:1;min-width:0;overflow:auto;padding:12px 14px 0;display:flex;flex-direction:column}
#tabs{position:sticky;bottom:0;margin-top:auto;display:flex;align-items:flex-end;gap:2px;padding:8px 0 0;background:#F4F6F3;border-top:1px solid #DADFD8;z-index:15}
.tab{border:1px solid #DADFD8;border-bottom:none;background:#E9EDE8;border-radius:6px 6px 0 0;padding:6px 12px;cursor:pointer;font:inherit;display:flex;align-items:center;gap:6px;max-width:220px}
.tab span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tab.on{background:#fff;color:#165C2B;font-weight:600;border-color:#C9D1C8}
.tab b{font-weight:400;color:#5A6460;padding:0 2px;border-radius:3px}
.tab b:hover{background:#EEF1ED;color:#C62828}
.tab input{font:inherit;width:140px;border:1px solid #1F7A3A;border-radius:4px;padding:1px 4px}
#pfilters{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:-2px 0 10px;font-size:12px;color:#5A6460}
.fchip{border:1px solid #8C6BB1;background:#F3EFFA;color:#4B3A78;border-radius:12px;padding:2px 4px 2px 10px;cursor:pointer;display:inline-flex;align-items:center;gap:4px}
.fchip:hover{background:#E9E1F6}
.fchip b{font-weight:400;padding:0 5px;border-radius:8px}
.fchip b:hover{background:#D9CDEE;color:#C62828}
.fadd{border:1px dashed #B9A9DD;background:#fff;color:#5E35B1;border-radius:12px;padding:2px 10px;cursor:pointer;font:inherit;font-size:12px}
.fadd:hover{background:#F7F3FC}
#fpane{width:230px;flex:none;background:#fff;border-left:1px solid #DADFD8;overflow:auto;padding:12px;position:relative}
.fsec{margin-bottom:14px}
.fsec .lab{font-size:11px;font-weight:700;color:#5A6460;text-transform:uppercase;letter-spacing:.04em;margin-bottom:5px}
.fsec .chips{display:flex;flex-direction:column;gap:4px}
.fsec .fchip{border-radius:6px;justify-content:space-between}
.fsec .fchip span{white-space:normal}
.fsec .none{font-size:12px;color:#9AA59C}
.fsec select{margin-top:4px}
.xinfo{font-size:12px;border:1px solid #BFD3EE;background:#EAF1FA;color:#1F4E8C;border-radius:6px;padding:3px 4px 3px 8px;display:flex;justify-content:space-between;align-items:center;gap:4px}
.xinfo b{cursor:pointer;font-weight:400;padding:0 5px;border-radius:6px}
.xinfo b:hover{background:#D7E5F7;color:#C62828}
.ro #viz,.ro #fields,.ro #addv,.ro #alignbar,.ro .card .ib,.ro .card .rs,.ro .ix,.ro #addpage,.ro #duppage,
.ro .tab b[data-x],.ro .fadd,.ro .fchip b{display:none!important}
.ro .card .head{cursor:default}
.ro .card.target,.ro .card.msel{outline:none}
.ro .card.sel{border-color:#DADFD8;box-shadow:none}
.ro #pagetitle{pointer-events:none;border-color:transparent;background:transparent}
.ro .fchip{cursor:default}
.card.msel{outline:2px dashed #1F7A3A;outline-offset:2px}
#alignbar{display:none;align-items:center;gap:3px;background:#fff;border:1px solid #C9D1C8;border-radius:8px;padding:3px 6px}
#alignbar.on{display:flex}
#alignbar span{font-size:11px;color:#5A6460;margin-right:4px}
#alignbar button{border:1px solid transparent;background:transparent;border-radius:5px;height:26px;min-width:28px;cursor:pointer;padding:0 4px}
#alignbar button:hover{background:#EEF1ED;border-color:#C9D1C8}
#alignbar i{display:inline-block;width:1px;height:18px;background:#DADFD8;margin:0 3px}
.ix{font-size:10px;border-radius:9px;padding:1px 7px;cursor:pointer;white-space:nowrap;display:none;border:1px solid}
.ix.on{background:#EAF1FA;color:#1F4E8C;border-color:#2F6DB5}
.ix.off{background:#fff;color:#9AA59C;border-color:#C9D1C8;text-decoration:line-through}
.crumb{font-size:11px;color:#2F6DB5;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:45%}
.crumb b{cursor:pointer;font-weight:600;padding:0 4px;border-radius:4px}
.crumb b:hover{background:#EAF1FA}
.kpi .v.good{color:#1F7A3A}
.kpi .v.bad{color:#C62828}
.calcnew{margin:2px 0 6px 6px;border:1px dashed #B9A9DD;background:#fff;color:#5E35B1;border-radius:6px;padding:4px 10px;cursor:pointer;font:inherit;font-size:12px}
.calcnew:hover{background:#F7F3FC}
.fld .ed{margin-left:auto;color:#5E35B1;border-radius:4px;padding:0 4px;visibility:hidden}
.fld:hover .ed{visibility:visible}
.fld .ed:hover{background:#EDE6F7}
.tgt{display:flex;gap:4px}
.tgt input{width:50%;height:28px;border:1px solid #C9D1C8;border-radius:5px;padding:0 6px;font:inherit}
.card.target{outline:2px dashed #2F6DB5;outline-offset:2px}
.tg{display:flex;flex-direction:column;gap:3px;margin-top:5px;max-height:180px;overflow:auto}
.tg label{display:flex;gap:6px;align-items:center;font-size:12px;cursor:pointer}
#viz{width:236px;flex:none;background:#fff;border-left:1px solid #DADFD8;overflow:auto;padding:12px;position:relative}
#fields{width:260px;flex:none;background:#fff;border-left:1px solid #DADFD8;display:flex;flex-direction:column;position:relative}
.ph{display:flex;align-items:center;justify-content:space-between;gap:6px}
.ph h3{margin:0 0 8px}
.fold{border:none;background:transparent;cursor:pointer;color:#5A6460;font-size:15px;padding:0 4px;border-radius:4px;margin-bottom:8px}
.fold:hover{background:#EEF1ED;color:#1C2321}
#fpane.collapsed,#viz.collapsed,#fields.collapsed{width:30px;padding:8px 0;overflow:hidden;cursor:pointer}
.pane.collapsed > *:not(.strip){display:none}
.strip{display:none}
.pane.collapsed .strip{display:flex;flex-direction:column;align-items:center;gap:10px;height:100%}
.strip span{writing-mode:vertical-rl;font-weight:700;color:#1F7A3A;font-size:12px;letter-spacing:.05em;text-transform:uppercase}
.strip:hover span{color:#165C2B}
details details{margin-left:12px}
details details summary{font-weight:600;color:#3E5F46}
h3{font-size:13px;margin:0 0 8px;text-transform:uppercase;letter-spacing:.05em;color:#1F7A3A}
.bar{display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap}
.btn{height:30px;padding:0 12px;border:1px solid #C9D1C8;border-radius:6px;background:#fff;cursor:pointer;font:inherit}
.btn:hover{background:#F0F4EF}
.btn.add{border-style:dashed;color:#1F7A3A;font-weight:600;border-color:#9FB39F}
#pagetitle{font-size:16px;font-weight:700;border:1px solid transparent;border-radius:4px;padding:3px 6px;background:transparent;font-family:inherit;min-width:160px}
#pagetitle:hover,#pagetitle:focus{border-color:#C9D1C8;background:#fff;outline:none}
#cross{display:flex;gap:6px;flex-wrap:wrap}
.xchip{border:2px solid #2F6DB5;background:#EAF1FA;color:#1F4E8C;border-radius:14px;padding:2px 10px;cursor:pointer;font-weight:600}
.xchip:hover{background:#D7E5F7}
#grid{position:relative;min-height:200px;flex-shrink:0}
.card{background:#fff;border:1px solid #DADFD8;border-radius:10px;display:flex;flex-direction:column;min-width:0;position:absolute;box-sizing:border-box}
.card.drag{opacity:.85;box-shadow:0 8px 24px rgba(0,0,0,.18);z-index:10}
.rs{position:absolute;right:1px;bottom:1px;width:14px;height:14px;cursor:nwse-resize;background:linear-gradient(135deg,transparent 50%,#9AA59C 50%,#9AA59C 60%,transparent 60%,transparent 70%,#9AA59C 70%,#9AA59C 80%,transparent 80%);border-radius:0 0 9px 0;opacity:0}
.card:hover .rs,.card.sel .rs{opacity:1}
.card .head{cursor:move}
.fmark{font-size:10px;color:#5E35B1;background:#F3EFFA;border-radius:8px;padding:0 6px;white-space:nowrap}
.card.sel{border-color:#1F7A3A;box-shadow:0 0 0 2px #1F7A3A33}
.card .head{display:flex;align-items:center;gap:6px;padding:7px 8px 4px 12px;cursor:pointer}
.card .title{font-weight:600;flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dot{width:11px;height:11px;border-radius:6px;flex:none}
.ib{border:none;background:transparent;cursor:pointer;color:#5A6460;font:inherit;padding:2px 4px;border-radius:4px;display:none}
.card:hover .ib,.card.sel .ib{display:inline-block}
.ib:hover{background:#EEF1ED;color:#1C2321}
.body{padding:0 8px 8px;flex:1;min-height:0;display:flex;flex-direction:column}
.plot{flex:1;min-height:60px}
.kpi{padding:6px 6px 10px}
.kpi .v{font-size:30px;font-weight:700;color:#165C2B;line-height:1.1}
.kpi .u{font-size:13px;color:#5A6460;margin-left:4px;font-weight:500}
.kpi .s{font-size:12px;color:#5A6460;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.empty{flex:1;min-height:60px;display:flex;align-items:center;justify-content:center;color:#5A6460;border:1px dashed #C9D1C8;border-radius:8px;margin:4px;text-align:center;padding:10px}
.tbl{flex:1;min-height:0;overflow:auto;border:1px solid #EEF1ED;border-radius:6px}
.tbl table{border-collapse:collapse;width:100%;font-size:12px}
.tbl th{position:sticky;top:0;background:#F4F6F3;text-align:left;padding:4px 6px;font-weight:600}
.tbl td{padding:3px 6px;border-top:1px solid #EEF1ED;white-space:nowrap}
.tbl tr:hover td{background:#F0F7F2;cursor:pointer}
.note{font-size:11px;color:#5A6460;padding:0 4px}
.gallery{display:grid;grid-template-columns:repeat(4,1fr);gap:4px;margin-bottom:12px}
.vt{height:40px;border:1px solid #DADFD8;border-radius:6px;background:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0}
.vt:hover{border-color:#1F7A3A;background:#F0F7F2}
.vt.on{border:2px solid #1F7A3A;background:#E6F2E9}
.well{margin-bottom:10px}
.well .lab{font-size:11px;font-weight:600;color:#5A6460;margin-bottom:3px}
.drop{min-height:30px;border:1px dashed #B9C2B8;border-radius:6px;padding:3px;display:flex;flex-wrap:wrap;gap:3px;align-items:center;color:#9AA59C;font-size:12px}
.drop.over{border-color:#1F7A3A;background:#E6F2E9}
.drop.bad{border-color:#C62828;background:#FDECEA}
.chip{background:#E6F2E9;border:1px solid #1F7A3A;color:#165C2B;border-radius:5px;padding:2px 4px 2px 7px;display:flex;align-items:center;gap:3px;max-width:100%}
.chip span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chip b{cursor:pointer;padding:0 4px;font-weight:400}
select,input.t{width:100%;height:28px;border:1px solid #C9D1C8;border-radius:5px;font:inherit;padding:0 6px;background:#fff}
.hint{color:#5A6460;font-size:12px;line-height:1.45}
#fsearch{margin:10px 12px 6px;height:30px;border:1px solid #C9D1C8;border-radius:6px;padding:0 8px;font:inherit}
#flist{overflow:auto;flex:1;padding:0 6px 10px 10px}
details{margin:1px 0}
summary{cursor:pointer;font-weight:600;color:#165C2B;padding:4px 2px;list-style:none;display:flex;gap:6px;align-items:center}
summary::-webkit-details-marker{display:none}
summary .arr{width:10px;color:#5A6460;font-size:10px}
summary .cnt{color:#9AA59C;font-weight:400}
.fld{display:flex;gap:6px;align-items:center;padding:3px 6px 3px 18px;border-radius:5px;cursor:grab;user-select:none}
.fld:hover{background:#F0F7F2}
.fld .k{font-size:10px;color:#fff;background:#5A6460;border-radius:3px;padding:0 3px;min-width:18px;text-align:center}
.fld .k.num{background:#2F6DB5}
.fld .k.cat{background:#C98A00}
.fld span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sl{display:flex;flex-direction:column;gap:5px;padding:2px 2px 6px;flex:1;min-height:0}
.sl .q{height:26px;border:1px solid #C9D1C8;border-radius:5px;padding:0 7px;font:inherit}
.sl .acts{display:flex;gap:10px;font-size:11px}
.sl .acts a{color:#1F7A3A;cursor:pointer;text-decoration:underline}
.sl .opts{flex:1;min-height:0;max-height:260px;overflow:auto;display:flex;flex-direction:column}
.sl .ddp .opts{max-height:220px}
.sl .opt{display:flex;align-items:center;gap:7px;padding:3px 4px;border-radius:4px;cursor:pointer}
.sl .opt:hover{background:#F0F7F2}
.sl .box{width:14px;height:14px;border:1.5px solid #8A938C;border-radius:3px;flex:none;display:flex;align-items:center;justify-content:center;font-size:11px;color:#fff}
.sl .box.round{border-radius:7px}
.sl .opt.on .box{background:#1F7A3A;border-color:#1F7A3A}
.sl .opt .l{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sl .opt .n,.sl .tile .n{color:#9AA59C;font-size:11px}
.sl .tiles{display:flex;flex-wrap:wrap;gap:5px;overflow:auto;align-content:flex-start}
.sl .tile{border:1px solid #C9D1C8;border-radius:6px;padding:5px 10px;cursor:pointer;background:#fff;font:inherit}
.sl .tile:hover{border-color:#1F7A3A}
.sl .tile.on{background:#1F7A3A;border-color:#1F7A3A;color:#fff}
.sl .tile.on .n{color:#D7EBDC}
.sl .dd{position:relative}
.sl .ddb{width:100%;height:32px;border:1px solid #C9D1C8;border-radius:6px;background:#fff;text-align:left;padding:0 28px 0 10px;cursor:pointer;font:inherit;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sl .ddb:after{content:'▾';position:absolute;right:10px;top:7px;color:#5A6460}
.sl .ddp{position:absolute;left:0;right:0;top:36px;z-index:20;background:#fff;border:1px solid #C9D1C8;border-radius:6px;box-shadow:0 6px 18px rgba(0,0,0,.12);padding:6px}
.sl .rng{display:flex;gap:8px;align-items:center}
.sl .rng input[type=number]{width:46%;height:28px;border:1px solid #C9D1C8;border-radius:5px;padding:0 6px;font:inherit}
.sl .dual{position:relative;height:26px}
.sl .dual input[type=range]{position:absolute;left:0;right:0;width:100%;top:4px;pointer-events:none;-webkit-appearance:none;background:transparent}
.sl .dual input[type=range]::-webkit-slider-thumb{pointer-events:auto;-webkit-appearance:none;width:16px;height:16px;border-radius:8px;background:#1F7A3A;border:2px solid #fff;box-shadow:0 0 0 1px #1F7A3A;cursor:pointer}
.sl .track{position:absolute;left:0;right:0;top:11px;height:4px;background:#DADFD8;border-radius:2px}
.sl .fill{position:absolute;top:11px;height:4px;background:#1F7A3A;border-radius:2px}
.sl .info{font-size:11px;color:#5A6460}
#toast{position:fixed;bottom:14px;left:50%;transform:translateX(-50%);background:#1C2321;color:#fff;padding:6px 14px;border-radius:6px;opacity:0;transition:opacity .2s;pointer-events:none}
</style></head><body>
<div id="app">
  <div id="canvas">
    <div class="bar">
      <input id="pagetitle" value="Page 1" title="Name of this page">
      <button class="btn add" id="addv" title="Add an empty visual - then pick a type and drag fields into it">+ New visual</button>
      <div id="alignbar"></div>
      <div id="cross"></div>
    </div>
    <div id="grid"></div>
    <div id="tabs"></div>
  </div>
  <div id="fpane" class="pane"><div class="strip" title="Show Filters"><span>‹</span><span>Filters</span></div>
    <div class="ph"><h3>Filters</h3><button class="fold" data-p="fpane" title="Collapse to get more room for the page">›</button></div>
    <div id="fbody"></div></div>
  <div id="viz" class="pane"><div class="strip" title="Show Visualizations"><span>‹</span><span>Visualizations</span></div>
    <div class="ph"><h3>Visualizations</h3><button class="fold" data-p="viz" title="Collapse to get more room for the page">›</button></div>
    <div class="gallery" id="gallery"></div><div id="wells"></div></div>
  <div id="fields" class="pane"><div class="strip" title="Show Fields"><span>‹</span><span>Fields</span></div>
    <div class="ph" style="padding:12px 12px 0"><h3>Fields</h3><button class="fold" data-p="fields" title="Collapse to get more room for the page">›</button></div>
    <input id="fsearch" placeholder="Search a field…"><div id="flist"></div></div>
</div>
<div id="toast"></div>
<script>
var RO=false, STACKS={}, bridge=null, CATALOG=[], FIELDS={}, GROUPS=[], TREE=[], TYPES={}, WELLS={}, AGGS={}, SLSTYLES={}, DDOPEN={}, SLQ={};
var SPEC={pages:[{id:'p1',title:'Page 1',visuals:[],filters:[]}],active:'p1'}, SEL=null, RESULTS={}, PFILTERS=[];
var MSEL=[], GRID={cols:12,row:20}, GAP=10, FDATA={all:[],page:[],cross:[],slicers:[],ply:'any'};
function PG(){for(var i=0;i<SPEC.pages.length;i++)if(SPEC.pages[i].id===SPEC.active)return SPEC.pages[i];return SPEC.pages[0];}
var ICON={
 points:'<circle cx="8" cy="20" r="2.4"/><circle cx="13" cy="15" r="2.4"/><circle cx="18" cy="17" r="2.4"/><circle cx="23" cy="9" r="2.4"/>',
 trend:'<circle cx="8" cy="20" r="2.2"/><circle cx="14" cy="17" r="2.2"/><circle cx="20" cy="12" r="2.2"/><line x1="5" y1="22" x2="26" y2="7" stroke-dasharray="3 2"/>',
 line:'<polyline points="5,21 11,14 17,16 25,7" fill="none"/>',
 bar:'<rect x="5" y="13" width="5" height="11"/><rect x="12" y="7" width="5" height="17"/><rect x="19" y="10" width="5" height="14"/>',
 box:'<rect x="7" y="10" width="7" height="9" fill="none"/><line x1="10.5" y1="5" x2="10.5" y2="10"/><line x1="10.5" y1="19" x2="10.5" y2="24"/><rect x="17" y="8" width="7" height="8" fill="none"/><line x1="20.5" y1="4" x2="20.5" y2="8"/><line x1="20.5" y1="16" x2="20.5" y2="21"/>',
 violin:'<path d="M10 4 C15 10 13 16 10 24 C7 16 5 10 10 4Z"/><path d="M21 6 C26 12 24 17 21 23 C18 17 16 12 21 6Z"/>',
 hist:'<rect x="4" y="18" width="4" height="6"/><rect x="9" y="11" width="4" height="13"/><rect x="14" y="6" width="4" height="18"/><rect x="19" y="12" width="4" height="12"/><rect x="24" y="19" width="3" height="5"/>',
 density:'<ellipse cx="15" cy="14" rx="11" ry="8" fill-opacity=".25"/><ellipse cx="15" cy="14" rx="6" ry="4" fill-opacity=".6"/>',
 column:'<rect x="5" y="15" width="5" height="9"/><rect x="5" y="9" width="5" height="6" fill-opacity=".45"/><rect x="12" y="11" width="5" height="13"/><rect x="12" y="4" width="5" height="7" fill-opacity=".45"/><rect x="19" y="17" width="5" height="7"/><rect x="19" y="12" width="5" height="5" fill-opacity=".45"/>',
 matrix:'<rect x="4" y="5" width="7" height="6"/><rect x="12" y="5" width="7" height="6" fill-opacity=".4"/><rect x="20" y="5" width="7" height="6" fill-opacity=".7"/><rect x="4" y="12" width="7" height="6" fill-opacity=".5"/><rect x="12" y="12" width="7" height="6"/><rect x="20" y="12" width="7" height="6" fill-opacity=".3"/><rect x="4" y="19" width="7" height="6" fill-opacity=".8"/><rect x="12" y="19" width="7" height="6" fill-opacity=".2"/><rect x="20" y="19" width="7" height="6"/>',
 kpi:'<text x="15" y="20" font-size="13" font-weight="700" text-anchor="middle" stroke="none">123</text>',
 table:'<rect x="4" y="5" width="23" height="19" fill="none"/><line x1="4" y1="11" x2="27" y2="11"/><line x1="4" y1="17" x2="27" y2="17"/><line x1="12" y1="5" x2="12" y2="24"/>',
 slicer:'<rect x="4" y="5" width="5" height="5" rx="1"/><line x1="12" y1="7.5" x2="26" y2="7.5"/><rect x="4" y="12" width="5" height="5" rx="1" fill="none"/><line x1="12" y1="14.5" x2="24" y2="14.5"/><rect x="4" y="19" width="5" height="5" rx="1"/><line x1="12" y1="21.5" x2="22" y2="21.5"/>'
};
function icon(t){return '<svg width="30" height="28" viewBox="0 0 30 28" fill="#2F6DB5" stroke="#2F6DB5" stroke-width="1.6">'+(ICON[t]||'')+'</svg>';}
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function toast(t){var e=document.getElementById('toast');e.textContent=t;e.style.opacity=1;clearTimeout(e._t);e._t=setTimeout(function(){e.style.opacity=0;},Math.max(1800,String(t).length*45));}
function vis(id){return PG().visuals.filter(function(v){return v.id===id;})[0];}

new QWebChannel(qt.webChannelTransport,function(ch){bridge=ch.objects.bridge;bridge.ready();});

// ── collapsible panes (more room for the page) ────────────────
function resizePlots(){document.querySelectorAll('.plot').forEach(function(p){if(p.data&&typeof Plotly!=='undefined')Plotly.Plots.resize(p);});}
function setPane(id,collapsed,silent){
  var p=document.getElementById(id);p.classList.toggle('collapsed',collapsed);
  if(!silent&&!RO&&bridge)bridge.paneState(id==='fpane'?'filters':id,!!collapsed);      // remembered by TrippleT (QSettings)
  setTimeout(function(){if(typeof relayout==='function')relayout();else resizePlots();},60);
}
document.querySelectorAll('.fold').forEach(function(b){b.addEventListener('click',function(e){e.stopPropagation();setPane(b.dataset.p,true);});});
document.querySelectorAll('.strip').forEach(function(s){s.addEventListener('click',function(){setPane(s.parentNode.id,false);});});

window.addEventListener('resize',function(){clearTimeout(window._rz);window._rz=setTimeout(resizePlots,120);});

function init(data){
  CATALOG=data.catalog;GROUPS=data.groups;TREE=data.tree||GROUPS.map(function(g){return [g,[]];});TYPES=data.types;WELLS=data.wells;AGGS=data.aggs;SLSTYLES=data.slicer_styles||{};STACKS=data.stacks||{};
  FIELDS={};CATALOG.forEach(function(f){FIELDS[f.key]=f;});
  SPEC=data.spec;SEL=null;MSEL=[];GRID=data.grid||GRID;LAST=JSON.stringify(SPEC);HIST=[];FUT=[];
  RO=!!data.readonly;document.body.classList.toggle('ro',RO);
  if(RO)setPane('fpane',true,true);
  else Object.keys(data.panes||{}).forEach(function(id){setPane(id==='filters'?'fpane':id,!!data.panes[id],true);});
  renderGallery();renderFields();renderAll();
}
function setSpec(spec){var now=JSON.stringify(spec);if(LAST!==null&&now!==LAST){HIST.push(LAST);FUT=[];}LAST=now;
  SPEC=spec;if(SEL&&!vis(SEL))SEL=null;renderAll();}

// ── PDF: render each chart once more, off screen, at a fixed size ───
function exportImages(jobs){
  var out={}, i=0, host=document.createElement('div');
  host.style.cssText='position:fixed;left:-6000px;top:0;';document.body.appendChild(host);
  function next(){
    if(i>=jobs.length){document.body.removeChild(host);bridge.imagesReady(JSON.stringify(out));return;}
    var j=jobs[i++], d=document.createElement('div');d.style.width=j.w+'px';d.style.height=j.h+'px';host.appendChild(d);
    if(typeof Plotly==='undefined'){host.removeChild(d);next();return;}
    var lay=Object.assign({},j.figure.layout,{width:j.w,height:j.h,autosize:false,dragmode:false});
    Plotly.newPlot(d,j.figure.data,lay,{staticPlot:true})
      .then(function(){return Plotly.toImage(d,{format:'png',width:j.w,height:j.h,scale:2});})
      .then(function(u){out[j.key]=u.split(',')[1];Plotly.purge(d);host.removeChild(d);next();})
      .catch(function(){try{Plotly.purge(d);}catch(e){}host.removeChild(d);next();});
  }
  next();
}
function renderAll(){document.getElementById('pagetitle').value=PG().title||'Page 1';renderTabs();renderGrid();renderWells();}
var _pushT=null, HIST=[], FUT=[], LAST=null;
function push(){clearTimeout(_pushT);_pushT=setTimeout(function(){
  var now=JSON.stringify(SPEC);
  if(LAST!==null&&now!==LAST){HIST.push(LAST);if(HIST.length>60)HIST.shift();FUT=[];}
  LAST=now;if(bridge)bridge.updateSpec(now);},120);}
function restore(json){SPEC=JSON.parse(json);LAST=json;if(SEL&&!vis(SEL))SEL=null;RESULTS={};
  document.getElementById('grid').innerHTML='';renderAll();if(bridge)bridge.updateSpec(json);}
function undo(){if(!HIST.length){toast('Nothing to undo');return;}FUT.push(JSON.stringify(SPEC));restore(HIST.pop());toast('Undone');}
function redo(){if(!FUT.length){toast('Nothing to redo');return;}HIST.push(JSON.stringify(SPEC));restore(FUT.pop());toast('Redone');}
document.addEventListener('keydown',function(e){
  var tag=(e.target&&e.target.tagName)||'';if(tag==='INPUT'||tag==='TEXTAREA'||tag==='SELECT'||RO)return;
  if((e.ctrlKey||e.metaKey)&&!e.shiftKey&&e.key.toLowerCase()==='z'){e.preventDefault();undo();}
  else if((e.ctrlKey||e.metaKey)&&(e.key.toLowerCase()==='y'||(e.shiftKey&&e.key.toLowerCase()==='z'))){e.preventDefault();redo();}
  else if(e.key==='Delete'&&SEL){cardAction(SEL,'x');}
  else if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='a'){e.preventDefault();MSEL=PG().visuals.map(function(v){return v.id;});
    if(!SEL&&MSEL.length)SEL=MSEL[0];markSel();renderWells();}
  else if(e.key==='Escape'){MSEL=[];markSel();}
  else if(e.key.indexOf('Arrow')===0&&(SEL||MSEL.length)){
    e.preventDefault();var ids=MSEL.length>1?MSEL:[SEL], dx=e.key==='ArrowLeft'?-1:e.key==='ArrowRight'?1:0, dy=e.key==='ArrowUp'?-1:e.key==='ArrowDown'?1:0;
    ids.map(vis).filter(Boolean).forEach(function(v){v.x=Math.max(0,Math.min(GRID.cols-v.w,v.x+dx));v.y=Math.max(0,v.y+dy);});
    relayout();gridHeight();push();}
});

// ── fields pane ───────────────────────────────────────────────
var OPEN={};   // folders the user opened stay open while the list is redrawn
function fieldsOf(g,top,q){return CATALOG.filter(function(f){return f.group===g&&(!q||f.label.toLowerCase().indexOf(q)>=0||g.toLowerCase().indexOf(q)>=0||top.toLowerCase().indexOf(q)>=0);});}
function fieldHtml(fs){
  return fs.map(function(f){
    var calc=f.group==='Calculated';
    return '<div class="fld" draggable="true" data-key="'+esc(f.key)+'" title="'+esc(f.label)+' - drag into a well, or click to add to the selected visual">'
      +'<span class="k '+f.kind+'">'+(calc?'fx':(f.kind==='num'?'#':'Aa'))+'</span><span>'+esc(f.label)+'</span>'
      +(calc?'<span class="ed" data-calc="'+esc(f.key)+'" title="Change or delete">✎</span>':'')+'</div>';}).join('');
}
function folder(id,name,n,inner,q){
  return '<details data-f="'+esc(id)+'"'+((q||OPEN[id])?' open':'')+'><summary><span class="arr">▸</span>'+esc(name)
    +' <span class="cnt">('+n+')</span></summary>'+inner+'</details>';
}
function renderFields(){
  var q=document.getElementById('fsearch').value.trim().toLowerCase(), h='<button class="calcnew" id="calcnew" title="Your own number from a formula, e.g. FP/m per air consumption">+ New calculated field</button>';
  TREE.forEach(function(t){
    var top=t[0], subs=t[1], own=fieldsOf(top,top,q), inner=fieldHtml(own), n=own.length;
    subs.forEach(function(g){var fs=fieldsOf(g,top,q);if(fs.length){n+=fs.length;inner+=folder(top+'/'+g,g,fs.length,fieldHtml(fs),q);}});
    if(n)h+=folder(top,top,n,inner,q);
  });
  var el=document.getElementById('flist');el.innerHTML=h||'<div class="hint">No field found.</div>';
  el.querySelectorAll('details').forEach(function(d){
    var arr=d.querySelector(':scope > summary .arr');
    d.addEventListener('toggle',function(e){e.stopPropagation();arr.textContent=d.open?'▾':'▸';
      if(!document.getElementById('fsearch').value.trim())OPEN[d.dataset.f]=d.open;});
    if(d.open)arr.textContent='▾';});
  el.querySelectorAll('.fld').forEach(function(n){
    n.addEventListener('dragstart',function(e){e.dataTransfer.setData('text/plain',n.dataset.key);});
    n.addEventListener('click',function(e){if(e.target.dataset.calc){bridge.editCalc(e.target.dataset.calc);return;}addFieldToSelected(n.dataset.key);});
  });
  document.getElementById('calcnew').addEventListener('click',function(){bridge.editCalc('');});
}
document.getElementById('fsearch').addEventListener('input',renderFields);

function accepts(well,key,v){
  var f=FIELDS[key];if(!f)return false;
  var kind=WELLS[well][1];
  if(well==='value'&&v&&v.agg==='count')return true;
  return kind==='any'||kind===f.kind;
}
function setWell(v,well,key){
  if(!accepts(well,key,v)){toast(WELLS[well][0]+' needs a number field'+(well==='y'||well==='value'?' - to count experiments, series or trials use the visual Columns':''));return false;}
  v.wells=v.wells||{};
  if(well==='columns'||well==='drill'){v.wells[well]=(v.wells[well]||[]);if(v.wells[well].indexOf(key)<0)v.wells[well].push(key);}
  else v.wells[well]=key;
  if(well==='drill'||well==='x')v.drillpath=[];
  if(!v.title_set)v.title='';
  return true;
}
function addFieldToSelected(key){
  var v=SEL&&vis(SEL);
  if(!v){toast('Select a visual first (click it), or drag the field into a well');return;}
  var wells=TYPES[v.type].wells, w=v.wells||{};
  for(var i=0;i<wells.length;i++){
    var wl=wells[i];
    if(wl==='drill')continue;
    if(wl==='columns'||!w[wl]){if(accepts(wl,key,v)){setWell(v,wl,key);changed();return;}}
  }
  toast('No free well for this field - drag it onto a well to replace');
}

// ── visualizations pane ───────────────────────────────────────
function renderGallery(){
  var h='';Object.keys(TYPES).forEach(function(t){h+='<button class="vt" data-t="'+t+'" title="'+esc(TYPES[t].label+': '+TYPES[t].tip)+'">'+icon(t)+'</button>';});
  var g=document.getElementById('gallery');g.innerHTML=h;
  g.querySelectorAll('.vt').forEach(function(b){b.addEventListener('click',function(){
    var v=SEL&&vis(SEL);
    if(v){v.type=b.dataset.t;if(!v.title_set)v.title='';
      if(TYPES[v.type].defagg&&!(v.wells||{}).value&&(!v.agg||v.agg==='avg'))v.agg=TYPES[v.type].defagg;changed();}
    else addVisual(b.dataset.t);
  });});
}
function renderWells(){
  document.querySelectorAll('.vt').forEach(function(b){b.classList.toggle('on',!!SEL&&vis(SEL)&&vis(SEL).type===b.dataset.t);});
  var el=document.getElementById('wells'), v=SEL&&vis(SEL);
  if(!v){el.innerHTML='<div class="hint">Click a visual on the page to change it - or click a type above to add a new one.<br><br>Then drag fields from <b>Fields</b> into its wells.</div>';return;}
  var t=TYPES[v.type], h='<div class="hint" style="margin-bottom:8px"><b>'+esc(t.label)+'</b> - '+esc(t.tip)+'</div>';
  t.wells.forEach(function(wl){
    var multi=(wl==='columns'||wl==='drill');
    var keys=multi?((v.wells||{})[wl]||[]):((v.wells||{})[wl]?[(v.wells||{})[wl]]:[]);
    h+='<div class="well"><div class="lab">'+esc(WELLS[wl][0])+(WELLS[wl][1]==='num'?' · number':'')+'</div><div class="drop" data-w="'+wl+'">';
    if(!keys.length)h+='drop a field here';
    keys.forEach(function(k){if(FIELDS[k])h+='<div class="chip"><span title="'+esc(FIELDS[k].label)+'">'+esc(FIELDS[k].label)+'</span><b data-w="'+wl+'" data-k="'+esc(k)+'">×</b></div>';});
    h+='</div></div>';
  });
  if(t.agg){
    h+='<div class="well"><div class="lab">Aggregation</div><select id="agg">';
    Object.keys(AGGS).forEach(function(a){h+='<option value="'+a+'"'+((v.agg||t.defagg||'avg')===a?' selected':'')+'>'+esc(AGGS[a])+'</option>';});
    h+='</select></div>';
  }
  if(v.type==='column'){
    h+='<div class="well"><div class="lab">Bars</div><select id="vstack">';
    Object.keys(STACKS).forEach(function(k){h+='<option value="'+k+'"'+((v.stack||'stacked')===k?' selected':'')+'>'+esc(STACKS[k])+'</option>';});
    h+='</select></div>';
  }
  if(v.type==='points'||v.type==='trend'){
    h+='<div class="well"><label style="display:flex;gap:6px;align-items:center;cursor:pointer"><input type="checkbox" id="vnotes"'+(v.notes?' checked':'')+'> Show notes on values</label></div>';
  }
  if(t.target){
    var tg=v.target||{};
    h+='<div class="well"><div class="lab">Target</div><div class="tgt"><input type="number" step="any" id="tgval" placeholder="none" value="'+(tg.value!=null?esc(tg.value):'')+'">'
      +'<select id="tgbetter"><option value="higher"'+(tg.better!=='lower'?' selected':'')+'>higher is better</option><option value="lower"'+(tg.better==='lower'?' selected':'')+'>lower is better</option></select></div></div>';
  }
  if(v.type==='slicer'){
    var fk=(v.wells||{}).field, isNum=fk&&FIELDS[fk]&&FIELDS[fk].kind==='num', cur=v.style||(isNum?'between':'list');
    h+='<div class="well"><div class="lab">Style</div><select id="slstyle">';
    Object.keys(SLSTYLES).forEach(function(k){if(k==='between'&&!isNum)return;h+='<option value="'+k+'"'+(cur===k?' selected':'')+'>'+esc(SLSTYLES[k])+'</option>';});
    h+='</select></div><div class="well"><label style="display:flex;gap:6px;align-items:center;cursor:pointer"><input type="checkbox" id="slmulti"'+(v.multi===false?'':' checked')+'> Multi-select</label></div>'
      +'<div class="well"><button class="btn" id="slclear" style="width:100%">Clear selection</button></div>';
    var others=PG().visuals.filter(function(o){return o.id!==v.id;}), tg=v.targets;
    h+='<div class="well"><div class="lab">Applies to</div><select id="sltarget"><option value="all"'+(tg==null?' selected':'')+'>All visuals on this page</option>'
      +'<option value="some"'+(tg!=null?' selected':'')+'>Selected visuals</option></select>';
    if(tg!=null){h+='<div class="tg">'+others.map(function(o){var rr=RESULTS[o.id];
        return '<label><input type="checkbox" data-t="'+esc(o.id)+'"'+(tg.indexOf(o.id)>=0?' checked':'')+'> '
          +esc((o.title_set&&o.title)||(rr&&rr.title)||TYPES[o.type].label)+'</label>';}).join('')+'</div>';}
    h+='</div>';
  }
  h+='<div class="well"><div class="lab">Title</div><input class="t" id="vtitle" value="'+esc(v.title_set?v.title:'')+'" placeholder="'+esc((RESULTS[v.id]||{}).title||'automatic')+'"></div>';
  el.innerHTML=h;
  el.querySelectorAll('.drop').forEach(function(d){
    d.addEventListener('dragover',function(e){e.preventDefault();d.classList.add('over');});
    d.addEventListener('dragleave',function(){d.classList.remove('over');});
    d.addEventListener('drop',function(e){e.preventDefault();d.classList.remove('over');
      var k=e.dataTransfer.getData('text/plain');if(setWell(v,d.dataset.w,k))changed();});
  });
  el.querySelectorAll('.chip b').forEach(function(b){b.addEventListener('click',function(){
    if(b.dataset.w==='columns'||b.dataset.w==='drill')v.wells[b.dataset.w]=v.wells[b.dataset.w].filter(function(k){return k!==b.dataset.k;});
    else delete v.wells[b.dataset.w];
    if(b.dataset.w==='drill'||b.dataset.w==='x')v.drillpath=[];
    changed();});});
  var ag=document.getElementById('agg');if(ag)ag.addEventListener('change',function(){v.agg=ag.value;changed();});
  var vs=document.getElementById('vstack');if(vs)vs.addEventListener('change',function(){v.stack=vs.value;changed();});
  var vn=document.getElementById('vnotes');if(vn)vn.addEventListener('change',function(){v.notes=vn.checked;changed();});
  var tv=document.getElementById('tgval'), tb=document.getElementById('tgbetter');
  function setTarget(){var x=tv.value.trim();v.target=x===''?null:{value:parseFloat(x),better:tb.value};changed();}
  if(tv){tv.addEventListener('change',setTarget);tb.addEventListener('change',setTarget);}
  var ss=document.getElementById('slstyle');if(ss)ss.addEventListener('change',function(){v.style=ss.value;v.sel={};changed();});
  var sm=document.getElementById('slmulti');if(sm)sm.addEventListener('change',function(){v.multi=sm.checked;if(!sm.checked&&v.sel&&v.sel.values&&v.sel.values.length>1)v.sel={values:[v.sel.values[0]]};changed();});
  var sc=document.getElementById('slclear');if(sc)sc.addEventListener('click',function(){v.sel={};changed();});
  var stg=document.getElementById('sltarget');if(stg)stg.addEventListener('change',function(){
    v.targets=stg.value==='all'?null:PG().visuals.filter(function(o){return o.id!==v.id;}).map(function(o){return o.id;});changed();});
  el.querySelectorAll('.tg input').forEach(function(cb){cb.addEventListener('change',function(){
    v.targets=[].map.call(el.querySelectorAll('.tg input:checked'),function(x){return x.dataset.t;});markSel();push();});});
  var ti=document.getElementById('vtitle');ti.addEventListener('change',function(){v.title=ti.value.trim();v.title_set=!!v.title;changed();});
}

// ── canvas ────────────────────────────────────────────────────
function nextId(){var m=0;SPEC.pages.forEach(function(pg){pg.visuals.forEach(function(v){var n=parseInt(String(v.id).slice(1))||0;if(n>m)m=n;});});return 'v'+(m+1);}
function bottom(){var m=0;PG().visuals.forEach(function(v){m=Math.max(m,(v.y||0)+(v.h||0));});return m;}
function defaultH(t,st){return t==='kpi'?6:(t==='slicer'?(st==='between'?6:9):16);}
function addVisual(t){
  var w=(t==='kpi'||t==='slicer'?3:6);
  var v={id:nextId(),type:t||'points',x:0,y:bottom(),w:w,h:defaultH(t),title:'',agg:(TYPES[t]&&TYPES[t].defagg)||'avg',wells:{},filters:[]};
  PG().visuals.push(v);SEL=v.id;changed();
  setTimeout(function(){var c=document.querySelector('[data-id="'+v.id+'"]');if(c)c.scrollIntoView({behavior:'smooth',block:'nearest'});},50);
}
document.getElementById('addv').addEventListener('click',function(){addVisual('points');});
document.getElementById('pagetitle').addEventListener('change',function(){PG().title=this.value.trim()||'Page 1';renderTabs();push();});
function changed(){renderGrid();renderWells();push();}

function colW(){var g=document.getElementById('grid');return (g.clientWidth+GAP)/GRID.cols;}
function place(c,v){var cw=colW();c.style.left=(v.x*cw)+'px';c.style.top=(v.y*GRID.row)+'px';
  c.style.width=Math.max(40,v.w*cw-GAP)+'px';c.style.height=Math.max(40,v.h*GRID.row-GAP)+'px';}
function gridHeight(){document.getElementById('grid').style.height=(bottom()*GRID.row+40)+'px';}
function resizePlot(c){var p=c&&c.querySelector('.plot');if(p&&p.data&&typeof Plotly!=='undefined')Plotly.Plots.resize(p);}
function startMove(e,c,v,mode){
  if(e.button!==0||RO)return;
  var sx=e.clientX, sy=e.clientY, ox=v.x, oy=v.y, ow=v.w, oh=v.h, cw=colW(), moved=false;
  var group=(mode==='move'&&MSEL.length>1&&MSEL.indexOf(v.id)>=0)?MSEL.map(vis).filter(Boolean):[v];
  var start=group.map(function(g){return {g:g,x:g.x,y:g.y};});
  var minX=Math.min.apply(null,group.map(function(g){return g.x;})), maxR=Math.max.apply(null,group.map(function(g){return g.x+g.w;}));
  var minY=Math.min.apply(null,group.map(function(g){return g.y;}));
  function mm(ev){
    var dx=ev.clientX-sx, dy=ev.clientY-sy;
    if(!moved&&Math.abs(dx)+Math.abs(dy)<5)return;
    moved=true;c.classList.add('drag');
    if(mode==='move'){
      var gx=Math.max(-minX,Math.min(GRID.cols-maxR,Math.round(dx/cw))), gy=Math.max(-minY,Math.round(dy/GRID.row));
      start.forEach(function(s0){s0.g.x=s0.x+gx;s0.g.y=s0.y+gy;var cc=document.querySelector('[data-id="'+s0.g.id+'"]');if(cc)place(cc,s0.g);});
    }
    else{v.w=Math.max(2,Math.min(GRID.cols-v.x,ow+Math.round(dx/cw)));v.h=Math.max(3,oh+Math.round(dy/GRID.row));place(c,v);}
    gridHeight();
  }
  function mu(){document.removeEventListener('mousemove',mm);document.removeEventListener('mouseup',mu);
    c.classList.remove('drag');if(moved){if(mode==='size')resizePlot(c);push();}}
  document.addEventListener('mousemove',mm);document.addEventListener('mouseup',mu);
  e.preventDefault();
}
function renderGrid(){
  var g=document.getElementById('grid'), keep={};
  g.querySelectorAll('.card').forEach(function(c){keep[c.dataset.id]=c;});
  var emp=g.querySelector('.empty.page');if(emp)emp.remove();
  var order=PG().visuals.map(function(v){return v.id;});
  Object.keys(keep).forEach(function(id){if(order.indexOf(id)<0)g.removeChild(keep[id]);});
  PG().visuals.forEach(function(v){
    var c=keep[v.id];
    if(!c){c=document.createElement('div');c.className='card';c.dataset.id=v.id;
      c.innerHTML='<div class="head"><span class="dot"></span><span class="title"></span><span class="crumb"></span><span class="fmark"></span><span class="ix"></span>'
        +'<button class="ib" data-a="e" title="Export the data of this visual to Excel">⤓</button>'
        +'<button class="ib" data-a="d" title="Duplicate">⧉</button><button class="ib" data-a="x" title="Remove">✕</button></div>'
        +'<div class="body"></div><div class="rs" title="Drag to resize"></div>';
      c.addEventListener('mousedown',function(e){if(e.target.closest('.ib')||e.target.closest('.ix'))return;
        var id=c.dataset.id;
        if(e.ctrlKey||e.shiftKey||e.metaKey){
          if(!MSEL.length&&SEL&&SEL!==id)MSEL=[SEL];
          var i=MSEL.indexOf(id);if(i>=0&&MSEL.length>1&&!e.target.closest('.head'))MSEL.splice(i,1);else if(i<0)MSEL.push(id);
          SEL=id;markSel();renderWells();return;}
        if(MSEL.indexOf(id)<0)MSEL=[];
        if(SEL!==id){SEL=id;markSel();renderWells();}});
      c.querySelector('.head').addEventListener('mousedown',function(e){if(e.target.closest('.ib'))return;startMove(e,c,vis(c.dataset.id),'move');});
      c.querySelector('.rs').addEventListener('mousedown',function(e){e.stopPropagation();startMove(e,c,vis(c.dataset.id),'size');});
      c.querySelectorAll('.ib').forEach(function(b){b.addEventListener('click',function(e){e.stopPropagation();cardAction(c.dataset.id,b.dataset.a);});});
      c.querySelector('.ix').addEventListener('mousedown',function(e){e.stopPropagation();});
      c.querySelector('.ix').addEventListener('click',function(e){e.stopPropagation();toggleTarget(c.dataset.id);});
      c.addEventListener('dragover',function(e){e.preventDefault();});
      c.addEventListener('drop',function(e){e.preventDefault();if(RO)return;SEL=c.dataset.id;addFieldToSelected(e.dataTransfer.getData('text/plain'));});
      g.appendChild(c);
    }
    place(c,v);
    fillCard(c,v);
  });
  gridHeight();
  markSel();
  if(!PG().visuals.length){var d=document.createElement('div');d.className='empty page';d.style.height='200px';
    d.innerHTML='Empty page - click <b>&nbsp;+ New visual&nbsp;</b> or a type in Visualizations.';g.appendChild(d);}
}
function relayout(){document.querySelectorAll('.card').forEach(function(c){var v=vis(c.dataset.id);if(v){place(c,v);resizePlot(c);}});}
window.addEventListener('resize',function(){clearTimeout(window._rl);window._rl=setTimeout(relayout,100);});

// ── pages (tabs at the bottom, like Power BI) ─────────────────
function renderTabs(){
  var t=document.getElementById('tabs'), h='';
  SPEC.pages.forEach(function(pg){
    h+='<div class="tab'+(pg.id===SPEC.active?' on':'')+'" data-p="'+esc(pg.id)+'" title="Click: open · double-click: rename">'
      +'<span>'+esc(pg.title)+'</span>'+(SPEC.pages.length>1&&pg.id===SPEC.active?'<b data-x="1" title="Delete this page">✕</b>':'')+'</div>';
  });
  h+='<button class="tab" id="addpage" title="Add a page">+</button><button class="tab" id="duppage" title="Duplicate this page">⧉</button>';
  t.innerHTML=h;
  t.querySelectorAll('.tab[data-p]').forEach(function(el){
    el.addEventListener('click',function(e){
      if(e.target.dataset.x){var pg=PG();if(confirm('Delete the page “'+pg.title+'” with its '+pg.visuals.length+' visuals?')){
        SPEC.pages=SPEC.pages.filter(function(x){return x.id!==pg.id;});SPEC.active=SPEC.pages[0].id;SEL=null;renderAll();push();}return;}
      if(SPEC.active!==el.dataset.p){SPEC.active=el.dataset.p;SEL=null;RESULTS={};
        document.getElementById('grid').innerHTML='';renderAll();push();}
    });
    el.addEventListener('dblclick',function(){
      if(RO)return;
      var pg=SPEC.pages.filter(function(x){return x.id===el.dataset.p;})[0];
      el.innerHTML='<input value="'+esc(pg.title)+'">';var i=el.querySelector('input');i.focus();i.select();
      function done(){pg.title=i.value.trim()||pg.title;renderTabs();document.getElementById('pagetitle').value=PG().title;push();}
      i.addEventListener('keydown',function(e){if(e.key==='Enter')done();if(e.key==='Escape')renderTabs();});
      i.addEventListener('blur',done);
    });
  });
  document.getElementById('addpage').addEventListener('click',function(){
    var m=0;SPEC.pages.forEach(function(p){var n=parseInt(String(p.id).slice(1))||0;if(n>m)m=n;});
    var pg={id:'p'+(m+1),title:'Page '+(SPEC.pages.length+1),visuals:[],filters:[]};
    SPEC.pages.push(pg);SPEC.active=pg.id;SEL=null;RESULTS={};document.getElementById('grid').innerHTML='';renderAll();push();
  });
  document.getElementById('duppage').addEventListener('click',function(){
    var src=PG(), m=0;SPEC.pages.forEach(function(p){var n=parseInt(String(p.id).slice(1))||0;if(n>m)m=n;});
    var pg=JSON.parse(JSON.stringify(src));pg.id='p'+(m+1);pg.title=src.title+' (copy)';
    var used={};SPEC.pages.forEach(function(p){p.visuals.forEach(function(v){used[v.id]=1;});});
    var k=0;pg.visuals.forEach(function(v){do{k++;}while(used['v'+k]);used['v'+k]=1;v.id='v'+k;});
    SPEC.pages.push(pg);SPEC.active=pg.id;SEL=null;RESULTS={};document.getElementById('grid').innerHTML='';renderAll();push();
  });
}

// ── Filters pane: all pages / this page / this visual / clicks & slicers ──
function chipList(scope,vid,texts){
  if(!texts.length)return '<div class="none">none</div>';
  return texts.map(function(t,i){return '<span class="fchip" data-s="'+scope+'" data-v="'+esc(vid)+'" data-i="'+i+'" title="Click to change">'
    +'<span>'+esc(t)+'</span><b title="Remove">×</b></span>';}).join('');
}
function renderFilterPane(){
  var v=SEL&&vis(SEL), r=v&&RESULTS[v.id], h='';
  h+='<div class="fsec"><div class="lab">On all pages</div><div class="chips">'+chipList('all','',FDATA.all)+'</div>'
    +'<button class="fadd" data-s="all" style="margin-top:5px">+ Add filter</button>'
    +'<div class="hint" style="margin-top:6px">Yarn filters apply to</div><select id="plyscope">'
    +[['any','Any ply'],['core','Core only'],['effect','Effect only']].map(function(o){return '<option value="'+o[0]+'"'+(FDATA.ply===o[0]?' selected':'')+'>'+o[1]+'</option>';}).join('')
    +'</select></div>';
  h+='<div class="fsec"><div class="lab">On this page</div><div class="chips">'+chipList('page','',FDATA.page)+'</div>'
    +'<button class="fadd" data-s="page" style="margin-top:5px">+ Add filter</button></div>';
  h+='<div class="fsec"><div class="lab">On this visual</div>';
  if(v){h+='<div class="hint" style="margin-bottom:4px">'+esc((v.title_set&&v.title)||(r&&r.title)||TYPES[v.type].label)+'</div>'
      +'<div class="chips">'+chipList('visual',v.id,(r&&r.vfilters)||[])+'</div><button class="fadd" data-s="visual" data-v="'+esc(v.id)+'" style="margin-top:5px">+ Add filter</button>';}
  else h+='<div class="none">Select a visual on the page.</div>';
  h+='</div>';
  if(FDATA.cross.length||FDATA.slicers.length){
    h+='<div class="fsec"><div class="lab">Clicks and slicers</div><div class="chips">';
    FDATA.cross.forEach(function(c){h+='<span class="xinfo" title="Clicked in '+esc(c.from)+'"><span>'+esc(c.text)+'</span><b data-x="'+esc(c.source)+'">×</b></span>';});
    FDATA.slicers.forEach(function(c){h+='<span class="xinfo" title="Slicer - applies to '+esc(c.to)+'"><span>'+esc(c.text)+' <i style="opacity:.7">('+esc(c.to)+')</i></span><b data-sl="'+esc(c.source)+'">×</b></span>';});
    h+='</div></div>';
  }
  var el=document.getElementById('fbody');el.innerHTML=h;
  el.querySelectorAll('.fchip').forEach(function(c){c.addEventListener('click',function(e){
    if(RO)return;
    var i=parseInt(c.dataset.i);
    if(e.target.tagName==='B')bridge.removeFilter(c.dataset.s,c.dataset.v,i);else bridge.editFilter(c.dataset.s,c.dataset.v,i);});});
  el.querySelectorAll('.fadd').forEach(function(b){b.addEventListener('click',function(){bridge.editFilter(b.dataset.s,b.dataset.v||'',-1);});});
  el.querySelectorAll('.xinfo b').forEach(function(b){b.addEventListener('click',function(){
    if(b.dataset.x)bridge.clearCross(b.dataset.x);
    else{var sv=vis(b.dataset.sl);if(sv){sv.sel={};changed();}}});});
  var ps=document.getElementById('plyscope');ps.disabled=RO;ps.addEventListener('change',function(){bridge.setPlyScope(ps.value);});
}
function toggleTarget(id){
  if(RO)return;
  var sv=SEL&&vis(SEL);if(!sv||sv.type!=='slicer')return;
  var all=PG().visuals.filter(function(o){return o.id!==sv.id;}).map(function(o){return o.id;});
  var tg=sv.targets==null?all.slice():sv.targets.slice(), i=tg.indexOf(id);
  if(i>=0)tg.splice(i,1);else tg.push(id);
  sv.targets=(tg.length===all.length&&all.every(function(x){return tg.indexOf(x)>=0;}))?null:tg;
  markSel();renderWells();push();
}
function renderAlignBar(){
  var b=document.getElementById('alignbar');
  MSEL=MSEL.filter(function(id){return !!vis(id);});
  if(MSEL.length<2){b.className='';b.innerHTML='';return;}
  var B=function(a,t,svg){return '<button data-al="'+a+'" title="'+t+'"><svg width="18" height="16" viewBox="0 0 18 16" fill="none" stroke="#2F4A37" stroke-width="1.5">'+svg+'</svg></button>';};
  b.innerHTML='<span>'+MSEL.length+' selected</span>'
    +B('left','Align left','<line x1="2" y1="1" x2="2" y2="15"/><rect x="4" y="3" width="10" height="3"/><rect x="4" y="9" width="6" height="3"/>')
    +B('center','Align centre','<line x1="9" y1="1" x2="9" y2="15"/><rect x="3" y="3" width="12" height="3"/><rect x="5" y="9" width="8" height="3"/>')
    +B('right','Align right','<line x1="16" y1="1" x2="16" y2="15"/><rect x="4" y="3" width="10" height="3"/><rect x="8" y="9" width="6" height="3"/>')
    +'<i></i>'
    +B('top','Align top','<line x1="1" y1="2" x2="17" y2="2"/><rect x="3" y="4" width="4" height="10"/><rect x="10" y="4" width="4" height="6"/>')
    +B('middle','Align middle','<line x1="1" y1="8" x2="17" y2="8"/><rect x="3" y="2" width="4" height="12"/><rect x="10" y="4" width="4" height="8"/>')
    +B('bottom','Align bottom','<line x1="1" y1="14" x2="17" y2="14"/><rect x="3" y="2" width="4" height="10"/><rect x="10" y="6" width="4" height="6"/>')
    +'<i></i>'
    +B('w','Same width as the last clicked','<rect x="2" y="2" width="14" height="4"/><rect x="2" y="10" width="14" height="4"/>')
    +B('h','Same height as the last clicked','<rect x="2" y="2" width="5" height="12"/><rect x="11" y="2" width="5" height="12"/>')
    +B('size','Same size as the last clicked','<rect x="2" y="2" width="6" height="6"/><rect x="10" y="8" width="6" height="6"/>')
    +'<i></i>'
    +B('dh','Distribute horizontally (equal gaps)','<rect x="1" y="4" width="3" height="8"/><rect x="7.5" y="4" width="3" height="8"/><rect x="14" y="4" width="3" height="8"/>')
    +B('dv','Distribute vertically (equal gaps)','<rect x="4" y="1" width="10" height="3"/><rect x="4" y="6.5" width="10" height="3"/><rect x="4" y="12" width="10" height="3"/>');
  b.className='on';
  b.querySelectorAll('button').forEach(function(x){x.addEventListener('click',function(){alignSel(x.dataset.al);});});
}
function alignSel(a){
  var g=MSEL.map(vis).filter(Boolean);if(g.length<2)return;
  var ref=vis(SEL)&&MSEL.indexOf(SEL)>=0?vis(SEL):g[0];
  var minX=Math.min.apply(null,g.map(function(v){return v.x;})), maxR=Math.max.apply(null,g.map(function(v){return v.x+v.w;}));
  var minY=Math.min.apply(null,g.map(function(v){return v.y;})), maxB=Math.max.apply(null,g.map(function(v){return v.y+v.h;}));
  var cx=(minX+maxR)/2, cy=(minY+maxB)/2;
  g.forEach(function(v){
    if(a==='left')v.x=minX;else if(a==='right')v.x=maxR-v.w;else if(a==='center')v.x=Math.round(cx-v.w/2);
    else if(a==='top')v.y=minY;else if(a==='bottom')v.y=maxB-v.h;else if(a==='middle')v.y=Math.round(cy-v.h/2);
    else if(a==='w'||a==='size')v.w=ref.w;
    if(a==='h'||a==='size')v.h=ref.h;
    v.x=Math.max(0,Math.min(GRID.cols-v.w,v.x));v.y=Math.max(0,v.y);
  });
  if(a==='dh'||a==='dv'){
    var hor=a==='dh', s2=g.slice().sort(function(p,q){return hor?p.x-q.x:p.y-q.y;});
    var lo=hor?s2[0].x:s2[0].y, last=s2[s2.length-1], hi=hor?last.x+last.w:last.y+last.h;
    var used=s2.reduce(function(t,v){return t+(hor?v.w:v.h);},0), gap=Math.max(0,(hi-lo-used)/(s2.length-1)), pos=lo;
    s2.forEach(function(v){if(hor)v.x=Math.round(pos);else v.y=Math.round(pos);pos+=(hor?v.w:v.h)+gap;});
  }
  relayout();gridHeight();push();
}
function markSel(){
  renderAlignBar();
  var sv=SEL&&vis(SEL), tg=(sv&&sv.type==='slicer')?(sv.targets==null?PG().visuals.map(function(o){return o.id;}):sv.targets):[];
  document.querySelectorAll('.card').forEach(function(c){c.classList.toggle('sel',c.dataset.id===SEL);
    c.classList.toggle('msel',MSEL.length>1&&MSEL.indexOf(c.dataset.id)>=0);
    var isT=c.dataset.id!==SEL&&tg.indexOf(c.dataset.id)>=0, ix=c.querySelector('.ix');
    c.classList.toggle('target',isT);
    if(ix){var show=!!(sv&&sv.type==='slicer'&&c.dataset.id!==SEL);ix.style.display=show?'inline-block':'none';
      ix.className='ix '+(isT?'on':'off');ix.textContent=isT?'slicer: on':'slicer: off';
      ix.title=isT?'This visual follows the selected slicer - click to switch it off':'Not filtered by the selected slicer - click to switch it on';}});
  if(typeof renderFilterPane==='function'&&FDATA)renderFilterPane();
}
function cardAction(id,a){
  var vs=PG().visuals, i=vs.findIndex(function(v){return v.id===id;}), v=vs[i];
  if(a==='e'){bridge.exportVisual(id);return;}
  if(a==='x'){vs.splice(i,1);if(SEL===id)SEL=null;}
  else if(a==='d'){var c=JSON.parse(JSON.stringify(v));c.id=nextId();c.y=bottom();c.x=0;vs.push(c);SEL=c.id;}
  changed();
}
var FAIR={green:'#1F7A3A',amber:'#C98A00',red:'#C62828'};
function fillCard(c,v){
  var r=RESULTS[v.id], body=c.querySelector('.body'), dot=c.querySelector('.dot');
  c.querySelector('.title').textContent=(v.title_set&&v.title)||(r&&r.title)||TYPES[v.type].label;
  var cr=c.querySelector('.crumb');
  if(r&&r.drill){cr.innerHTML=(r.drill.depth?'<b data-up="1" title="One level up">⤴</b>':'')+esc(r.drill.path.concat([r.drill.levels[r.drill.depth]]).join(' › '))
      +(r.drill.can_down?' <span style="color:#9AA59C">(double-click a bar)</span>':'');
    cr.title='Drill-down: '+r.drill.levels.join(' › ');
    var up=cr.querySelector('[data-up]');if(up)up.onclick=function(e){e.stopPropagation();(v.drillpath||[]).pop();changed();};}
  else cr.innerHTML='';
  var nf=(v.filters||[]).length, fm=c.querySelector('.fmark');
  fm.textContent=nf?('filter '+nf):'';fm.style.display=nf?'':'none';
  fm.title=nf&&r&&r.vfilters?('Filters on this visual: '+r.vfilters.join(' · ')):'';
  if(r&&r.fair){dot.style.background=FAIR[r.fair.level];dot.title=r.fair.headline+' ('+r.fair.grouping+'): '+r.fair.text;dot.style.visibility='visible';}
  else dot.style.visibility='hidden';
  if(!r){body.innerHTML='<div class="empty">Calculating…</div>';return;}
  if(r.kind==='plotly'){
    if(body.querySelector('.plot')===null)body.innerHTML='';
    var p=body.querySelector('.plot');
    if(!p){body.innerHTML='<div class="plot"></div>'+(r.note?'<div class="note"></div>':'');p=body.querySelector('.plot');}
    var n=body.querySelector('.note');if(r.note){if(!n){n=document.createElement('div');n.className='note';body.appendChild(n);}n.textContent=r.note;}else if(n)n.remove();
    if(typeof Plotly==='undefined'){body.innerHTML='<div class="empty">The chart library could not be loaded (internet connection?).</div>';return;}
    if(r.selectable){r.figure.layout.dragmode='select';r.figure.layout.selectdirection='any';}
    if(p._rid!==r._rid){p._rid=r._rid;Plotly.react(p,r.figure.data,r.figure.layout,{responsive:true,displaylogo:false,displayModeBar:false});}
    if(!p._bound){p._bound=1;
      p.on('plotly_click',function(e){
        var vv=vis(v.id), rr=RESULTS[v.id], pt=e.points&&e.points[0];if(!pt||!vv)return;
        if(rr&&rr.selectable){toast('Drag a rectangle around points to filter the other visuals - double-click to clear');return;}
        if(!rr||!rr.clickable){toast('Click a bar, box or matrix cell to filter the other visuals');return;}
        var now=Date.now(), same=p._last&&p._last.x===String(pt.x)&&now-p._last.t<450;
        p._last={x:String(pt.x),t:now};
        if(same&&rr.drill&&rr.drill.can_down){        // double-click: one level down
          p._last=null;bridge.clearCross(v.id);
          vv.drillpath=(vv.drillpath||[]).concat([{key:rr.drill.cur,value:String(pt.x)}]);changed();return;}
        bridge.visualClick(v.id,JSON.stringify({x:pt.x,y:pt.y,n:(pt.data&&pt.data.name)||''}));});
      p.on('plotly_selected',function(e){
        var ids=[];((e&&e.points)||[]).forEach(function(q){if(q.customdata!=null)ids.push(q.customdata);});
        bridge.visualSelect(v.id,JSON.stringify(ids));});
      p.on('plotly_deselect',function(){bridge.visualSelect(v.id,'[]');});
    }
  } else if(r.kind==='slicer'){
    renderSlicer(body,v,r);
  } else if(r.kind==='kpi'){
    body.innerHTML='<div class="kpi"><div><span class="v'+(r.status?' '+r.status:'')+'">'+esc(r.value)+'</span><span class="u">'+esc(r.unit||'')+'</span></div><div class="s">'+esc(r.sub||'')+'</div></div>';
  } else if(r.kind==='table'){
    var h='<div class="tbl"><table><tr>'+r.head.map(function(x){return '<th>'+esc(x)+'</th>';}).join('')+'</tr>';
    r.rows.forEach(function(row){h+='<tr data-t="'+row[0]+'">'+row.slice(1).map(function(x){return '<td>'+esc(x)+'</td>';}).join('')+'</tr>';});
    h+='</table></div>'+(r.more?'<div class="note">'+r.more+' more trials not listed</div>':'')+'<div class="note">double-click a line to open it in Show Experiment</div>';
    body.innerHTML=h;
    body.querySelectorAll('tr[data-t]').forEach(function(tr){tr.addEventListener('dblclick',function(){bridge.openTrial(parseInt(tr.dataset.t));});});
  } else {
    body.innerHTML='<div class="empty">'+esc(r.message||'')+'</div>';
  }
}
// ── slicer ────────────────────────────────────────────────────
function selVals(v){return ((v.sel||{}).values||[]).map(String);}
function toggleVal(v,lab,multi){
  var cur=selVals(v), i=cur.indexOf(lab);
  if(multi){if(i>=0)cur.splice(i,1);else cur.push(lab);}
  else cur=(i>=0&&cur.length===1)?[]:[lab];
  v.sel=cur.length?{values:cur}:{};
  push();
}
function optListHtml(v,r){
  var q=(SLQ[v.id]||'').toLowerCase(), cur=selVals(v), h='';
  if((r.options||[]).length>8)h+='<input class="q" placeholder="Search…" value="'+esc(SLQ[v.id]||'')+'">';
  h+='<div class="acts"><a data-act="all" title="No selection = everything">All</a>'+(cur.length?'<a data-act="clr">Clear ('+cur.length+')</a>':'')+'</div><div class="opts">';
  (r.options||[]).forEach(function(o){
    if(q&&o.label.toLowerCase().indexOf(q)<0)return;
    var on=cur.indexOf(o.label)>=0;
    h+='<div class="opt'+(on?' on':'')+'" data-l="'+esc(o.label)+'"><span class="box'+(r.multi?'':' round')+'">'+(on?'✓':'')+'</span>'
      +'<span class="l">'+esc(o.label)+(r.unit&&r.fkind==='num'?' '+esc(r.unit):'')+'</span><span class="n">'+o.n+'</span></div>';
  });
  h+='</div>'+(r.more?'<div class="info">'+r.more+' more values - use the search</div>':'');
  return h;
}
function bindOptList(el,v,r){
  var q=el.querySelector('.q');
  if(q){q.addEventListener('input',function(){SLQ[v.id]=q.value;var pos=q.selectionStart;renderSlicer(el.closest('.body'),v,r);
    var nq=el.closest('.body').querySelector('.q');if(nq){nq.focus();nq.setSelectionRange(pos,pos);}});}
  el.querySelectorAll('.opt').forEach(function(o){o.addEventListener('click',function(){toggleVal(v,o.dataset.l,r.multi);
    o.classList.toggle('on');o.querySelector('.box').textContent=o.classList.contains('on')?'✓':'';});});
  el.querySelectorAll('.acts a').forEach(function(a){a.addEventListener('click',function(){v.sel={};push();});});
}
function renderSlicer(body,v,r){
  var st=r.style, cur=selVals(v), h='<div class="sl">';
  if(st==='between'){
    var rg=r.range;
    if(!rg){body.innerHTML='<div class="empty">No values</div>';return;}
    var lo=(v.sel&&v.sel.min!=null)?v.sel.min:rg.min, hi=(v.sel&&v.sel.max!=null)?v.sel.max:rg.max;
    h+='<div class="rng"><input type="number" class="mn" step="any" value="'+lo+'"><span>–</span><input type="number" class="mx" step="any" value="'+hi+'"></div>'
      +'<div class="dual"><div class="track"></div><div class="fill"></div>'
      +'<input type="range" class="r1" min="'+rg.min+'" max="'+rg.max+'" step="'+rg.step+'" value="'+lo+'">'
      +'<input type="range" class="r2" min="'+rg.min+'" max="'+rg.max+'" step="'+rg.step+'" value="'+hi+'"></div>'
      +'<div class="info">'+esc(String(rg.min))+' – '+esc(String(rg.max))+(r.unit?' '+esc(r.unit):'')+' in the trials the other filters leave</div>';
  } else if(st==='tiles'){
    h+='<div class="tiles">'+(r.options||[]).map(function(o){return '<button class="tile'+(cur.indexOf(o.label)>=0?' on':'')+'" data-l="'+esc(o.label)+'">'
      +esc(o.label)+' <span class="n">'+o.n+'</span></button>';}).join('')+'</div>'
      +(cur.length?'<div class="acts"><a data-act="clr">Clear ('+cur.length+')</a></div>':'');
  } else if(st==='dropdown'){
    var txt=cur.length===0?'All':(cur.length===1?cur[0]:cur.length+' selected');
    h+='<div class="dd"><button class="ddb" title="'+esc(cur.join(', ')||'All')+'">'+esc(txt)+'</button>'
      +(DDOPEN[v.id]?'<div class="ddp">'+optListHtml(v,r)+'</div>':'')+'</div>';
  } else {
    h+=optListHtml(v,r);
  }
  body.innerHTML=h+'</div>';
  var el=body.querySelector('.sl');
  if(st==='between'){
    var r1=el.querySelector('.r1'), r2=el.querySelector('.r2'), mn=el.querySelector('.mn'), mx=el.querySelector('.mx'), fill=el.querySelector('.fill');
    function paint(){var a=+r1.value,b=+r2.value,span=(r.range.max-r.range.min)||1;
      fill.style.left=((Math.min(a,b)-r.range.min)/span*100)+'%';fill.style.right=(100-(Math.max(a,b)-r.range.min)/span*100)+'%';}
    function commit(a,b){a=+a;b=+b;if(a>b){var t=a;a=b;b=t;}
      v.sel=(a<=r.range.min&&b>=r.range.max)?{}:{min:a,max:b};push();}
    r1.addEventListener('input',function(){mn.value=r1.value;paint();});
    r2.addEventListener('input',function(){mx.value=r2.value;paint();});
    r1.addEventListener('change',function(){commit(r1.value,r2.value);});
    r2.addEventListener('change',function(){commit(r1.value,r2.value);});
    mn.addEventListener('change',function(){commit(mn.value,mx.value);});
    mx.addEventListener('change',function(){commit(mn.value,mx.value);});
    paint();
  } else if(st==='tiles'){
    el.querySelectorAll('.tile').forEach(function(b){b.addEventListener('click',function(){toggleVal(v,b.dataset.l,r.multi);b.classList.toggle('on');});});
    el.querySelectorAll('.acts a').forEach(function(a){a.addEventListener('click',function(){v.sel={};push();});});
  } else if(st==='dropdown'){
    el.querySelector('.ddb').addEventListener('click',function(e){e.stopPropagation();DDOPEN[v.id]=!DDOPEN[v.id];renderSlicer(body,v,r);});
    var pop=el.querySelector('.ddp');if(pop){pop.addEventListener('mousedown',function(e){e.stopPropagation();});bindOptList(pop,v,r);}
  } else bindOptList(el,v,r);
}
document.addEventListener('mousedown',function(e){
  if(e.target.closest('.dd'))return;
  var open=Object.keys(DDOPEN).filter(function(k){return DDOPEN[k];});
  if(!open.length)return;
  open.forEach(function(k){DDOPEN[k]=false;});
  document.querySelectorAll('.card').forEach(function(c){var v=vis(c.dataset.id), r=RESULTS[c.dataset.id];if(v&&r&&r.kind==='slicer')renderSlicer(c.querySelector('.body'),v,r);});
});

var _rid=0;
function renderResults(data){
  if(data.page&&data.page!==PG().id)return;          // late answer for a page we already left
  Object.keys(data.results).forEach(function(id){data.results[id]._rid=++_rid;});
  RESULTS=data.results;
  FDATA={all:data.allFilters||[],page:data.pageFilters||[],cross:data.cross||[],slicers:data.slicers||[],ply:data.plyScope||'any'};
  renderFilterPane();
  var x=document.getElementById('cross');
  x.innerHTML=data.cross.map(function(c){return '<span class="xchip" data-s="'+esc(c.source)+'" title="Clicked in '+esc(c.from)+' - click to remove">'+esc(c.text)+'  ×</span>';}).join('');
  x.querySelectorAll('.xchip').forEach(function(ch){ch.addEventListener('click',function(){bridge.clearCross(ch.dataset.s);});});
  document.querySelectorAll('.card').forEach(function(c){var v=vis(c.dataset.id);if(v)fillCard(c,v);});
  if(SEL)renderWells();
}
function snapshotAll(){ /* for a later PDF step */ }
</script></body></html>"""
