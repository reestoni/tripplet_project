# ui/smart_dashboard_html.py
"""Web page of the Smart Chart dashboard (ui/smart_dashboard.py): page
canvas with visuals, Visualizations pane (types + wells) and Fields pane
(all tables, collapsible, drag & drop) - modelled on Power BI.
The page owns the layout (spec); Python computes every visual
(ui/smart_dashboard_engine.py) and sends results back via renderResults().
Raw string on purpose: backslashes in the JS stay as they are."""

DASHBOARD_HTML = r"""<!doctype html><html><head><meta charset="utf-8">
<script src="plotly-2.32.0.min.js"></script>
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
#fpane.collapsed,#viz.collapsed,#fields.collapsed{width:30px!important;padding:8px 0;overflow:hidden;cursor:pointer}
.grip{position:absolute;left:-3px;top:0;bottom:0;width:7px;cursor:col-resize;z-index:30}
.grip:hover,.grip.on{background:linear-gradient(90deg,transparent 2px,#1F7A3A 2px,#1F7A3A 4px,transparent 4px)}
.pane.collapsed .grip{display:none}
body.resizing{cursor:col-resize;user-select:none}
body.resizing iframe,body.resizing .plot{pointer-events:none}
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
.txt{padding:2px 6px 6px;font-size:13px;line-height:1.45;overflow:auto;flex:1;min-height:0}
.txt .th{font-size:1.45em;font-weight:700;color:#165C2B;margin:2px 0 4px}
.txt .tl{color:#1C2321}
.card.textcard{background:transparent;border-color:transparent}
.card.textcard .head{position:absolute;right:4px;top:2px;padding:2px;z-index:2;background:transparent}
.card.textcard .head .title:empty,.card.textcard .head .dot{display:none}
.card.textcard .body{padding-top:6px}
.card.textcard:hover,.card.textcard.sel{background:#fff;border-color:#DADFD8}
.ro .card.textcard:hover{background:transparent;border-color:transparent}
textarea{width:100%;border:1px solid #C9D1C8;border-radius:5px;font:inherit;padding:5px 6px;resize:vertical}
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
.sl .opts{flex:1;min-height:0;overflow:auto;display:flex;flex-direction:column}
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
.sl .yr{display:flex;align-items:center;gap:6px;padding:3px 4px;border-radius:4px;cursor:pointer;font-weight:600}
.sl .yr:hover,.sl .mo:hover{background:#F0F7F2}
.sl .yr .car{width:12px;color:#5A6460;font-size:10px;flex:none;text-align:center}
.sl .mo{display:flex;align-items:center;gap:7px;padding:2px 4px 2px 24px;border-radius:4px;cursor:pointer}
.sl .mo.zero{color:#B5BCB7}
.sl .yr .l,.sl .mo .l{flex:1}
.sl .box.part{background:#9CC8A9;border-color:#1F7A3A}
.sl .on>.box{background:#1F7A3A;border-color:#1F7A3A}
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
.vtabs{display:flex;gap:2px;margin:0 0 10px;border-bottom:1px solid #DADFD8}
.vtabs button{flex:1;border:none;background:transparent;font:inherit;font-weight:600;color:#5A6460;padding:6px 0 7px;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px}
.vtabs button:hover{color:#1C2321}
.vtabs button.on{color:#165C2B;border-bottom-color:#1F7A3A}
.fdot{display:inline-block;width:6px;height:6px;border-radius:3px;background:#1F7A3A;vertical-align:middle;margin-left:3px}
.fmt{border:1px solid #EEF1ED;border-radius:6px;margin-bottom:6px}
.fmt>summary{padding:6px 8px;font-size:12px;color:#1C2321;display:flex;align-items:center;gap:6px}
.fmt>summary .rst{margin-left:auto;font-weight:400;font-size:11px;color:#1F7A3A;text-decoration:underline;cursor:pointer}
.fmt .in{padding:2px 8px 8px}
.fmt .row{margin-top:6px}
.fmt .row .lab{font-size:11px;font-weight:600;color:#5A6460;margin-bottom:3px;display:flex;justify-content:space-between;align-items:center}
.fmt .row .lab label{font-weight:400;display:flex;gap:4px;align-items:center;cursor:pointer}
.fmt .two{display:flex;gap:6px}
.fmt .two input{width:50%}
.fmt input.t:disabled{background:#F4F6F3;color:#9AA59C}
.crow{display:flex;align-items:center;gap:6px;padding:2px 0;font-size:12px}
.crow span{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.crow b{cursor:pointer;font-weight:400;color:#5A6460;padding:0 4px;border-radius:4px}
.crow b:hover{background:#EEF1ED;color:#C62828}
.sw{width:22px;height:16px;border:1px solid #9AA59C;border-radius:4px;cursor:pointer;flex:none;padding:0}
.chk{display:flex;gap:6px;align-items:center;font-size:12px;cursor:pointer;margin-top:6px}
.rule{border:1px solid #EEF1ED;border-radius:6px;padding:5px 22px 5px 5px;margin-top:6px;display:flex;flex-direction:column;gap:4px;position:relative}
.rule .rx{position:absolute;right:4px;top:2px;cursor:pointer;color:#5A6460;padding:0 4px;border-radius:4px}
.rule .rx:hover{background:#EEF1ED;color:#C62828}
.rule select,.rule input{height:26px}
.tbl th.srt{cursor:pointer;user-select:none}
.tbl th.srt:hover{background:#E9EDE8}
#views{display:flex;border:1px solid #C9D1C8;border-radius:7px;overflow:hidden;flex:none}
#views button{border:none;background:#fff;font:inherit;font-size:12px;padding:0 12px;height:28px;cursor:pointer;color:#5A6460}
#views button.on{background:#1F7A3A;color:#fff;font-weight:600}
#model{display:none;flex:1;min-height:0;gap:12px}
body.modelmode #model{display:flex}
body.modelmode #grid,body.modelmode #tabs,body.modelmode #addv,body.modelmode #alignbar,body.modelmode #cross,
body.modelmode #pagetitle,body.modelmode #fpane,body.modelmode #viz,body.modelmode #fields{display:none!important}
#mcanvas{flex:1;min-width:0;position:relative;background:#fff;border:1px solid #DADFD8;border-radius:10px;overflow:hidden}
#mcanvas svg{position:absolute;inset:0;width:100%;height:100%}
.mnode{position:absolute;width:168px;background:#fff;border:1px solid #C9D1C8;border-left:4px solid #232E3A;border-radius:8px;
  padding:6px 9px;cursor:pointer;box-shadow:0 1px 3px rgba(0,0,0,.06);transform:translate(-50%,-50%)}
.mnode:hover{box-shadow:0 3px 10px rgba(0,0,0,.12)}
.mnode.lab{border-left-color:#8CC63F}
.mnode.calc{border-left-color:#8C6BB1}
.mnode.centre{width:190px;border:2px solid #1F7A3A;border-left-width:6px;background:#F0F7F2}
.mnode.on{outline:2px solid #1F7A3A;outline-offset:2px}
.mnode b{display:block;font-size:12.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mnode span{display:block;font-size:10.5px;color:#5A6460;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#mdetail{width:300px;flex:none;background:#fff;border:1px solid #DADFD8;border-radius:10px;padding:12px 14px;overflow:auto}
#mdetail h4{margin:0 0 2px;font-size:15px;color:#165C2B}
#mdetail .rel{display:inline-block;font-size:11px;font-weight:700;color:#fff;background:#232E3A;border-radius:9px;padding:1px 8px;margin:4px 0 8px}
#mdetail .how{font-size:12px;line-height:1.45;color:#1C2321;margin-bottom:8px}
#mdetail .tbls{font-size:11px;color:#5A6460;margin-bottom:10px}
#mdetail .mf{display:flex;align-items:center;gap:6px;padding:3px 0;border-top:1px solid #F0F2EF;font-size:12px}
#mdetail .mf .nm{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#mdetail .mf .fl{font-size:11px;color:#5A6460;flex:none}
#mdetail .mf .bar{width:46px;height:5px;border-radius:3px;background:#EEF1ED;flex:none;overflow:hidden}
#mdetail .mf .bar i{display:block;height:100%;background:#8CC63F}
#mdetail .key{font-size:11px;color:#5A6460;line-height:1.5;margin-top:12px;border-top:1px solid #EEF1ED;padding-top:8px}
#mdetail .lock{font-size:11px;color:#5A6460;background:#F4F6F3;border-radius:6px;padding:5px 8px;margin-top:10px}
#painter{display:inline-flex;align-items:center;gap:6px;padding:0 11px 0 8px;font-weight:600;color:#165C2B;background:#F0F7F2;border-color:#CFE3D5}
#painter:hover:not(:disabled){background:#E1F0E5;border-color:#1F7A3A}
#painter:disabled{opacity:.45;cursor:default}
#painter.on{background:#1F7A3A;border-color:#1F7A3A;color:#fff}
#painter.on.sticky{box-shadow:0 0 0 3px #8CC63F}
body.painting .card{cursor:copy}
body.painting .card .head{cursor:copy}
body.painting .card.psrc{outline:2px solid #8CC63F;outline-offset:2px}
.ro #painter{display:none!important}
.dot.fair{cursor:pointer}
.ro .card:hover .ib.fo{display:inline-block!important}
.dot.fair:hover{box-shadow:0 0 0 3px rgba(0,0,0,.12)}
#focus{position:absolute;inset:0;z-index:40;background:#F4F6F3;display:none;flex-direction:column;padding:12px 14px;gap:10px}
#focus.on{display:flex}
#focus .fh{display:flex;align-items:center;gap:10px}
#focus .fh b{font-size:15px;flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#focus .fbox{background:#fff;border:1px solid #DADFD8;border-radius:10px;padding:8px;display:flex;flex-direction:column;min-height:0}
#focus .fplot{flex:3;min-height:160px}
#focus .fplot .plot{flex:1}
#focus .flist{flex:2;min-height:120px}
#focus .flist .tbl{flex:1}
#focus .flist tr.hit td{background:#DDEFE3!important}
#focus .fnote{font-size:11px;color:#5A6460;padding:4px 2px 0}
#canvas{position:relative}
#dtbar{display:none;align-items:center;gap:8px;flex-wrap:wrap;background:#FFF6E0;border:1px solid #F0D58A;border-radius:8px;padding:5px 10px;margin-bottom:8px;font-size:12px}
#dtbar.on{display:flex}
#dtbar .dtt{flex:1;min-width:0}
#dtbar .dtt i{font-style:normal;background:#fff;border:1px solid #F0D58A;border-radius:10px;padding:1px 8px;margin-left:4px;white-space:nowrap}
#dtbar .btn{height:26px}
body.modelmode #dtbar{display:none!important}
#dtmenu{position:fixed;z-index:60;background:#fff;border:1px solid #C9D1C8;border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.16);padding:4px;min-width:180px}
#dtmenu .mh{font-size:11px;font-weight:700;color:#5A6460;padding:4px 8px 3px;text-transform:uppercase;letter-spacing:.04em}
#dtmenu .mv{font-size:11px;color:#5A6460;padding:0 8px 5px;border-bottom:1px solid #EEF1ED;margin-bottom:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:260px}
#dtmenu .mi{padding:6px 10px;border-radius:5px;cursor:pointer;font-weight:600;color:#165C2B}
#dtmenu .mi:hover{background:#F0F7F2}
.an .two select{width:50%}
.dtf{display:flex;flex-wrap:wrap;gap:4px;margin:4px 0}
#toast{position:fixed;bottom:14px;left:50%;transform:translateX(-50%);background:#1C2321;color:#fff;padding:6px 14px;border-radius:6px;opacity:0;transition:opacity .2s;pointer-events:none}
</style></head><body>
<div id="app">
  <div id="canvas">
    <div class="bar">
      <div id="views" title="Report: the pages with their visuals · Model: how the tables hang together (read only)">
        <button data-view="report" class="on">Report</button><button data-view="model">Model</button></div>
      <input id="pagetitle" value="Page 1" title="Name of this page">
      <button class="btn add" id="addv" title="Add an empty visual - then pick a type and drag fields into it">+ New visual</button>
      <button class="btn" id="painter" disabled title="Copy format: click a visual, then this button, then the visual that should get the same format. Double-click: keep copying until Esc."><svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke-linecap="round" stroke-linejoin="round"><rect x="1.5" y="1.8" width="13" height="6" rx="2" fill="#8CC63F" stroke="#1F7A3A" stroke-width="1.2"/><line x1="4" y1="3.9" x2="10.5" y2="3.9" stroke="#FFFFFF" stroke-width="1.1" stroke-opacity=".8"/><path d="M14.5 4.8H17.2V10.2H9.5V12.2" stroke="#232E3A" stroke-width="1.5"/><rect x="7.9" y="12.2" width="3.2" height="6.3" rx="1.3" fill="#232E3A"/></svg>Copy format</button>
      <div id="alignbar"></div>
      <div id="cross"></div>
    </div>
    <div id="dtbar"></div>
    <div id="grid"></div>
    <div id="model"><div id="mcanvas"></div><div id="mdetail"></div></div>
    <div id="focus"></div>
    <div id="tabs"></div>
  </div>
  <div id="fpane" class="pane"><div class="grip" title="Drag to make it wider or narrower - double-click for the standard width"></div><div class="strip" title="Show Filters"><span>‹</span><span>Filters</span></div>
    <div class="ph"><h3>Filters</h3><button class="fold" data-p="fpane" title="Collapse to get more room for the page">›</button></div>
    <div id="fbody"></div></div>
  <div id="viz" class="pane"><div class="grip" title="Drag to make it wider or narrower - double-click for the standard width"></div><div class="strip" title="Show Visualizations"><span>‹</span><span>Visualizations</span></div>
    <div class="ph"><h3>Visualizations</h3><button class="fold" data-p="viz" title="Collapse to get more room for the page">›</button></div>
    <div class="gallery" id="gallery"></div><div id="wells"></div></div>
  <div id="fields" class="pane"><div class="grip" title="Drag to make it wider or narrower - double-click for the standard width"></div><div class="strip" title="Show Fields"><span>‹</span><span>Fields</span></div>
    <div class="ph" style="padding:12px 12px 0"><h3>Fields</h3><button class="fold" data-p="fields" title="Collapse to get more room for the page">›</button></div>
    <input id="fsearch" placeholder="Search a field…"><div id="flist"></div></div>
</div>
<div id="toast"></div>
<script>
var MULTIW=['columns','drill','values'], PSIZES={}, PIESHAPES={}, FORMATS={}, SORTS={}, LEGENDPOS={}, PALS={}, MSCALES={}, FONTS={}, CARDSIZES={}, RULEOPS={}, RULECOLS={}, MONTHOF={}, YOPEN={}, RO=false, STACKS={}, bridge=null, CATALOG=[], FIELDS={}, GROUPS=[], TREE=[], TYPES={}, WELLS={}, AGGS={}, SLSTYLES={}, DDOPEN={}, SLQ={};
var SPEC={pages:[{id:'p1',title:'Page 1',visuals:[],filters:[]}],active:'p1'}, SEL=null, RESULTS={}, PFILTERS=[];
var MSEL=[], GRID={cols:12,row:20}, GAP=10, FDATA={all:[],page:[],cross:[],slicers:[],ply:'any',through:null}, ANA={kinds:{},colours:{},defaults:{},types:[]};
function PG(){for(var i=0;i<SPEC.pages.length;i++)if(SPEC.pages[i].id===SPEC.active)return SPEC.pages[i];return SPEC.pages[0];}
var ICON={
 points:'<circle cx="7.5" cy="19" r="2.3" fill="#1F7A3A"/><circle cx="12.5" cy="12.5" r="2.3" fill="#8CC63F"/><circle cx="17" cy="16.5" r="2.3" fill="#1F7A3A"/><circle cx="22.5" cy="8" r="2.3" fill="#8CC63F"/><circle cx="23" cy="17" r="2.3" fill="#232E3A"/>',
 trend:'<line x1="4.5" y1="22" x2="25.5" y2="6" stroke="#232E3A" stroke-width="1.5" stroke-dasharray="2.6 2"/><circle cx="8" cy="17.5" r="2.2" fill="#1F7A3A"/><circle cx="13" cy="16" r="2.2" fill="#8CC63F"/><circle cx="17" cy="10.5" r="2.2" fill="#1F7A3A"/><circle cx="22.5" cy="10" r="2.2" fill="#8CC63F"/>',
 line:'<polyline points="4.5,21 10.5,16 16,18 25.5,8" stroke="#1F7A3A" stroke-width="2"/><polyline points="4.5,14 10.5,11 16,13 25.5,4.5" stroke="#8CC63F" stroke-width="1.6"/><circle cx="10.5" cy="16" r="1.6" fill="#232E3A"/><circle cx="16" cy="18" r="1.6" fill="#232E3A"/>',
 bar:'<line x1="3.5" y1="24" x2="26.5" y2="24" stroke="#232E3A" stroke-width="1.4"/><rect x="5.5" y="13" width="5" height="10" rx="1.2" fill="#1F7A3A"/><rect x="12.5" y="6" width="5" height="17" rx="1.2" fill="#8CC63F"/><rect x="19.5" y="10" width="5" height="13" rx="1.2" fill="#1F7A3A"/>',
 box:'<line x1="9.5" y1="4" x2="9.5" y2="23" stroke="#232E3A" stroke-width="1.3"/><rect x="6" y="9" width="7" height="9" rx="1.3" fill="#D6EBDC" stroke="#1F7A3A" stroke-width="1.5"/><line x1="6" y1="13" x2="13" y2="13" stroke="#232E3A" stroke-width="1.5"/><line x1="20.5" y1="6" x2="20.5" y2="21" stroke="#232E3A" stroke-width="1.3"/><rect x="17" y="8" width="7" height="8" rx="1.3" fill="#EEF7D9" stroke="#8CC63F" stroke-width="1.5"/><line x1="17" y1="11" x2="24" y2="11" stroke="#232E3A" stroke-width="1.5"/>',
 violin:'<path d="M9.5 3.5C14 9 12.5 15.5 9.5 24.5C6.5 15.5 5 9 9.5 3.5Z" fill="#1F7A3A"/><path d="M20.5 5.5C25 11 23.5 16.5 20.5 23C17.5 16.5 16 11 20.5 5.5Z" fill="#8CC63F"/><line x1="7.2" y1="13" x2="11.8" y2="13" stroke="#FFFFFF" stroke-width="1.3"/><line x1="18.2" y1="13.5" x2="22.8" y2="13.5" stroke="#232E3A" stroke-width="1.3"/>',
 hist:'<line x1="3.5" y1="24" x2="26.5" y2="24" stroke="#232E3A" stroke-width="1.4"/><rect x="4.0" y="18" width="4" height="5" rx="0.8" fill="#8CC63F"/><rect x="8.5" y="12" width="4" height="11" rx="0.8" fill="#1F7A3A"/><rect x="13.0" y="6" width="4" height="17" rx="0.8" fill="#1F7A3A"/><rect x="17.5" y="11" width="4" height="12" rx="0.8" fill="#1F7A3A"/><rect x="22.0" y="17" width="4" height="6" rx="0.8" fill="#8CC63F"/>',
 density:'<ellipse cx="15" cy="14" rx="11.5" ry="8.5" fill="#D6EBDC"/><ellipse cx="15" cy="14" rx="7.5" ry="5.2" fill="#8CC63F"/><ellipse cx="15" cy="14" rx="3.6" ry="2.5" fill="#1F7A3A"/>',
 column:'<line x1="3.5" y1="24" x2="26.5" y2="24" stroke="#232E3A" stroke-width="1.4"/><rect x="5.5" y="15" width="5" height="8" fill="#1F7A3A"/><rect x="5.5" y="10" width="5" height="5" rx="1" fill="#8CC63F"/><rect x="12.5" y="11" width="5" height="12" fill="#1F7A3A"/><rect x="12.5" y="4.5" width="5" height="6.5" rx="1" fill="#8CC63F"/><rect x="19.5" y="17" width="5" height="6" fill="#1F7A3A"/><rect x="19.5" y="12" width="5" height="5" rx="1" fill="#8CC63F"/>',
 stack:'<line x1="3.5" y1="24" x2="26.5" y2="24" stroke="#232E3A" stroke-width="1.4"/><rect x="6" y="15" width="7" height="8" fill="#1F7A3A"/><rect x="6" y="9" width="7" height="6" fill="#8CC63F"/><rect x="6" y="4.5" width="7" height="4.5" rx="1" fill="#232E3A"/><rect x="17" y="13" width="7" height="10" fill="#1F7A3A"/><rect x="17" y="8.5" width="7" height="4.5" fill="#8CC63F"/><rect x="17" y="5" width="7" height="3.5" rx="1" fill="#232E3A"/>',
 pie:'<circle cx="15" cy="14" r="10" fill="#8CC63F"/><path d="M15 14V4A10 10 0 0 1 23.66 19Z" fill="#1F7A3A"/><path d="M15 14L23.66 19A10 10 0 0 1 11 23.17Z" fill="#232E3A"/><circle cx="15" cy="14" r="10" fill="none" stroke="#FFFFFF" stroke-width="0.8"/>',
 control:'<line x1="3.5" y1="6" x2="26.5" y2="6" stroke="#C62828" stroke-width="1.1" stroke-dasharray="2.4 1.8"/><line x1="3.5" y1="22" x2="26.5" y2="22" stroke="#C62828" stroke-width="1.1" stroke-dasharray="2.4 1.8"/><line x1="3.5" y1="14" x2="26.5" y2="14" stroke="#232E3A" stroke-width="1.2"/><polyline points="4.5,15 9,11.5 13.5,16.5 18,12 22.5,4" stroke="#1F7A3A" stroke-width="1.7"/><circle cx="9" cy="11.5" r="1.6" fill="#1F7A3A"/><circle cx="13.5" cy="16.5" r="1.6" fill="#1F7A3A"/><circle cx="22.5" cy="4" r="2" fill="#C62828"/>',
 radar:'<polygon points="15,3 25.5,10.5 21.5,23.5 8.5,23.5 4.5,10.5" fill="none" stroke="#C9D1C8" stroke-width="1"/><polygon points="15,8.5 20,12 18,18.5 12,18.5 10,12" fill="none" stroke="#DADFD8" stroke-width="0.8"/><polygon points="15,5 22.5,11.5 17.5,20.5 9.5,21.5 8,12" fill="#1F7A3A" fill-opacity="0.35" stroke="#1F7A3A" stroke-width="1.5"/><polygon points="15,10 19,12 20.5,21 12,19 6.5,11" fill="none" stroke="#8CC63F" stroke-width="1.5"/>',
 matrix:'<rect x="4.0" y="4.0" width="6.6" height="5.8" rx="1.1" fill="#1F7A3A"/><rect x="11.6" y="4.0" width="6.6" height="5.8" rx="1.1" fill="#8CC63F"/><rect x="19.2" y="4.0" width="6.6" height="5.8" rx="1.1" fill="#D6EBDC"/><rect x="4.0" y="10.8" width="6.6" height="5.8" rx="1.1" fill="#8CC63F"/><rect x="11.6" y="10.8" width="6.6" height="5.8" rx="1.1" fill="#1F7A3A"/><rect x="19.2" y="10.8" width="6.6" height="5.8" rx="1.1" fill="#232E3A"/><rect x="4.0" y="17.6" width="6.6" height="5.8" rx="1.1" fill="#D6EBDC"/><rect x="11.6" y="17.6" width="6.6" height="5.8" rx="1.1" fill="#232E3A"/><rect x="19.2" y="17.6" width="6.6" height="5.8" rx="1.1" fill="#1F7A3A"/>',
 kpi:'<text x="15" y="17" font-size="11.5" font-weight="700" text-anchor="middle" fill="#1F7A3A" font-family="Segoe UI,Arial,sans-serif">123</text><line x1="7" y1="21.5" x2="23" y2="21.5" stroke="#8CC63F" stroke-width="2"/>',
 table:'<rect x="4" y="4.5" width="22" height="19" rx="2" fill="#FFFFFF" stroke="#232E3A" stroke-width="1.3"/><path d="M4 6.5A2 2 0 0 1 6 4.5H24A2 2 0 0 1 26 6.5V10H4Z" fill="#1F7A3A"/><line x1="4" y1="16.5" x2="26" y2="16.5" stroke="#C9D1C8" stroke-width="1"/><line x1="12" y1="10" x2="12" y2="23.5" stroke="#C9D1C8" stroke-width="1"/><rect x="12.6" y="10.6" width="12.8" height="5.4" fill="#D6EBDC"/>',
 slicer:'<rect x="4" y="4.5" width="6" height="6" rx="1.4" fill="#1F7A3A"/><polyline points="5.3,7.6 6.6,8.9 8.9,6" stroke="#FFFFFF" stroke-width="1.3"/><line x1="13" y1="7.5" x2="26" y2="7.5" stroke="#232E3A" stroke-width="1.5"/><rect x="4" y="11.5" width="6" height="6" rx="1.4" fill="#FFFFFF" stroke="#232E3A" stroke-width="1.2"/><line x1="13" y1="14.5" x2="23" y2="14.5" stroke="#9AA59C" stroke-width="1.5"/><rect x="4" y="18.5" width="6" height="6" rx="1.4" fill="#8CC63F"/><polyline points="5.3,21.6 6.6,22.9 8.9,20" stroke="#FFFFFF" stroke-width="1.3"/><line x1="13" y1="21.5" x2="21" y2="21.5" stroke="#232E3A" stroke-width="1.5"/>',
 text:'<text x="4" y="13.5" font-size="11" font-weight="700" fill="#232E3A" font-family="Segoe UI,Arial,sans-serif">Aa</text><line x1="4.5" y1="18" x2="25.5" y2="18" stroke="#1F7A3A" stroke-width="1.6"/><line x1="4.5" y1="22.5" x2="19" y2="22.5" stroke="#8CC63F" stroke-width="1.6"/>'
};
function icon(t){return '<svg width="30" height="28" viewBox="0 0 30 28" fill="none" stroke-linecap="round" stroke-linejoin="round">'+(ICON[t]||'')+'</svg>';}
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
// side panes: drag the left edge to make them wider or narrower (remembered per user), double-click = standard
var PANE_MIN=170, PANE_MAX=560;
function paneKey(id){return id==='fpane'?'filters':id;}
document.querySelectorAll('.grip').forEach(function(g){
  var pane=g.parentNode;
  g.addEventListener('mousedown',function(e){
    if(e.button!==0)return;e.preventDefault();e.stopPropagation();
    var sx=e.clientX, sw=pane.getBoundingClientRect().width, w=sw, t=null;
    g.classList.add('on');document.body.classList.add('resizing');
    function mm(ev){w=Math.max(PANE_MIN,Math.min(PANE_MAX,Math.round(sw+(sx-ev.clientX))));pane.style.width=w+'px';
      clearTimeout(t);t=setTimeout(relayout,60);}
    function mu(){document.removeEventListener('mousemove',mm);document.removeEventListener('mouseup',mu);
      g.classList.remove('on');document.body.classList.remove('resizing');relayout();
      if(bridge&&Math.abs(w-sw)>1)bridge.paneWidth(paneKey(pane.id),w);}
    document.addEventListener('mousemove',mm);document.addEventListener('mouseup',mu);
  });
  g.addEventListener('dblclick',function(e){e.stopPropagation();pane.style.width='';relayout();if(bridge)bridge.paneWidth(paneKey(pane.id),0);});
});

window.addEventListener('resize',function(){clearTimeout(window._rz);window._rz=setTimeout(resizePlots,120);});

function init(data){
  CATALOG=data.catalog;GROUPS=data.groups;TREE=data.tree||GROUPS.map(function(g){return [g,[]];});TYPES=data.types;WELLS=data.wells;AGGS=data.aggs;SLSTYLES=data.slicer_styles||{};STACKS=data.stacks||{};FORMATS=data.formats||{};PIESHAPES=data.pie_shapes||{pie:'Pie',donut:'Donut'};PSIZES=data.point_sizes||{};SORTS=data.sorts||{};LEGENDPOS=data.legend_pos||{};PALS=data.palettes||{};MSCALES=data.matrix_scales||{};FONTS=data.font_sizes||{};CARDSIZES=data.card_sizes||{};RULEOPS=data.rule_ops||{};RULECOLS=data.rule_colours||{};MONTHOF=data.month_of||{};ANA=data.analytics||ANA;MULTIW=data.multi_wells||MULTIW;
  FIELDS={};CATALOG.forEach(function(f){FIELDS[f.key]=f;});
  SPEC=data.spec;SEL=null;MSEL=[];GRID=data.grid||GRID;LAST=JSON.stringify(SPEC);HIST=[];FUT=[];
  RO=!!data.readonly;document.body.classList.toggle('ro',RO);
  MODEL=data.model||{nodes:[]};NTRIALS=data.trials||0;MFILL={};
  if(document.body.classList.contains('modelmode'))renderModel();
  var pw=data.pane_widths||{};['fpane','viz','fields'].forEach(function(id){var w=pw[paneKey(id)];
    document.getElementById(id).style.width=w?Math.max(PANE_MIN,Math.min(PANE_MAX,w))+'px':'';});
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
  if(e.key==='Escape'&&(PAINT||FOCUS)){endPaint();closeFocus();return;}
  var tag=(e.target&&e.target.tagName)||'';if(tag==='INPUT'||tag==='TEXTAREA'||tag==='SELECT'||RO)return;
  if((e.ctrlKey||e.metaKey)&&!e.shiftKey&&e.key.toLowerCase()==='z'){e.preventDefault();undo();}
  else if((e.ctrlKey||e.metaKey)&&(e.key.toLowerCase()==='y'||(e.shiftKey&&e.key.toLowerCase()==='z'))){e.preventDefault();redo();}
  else if(e.key==='Delete'&&SEL){cardAction(SEL,'x');}
  else if((e.ctrlKey||e.metaKey)&&e.shiftKey&&e.key.toLowerCase()==='v'){e.preventDefault();copyFormat();}
  else if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='a'){e.preventDefault();MSEL=PG().visuals.map(function(v){return v.id;});
    if(!SEL&&MSEL.length)SEL=MSEL[0];markSel();renderWells();}
  else if(e.key==='Escape'){clearSel();}
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
  if(MULTIW.indexOf(well)>=0){v.wells[well]=(v.wells[well]||[]);if(v.wells[well].indexOf(key)<0)v.wells[well].push(key);}
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
    if(MULTIW.indexOf(wl)>=0||!w[wl]){if(accepts(wl,key,v)){setWell(v,wl,key);changed();return;}}
  }
  toast('No free well for this field - drag it onto a well to replace');
}

// ── Format tab (Etappe 1): sort & Top N, numbers, data labels, axes, legend ──
var VTAB='build', FMTSHUT={};
var FMT_KEYS={sort:['sort','top'],numbers:['decimals'],labels:['labels'],errbars:['errbars'],colours:['palette','colours','colour','scale'],markers:['shapes','psize'],text:['font','grid'],axes:['xtitle','ytitle','ymin','ymax','xlog','ylog'],legend:['legend'],card:['vsize','unit','sub'],table:['tsort','rules']};
var FMT_NAMES={sort:'Sort and Top N',numbers:'Numbers',labels:'Data labels',errbars:'Error bars',colours:'Colours',markers:'Points and lines',text:'Text and grid',axes:'Axes',legend:'Legend',card:'Card',table:'Table: order and colour rules'};
function fmtSet(v,key,val){v.fmt=v.fmt||{};
  if(val===null||val===undefined||val==='auto'||(typeof val==='number'&&isNaN(val)))delete v.fmt[key];else v.fmt[key]=val;
  if(!Object.keys(v.fmt).length)delete v.fmt;changed();}
function fmtNum(s){s=String(s==null?'':s).trim().replace(',','.');return s===''?null:parseFloat(s);}
function opts(map,cur){return Object.keys(map).map(function(k){return '<option value="'+k+'"'+(String(cur)===k?' selected':'')+'>'+esc(map[k])+'</option>';}).join('');}
function axisTitle(v,axis){var r=RESULTS[v.id], lay=r&&r.figure&&r.figure.layout, a=lay&&lay[axis], t=a&&a.title;
  return (t&&t.text)||'';}
function formatHtml(v,secs){
  var f=v.fmt||{}, h='';
  var show=secs.filter(function(s){return s!=='yrange'&&s!=='logx'&&s!=='logy';});
  show.forEach(function(sec){
    var keys=FMT_KEYS[sec].filter(function(k){return sec!=='axes'||((secs.indexOf('yrange')>=0||(k!=='ymin'&&k!=='ymax'))
      &&(secs.indexOf('logx')>=0||k!=='xlog')&&(secs.indexOf('logy')>=0||k!=='ylog'));});
    var set=keys.some(function(k){return f[k]!==undefined;});
    h+='<details class="fmt" data-sec="'+sec+'"'+(FMTSHUT[sec]?'':' open')+'><summary><span class="arr">▸</span>'+esc(FMT_NAMES[sec])
      +(set?' <i class="fdot" title="Changed from the standard"></i><span class="rst" data-rst="'+sec+'" title="Back to the standard">Reset</span>':'')+'</summary><div class="in">';
    if(sec==='sort'){
      h+='<div class="row"><div class="lab">Order</div><select id="fsort">'+opts(SORTS,f.sort||'auto')+'</select></div>'
        +'<div class="row"><div class="lab">Show only the top</div><input class="t" id="ftop" type="number" min="1" step="1" placeholder="all" value="'+(f.top||'')+'"></div>'
        +'<div class="hint" style="margin-top:4px">Top N keeps the highest values (the lowest when sorted low to high).</div>';
    } else if(sec==='numbers'){
      h+='<div class="row"><div class="lab">Decimal places</div><select id="fdec">'
        +opts({auto:autoLab('decimals',String,'Automatic'),0:'0',1:'1',2:'2',3:'3',4:'4'},f.decimals==null?'auto':f.decimals)+'</select></div>';
    } else if(sec==='labels'){
      h+='<div class="row"><div class="lab">Values on the chart</div><select id="flab">'
        +opts({auto:autoLab('labels',function(x){return x?'On':'Off';},'Automatic'),on:'On',off:'Off'},f.labels===true?'on':f.labels===false?'off':'auto')+'</select></div>';
    } else if(sec==='errbars'){
      h+='<div class="row"><div class="lab">Bars on the mean</div><select id="ferr">'
        +opts({auto:'Standard deviation',ci:'95 % confidence',minmax:'Min – Max',off:'Off'},f.errbars||'auto')+'</select></div>'
        +'<div class="hint" style="margin-top:4px">Standard deviation: how much the trials scatter. 95 % confidence: where the true mean lies - '
        +'if two bars hardly overlap, the difference is probably real. Min – Max: worst and best trial.'+'</div>';
    } else if(sec==='axes'){
      [['xtitle','X axis title','xaxis'],['ytitle','Y axis title','yaxis']].forEach(function(a){
        var hidden=f[a[0]]==='';
        h+='<div class="row"><div class="lab"><span>'+a[1]+'</span><label><input type="checkbox" data-hide="'+a[0]+'"'+(hidden?' checked':'')+'> hide</label></div>'
          +'<input class="t" data-title="'+a[0]+'" value="'+esc(hidden?'':(f[a[0]]||''))+'" placeholder="'+esc(axisTitle(v,a[2])||'automatic')+'"'+(hidden?' disabled':'')+'></div>';
      });
      if(secs.indexOf('yrange')>=0)
        h+='<div class="row"><div class="lab">Y axis from / to</div><div class="two"><input class="t" id="fymin" placeholder="auto" value="'+(f.ymin!=null?esc(f.ymin):'')+'">'
          +'<input class="t" id="fymax" placeholder="auto" value="'+(f.ymax!=null?esc(f.ymax):'')+'"></div></div>';
      if(secs.indexOf('logx')>=0)h+='<label class="chk"><input type="checkbox" id="fxlog"'+(f.xlog?' checked':'')+'> Logarithmic X axis</label>';
      if(secs.indexOf('logy')>=0)h+='<label class="chk"><input type="checkbox" id="fylog"'+(f.ylog?' checked':'')+'> Logarithmic Y axis</label>';
    } else if(sec==='markers'){
      h+='<label class="chk" style="margin-top:2px"><input type="checkbox" id="fshapes"'+(f.shapes?' checked':'')+'> A different shape per colour</label>'
        +'<div class="row"><div class="lab">Point size</div><select id="fpsize">'+opts(Object.assign({auto:'Normal'},PSIZES),f.psize||'auto')+'</select></div>';
    } else if(sec==='legend'){
      h+='<div class="row"><div class="lab">Position</div><select id="fleg">'+opts(Object.assign({},LEGENDPOS,{auto:autoLab('legend',function(x){return LEGENDPOS[x]||x;},'Automatic')}),f.legend||'auto')+'</select></div>';
    } else if(sec==='colours'){
      var rc=(RESULTS[v.id]||{}).colours||{groups:[],single:null}, own=f.colours||{};
      if(v.type==='matrix'){
        h+='<div class="row"><div class="lab">Colour scale</div><select id="fscale">'+opts(MSCALES,f.scale||'RdYlGn')+'</select></div>'
          +'<div class="hint" style="margin-top:4px">With a target the colours show good and bad instead.</div>';
      } else {
        h+='<div class="row"><div class="lab">Palette</div><select id="fpal">'+opts(Object.assign({auto:autoLab('palette',function(x){return PALS[x]||x;},'Automatic')},PALS),f.palette||'auto')+'</select></div>';
        if(rc.groups&&rc.groups.length){
          h+='<div class="row"><div class="lab">Colour per value</div>'+rc.groups.map(function(g){
            return '<div class="crow"><button class="sw" data-cl="'+esc(g[0])+'" data-cur="'+esc(g[1])+'" style="background:'+esc(g[1])+'" title="Click to choose a colour"></button>'
              +'<span title="'+esc(g[0])+'">'+esc(g[0])+'</span>'+(own[g[0]]?'<b data-unc="'+esc(g[0])+'" title="Back to the palette colour">×</b>':'')+'</div>';}).join('')+'</div>';
        } else if(rc.single){
          h+='<div class="row"><div class="lab">Colour</div><div class="crow"><button class="sw" data-cl="" data-cur="'+esc(rc.single)+'" style="background:'+esc(rc.single)+'" title="Click to choose a colour"></button>'
            +'<span>'+(f.colour?'own colour':'from the palette')+'</span>'+(f.colour?'<b data-unc="" title="Back to the palette colour">×</b>':'')+'</div></div>';
        }
      }
    } else if(sec==='text'){
      h+='<div class="row"><div class="lab">Text size</div><select id="ffont">'+opts(Object.assign({auto:autoLab('font',function(x){return FONTS[x]||x;},'Normal')},FONTS),f.font||'auto')+'</select></div>';
      var gridOn=f.grid!=null?f.grid!==false:themeOf().grid!==false;
      if(v.type!=='table'&&v.type!=='matrix')h+='<label class="chk"><input type="checkbox" id="fgrid"'+(gridOn?' checked':'')+'> Grid lines</label>';
    } else if(sec==='card'){
      h+='<div class="row"><div class="lab">Size of the number</div><select id="fvsize">'+opts(Object.assign({auto:'Medium'},CARDSIZES),f.vsize||'auto')+'</select></div>'
        +'<label class="chk"><input type="checkbox" id="funit"'+(f.unit===false?'':' checked')+'> Show the unit</label>'
        +'<label class="chk"><input type="checkbox" id="fsub"'+(f.sub===false?'':' checked')+'> Show the line below (n, SD, trial …)</label>';
    } else if(sec==='table'){
      var cols=((v.wells||{}).columns||[]).filter(function(k){return FIELDS[k];}), ts=f.tsort;
      var name=function(k){return k==='trial'?'Trial':k==='series'?'Series':(FIELDS[k]?FIELDS[k].label:k);};
      h+='<div class="row"><div class="lab">Order</div>'+(ts?'<div class="crow"><span>'+esc(name(ts.key))+(ts.dir==='desc'?' (high to low)':' (low to high)')+'</span><b id="ftsclr" title="Back to the normal order">×</b></div>'
          :'<div class="hint">Click a column heading in the table to sort; click again to turn it round.</div>')+'</div>';
      h+='<div class="row"><div class="lab">Colour rules</div>';
      (f.rules||[]).forEach(function(r,i){
        h+='<div class="rule" data-i="'+i+'"><span class="rx" title="Remove this rule">×</span>'
          +'<select data-r="key">'+cols.map(function(k){return '<option value="'+esc(k)+'"'+(r.key===k?' selected':'')+'>'+esc(name(k))+'</option>';}).join('')+'</select>'
          +'<select data-r="op">'+opts(RULEOPS,r.op||'>')+'</select>'
          +'<div class="two"><input class="t" data-r="a" placeholder="value" value="'+esc(r.a==null?'':r.a)+'">'
          +(r.op==='between'?'<input class="t" data-r="b" placeholder="and" value="'+esc(r.b==null?'':r.b)+'">':'')+'</div>'
          +'<select data-r="colour">'+Object.keys(RULECOLS).map(function(c){return '<option value="'+c+'"'+(r.colour===c?' selected':'')
            +' style="background:'+RULECOLS[c]+'">'+c[0].toUpperCase()+c.slice(1)+'</option>';}).join('')+'</select></div>';
      });
      h+=cols.length?'<button class="fadd" id="fradd" style="margin-top:6px">+ Add colour rule</button>':'<div class="hint">Add columns in Build first.</div>';
      h+='</div>';
    }
    h+='</div></details>';
  });
  return h;
}
function bindFormat(el,v){
  el.querySelectorAll('details.fmt').forEach(function(d){var arr=d.querySelector('.arr');arr.textContent=d.open?'▾':'▸';
    d.addEventListener('toggle',function(){FMTSHUT[d.dataset.sec]=!d.open;arr.textContent=d.open?'▾':'▸';});});
  el.querySelectorAll('.rst').forEach(function(r){r.addEventListener('click',function(e){e.preventDefault();e.stopPropagation();
    FMT_KEYS[r.dataset.rst].forEach(function(k){if(v.fmt)delete v.fmt[k];});if(v.fmt&&!Object.keys(v.fmt).length)delete v.fmt;changed();});});
  var on=function(id,fn){var x=document.getElementById(id);if(x)x.addEventListener('change',function(){fn(x.value);});};
  on('fsort',function(x){fmtSet(v,'sort',x);});
  on('ftop',function(x){var n=parseInt(x);fmtSet(v,'top',n>0?n:null);});
  on('fdec',function(x){fmtSet(v,'decimals',x==='auto'?null:parseInt(x));});
  on('flab',function(x){fmtSet(v,'labels',x==='on'?true:x==='off'?false:null);});
  on('fleg',function(x){fmtSet(v,'legend',x);});
  on('ferr',function(x){fmtSet(v,'errbars',x==='auto'?null:x);});
  on('fymin',function(x){fmtSet(v,'ymin',fmtNum(x));});
  on('fymax',function(x){fmtSet(v,'ymax',fmtNum(x));});
  on('fpsize',function(x){fmtSet(v,'psize',x);});
  [['fxlog','xlog'],['fylog','ylog'],['fshapes','shapes']].forEach(function(p){var c=document.getElementById(p[0]);
    if(c)c.addEventListener('change',function(){fmtSet(v,p[1],c.checked?true:null);});});
  el.querySelectorAll('[data-title]').forEach(function(i){i.addEventListener('change',function(){var t=i.value.trim();fmtSet(v,i.dataset.title,t||null);});});
  el.querySelectorAll('[data-hide]').forEach(function(c){c.addEventListener('change',function(){fmtSet(v,c.dataset.hide,c.checked?'':null);});});
  on('fscale',function(x){fmtSet(v,'scale',x==='RdYlGn'?null:x);});
  on('fpal',function(x){fmtSet(v,'palette',x);});
  on('ffont',function(x){fmtSet(v,'font',x);});
  on('fvsize',function(x){fmtSet(v,'vsize',x);});
  [['funit','unit'],['fsub','sub']].forEach(function(p){var c=document.getElementById(p[0]);
    if(c)c.addEventListener('change',function(){fmtSet(v,p[1],c.checked?null:false);});});
  var gc=document.getElementById('fgrid');if(gc)gc.addEventListener('change',function(){     // own setting only where it differs from the theme
    var th=themeOf().grid!==false;fmtSet(v,'grid',gc.checked===th?null:gc.checked);});
  el.querySelectorAll('.sw').forEach(function(b){b.addEventListener('click',function(){if(bridge)bridge.pickColour(v.id,b.dataset.cl,b.dataset.cur);});});
  el.querySelectorAll('[data-unc]').forEach(function(b){b.addEventListener('click',function(){
    if(b.dataset.unc===''){fmtSet(v,'colour',null);return;}
    var c=Object.assign({},(v.fmt||{}).colours||{});delete c[b.dataset.unc];fmtSet(v,'colours',Object.keys(c).length?c:null);});});
  var tc=document.getElementById('ftsclr');if(tc)tc.addEventListener('click',function(){fmtSet(v,'tsort',null);});
  function readRules(){return [].map.call(el.querySelectorAll('.rule'),function(r){var o={};
    r.querySelectorAll('[data-r]').forEach(function(i){var val=i.value.trim();if(i.dataset.r==='a'||i.dataset.r==='b'){val=val.replace(',','.');}if(val!=='')o[i.dataset.r]=val;});return o;});}
  el.querySelectorAll('.rule [data-r]').forEach(function(i){i.addEventListener('change',function(){var rs=readRules();fmtSet(v,'rules',rs.length?rs:null);});});
  el.querySelectorAll('.rule .rx').forEach(function(x){x.addEventListener('click',function(){
    var rs=readRules();rs.splice(parseInt(x.parentNode.dataset.i),1);fmtSet(v,'rules',rs.length?rs:null);});});
  var ra=document.getElementById('fradd');if(ra)ra.addEventListener('click',function(){
    var cols=((v.wells||{}).columns||[]).filter(function(k){return FIELDS[k];}), num=cols.filter(function(k){return FIELDS[k].kind==='num';});
    fmtSet(v,'rules',(((v.fmt||{}).rules)||[]).concat([{key:num[0]||cols[0],op:'>',colour:'green'}]));});
}
function tableSort(v,key){
  var ts=(v.fmt||{}).tsort;
  fmtSet(v,'tsort',!ts||ts.key!==key?{key:key,dir:'asc'}:ts.dir==='asc'?{key:key,dir:'desc'}:null);
}
function vtabsHtml(v,secs){
  if(v&&!secs.length)return '';
  var f=v?v.fmt:SPEC.theme, dot=f&&Object.keys(f).length?' <i class="fdot"></i>':'';
  var an=v&&ANA.types.indexOf(v.type)>=0, adot=an&&(v.analytics||[]).length?' <i class="fdot"></i>':'';
  return '<div class="vtabs"><button data-vt="build"'+(VTAB==='build'?' class="on"':'')+' title="Type, fields and options">Build</button>'
    +'<button data-vt="format"'+(VTAB==='format'?' class="on"':'')+' title="'+(v?'Sort, numbers, labels, colours, axes, legend':'Dashboard theme: palette, text size, decimals … for all visuals')+'">Format'+dot+'</button>'
    +(an?'<button data-vt="analytics"'+(VTAB==='analytics'?' class="on"':'')+' title="Average, median, standard deviations, percentile, constant lines and bands (e.g. spec limits)">Analytics'+adot+'</button>':'')+'</div>';
}
function bindTabs(el){el.querySelectorAll('.vtabs button').forEach(function(b){b.addEventListener('click',function(){VTAB=b.dataset.vt;renderWells();});});}
function keepFocus(fn){var a=document.activeElement, id=a&&(a.id||(a.dataset&&a.dataset.title&&'t:'+a.dataset.title));fn();
  if(!id)return;var n=id.indexOf('t:')===0?document.querySelector('[data-title="'+id.slice(2)+'"]'):document.getElementById(id);if(n&&!n.disabled)n.focus();}
function renderWells(){keepFocus(renderWells_);}

// ── Analytics (like the Power BI Analytics pane): lines and bands on a chart ──
function analyticsHtml(v){
  var items=v.analytics||[], h='<div class="hint" style="margin-bottom:8px">Lines are calculated from the single trials in the chart'
    +(v.type==='column'?' - here from the plotted columns':'')+', per small multiple. Constant lines and bands are fixed values, e.g. spec limits.</div>';
  items.forEach(function(a,i){
    var k=a.kind, col=a.colour||ANA.defaults[k]||'blue', p='';
    if(k==='sd')p='<div class="lab" style="font-size:11px;color:#5A6460">How many</div><select data-f="n">'+opts({'1':'± 1 SD','2':'± 2 SD','3':'± 3 SD'},String(a.n||1))+'</select>';
    else if(k==='percentile')p='<input class="t" type="number" step="any" min="0" max="100" data-f="p" placeholder="Percentile, e.g. 90" value="'+(a.p!=null?esc(a.p):'90')+'">';
    else if(k==='constant')p='<input class="t" type="number" step="any" data-f="value" placeholder="Value" value="'+(a.value!=null?esc(a.value):'')+'">';
    else if(k==='band')p='<div class="two"><input class="t" type="number" step="any" data-f="lo" placeholder="From" value="'+(a.lo!=null?esc(a.lo):'')+'">'
      +'<input class="t" type="number" step="any" data-f="hi" placeholder="To" value="'+(a.hi!=null?esc(a.hi):'')+'"></div>';
    h+='<div class="rule an" data-i="'+i+'"><b class="rx" title="Remove this line">×</b>'
      +'<div style="font-weight:600;font-size:12px;color:'+(ANA.colours[col]||'#1C2321')+'">'+esc(ANA.kinds[k]||k)+'</div>'+p
      +'<div class="two"><input class="t" data-f="label" placeholder="Label (optional)" value="'+esc(a.label||'')+'">'
      +'<select data-f="colour" title="Colour">'+Object.keys(ANA.colours).map(function(c){return '<option value="'+c+'"'+(c===col?' selected':'')+'>'+c+'</option>';}).join('')+'</select></div></div>';
  });
  h+='<select id="anadd" style="margin-top:8px"><option value="">+ Add a line…</option>'+Object.keys(ANA.kinds).map(function(k){return '<option value="'+k+'">'+esc(ANA.kinds[k])+'</option>';}).join('')+'</select>';
  if(items.length)h+='<div class="hint" style="margin-top:8px;text-align:right"><a id="anclr" style="color:#1F7A3A;text-decoration:underline;cursor:pointer">Remove all</a></div>';
  return h;
}
function bindAnalytics(el,v){
  function read(){v.analytics=[].map.call(el.querySelectorAll('.an'),function(r){
    var a=JSON.parse(JSON.stringify((v.analytics||[])[parseInt(r.dataset.i)]||{}));
    r.querySelectorAll('[data-f]').forEach(function(f){var key=f.dataset.f, val=f.value;
      if(key==='label'||key==='colour'){if(val&&!(key==='colour'&&val===ANA.defaults[a.kind]))a[key]=val;else delete a[key];}
      else{var x=fmtNum(val);if(x===null||isNaN(x))delete a[key];else a[key]=x;}});
    return a;});
    if(!v.analytics.length)delete v.analytics;changed();}
  el.querySelectorAll('.an [data-f]').forEach(function(f){f.addEventListener('change',read);});
  el.querySelectorAll('.an .rx').forEach(function(b){b.addEventListener('click',function(){
    v.analytics.splice(parseInt(b.closest('.an').dataset.i),1);if(!v.analytics.length)delete v.analytics;changed();});});
  var ad=document.getElementById('anadd');if(ad)ad.addEventListener('change',function(){if(!ad.value)return;
    var a={kind:ad.value};if(a.kind==='percentile')a.p=90;if(a.kind==='sd')a.n=1;
    v.analytics=(v.analytics||[]).concat([a]);changed();});
  var cl=document.getElementById('anclr');if(cl)cl.addEventListener('click',function(){delete v.analytics;changed();});
}

// ── drill-through: right-click a bar, box, cell, slice … → a detail page ──
function goPage(id){
  if(!SPEC.pages.some(function(p){return p.id===id;}))return;
  closeDtMenu();SPEC.active=id;SEL=null;MSEL=[];RESULTS={};document.getElementById('grid').innerHTML='';renderAll();push();
}
function closeDtMenu(){var m=document.getElementById('dtmenu');if(m)m.remove();}
function dtMenu(ev,vid,pt,pages){
  closeDtMenu();var m=document.createElement('div');m.id='dtmenu';
  var val=[pt.x,pt.n].filter(function(x){return x!=null&&x!=='';}).map(String).join(' · ');
  m.innerHTML='<div class="mh">Drill through</div>'+(val?'<div class="mv">'+esc(val)+'</div>':'')
    +pages.map(function(p){return '<div class="mi" data-p="'+esc(p.id)+'">'+esc(p.title)+'</div>';}).join('');
  document.body.appendChild(m);
  var x=Math.min(ev.clientX,window.innerWidth-m.offsetWidth-6), y=Math.min(ev.clientY,window.innerHeight-m.offsetHeight-6);
  m.style.left=Math.max(4,x)+'px';m.style.top=Math.max(4,y)+'px';
  m.addEventListener('mousedown',function(e){e.stopPropagation();});
  m.querySelectorAll('.mi').forEach(function(i){i.addEventListener('click',function(){closeDtMenu();bridge.drillThrough(vid,JSON.stringify(pt),i.dataset.p);});});
}
document.addEventListener('mousedown',function(){closeDtMenu();});
document.addEventListener('keydown',function(e){if(e.key==='Escape')closeDtMenu();});
function renderDtBar(){
  var b=document.getElementById('dtbar'), t=FDATA.through;
  if(!t){b.className='';b.innerHTML='';return;}
  b.className='on';
  b.innerHTML=(t.from?'<button class="btn" id="dtback" title="Back to the page you came from">← Back to '+esc(t.fromTitle)+'</button>':'')
    +'<span class="dtt"><b>Drill-through</b>'+t.text.map(function(x){return '<i>'+esc(x)+'</i>';}).join('')+'</span>'
    +'<button class="btn" id="dtclr" title="Show this page without the drill-through filter">Clear</button>';
  var bk=document.getElementById('dtback');if(bk)bk.addEventListener('click',function(){bridge.drillBack(true);});
  document.getElementById('dtclr').addEventListener('click',function(){bridge.drillBack(false);});
}
function dtConfigHtml(){
  var pg=PG(), keys=(pg.drillthrough||[]).filter(function(k){return FIELDS[k];});
  var h='<div class="fsec"><div class="lab">Drill-through to this page</div>';
  if(RO){if(!keys.length)return '';
    return h+'<div class="hint">Right-click a value of '+keys.map(function(k){return '<b>'+esc(FIELDS[k].label)+'</b>';}).join(', ')+' on another page to come here.</div></div>';}
  h+='<div class="dtf">'+(keys.length?keys.map(function(k){return '<span class="chip"><span>'+esc(FIELDS[k].label)+'</span><b data-dk="'+esc(k)+'" title="Remove">×</b></span>';}).join(''):'<div class="none">none - this is a normal page</div>')+'</div>'
    +'<select id="dtadd"><option value="">+ Add a field…</option>'+CATALOG.filter(function(f){return keys.indexOf(f.key)<0;}).map(function(f){
      return '<option value="'+esc(f.key)+'">'+esc(f.label)+' ('+esc(f.group)+')</option>';}).join('')+'</select>';
  if(keys.length)h+='<label class="chk"><input type="checkbox" id="dtkeep"'+(pg.dt_keep===false?'':' checked')+'> Keep all filters of the clicked visual</label>';
  h+='<div class="hint" style="margin-top:6px">Makes this a detail page: a right-click on a bar, box, cell or slice of such a field on another page offers <b>Drill through</b> to here.</div></div>';
  return h;
}
function bindDtConfig(el){
  var pg=PG();
  el.querySelectorAll('[data-dk]').forEach(function(b){b.addEventListener('click',function(){
    pg.drillthrough=(pg.drillthrough||[]).filter(function(k){return k!==b.dataset.dk;});if(!pg.drillthrough.length){delete pg.drillthrough;delete pg.dt_keep;}push();renderFilterPane();});});
  var ad=document.getElementById('dtadd');if(ad)ad.addEventListener('change',function(){if(!ad.value)return;
    pg.drillthrough=(pg.drillthrough||[]).concat([ad.value]);push();renderFilterPane();});
  var kp=document.getElementById('dtkeep');if(kp)kp.addEventListener('change',function(){if(kp.checked)delete pg.dt_keep;else pg.dt_keep=false;push();});
}

// ── Etappe 3: dashboard theme (Format with nothing selected) and format painter ──
var THEME_KEYS=['palette','font','grid','decimals','labels','legend'];
function themeOf(){return SPEC.theme||{};}
function themeSet(key,val){SPEC.theme=SPEC.theme||{};
  if(val===null||val===undefined||val==='auto')delete SPEC.theme[key];else SPEC.theme[key]=val;
  if(!Object.keys(SPEC.theme).length)delete SPEC.theme;changed();}
function autoLab(key,text,def){var t=themeOf()[key];return t==null?def:'Dashboard: '+text(t);}
function themeHtml(){
  var t=themeOf(), set=Object.keys(t).length>0, sec=function(name,inner){
    return '<details class="fmt" open><summary><span class="arr">▾</span>'+esc(name)+'</summary><div class="in">'+inner+'</div></details>';};
  return '<div class="hint" style="margin-bottom:8px"><b>Dashboard theme</b> - for every visual on every page. '
      +'A visual\'s own Format wins. Click a visual to format only that one.'
      +(set?' <a class="rst" id="thrst" style="color:#1F7A3A;text-decoration:underline;cursor:pointer">Reset all</a>':'')+'</div>'
    +sec('Colours','<div class="row"><div class="lab">Palette</div><select id="thpal">'+opts(Object.assign({auto:'Standard (Heberlein)'},PALS),t.palette||'auto')+'</select></div>')
    +sec('Text and grid','<div class="row"><div class="lab">Text size</div><select id="thfont">'+opts(Object.assign({auto:'Normal'},FONTS),t.font||'auto')+'</select></div>'
      +'<label class="chk"><input type="checkbox" id="thgrid"'+(t.grid===false?'':' checked')+'> Grid lines</label>')
    +sec('Numbers','<div class="row"><div class="lab">Decimal places</div><select id="thdec">'
      +opts({auto:'Automatic',0:'0',1:'1',2:'2',3:'3',4:'4'},t.decimals==null?'auto':t.decimals)+'</select></div>'
      +'<div class="row"><div class="lab">Values on bars and lines</div><select id="thlab">'
      +opts({auto:'Automatic',on:'On',off:'Off'},t.labels===true?'on':t.labels===false?'off':'auto')+'</select></div>')
    +sec('Legend','<div class="row"><div class="lab">Position</div><select id="thleg">'+opts(LEGENDPOS,t.legend||'auto')+'</select></div>');
}
function bindTheme(el){
  var on=function(id,fn){var x=document.getElementById(id);if(x)x.addEventListener('change',function(){fn(x);});};
  on('thpal',function(x){themeSet('palette',x.value);});
  on('thfont',function(x){themeSet('font',x.value);});
  on('thgrid',function(x){themeSet('grid',x.checked?null:false);});
  on('thdec',function(x){themeSet('decimals',x.value==='auto'?null:parseInt(x.value));});
  on('thlab',function(x){themeSet('labels',x.value==='on'?true:x.value==='off'?false:null);});
  on('thleg',function(x){themeSet('legend',x.value);});
  var r=document.getElementById('thrst');if(r)r.addEventListener('click',function(){delete SPEC.theme;changed();});
}
// format painter: the keys of the sections both visuals have (not the axes - titles and ranges belong to the fields)
function paintKeys(type){var ks=[];(FORMATS[type]||[]).forEach(function(s){if(s!=='axes'&&s!=='yrange')ks=ks.concat(FMT_KEYS[s]||[]);});return ks;}
function copyFormat(){
  var src=vis(SEL), targets=MSEL.map(vis).filter(function(t){return t&&src&&t.id!==src.id;});
  if(!src||!targets.length){toast('Select two or more visuals - the last one you click gives its format');return;}
  var sk=paintKeys(src.type), sf=src.fmt||{}, n=0;
  targets.forEach(function(t){
    var tk=paintKeys(t.type).filter(function(k){return sk.indexOf(k)>=0;});
    if(!tk.length)return;
    var f=Object.assign({},t.fmt||{});
    tk.forEach(function(k){if(sf[k]!==undefined)f[k]=JSON.parse(JSON.stringify(sf[k]));else delete f[k];});
    if(Object.keys(f).length)t.fmt=f;else delete t.fmt;n++;
  });
  changed();
  toast(n?'Format copied to '+n+' visual'+(n>1?'s':''):'These visuals have nothing to format in common');
}

// ── model view (read only): the tables around the trial ─────────
var MODEL={nodes:[]}, MSELN='General', MFILL={}, NTRIALS=0;
function setView(view){
  document.body.classList.toggle('modelmode',view==='model');
  document.querySelectorAll('#views button').forEach(function(b){b.classList.toggle('on',b.dataset.view===view);});
  if(view==='model')renderModel();else setTimeout(relayout,30);
}
document.querySelectorAll('#views button').forEach(function(b){b.addEventListener('click',function(){setView(b.dataset.view);});});
function renderModel(){
  var cv=document.getElementById('mcanvas'), W=cv.clientWidth, H=cv.clientHeight;
  if(!W||!H)return;
  var centre=MODEL.nodes.filter(function(n){return n.kind==='centre';})[0], rest=MODEL.nodes.filter(function(n){return n.kind!=='centre';});
  // trial in the middle, the tables it refers to on the left, the lab tables in one or two columns on the right
  var clampX=function(x){return Math.max(96,Math.min(W-96,x));}, pos={};
  var dims=rest.filter(function(n){return n.kind!=='lab';}), labs=rest.filter(function(n){return n.kind==='lab';});
  var cx=clampX(W*0.40), cy=H/2;
  if(centre)pos[centre.id]=[cx,cy];
  dims.forEach(function(n,i){pos[n.id]=[clampX(W*0.12),H*(i+1)/(dims.length+1)];});
  // second lab column half a row lower, so its links run through the gaps of the first column
  var cols=labs.length>7?2:1, rows=Math.ceil(labs.length/cols), colX=cols===2?[W*0.66,W*0.88]:[W*0.78], step=H/(rows+(cols===2?1.5:1));
  labs.forEach(function(n,i){var c=Math.floor(i/rows), r=i%rows;pos[n.id]=[clampX(colX[c]),step*(r+1+0.5*c)];});
  var HALF=84, CHALF=95, trunkL=(clampX(W*0.12)+HALF+cx-CHALF)/2, trunkR=labs.length?(cx+CHALF+clampX(colX[0])-HALF)/2:cx;
  var links='', pills='';
  rest.slice().sort(function(a,b){return (a.id===MSELN)-(b.id===MSELN);}).forEach(function(n){
    var p=pos[n.id], right=p[0]>cx, sel=n.id===MSELN;
    var col=n.kind==='lab'?'#8CC63F':n.kind==='calc'?'#8C6BB1':'#232E3A';
    var x0=right?cx+CHALF:cx-CHALF, tx=right?trunkR:trunkL, x1=right?p[0]-HALF:p[0]+HALF;
    links+='<path d="M'+x0+' '+cy+'H'+tx+'V'+p[1]+'H'+x1+'" fill="none" stroke="'+col+'" stroke-width="'+(sel?2.6:1.3)+'" stroke-opacity="'+(sel?1:.6)+'"/>';
    if(n.relation){var px=right?x1-25:x1+25;
      pills+='<g><rect x="'+(px-21)+'" y="'+(p[1]-9)+'" width="42" height="18" rx="9" fill="#fff" stroke="'+col+'" stroke-width="'+(sel?1.6:1)+'"/>'
        +'<text x="'+px+'" y="'+(p[1]+4)+'" text-anchor="middle" font-size="10.5" font-weight="700" fill="#232E3A" font-family="Segoe UI,sans-serif">'+esc(n.relation)+'</text></g>';}});
  var svg='<svg>'+links+pills+'</svg>';
  var h=svg;
  MODEL.nodes.forEach(function(n){var p=pos[n.id];
    h+='<div class="mnode '+n.kind+(n.id===MSELN?' on':'')+'" data-n="'+esc(n.id)+'" style="left:'+p[0]+'px;top:'+p[1]+'px" title="Click for its fields">'
      +'<b>'+esc(n.title)+'</b><span>'+n.fields.length+' field'+(n.fields.length===1?'':'s')+(n.tables.length?' · '+esc(n.tables.join(', ')):'')+'</span></div>';});
  cv.innerHTML=h;
  cv.querySelectorAll('.mnode').forEach(function(el){el.addEventListener('click',function(){MSELN=el.dataset.n;renderModel();});});
  renderModelDetail();
}
function renderModelDetail(){
  var n=MODEL.nodes.filter(function(x){return x.id===MSELN;})[0]||MODEL.nodes[0], el=document.getElementById('mdetail');
  if(!n){el.innerHTML='';return;}
  var fill=MFILL[n.id];
  if(!fill&&bridge&&!MFILL['?'+n.id]){MFILL['?'+n.id]=1;bridge.modelFields(n.id);}
  var h='<h4>'+esc(n.title)+'</h4>'+(n.relation?'<span class="rel" title="Trials : rows of this table">'+esc(n.relation)+'</span>':'<div style="height:6px"></div>')
    +'<div class="how">'+esc(n.how)+'</div>'+(n.tables.length?'<div class="tbls">Tables: '+esc(n.tables.join(', '))+'</div>':'');
  n.fields.forEach(function(f){var c=fill?fill[f.key]:null, pct=c!=null&&NTRIALS?Math.round(100*c/NTRIALS):null;
    h+='<div class="mf"><span class="k '+f.kind+'" style="font-size:10px;color:#fff;background:'+(f.kind==='num'?'#2F6DB5':'#C98A00')+';border-radius:3px;padding:0 3px;min-width:18px;text-align:center">'
      +(f.kind==='num'?'#':'Aa')+'</span><span class="nm" title="'+esc(f.label)+'">'+esc(f.label)+'</span>'
      +(pct==null?'<span class="fl">…</span>':'<span class="bar" title="'+c+' of '+NTRIALS+' trials have a value"><i style="width:'+pct+'%"></i></span><span class="fl">'+pct+' %</span>')+'</div>';});
  h+='<div class="key"><b>1 : 1</b> one value per trial · <b>1 : n</b> several rows per trial, averaged · <b>n : 1</b> many trials share one row. '
    +'The bar shows how many trials have a value.</div>'
    +'<div class="lock">Read only - the links between the tables are fixed in TrippleT and cannot be changed here.</div>';
  el.innerHTML=h;
}
function modelFields(group,counts,n){MFILL[group]=counts;NTRIALS=n;if(document.body.classList.contains('modelmode'))renderModelDetail();}
window.addEventListener('resize',function(){if(document.body.classList.contains('modelmode')){clearTimeout(window._mr);window._mr=setTimeout(renderModel,120);}});

// ── format painter (Power BI style): select a visual, click Copy format, click the target ──
var PAINT=null;   // {src: visual id, sticky: double-clicked = keep copying until Esc}
function painterState(){
  var b=document.getElementById('painter'), v=SEL&&vis(SEL);
  b.disabled=!PAINT&&!(v&&(FORMATS[v.type]||[]).length);
  b.classList.toggle('on',!!PAINT);b.classList.toggle('sticky',!!(PAINT&&PAINT.sticky));
  document.body.classList.toggle('painting',!!PAINT);
  document.querySelectorAll('.card').forEach(function(c){c.classList.toggle('psrc',!!PAINT&&c.dataset.id===PAINT.src);});
}
function startPaint(sticky){
  var v=SEL&&vis(SEL);if(!v)return;
  PAINT={src:v.id,sticky:!!sticky};painterState();
  toast(sticky?'Click the visuals that should get this format - Esc when done':'Click the visual that should get this format - Esc to cancel');
}
function endPaint(){if(!PAINT)return;PAINT=null;painterState();}
function paintFormat(srcId,ids){
  var src=vis(srcId), sk=src?paintKeys(src.type):[], sf=(src&&src.fmt)||{}, n=0;
  ids.map(vis).filter(function(t){return t&&src&&t.id!==src.id;}).forEach(function(t){
    var tk=paintKeys(t.type).filter(function(k){return sk.indexOf(k)>=0;});
    if(!tk.length)return;
    var f=Object.assign({},t.fmt||{});
    tk.forEach(function(k){if(sf[k]!==undefined)f[k]=JSON.parse(JSON.stringify(sf[k]));else delete f[k];});
    if(Object.keys(f).length)t.fmt=f;else delete t.fmt;n++;});
  return n;
}
(function(){
  var b=document.getElementById('painter'), clicks=0, t=null;
  // one click = copy once, double-click = keep copying (like Power BI); a second click ends it
  b.addEventListener('click',function(){
    if(PAINT&&!t){endPaint();return;}
    clicks++;clearTimeout(t);
    t=setTimeout(function(){var sticky=clicks>1;clicks=0;t=null;if(PAINT)endPaint();startPaint(sticky);},230);
  });
})();
function paintOn(id){           // a click on a card while painting
  if(!PAINT||id===PAINT.src)return false;
  var n=paintFormat(PAINT.src,[id]);
  toast(n?'Format copied':'This visual has nothing to format in common with the first one');
  if(!PAINT.sticky)endPaint();
  changed();
  return true;
}

// ── focus mode: one visual big, its trials below ──────────────
var FOCUS=null;
function openFocus(id){
  var v=vis(id), r=RESULTS[id];if(!v||!r)return;
  FOCUS=id;endPaint();
  var el=document.getElementById('focus');el.classList.add('on');
  el.innerHTML='<div class="fh"><b></b><button class="btn" id="fclose" title="Back to the page (Esc)">Back to the page</button></div>'
    +'<div class="fbox fplot"></div><div class="fbox flist"><div class="hint">Loading the trials …</div></div>';
  el.querySelector('#fclose').addEventListener('click',closeFocus);
  renderFocus();
  if(bridge)bridge.focusRows(id);
}
function closeFocus(){
  if(!FOCUS)return;
  var p=document.querySelector('#focus .plot');if(p&&typeof Plotly!=='undefined')Plotly.purge(p);
  FOCUS=null;document.getElementById('focus').classList.remove('on');document.getElementById('focus').innerHTML='';
}
function renderFocus(){
  var v=vis(FOCUS), r=RESULTS[FOCUS], el=document.getElementById('focus');
  if(!v||!r){closeFocus();return;}
  el.querySelector('.fh b').textContent=(v.title_set&&v.title)||r.title||TYPES[v.type].label;
  var box=el.querySelector('.fplot');
  if(r.kind==='plotly'&&typeof Plotly!=='undefined'){
    var p=box.querySelector('.plot');
    if(!p){box.innerHTML='<div class="plot"></div>'+(r.note?'<div class="fnote"></div>':'');p=box.querySelector('.plot');}
    var n=box.querySelector('.fnote');if(n)n.textContent=r.note||'';
    var lay=Object.assign({},r.figure.layout,{autosize:true});
    Plotly.react(p,r.figure.data,lay,{responsive:true,displaylogo:false,displayModeBar:false});
    if(!p._fb){p._fb=1;p.on('plotly_click',function(e){var pt=e.points&&e.points[0];if(pt&&pt.customdata!=null)focusHit(pt.customdata,true);});}
  } else {
    var card=document.querySelector('[data-id="'+FOCUS+'"] .body');box.innerHTML=card?card.innerHTML:'';
  }
}
function focusRows(id,data){
  if(id!==FOCUS)return;
  var box=document.querySelector('#focus .flist');if(!box)return;
  var h='<div class="tbl"><table><tr>'+data.head.map(function(x){return '<th>'+esc(x)+'</th>';}).join('')+'</tr>';
  data.rows.forEach(function(row){h+='<tr data-t="'+row[0]+'">'+row.slice(1).map(function(x){return '<td>'+esc(x)+'</td>';}).join('')+'</tr>';});
  h+='</table></div><div class="fnote">'+data.rows.length+' trial'+(data.rows.length===1?'':'s')
    +(data.more?' (and '+data.more+' more)':'')+' - click a line to find it in the chart, double-click to open it in Show Experiment</div>';
  box.innerHTML=data.rows.length?h:'<div class="hint">No trials in this visual.</div>';
  box.querySelectorAll('tr[data-t]').forEach(function(tr){
    tr.addEventListener('click',function(){focusHit(parseInt(tr.dataset.t),false);});
    tr.addEventListener('dblclick',function(){if(bridge)bridge.openTrial(parseInt(tr.dataset.t));});});
}
function focusHit(tid,fromChart){
  var box=document.querySelector('#focus .flist');if(!box)return;
  box.querySelectorAll('tr.hit').forEach(function(x){x.classList.remove('hit');});
  var tr=box.querySelector('tr[data-t="'+tid+'"]');
  if(tr){tr.classList.add('hit');if(fromChart)tr.scrollIntoView({block:'center'});}
  var p=document.querySelector('#focus .plot');
  if(p&&p.data&&typeof Plotly!=='undefined'){        // light up the point(s) of this trial
    var sel=p.data.map(function(t){var cd=t.customdata;if(!cd)return null;
      var ix=[];cd.forEach(function(c,i){if(c===tid)ix.push(i);});return ix;});
    if(sel.some(function(s){return s&&s.length;}))Plotly.restyle(p,{selectedpoints:sel});
  }
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
function renderWells_(){
  document.querySelectorAll('.vt').forEach(function(b){b.classList.toggle('on',!!SEL&&vis(SEL)&&vis(SEL).type===b.dataset.t);});
  var el=document.getElementById('wells'), v=SEL&&vis(SEL);
  if(!v){
    if(VTAB==='format'&&!RO){el.innerHTML=vtabsHtml(null,[])+themeHtml();bindTabs(el);bindTheme(el);return;}
    el.innerHTML=(RO?'':vtabsHtml(null,[]))+'<div class="hint">Click a visual on the page to change it - or click a type above to add a new one.<br><br>Then drag fields from <b>Fields</b> into its wells.'
      +'<br><br><b>Format</b> without a visual selected sets a theme for the whole dashboard.</div>';bindTabs(el);return;}
  var secs=FORMATS[v.type]||[];if(VTAB==='format'&&!secs.length)VTAB='build';
  if(VTAB==='analytics'&&ANA.types.indexOf(v.type)<0)VTAB='build';
  if(VTAB==='analytics'){el.innerHTML=vtabsHtml(v,secs)+analyticsHtml(v);bindTabs(el);bindAnalytics(el,v);return;}
  if(VTAB==='format'){
    var own=v.fmt&&Object.keys(v.fmt).length;
    el.innerHTML=vtabsHtml(v,secs)+(own?'<div class="hint" style="margin:-4px 0 8px;text-align:right"><a id="frstall" style="color:#1F7A3A;text-decoration:underline;cursor:pointer" title="All sections back to the standard (or the dashboard theme)">Reset all</a></div>':'')
      +formatHtml(v,secs);bindTabs(el);bindFormat(el,v);
    var ra=document.getElementById('frstall');if(ra)ra.addEventListener('click',function(){delete v.fmt;changed();});
    return;}
  var t=TYPES[v.type], h=vtabsHtml(v,secs)+'<div class="hint" style="margin-bottom:8px"><b>'+esc(t.label)+'</b> - '+esc(t.tip)+'</div>';
  t.wells.forEach(function(wl){
    var multi=MULTIW.indexOf(wl)>=0;
    var keys=multi?((v.wells||{})[wl]||[]):((v.wells||{})[wl]?[(v.wells||{})[wl]]:[]);
    h+='<div class="well"><div class="lab">'+esc(WELLS[wl][0])+(WELLS[wl][1]==='num'?' · number':'')+'</div><div class="drop" data-w="'+wl+'">';
    if(!keys.length)h+='drop a field here';
    keys.forEach(function(k){if(FIELDS[k])h+='<div class="chip"><span title="'+esc(FIELDS[k].label)+'">'+esc(FIELDS[k].label)+'</span><b data-w="'+wl+'" data-k="'+esc(k)+'">×</b></div>';});
    h+='</div></div>';
  });
  if(t.agg){
    h+='<div class="well"><div class="lab">Aggregation</div><select id="agg">';
    Object.keys(AGGS).forEach(function(a){if(t.nocount&&a.indexOf('count')===0)return;h+='<option value="'+a+'"'+((v.agg||t.defagg||'avg')===a?' selected':'')+'>'+esc(AGGS[a])+'</option>';});
    h+='</select></div>';
  }
  if(v.type==='column'||v.type==='stack'){
    var defst=v.type==='stack'?'percent':'stacked';
    h+='<div class="well"><div class="lab">Bars</div><select id="vstack">';
    Object.keys(STACKS).forEach(function(k){h+='<option value="'+k+'"'+((v.stack||defst)===k?' selected':'')+'>'+esc(STACKS[k])+'</option>';});
    h+='</select></div>';
  }
  if(v.type==='pie'){
    h+='<div class="well"><div class="lab">Shape</div><select id="vshape">'+opts(PIESHAPES,v.shape||'pie')+'</select></div>';
  }
  if(v.type==='text'){
    h+='<div class="well"><div class="lab">Text</div><textarea id="vtext" rows="7" placeholder="# A heading&#10;A line of text - **bold** works too">'+esc(v.text||'')+'</textarea>'
      +'<div class="hint" style="margin-top:4px">A line starting with # is a heading, **text** is bold.</div></div>';
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
    var fk=(v.wells||{}).field, isNum=fk&&FIELDS[fk]&&FIELDS[fk].kind==='num', isTime=!!(fk&&MONTHOF[fk]),
        cur=v.style||(isNum?'between':(isTime?'hierarchy':'list'));
    h+='<div class="well"><div class="lab">Style</div><select id="slstyle">';
    Object.keys(SLSTYLES).forEach(function(k){if(k==='between'&&!isNum)return;if(k==='hierarchy'&&!isTime)return;h+='<option value="'+k+'"'+(cur===k?' selected':'')+'>'+esc(SLSTYLES[k])+'</option>';});
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
    if(MULTIW.indexOf(b.dataset.w)>=0)v.wells[b.dataset.w]=v.wells[b.dataset.w].filter(function(k){return k!==b.dataset.k;});
    else delete v.wells[b.dataset.w];
    if(b.dataset.w==='drill'||b.dataset.w==='x')v.drillpath=[];
    changed();});});
  var ag=document.getElementById('agg');if(ag)ag.addEventListener('change',function(){v.agg=ag.value;changed();});
  var vs=document.getElementById('vstack');if(vs)vs.addEventListener('change',function(){v.stack=vs.value;changed();});
  var vsh=document.getElementById('vshape');if(vsh)vsh.addEventListener('change',function(){v.shape=vsh.value==='pie'?undefined:vsh.value;changed();});
  var vtx=document.getElementById('vtext');if(vtx)vtx.addEventListener('input',function(){v.text=vtx.value;
    clearTimeout(vtx._t);vtx._t=setTimeout(function(){var c=document.querySelector('[data-id="'+v.id+'"]');if(c)fillTextCard(c,v);push();},250);});
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
  bindTabs(el);
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
function clearSel(){if(!SEL&&!MSEL.length)return;SEL=null;MSEL=[];markSel();renderWells();}
// click on the empty page = nothing selected; a type in Visualizations then adds a new visual
document.getElementById('canvas').addEventListener('mousedown',function(e){
  var t=e.target;if(t.closest('.card,#tabs,#cross,#alignbar,button,input'))return;
  if(e.offsetX>=t.clientWidth||e.offsetY>=t.clientHeight)return;      // scrollbar
  if(PAINT){endPaint();return;}
  clearSel();});

function colW(){var g=document.getElementById('grid');return (g.clientWidth+GAP)/GRID.cols;}
function place(c,v){var cw=colW();c.style.left=(v.x*cw)+'px';c.style.top=(v.y*GRID.row)+'px';
  c.style.width=Math.max(40,v.w*cw-GAP)+'px';c.style.height=Math.max(40,v.h*GRID.row-GAP)+'px';}
function gridHeight(){document.getElementById('grid').style.height=(bottom()*GRID.row+40)+'px';}
function resizePlot(c){var p=c&&c.querySelector('.plot');if(p&&p.data&&typeof Plotly!=='undefined')Plotly.Plots.resize(p);}
function startMove(e,c,v,mode){
  if(e.button!==0||RO||PAINT)return;
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
        +'<button class="ib fo" data-a="f" title="Focus: this visual big, with its trials below (Esc goes back)">⤢</button>'
        +'<button class="ib" data-a="e" title="Export the data of this visual to Excel">⤓</button>'
        +'<button class="ib" data-a="d" title="Duplicate">⧉</button><button class="ib" data-a="x" title="Remove">✕</button></div>'
        +'<div class="body"></div><div class="rs" title="Drag to resize"></div>';
      c.addEventListener('mousedown',function(e){if(e.target.closest('.ib')||e.target.closest('.ix'))return;
        var id=c.dataset.id;
        if(PAINT){e.preventDefault();e.stopPropagation();if(!paintOn(id)&&id===PAINT.src)toast('Now click the visual that should get this format');return;}
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
  h+=dtConfigHtml();
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
  bindDtConfig(el);
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
  if(typeof painterState==='function')painterState();
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
  if(a==='f'){openFocus(id);return;}
  if(a==='x'){vs.splice(i,1);if(SEL===id)SEL=null;}
  else if(a==='d'){var c=JSON.parse(JSON.stringify(v));c.id=nextId();c.y=bottom();c.x=0;vs.push(c);SEL=c.id;}
  changed();
}
var FAIR={green:'#1F7A3A',amber:'#C98A00',red:'#C62828'};
function fillCard(c,v){
  var r=RESULTS[v.id], body=c.querySelector('.body'), dot=c.querySelector('.dot');
  c.querySelector('.title').textContent=v.type==='text'?((v.title_set&&v.title)||''):((v.title_set&&v.title)||(r&&r.title)||TYPES[v.type].label);
  c.classList.toggle('textcard',v.type==='text');
  var cr=c.querySelector('.crumb');
  if(r&&r.drill){cr.innerHTML=(r.drill.depth?'<b data-up="1" title="One level up">⤴</b>':'')+esc(r.drill.path.concat([r.drill.levels[r.drill.depth]]).join(' › '))
      +(r.drill.can_down?' <span style="color:#9AA59C">(double-click a bar)</span>':'');
    cr.title='Drill-down: '+r.drill.levels.join(' › ');
    var up=cr.querySelector('[data-up]');if(up)up.onclick=function(e){e.stopPropagation();(v.drillpath||[]).pop();changed();};}
  else cr.innerHTML='';
  var nf=(v.filters||[]).length, fm=c.querySelector('.fmark');
  fm.textContent=nf?('filter '+nf):'';fm.style.display=nf?'':'none';
  fm.title=nf&&r&&r.vfilters?('Filters on this visual: '+r.vfilters.join(' · ')):'';
  if(r&&r.fair){dot.style.background=FAIR[r.fair.level];dot.title=r.fair.headline+' ('+r.fair.grouping+'): '+r.fair.text+' - click for details';
    dot.style.visibility='visible';dot.classList.add('fair');
    if(!dot._b){dot._b=1;dot.addEventListener('mousedown',function(e){e.stopPropagation();});
      dot.addEventListener('click',function(e){e.stopPropagation();if(bridge)bridge.fairDetails(c.dataset.id);});}}
  else dot.style.visibility='hidden';
  if(!r){body.innerHTML='<div class="empty">Calculating…</div>';return;}
  if(r.kind==='plotly'){
    if(body.querySelector('.plot')===null)body.innerHTML='';
    var p=body.querySelector('.plot');
    if(!p){body.innerHTML='<div class="plot"></div>'+(r.note?'<div class="note"></div>':'');p=body.querySelector('.plot');}
    var n=body.querySelector('.note');if(r.note){if(!n){n=document.createElement('div');n.className='note';body.appendChild(n);}n.textContent=r.note;}else if(n)n.remove();
    if(typeof Plotly==='undefined'){body.innerHTML='<div class="empty">The chart library could not be loaded.</div>';return;}
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
        bridge.visualClick(v.id,JSON.stringify({x:pt.x!==undefined?pt.x:pt.label,y:pt.y,n:(pt.data&&pt.data.name)||''}));});
      p.on('plotly_hover',function(e){var pt=e.points&&e.points[0];
        p._hov=pt?{x:pt.x!==undefined?pt.x:pt.label,y:pt.y,n:(pt.data&&pt.data.name)||''}:null;});
      p.on('plotly_unhover',function(){p._hov=null;});
      p.addEventListener('contextmenu',function(e){
        var rr=RESULTS[v.id];if(!rr||!rr.through||!rr.through.length)return;
        e.preventDefault();e.stopPropagation();
        if(!p._hov){toast('Right-click on a bar, box, cell or slice to drill through');return;}
        dtMenu(e,v.id,p._hov,rr.through);});
      p.on('plotly_selected',function(e){
        var ids=[];((e&&e.points)||[]).forEach(function(q){if(q.customdata!=null)ids.push(q.customdata);});
        bridge.visualSelect(v.id,JSON.stringify(ids));});
      p.on('plotly_deselect',function(){bridge.visualSelect(v.id,'[]');});
    }
  } else if(r.kind==='text'){
    fillTextCard(c,v,r);
  } else if(r.kind==='slicer'){
    renderSlicer(body,v,r);
  } else if(r.kind==='kpi'){
    body.innerHTML='<div class="kpi"><div><span class="v'+(r.status?' '+r.status:'')+'"'+(r.vsize?' style="font-size:'+r.vsize+'px"':'')+'>'+esc(r.value)+'</span><span class="u">'+esc(r.unit||'')+'</span></div><div class="s">'+esc(r.sub||'')+'</div></div>';
  } else if(r.kind==='table'){
    var ks=r.keys||[], ts=r.tsort||{}, bg=r.cellbg||[];
    var h='<div class="tbl"'+(r.font?' style="font-size:'+r.font+'px"':'')+'><table'+(r.font?' style="font-size:inherit"':'')+'><tr>'+r.head.map(function(x,i){
      var k=ks[i], arrow=k&&ts.key===k?(ts.dir==='desc'?' ▼':' ▲'):'';
      return '<th'+(k?' class="srt" data-k="'+esc(k)+'" title="Click to sort"':'')+'>'+esc(x)+arrow+'</th>';}).join('')+'</tr>';
    r.rows.forEach(function(row,j){var b=bg[j]||[];h+='<tr data-t="'+row[0]+'">'+row.slice(1).map(function(x,i){
      return '<td'+(b[i]?' style="background:'+b[i]+'"':'')+'>'+esc(x)+'</td>';}).join('')+'</tr>';});
    h+='</table></div>'+(r.more?'<div class="note">'+r.more+' more trials not listed</div>':'')+'<div class="note">double-click a line to open it in Show Experiment</div>';
    body.innerHTML=h;
    body.querySelectorAll('tr[data-t]').forEach(function(tr){tr.addEventListener('dblclick',function(){bridge.openTrial(parseInt(tr.dataset.t));});});
    body.querySelectorAll('th.srt').forEach(function(th){th.addEventListener('mousedown',function(e){e.stopPropagation();});
      th.addEventListener('click',function(){var vv=vis(v.id);if(vv)tableSort(vv,th.dataset.k);});});
  } else {
    body.innerHTML='<div class="empty">'+esc(r.message||'')+'</div>';
  }
}
// ── text visual: "# " = heading, **bold** ─────────────────────
function textHtml(t){
  var lines=String(t||'').split('\n'), h='';
  lines.forEach(function(line){
    var x=esc(line).replace(/\*\*(.+?)\*\*/g,'<b>$1</b>');
    if(/^#\s+/.test(line))h+='<div class="th">'+x.replace(/^#\s+/,'')+'</div>';
    else h+='<div class="tl">'+(x||'&nbsp;')+'</div>';});
  return h;
}
function fillTextCard(c,v,r){
  r=r||RESULTS[v.id]||{};
  var body=c.querySelector('.body'), t=v.text||'';
  body.innerHTML=t?'<div class="txt"'+(r.font?' style="font-size:'+r.font+'px"':'')+'>'+textHtml(t)+'</div>'
    :'<div class="empty">Click the visual and write your text in Build</div>';
  // a text box has no title bar to grab - it moves by its text
  body.onmousedown=function(e){if(!RO&&!e.target.closest('.rs'))startMove(e,c,vis(c.dataset.id),'move');};
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
  } else if(st==='hierarchy'){
    var tree=r.tree||[];
    if(!tree.length&&!r.none){body.innerHTML='<div class="empty">No dates</div>';return;}
    h+='<div class="acts"><a data-act="all" title="No selection = everything">All</a>'+(cur.length?'<a data-act="clr">Clear ('+cur.length+')</a>':'')+'</div><div class="opts">';
    tree.forEach(function(t,ti){
      var labs=t.months.map(function(m){return m.label;}), nOn=labs.filter(function(l){return cur.indexOf(l)>=0;}).length;
      var key=v.id+':'+t.year, open=YOPEN[key]!=null?YOPEN[key]:(ti===0||nOn>0);
      h+='<div class="yr'+(nOn===12?' on':'')+'" data-y="'+esc(t.year)+'"><span class="car">'+(open?'▾':'▸')+'</span>'
        +'<span class="box'+(nOn&&nOn<12?' part':'')+'">'+(nOn===12?'✓':'')+'</span><span class="l">'+esc(t.year)+'</span><span class="n">'+t.n+'</span></div>';
      if(open)t.months.forEach(function(m){var on=cur.indexOf(m.label)>=0;
        h+='<div class="mo'+(on?' on':'')+(m.n?'':' zero')+'" data-l="'+esc(m.label)+'"><span class="box">'+(on?'✓':'')+'</span>'
          +'<span class="l">'+esc(m.name)+'</span><span class="n">'+m.n+'</span></div>';});
    });
    if(r.none){var onN=cur.indexOf('(none)')>=0;
      h+='<div class="mo'+(onN?' on':'')+'" data-l="(none)" style="padding-left:4px"><span class="box">'+(onN?'✓':'')+'</span><span class="l">(no date)</span><span class="n">'+r.none+'</span></div>';}
    h+='</div>';
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
  } else if(st==='hierarchy'){
    el.querySelectorAll('.yr').forEach(function(y){y.addEventListener('click',function(e){
      var key=v.id+':'+y.dataset.y, t=(r.tree||[]).filter(function(x){return x.year===y.dataset.y;})[0];
      if(e.target.classList.contains('car')){
        var wasOpen=y.querySelector('.car').textContent==='▾';YOPEN[key]=!wasOpen;renderSlicer(body,v,r);return;}
      var labs=t.months.map(function(m){return m.label;}), cur2=selVals(v);
      var all=labs.every(function(l){return cur2.indexOf(l)>=0;});
      if(!r.multi)cur2=all?[]:labs.slice();
      else if(all)cur2=cur2.filter(function(l){return labs.indexOf(l)<0;});
      else labs.forEach(function(l){if(cur2.indexOf(l)<0)cur2.push(l);});
      YOPEN[key]=true;v.sel=cur2.length?{values:cur2}:{};push();});});
    el.querySelectorAll('.mo').forEach(function(m){m.addEventListener('click',function(){toggleVal(v,m.dataset.l,r.multi);
      m.classList.toggle('on');m.querySelector('.box').textContent=m.classList.contains('on')?'✓':'';});});
    el.querySelectorAll('.acts a').forEach(function(a){a.addEventListener('click',function(){v.sel={};push();});});
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
  FDATA={all:data.allFilters||[],page:data.pageFilters||[],cross:data.cross||[],slicers:data.slicers||[],ply:data.plyScope||'any',through:data.through||null};
  renderFilterPane();renderDtBar();
  var x=document.getElementById('cross');
  x.innerHTML=data.cross.map(function(c){return '<span class="xchip" data-s="'+esc(c.source)+'" title="Clicked in '+esc(c.from)+' - click to remove">'+esc(c.text)+'  ×</span>';}).join('');
  x.querySelectorAll('.xchip').forEach(function(ch){ch.addEventListener('click',function(){bridge.clearCross(ch.dataset.s);});});
  document.querySelectorAll('.card').forEach(function(c){var v=vis(c.dataset.id);if(v)fillCard(c,v);});
  if(SEL)renderWells();
  if(FOCUS){if(RESULTS[FOCUS]){renderFocus();if(bridge)bridge.focusRows(FOCUS);}else closeFocus();}
}
function snapshotAll(){ /* for a later PDF step */ }
</script></body></html>"""
