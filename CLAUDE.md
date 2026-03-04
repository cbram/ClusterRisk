# ClusterRisk - Technische Dokumentation

## Architektur

```
Portfolio Performance CSV → csv_parser.py
         ↓
  risk_calculator.py ←→ etf_details_parser.py (data/etf_details/*.csv)
         ↓                        ↑
         │                   morningstar_fetcher.py (auto bei fehlend/veraltet)
         │                   etf_data_fetcher.py (Fallback)
         ↓
   visualizer.py → app.py (Streamlit)
```

## ETF-Datenquellen (Priorität)

1. **ETF-Detail-Dateien** (`data/etf_details/{TICKER}.csv`) – Parser
2. **Morningstar-API** – automatisch, speichert in CSV via `etf_detail_writer.py`
3. **Fetcher** – justETF, Yahoo (Fallback)

## Datenfluss

### Input: `csv_parser.py`

- Liest PP Vermögensaufstellung (CSV, Semikolon)
- Positionen: Bestand, Name, Symbol, ISIN, Kurs, Marktwert
- Typ: Stock, ETF, Cash, Commodity
- Sektor: PP-Taxonomie (höchste Priorität), Notiz für Cash/Geldmarkt

### ETF-Auflösung: `risk_calculator._expand_etf_holdings()`

1. Lokale Datei (nicht veraltet) → `etf_details_parser`
2. Sonst: Morningstar → speichern → nutzen
3. Sonst: Fetcher (justETF, Yahoo) → speichern → nutzen

### ETF-Detail-Format

`data/etf_details/{TICKER}.csv`: METADATA, COUNTRY_ALLOCATION, SECTOR_ALLOCATION, CURRENCY_ALLOCATION, TOP_HOLDINGS

- **Type:** Stock, Bond, Money Market, Commodity
- **Money Market** → Cash in Anlageklassen
- **Commodity** → kein Währungsrisiko
- **Proxy ISIN** für Swap-ETFs (Allokation vom Proxy)

### Risiko-Berechnung

- **Sektor-Priorität:** CSV (PP) > ISIN/ETF-Details > ETF-Holdings
- **Währung:** Handelswährung der Aktie; Commodities ausgeschlossen
- **Other Holdings:** Currency Allocation minus Top Holdings (keine Doppelzählung)
- **Land:** ISIN-Ländercode, 2- und 3-Buchstaben-Codes

### Visualisierung

- Treemap, Pie, Bar (Plotly)
- Slider: max. Positionen pro Chart
- "Other Holdings" → hellblau
- Bar: einheitliche Farbpalette (keine Risiko-Farben mehr)

## Module

| Modul | Zweck |
|-------|-------|
| `csv_parser.py` | PP CSV parsen |
| `risk_calculator.py` | ETF-Expansion, 5 Risiko-Dimensionen |
| `etf_details_parser.py` | ETF-Detail-CSVs lesen |
| `morningstar_fetcher.py` | Morningstar-API (Basis: pp-portfolio-classifier) |
| `etf_detail_writer.py` | Morningstar/Fetcher-Output → CSV speichern |
| `etf_data_fetcher.py` | Fallback: justETF, Yahoo |
| `etf_detail_generator.py` | justETF-Scraper (CLI, keine App-UI) |
| `morningstar_csv_importer.py` | pp_data_fetched.csv → ETF-Detail-CSVs (CLI) |
| `ticker_sector_mapper.py` | Ticker→Sektor (Cache, Yahoo, OpenFIGI) |
| `exchange_rate.py` | EZB-Wechselkurse |
| `diagnostics.py` | Warnungen/Fehler in GUI |

## Diagnose-System

`src/diagnostics.py` – sammelt Warnungen (ETF-Daten, Branchen, Parse-Fehler), Anzeige in App-Expander.

## Bekannte Limitierungen

- Morningstar: Token von öffentlicher Webseite
- Fetcher: justETF/Yahoo für EU-ETFs oft unzuverlässig
- Testdaten: `data/Beispiel_Vermoegensaufstellung.csv`

## Erweiterungen

- **Neue Dimension:** `_calculate_xyz_risk()` in risk_calculator → Tab in app → visualizer
- **Neue ETF-Quelle:** etf_data_fetcher oder ETF-Detail-Datei
