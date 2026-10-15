"""export_dty_jet_training_data.py

Exportiert eine Trainings-CSV für den geplanten DTY-Jet-Empfehler (siehe
CLAUDE.md, Konzept-Diskussion 2026-08-25): eine Zeile pro DTY-Trial mit
Düsengeometrie + Prozessparametern (+ optional Garn-Merkmalen) als Features,
und FPm/FPmCV (Tension=0.0) sowie Stability@0.3/0.6/1.0/1.3 als Zielspalten-
KANDIDATEN. Bewusst KEIN Leakage-Schutz zwischen den 6 Zielspalten eingebaut
(welche Spalten für welches Zielmodell gedroppt werden, entscheidet der
Nutzer selbst im ModelCreator, siehe core/data_io.py::split_xy()'s
base_drop-Liste dort) - diese CSV liefert nur die Rohdaten, ein Zielmodell
pro Spalte trainiert der ModelCreator separat (train_compare_and_package(),
ein Call pro target).

WICHTIG - ConditionGroup statt TrialID als group_col (2026-08-25, Nutzer-
Hinweis: "oft mache ich 3 identische Versuche mit 3 verschiedenen
physischen Plättchen. eigentlich sind dann alle gleich"): TrialID-Grouping
(ModelCreators Default) verhindert nur, dass EIN Trial gleichzeitig in
Train- und Test-Split landet - schützt aber NICHT davor, dass zwei
VERSCHIEDENE Trials mit identischer Jet+Prozess+Garn-Kombination (= nahezu
identischer Feature-Zeile) auf verschiedene Seiten des Splits fallen. Per
echter Datenprobe verifiziert, nicht angenommen: von 10'921 DTY-Trials gibt
es nur 3'971 wirklich unterschiedliche (Jet, AirPressure, Overfeed,
SpeedShaft2, YarnID)-Kombinationen - Gruppengrösse 3 (exakt das
beschriebene Plättchen-Muster) ist mit 1'732 Gruppen die häufigste, manche
Kombinationen (offenbar wiederkehrende Referenzbedingungen) kommen bis zu
81-mal vor. 90% aller Trials haben mindestens einen "Zwilling" - mit
TrialID-Grouping würde ein Modell beim Testen also ständig auf Bedingungen
treffen, die es unter einer anderen TrialID bereits gesehen hat, und die
Generalisierungs-Güte würde massiv überschätzt. Fix: neue Spalte
`ConditionGroup` (Text-Konkatenation aus JetID|AirPressure|Overfeed|
SpeedShaft2|YarnID) - im ModelCreator als group_col statt TrialID verwenden.
`ConditionGroupSize` zeigt zur Kontrolle direkt in der CSV, wie viele Trials
zu derselben Gruppe gehören.

Spalten-Gruppen (siehe Header-Kommentar-Zeile in der CSV selbst nicht - nur
hier dokumentiert):
  - Kontext/ID  : TrialID, Versuchsnummer, SeriesName, ExperimentIDTxt, JetID,
                  JetName (nur zur Nachvollziehbarkeit, NICHT als Feature
                  gedacht - rohe IDs haben keine sinnvolle numerische Bedeutung)
  - Grouping    : ConditionGroup (als group_col im ModelCreator verwenden,
                  NICHT TrialID - siehe Docstring oben), ConditionGroupSize
  - Prozess     : AirPressure, SpeedShaft2, Overfeed
  - Jet-Geometrie (bewährter Kern, identisch zu
                  ui/yarnscope/dty_analysis.py::_fetch_trial_process_and_jet_features(),
                  dem Feature-Set der bereits produktiven Stab_*-Modelle)
  - Jet-Geometrie (Ergänzung, im alten Feature-Set gefehlt): YarnChannelShape,
                  Kreisbogen, SchanzeEingang
  - Garn        : YarnTiter/YarnFilaments/YarnDpf/YarnMaterial/YarnGarntyp -
                  vom ERSTEN Ply (tbltrialsettings.Ply = 'Ply 1', Textspalte,
                  kein Integer - verifiziert per echter Datenprobe) des
                  Trials, bei Mehrfach-Ply-Trials also nicht vollständig -
                  bekannte Vereinfachung.
  - Targets     : FPm_00, FPmCV_00, Stability_03, Stability_06, Stability_10,
                  Stability_13 - NICHT jede Zeile hat alle 6 (Messabdeckung
                  unterscheidet sich je Tension-Stufe, siehe CLAUDE.md).

Scope: nur Trials auf DTY-Maschinen (tblmaschinentypen.Maschinentyp IN
('DTY','DT/DW'), gleiche Konvention wie an anderen Stellen im Projekt, siehe
CLAUDE.md) mit zugewiesenem Jet UND mindestens einem der 6 Zielwerte.

Nutzung:
    TRIPPLET_MODE=dev_local python export_dty_jet_training_data.py --out dty_jet_training_data.csv
"""
from __future__ import annotations

import argparse
import csv


_SQL = """
SELECT
    t.ID                        AS TrialID,
    t.Versuchsnummer            AS Versuchsnummer,
    ts.SeriesName                AS SeriesName,
    e.ExperimentID                AS ExperimentIDTxt,
    t.JetID                     AS JetID,
    j.Jet                        AS JetName,

    -- Grouping fuer Leakage-sicheres CV (siehe Moduldocstring) - ALS group_col
    -- im ModelCreator verwenden, NICHT TrialID.
    CONCAT_WS('|', t.JetID, t.AirPressure, t.Shaft2x_OF, t.SpeedShaft2, tset.YarnID) AS ConditionGroup,
    COUNT(*) OVER (
        PARTITION BY t.JetID, t.AirPressure, t.Shaft2x_OF, t.SpeedShaft2, tset.YarnID
    )                            AS ConditionGroupSize,

    -- Prozessparameter
    t.AirPressure                AS AirPressure,
    t.SpeedShaft2                AS SpeedShaft2,
    t.Shaft2x_OF                AS Overfeed,

    -- Jet-Geometrie (bewaehrter Kern, identisch zu
    -- _fetch_trial_process_and_jet_features() in ui/yarnscope/dty_analysis.py)
    j.Luftbohrung                AS Luftbohrung,
    j.AnzahlLuftbohrungen        AS AnzahlLuftbohrungen,
    j.WinkelLuftbohrung        AS WinkelLuftbohrung,
    acs.AirChannelShape            AS Luftkanalform,
    j.GarnkanalBreite            AS GarnkanalBreite,
    j.GarnkanalTiefe            AS GarnkanalTiefe,
    j.GarnkanalRadius            AS GarnkanalRadius,
    j.GarnkanalLängeEingang        AS GarnkanalLaengeEingang,
    j.GarnkanalLängeAusgang        AS GarnkanalLaengeAusgang,
    wk.Wirbelkammer                AS Wirbelkammer,
    j.WirbelkammerBreite        AS WirbelkammerBreite,
    j.WirbelkammerRadius        AS WirbelkammerRadius,
    j.WirbelkammerKreissehne    AS WirbelkammerKreissehne,
    j.GebogenerKanal            AS GebogenerKanal,
    j.WinkelKonusI                AS WinkelKonusI,
    j.WinkelKonusII                AS WinkelKonusII,
    j.RadiusKonus                AS RadiusKonus,
    j.AbstandLBKonus            AS AbstandLBKonus,
    j.AbstandEinlaufKonusZuLB    AS AbstandEinlaufKonusZuLB,
    j.Konuslänge                AS Konuslaenge,
    j.LängeDK                    AS LaengeDK,
    kf.KonusForm                AS KonusForm,
    j.AbstandSchlitzEingang        AS AbstandSchlitzEingang,
    j.AbstandSchlitzAusgang        AS AbstandSchlitzAusgang,
    j.SchlitzbreiteEingang        AS SchlitzbreiteEingang,
    j.SchlitzbreiteAusgang        AS SchlitzbreiteAusgang,
    j.Luftverbrauch                AS Luftverbrauch,

    -- Jet-Geometrie (Ergaenzung, fehlte im alten Feature-Set)
    ycs.Shape                    AS YarnChannelShape,
    j.Kreisbogen                AS Kreisbogen,
    j.SchanzeEingang            AS SchanzeEingang,

    -- Garn (Ply 1, siehe Docstring)
    y.Titer                        AS YarnTiter,
    y.NumberOfFilaments            AS YarnFilaments,
    y.dpf                        AS YarnDpf,
    mat.Material                AS YarnMaterial,
    gt.Garntyp                    AS YarnGarntyp,

    -- Targets (Kandidaten - je EINE eigene Modell-Trainingsrunde im ModelCreator)
    fpm.FPm_00                    AS FPm_00,
    fpm.FPmCV_00                AS FPmCV_00,
    stab.Stability_03            AS Stability_03,
    stab.Stability_06            AS Stability_06,
    stab.Stability_10            AS Stability_10,
    stab.Stability_13            AS Stability_13

FROM tbltrial t
JOIN tbltrialseries ts    ON ts.ID = t.TrialSeriesID
JOIN tblmaschine m         ON m.ID = ts.MachineID
JOIN tblmaschinentypen mt ON mt.ID = m.Maschinentyp
JOIN tblexperimente e     ON e.ID = ts.ExperimentID
JOIN tbljets j             ON j.ID = t.JetID
LEFT JOIN tblairchannelshape acs ON acs.ID = j.Luftkanalform
LEFT JOIN tblwirbelkammer wk    ON wk.ID = j.Wirbelkammer
LEFT JOIN tblkonusform kf        ON kf.ID = j.KonusForm
LEFT JOIN tblyarnchannelshape ycs ON ycs.ID = j.YarnChannelShape
LEFT JOIN tbltrialsettings tset ON tset.TrialID = t.ID AND tset.Ply = 'Ply 1'
LEFT JOIN tblyarn y             ON y.ID = tset.YarnID
LEFT JOIN tblmaterial mat        ON mat.ID = y.Material
LEFT JOIN tblgarntyp gt        ON gt.ID = y.Garntyp
LEFT JOIN (
    SELECT TrialID, AVG(FPm) AS FPm_00, AVG(FPmCV) AS FPmCV_00
    FROM tbllaboritematlab
    WHERE Tension = 0.0
    GROUP BY TrialID
) fpm ON fpm.TrialID = t.ID
LEFT JOIN (
    SELECT
        TrialID,
        AVG(CASE WHEN Tension = 0.3 THEN Stability END) AS Stability_03,
        AVG(CASE WHEN Tension = 0.6 THEN Stability END) AS Stability_06,
        AVG(CASE WHEN Tension = 1.0 THEN Stability END) AS Stability_10,
        AVG(CASE WHEN Tension = 1.3 THEN Stability END) AS Stability_13
    FROM tbllaboritematlab
    WHERE Tension IN (0.3, 0.6, 1.0, 1.3)
    GROUP BY TrialID
) stab ON stab.TrialID = t.ID

WHERE mt.Maschinentyp IN ('DTY', 'DT/DW')
  AND t.JetID IS NOT NULL
  -- Reference samples (customer originals, db/trial_reference.py) are not
  -- our trials - unknown/estimated settings would only add noise.
  AND {ref_filter}
  AND (
        fpm.FPm_00 IS NOT NULL OR fpm.FPmCV_00 IS NOT NULL
        OR stab.Stability_03 IS NOT NULL OR stab.Stability_06 IS NOT NULL
        OR stab.Stability_10 IS NOT NULL OR stab.Stability_13 IS NOT NULL
      )
ORDER BY t.ID
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="dty_jet_training_data.csv", help="Pfad der Ausgabe-CSV")
    args = parser.parse_args()

    from db.connection import fetch_all
    from db.trial_reference import exclude_references_sql
    rows = fetch_all(_SQL.replace("{ref_filter}", exclude_references_sql("t")), [])

    if not rows:
        print("Keine Zeilen gefunden.")
        return

    fieldnames = list(rows[0].keys())
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    n_with_fpm = sum(1 for r in rows if r.get("FPm_00") is not None)
    n_with_s03 = sum(1 for r in rows if r.get("Stability_03") is not None)
    n_with_s06 = sum(1 for r in rows if r.get("Stability_06") is not None)
    n_with_s10 = sum(1 for r in rows if r.get("Stability_10") is not None)
    n_with_s13 = sum(1 for r in rows if r.get("Stability_13") is not None)
    n_distinct_jets = len({r.get("JetID") for r in rows if r.get("JetID") is not None})
    n_distinct_groups = len({r.get("ConditionGroup") for r in rows if r.get("ConditionGroup")})

    print(f"{len(rows)} Zeilen exportiert nach {args.out}")
    print(f"  distinct Jets: {n_distinct_jets}")
    print(f"  distinct ConditionGroups: {n_distinct_groups}  "
          f"(group_col fuers ModelCreator-Training - NICHT TrialID, siehe Moduldocstring)")
    print(f"  FPm_00: {n_with_fpm}  Stability_03: {n_with_s03}  Stability_06: {n_with_s06}  "
          f"Stability_10: {n_with_s10}  Stability_13: {n_with_s13}")


if __name__ == "__main__":
    main()
