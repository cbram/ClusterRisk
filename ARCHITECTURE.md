# ClusterRisk - System-Architektur

## Datenfluss

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         PORTFOLIO PERFORMANCE                            │
│                              (XML Export)                                │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         XML PARSER (xml_parser.py)                       │
│                                                                          │
│  • Liest Portfolio Performance XML                                       │
│  • Extrahiert Positionen (ETFs, Aktien, Rohstoffe, Tagesgeld)          │
│  • Identifiziert ETFs anhand von ISINs                                  │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                   ETF DATA FETCHER (etf_data_fetcher.py)                 │
│                                                                          │
│  Datenquellen (in Reihenfolge):                                         │
│  1. Cache (data/cache/)                                                  │
│  2. justETF.com           ─────┐                                        │
│  3. extraETF.com          ─────┤                                        │
│  4. iShares direkt        ─────┼───► Holdings + Gewichtung             │
│  5. Yahoo Finance         ─────┘                                        │
│                                                                          │
│  Output: ETF-Zusammensetzung (Top 50 Holdings + Gewichtung)            │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                   RISK CALCULATOR (risk_calculator.py)                   │
│                                                                          │
│  ETF-DURCHSCHAU:                                                         │
│  ┌────────────────────────────────────────────────────────────┐        │
│  │  ETF 1 (€10,000)                                            │        │
│  │  ├─ Apple (10%) ───────► € 1,000                           │        │
│  │  ├─ Microsoft (8%) ─────► €   800                          │        │
│  │  └─ Amazon (5%) ────────► €   500                          │        │
│  │                                                             │        │
│  │  ETF 2 (€5,000)                                             │        │
│  │  ├─ Apple (15%) ────────► €   750                          │        │
│  │  └─ Tesla (10%) ────────► €   500                          │        │
│  │                                                             │        │
│  │  Direkte Aktie: Apple ──► € 2,000                          │        │
│  │                                                             │        │
│  │  AGGREGIERT: Apple = € 3,750 (aus 3 Quellen!)              │        │
│  └────────────────────────────────────────────────────────────┘        │
│                                                                          │
│  BERECHNET:                                                              │
│  • Anlageklassen-Verteilung                                             │
│  • Sektor/Branchen-Exposition                                           │
│  • Währungsrisiko                                                       │
│  • Einzelpositions-Klumpenrisiko (wichtigste Analyse!)                  │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         VISUALIZER (visualizer.py)                       │
│                                                                          │
│  VISUALISIERUNGEN:                                                       │
│  ├─ Treemap (hierarchisch)                                              │
│  ├─ Pie Chart (Verteilung)                                              │
│  ├─ Bar Chart (Top N mit Risiko-Schwellen)                             │
│  └─ Tabellen (sortierbar, filterbar)                                    │
│                                                                          │
│  RISIKO-INDIKATOREN:                                                     │
│  • ROT:   > 10% (Hohes Risiko)                                          │
│  • GELB:  5-10% (Mittleres Risiko)                                      │
│  • GRÜN:  < 5%  (Niedriges Risiko)                                      │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            │                    │                    │
            ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  STREAMLIT UI    │  │  EXPORT          │  │  DATABASE        │
│  (app.py)        │  │  (export.py)     │  │  (database.py)   │
│                  │  │                  │  │                  │
│  • File Upload   │  │  • Excel (.xlsx) │  │  • SQLite        │
│  • Interaktive   │  │  • LibreOffice   │  │  • Historie      │
│    Dashboards    │  │    (.ods)        │  │  • Zeitreihen    │
│  • Settings      │  │  • Multi-Sheet   │  │  • Vergleiche    │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

## Komponenten-Übersicht

### 1. **Frontend (Streamlit)**
- **Datei**: `app.py`
- **Aufgaben**:
  - Web-Interface
  - File Upload
  - Tab-Navigation
  - Settings-Management
  
### 2. **Parser**
- **Datei**: `src/xml_parser.py`
- **Aufgaben**:
  - XML-Parsing
  - Position-Extraktion
  - Typ-Erkennung (ETF, Aktie, etc.)

### 3. **ETF Data Fetcher**
- **Datei**: `src/etf_data_fetcher.py`
- **Aufgaben**:
  - Multi-Source Daten-Abruf
  - Caching
  - ISIN → Ticker Mapping

### 4. **Risk Calculator**
- **Datei**: `src/risk_calculator.py`
- **Aufgaben**:
  - ETF-Durchschau
  - Positions-Aggregation
  - Risiko-Berechnung

### 5. **Visualizer**
- **Datei**: `src/visualizer.py`
- **Aufgaben**:
  - Plotly-Charts
  - Risiko-Farbcodierung
  - Tabellen-Formatierung

### 6. **Export**
- **Datei**: `src/export.py`
- **Aufgaben**:
  - Excel-Export
  - LibreOffice-Export
  - Multi-Sheet-Erstellung

### 7. **Database**
- **Datei**: `src/database.py`
- **Aufgaben**:
  - Historie-Speicherung
  - Zeitreihen-Abfragen
  - SQLite-Management

## Daten-Strukturen

### Portfolio-Daten
```python
{
    'positions': [
        {
            'name': 'ETF Name',
            'isin': 'IE00B4L5Y983',
            'type': 'ETF',
            'value': 10000.0,
            'currency': 'EUR'
        }
    ],
    'total_value': 50000.0,
    'total_positions': 10
}
```

### ETF-Holdings
```python
{
    'isin': 'IE00B4L5Y983',
    'name': 'iShares Core MSCI World',
    'holdings': [
        {
            'name': 'Apple Inc.',
            'weight': 0.045  # 4.5%
        }
    ],
    'source': 'justETF'
}
```

### Risk-Daten
```python
{
    'asset_class': DataFrame,  # Anlageklassen
    'sector': DataFrame,       # Sektoren
    'currency': DataFrame,     # Währungen
    'positions': DataFrame,    # Einzelpositionen (wichtigste!)
    'total_value': 50000.0
}
```

## Deployment-Optionen

### 1. Lokal (macOS)
```bash
./start.sh
```
- Nutzt: Python Virtual Environment
- Port: 8501
- Daten: ./data/

### 2. Docker
```bash
docker-compose up -d
```
- Nutzt: Docker Container
- Port: 8501
- Daten: Volume Mount

### 3. Unraid
- Docker Container via UI
- Persistent Volumes
- Netzwerk-Zugriff
- 24/7 Verfügbarkeit

## Konfiguration

### Cache-Einstellungen
- **Speicherort**: `data/cache/`
- **Format**: JSON pro ISIN
- **Dauer**: 1-30 Tage (konfigurierbar)

### ISIN-Mappings
- **Datei**: `config.py`
- **Format**: `{'ISIN': 'Ticker'}`
- **Zweck**: Bessere Daten-Abruf-Erfolgsrate

### Risiko-Schwellenwerte
- **Hoch**: > 10%
- **Mittel**: 5-10%
- **Niedrig**: < 5%

## Erweiterungspunkte

### Neue ETF-Datenquelle hinzufügen
1. Methode in `etf_data_fetcher.py` erstellen
2. In `get_etf_holdings()` einbinden
3. Testen

### Neue Analyse-Dimension
1. Funktion in `risk_calculator.py` erstellen
2. Tab in `app.py` hinzufügen
3. Visualisierung in `visualizer.py` implementieren

### Neue Visualisierung
1. Funktion in `visualizer.py` erstellen
2. Plotly-Chart definieren
3. In entsprechendem Tab einbinden
