# ui/widgets/help_texts_manage_jets.py
"""Hilfetexte Manage Jets (EN/DE/ES/ZH) fuer ui/widgets/multilang_help.py.

Spiegelt ui/screen_manage_jets.py (Suche ueber Jet/Remarks mit ";" = ODER,
Spaltenfilter per Rechtsklick auf den Kopf = UND, Spalten verschiebbar +
Columns…, New Jet / Copy (Formular vorbelegt, Feld Jet leer) / Edit in Form /
Delete / Save Changes; nur bearbeitbar mit can_use_admin_box(), sonst
read-only). Bei Aenderungen dort hier (alle 4 Sprachen) und in
assets/images/help_manage_jets.svg nachziehen.
"""

SVG = "assets/images/help_manage_jets.svg"
SVG_W, SVG_H = 940, 240


def B(name: str) -> str:
    return f"<b>[{name}]</b>"


TEXTS = {
    "en": {
        "window_title": "How does Manage Jets work?",
        "close": "Close",
        "tabs": [
            {"key": "tasks", "title": "How do I…?", "blocks": [
                ("p", "Manage Jets is the catalogue of all jets with their geometry. Numbers (1)–(2) refer to the "
                      "<i>Screen guide</i> tab."),
                ("warn", "Changing jets requires admin rights. For everyone else the screen is read-only."),
                ("h", "Finding"),
                ("task", "Search for jets",
                 ["Type into <i>Search Jet or Remarks…</i> (1). It searches the jet name and the remarks.",
                  "Separate several terms with <b>;</b> to find rows that contain <i>any</i> of them, e.g. <i>S+ 1.2; S+ 1.4</i>."]),
                ("task", "Filter by a column (e.g. air bore or process)",
                 ["Right-click the column header (2).",
                  "Enter text (<i>contains…</i>) or, for numbers, a range from/to.",
                  "A green ▼ marks filtered columns. Right-click again → <i>Clear this filter</i> or <i>Clear all filters</i>."],
                 "Column filters work together (all must match), in addition to the search."),
                ("h", "Changing"),
                ("task", "Add a new jet",
                 [f"Click {B('New Jet')}, fill in the form and save it."]),
                ("task", "Add a jet that is similar to an existing one",
                 ["Select the existing jet.",
                  f"Click {B('Copy')}. The form opens with all its values; only the name <i>Jet</i> is empty.",
                  "Enter the new name, adjust the values and save."]),
                ("task", "Change a jet",
                 [f"Double-click the row (or {B('Edit in Form')}) to edit it in a form, or",
                  f"edit cells directly in the table and click {B('Save Changes')}."]),
                ("task", "Delete jets",
                 [f"Select the row(s), click {B('Delete')} and confirm."]),
                ("task", "Rearrange the columns",
                 ["Drag a column header to another position, or",
                  f"click {B('Columns…')}, drag the columns into the order you want and click <i>Save layout</i> to keep it."]),
            ]},
            {"key": "screen", "title": "Screen guide", "blocks": [
                ("svg", SVG, {"hint_edit": "double-click a row: form · edit cells directly, then Save Changes",
                              "hint_filter": "right-click a column header to filter it (green ▼ = filter active)"},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Search and buttons", "Search in jet name and remarks (; = several terms); Reload, New Jet, "
                                               "Copy, Edit in Form, Delete, Save Changes, Columns…."),
                    ("(2) Column headers", "Right-click to filter, drag to rearrange. The jet column stays fixed on the left."),
                ]),
            ]},
        ],
    },
    "de": {
        "window_title": "Wie funktioniert Manage Jets?",
        "close": "Schliessen",
        "tabs": [
            {"key": "tasks", "title": "Wie mache ich…?", "blocks": [
                ("p", "Manage Jets ist der Katalog aller Düsen mit ihrer Geometrie. Die Nummern (1)–(2) verweisen auf "
                      "den Tab <i>Bildschirm</i>."),
                ("warn", "Düsen ändern erfordert Admin-Rechte. Für alle anderen ist der Bildschirm nur lesbar."),
                ("h", "Finden"),
                ("task", "Düsen suchen",
                 ["In <i>Search Jet or Remarks…</i> (1) tippen. Gesucht wird im Düsennamen und in den Bemerkungen.",
                  "Mehrere Begriffe mit <b>;</b> trennen, um Zeilen zu finden, die <i>einen davon</i> enthalten, z.&nbsp;B. <i>S+ 1.2; S+ 1.4</i>."]),
                ("task", "Nach einer Spalte filtern (z.&nbsp;B. Luftbohrung oder Prozess)",
                 ["Rechtsklick auf den Spaltenkopf (2).",
                  "Text eingeben (<i>contains…</i>) oder bei Zahlen einen Bereich von/bis.",
                  "Ein grünes ▼ markiert gefilterte Spalten. Erneuter Rechtsklick → <i>Clear this filter</i> oder <i>Clear all filters</i>."],
                 "Spaltenfilter wirken zusammen (alle müssen passen), zusätzlich zur Suche."),
                ("h", "Ändern"),
                ("task", "Eine neue Düse anlegen",
                 [f"Auf {B('New Jet')} klicken, das Formular ausfüllen und speichern."]),
                ("task", "Eine Düse anlegen, die einer bestehenden ähnelt",
                 ["Die bestehende Düse markieren.",
                  f"Auf {B('Copy')} klicken. Das Formular öffnet sich mit allen Werten; nur der Name <i>Jet</i> ist leer.",
                  "Neuen Namen eingeben, Werte anpassen und speichern."]),
                ("task", "Eine Düse ändern",
                 [f"Doppelklick auf die Zeile (oder {B('Edit in Form')}) zum Bearbeiten im Formular, oder",
                  f"Zellen direkt in der Tabelle ändern und {B('Save Changes')} klicken."]),
                ("task", "Düsen löschen",
                 [f"Zeile(n) markieren, {B('Delete')} klicken und bestätigen."]),
                ("task", "Die Spalten umordnen",
                 ["Einen Spaltenkopf an eine andere Position ziehen, oder",
                  f"auf {B('Columns…')} klicken, die Spalten in die gewünschte Reihenfolge ziehen und mit <i>Save layout</i> merken."]),
            ]},
            {"key": "screen", "title": "Bildschirm", "blocks": [
                ("svg", SVG, {"hint_edit": "Doppelklick auf eine Zeile: Formular · Zellen direkt ändern, dann Save Changes",
                              "hint_filter": "Rechtsklick auf einen Spaltenkopf filtert die Spalte (grünes ▼ = Filter aktiv)"},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Suche und Buttons", "Suche in Düsenname und Bemerkungen (; = mehrere Begriffe); Reload, New Jet, "
                                              "Copy, Edit in Form, Delete, Save Changes, Columns…."),
                    ("(2) Spaltenköpfe", "Rechtsklick zum Filtern, Ziehen zum Umordnen. Die Düsenspalte bleibt links fix."),
                ]),
            ]},
        ],
    },
    "es": {
        "window_title": "¿Cómo funciona Manage Jets?",
        "close": "Cerrar",
        "tabs": [
            {"key": "tasks", "title": "¿Cómo hago…?", "blocks": [
                ("p", "Manage Jets es el catálogo de todas las toberas con su geometría. Los números (1)–(2) se refieren "
                      "a la pestaña <i>Pantalla</i>."),
                ("warn", "Modificar toberas requiere derechos de administrador. Para los demás, la pantalla es de solo lectura."),
                ("h", "Buscar"),
                ("task", "Buscar toberas",
                 ["Escribe en <i>Search Jet or Remarks…</i> (1). Se busca en el nombre de la tobera y en las observaciones.",
                  "Separa varios términos con <b>;</b> para encontrar filas que contengan <i>cualquiera</i> de ellos, p.&nbsp;ej. <i>S+ 1.2; S+ 1.4</i>."]),
                ("task", "Filtrar por una columna (p.&nbsp;ej. orificio de aire o proceso)",
                 ["Clic derecho en el encabezado de la columna (2).",
                  "Introduce un texto (<i>contains…</i>) o, para números, un rango desde/hasta.",
                  "Un ▼ verde marca las columnas filtradas. Otro clic derecho → <i>Clear this filter</i> o <i>Clear all filters</i>."],
                 "Los filtros de columna se combinan (deben cumplirse todos), además de la búsqueda."),
                ("h", "Modificar"),
                ("task", "Crear una tobera nueva",
                 [f"Haz clic en {B('New Jet')}, rellena el formulario y guárdalo."]),
                ("task", "Crear una tobera parecida a una existente",
                 ["Selecciona la tobera existente.",
                  f"Haz clic en {B('Copy')}. El formulario se abre con todos sus valores; solo el nombre <i>Jet</i> está vacío.",
                  "Introduce el nombre nuevo, ajusta los valores y guarda."]),
                ("task", "Cambiar una tobera",
                 [f"Doble clic en la fila (o {B('Edit in Form')}) para editarla en un formulario, o",
                  f"edita las celdas directamente en la tabla y haz clic en {B('Save Changes')}."]),
                ("task", "Borrar toberas",
                 [f"Selecciona la(s) fila(s), haz clic en {B('Delete')} y confirma."]),
                ("task", "Reordenar las columnas",
                 ["Arrastra un encabezado de columna a otra posición, o",
                  f"haz clic en {B('Columns…')}, arrastra las columnas al orden deseado y haz clic en <i>Save layout</i> para conservarlo."]),
            ]},
            {"key": "screen", "title": "Pantalla", "blocks": [
                ("svg", SVG, {"hint_edit": "doble clic en una fila: formulario · editar celdas directamente y luego Save Changes",
                              "hint_filter": "clic derecho en un encabezado para filtrar la columna (▼ verde = filtro activo)"},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) Búsqueda y botones", "Buscar en nombre de tobera y observaciones (; = varios términos); Reload, "
                                               "New Jet, Copy, Edit in Form, Delete, Save Changes, Columns…."),
                    ("(2) Encabezados", "Clic derecho para filtrar, arrastrar para reordenar. La columna de la tobera "
                                        "queda fija a la izquierda."),
                ]),
            ]},
        ],
    },
    "zh": {
        "window_title": "Manage Jets 如何使用？",
        "close": "关闭",
        "tabs": [
            {"key": "tasks", "title": "我该如何……？", "blocks": [
                ("p", "Manage Jets 是所有喷嘴及其几何参数的目录。编号 (1)–(2) 对应"
                      " <i>界面说明</i> 选项卡。"),
                ("warn", "修改喷嘴需要管理员权限。其他人只能以只读方式查看此界面。"),
                ("h", "查找"),
                ("task", "搜索喷嘴",
                 ["在 <i>Search Jet or Remarks…</i> (1) 中输入内容。会搜索喷嘴名称和备注。",
                  "用 <b>;</b> 分隔多个关键词，可找到包含其中<i>任意</i>一个的行，例如 <i>S+ 1.2; S+ 1.4</i>。"]),
                ("task", "按列筛选（例如气孔或工艺）",
                 ["右键点击列标题 (2)。",
                  "输入文本（<i>contains…</i>），数字列则输入起止范围。",
                  "绿色 ▼ 表示该列已筛选。再次右键 → <i>Clear this filter</i> 或 <i>Clear all filters</i>。"],
                 "多个列筛选同时生效（必须全部满足），并与搜索叠加。"),
                ("h", "修改"),
                ("task", "添加新喷嘴",
                 [f"点击 {B('New Jet')}，填写表单并保存。"]),
                ("task", "添加与现有喷嘴相似的喷嘴",
                 ["选中现有喷嘴。",
                  f"点击 {B('Copy')}。表单会带着它的所有数值打开，只有名称 <i>Jet</i> 为空。",
                  "输入新名称，调整数值后保存。"]),
                ("task", "修改喷嘴",
                 [f"双击该行（或点击 {B('Edit in Form')}）在表单中编辑，或",
                  f"直接在表格中编辑单元格，然后点击 {B('Save Changes')}。"]),
                ("task", "删除喷嘴",
                 [f"选中一行或多行，点击 {B('Delete')} 并确认。"]),
                ("task", "重新排列列",
                 ["将列标题拖到其他位置，或",
                  f"点击 {B('Columns…')}，将列拖成所需顺序，然后点击 <i>Save layout</i> 保存。"]),
            ]},
            {"key": "screen", "title": "界面说明", "blocks": [
                ("svg", SVG, {"hint_edit": "双击一行：打开表单 · 或直接编辑单元格，然后点 Save Changes",
                              "hint_filter": "右键点击列标题进行筛选（绿色 ▼ = 筛选已启用）"},
                 SVG_W, SVG_H),
                ("areas", [
                    ("(1) 搜索和按钮", "在喷嘴名称和备注中搜索（; = 多个关键词）；Reload、New Jet、"
                                     "Copy、Edit in Form、Delete、Save Changes、Columns…。"),
                    ("(2) 列标题", "右键筛选，拖动重新排列。喷嘴列固定在最左侧。"),
                ]),
            ]},
        ],
    },
}
