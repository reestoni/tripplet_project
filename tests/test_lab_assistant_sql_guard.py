"""Tests fuer ui/lab_assistant_worker.py's validate_readonly_sql().

Der Lab-Assistant-Chat (ui/screen_lab_assistant.py) laesst Claude selbst SQL
gegen die laufende DB (dev_local/dev/prod) ausfuehren - es gibt in diesem
Projekt KEINEN separaten read-only DB-User (siehe db/connection.py's
_load_secrets()), validate_readonly_sql() ist deshalb die EINZIGE Absicherung
gegen Schreibzugriffe/Mehrfach-Statements/Zugriff auf tbluser (pw_hash/
api_key_enc). Bewusst als eigene, DB-/Qt-freie Testdatei (keine TRIPPLET_MODE-
Umgebung noetig, laeuft ueberall schnell) statt in test_tripplet_ui.py/
test_tripplet_regression.py, weil dieser Guard sicherheitsrelevant genug ist,
um eigene, klar benannte Regressionstests zu verdienen.
"""

import pytest

from ui.lab_assistant_worker import MAX_ROWS_PER_QUERY, validate_readonly_sql


# ---- akzeptierte Queries ------------------------------------------------

def test_plain_select_is_accepted():
    out = validate_readonly_sql("SELECT * FROM tbltrial")
    assert out.startswith("SELECT * FROM tbltrial")


def test_with_cte_is_accepted():
    out = validate_readonly_sql("WITH x AS (SELECT 1) SELECT * FROM x")
    assert out.startswith("WITH x AS (SELECT 1) SELECT * FROM x")


def test_lowercase_select_is_accepted():
    out = validate_readonly_sql("select id from tbljets")
    assert out.startswith("select id from tbljets")


def test_trailing_semicolon_is_stripped_not_rejected():
    out = validate_readonly_sql("SELECT 1;")
    assert ";" not in out


def test_explicit_limit_is_not_overridden():
    out = validate_readonly_sql("SELECT * FROM tbltrial LIMIT 5")
    assert out.count("LIMIT") == 1
    assert "LIMIT 5" in out


def test_missing_limit_gets_injected():
    out = validate_readonly_sql("SELECT * FROM tbltrial")
    assert f"LIMIT {MAX_ROWS_PER_QUERY + 1}" in out


# ---- abgelehnte Queries: Schreib-/DDL-Zugriffe ---------------------------

@pytest.mark.parametrize("sql", [
    "INSERT INTO tbltrial (ID) VALUES (1)",
    "UPDATE tbltrial SET Versuchsnummer = 1",
    "DELETE FROM tbltrial",
    "DROP TABLE tbltrial",
    "ALTER TABLE tbltrial ADD COLUMN x INT",
    "TRUNCATE TABLE tbltrial",
    "CREATE TABLE x (id INT)",
    "GRANT ALL ON tbltrial TO 'x'@'%'",
    "REPLACE INTO tbltrial (ID) VALUES (1)",
    "CALL some_procedure()",
])
def test_write_and_ddl_statements_are_rejected(sql):
    with pytest.raises(ValueError):
        validate_readonly_sql(sql)


def test_stacked_statements_are_rejected():
    with pytest.raises(ValueError):
        validate_readonly_sql("SELECT 1; DROP TABLE tbltrial")


def test_outfile_export_is_rejected():
    with pytest.raises(ValueError):
        validate_readonly_sql("SELECT * FROM tbltrial INTO OUTFILE '/tmp/x.csv'")


def test_empty_query_is_rejected():
    with pytest.raises(ValueError):
        validate_readonly_sql("")
    with pytest.raises(ValueError):
        validate_readonly_sql("   ")


# ---- abgelehnte Queries: tbluser (pw_hash/api_key_enc) -------------------

@pytest.mark.parametrize("sql", [
    "SELECT * FROM tbluser",
    "select * from TblUser",
    "SELECT pw_hash FROM tblUser",
    "SELECT t.* FROM tbltrial t JOIN tbluser u ON 1=1",
    "SELECT * FROM tbltrial WHERE ID IN (SELECT ID FROM tbluser)",
])
def test_tbluser_access_is_rejected(sql):
    with pytest.raises(ValueError):
        validate_readonly_sql(sql)


def test_unrelated_query_is_not_falsely_blocked_by_user_substring():
    # 'tbluser' darf keine anderen, aehnlich benannten, legitimen Tabellen
    # blockieren - im echten Schema gibt es keine solche Kollision, aber der
    # Test dokumentiert die Absicht: nur die exakte Tabelle 'tbluser' ist
    # gesperrt, kein pauschales "user" ueberall.
    out = validate_readonly_sql("SELECT * FROM tbluserdirectory")
    assert "tbluserdirectory" in out
