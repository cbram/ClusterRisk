# ClusterRisk - System-Architektur

## Datenfluss

```
Portfolio Performance CSV
         ↓
    csv_parser.py
         ↓
  risk_calculator.py ←→ etf_details_parser.py (data/etf_details/*.csv)
         ↓                        ↑
         │                   morningstar_fetcher.py (wenn Datei fehlt/veraltet)
         │                        ↑
         │                   etf_data_fetcher.py (Fallback: justETF, Yahoo)
         ↓
   visualizer.py
         ↓
  app.py (Streamlit) → export.py | database.py
```

## ETF-Datenquellen (Priorität)

1. **ETF-Detail-Dateien** (`data/etf_details/{TICKER}.csv`) – lokal, Parser
2. **Morningstar-API** – automatisch bei fehlender/veralteter Datei, speichert in CSV
3. **Fetcher** (`etf_data_fetcher.py`) – justETF-Scraping, Yahoo Finance

## Komponenten

| Komponente | Datei | Aufgabe |
|------------|-------|---------|
| Frontend | `app.py` | Streamlit, Upload, Tabs, Sidebar, Beispiel-Button |
| Parser | `csv_parser.py` | PP CSV → Positionen, Typen, Sektor aus PP |
| Risk Calculator | `risk_calculator.py` | ETF-Expansion, 5 Risiko-Dimensionen |
| ETF Parser | `etf_details_parser.py` | Liest ETF-Detail-CSVs |
| Morningstar | `morningstar_fetcher.py` | API-Abruf, speichert via `etf_detail_writer.py` |
| Fetcher | `etf_data_fetcher.py` | Fallback: justETF, Yahoo |
| Visualizer | `visualizer.py` | Treemap, Pie, Bar |
| Export | `export.py` | Excel, LibreOffice |
| Database | `database.py` | Historie, SQLite |

## Risiko-Dimensionen

- **Anlageklasse:** Stock, Bond, Cash, Commodity (Money Market → Cash)
- **Sektor:** Aktien + Bonds (Bonds: Corporate, Government, …)
- **Währung:** Handelswährung, Commodities ausgeschlossen
- **Land:** ISIN-Ländercode, Währung-Fallback
- **Einzelpositionen:** Aggregiert, ETF-Durchschau

## Konfiguration

- **ETF-Update:** 1–90 Tage (Sidebar-Slider), steuert Veraltungsprüfung
- **ISIN-Map:** `data/etf_isin_ticker_map.csv`
- **Ticker-Sektor:** `data/ticker_sector_cache.json`, `manage_ticker_cache.py`
- **Wechselkurse:** EZB-API, 24h Cache

## Erweiterungen

- **Neue Analyse-Dimension:** `risk_calculator.py` → `app.py` (Tab) → `visualizer.py`
- **Neue ETF-Datenquelle:** `etf_data_fetcher.py` oder ETF-Detail-Datei (bevorzugt)
