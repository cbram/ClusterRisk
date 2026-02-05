# ClusterRisk - Portfolio Klumpenrisiko Analyse

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.31+-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Portfolio Performance](https://img.shields.io/badge/Portfolio%20Performance-required-orange.svg)

**ClusterRisk** ist ein Tool zur Analyse von Klumpenrisiken in Investment-Portfolios. Es liest [Portfolio Performance](https://www.portfolio-performance.info/) CSV-Exporte, löst ETFs in ihre Einzelpositionen auf und visualisiert Risiken über verschiedene Dimensionen.

> **Wichtig:** Das Tool ist aktuell für die Verwendung mit [Portfolio Performance](https://www.portfolio-performance.info/) optimiert. Die kostenlose Open-Source-Software zur Depot-Verwaltung ist erforderlich, um die Portfolio-Daten im richtigen CSV-Format zu exportieren.

## 🎯 Features

- 📊 **Mehrere Analyse-Dimensionen**
  - Anlageklasse (Tagesgeld, ETFs, Rohstoffe, Aktien)
  - Branche/Sektor
  - Währung
  - Einzelpositionen (mit ETF-Durchschau)

- 🔍 **ETF-Durchschau**
  - Automatisches Abrufen der ETF-Zusammensetzung
  - Berechnung der tatsächlichen Exposition pro Einzelaktie
  - Mehrere Datenquellen (justETF, Yahoo Finance, etc.)

- 📈 **Interaktive Visualisierungen**
  - Treemap-Diagramme
  - Kreisdiagramme
  - Balkendiagramme mit Risiko-Schwellenwerten

- 💾 **Export & Historie**
  - Export nach Excel (.xlsx) und LibreOffice (.ods)
  - Historie-Funktion zur Verfolgung von Entwicklungen
  - SQLite-Datenbank für persistente Speicherung

- 🐳 **Docker-ready**
  - Einfaches Deployment auf Unraid oder anderen Servern
  - Persistente Daten-Volumes

## 🚀 Installation

### Lokale Installation (macOS)

```bash
# Repository klonen oder herunterladen
cd ClusterRisk

# Virtual Environment erstellen
python3 -m venv venv
source venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt

# App starten
streamlit run app.py
```

Die App läuft dann auf `http://localhost:8501`

### Docker Installation

```bash
# Mit Docker Compose
docker-compose up -d

# Oder manuell
docker build -t clusterrisk .
docker run -p 8501:8501 -v $(pwd)/data:/app/data clusterrisk
```

### Unraid Installation

1. Community Applications → "Add Container"
2. Repository: `your-dockerhub-username/clusterrisk:latest`
3. Port: `8501` → `8501`
4. Path: `/app/data` → `/mnt/user/appdata/clusterrisk/data`
5. Starten!

## 📖 Verwendung

### Voraussetzungen

**[Portfolio Performance](https://www.portfolio-performance.info/)** (kostenlose Open-Source Depot-Verwaltung)
- Download: https://www.portfolio-performance.info/
- Verfügbar für Windows, macOS, Linux
- Wird benötigt, um Portfolio-Daten im korrekten CSV-Format zu exportieren

### 1. Portfolio Performance CSV exportieren

1. Öffne **Portfolio Performance**
2. Gehe zu **Berichte** → **Vermögensaufstellung**
3. Klicke auf **Daten Exportieren** → **CSV**
4. Speichere die CSV-Datei

**Wichtig:** Aktiviere in der Vermögensaufstellung folgende Spalten:
- Bestand
- Name
- Symbol (Ticker)
- ISIN
- Kurs
- Marktwert
- Branchen (GICS, Sektoren) - für automatische Branchenerkennung
- Notiz - für spezielle Marker (z.B. "Geldmarkt ETF")

### 2. CSV-Datei hochladen

1. Öffne ClusterRisk im Browser (`http://localhost:8501`)
2. Klicke auf **"Browse files"** in der Sidebar
3. Wähle deine **Portfolio Performance CSV-Datei**
4. Die Analyse startet automatisch

### 3. Analyse erkunden

- **Anlageklasse**: Verteilung nach Asset-Typen (Stock, ETF, Cash, Commodity)
- **Branche/Sektor**: Branchen-Exposition (inkl. ETF-Holdings)
- **Währung**: Währungsrisiko (exkl. Commodities, da diese kein Währungsrisiko haben)
  - **Toggle**: "Commodities einblenden" - zeigt Commodities als separate Kategorie
- **Land**: Geografisches Risiko basierend auf ISIN-Ländercodes
- **Einzelpositionen**: Die wichtigste Ansicht - zeigt alle Einzelaktien inkl. ETF-Durchschau
  - **Toggle**: "Cash ausblenden" - fokussiert auf investierte Positionen

**Wichtige Features:**

🥇 **Commodities (Gold, Rohstoffe):**
- Werden als `Commodity` in Anlageklassen klassifiziert
- Haben **KEIN Währungsrisiko** (werden aus Währungsberechnung ausgeschlossen)
- Optional einblendbar in Währungsansicht als "Commodity (kein Währungsrisiko)"

💱 **Korrektes Währungsrisiko:**
- Nutzt die **Handelswährung** jeder Aktie (nicht die ETF-Währung)
- "Other Holdings" werden nach **Currency Allocation** aufgeteilt (ohne Doppelzählung)
- Beispiel: Apple in einem EUR-ETF → USD-Risiko

**Visualisierungs-Einstellungen:**

In der Sidebar kannst du die Anzahl der angezeigten Positionen für jede Visualisierung anpassen:

- **Treemap**: 10-100 Positionen (Standard: 30)
  - Größere Werte zeigen mehr Details, können aber unübersichtlich werden
- **Pie Chart**: 5-30 Positionen (Standard: 10)
  - Rest wird automatisch als "Sonstige" zusammengefasst
- **Bar Chart**: 10-100 Positionen (Standard: 30)
  - Zeigt detaillierte Prozent-Werte mit Risiko-Schwelle bei 10%

💡 **Tipp**: Für große Portfolios mit vielen ETF-Durchschau-Positionen kannst du die Limits erhöhen, um mehr Details zu sehen!

### 4. Export

- Wähle das gewünschte Format (Excel oder LibreOffice)
- Klicke auf den Download-Button
- Die Datei enthält alle Analysen als separate Sheets

## 🔧 Konfiguration

### ETF-Holdings manuell pflegen

Das Tool verwendet **strukturierte ETF-Detail-Dateien** für präzise ETF-Analysen. Diese Dateien enthalten alle relevanten Informationen pro ETF.

#### Neue Struktur (empfohlen): ETF-Detail-Dateien

**Ort:** `data/etf_details/`

Für jeden ETF wird eine separate CSV-Datei erstellt, benannt nach dem **Ticker-Symbol** (z.B. `EUNL.csv`, `VGWD.csv`).

**Dateiformat:**

```csv
METADATA
ISIN,IE00B4L5Y983
Name,iShares Core MSCI World UCITS ETF USD (Acc)
Ticker,EUNL
Type,Stock
Region,World
Currency,USD
TER,0.20

COUNTRY_ALLOCATION
Country,Weight
US,70.8
JP,6.2
GB,3.8
...

SECTOR_ALLOCATION
Sector,Weight
Technology,24.5
Financial Services,15.2
Healthcare,11.8
...

CURRENCY_ALLOCATION
Currency,Weight
USD,72.5
JPY,6.2
EUR,9.5
...

TOP_HOLDINGS
Name,Weight,Currency,Sector,Industry,Country
Apple Inc,4.98,USD,Technology,Consumer Electronics,US
NVIDIA Corp,4.67,USD,Technology,Semiconductors,US
Microsoft Corp,3.95,USD,Technology,Software,US
...
```

**Abschnitte:**
- `METADATA`: Grundlegende ETF-Informationen
  - `Type`: **Stock** (Aktien-ETF), **Money Market** (Geldmarkt), **Bond** (Anleihen), **Commodity** (Rohstoffe/Gold)
  - **Wichtig:** `Commodity`-ETFs haben **KEIN Währungsrisiko**
- `COUNTRY_ALLOCATION`: Länderverteilung in Prozent
- `SECTOR_ALLOCATION`: Sektorverteilung in Prozent
- `CURRENCY_ALLOCATION`: Währungsverteilung in Prozent
  - Wird für "Other Holdings" verwendet (ohne Doppelzählung der Top Holdings)
- `TOP_HOLDINGS`: Top 10-15 Einzelpositionen mit Details
  - **Wichtig:** Muss "Other Holdings" Zeile enthalten für korrekte Berechnung

**Beispiel "Other Holdings":**
```csv
Other Holdings,68.94,Mixed,Diversified,Diversified,Mixed
```

Die Currency Allocation wird verwendet, um "Other Holdings" korrekt auf Währungen aufzuteilen:
- ETF Gesamt-Currency - Top Holdings Währungen = Other Holdings Währungsverteilung
- Dies vermeidet Doppelzählung und ergibt korrektes Währungsrisiko

**ISIN-zu-Ticker-Mapping:**

Die Datei `data/etf_isin_ticker_map.csv` verknüpft ISINs mit Ticker-Symbolen:

```csv
ISIN,Ticker,Name
IE00B4L5Y983,EUNL,iShares Core MSCI World UCITS ETF USD (Acc)
IE00B8GKDB10,VGWD,Vanguard FTSE All-World High Dividend Yield UCITS ETF
LU0290358497,XEON,Xtrackers II EUR Overnight Rate Swap UCITS ETF 1C
DE000A2T0VU5,XGDU,Xtrackers IE Physical Gold ETC Securities
```

**Vorteile der neuen Struktur:**
- ✅ Vollständige Sektor-, Länder- und Währungsverteilungen
- ✅ Korrekte Behandlung von "Other Holdings" ohne Doppelzählung
- ✅ ETF-Typ-Information (Money Market = Cash, Commodity = kein Währungsrisiko)
- ✅ Einfachere Wartung (eine Datei pro ETF)
- ✅ Erweiterbar für weitere Metadaten (TER, Region, etc.)

**Verfügbare ETF-Detail-Dateien:**
- `EUNL.csv` - iShares Core MSCI World
- `VGWD.csv` - Vanguard FTSE All-World High Dividend Yield
- `AEEM.csv` - Amundi MSCI Emerging Markets
- `AUM5.csv` - Amundi S&P 500 Swap
- `GERD.csv` - L&G Gerd Kommer Multifactor Equity
- `XEON.csv` - Xtrackers EUR Overnight Rate Swap (Money Market)
- `XGDU.csv` - Xtrackers Physical Gold ETC (Commodity)

**Datenquellen für neue ETFs:**
- [justETF.com](https://www.justetf.com) - Factsheets und Allokationsdaten
- [extraETF.com](https://extraetf.com) - Alternative Quelle
- Offizielle ETF-Anbieter Websites (iShares, Vanguard, Amundi, Xtrackers)

*Hinweis: Die genannten Websites sind unabhängige Informationsquellen. Nutzer müssen Daten manuell übertragen.*

#### Fallback: Legacy-Strukturen

Falls ein ETF noch keine Detail-Datei hat, nutzt das Tool automatisch Fallback-Quellen:

1. **User CSV** (`data/user_etf_holdings.csv`) - Manuell gepflegte Holdings
2. **Mock-Daten** (`src/mock_etf_holdings.py`) - Statische Daten für populäre ETFs
3. **API-Fetcher** - Automatischer Abruf (meist unzuverlässig für EU-ETFs)

**Empfehlung:** Erstelle für alle deine ETFs ETF-Detail-Dateien für beste Ergebnisse!

### Cache-Einstellungen

In der Sidebar kannst du die Cache-Dauer für ETF-Daten einstellen (1-30 Tage). Dies reduziert API-Aufrufe und beschleunigt wiederholte Analysen.

**Hinweis:** Bei Verwendung von ETF-Detail-Dateien wird kein API-Cache benötigt, da alle Daten lokal vorliegen.

### Datenquellen

**ETF-Holdings (in Priorität):**

1. **ETF-Detail-Dateien** (`data/etf_details/*.csv`) - **Empfohlen!**
   - Strukturierte Dateien pro ETF mit vollständigen Allokationen
   - Beste Datenqualität und Genauigkeit
   - Kein API-Cache nötig
   
2. **Fallback-Quellen** (wenn keine Detail-Datei vorhanden):
   - User CSV (`data/user_etf_holdings.csv`) - Manuell gepflegt
   - Mock-Daten (`src/mock_etf_holdings.py`) - Statische Daten für wenige populäre ETFs
   - API-Fetcher (Yahoo Finance) - Meist unzuverlässig für EU-ETFs

**Wechselkurse (automatisch):**
- Tagesaktuelle Kurse von der Europäischen Zentralbank (EZB)
- 24h-Caching für Performance
- Automatische Umrechnung für Fremdwährungs-Aktien (USD, GBP, CHF, etc.)

### ISIN-zu-Ticker Mapping

**Automatisches Ticker-zu-Sektor Mapping:**

Das Tool verwendet ein **intelligentes Caching-System** für Ticker-zu-Sektor-Zuordnungen:

1. **Lokaler Cache** (`data/ticker_sector_cache.json`) - Wird automatisch erstellt und erweitert
2. **Yahoo Finance API** - Automatisches Abrufen für neue Tickers
3. **OpenFIGI API** - Fallback wenn Yahoo Finance fehlschlägt
4. **Cache-Dauer**: 90 Tage (konfigurierbar)

**Vorteile:**
- ✅ Keine wiederholten API-Calls für bekannte Ticker
- ✅ Automatisches Erweitern beim Hinzufügen neuer Positionen
- ✅ Manuell editierbar für Korrekturen
- ✅ Teilen des Caches zwischen Teammitgliedern möglich

**Manuelles Update:**
```bash
# Cache-Statistiken anzeigen
python manage_ticker_cache.py stats

# Alle Einträge auflisten
python manage_ticker_cache.py list

# Ticker manuell hinzufügen
python manage_ticker_cache.py add AAPL Technology

# Ticker entfernen
python manage_ticker_cache.py remove AAPL

# Sektor von API neu laden (force refresh)
python manage_ticker_cache.py fetch TSLA
```

**Cache teilen:**
Die Datei `data/ticker_sector_cache.json` kann im Team geteilt werden (z.B. via Git), um APIs zu schonen und konsistente Zuordnungen zu gewährleisten.

**Hinweis:** Der Ticker-Sektor-Mapper wird nur für **Aktien** verwendet, nicht für ETFs (diese werden aufgelöst) oder Commodities.

## 📊 Währungsrisiko & Commodities

### Korrekte Währungsbehandlung

Das Tool berechnet das **echte Währungsrisiko** deines Portfolios:

1. **Handelswährung statt ETF-Währung:**
   - Apple in einem EUR-ETF → **USD-Risiko** (nicht EUR)
   - ASML in einem USD-ETF → **EUR-Risiko** (nicht USD)

2. **"Other Holdings" ohne Doppelzählung:**
   - Verwendet Currency Allocation des ETFs
   - Zieht Währungen der Top Holdings ab
   - Beispiel: ETF 72.5% USD, Top Holdings 25% USD → Other Holdings 47.5% USD

3. **Commodities haben KEIN Währungsrisiko:**
   - Gold, Silber, Rohstoffe werden aus Währungsberechnung ausgeschlossen
   - Optional einblendbar als "Commodity (kein Währungsrisiko)"
   - Toggle in der Währungsansicht: "Commodities einblenden"

### Commodity-ETFs

Commodity-ETFs (z.B. Xetra Gold `XGDU`) werden speziell behandelt:

- **Type: Commodity** in ETF-Detail-Datei
- Erscheinen in **Anlageklassen** als "Commodity"
- Werden aus **Währungsrisiko** ausgeschlossen (kein Risiko)
- Optional in **Währungsansicht** einblendbar

## 📊 Risiko-Schwellenwerte

Das Tool verwendet folgende Schwellenwerte für Klumpenrisiken:

- **> 10%**: Hohes Risiko (rot markiert)
- **5-10%**: Mittleres Risiko (gelb markiert)
- **< 5%**: Niedriges Risiko

Diese sind etablierte Portfolio-Management-Richtlinien, können aber nach deinen Bedürfnissen angepasst werden.

## 🗂️ Projektstruktur

```
ClusterRisk/
├── app.py                      # Streamlit Haupt-App
├── requirements.txt            # Python Dependencies
├── Dockerfile                  # Docker Image
├── docker-compose.yml          # Docker Compose Config
├── src/
│   ├── csv_parser.py          # Portfolio Performance CSV Parser
│   ├── etf_data_fetcher.py    # ETF-Daten Abruf (Legacy-Fallback)
│   ├── etf_details_parser.py  # ETF-Detail-Dateien Parser (Primär)
│   ├── risk_calculator.py     # Klumpenrisiko-Berechnung
│   ├── visualizer.py          # Visualisierungen
│   ├── export.py              # Export-Funktionen
│   ├── database.py            # Historie-Verwaltung
│   ├── exchange_rate.py       # Wechselkurs-Manager (EZB-API)
│   ├── ticker_sector_mapper.py # Dynamisches Ticker-Sektor-Mapping
│   ├── mock_etf_holdings.py   # Mock-Daten (Legacy-Fallback)
│   └── user_etf_holdings.py   # User-CSV Manager (Legacy-Fallback)
├── data/
│   ├── cache/                 # ETF-Daten & Wechselkurs Cache
│   ├── etf_details/           # ⭐ Strukturierte ETF-Detail-Dateien (Primär)
│   │   ├── EUNL.csv          # iShares Core MSCI World
│   │   ├── VGWD.csv          # Vanguard FTSE All-World High Div
│   │   ├── AEEM.csv          # Amundi MSCI Emerging Markets
│   │   ├── AUM5.csv          # Amundi S&P 500 Swap
│   │   ├── GERD.csv          # L&G Gerd Kommer Multifactor
│   │   ├── XEON.csv          # Xtrackers EUR Overnight Rate
│   │   ├── XGDU.csv          # Xtrackers Physical Gold ETC
│   │   └── ...               # Deine weiteren ETFs hier
│   ├── etf_isin_ticker_map.csv # ISIN-zu-Ticker-Mapping
│   ├── user_etf_holdings.csv  # Legacy: Manuell gepflegte Holdings
│   ├── ticker_sector_cache.json # Ticker-Sektor Cache
│   └── history.db             # SQLite Historie
└── README.md
```

## 🛠️ Entwicklung

### Neuen ETF hinzufügen (empfohlen)

**Erstelle eine ETF-Detail-Datei:**

1. Erstelle `data/etf_details/{TICKER}.csv` (z.B. `SPYY.csv`)
2. Fülle die Sections aus (METADATA, COUNTRY_ALLOCATION, SECTOR_ALLOCATION, CURRENCY_ALLOCATION, TOP_HOLDINGS)
3. Füge ISIN-Mapping in `data/etf_isin_ticker_map.csv` hinzu
4. Fertig! Der ETF wird automatisch erkannt

**Datenquellen:**
- [justETF.com](https://www.justetf.com) - Factsheets mit Top Holdings und Allokationen
- [extraETF.com](https://extraetf.com) - Alternative Quelle
- Offizielle ETF-Anbieter Websites

### Neue Analyse-Dimension hinzufügen

1. Erweitere `calculate_cluster_risks()` in `src/risk_calculator.py`
2. Füge einen neuen Tab in `app.py` hinzu
3. Implementiere die Visualisierung in `src/visualizer.py`

## 🐛 Bekannte Einschränkungen

- **Automatischer ETF-Abruf**: Yahoo Finance und Web-Scraping sind für EU-ETFs meist unzuverlässig
- **Rate Limits**: Einige ETF-Provider beschränken automatischen Zugriff
- **Web-Scraping**: Kann brechen wenn Websites ihre Struktur ändern

**✅ Empfohlene Lösung:** Erstelle ETF-Detail-Dateien für alle deine ETFs (siehe oben)

## 🤝 Beitragen

Contributions sind willkommen! Siehe `.github/CONTRIBUTING.md` für Details.

Mögliche Bereiche:
- Bug-Fixes und Verbesserungen
- Neue ETF-Detail-Dateien
- Dokumentations-Updates
- Feature-Vorschläge (via Issues)

## ⚠️ Disclaimer

**Keine Anlageberatung:**
Dieses Tool dient ausschließlich zu Informationszwecken und stellt keine Anlageberatung dar. Investitionsentscheidungen sollten immer auf eigener Recherche und ggf. professioneller Beratung basieren.

**Datenquellen:**
Die Nennung von Websites (justETF, extraETF, etc.) und ETF-Anbietern (iShares, Vanguard, Amundi, Xtrackers, etc.) erfolgt ausschließlich zu Informationszwecken. Es besteht keine geschäftliche Beziehung, Partnerschaft oder Empfehlung. Die genannten Namen und Marken sind Eigentum ihrer jeweiligen Inhaber.

**ETF-Daten:**
Die in den Beispiel-ETF-Detail-Dateien enthaltenen Daten basieren auf öffentlich zugänglichen Informationen (Factsheets, Websites der ETF-Anbieter). Nutzer sind selbst dafür verantwortlich, die Aktualität und Richtigkeit der Daten zu überprüfen.

**Datengenauigkeit:**
Die Genauigkeit der Analysen hängt von der Qualität der bereitgestellten Daten ab. Es wird keine Gewähr für die Richtigkeit der Ergebnisse übernommen.

**Haftungsausschluss:**
Die Nutzung erfolgt auf eigene Verantwortung. Der Autor übernimmt keine Haftung für finanzielle Entscheidungen, die auf Basis dieses Tools getroffen werden, oder für Schäden, die durch die Nutzung entstehen.

## 📄 Lizenz

MIT License - siehe LICENSE Datei

Die Software wird "wie besehen" ohne jegliche Gewährleistung bereitgestellt.

## 💬 Support

Bei Fragen oder Problemen öffne bitte ein Issue auf GitHub.

---

**Erstellt mit ❤️ für Portfolio-Optimierung**

*Hinweis: Dieses Projekt steht in keiner Verbindung zu den genannten Finanzdienstleistern, ETF-Anbietern oder Informationsportalen.*
