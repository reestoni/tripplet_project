# tests/test_web_assets.py
"""Plotly liegt lokal in assets/js - Charts müssen ohne Internet laufen."""
import os

from ui.pathutil import resource_path, web_base_url
from ui.report_html_template import _HTML_TEMPLATE
from ui.smart_dashboard_html import DASHBOARD_HTML


def test_plotly_is_bundled_and_pages_use_it():
    assert os.path.isfile(resource_path("assets/js/plotly-2.32.0.min.js"))
    assert web_base_url().toLocalFile().endswith("assets/js/")
    for html in (_HTML_TEMPLATE, DASHBOARD_HTML):
        assert '<script src="plotly-2.32.0.min.js"></script>' in html
        assert "cdn.plot.ly" not in html
