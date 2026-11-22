# WaveTB

Selbstprüfende VHDL-Testbenches aus gezeichneten Wellenformen – lokal, ohne Online-Tool.

[Lizenz: MIT](LICENSE) · Repository: https://github.com/KiJo-EE/VHDL-Testbench-Generator

Du beschreibst das erwartete Verhalten deines Moduls als Wellenform (WaveDrom-Format, live gerendert in einer
Web-GUI). WaveTB erzeugt daraus die Testbench, simuliert mit **GHDL** und öffnet das Ergebnis in **Surfer**.
Optional wird eine **VUnit**-Testbench samt `run_vunit.py` erzeugt. Python-Standardbibliothek genügt, es gibt nichts
zu installieren.

Die Struktur der Testbenches und das Wellenform-Format orientieren sich am
[Online-Generator von ITDev](https://www.itdev.co.uk/content/vhdl-testbench-generator-example); Wellenform-Dateien
aus diesem Tool laufen unverändert weiter. WaveTB ist ein unabhängiges Projekt ohne Verbindung zu ITDev
und enthält keinen Code von dort.

## Voraussetzungen

| Programm | wofür | Pflicht |
|---|---|---|
| Python 3.10+ | WaveTB selbst (nur Standardbibliothek, nichts zu installieren) | ja |
| GHDL (im `PATH`) | Simulation, VHDL-2008 | ja |
| Surfer (im `PATH`, oder `surfer` in `wavetb.json` bzw. Umgebungsvariable `SURFER`) | Wellenform-Anzeige | für „+ Surfer" |
| VUnit (`pip install vunit_hdl`) | nur im Modus `vunit` | optional |

## Installation

```bash
git clone https://github.com/KiJo-EE/VHDL-Testbench-Generator.git
cd VHDL-Testbench-Generator
```

Mehr ist nicht nötig, solange Python und GHDL (siehe oben) installiert sind.

## Schnellstart

```bash
python . gui examples/axis_pipe_stage
```

(im Repository-Ordner; öffnet den Browser auf einem lokalen Port). Dort **Simulieren + Surfer** klicken – das
Beispiel ist ein einfacher AXI-Stream-Pipeline-Stage und sollte durchlaufen. Das Beispiel `examples/hierarchy`
zeigt Untermodule in Unterordnern.

Weitere Befehle:

```bash
python . new mein_ordner --top C:\pfad\zu\mein_modul.vhd    # neuen Testbench-Ordner anlegen
python . gen mein_ordner                                    # nur Testbench erzeugen
python . run mein_ordner [--test NAME] [--surfer]           # erzeugen + simulieren (+ Surfer)
python . gui mein_ordner [--port N] [--no-browser]          # Web-GUI
```

`run` liefert Exitcode 0 bei bestandenen und 1 bei fehlgeschlagenen Tests (nutzbar in Skripten/CI).
Unter Windows geht auch `wavetb.cmd gui mein_ordner`.

## Testbench-Ordner (Speicherort)

Alles, was zu einem Test-Setup gehört, liegt in **einem Ordner**, den du in der GUI unter „Top-Level" im Feld
**Testbench-Ordner** angibst (oder beim Start als Argument: `python . gui mein_ordner`). Der Ordner muss nicht
beim VHDL-Code liegen:

```
mein_ordner/
  wavetb.json                       Einstellungen
  basic.wave.json                   ein Test pro Datei (Wellenform), Name = Testname
  axis_pipe_stage_basic_tb.vhd      generierte Testbench (plain: eine pro Test)
  build/                            Temporäres: GHDL-Arbeitsverzeichnis, .ghw-Wellen, bei VUnit vunit_out/
```

- Ändern des Feldes (oder „…") wechselt den Speicherort. Liegt dort schon ein WaveTB-Projekt, fragt die GUI, ob es geladen werden soll.
  Pfade zum Top-Level bleiben dabei gültig.
- Neu erzeugte Testbenches ersetzen die alten. Von WaveTB erzeugte Dateien, die nicht mehr gebraucht werden
  (umbenannte/gelöschte Tests, Moduswechsel), werden entfernt. **Eine Datei, die nicht von WaveTB stammt, wird nie überschrieben** –
  stattdessen gibt es eine Fehlermeldung.
- `build/` kann gelöscht werden und gehört nicht ins Repository.
- Alte Ordner im früheren Layout (`project.json` + `tests/`) werden noch gelesen und beim nächsten Speichern ins neue Layout geschrieben (die alten Dateien kannst du danach löschen).

`wavetb.json`:

```json
{
  "top": "../src/axis_pipe_stage.vhd",
  "entity": "axis_pipe_stage",
  "search": [],
  "sources": [],
  "period_ns": 10,
  "clock": "",
  "mode": "plain",
  "surfer": ""
}
```

| Feld | Bedeutung |
|---|---|
| `top` | VHDL-Datei mit dem zu testenden Modul – relativ zum Testbench-Ordner oder absolut (die GUI speichert relativ, solange der Pfad höchstens 3 Ebenen nach oben geht), die Datei darf **irgendwo auf dem PC** liegen. In der GUI per „…“ auswählen. Ports werden daraus gelesen, Untermodule automatisch gefunden (siehe unten) |
| `entity` | Entity innerhalb der Top-Datei (die GUI zeigt die Auswahlliste nur, wenn die Datei mehrere Entities enthält; leer = die letzte der Datei. Für ein Submodul einfach dessen Datei als Top-Level wählen) |
| `search` | Zusätzliche Ordner (rekursiv), in denen nach Untermodulen gesucht wird. Standard: der Ordner der Top-Datei samt Unterordnern |
| `sources` | Optional: Dateien/Globs, die **immer** mitcompiliert werden (z. B. wenn etwas nirgends referenziert wird). Ohne `top` ersetzt das die automatische Suche (alter Modus) |
| `period_ns` | Taktperiode |
| `clock` | Optional, nur in `wavetb.json` (nicht in der GUI): Name des Takt-Signals. Standard: das erste Signal mit `p`/`n`-Wellenform – reicht fast immer, es wird ohnehin nur ein Takt unterstützt |
| `mode` | `plain` (reines VHDL-2008, eine Testbench pro Test) oder `vunit` |
| `surfer` | optional: Pfad zu `surfer.exe`, falls nicht im `PATH` |

In der GUI stehen diese Felder oben; **Speichern** (oder Strg+S) schreibt `wavetb.json` und die `*.wave.json`-Dateien in den Testbench-Ordner.

## Untermodule und Hierarchie

Du wählst nur die Top-Datei. WaveTB liest sie und folgt allen Verweisen:

- `entity work.name` und Component-Instanzen (`u1 : name port map …`)
- `use work.paket.all` bzw. `work.paket.…`
- Architekturen und Package-Bodies, die in **getrennten Dateien** stehen

Gesucht wird rekursiv im Ordner der Top-Datei (plus `search`). Gefundene Dateien werden in die richtige
Compile-Reihenfolge gebracht (Abhängigkeiten zuerst); **nicht benötigte Dateien im selben Baum werden ignoriert** – auch
andere Testbenches oder Dateien mit Fehlern stören nicht. Die Liste steht in der GUI unter der Kopfzeile („Quellen: n Dateien“,
aufklappbar) und im Log. Hinweise dort heißen z. B. „`xyz` nicht in den Quellen gefunden“ (Vendor-Primitive wie UNISIM oder
fremde Bibliotheken – die müssen dann in `search` bzw. in deinem GHDL-Setup verfügbar sein) oder „mehrfach definiert“
(dann wird die Datei im nächstliegenden Ordner genommen).
Ein Beispiel mit Unterordnern, getrennter Architektur/Package-Body und einer absichtlich kaputten, ungenutzten Datei
liegt in `examples/hierarchy`.

Grenzen: Es wird nur die Bibliothek `work` aufgelöst (Dateien mit `library foo; use foo.…` brauchen ggf. `sources`),
und Verweise werden per Textsuche erkannt, nicht per vollständigem VHDL-Parser (z. B. Instanzen in `generate`-Blöcken
funktionieren, dynamisch gebaute Namen nicht).

## Wellenform schreiben

Format: [WaveDrom](https://wavedrom.com/) mit einer Ergänzung – jedes Signal braucht `dir: 'in'|'out'` (aus Sicht des DUT).

```js
{
  signal: [
    {dir: 'in',  name: 'clk',             wave: 'p......'},
    ['In Group',
      {dir: 'out', name: 'axis_in_tready', wave: '1......'},
      {dir: 'in',  name: 'axis_in_tvalid', wave: '01.010.'},
      {dir: 'in',  name: 'axis_in_tdata',  wave: 'x==x=x.', width: 8, data: ["AA","5F","6B"], radix: 'h'},
    ],
    {dir: 'in',  name: 'axis_out_tready',  wave: '1......'},
    {dir: 'out', name: 'axis_out_tvalid',  wave: '0.1.010'},
    {dir: 'out', name: 'axis_out_tdata',   wave: 'xx==x=x', width: 8, data: ["AA","5F","6B"], radix: 'h'},
  ],
}
```

Kommentare, Keys ohne Anführungszeichen, `'…'` und Kommas am Ende sind erlaubt.

**Wave-Zeichen** (ein Zeichen = eine Taktperiode):

| Zeichen | Bedeutung |
|---|---|
| `p` `n` `P` `N` | Takt (steigend / fallend; `P`/`N` mit Pfeil). Nur für das Taktsignal, in allen Tests derselbe Typ |
| `0` `1` `h` `l` | Pegel |
| `x` | Eingang: `X` treiben · Ausgang: **nicht prüfen** (don't care) |
| `z` | hochohmig |
| `=` `2`–`9` | nächster Wert aus `data` |
| `.` `\|` | vorigen Wert halten |

**Weitere Schlüssel:** `width` (Bitbreite, wird bei vorhandenem VHDL daraus gelesen), `data` (Liste oder
Leerzeichen-getrennter String), `radix` (`h` hex, `b` binär, `d` dezimal, `o` oktal; mit `s` davor vorzeichenbehaftet,
z. B. `sd` für `-23`), `period` (jedes Zeichen n-mal wiederholen). Gruppen als `['Name', {…}, {…}]`.

Tipps:
- **Vorlage aus Entity** (Button): legt für alle Ports ein Gerüst an.
- Kürzere Wellenformen halten ihren letzten Wert; nicht aufgeführte Eingänge werden mit `0`, nicht aufgeführte Ausgänge nicht geprüft.
- Mehrere Tests = mehrere `*.wave.json`-Dateien im Testbench-Ordner (in der GUI die Liste rechts: `+ Test`, Doppelklick = umbenennen).

## Zeitmodell (wichtig fürs Verständnis)

Zyklus *i* ist das *i*-te Wave-Zeichen. Die Eingänge von Zyklus *i* werden direkt nach der Taktflanke gesetzt, die
Zyklus *i* beginnt; die Ausgänge werden an der Flanke geprüft, die Zyklus *i* beendet – also so, wie es die gezeichnete
Wellenform zeigt (Ausgang reagiert eine Periode nach dem Eingang, wenn dein Design ein Register hat).
Ein Reset muss als normales Signal mit in die Wellenform gezeichnet werden.

## Was erzeugt wird

Nach **TB erzeugen** (oder jedem Lauf) liegen die Dateien in `build/`:

- `plain`: `<entity>_<test>_tb.vhd` pro Test, direkt im Testbench-Ordner. Aufbau: `component` + `UUT`, Taktgenerator, eine Prozedur
  `check_cycle` und je Zyklus ein Aufruf `check_cycle(<port>_value => …)`. Fehler werden mit Zyklus, Signal, Soll und Ist gemeldet; Ende mit `TEST PASSED`
  oder `severity failure`.
- `vunit`: `<entity>_tb.vhd` (Tests heißen `test_<name>`) und `run_vunit.py`, ebenfalls im Testbench-Ordner. Direkt nutzbar:
  `python run_vunit.py -p 4` (zum Debuggen `--gtkwave-fmt ghw`).
- Wellenform-Dateien (`.ghw`) in `build/waves/` bzw. `build/vunit_out/`.

Bei „Simulieren + Surfer" öffnet Surfer die Wellenform mit den Signalen in derselben Reihenfolge wie in der Vorschau;
Gruppen erscheinen als benannte Trennlinie (Surfer kennt per Kommandozeile keine echten Gruppen).

## Einschränkungen

- Port-Typen: `std_logic`, `std_logic_vector`, `std_ulogic_vector`, `unsigned`, `signed`. Generics werden mit ihren Default-Werten aufgelöst (kein Generic-Map).
- `inout`-Ports werden getrieben, aber nicht geprüft.
- Wellenformen werden als Text editiert (live Vorschau), nicht mit der Maus gezeichnet.
- Im Plain-Modus läuft jeder Test als eigene Simulation; DUT-Zustand wird nicht zwischen Tests mitgenommen.
- Der GUI-Server liest den Python-Code nur beim Start – nach Änderungen am Tool neu starten.

## Fehlersuche

| Meldung | Ursache |
|---|---|
| `'ghdl' nicht im PATH gefunden` | GHDL installieren / `PATH` ergänzen |
| `Top-Datei nicht gefunden` | Pfad im Feld „Top-Level“ (`top`) stimmt nicht (relativ zum Testbench-Ordner) |
| `Entity '…' nicht in der Top-Datei gefunden` | Entity-Auswahl passt nicht zur gewählten Datei |
| GHDL meldet fehlende Entity/Package | Das Modul liegt außerhalb des Suchbaums → Ordner unter „Weitere Ordner“ (`search`) ergänzen |
| `Signal 'x' existiert nicht im Entity` | Name stimmt nicht mit dem Port überein (Groß-/Kleinschreibung egal) |
| `Signal 'x' hat keine Richtung` | `dir: 'in'` bzw. `'out'` ergänzen |
| `Kein Takt gefunden` | Taktsignal braucht eine Wellenform mit `p`/`n` |
| `Wert … passt nicht in … (8 Bit)` | `data`-Wert oder `radix` prüfen (vorzeichenlos 0–255, mit `s` −128…127) |
| `VUnit nicht installiert` | `pip install vunit_hdl` |
| Surfer startet nicht | `surfer` in den `PATH` legen oder in `wavetb.json` eintragen |

## Dateien des Tools

`wavetb/core.py` (Wellenform-Parser) · `vhdl.py` (Entity-Parser) · `deps.py` (Abhängigkeiten/Compile-Reihenfolge) · `gen.py` (Testbench-Generator) · `runner.py`
(GHDL/VUnit/Surfer) · `server.py` + `static/index.html` (GUI) · `examples/` (Beispielprojekte).

## Lizenz

WaveTB steht unter der [MIT-Lizenz](LICENSE).

GHDL, Surfer und VUnit sind eigenständige Programme mit eigenen Lizenzen; sie werden von WaveTB nur aufgerufen und
nicht mitgeliefert. Das Wellenform-Format stammt von [WaveDrom](https://wavedrom.com/) (WaveTB nutzt nur das
Format, keinen WaveDrom-Code).
