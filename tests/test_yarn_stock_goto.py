"""Tests fuer parse_spool_input() ("Go to spool #" in Yarn Stock): Nummer
von Hand oder kompletter QR-Inhalt eines Spulen-Etiketts (Handscanner)."""
import pytest

from ui.screen_yarn_stock import parse_spool_input, _qr_content


@pytest.mark.parametrize("text, expected", [
    ("213", 213),
    ("  213  ", 213),
    ("#213", 213),
    ("# 213", 213),
    # Kompletter QR-Inhalt, wie ihn _qr_content() erzeugt
    ("Y:PES POY 85/50F36 DTEX (SD ROUND - WHITE);B:989G;L:E12;S:213", 213),
    ("Y:X;B:;L:;S:7", 7),
    # Scanner mit US-Layout auf CH/DE-Tastatur: ":" kommt als anderes Zeichen an
    ("YÖPES POY;BÖ989G;LÖE12;SÖ213", 213),
    ("y:pes;b:989g;l:e12;s:213", 213),
    ("Y:X;B:1;L:A1;S:213\r\n", 213),
])
def test_parse_valid(text, expected):
    assert parse_spool_input(text) == expected


@pytest.mark.parametrize("text", [
    "", "   ", "#", "abc", "E12", "Y:X;B:989G;L:E12",
    "²",  # Unicode-"Ziffer", die int() nicht versteht
])
def test_parse_invalid(text):
    assert parse_spool_input(text) is None


def test_roundtrip_with_label_content():
    """Was auf das Etikett gedruckt wird, muss wieder zur selben Spule fuehren -
    auch wenn Batch/Location selbst Ziffern enthalten."""
    item = {"Yarn": "PES POY 280/167f72 dtex", "Batch": "T003G/0", "Location": "I12", "SpoolID": 4711}
    assert parse_spool_input(_qr_content(item)) == 4711
