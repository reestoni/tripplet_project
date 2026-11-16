# ui/widgets/help_texts_manage_yarn.py
"""Hilfetexte Manage Yarn (EN/DE/ES/ZH) fuer ui/widgets/multilang_help.py.

Spiegelt ui/screen_manage_yarn.py (Namensfilter, Spaltenfilter per Rechtsklick
auf den Kopf - FilterableHeaderView aus screen_manage_jets, Spalten
verschiebbar + Columns…-Dialog, UsedInTrial-Aufklappen, Formular New/Edit
Yarn mit Duplicate-Check, Rechte: Loeschen can_use_admin_box(), MinStock
app_meta.can_edit_min_stock()). Bei Aenderungen dort hier (alle 4 Sprachen)
und in assets/images/help_manage_yarn.svg nachziehen.
"""

SVG = "assets/images/help_manage_yarn.svg"
SVG_W, SVG_H = 940, 240


def B(name: str) -> str:
    return f"<b>[{name}]</b>"


TEXTS = {
    "en": {
        "window_title": "How does Manage Yarn work?",
        "close": "Close",
        "tabs": [
            {"key": "tasks", "title": "How do I…?", "blocks": [
                ("p", "Manage Yarn is the yarn catalogue: every yarn that can be used in trials. Numbers (1)–(3) refer "
                      "to the <i>Screen guide</i> tab."),
                ("h", "Finding"),
                ("task", "Find a yarn by name",
                 ["Type part of the name into <i>Filter by Name…</i> (1). Matches are highlighted."]),
                ("task", "Filter by a column (e.g. titer or material)",
                 ["Right-click the column header (2).",
                  "Enter text (<i>contains…</i>) or, for numbers, a range from/to.",
                  "A green ▼ marks filtered columns. Right-click again → <i>Clear this filter</i> or <i>Clear all filters</i>."],
                 "Several column filters work together (all must match)."),
                ("task", "Learn more about a material or yarn type",
                 ["Right-click the <i>Material</i> (e.g. PES) or <i>Garntyp</i> (e.g. DTY) cell of a yarn → "
                  "<b>Learn more in Knowledge Base…</b>. The same works on the drop-downs in New/Edit Yarn.",
                  "The fibre portrait (or the process page) opens in a window. " + B("Close") + " or Esc brings you back."]),
                ("task", "See in which trial series a yarn was used",
                 ["Click the <i>UsedInTrial</i> cell of the yarn (3). The series appear below it.",
                  "Click a series to see the trial numbers, double-click it to open the series."]),
                ("h", "Changing"),
                ("task", "Add a new yarn",
                 [f"Click {B('New Yarn')}, fill in the form and save it."],
                 "TrippleT warns if a yarn with the same type, material, titer, filaments and colour already exists."),
                ("task", "Change a yarn",
                 [f"Double-click the row (or {B('Edit in Form')}) to edit it in a form, or",
                  f"edit cells directly in the table and click {B('Save Changes')}."]),
                ("task", "Set the minimum stock",
                 ["Edit the <i>MinStock</i> column (or the field in the form)."],
                 "Superusers only. It can also be set in Yarn Stock."),
                ("task", "Delete a yarn",
                 [f"Select the row(s), click {B('Delete')} and confirm."],
                 "Admins only."),
                ("task", "Rearrange the columns",
                 ["Drag a column header to another position, or",
                  f"click {B('Columns…')}, drag the columns into the order you want and click <i>Save layout</i> to keep it."]),
            ]},
            {"key": "screen", "title": "Screen guide", "blocks": [
                ("svg", SVG, {"hint_edit": "double-click a row: form · edit cells directly, then Save Changes",
                              "hint_filter": "right-click a column header to filter it (green ▼ = filter active)"},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Name filter and buttons", "Filter by name; Reload, New Yarn, Edit in Form, Columns…, Delete, "
                                                    "Save Changes."),
                    ("(2) Column headers", "Click to sort, right-click to filter, drag to rearrange."),
                    ("(3) UsedInTrial", "Number of trial series using the yarn; click to expand them. <i>StockKg</i> "
                                        "shows the kilos currently in the yarn store."),
                ]),
            ]},
        ],
    },
    "de": {
        "window_title": "Wie funktioniert Manage Yarn?",
        "close": "Schliessen",
        "tabs": [
            {"key": "tasks", "title": "Wie mache ich…?", "blocks": [
                ("p", "Manage Yarn ist der Garnkatalog: jedes Garn, das in Versuchen verwendet werden kann. Die "
                      "Nummern (1)–(3) verweisen auf den Tab <i>Bildschirm</i>."),
                ("h", "Finden"),
                ("task", "Ein Garn über den Namen finden",
                 ["Einen Teil des Namens in <i>Filter by Name…</i> (1) eintippen. Treffer werden hervorgehoben."]),
                ("task", "Nach einer Spalte filtern (z.&nbsp;B. Titer oder Material)",
                 ["Rechtsklick auf den Spaltenkopf (2).",
                  "Text eingeben (<i>contains…</i>) oder bei Zahlen einen Bereich von/bis.",
                  "Ein grünes ▼ markiert gefilterte Spalten. Erneuter Rechtsklick → <i>Clear this filter</i> oder <i>Clear all filters</i>."],
                 "Mehrere Spaltenfilter wirken zusammen (alle müssen passen)."),
                ("task", "Mehr über ein Material oder einen Garntyp erfahren",
                 ["Rechtsklick auf die Zelle <i>Material</i> (z.&nbsp;B. PES) oder <i>Garntyp</i> (z.&nbsp;B. DTY) eines Garns → "
                  "<b>Learn more in Knowledge Base…</b>. Das geht auch bei den Auswahllisten in New/Edit Yarn.",
                  "Das Faserporträt (oder die Seite zum Verfahren) öffnet sich in einem Fenster. " + B("Close") + " oder Esc bringt dich zurück."]),
                ("task", "Sehen, in welchen Versuchsserien ein Garn verwendet wurde",
                 ["Auf die Zelle <i>UsedInTrial</i> des Garns klicken (3). Die Serien erscheinen darunter.",
                  "Klick auf eine Serie zeigt die Versuchsnummern, Doppelklick öffnet die Serie."]),
                ("h", "Ändern"),
                ("task", "Ein neues Garn anlegen",
                 [f"Auf {B('New Yarn')} klicken, das Formular ausfüllen und speichern."],
                 "TrippleT warnt, wenn es schon ein Garn mit gleichem Typ, Material, Titer, Filamenten und Farbe gibt."),
                ("task", "Ein Garn ändern",
                 [f"Doppelklick auf die Zeile (oder {B('Edit in Form')}) zum Bearbeiten im Formular, oder",
                  f"Zellen direkt in der Tabelle ändern und {B('Save Changes')} klicken."]),
                ("task", "Den Mindestbestand setzen",
                 ["Die Spalte <i>MinStock</i> (oder das Feld im Formular) bearbeiten."],
                 "Nur Superuser. Geht auch in Yarn Stock."),
                ("task", "Ein Garn löschen",
                 [f"Zeile(n) markieren, {B('Delete')} klicken und bestätigen."],
                 "Nur Admins."),
                ("task", "Die Spalten umordnen",
                 ["Einen Spaltenkopf an eine andere Position ziehen, oder",
                  f"auf {B('Columns…')} klicken, die Spalten in die gewünschte Reihenfolge ziehen und mit <i>Save layout</i> merken."]),
            ]},
            {"key": "screen", "title": "Bildschirm", "blocks": [
                ("svg", SVG, {"hint_edit": "Doppelklick auf eine Zeile: Formular · Zellen direkt ändern, dann Save Changes",
                              "hint_filter": "Rechtsklick auf einen Spaltenkopf filtert die Spalte (grünes ▼ = Filter aktiv)"},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Namensfilter und Buttons", "Nach Namen filtern; Reload, New Yarn, Edit in Form, Columns…, "
                                                     "Delete, Save Changes."),
                    ("(2) Spaltenköpfe", "Klick sortiert, Rechtsklick filtert, Ziehen ordnet um."),
                    ("(3) UsedInTrial", "Anzahl Versuchsserien mit diesem Garn; Klick klappt sie auf. <i>StockKg</i> "
                                        "zeigt die Kilos, die aktuell im Garnlager sind."),
                ]),
            ]},
        ],
    },
    "es": {
        "window_title": "¿Cómo funciona Manage Yarn?",
        "close": "Cerrar",
        "tabs": [
            {"key": "tasks", "title": "¿Cómo hago…?", "blocks": [
                ("p", "Manage Yarn es el catálogo de hilos: todos los hilos que se pueden usar en ensayos. Los números "
                      "(1)–(3) se refieren a la pestaña <i>Pantalla</i>."),
                ("h", "Buscar"),
                ("task", "Encontrar un hilo por su nombre",
                 ["Escribe parte del nombre en <i>Filter by Name…</i> (1). Las coincidencias se resaltan."]),
                ("task", "Filtrar por una columna (p.&nbsp;ej. título o material)",
                 ["Clic derecho en el encabezado de la columna (2).",
                  "Introduce un texto (<i>contains…</i>) o, para números, un rango desde/hasta.",
                  "Un ▼ verde marca las columnas filtradas. Otro clic derecho → <i>Clear this filter</i> o <i>Clear all filters</i>."],
                 "Varios filtros de columna se combinan (deben cumplirse todos)."),
                ("task", "Saber más sobre un material o un tipo de hilo",
                 ["Clic derecho en la celda <i>Material</i> (p.&nbsp;ej. PES) o <i>Garntyp</i> (p.&nbsp;ej. DTY) de un hilo → "
                  "<b>Learn more in Knowledge Base…</b>. También funciona en las listas desplegables de New/Edit Yarn.",
                  "El retrato de la fibra (o la página del proceso) se abre en una ventana. " + B("Close") + " o Esc te devuelve."]),
                ("task", "Ver en qué series de ensayos se usó un hilo",
                 ["Haz clic en la celda <i>UsedInTrial</i> del hilo (3). Las series aparecen debajo.",
                  "Un clic en una serie muestra los números de ensayo, un doble clic abre la serie."]),
                ("h", "Modificar"),
                ("task", "Crear un hilo nuevo",
                 [f"Haz clic en {B('New Yarn')}, rellena el formulario y guárdalo."],
                 "TrippleT avisa si ya existe un hilo con el mismo tipo, material, título, filamentos y color."),
                ("task", "Cambiar un hilo",
                 [f"Doble clic en la fila (o {B('Edit in Form')}) para editarlo en un formulario, o",
                  f"edita las celdas directamente en la tabla y haz clic en {B('Save Changes')}."]),
                ("task", "Definir el stock mínimo",
                 ["Edita la columna <i>MinStock</i> (o el campo del formulario)."],
                 "Solo superusuarios. También se puede hacer en Yarn Stock."),
                ("task", "Borrar un hilo",
                 [f"Selecciona la(s) fila(s), haz clic en {B('Delete')} y confirma."],
                 "Solo administradores."),
                ("task", "Reordenar las columnas",
                 ["Arrastra un encabezado de columna a otra posición, o",
                  f"haz clic en {B('Columns…')}, arrastra las columnas al orden deseado y haz clic en <i>Save layout</i> para conservarlo."]),
            ]},
            {"key": "screen", "title": "Pantalla", "blocks": [
                ("svg", SVG, {"hint_edit": "doble clic en una fila: formulario · editar celdas directamente y luego Save Changes",
                              "hint_filter": "clic derecho en un encabezado para filtrar la columna (▼ verde = filtro activo)"},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Filtro de nombre y botones", "Filtrar por nombre; Reload, New Yarn, Edit in Form, Columns…, "
                                                       "Delete, Save Changes."),
                    ("(2) Encabezados", "Clic para ordenar, clic derecho para filtrar, arrastrar para reordenar."),
                    ("(3) UsedInTrial", "Número de series de ensayos que usan el hilo; un clic las despliega. "
                                        "<i>StockKg</i> muestra los kilos que hay ahora en el almacén de hilo."),
                ]),
            ]},
        ],
    },
    "zh": {
        "window_title": "Manage Yarn 如何使用？",
        "close": "关闭",
        "tabs": [
            {"key": "tasks", "title": "我该如何……？", "blocks": [
                ("p", "Manage Yarn 是纱线目录：包含所有可用于试验的纱线。编号 (1)–(3) 对应"
                      " <i>界面说明</i> 选项卡。"),
                ("h", "查找"),
                ("task", "按名称查找纱线",
                 ["在 <i>Filter by Name…</i> (1) 中输入名称的一部分。匹配项会被高亮显示。"]),
                ("task", "按列筛选（例如纤度或材料）",
                 ["右键点击列标题 (2)。",
                  "输入文本（<i>contains…</i>），数字列则输入起止范围。",
                  "绿色 ▼ 表示该列已筛选。再次右键 → <i>Clear this filter</i> 或 <i>Clear all filters</i>。"],
                 "多个列筛选同时生效（必须全部满足）。"),
                ("task", "进一步了解某种材料或纱线类型",
                 ["右键点击纱线的 <i>Material</i>（例如 PES）或 <i>Garntyp</i>（例如 DTY）单元格 → "
                  "<b>Learn more in Knowledge Base…</b>。在 New/Edit Yarn 的下拉框中同样可用。",
                  "纤维介绍（或工艺页面）会在窗口中打开。" + B("Close") + " 或 Esc 可返回。"]),
                ("task", "查看纱线用于哪些试验系列",
                 ["点击该纱线的 <i>UsedInTrial</i> 单元格 (3)。系列会显示在其下方。",
                  "单击系列可查看试验编号，双击可打开该系列。"]),
                ("h", "修改"),
                ("task", "添加新纱线",
                 [f"点击 {B('New Yarn')}，填写表单并保存。"],
                 "如果已存在类型、材料、纤度、单丝数和颜色都相同的纱线，TrippleT 会发出警告。"),
                ("task", "修改纱线",
                 [f"双击该行（或点击 {B('Edit in Form')}）在表单中编辑，或",
                  f"直接在表格中编辑单元格，然后点击 {B('Save Changes')}。"]),
                ("task", "设置最低库存",
                 ["编辑 <i>MinStock</i> 列（或表单中的对应字段）。"],
                 "仅限超级用户。也可在 Yarn Stock 中设置。"),
                ("task", "删除纱线",
                 [f"选中一行或多行，点击 {B('Delete')} 并确认。"],
                 "仅限管理员。"),
                ("task", "重新排列列",
                 ["将列标题拖到其他位置，或",
                  f"点击 {B('Columns…')}，将列拖成所需顺序，然后点击 <i>Save layout</i> 保存。"]),
            ]},
            {"key": "screen", "title": "界面说明", "blocks": [
                ("svg", SVG, {"hint_edit": "双击一行：打开表单 · 或直接编辑单元格，然后点 Save Changes",
                              "hint_filter": "右键点击列标题进行筛选（绿色 ▼ = 筛选已启用）"},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) 名称筛选和按钮", "按名称筛选；Reload、New Yarn、Edit in Form、Columns…、Delete、"
                                         "Save Changes。"),
                    ("(2) 列标题", "单击排序，右键筛选，拖动重新排列。"),
                    ("(3) UsedInTrial", "使用该纱线的试验系列数量；点击展开。<i>StockKg</i> "
                                        "显示纱线库房中当前的公斤数。"),
                ]),
            ]},
        ],
    },
}
