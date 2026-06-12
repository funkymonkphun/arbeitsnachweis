# Arbeitsnachweis Tonabteilung

Ein Desktop-Programm zur Erfassung und Verwaltung von Arbeitszeiten mit PDF-Export und automatischem Dienstplan-Import. Verfügbar als `.app` (macOS) und `.exe` (Windows).

---

## Inhalt

1. [Installation & Start](#installation--start)
2. [Oberfläche im Überblick](#oberfläche-im-überblick)
3. [Mitarbeiterverwaltung](#mitarbeiterverwaltung)
4. [Arbeitszeiterfassung](#arbeitszeiterfassung)
5. [Automatische Berechnungen](#automatische-berechnungen)
6. [Urlaub eintragen](#urlaub-eintragen)
7. [Feiertagserkennung](#feiertagserkennung)
8. [Zeitraster umschalten](#zeitraster-umschalten)
9. [Dienstplan importieren](#dienstplan-importieren)
10. [Monat wechseln](#monat-wechseln)
11. [Speichern & Laden](#speichern--laden)
12. [Monat leeren](#monat-leeren)
13. [PDF exportieren](#pdf-exportieren)
14. [Ü.Std-Farbe in der PDF](#überstunden-farbe-in-der-pdf)
15. [Datenpfad ändern](#datenpfad-ändern)
16. [Dark & Light Mode](#dark--light-mode)
17. [Datenspeicherung](#datenspeicherung)

---

## Installation & Start

**Als fertige App (empfohlen)**
Einfach die `.app`-Datei (macOS) bzw. `.exe`-Datei (Windows) starten – keine Installation nötig.

**Als Python-Skript**
Voraussetzungen installieren und starten:
```bash
pip install customtkinter reportlab holidays pdfplumber
python arbeitsnachweis.py
```

---

## Oberfläche im Überblick

Das Fenster ist in drei Bereiche gegliedert:

**Obere Leiste (Zeile 1):** Mitarbeiterauswahl, Jahres- und Monatsauswahl sowie Schaltflächen für Dienstplan-Import, Zeitraster, Ü.Std-Farbe und PDF-Export.

**Obere Leiste (Zeile 2):** Wochenstunden, Arbeitstage, berechnetes Tages-Soll sowie Datenpfad-Anzeige und -Wechsel.

**Hauptbereich:** Scrollbare Tagesliste des gewählten Monats – eine Zeile pro Tag.

**Untere Leiste:** Gesamtsummen für den Monat sowie die Schaltflächen „Fortschritt Speichern" und „Monat leeren".

---

## Mitarbeiterverwaltung

Über den Button **⚙️ Verwaltung** öffnet sich das Mitarbeiter-Fenster.

- **Neues Profil anlegen:** „Profil leeren (Neu)" klicken, Name, Wochenstunden und Arbeitstage/Woche eingeben, dann „Speichern".
- **Profil bearbeiten:** Mitarbeiter in der Liste auswählen, Werte anpassen, „Speichern" klicken.
- **Profil löschen:** Mitarbeiter auswählen und „Löschen" klicken – es erscheint eine Sicherheitsabfrage.

Jeder Mitarbeiter hat zwei Einstellungen:
- **Wochenstunden** – Gesamte Sollstunden pro Woche (z. B. `30`)
- **Arbeitstage/Woche** – Anzahl der Arbeitstage (z. B. `5` oder `6`)

Aus diesen beiden Werten berechnet das Programm automatisch das **Tages-Soll** (`Wochenstunden ÷ Arbeitstage`), das in der oberen Leiste angezeigt wird.

---

## Arbeitszeiterfassung

Jede Zeile entspricht einem Tag des Monats. Die Spalten von links nach rechts:

| Spalte | Bedeutung |
|--------|-----------|
| **Tag** | Tagesnummer (01–31) |
| **Vormittag Von / Bis** | Beginn und Ende der Vormittagsschicht |
| **Nachmittag Von / Bis** | Beginn und Ende der Nachmittagsschicht |
| **Std.ges** | Automatisch berechnete Gesamtstunden des Tages |
| **D.Plan** | Geplante Tagesstunden (wird automatisch aus den Zeiten übernommen, kann aber manuell angepasst werden) |
| **A** | Freitextfeld – z. B. für Abwesenheitsart |
| **H** | Freitextfeld – z. B. für Hinweise |
| **Ü.Std** | Automatisch berechnete Überstunden des Tages |
| **Bemerkung** | Freitextfeld – z. B. für Notizen, wird bei Feiertagen automatisch befüllt |

**Zeitauswahl:** Die Uhrzeitfelder sind Dropdown-Menüs. Alternativ kann die Zeit auch direkt eingetippt werden – das Programm formatiert sie automatisch:
- `8` → `08:00`
- `830` → `08:30`
- `0830` → `08:30`

---

## Automatische Berechnungen

Das Programm berechnet bei jeder Eingabe automatisch:

**Std.ges** = Vormittag (Von–Bis) + Nachmittag (Von–Bis)

**D.Plan** = Wird automatisch auf den Wert von Std.ges gesetzt, sobald Zeiten eingetragen werden. Dieser Wert kann manuell überschrieben werden.

**Ü.Std** = Std.ges − D.Plan (nur wenn positiv, sonst leer)

**Gesamtsummen** (untere Leiste) = Summe über alle Tage des Monats für Std.ges, D.Plan und Ü.Std.

---

## Urlaub eintragen

Jede Zeile hat am rechten Rand einen **„Urlaub"**-Button.

- **Urlaub aktivieren (blau):** D.Plan wird automatisch auf das Tages-Soll gesetzt, Bemerkung wird auf „Urlaub" gesetzt, eingetragene Zeiten werden entfernt. Bei Sonn- und Feiertagen bleibt D.Plan auf `0,00`.
- **Urlaub deaktivieren (grau):** D.Plan wird auf `0,00` zurückgesetzt, der Tag ist wieder normal editierbar.

---

## Feiertagserkennung

Das Programm erkennt automatisch **Feiertage in NRW** sowie **Sonntage**. Fällt ein Tag auf einen Feiertag, wird die Bemerkungsspalte beim Laden des Monats automatisch mit dem Namen des Feiertags befüllt (z. B. „Weihnachtstag").

---

## Zeitraster umschalten

Der Button **„Zeitraster: 30 Min"** wechselt zwischen zwei Abstufungen für die Dropdown-Uhrzeitfelder:

- **30 Minuten:** Auswahlmöglichkeiten in 30-Minuten-Schritten (z. B. 08:00, 08:30, 09:00 …)
- **15 Minuten:** Auswahlmöglichkeiten in 15-Minuten-Schritten (z. B. 08:00, 08:15, 08:30 …)

Bereits eingetragene Werte bleiben beim Wechsel erhalten.

---

## Dienstplan importieren

Mit dem Button **„📋 Dienstplan importieren"** lassen sich Arbeitszeiten direkt aus einem Wochen-Dienstplan im PDF-Format übernehmen – ganz ohne manuelles Abtippen.

**So funktioniert's:**

1. Button klicken und die PDF-Datei des Dienstplans auswählen.
2. Das Programm liest die komplette Tabelle aus und erkennt **alle Mitarbeiterzeilen** der Woche automatisch.
3. Ein Auswahlfenster öffnet sich:
   - **Links:** Liste aller im Dienstplan gefundenen Zeilen (Namen oder „Zeile 1, 2, 3 …", falls kein Name erkannt wurde).
   - **Rechts:** Vorschau der Arbeitszeiten (früh/spät) für die ausgewählte Zeile, Tag für Tag.
4. Die passende Zeile auswählen (unabhängig davon, ob der Name im Dienstplan mit dem Profilnamen übereinstimmt) und auf **„✅ Importieren"** klicken.
5. Die Vormittags- und Nachmittagszeiten werden für die entsprechenden Tage automatisch in die Tabelle übernommen. Std.ges und Ü.Std werden sofort neu berechnet.

**Hinweise:**
- Tage, die als **Urlaub** markiert waren, werden beim Import automatisch wieder auf „normal" umgeschaltet.
- Tage, die **außerhalb des aktuell angezeigten Monats** liegen (z. B. wenn die Woche zwei Monate überspannt), werden übersprungen – am Ende erscheint eine Meldung, welche Tage das waren.
- Voraussetzung ist die Python-Bibliothek `pdfplumber` (`pip install pdfplumber`). Bei fehlender Installation erscheint ein Hinweis.
- Das PDF muss **echten Text** enthalten (kein gescanntes Bild) – die meisten am Computer erstellten Dienstpläne erfüllen das.

---

## Monat wechseln

Über die Dropdown-Menüs **Jahr** und **Monat** kann frei zwischen Zeiträumen gewechselt werden. Beim Wechsel wird der aktuelle Monat automatisch im Arbeitsspeicher gesichert, sodass keine Daten verloren gehen.

Auch beim Wechsel des **Mitarbeiters** werden die Daten des bisherigen Monats gesichert und die Wochenstunden sowie Arbeitstage des neuen Profils automatisch geladen.

---

## Speichern & Laden

**Automatisch:** Beim Monatswechsel oder Mitarbeiterwechsel werden die aktuellen Daten automatisch im Arbeitsspeicher gehalten.

**Manuell speichern:** Der Button **„Fortschritt Speichern"** (unten rechts, blau) schreibt alle Daten dauerhaft in die JSON-Datei auf der Festplatte. Es empfiehlt sich, regelmäßig zu speichern.

**Laden:** Beim Programmstart werden alle vorhandenen Daten automatisch aus der JSON-Datei geladen.

---

## Monat leeren

Der Button **„Monat leeren"** (unten rechts, rot) löscht nach einer Sicherheitsabfrage alle eingetragenen Zeiten des aktuell angezeigten Monats unwiderruflich. Andere Monate und Mitarbeiter bleiben davon unberührt.

---

## PDF exportieren

Der Button **„PDF Exportieren…"** öffnet einen Speicherdialog. Der Dateiname wird automatisch vorgeschlagen (`Arbeitsnachweis_Name_Monat_Jahr.pdf`).

Die exportierte PDF enthält:
- Titel und Kopfzeile mit Name, Monat und Jahr
- Tabelle mit allen Tagen (Tag, Vormittag, Nachmittag, Std.ges, D.Plan, A, H, Ü.Std, Bemerkung)
- Summenzeile am Ende der Tabelle
- Unterschriftenfelder für „aufgestellt", „für die Richtigkeit" und „geprüft"

---

## Überstunden-Farbe in der PDF

Mit dem Button **„🎨 Ü.Std-Farbe (PDF)"** lässt sich die Textfarbe der Ü.Std-Spalte in der exportierten PDF frei wählen. Der native Farbwähler des Betriebssystems öffnet sich. Die gewählte Farbe wird gespeichert und beim nächsten Programmstart automatisch wiederhergestellt.

---

## Datenpfad ändern

Über **„📁 Datenpfad ändern"** (Zeile 2, rechts) kann der Ordner gewählt werden, in dem die Datendateien gespeichert werden. Beim Wechsel werden die aktuellen Daten zunächst am alten Speicherort gesichert, bevor der neue Pfad aktiv wird.

Der gewählte Pfad wird in der Konfigurationsdatei `~/.arbeitsnachweis_config.json` gespeichert und beim nächsten Start automatisch verwendet.

**Standard-Pfadreihenfolge beim ersten Start:**
1. Verzeichnis der `.exe`/`.app` bzw. des Skripts (wenn beschreibbar)
2. `~/Dokumente/Arbeitsnachweis` (automatisch erstellt, falls nötig)

---

## Dark & Light Mode

Das Programm passt sich automatisch dem Erscheinungsbild des Betriebssystems an – Dark Mode und Light Mode werden ohne weitere Einstellungen unterstützt.

---

## Datenspeicherung

Alle Daten werden lokal gespeichert – keine Cloud, keine externe Verbindung.

| Datei | Inhalt |
|-------|--------|
| `arbeitsnachweis_daten.json` | Alle erfassten Arbeitszeiten (alle Mitarbeiter, alle Monate) |
| `mitarbeiter_daten.json` | Mitarbeiterprofile mit Wochenstunden und Arbeitstagen |
| `~/.arbeitsnachweis_config.json` | Einstellungen: Datenpfad, PDF-Ü.Std-Farbe |

Die ersten beiden Dateien liegen im eingestellten Datenpfad. Die Konfigurationsdatei liegt immer im Home-Verzeichnis des Nutzers.
