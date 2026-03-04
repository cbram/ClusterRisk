# ClusterRisk - Portfolio Klumpenrisiko Analyse

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.31+-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Portfolio Performance](https://img.shields.io/badge/Portfolio%20Performance-required-orange.svg)

**ClusterRisk** analysiert Klumpenrisiken in Investment-Portfolios. Liest [Portfolio Performance](https://www.portfolio-performance.info/) CSV-Exporte, löst ETFs in Einzelpositionen auf und visualisiert Risiken über mehrere Dimensionen.

> **Voraussetzung:** [Portfolio Performance](https://www.portfolio-performance.info/) für den CSV-Export der Vermögensaufstellung.

## 🎯 Features

- **Analyse-Dimensionen:** Anlageklasse, Branche/Sektor, Währung, Land, Einzelpositionen (mit ETF-Durchschau)
- **ETF-Daten:** Morningstar-API (automatisch), Fallback: justETF, Yahoo Finance
- **Beispiel-Portfolio:** Button lädt Demo ohne CSV-Upload
- **Diagnose-System:** Fehlende ETF-Daten, Aktien ohne Branche, Parse-Fehler – direkt in der GUI
- **Visualisierungen:** Treemap, Pie, Bar-Chart (Sliders für max. Positionen)
- **Export:** Excel (.xlsx), LibreOffice (.ods) | **Historie:** SQLite, Verlaufsdiagramme
- **Docker-ready:** Unraid, Docker Compose

## 📸 Galerie

| Hauptansicht | Anlageklasse | Branche/Sektor |
|:---:|:---:|:---:|
| ![Übersicht](docs/screenshots/Screenshot%201.png) | ![Anlageklasse](docs/screenshots/Screenshot%202.png) | ![Branche](docs/screenshots/Screenshot%203.png) |

*Screenshots aktualisieren:* [docs/screenshots/README.md](docs/screenshots/README.md)

## 🚀 Installation

**macOS / Linux:** `./start.sh` oder:
```bash
cd ClusterRisk && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && streamlit run app.py
```

**Windows:** [Python 3.9+](https://www.python.org/downloads/) („Add to PATH“ aktivieren)
```powershell
cd ClusterRisk && python -m venv venv && .\venv\Scripts\Activate.ps1
pip install -r requirements.txt && streamlit run app.py
```

**Docker:** `docker-compose up -d` | App: `http://localhost:8501`

## 📖 Verwendung

1. **CSV exportieren:** Portfolio Performance → Berichte → Vermögensaufstellung → Export → CSV
2. **Hochladen:** In ClusterRisk „Browse files“ oder **„Beispiel-Portfolio laden“**
3. **Analysieren:** Tabs Anlageklasse, Branche, Währung, Land, Einzelpositionen, Detaildaten (Export), Historie

**Spalten in PP:** Bestand, Name, Symbol, ISIN, Kurs, Marktwert; optional: Branchen (GICS), Notiz

**Besonderheiten:**
- **Commodities** (Gold, Rohstoffe): Kein Währungsrisiko, optional einblendbar
- **Währung:** Handelswährung der Aktie (nicht ETF-Währung)
- **Sidebar:** Slider für Treemap/Pie/Bar-Limits, Risikoschwellen, ETF-Update-Intervall (1–90 Tage)

## 🔧 ETF-Konfiguration

**Neuen ETF hinzufügen (automatisch):** ISIN + Ticker in `data/etf_isin_ticker_map.csv` eintragen → Portfolio analysieren → Morningstar liefert Daten und speichert in `data/etf_details/{TICKER}.csv`

**Manuell:** `data/etf_details/{TICKER}.csv` anlegen. Vorlage: `data/etf_details/EUNL.csv`.

**Datenquellen:** 1) ETF-Detail-Dateien (lokal), 2) Morningstar-API, 3) Fallback: justETF, Yahoo. Wechselkurse: EZB-API.

**Ticker-Sektor-Cache:** `python manage_ticker_cache.py stats|list|add AAPL Technology`

## 🗂️ Projektstruktur

```
ClusterRisk/
├── app.py                 # Streamlit-App
├── src/
│   ├── risk_calculator.py # Kernlogik
│   ├── morningstar_fetcher.py, etf_details_parser.py, etf_data_fetcher.py
│   ├── visualizer.py, export.py, database.py, exchange_rate.py
│   └── ticker_sector_mapper.py
├── data/
│   ├── etf_details/       # ETF-Detail-CSVs (EUNL, VGWD, XEON, …)
│   ├── etf_isin_ticker_map.csv
│   ├── ticker_sector_cache.json
│   └── history.db
└── manage_ticker_cache.py
```

## 🛠️ Entwicklung

**Neue Analyse-Dimension:** `risk_calculator.py` → `app.py` (Tab) → `visualizer.py`

## 🐛 Einschränkungen & Troubleshooting

- **Morningstar:** Token von öffentlicher Webseite; Änderungen können Abruf beeinträchtigen
- **Fallback:** justETF/Yahoo für EU-ETFs oft unzuverlässig
- **Empfehlung:** ETF-Detail-Dateien in `data/etf_details/` pflegen
- **0 Positionen:** CSV von PP „Vermögensaufstellung“? Spalten Bestand, Name, Symbol, ISIN, Kurs, Marktwert?
- **ETF nicht aufgelöst:** ISIN in `etf_isin_ticker_map.csv` eintragen oder Detail-Datei anlegen
- **Port belegt:** `streamlit run app.py --server.port 8502`

## 🙏 Credits & Support

Morningstar-Integration: [pp-portfolio-classifier](https://github.com/Alfons1Qto12/pp-portfolio-classifier) (Alfons1Qto12). Beitragen: [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md). Issues: GitHub.

## ⚠️ Disclaimer

Keine Anlageberatung. Datenquellen (justETF, extraETF, Morningstar, etc.) nur zu Informationszwecken – keine Partnerschaft. Nutzung auf eigene Verantwortung. Siehe [LICENSE](LICENSE).

---

**Erstellt mit ❤️ für Portfolio-Optimierung**
