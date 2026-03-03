# ClusterRisk - Technische Dokumentation

Dieses Dokument beschreibt die technische Implementierung und Architektur von ClusterRisk.

## Architektur-Übersicht

```
Portfolio Performance CSV
         ↓
    CSV Parser
         ↓
  Risk Calculator ←→ ETF Details Parser
         ↓              ↓
   Visualizer      (ETF-Detail-Dateien)
         ↓              ↑
   Streamlit App    ETF Detail Generator
                        ↑
                   justETF Scraper
```

## Datenfluss

### 1. Input-Verarbeitung

**Portfolio Performance CSV → `src/csv_parser.py`**

Der CSV-Parser liest die Vermögensaufstellung aus Portfolio Performance:

```python
def parse_portfolio_csv(csv_path: str) -> Dict:
    # Liest CSV mit deutschen Dezimaltrennern
    # Extrahiert:
    # - Positionen (Bestand, Name, Symbol, ISIN, Kurs, Marktwert)
    # - Währung (aus Kurs-Feld extrahiert)
    # - Sektor (aus PP Taxonomie, höchste Priorität)
    # - Typ (Stock, ETF, Cash, Commodity)
```

**Wichtige Features:**
- Erkennt Cash-Konten via Keywords ("Konto", "Cash") oder `Notiz`-Feld
- Unterstützt mehrere Portfolios/Konten
- Priorisiert Sektor aus PP-Taxonomie über andere Quellen

### 2. ETF-Auflösung

**`src/risk_calculator.py::_expand_etf_holdings()`**

ETFs werden in ihre Einzelpositionen aufgelöst mit mehreren Datenquellen:

**Priorität der ETF-Datenquellen:**

1. **ETF-Detail-Dateien** (`data/etf_details/*.csv`)
   - Strukturierte CSV-Dateien pro ETF (benannt nach Ticker)
   - Enthalten: Metadata, Top Holdings, Country/Sector/Currency Allocations
   - Parser: `src/etf_details_parser.py`
   - **Vorteil:** Vollständige Allokationsdaten für korrekte "Other Holdings" Behandlung
   - Können automatisch via `src/etf_detail_generator.py` aus justETF generiert werden
   - Oder via **Morningstar (pp-portfolio-classifier):** `src/morningstar_csv_importer.py` importiert `pp_data_fetched.csv` und erzeugt dasselbe CSV-Format (Option A, manueller Abruf bei Morningstar)

2. **API-Fetcher** (`src/etf_data_fetcher.py`)
   - justETF (Scraping), Yahoo Finance, OpenFIGI
   - Fallback wenn keine Detail-Dateien vorhanden

### 3. ETF-Detail-Dateien

**Format:** `data/etf_details/{TICKER}.csv`

**Erstellung:** Manuell, via `src/etf_detail_generator.py` (justETF Scraping) oder via `src/morningstar_csv_importer.py` aus pp-portfolio-classifier-Ausgabe (`pp_data_fetched.csv`)

**Sections (zwei Header-Formate werden unterstützt):**

```csv
# ETF Metadata
ISIN,IE00B4L5Y983
Name,iShares Core MSCI World UCITS ETF USD (Acc)
Ticker,EUNL
Type,Stock
Index,MSCI World               # Automatisch von justETF gescrapet
Region,World
Currency,USD
TER,0.20
Proxy ISIN,                    # Optional: ISIN eines physischen Proxy-ETFs (für Swap-ETFs)
Last Updated,2026-02-08
Source,justETF (auto-generated) # oder: justETF (via Proxy: ...) / leer bei manuell
Last Updated,2026-02-04

# Country Allocation (%)
Country,Weight
US,70.8
JP,6.2
...

# Sector Allocation (%)
Sector,Weight
Technology,24.5
Financial Services,15.2
...

# Currency Allocation (%)
Currency,Weight
USD,72.5
JPY,6.2
...

# Top Holdings
Name,Weight,Currency,Sector,Country,ISIN
Apple Inc,4.98,USD,Technology,US,US0378331005
NVIDIA Corp,4.67,USD,Technology,US,US67066G1040
...
```

**Hinweis:** Der Parser unterstützt auch das alternative Format ohne `#` (z.B. `METADATA`, `COUNTRY_ALLOCATION`), sowie verschiedene Spaltenreihenfolgen in Holdings (Header-basiertes Parsing).

**Automatische Generierung via justETF:**
- Aufruf über Streamlit-Sidebar: ISIN + Ticker eingeben → "Generieren"
- Scrapt: Holdings (mit ISINs), Länder- und Sektor-Allokation, Metadaten
- Leitet Währungs-Allokation automatisch aus Ländern ab (Country→Currency Mapping)
- Aktualisiert `data/etf_isin_ticker_map.csv` automatisch

**ETF-Typ-Behandlung:**

- `Type: Stock` → Holdings werden als `Stock` klassifiziert
- `Type: Money Market` → ETF wird als `Cash` in der Anlageklassen-Ansicht behandelt
- `Type: Bond` → Holdings werden als `Bond` klassifiziert
- `Type: Commodity` → ETF wird als `Commodity` klassifiziert, **KEIN Währungsrisiko**

**Proxy-ISIN (für Swap-ETFs):**

Swap-ETFs liefern auf justETF keine physischen Holdings, sondern listen andere ETFs/Fonds als Collateral. Um dennoch korrekte Allokationsdaten zu erhalten, kann ein physisch replizierender ETF auf denselben Index als Proxy angegeben werden:

```csv
# ETF Metadata
ISIN,LU0292107645
Name,Xtrackers MSCI Emerging Markets Swap UCITS ETF 1C
Ticker,XMME
Type,Stock
Region,Emerging Markets
Proxy ISIN,IE00B4L5YC18
Source,justETF (via Proxy: IE00B4L5YC18)
```

- `Proxy ISIN` wird in der Metadata-Section der ETF-Detail-Datei gespeichert
- Beim Generieren/Aktualisieren werden Allokationen/Holdings vom Proxy gescrapet
- Metadaten (Name, ISIN, TER, Typ) bleiben die des eigentlichen ETFs
- In der UI mit 🔗 gekennzeichnet

**Datenquellen-Typen:**

- **auto** (`Source` enthält "justETF"/"auto"): Automatisch generiert, aktualisierbar
- **proxy** (`Proxy ISIN` gesetzt): Via Proxy automatisch generiert, aktualisierbar
- **manual** (kein Source-Feld oder unbekanntes Format): Manuell gepflegt, wird bei Batch-Updates übersprungen

**ISIN-zu-Ticker-Mapping:**

`data/etf_isin_ticker_map.csv`:
```csv
ISIN,Ticker,Name
IE00B4L5Y983,EUNL,iShares Core MSCI World UCITS ETF USD (Acc)
LU0290358497,XEON,Xtrackers II EUR Overnight Rate Swap UCITS ETF 1C
DE000A2T0VU5,XGDU,Xtrackers IE Physical Gold ETC Securities
```

Wird von `risk_calculator.py` beim Start geladen.

### 4. Risiko-Berechnung

**`src/risk_calculator.py`**

Berechnet Klumpenrisiken über 5 Dimensionen:

#### 4.1 Anlageklasse (`_calculate_asset_class_risk`)

```python
# ETF_Holding → Stock (Holdings sind meist Aktien)
# Money Market ETFs → Cash (via etf_type)
```

**Spezialbehandlung:**
- Geldmarkt-ETFs werden als `Cash` klassifiziert (via `Type: Money Market` in Metadata)
- ETF-Holdings werden nach ihrem tatsächlichen Typ klassifiziert

#### 4.2 Sektor (`_calculate_sector_risk`)

**Sektor-Priorität (Konfliktauflösung):**

1. **CSV** (Priorität 2): Sektor aus Portfolio Performance Taxonomie
   - `sector_source = 'csv'`
   - Höchste Priorität, da vom User manuell zugeordnet

2. **ISIN/ETF-Details** (Priorität 1): Sektor via ISIN-Lookup oder ETF-Detail-Datei
   - `sector_source = 'isin'` oder `'etf_details'`
   - Mittlere Priorität

3. **ETF-Holdings** (Priorität 0): Sektor aus ETF-Holding-Daten
   - `sector_source = 'etf'`
   - Niedrigste Priorität

**Sektor-Normalisierung:**

`_normalize_sector_name()` mapped verschiedene Bezeichnungen:
```python
'Informationstechnologie' → 'Technology'
'Basiskonsumgüter' → 'Consumer Staples'
'Zyklische Konsumgüter' → 'Consumer Cyclical'
```

**Filtering:**
- `Diversified` und `ETF` werden ausgefiltert (keine echten Branchen)

#### 4.3 Währung (`_calculate_currency_risk`)

Verwendet die **Handelswährung** der Aktie, nicht die ETF-Währung:

```python
# AAPL wird an NYSE in USD gehandelt
# → Währung: USD (nicht EUR, auch wenn ETF in EUR ist)
```

**WICHTIG: Commodities haben KEIN Währungsrisiko!**

Commodities (Gold, Silber, Rohstoffe) werden aus der Währungsberechnung **ausgeschlossen**:

```python
for position in expanded_positions:
    if position.get('type') == 'Commodity':
        continue  # Kein Währungsrisiko!
    currencies[currency] += position['value']
```

**Alternative Ansicht: Mit Commodities**

`_calculate_currency_risk_with_commodities()` bietet eine optionale Ansicht, die Commodities als separate Kategorie "Commodity (kein Währungsrisiko)" zeigt.

Währung wird bestimmt via:
1. Explizite Währung aus Holding-Daten
2. ISIN-basierte Zuordnung (`_get_stock_currency`)
   - US → USD, GB → GBP, DE → EUR, etc.

**"Other Holdings" Währungsverteilung:**

Für "Other Holdings" wird die Currency Allocation des ETFs genutzt, **MINUS** der Währungen der Top Holdings:

```python
# Beispiel EUNL:
# - Top 15 Holdings: 25% des ETFs in USD
# - Currency Allocation Gesamt: 72.5% USD
# - Other Holdings USD: 72.5% - 25% = 47.5% des ETFs
```

Dies vermeidet Doppelzählung und ergibt korrektes Währungsrisiko.

#### 4.4 Land (`_calculate_country_risk`)

**Länder-Priorität:**

1. **Explizites Country-Feld** (aus ETF-Detail-Datei oder User-CSV)
2. **ISIN-Ländercode** (erste 2 Zeichen)
   - US → USA, DE → Deutschland, GB → Großbritannien
3. **Währung als Proxy** (für ETF-Holdings ohne ISIN)
   - USD → USA, EUR → Eurozone

**Spezialbehandlung:**
- Cash-Positionen: Immer Währung verwenden (ISIN oft irreführend bei LU-ISINs)
- Filtering: ETFs die nicht aufgelöst wurden werden übersprungen

#### 4.5 Einzelpositionen (`_calculate_position_risk`)

**Aggregation:**
- Positionen werden nach normalisiertem Namen gruppiert
- Alle Cash-Positionen werden zu "Cash" zusammengefasst
- Ticker-Symbol wird für Labels verwendet

**Name-Normalisierung:**
```python
"Apple Inc." → "apple inc"
"APPLE INC" → "apple inc"
"Apple Inc Class A" → "apple inc"
```

**Konfliktauflösung:**
- Höchste Sektor-Priorität gewinnt (CSV > ISIN/ETF-Details > ETF)
- Ticker-Symbol wird aktualisiert wenn vorhanden

### 5. Visualisierung

**`src/visualizer.py`**

Erstellt interaktive Plotly-Visualisierungen:

#### 5.1 Treemap

```python
def _create_treemap(df, category, max_items=30):
    # Diskrete Farbskala für alle Kategorien
    # "Other Holdings" → hellblau (#ADD8E6)
    # Ticker-Symbole als Labels (falls vorhanden)
```

#### 5.2 Pie Chart

```python
def _create_pie_chart(df, category, max_items=10):
    # Top N Positionen + "Sonstige"
    # Ticker-Symbole für Einzelpositionen
    # "Other Holdings" → hellblau
```

#### 5.3 Bar Chart

```python
def _create_bar_chart(df, category, max_items=30):
    # Risiko-Schwellenwerte:
    # > 10% → rot
    # 5-10% → gelb
    # < 5% → grün
```

**User-konfigurierbare Limits:**

In `app.py` (Sidebar):
```python
max_positions_treemap = st.slider("Max. Positionen in Treemap", 10, 100, 30, 5)
max_positions_pie = st.slider("Max. Positionen in Pie Chart", 5, 30, 10, 5)
max_positions_bar = st.slider("Max. Positionen in Bar Chart", 10, 100, 30, 10)
```

### 6. Spezial-Features

#### 6.1 Dynamisches Ticker-Sektor-Mapping

**`src/ticker_sector_mapper.py`**

Intelligentes Caching-System für Ticker-zu-Sektor-Zuordnungen:

```python
class TickerSectorMapper:
    def get_sector_for_ticker(ticker: str, use_cache: bool = True):
        # 1. Lokaler Cache (data/ticker_sector_cache.json)
        # 2. Yahoo Finance API
        # 3. OpenFIGI API (Fallback)
        # Cache-Dauer: 90 Tage
```

**Management-Script:** `manage_ticker_cache.py`
```bash
python manage_ticker_cache.py stats     # Statistiken
python manage_ticker_cache.py add AAPL Technology
python manage_ticker_cache.py fetch TSLA  # Force refresh
```

#### 6.2 Wechselkurs-Management

**`src/exchange_rate.py`**

```python
class ExchangeRateManager:
    def get_rate(from_currency: str, to_currency: str = 'EUR'):
        # Quelle: EZB-API
        # Cache: 24h
        # Fallback: Statische Rates
```

#### 6.3 Historie-Tracking

**`src/database.py`**

SQLite-Datenbank für Portfolio-Historie:

```python
def save_analysis(portfolio_data: Dict, risk_data: Dict):
    # Speichert:
    # - Timestamp
    # - Total Value
    # - Positions (JSON)
    # - Risk Data (JSON)
```

**TODO:** Timeline-Visualisierungen

#### 6.4 Cash-Toggle

In der "Einzelpositionen"-Ansicht:

```python
exclude_cash = st.checkbox("Cash ausblenden")
if exclude_cash:
    positions_filtered = risk_data['positions'][
        risk_data['positions']['Position'] != 'Cash'
    ].copy()
    # Neuberechnung der Prozentsätze
```

### 7. Export-Funktionen

**`src/export.py`**

```python
def export_to_excel(risk_data: Dict) -> bytes:
    # Erstellt .xlsx mit mehreren Sheets
    # - Anlageklasse
    # - Sektor
    # - Währung
    # - Land
    # - Einzelpositionen

def export_to_ods(risk_data: Dict) -> bytes:
    # LibreOffice-Format
```

## Datenstrukturen

### Portfolio Data (nach CSV-Parse)

```python
{
    'total_value': 50000.0,
    'positions': [
        {
            'name': 'Apple Inc',
            'type': 'Stock',
            'isin': 'US0378331005',
            'ticker_symbol': 'AAPL',
            'shares': 10,
            'value': 2000.0,
            'currency': 'USD',
            'sector_from_pp': 'Technology'  # Aus PP Taxonomie
        },
        {
            'name': 'iShares Core MSCI World',
            'type': 'ETF',
            'isin': 'IE00B4L5Y983',
            'ticker_symbol': 'EUNL',
            'shares': 50,
            'value': 5000.0,
            'currency': 'EUR'
        }
    ]
}
```

### ETF Details (aus Detail-Datei)

```python
{
    'ticker': 'EUNL',
    'isin': 'IE00B4L5Y983',
    'name': 'iShares Core MSCI World UCITS ETF',
    'type': 'Stock',  # ETF-Typ
    'region': 'World',
    'currency': 'USD',
    'ter': '0.20',
    'country_allocation': [
        {'name': 'US', 'weight': 0.708},
        {'name': 'JP', 'weight': 0.062}
    ],
    'sector_allocation': [
        {'name': 'Technology', 'weight': 0.245},
        {'name': 'Financial Services', 'weight': 0.152}
    ],
    'currency_allocation': [
        {'name': 'USD', 'weight': 0.725},
        {'name': 'JPY', 'weight': 0.062}
    ],
    'holdings': [
        {
            'name': 'Apple Inc',
            'weight': 0.0498,
            'currency': 'USD',
            'sector': 'Technology',
            'country': 'US'
        }
    ]
}
```

### Expanded Positions (nach ETF-Auflösung)

```python
[
    {
        'name': 'Apple Inc',
        'type': 'Stock',
        'value': 2249.0,  # 2000 direkt + 249 aus ETF
        'currency': 'USD',
        'sector': 'Technology',
        'country': 'US',
        'source_etf': 'iShares Core MSCI World',  # Falls aus ETF
        'original_type': 'ETF_Holding',
        'sector_source': 'etf_details',  # Priorität 1
        'etf_type': 'Stock'  # Aus ETF Metadata
    }
]
```

### Risk Data (Output)

```python
{
    'asset_class': pd.DataFrame([...]),  # Anlageklasse
    'sector': pd.DataFrame([...]),       # Sektor
    'currency': pd.DataFrame([...]),     # Währung
    'country': pd.DataFrame([...]),      # Land
    'positions': pd.DataFrame([...]),    # Einzelpositionen
    'total_value': 50000.0
}
```

## Bekannte Limitierungen

### ETF-Daten

- **Yahoo Finance:** Stellt für europäische ETFs meist keine Holdings bereit
- **Web-Scraping:** Fragil, bricht bei Website-Änderungen
- **Lösung:** ETF-Detail-Dateien manuell pflegen

### "Other Holdings" Behandlung

**Problem:** Bei ETFs mit nur Top 10-15 Holdings fehlen Allokationsdaten für "Other Holdings"

**Lösung in neuer Struktur:**
- ETF-Detail-Dateien enthalten vollständige Sektor/Land/Währungsverteilungen
- "Other Holdings" wird in Sektor/Land/Währung-Ansichten über Gesamt-Allokation behandelt
- In Einzelpositionen-Ansicht: "Other Holdings - {ETF Name}" pro ETF

### Sektor-Mapping

- **Herausforderung:** Verschiedene Taxonomien (GICS, MSCI, PP custom)
- **Lösung:** Normalisierung + User kann in PP Taxonomie überschreiben (höchste Priorität)

## Performance-Optimierungen

### Caching

1. **ETF-Daten:** 7 Tage (konfigurierbar)
2. **Wechselkurse:** 24 Stunden
3. **Ticker-Sektor-Mapping:** 90 Tage

### Batch-Verarbeitung

- Alle API-Calls werden gecacht
- CSV-Parsing ist optimiert für große Dateien
- ETF-Detail-Dateien werden lazy geladen

## Testing

### Testdaten

- `Testdepot.csv`: Minimales Portfolio für Entwicklung
- ETF-Detail-Dateien in `data/etf_details/`: Vorab generierte Detail-Daten für Tests

### Debug-Modus

Aktiviere Debug-Output in `risk_calculator.py`:
```python
DEBUG = True  # Zeigt detaillierte Verarbeitungsschritte
```

## Deployment

### Docker

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
```

### Volumes

```yaml
volumes:
  - ./data:/app/data  # Persistente Daten
```

## Erweiterungen

### Neue ETF-Datenquelle

1. Erstelle neue Fetch-Methode in `etf_data_fetcher.py`
2. Integriere in `get_etf_holdings()` Fallback-Kette
3. Oder: Erstelle ETF-Detail-Datei (bevorzugt)

### Neue Analyse-Dimension

1. Füge `_calculate_xyz_risk()` in `risk_calculator.py` hinzu
2. Erweitere `calculate_cluster_risks()` Return-Dict
3. Neuer Tab in `app.py`
4. Visualisierung in `visualizer.py`

## Changelog

### 2026-03-02: Morningstar CSV-Importer (Option A)

- ✅ **`src/morningstar_csv_importer.py`:** Liest `pp_data_fetched.csv` (Ausgabe von [pp-portfolio-classifier](https://github.com/Alfons1Qto12/pp-portfolio-classifier/tree/new-api-branch)), gruppiert nach ISIN, mappt Taxonomien (Asset Type, Country, Stock/Bond Sector, Holding) ins ClusterRisk-Format und schreibt `data/etf_details/{TICKER}.csv`.
- ✅ Nur ISINs mit Eintrag in `data/etf_isin_ticker_map.csv` werden geschrieben; fehlende werden übersprungen und gemeldet.
- ✅ Währungs-Allokation wird aus Länder-Allokation abgeleitet (wie beim justETF-Generator).
- ✅ Streamlit: Sidebar „🔄 ETF-Details“ → Expander „📥 Aus Morningstar (pp-portfolio-classifier) importieren“ mit Datei-Upload und Import-Button.
- ✅ CLI: `python -m src.morningstar_csv_importer [pp_data_fetched.csv]` mit Optionen `-o`, `-m`.
- Konzept: `docs/KONZEPT_Morningstar_Integration.md`.

### 2026-02-08: justETF Auto-Generator + Proxy-ISIN für Swap-ETFs

- ✅ **ETF-Detail-Generator** (`src/etf_detail_generator.py`): Automatische Generierung von ETF-Detail-Dateien durch Scraping von justETF.com
- ✅ **justETF-Scraper**: Session-basiertes Scraping mit Wicket AJAX-Calls für vollständige Länder-/Sektor-Allokationen, Holdings mit ISINs, und Metadaten
- ✅ **Country-to-Currency Mapping**: Automatische Ableitung der Währungs-Allokation aus Länder-Daten (~100 Länder gemappt)
- ✅ **Streamlit-Integration**: Sidebar mit ISIN/Ticker-Eingabe, Vorschau-Button und Generierungs-Button
- ✅ **Parser-Fix**: `etf_details_parser.py` unterstützt jetzt beide Section-Header-Formate (`# ETF Metadata` und `METADATA`) sowie Header-basiertes Holdings-Parsing (verschiedene Spaltenreihenfolgen)
- ✅ **Mock-Daten entfernt**: `mock_etf_holdings.py` gelöscht, da durch ETF-Detail-Dateien und Auto-Generator ersetzt
- ✅ **ISIN-Map Auto-Update**: Generierte ETFs werden automatisch in `data/etf_isin_ticker_map.csv` eingetragen
- ✅ **Proxy-ISIN für Swap-ETFs**: Swap-ETFs können eine Proxy-ISIN eines physisch replizierenden ETFs auf denselben Index angeben. Allokationen/Holdings werden vom Proxy gescrapet, Metadaten bleiben die des eigentlichen ETFs.
- ✅ **Datenquellen-Kennzeichnung**: ETF-Übersicht in der Sidebar zeigt Datenquelle pro ETF (🤖 auto, 🔗 Proxy, ✋ manuell)
- ✅ **Source-Feld in Metadata**: `Source` und optional `Proxy ISIN` werden in der ETF-Detail-CSV gespeichert
- ✅ **Batch-Update-Schutz**: Manuelle ETFs werden bei Batch-Updates übersprungen und sind in der UI als nicht-aktualisierbar gekennzeichnet

### 2026-02-04: Währungsrisiko & Commodities

- ✅ **Korrekte "Other Holdings" Währungsverteilung**: Verwendet ETF Currency Allocation minus Top Holdings (keine Doppelzählung)
- ✅ **Commodities ohne Währungsrisiko**: Gold, Rohstoffe werden aus Währungsberechnung ausgeschlossen
- ✅ **Gold ETC Support**: XGDU (Xetra Gold) als Commodity-ETF integriert
- ✅ **Commodities-Toggle**: Optional Commodities in Währungsansicht einblenden
- ✅ **CSV-Parser Optimierung**: Ticker-Sektor-Mapping nur für Aktien, nicht für ETFs
- ✅ **"Other Holdings" ergänzt**: Alle ETF-Detail-Dateien enthalten jetzt "Other Holdings" Einträge

### 2026-02-04: ETF-Detail-Struktur

- ✅ Neue strukturierte ETF-Detail-Dateien (`data/etf_details/*.csv`)
- ✅ Parser für ETF-Detail-Dateien (`src/etf_details_parser.py`)
- ✅ ISIN-zu-Ticker-Mapping (`data/etf_isin_ticker_map.csv`)
- ✅ Korrekte Behandlung von Money Market ETFs als Cash
- ✅ Vollständige Sektor/Land/Währungs-Allokationen pro ETF
- ✅ Priorisierung: ETF-Details > API-Fetcher

### 2026-02-03: CSV-Parser

- ✅ CSV-Parser für Portfolio Performance Vermögensaufstellung
- ✅ Entfernung des XML-Parsers
- ✅ Sektor-Priorität aus PP Taxonomie

### 2026-02-02: Ticker-Sektor-Mapping

- ✅ Dynamisches Ticker-zu-Sektor-Mapping mit Caching
- ✅ Management-Script für Cache-Verwaltung
- ✅ Yahoo Finance + OpenFIGI Integration

### 2026-02-01: Visualisierungs-Slider

- ✅ User-konfigurierbare Limits für Treemap/Pie/Bar
- ✅ Cash-Toggle für Einzelpositionen
- ✅ Ticker-Symbole in Visualisierungen

---

## 🔍 Diagnose-System (v1.2.0 - 2026-02-05)

### Zweck

Das Diagnose-System sammelt Warnungen und Fehler während des Parsings und der Risikoberechnung und zeigt sie direkt in der GUI an. Der Benutzer muss nicht mehr Terminal-Logs durchsuchen.

### Architektur

**`src/diagnostics.py`**:
- `DiagnosticLevel`: Enum für Schweregrad (INFO, WARNING, ERROR)
- `DiagnosticsCollector`: Sammelt strukturierte Meldungen mit Kategorie, Message und Details
- Globale Instanz: `get_diagnostics()` für einfache Verwendung

### Kategorien

1. **ETF-Daten**: Nicht auflösbare ETFs mit ISIN und Lösungsvorschlägen
2. **Branchen**: Aktien ohne Sektor-Information
3. **Parse-Fehler**: Probleme beim Lesen von ETF-Detail-Dateien

### Integration

**Parser & Calculator:**
```python
from src.diagnostics import get_diagnostics

diagnostics = get_diagnostics()
diagnostics.add_warning(
    'ETF-Daten',
    f'ETF "{name}" konnte nicht aufgelöst werden',
    f'ISIN: {isin}. Erstelle data/etf_details/{ticker}.csv'
)
```

**Streamlit App:**
```python
from src.diagnostics import get_diagnostics, reset_diagnostics

# Vor neuem Parsing
reset_diagnostics()

# Nach Berechnung
diagnostics = get_diagnostics()
summary = diagnostics.get_summary()

if summary['warnings'] > 0:
    with st.expander(f"⚠️ {summary['warnings']} Warnung(en)"):
        # Zeige gruppierte Warnungen
```

### Verwendung in Modulen

- **`csv_parser.py`**: Warnung bei fehlenden Branchen (nur für Stocks)
- **`risk_calculator.py`**: 
  - Warnung bei nicht auflösbaren ETFs
  - Warnung bei Aktien ohne Sektor-Information
- **`etf_details_parser.py`**: Fehler bei Parse-Problemen
- **`app.py`**: Anzeige aller gesammelten Diagnosen in Expander

---

**Erstellt mit ❤️ für Portfolio-Optimierung**
