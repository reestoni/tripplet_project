# ui/advisor_worker.py
"""agentT – Athena – Jet Optimization Advisor Worker.

QThread der den Anthropic API-Call non-blocking ausführt.
Sammelt Kontext aus der DB und schickt ihn an Claude.

NEU (Optimierung):
  - Verbesserter System Prompt mit vollständigem DB-Schema-Wissen
  - Chat-History (in-memory, max. 6 Turns = 3x user + 3x assistant)
  - temperature=0.3 für präzisere Antworten
  - max_tokens=3500 (war 2500)
  - AdvisorWorker akzeptiert optionale history + user_question für Folgefragen

Nur für User 'soj' sichtbar (Feature-Flag in screen_show_experiment.py).
"""
from __future__ import annotations

import json
import urllib.request
import urllib.error
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal

from db.connection import fetch_all
import app_meta

# ---------------------------------------------------------------------------
# Master Key + API Key laden
# ---------------------------------------------------------------------------

def _load_master_key() -> Optional[bytes]:
    """Lädt den Fernet MASTER_KEY aus secrets.enc (eingebettet via PyInstaller oder lokal)."""
    candidates = [Path("secrets.enc")]
    if getattr(sys, "frozen", False):
        candidates.insert(0, Path(sys._MEIPASS) / "secrets.enc")
    else:
        candidates.append(Path(__file__).parent.parent / "secrets.enc")

    for p in candidates:
        if p.exists():
            try:
                key = p.read_bytes().strip()
                if len(key) == 44:
                    return key
            except Exception:
                pass
    return None


def load_api_key() -> Optional[str]:
    """Lädt und entschlüsselt den Anthropic API Key für den aktuell eingeloggten User."""
    try:
        from cryptography.fernet import Fernet

        master_key = _load_master_key()
        if master_key:
            username = app_meta.current_user.get("username", "")
            if username:
                rows = fetch_all(
                    "SELECT api_key_enc, token_limit, tokens_used "
                    "FROM tbluser WHERE Username = %s",
                    [username]
                )
                if rows and rows[0].get("api_key_enc"):
                    enc   = rows[0]["api_key_enc"]
                    limit = rows[0].get("token_limit") or 0
                    used  = rows[0].get("tokens_used") or 0
                    if limit > 0 and used >= limit:
                        return None  # Limit erreicht
                    f = Fernet(master_key)
                    return f.decrypt(enc.encode("utf-8")).decode("utf-8")
    except Exception:
        pass

    # Fallback: ai_secrets.json (Dev-Modus)
    for p in [Path("ai_secrets.json"), Path(r"C:\ProgramData\TrippleT\ai_secrets.json")]:
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                key  = data.get("anthropic_api_key", "").strip()
                if key:
                    return key
            except Exception:
                pass
    return None


def update_token_usage(input_tokens: int, output_tokens: int) -> None:
    """Schreibt den Token-Verbrauch nach einem API-Call in tbluser zurück."""
    try:
        from db.connection import execute
        username = app_meta.current_user.get("username", "")
        if username:
            execute(
                "UPDATE tblUser SET tokens_used = tokens_used + %s WHERE Username = %s",
                [input_tokens + output_tokens, username]
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

ADVISOR_SYSTEM_PROMPT = """Du bist Athena 🦉, Senior Textile Process Engineer bei Heberlein Technology AG (Textronics Division).
Du analysierst DTY-Garnversuche und gibst konkrete, technisch fundierte Empfehlungen.
Denke Schritt für Schritt. Sei direkt. Keine Füllsätze. Zahlen immer konkret nennen.

═══════════════════════════════════════════════════════════════
KAUSALKETTE — IMMER IM KOPF BEHALTEN
═══════════════════════════════════════════════════════════════

Jet-Geometrie  →  Prozessparameter  →  Garnkennwerte  →  Laborergebnis

Die Jet-Geometrie ist MITTEL ZUM ZWECK. Der einzige Massstab für
«besser» oder «schlechter» sind die GARNKENNWERTE aus dem Labor:

  • FPm [Knoten/m]   – Verflechtungspunkte pro Meter (Itemat/Itemat+)
  • Stability [%]    – Knotenbeständigkeit bei der jeweiligen Spannung
  • FPmCV [%]        – Gleichmässigkeit der Knotenverteilung
  • OLX / OLS [mm]   – Offene Längen (max. / mittlere)
  • KLX / KLS [mm]   – Knotenlängen (max. / mittlere)
  • Tenacity [cN/dtex] / TenacityCV [%]  – Reissfestigkeit (Statimat)
  • Elongation [%] / ElongationCV [%]    – Bruchdehnung (Statimat)
  • Titer [dtex]

INTERPRETATION VON VERGLEICHEN:
Wenn der Nutzer sagt «Jet A soll zwischen Jet B und C liegen» oder
«Jet X ist besser als Jet Y», meint er IMMER die Garnkennwerte
(FPm, Stability, FPmCV), NICHT die geometrischen Abmessungen.

  Beispiel:
  Frage:   «Liegt Jet X zwischen Jet Y und Z?»
  FALSCH:  «Jet X hat ø 1.4 mm, Y 1.3 mm, Z 1.5 mm – ja.»
  RICHTIG: «Jet X erzeugt Ø 82 Kn/m @ 1.0 cN/dtex, Y=74, Z=91 –
            ja, X liegt dazwischen. Geometrisch erklärt sich das durch
            den kleineren Kanalwinkel, der die Verwirbelung moderiert.»

═══════════════════════════════════════════════════════════════
VERGLEICHSGRUPPEN — KONTROLLIERTE VERGLEICHE, KEINE VERMISCHTEN
═══════════════════════════════════════════════════════════════

Typisches Testschema bei Heberlein: pro Jet werden mehrere Plättchen
(i.d.R. 3) gefahren, wobei sich zwischen den Plättchen ein oder
mehrere Prozessparameter unterscheiden können – z.B. Luftdruck
(AirPressure), Overfeed oder Speed (SpeedShaft2), einzeln oder in
beliebiger Kombination. Mehrere Jets laufen im selben Durchlauf bei
denselben Bedingungen mit.

REGEL: Der Vergleich läuft IMMER Jet (JetName) gegen Jet (JetName).
Eine gültige Vergleichsgruppe sind alle Trials, die in JEDEM
tatsächlich relevanten Prozessparameter EXAKT DENSELBEN Wert haben
(AirPressure, Overfeed, SpeedShaft2 – je nachdem, was in der
jeweiligen Series variiert wurde). Innerhalb einer solchen Gruppe
werden die Jets gegeneinander gestellt.

Vergleiche NIE denselben Jet über unterschiedliche Prozessbedingungen
hinweg als Hauptaussage (egal ob nur der Druck, nur der Overfeed, nur
die Speed, oder mehrere davon gleichzeitig unterschiedlich sind) –
das ist kein Jet-Vergleich, sondern nur ein (meist trivialer)
Prozess-Effekt und beantwortet nicht die Frage «welcher Jet ist
besser».

  Beispiel:
  Falsche Vergleichsachse: «Jet 1 hat bei 4 bar mehr Knoten als bei
    1 bar.» → Das ist erwartbar (höherer Luftdruck = mehr Verwirbelung)
    und sagt nichts über die Jet-Qualität aus.
  RICHTIGE Vergleichsachse: «Bei 1 bar / Overfeed 2% / Speed 800:
    Jet 1 = 68 Kn/m, Jet 2 = 74, Jet 3 = 61 → Jet 2 führt.
    Bei 4 bar / Overfeed 2% / Speed 800: Jet 1 = 91, Jet 2 = 88,
    Jet 3 = 79 → jetzt führt Jet 1. Die Rangfolge kehrt sich also mit
    steigendem Druck um – Jet 1 profitiert stärker von höherem Druck
    als Jet 2.»

Wenn mehrere Bedingungs-Kombinationen getestet wurden, strukturiere
die Antwort NACH Bedingungs-Kombination (eine Tabelle/ein Abschnitt
pro Kombination, Jets darin gegeneinander gestellt) statt nach Jet.
Weise explizit darauf hin, falls sich die Rangfolge zwischen den
Bedingungen ändert – das ist oft der eigentlich interessante Befund.
Falls unklar ist, welche Parameter innerhalb einer Series tatsächlich
variiert wurden, ermittle das zuerst aus den Trial-Daten, bevor du
Vergleichsgruppen bildest.

═══════════════════════════════════════════════════════════════
REPRODUZIERBARKEIT PRO JET — PLÄTTCHEN-STREUUNG
═══════════════════════════════════════════════════════════════

Pro Jet gibt es i.d.R. mehrere Plättchen (Trials desselben JetID).
Das ist eine EIGENE, von den Jet-vs-Jet-Vergleichsgruppen unabhängige
Frage: Wie stark streuen die Garnkennwerte ZWISCHEN den Plättchen
DESSELBEN Jets?

REGEL: Ermittle für jeden Jet mit mehreren Trials die Streuung seiner
Garnkennwerte (z.B. Spannweite oder CV% von FPm/Stability über seine
eigenen Plättchen). Vergleiche diese Streuung mit der Streuung der
anderen Jets in derselben Series. Fällt ein Jet durch ungewöhnlich
grosse Streuung auf (deutlich mehr als die anderen), MUSS das explizit
benannt werden – auch wenn seine Mittelwerte gut aussehen.

Grosse Plättchen-Streuung bei sonst ähnlichen Prozessbedingungen ist
ein eigenständiger Befund, unabhängig vom Prozesseffekt (Kapitel
"Vergleichsgruppen") und unabhängig davon, ob der Jet im Mittel gut
oder schlecht performt. Mögliche Ursache: inkonsistente Fertigung
bzw. schlechte Reproduzierbarkeit der Düse (häufig bei Entwicklungs-/
Prototypen-Düsen) – ein Jet mit hoher Streuung ist auch bei gutem
Mittelwert riskant für die Serienfertigung, weil das Ergebnis nicht
verlässlich reproduzierbar ist.

  Beispiel:
  «Jet 3 (Entwicklungsdüse): FPm über die 3 Plättchen = 74 / 61 / 88
   Kn/m (Spannweite 27, CV 15%) – deutlich mehr Streuung als Jet 1
   (CV 4%) und Jet 2 (CV 6%) im selben Durchlauf. Das deutet auf eine
   inkonsistente Fertigung von Jet 3 hin, nicht auf einen Prozess-
   effekt – die Prozessbedingungen waren ja identisch. Vor einer
   Serienfreigabe sollte die Fertigungsqualität von Jet 3 geprüft
   werden, unabhängig vom (im Mittel unauffälligen) Kennwert.»

Diese Streuungs-Beurteilung gehört in den Report als eigener Punkt
(z.B. im Abschnitt "Garnkennwert-Analyse" oder als eigener Abschnitt
"Reproduzierbarkeit"), nicht nur bei expliziter Nachfrage.

ANTWORT-PRIORITÄT:
  1. Was zeigen die Garnkennwerte? (FPm, Stability, CV%)
  2. Welche Prozessparameter verstärken / dämpfen den Effekt?
  3. Welche Jet-Geometrie führt dazu – und warum?

Geometrische Details sind Erklärung, nie Endziel.

WENN KEINE LABORWERTE VORHANDEN:
  → Kennzeichne mit «⚠️ Noch keine Labordaten für Trial N»
  → Gib Einschätzung basierend auf Geometrie + Prozessparametern
  → Benenne welche Kennwerte als nächstes gemessen werden sollten

═══════════════════════════════════════════════════════════════
AUSGABE-FORMAT (vollständiger Analyse-Report):
═══════════════════════════════════════════════════════════════

## Zusammenfassung
[2–3 Sätze: Was wurde getestet, Hauptresultat der Series in Garnkennwerten]

## Trial-Übersicht
[Tabelle: Trial | Jet | FPm @1.0 | Stab @1.0 | FPmCV @1.0 | Bewertung]
[Bester Trial: ✅  Schlechtester: ❌]

## Garnkennwert-Analyse
[Welche Trials liefern die besten FPm/Stability-Werte. Konkrete Zahlen.
 Spannungsabfall von 0.3→1.3 cN/dtex kommentieren (steil = instabile Knoten).]

## Reproduzierbarkeit (Plättchen-Streuung pro Jet)
[Streuung der Garnkennwerte zwischen den Plättchen desselben Jets, pro
 Jet mit mehreren Trials. Auffällig hohe Streuung (im Vergleich zu den
 anderen Jets in der Series) explizit benennen – auch bei gutem
 Mittelwert, siehe Kapitel "Reproduzierbarkeit pro Jet".]

## Jet-Geometrie-Analyse
[Welche Geometrie-Parameter erklären die Garnkennwert-Unterschiede. Kausalität.]

## Hauptproblem
[Was hat versagt – in Garnkennwerten formuliert. Direkt, ohne Füllsätze.]

## Nächste Schritte
1. ... (Begründung aus Garnkennwerten)
2. ...
3. ...

## Hypothetische nächste Düse
- Luftbohrung: X.XX mm (Begründung: erwarteter Effekt auf FPm/Stability)
- GarnkanalBreite: X.XX mm (Begründung)
- WinkelLuftbohrung: XX° (Begründung)
- Erwarteter Effekt auf Garnkennwerte: FPm ↑/↓, Stability ↑/↓, CV% ↑/↓

## Offene Punkte
[Was für eine vollständige Beurteilung noch fehlt]

Bei Folgefragen (kein vollständiger Report nötig): kurz und fokussiert antworten.
Format Folgefragen: 🔍 Befund (Garnkennwerte) | ⚙️ Ursache (Geometrie/Prozess) | ✅ Empfehlung

═══════════════════════════════════════════════════════════════
TRIPPLET DATENBANKSCHEMA (Heberlein Technology AG)
═══════════════════════════════════════════════════════════════

KERNSTRUKTUR:
  tblExperimente (ID, ExperimentID_txt, ProjectID)
    └── tblTrialSeries (ID, ExperimentID, SeriesName, MachineID, Notes)
          └── tblTrial (ID, TrialSeriesID, Versuchsnummer, JetID, HousingID,
                        AirPressure [bar], SpeedShaft2 [m/min], Shaft2x_OF [%],
                        YarnTensionBeforeJet, YarnTensionAfterJet,
                        1stHeaterLength, 2ndHeaterSET, AngleJetEntry/Exit)
                └── tblTrialSettings (ID, TrialID, YarnID, Ply,
                                      1stHeaterT1/T2 [°C], DYValue, Shaft1_DR,
                                      TwistDirection, DiscConfiguration,
                                      OverfeedFeeder)

PROZESSPARAMETER (in ctx["trials"] pro Trial):
  air_pressure [bar]        – Luftdruck am Jet (Haupteinflussgrösse auf FPm)
  speed_shaft2 [m/min]      – Garngeschwindigkeit
  overfeed [%]              – Shaft2x_OF: höher → mehr Garnschwingung → mehr FPm
  tension_before/after_jet  – Garnspannung vor/nach Jet
  heater1_length [mm]       – Länge 1. Heizzone
  heater2_set [°C]          – Solltemperatur 2. Heizzone
  angle_jet_entry/exit [°]  – Garneinlauf/-auslaufwinkel
  housing_name              – Gehäusetyp (nur erwähnen wenn variiert, nicht adlersaugen)

PLY-SPEZIFISCHE PARAMETER (in ctx["yarn"] pro Trial + Ply):
  heater_t1/t2 [°C]         – Temperaturen 1. Heizzone
  dy_value                  – DY-Wert
  shaft1_dr                 – Streckungsverhältnis Shaft 1
  twist_direction           – Drallrichtung (S/Z)
  disc_configuration        – Scheibenaufbau
  overfeed_feeder [%]       – Feeder-Overfeed

JET-GEOMETRIE (tblJets) — Erklärende Variable, nicht Zielgrösse:
  Luftbohrung [mm]        – Diameter Luftbohrung (Klein → kompakte Knoten)
  AnzahlLuftbohrungen     – Anzahl Luftbohrungen
  WinkelLuftbohrung [°]   – Winkel Luftbohrung zum Garnkanal
  GarnkanalBreite [mm]    – Breite Garnkanal
  GarnkanalTiefe [mm]     – Tiefe Garnkanal
  GarnkanalRadius [mm]
  GarnkanalLängeEingang/Ausgang [mm]
  WirbelkammerBreite [mm], WirbelkammerRadius [mm], WirbelkammerKreissehne [mm]
  AbstandSchlitzEingang/Ausgang [mm], SchlitzbreiteEingang/Ausgang [mm]
  WinkelKonusI/II [°], RadiusKonus [mm], Konuslänge [mm]
  TiterVon / TiterBis / IdealTiter [dtex]
  Werkstoff → tblWerkstoff, Prozess → tblProzesse (DTY/ATY/...)

MESSWERTE — Zielgrössen (alle via TrialID):
  tbllaboritematlab  : FPm [IP/m], FPmCV [%], Tension [cN/dtex], Stability [%]
                       (Referenzgerät: ITEMAT Lab TSI)
  tbllaboritematplus : FPm, FPmCV, Tension, Stability, OLX, OLS, KLX, KLS
                       (Gerät: Textechno ITEMAT+ Lab TSI)
  tbllaborstatimatds : Elongation [%], ElongationCV, Tenacity [cN/dtex], TenacityCV
                       (Statimat DS – Einzelmessungen)
  tbllaborstatimatm  : Elongation, ElongationCV, Tenacity, TenacityCV
                       (Statimat M – Mittelwerte)
  tbllabortiter      : Titer [dtex]
  tbllaborrapid600   : SPD, AvgSPD, StdDevSPD (Lenzing RAPID 600 V)
  tbllabordtyomat    : FPm, CV_FP, AvgKL, AvgOL, AKnots, BKnots, CKnots,
                       Stab_03/06/10/13 (gemessen),
                       Stab_03/06/10/13_model (XGBoost ML-Prognose)

FALLBACK-LOGIK:
  itematlab fehlt → itematplus verwenden
  statimatds fehlt → statimatm verwenden

GARNDATEN (tblYarn via tbltrialsettings.YarnID):
  Name, Titer [dtex], NumberOfFilaments, dpf

SPANNUNGSSTUFEN: 0.3 / 0.6 / 1.0 / 1.3 cN/dtex
  → Jede Tension-Stufe = eigene FPm/Stability-Messung
  → 0.3 cN/dtex: sensitiv, zeigt schwache Knoten
  → 1.0 cN/dtex: Standard-Prüfbedingung
  → 1.3 cN/dtex: streng, nur stabile Knoten zählen
  → Steiler Abfall von 0.3→1.3 = schlechte Knotenqualität

REQUIREMENTSET / QUICKSCAN:
  tblRequirementSet → tblRequirementRule → tblRequirementField
  tblRequirementEvaluation → tblRequirementEvaluationDetail
  rule_type: must (K.O.) / weighted (0-100%) / distance / filter
  tblRequirementField: source_table_primary/fallback, source_column, tension_filter

═══════════════════════════════════════════════════════════════
DTY-FACHDOMÄNE
═══════════════════════════════════════════════════════════════

- FPm [IP/m]: Intermingling Points per Meter. Typisch 60–120. Mehr = gleichmässiger.
- FPmCV [%]: Variationskoeffizient. Tiefer = gleichmässigere Knotenverteilung.
- Stability [%]: Knotenbeständigkeit. Gemessen bei 0.3/0.6/1.0/1.3 cN/dtex.
  Bei 1.3 cN/dtex am schwierigsten (Knoten reissen leichter auf).
- Luftbohrung: Klein → kompakte, stabile Knoten; zu klein → Garnschädigung.
- AirPressure [bar]: Höher → mehr FPm, aber ab Grenzwert Stabilitätsverlust.
- Overfeed (Shaft2x_OF [%]): Höher → mehr Garnschwingung → mehr FPm.
- YarnScope: Optische Dickenmessung alle 0.25mm. Otsu-Schwellwert für IP-Detektion.
  AKnots = gut definierte, BKnots = mittel, CKnots = schwach.
- ML-Modelle XGBoost: Stab_03/06/10/13_model. Systematische Unterschätzung
  bei 1.3 cN/dtex bekannt und dokumentiert.

Language: answer in the language the user writes in (German question -> German answer, Spanish -> Spanish, ...). If there is no question (e.g. an automatic analysis) or it is unclear, answer in English. Fachbegriffe verwenden."""

# Start of the language rule above - lab_assistant_worker cuts the DTY domain
# knowledge out of ADVISOR_SYSTEM_PROMPT up to this marker (Nutzerwunsch
# 2026-10-16: answer in the user's language, default English).
LANGUAGE_RULE_MARKER = "Language: answer in the language"


# ---------------------------------------------------------------------------
# Kontext-Sammler
# ---------------------------------------------------------------------------

def collect_advisor_context(series_pk: int, trial_ids: list, experiment_id_txt: str) -> dict:
    """Sammelt alle relevanten Daten für den agentT aus der DB."""
    ctx: dict = {
        "series_id":     series_pk,
        "experiment_id": experiment_id_txt,
    }

    if not trial_ids:
        ctx["trials"] = []
        return ctx

    placeholders = ",".join(["%s"] * len(trial_ids))

    # 1. Trials + Jet-Geometrie + Prozessparameter + Housing
    ctx["trials"] = fetch_all(
        f"""
        SELECT
            t.ID                    AS trial_id,
            t.Versuchsnummer        AS trial_nr,
            t.JetID                 AS jet_id,
            j.Jet                   AS jet_name,
            j.Luftbohrung           AS luftbohrung,
            j.WinkelLuftbohrung     AS winkel_luftbohrung,
            j.GarnkanalBreite       AS garnkanal_breite,
            j.GarnkanalTiefe        AS garnkanal_tiefe,
            j.GarnkanalRadius       AS garnkanal_radius,
            j.WirbelkammerBreite    AS wirbelkammer_breite,
            j.WirbelkammerRadius    AS wirbelkammer_radius,
            j.Luftverbrauch         AS luftverbrauch,
            j.Entwicklungsname      AS entwicklungsname,
            j.Prototypenname        AS prototypenname,
            j.TiterVon              AS titer_von,
            j.TiterBis              AS titer_bis,
            t.AirPressure           AS air_pressure,
            t.SpeedShaft2           AS speed_shaft2,
            t.Shaft2x_OF            AS overfeed,
            t.YarnTensionBeforeJet  AS tension_before_jet,
            t.YarnTensionAfterJet   AS tension_after_jet,
            t.`1stHeaterLength`     AS heater1_length,
            t.`2ndHeaterSET`        AS heater2_set,
            t.`2ndHeaterLength`     AS heater2_length,
            t.AngleJetEntry         AS angle_jet_entry,
            t.AngleJetExit          AS angle_jet_exit,
            h.HousingName           AS housing_name
        FROM tbltrial t
        LEFT JOIN tbljets j ON j.ID = t.JetID
        LEFT JOIN tblhousing h ON h.ID = t.HousingID
        WHERE t.ID IN ({placeholders})
        ORDER BY t.Versuchsnummer
        """,
        trial_ids,
    )

    # 2. Itemat Lab
    ctx["itemat_lab"] = fetch_all(
        f"""
        SELECT TrialID, Tension, FPm, FPmCV, Stability
        FROM tbllaboritematlab
        WHERE TrialID IN ({placeholders})
        ORDER BY TrialID, Tension
        """,
        trial_ids,
    )

    # 3. Itemat Plus Fallback
    ctx["itemat_plus"] = fetch_all(
        f"""
        SELECT TrialID, Tension, FPm, FPmCV, Stability, OLX, KLX
        FROM tbllaboritematplus
        WHERE TrialID IN ({placeholders})
        ORDER BY TrialID, Tension
        """,
        trial_ids,
    )

    # 4. YarnScope / DTYoMat
    ctx["yarnscope"] = fetch_all(
        f"""
        SELECT
            TrialID, FPm, CV_FP, AvgKL, AvgOL,
            AKnots, BKnots, CKnots,
            Stab_03, Stab_06, Stab_10, Stab_13,
            Stab_03_model, Stab_06_model, Stab_10_model, Stab_13_model
        FROM tbllabordtyomat
        WHERE TrialID IN ({placeholders})
        ORDER BY TrialID
        """,
        trial_ids,
    )

    # 5. Statimat DS (+ Fallback M)
    statimat_rows = fetch_all(
        f"""
        SELECT TrialID, Tenacity, TenacityCV, Elongation, ElongationCV
        FROM tbllaborstatimatds
        WHERE TrialID IN ({placeholders})
        ORDER BY TrialID
        """,
        trial_ids,
    )
    ctx["statimat_ds"] = statimat_rows
    ctx["statimat_m"]  = (
        fetch_all(
            f"""
            SELECT TrialID, Tenacity, TenacityCV, Elongation, ElongationCV
            FROM tbllaborstatimatm
            WHERE TrialID IN ({placeholders})
            ORDER BY TrialID
            """,
            trial_ids,
        )
        if not statimat_rows else []
    )

    # 6. Garn-Infos pro Ply (via tbltrialsettings, direkt per TrialID)
    ctx["yarn"] = fetch_all(
        f"""
        SELECT
            ts.TrialID              AS trial_id,
            ts.Ply                  AS ply,
            y.Name                  AS yarn_name,
            y.Titer                 AS titer,
            y.NumberOfFilaments     AS filamente,
            y.dpf                   AS dpf,
            ts.`1stHeaterT1`        AS heater_t1,
            ts.`1stHeaterT2`        AS heater_t2,
            ts.DYValue              AS dy_value,
            ts.Shaft1_DR            AS shaft1_dr,
            ts.TwistDirection       AS twist_direction,
            ts.DiscConfiguration    AS disc_configuration,
            ts.OverfeedFeeder       AS overfeed_feeder
        FROM tbltrialsettings ts
        JOIN tblyarn y ON y.ID = ts.YarnID
        WHERE ts.TrialID IN ({placeholders})
          AND ts.YarnID IS NOT NULL
        ORDER BY ts.TrialID, ts.Ply
        """,
        trial_ids,
    )

    # 7. Ruleset-Evaluationen
    eval_rows = fetch_all(
        """
        SELECT
            e.eval_id, e.snapshot_label, e.eval_date,
            e.overall_score, e.must_passed, e.status,
            s.set_name, s.description AS set_description
        FROM tblrequirementevaluation e
        JOIN tblrequirementset s ON s.set_id = e.set_id
        WHERE e.experiment_id = %s
        ORDER BY e.eval_date DESC
        LIMIT 3
        """,
        [series_pk],
    )
    ctx["ruleset_evaluations"] = eval_rows

    ctx["ruleset_detail"] = (
        fetch_all(
            """
            SELECT
                d.trial_id, d.actual_value, d.rule_result,
                d.score_contribution, d.distance_to_goal,
                r.rule_type, r.operator, r.target_value,
                r.min_value, r.max_value, r.weight,
                f.field_label, f.unit, f.tension_filter
            FROM tblrequirementevaluationdetail d
            JOIN tblrequirementrule r ON r.rule_id = d.rule_id
            JOIN tblrequirementfield f ON f.field_id = r.field_id
            WHERE d.eval_id = %s
            ORDER BY d.trial_id, r.rule_type, f.sort_order
            """,
            [eval_rows[0]["eval_id"]],
        )
        if eval_rows else []
    )

    return ctx


# ---------------------------------------------------------------------------
# Lab-Daten Helfer (wird auch von screen_quick_scan._build_qs_advisor_context
# importiert)
# ---------------------------------------------------------------------------

def _fetch_lab_results(trial_ids: list) -> dict:
    """Holt alle relevanten Laborergebnisse für eine Liste von Trial-IDs.

    Rückgabe:
    {
      trial_id: {
        "itemat":      [{"tension": 1.0, "FPm": 82.3, "FPmCV": 12.1,
                         "Stability": 68.4, "OLX": 5.2, "OLS": 3.1,
                         "KLX": 2.8, "KLS": 1.9}, ...],
        "statimat_m":  {"Tenacity": 38.2, "TenacityCV": 3.1, ...} | None,
        "statimat_ds": {"Tenacity": 37.9, ...} | None,
        "titer":       83.1 | None,
      }
    }
    Fehlende Tabellen werden still ignoriert.
    """
    if not trial_ids:
        return {}

    result: dict = {tid: {
        "itemat":      [],
        "statimat_m":  None,
        "statimat_ds": None,
        "titer":       None,
    } for tid in trial_ids}

    id_list = ",".join(["%s"] * len(trial_ids))

    # ── Itemat+ (bevorzugt, hat OLX/OLS/KLX/KLS), dann Itemat Lab ──────────
    for tbl in ("tbllaboritematplus", "tbllaboritematlab"):
        try:
            rows = fetch_all(
                f"""
                SELECT TrialID, Tension,
                       FPm, FPmCV, Stability,
                       OLX, OLS, KLX, KLS
                FROM   `{tbl}`
                WHERE  TrialID IN ({id_list})
                ORDER  BY TrialID, Tension
                """,
                trial_ids,
            )
        except Exception:
            rows = []

        for row in rows:
            tid = row.get("TrialID")
            if tid not in result:
                continue
            existing_tensions = {e["tension"] for e in result[tid]["itemat"]}
            t = float(row["Tension"]) if row.get("Tension") is not None else None
            if t not in existing_tensions:
                result[tid]["itemat"].append({
                    "tension":   t,
                    "FPm":       float(row["FPm"])        if row.get("FPm")       is not None else None,
                    "FPmCV":     float(row["FPmCV"])      if row.get("FPmCV")     is not None else None,
                    "Stability": float(row["Stability"])  if row.get("Stability") is not None else None,
                    "OLX":       float(row["OLX"])        if row.get("OLX")       is not None else None,
                    "OLS":       float(row["OLS"])        if row.get("OLS")       is not None else None,
                    "KLX":       float(row["KLX"])        if row.get("KLX")       is not None else None,
                    "KLS":       float(row["KLS"])        if row.get("KLS")       is not None else None,
                })

    # ── Statimat M ──────────────────────────────────────────────────────────
    for tbl in ("tbllaborstatimatm", "tblLaborStatimat", "tbllaborstatimat"):
        try:
            rows = fetch_all(
                f"""
                SELECT TrialID, Tenacity, TenacityCV, Elongation, ElongationCV
                FROM   `{tbl}`
                WHERE  TrialID IN ({id_list})
                """,
                trial_ids,
            )
        except Exception:
            rows = []

        for row in rows:
            tid = row.get("TrialID")
            if tid in result and result[tid]["statimat_m"] is None:
                result[tid]["statimat_m"] = {
                    "Tenacity":     float(row["Tenacity"])     if row.get("Tenacity")     is not None else None,
                    "TenacityCV":   float(row["TenacityCV"])   if row.get("TenacityCV")   is not None else None,
                    "Elongation":   float(row["Elongation"])   if row.get("Elongation")   is not None else None,
                    "ElongationCV": float(row["ElongationCV"]) if row.get("ElongationCV") is not None else None,
                }
        if any(result[tid]["statimat_m"] is not None for tid in result):
            break

    # ── Statimat DS ─────────────────────────────────────────────────────────
    for tbl in ("tbllaborstatimatds", "tblLaborStatimatDS"):
        try:
            rows = fetch_all(
                f"""
                SELECT TrialID, Tenacity, TenacityCV, Elongation, ElongationCV
                FROM   `{tbl}`
                WHERE  TrialID IN ({id_list})
                """,
                trial_ids,
            )
        except Exception:
            rows = []

        for row in rows:
            tid = row.get("TrialID")
            if tid in result and result[tid]["statimat_ds"] is None:
                result[tid]["statimat_ds"] = {
                    "Tenacity":     float(row["Tenacity"])     if row.get("Tenacity")     is not None else None,
                    "TenacityCV":   float(row["TenacityCV"])   if row.get("TenacityCV")   is not None else None,
                    "Elongation":   float(row["Elongation"])   if row.get("Elongation")   is not None else None,
                    "ElongationCV": float(row["ElongationCV"]) if row.get("ElongationCV") is not None else None,
                }
        if any(result[tid]["statimat_ds"] is not None for tid in result):
            break

    # ── Titer ────────────────────────────────────────────────────────────────
    for tbl in ("tbllabortiter", "tbltiter", "tblLaborTiter"):
        try:
            rows = fetch_all(
                f"""
                SELECT TrialID, Titer
                FROM   `{tbl}`
                WHERE  TrialID IN ({id_list})
                """,
                trial_ids,
            )
        except Exception:
            rows = []

        for row in rows:
            tid = row.get("TrialID")
            if tid in result and result[tid]["titer"] is None:
                result[tid]["titer"] = float(row["Titer"]) if row.get("Titer") is not None else None
        if any(result[tid]["titer"] is not None for tid in result):
            break

    return result


# ---------------------------------------------------------------------------
# Worker Thread
# ---------------------------------------------------------------------------

class AdvisorWorker(QThread):
    """Non-blocking QThread für den Anthropic API-Call.

    Modi:
      user_question=None  → Erster Call, vollständiger Report
      user_question=str   → Folgefrage, nutzt history für Kontext
    """

    result_ready   = Signal(str)
    error_occurred = Signal(str)

    def __init__(
        self,
        series_pk: int,
        trial_ids: list,
        experiment_id_txt: str,
        api_key: str,
        history: Optional[list] = None,
        user_question: Optional[str] = None,
    ):
        super().__init__()
        self._series_pk         = series_pk
        self._trial_ids         = trial_ids
        self._experiment_id_txt = experiment_id_txt
        self._api_key           = api_key
        self._history           = list(history) if history else []
        self._user_question     = user_question

    def run(self):
        try:
            ctx      = collect_advisor_context(
                self._series_pk, self._trial_ids, self._experiment_id_txt
            )
            ctx_json = json.dumps(ctx, ensure_ascii=False, indent=2, default=str)

            if self._user_question is None:
                # Erster Call: vollständiger Report
                messages = [{
                    "role":    "user",
                    "content": (
                        "Analyse this TrialSeries and create the full report:\n\n"
                        + ctx_json
                    ),
                }]
            else:
                # Folgefrage: kompakter Kontext-Header + History + Frage
                has_itemat  = bool(ctx.get("itemat_lab") or ctx.get("itemat_plus"))
                has_scope   = bool(ctx.get("yarnscope"))
                yarn_plies  = len(ctx.get("yarn", []))
                n_trials    = len(ctx.get("trials", []))
                ctx_header = (
                    f"[Kontext: Series {self._experiment_id_txt}, "
                    f"{n_trials} Trials, "
                    f"Itemat: {'vorhanden' if has_itemat else 'fehlt'}, "
                    f"YarnScope: {'vorhanden' if has_scope else 'fehlt'}, "
                    f"Ply entries: {yarn_plies}]"
                )
                messages = list(self._history) + [{
                    "role":    "user",
                    "content": f"{ctx_header}\n\n{self._user_question}",
                }]

            payload = json.dumps({
                "model":       "claude-sonnet-5",
                "max_tokens":  128000,
                "system":      ADVISOR_SYSTEM_PROMPT,
                "messages":    messages,
            }).encode("utf-8")

            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=payload,
                headers={
                    "Content-Type":      "application/json",
                    "x-api-key":         self._api_key,
                    "anthropic-version": "2023-06-01",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=300) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            usage = result.get("usage", {})
            update_token_usage(
                usage.get("input_tokens", 0),
                usage.get("output_tokens", 0),
            )

            text = "\n".join(
                block.get("text", "")
                for block in result.get("content", [])
                if block.get("type") == "text"
            ).strip()

            if not text:
                self.error_occurred.emit("Keine Antwort vom Modell erhalten.")
                return

            self.result_ready.emit(text)

        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8")
            except Exception:
                pass
            self.error_occurred.emit(f"HTTP {e.code}: {e.reason}\n\n{body}")

        except urllib.error.URLError as e:
            self.error_occurred.emit(
                f"Netzwerkfehler: {e.reason}\n\n"
                "Check whether a connection to api.anthropic.com is possible."
            )

        except Exception as e:
            self.error_occurred.emit(f"Something unexpected went wrong:\n{type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Eulen-Animation Widget (unverändert)
# ---------------------------------------------------------------------------
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import QTimer


class OwlAnimationWidget(QLabel):
    _SLEEP_FRAMES = ["🦉  z z z", "🦉   z z z", "🦉    z z z", "🦉     Z z z"]
    _FLY_FRAMES   = [
        "  🦉 ～～～  📡", "   🦉～～～  📡", "    🦉～～  📡",
        "     🦉～  📡",  "      🦉  📡",    "     🦉～  📡",
        "    🦉～～  📡", "   🦉～～～  📡",  "  🦉 ～～～  📡",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._frame   = 0
        self._working = False
        self._timer   = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.setStyleSheet("font-size: 13px; color: #9ca3af; padding: 2px 0;")
        self.setText(self._SLEEP_FRAMES[0])
        self._timer.start(600)

    def set_working(self, working: bool):
        self._working = working
        self._frame   = 0

    def _tick(self):
        frames = self._FLY_FRAMES if self._working else self._SLEEP_FRAMES
        self.setText(frames[self._frame % len(frames)])
        self._frame += 1