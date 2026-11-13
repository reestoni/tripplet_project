# ui/widgets/experiment_request_help_texts.py
"""Texts of the Experiment Request help (ui/widgets/experiment_request_help_dialog.py)
as pure data - shared with the web app. English only (as on the desktop).
Moved from the dialog 2026-11-13, wording unchanged."""

WINDOW_TITLE = "Wie funktionieren Experiment Requests?"
SVG = "assets/images/experiment_request_flow.svg"
# native aspect ratio of the SVG (viewBox="-230 0 1170 500")
SVG_W, SVG_H = 1080, 461
INTRO = ("From request to experiment: green arrows are steps you take yourself, purple ones a superuser "
         "takes when reviewing.")
NOTE = ("<b>Important when editing:</b> if you change a request that is already approved or linked "
        'to an experiment, a separate <b>copy</b> in status "Open" is created (dashed in the diagram) '
        "– only when a superuser accepts it does the content go into the original, without changing "
        "its status or experiment link.")
