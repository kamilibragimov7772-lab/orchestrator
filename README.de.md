# Orchestrator — ein überprüfbarer Orchestrierungs-Stack für Claude Code

**[English](README.en.md) · [Русский](README.md) · [简体中文](README.zh-CN.md) · [Español](README.es.md) · [Português](README.pt-BR.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Deutsch](README.de.md) · [Français](README.fr.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md) · [Türkçe](README.tr.md)**

Macht aus einer Claude-Code-Sitzung einen Orchestrator: Aus einem Briefing wird ein Wellenplan,
jede Welle führt spezialisierte Subagenten aus, jede Welle landet als Datei, und ein
unabhängiger Prüfer nimmt das Ergebnis an oder weist es zurück. 41 Agentenkarten,
10 gemeinsame Verträge, 10 Slash-Commands, 4 optionale Skills.

MIT-Lizenz. Autor: **[@kamil_ibrgmv](https://instagram.com/kamil_ibrgmv)**. Protokoll **2.16.0**.

> **Bitte zuerst lesen — zur Sprache.** Das Orchestrierungsprotokoll, die Agentenkarten und die
> Abnahmekriterien sind **auf Russisch** geschrieben. Werkzeuge, Tests, Installationspfad und
> Code-Kommentare sind auf Englisch. Wer die Agenten selbst will, liest russisches Markdown.
> Wer die Installation sucht, die einen Agenten-Stack vertrauenswürdig macht: dieser Teil ist
> sprachunabhängig und der eigentliche Grund, warum es dieses Repository gibt.

---

## Warum es das gibt

An Subagenten-Sammlungen für Claude Code herrscht kein Mangel. Es fehlen die, die man
**überprüfen** kann. Die meisten sind ein Ordner mit Markdown-Dateien: Nichts belegt, dass die
Hooks auslösen, nichts belegt, dass der Secret-Scanner die richtigen Bytes liest, und nichts
schlägt fehl, wenn eine Prüfung still aufhört zu prüfen.

Dieses Repository trifft die umgekehrte Abwägung. Die Agentenbibliothek ist gewöhnlich;
**der Unterbau darum herum ist der Punkt**:

| Was die meisten liefern | Was hier geliefert wird |
|---|---|
| Nur Agenten-Markdown | Agenten **plus** Guards, Installer, Doctor, Abnahme-Gate, Sync |
| Keine Tests | **97 Tests**, nur Standardbibliothek, keine API-Aufrufe, kein Netzwerk |
| „Füge das in settings.json ein“ | Installer mit Kollisions-Preflight; **der Doctor führt den Guard wirklich aus** und verlangt, dass er blockiert |
| Hooks funktionieren angeblich | Smoke-Test mit drei Payloads: harmlos muss durchgehen, Secret muss blockieren, riskanter Befehl muss blockieren |
| „Ist sicher, vertrau dem Prompt“ | Prompt-Text gilt nie als Zugriffsgrenze — siehe [SECURITY.md](SECURITY.md) |

Alles, was ein Skript prüfen kann, prüft ein Skript. Denn eine Regel, die nur im Prompt lebt,
ist eine Regel, die still aufhört zu gelten.

---

## Schnellstart

Voraussetzung: **Python 3.10+** und **Git**. Kein API-Key, kein Netzwerk, keine Modellaufrufe:

```sh
git clone https://github.com/kamilibragimov7772-lab/orchestrator
cd orchestrator
python tools/verify.py
```

Das führt den Agenten-Vertragslinter, den Selbsttest des Fertigstellungszählers, die komplette
Testsuite und einen Secret-Scan aus. Nichts außerhalb des Checkouts wird angefasst.

Installiere in selbst gewählte Verzeichnisse — der Installer **plant zuerst und überschreibt nie**:

```sh
python tools/install.py \
  --destination /absolute/path/stack \
  --vault /absolute/path/knowledge-base \
  --mode minimal
```

Plan prüfen, dann erneut mit `--apply` ausführen. Existiert eine Zieldatei und weicht ab, bricht
die Installation ab und behält deine Datei. Danach das Ergebnis bestätigen:

```sh
python tools/doctor.py --root /absolute/path/stack --installed
```

`minimal` installiert sieben Rollen für Recherche und Markdown-Ergebnisse. `full` ergänzt die
Software-, Website- und Medien-Pipelines samt externen Abhängigkeiten. Windows-Hinweise und wie
man Claude Code auf das neue Verzeichnis zeigen lässt: [INSTALL.md](INSTALL.md).

---

## Was enthalten ist

| Schicht | Zweck | Prüfgrenze |
|---|---|---|
| `_orchestr_protocol.md`, `agents/`, `commands/` | Routing, Verträge, Definition of Done | Der Linter prüft Struktur; Antwortqualität braucht menschliche Abnahme |
| `tools/verify.py`, `tests/` | Ein reproduzierbarer Befehl, inklusive Negativfällen | Ohne Claude-API, ohne externes MCP |
| `tools/guard.py` | Erkennung von Zugangsdaten und destruktiven Befehlen bei PreToolUse | **Heuristische Verteidigung in der Tiefe** — Host-Rechte und Sandbox beibehalten |
| `tools/install.py`, `tools/doctor.py` | Zerstörungsfreie Installation; Bereitschaftsbericht | Der Doctor prüft weder Authentifizierung noch Modellqualität |
| `tools/acceptance-gate/` | Deterministische Run-Log-Prüfungen plus optionaler Prüfer-Worker | Modell-Worker ist **standardmäßig aus**; Live-End-to-End nicht zertifiziert |
| `tools/sync_stack.py` | Git-Brücke über eine exakte Allowlist | Optional; führt divergierte Branches nicht für dich zusammen |
| `tools/export_session.py` | Opt-in-Export von Transkripten | **Aus**; die Schwärzung ist musterbasiert, keine Datenschutzgarantie |

### Das Abnahme-Gate

Die Idee, die am längsten gebraucht hat, bis sie stimmte. Nach Abschluss eines Laufs bewertet
ein **separater Kontext** — der die Überlegungen des Orchestrators nie gesehen hat — das
Ergebnis gegen das Briefing. Zuerst läuft ein deterministisches Skript, das Modell beurteilt nur,
was das Skript nicht kann:

- `run_status` und `verdict` sind getrennte Felder. Ein Lauf, der nicht `done` ist, liefert
  *„nicht abnahmefähig“*, kein vorgetäuschtes Bestehen.
- `SKIP` ergibt **„unvollständig“**, niemals „angenommen“. Ein PDF wird als *nur Signatur —
  in einem Viewer öffnen* gemeldet, ein `.docx` als *Struktur parst, visuelle Abnahme separat*.
- Die Exit-Codes sind unterscheidbar: `0` angenommen · `1` abgelehnt · `3` unvollständig ·
  `4` nicht anwendbar · `2` Fehler.

Die Begründung, vom Autor über 259 Läufe gemessen: Eine Regel, die es in einen Validator
geschafft hat, hält zu 76–100%; dieselbe Regel als Prompt-Text hält zu 0–39%.

---

## Was es bewusst nicht tut

Vertrauen ist größtenteils eine Liste dessen, was ein Werkzeug hinter deinem Rücken unterlässt:

- **Bei der Installation kein automatischer Export, keine Spiegelung, kein Git-Push, kein Cron,
  kein Modellprozess.** Jedes davon ist opt-in und braucht ausdrückliche Konfiguration.
- **Keine Spiegelung im Stil von `robocopy /MIR`.** Sie konnte Dateien im Ziel löschen, die in
  der Quelle fehlen. Wurde entfernt.
- **Kein Überschreiben.** Kollidierende Dateien stoppen die Installation; deine Settings und
  Hooks werden zusammengeführt, nicht ersetzt.
- **Kein stilles Bestehen.** Eine fehlende Abhängigkeit oder eine nicht ausgeführte Prüfung
  meldet `NOT CHECKED` oder `SKIP`. Nie ein Bestehen, das nicht verdient wurde.
- **Keine Behauptung einer unbewiesenen Bewertung.** „9,5/10“ war das Ziel und ist
  **nicht zertifiziert** — die offenen Punkte stehen in [`audit_9_5/`](audit_9_5/), statt im
  Durchschnitt unterzugehen.

---

## Stand der Überprüfung

Die CI läuft auf Windows / Linux / macOS × Python 3.10 und 3.12, parst jedes PowerShell-Skript
und scannt die **gesamte Git-Historie** mit Gitleaks. Siehe
[`.github/workflows/ci.yml`](.github/workflows/ci.yml).

Ehrliche Grenzen, denn ein grünes Badge ist kein Beweis:

- Die Tests decken das Verhalten der Werkzeuge ab, nicht die Qualität dessen, was die Agenten schreiben.
- Live-End-to-End-Abnahme mit echtem Modell ist von der Suite **nicht** abgedeckt.
- Die Guards sind Heuristiken. Sie ergänzen die Host-Berechtigungen; sie ersetzen sie nicht.

---

## Dokumentation

| Datei | Beantwortet |
|---|---|
| [INSTALL.md](INSTALL.md) | Installation, Anbindung an Claude Code, Windows-Besonderheiten |
| [AGENTS.md](AGENTS.md) | Einstiegspunkt für die Arbeit an dieser Codebasis |
| [SECURITY.md](SECURITY.md) | Was die Guards schützen und was nicht; Datenschutz beim Export |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Die Prüfungen, die eine Änderung bestehen muss |
| [CHANGELOG.md](CHANGELOG.md) | Verhaltensänderungen |

## Methodische Grundlage

Technische Grundlage: **NIST SSDF 1.1** (NIST, 2022) — einen Defekt reproduzieren, beheben und
eine Regression ergänzen, die den kaputten Fall zurückweist — zusammen mit der offiziellen
Dokumentation des Hosts ([Claude Code hooks](https://code.claude.com/docs/en/hooks)).
Geprüft am 2026-09-06. SSDF dient der Risikoauswahl, nicht als Konformitätszertifikat.

## Lizenz

[MIT](LICENSE). Autor: **[@kamil_ibrgmv](https://instagram.com/kamil_ibrgmv)**.
