# Changelog - ClusterRisk

## [1.2.0] - 2026-02-05 - Diagnose-System in GUI

### ✨ Neue Features

**Diagnose-System:**
- ✅ **Warnungen & Fehler in GUI**: Keine Terminal-Logs mehr notwendig
  - Fehlende ETF-Daten mit ISIN und Lösungsvorschlägen
  - Aktien ohne Branchen-Information werden aufgelistet
  - Parse-Fehler bei ETF-Detail-Dateien
  - Gruppierung nach Kategorie (ETF-Daten, Branchen, etc.)
- ✅ **Erweiterbarer Expander**: Automatisch geöffnet bei Fehlern, geschlossen bei nur Warnungen
- ✅ **Klare Lösungsvorschläge**: Z.B. "Erstelle data/etf_details/[TICKER].csv"

### 📁 Neue Dateien

**Code:**
- `src/diagnostics.py` - Diagnose-System Modul
  - `DiagnosticsCollector` Klasse für strukturiertes Sammeln
  - Kategorisierung nach Schweregrad (INFO, WARNING, ERROR)
  - Globale Instanz für einfache Verwendung

### 🔧 Verbesserungen

- ✅ **Benutzerfreundlichkeit**: Sofortige Sichtbarkeit fehlender Daten
- ✅ **Code-Integration**: Diagnosen in Parser, Calculator und ETF-Details-Parser
- ✅ **Reset bei neuem Upload**: Diagnosen werden vor jedem neuen Parsing zurückgesetzt

### 📚 Dokumentation

- ✅ **VERSION**: Erhöht auf 1.2.0
- ✅ **CHANGELOG.md**: Dieser Eintrag

---

## [1.1.0] - 2026-02-04 - Währungsrisiko & Commodities

### ✨ Neue Features

**Korrektes Währungsrisiko:**
- ✅ **"Other Holdings" Währungsverteilung**: Verwendet ETF Currency Allocation minus Top Holdings Währungen
  - Vermeidet Doppelzählung
  - Ergibt korrektes Währungsrisiko für große ETF-Positionen
- ✅ **Commodities ohne Währungsrisiko**: Gold, Rohstoffe werden aus Währungsberechnung ausgeschlossen
- ✅ **Commodities-Toggle**: Optional Commodities in Währungsansicht einblenden als "Commodity (kein Währungsrisiko)"

**Gold & Commodity Support:**
- ✅ **Xetra Gold ETC (XGDU)**: Vollständig integriert
- ✅ **Type: Commodity**: In ETF-Detail-Dateien für korrekte Klassifizierung
- ✅ **Separate Anzeige**: Commodities erscheinen in Anlageklassen, nicht in Währungen

### 🔧 Verbesserungen

- ✅ **CSV-Parser Optimierung**: Ticker-Sektor-Mapping nur noch für Aktien, nicht für ETFs
- ✅ **"Other Holdings" ergänzt**: Alle ETF-Detail-Dateien enthalten jetzt "Other Holdings" Zeilen
- ✅ **Währungs-Toggle**: Zwei Ansichten verfügbar (mit/ohne Commodities)

### 📁 Neue Dateien

**ETF-Detail-Dateien:**
- `data/etf_details/XGDU.csv` - Xtrackers IE Physical Gold ETC Securities
- Alle bestehenden ETF-Detail-Dateien um "Other Holdings" erweitert

**Code:**
- `_calculate_currency_risk_with_commodities()` - Alternative Währungsberechnung mit Commodities
- `risk_data['currency_with_commodities']` - Neue Datenstruktur

### 🐛 Bugfixes

- ✅ **Doppelzählung**: "Other Holdings" Währungen werden nicht mehr doppelt gezählt
- ✅ **USD-Übergewichtung**: Korrektur durch richtige Currency Allocation Berechnung
- ✅ **ETF-Warnings**: Keine unnötigen Ticker-Sektor-Warnungen mehr für ETFs

### 📚 Dokumentation

- ✅ **README.md**: Neuer Abschnitt "Währungsrisiko & Commodities"
- ✅ **CLAUDE.md**: Erweitert um Currency Allocation Logik und Commodity-Behandlung
- ✅ **CHANGELOG_2026-02-04.md**: Detaillierte Änderungsdokumentation

---

## [1.0.0] - 2026-02-04 - ETF-Detail-Struktur

### ✨ Neue Features

**Strukturierte ETF-Detail-Dateien:**
- ✅ Neue strukturierte CSV-Dateien pro ETF in `data/etf_details/`
- ✅ Parser für ETF-Detail-Dateien (`src/etf_details_parser.py`)
- ✅ ISIN-zu-Ticker-Mapping (`data/etf_isin_ticker_map.csv`)
- ✅ Vollständige Sektor/Land/Währungs-Allokationen pro ETF
- ✅ ETF-Typ-Information (Stock, Money Market, Bond, Commodity)

**Korrekte ETF-Behandlung:**
- ✅ Money Market ETFs werden als `Cash` klassifiziert
- ✅ Priorisierung: ETF-Details > User-CSV > Mock > API

### 📁 ETF-Detail-Dateien erstellt

- `EUNL.csv` - iShares Core MSCI World
- `VGWD.csv` - Vanguard FTSE All-World High Dividend Yield
- `AEEM.csv` - Amundi MSCI Emerging Markets
- `AUM5.csv` - Amundi S&P 500 Swap
- `GERD.csv` - L&G Gerd Kommer Multifactor Equity
- `XEON.csv` - Xtrackers EUR Overnight Rate Swap

### 🔧 Code-Änderungen

**`src/risk_calculator.py`:**
- Import von `etf_details_parser`
- `_load_isin_ticker_map()` - Lädt ISIN-Ticker-Mapping
- `_expand_etf_holdings()` - Priorisiert ETF-Detail-Dateien
- `_calculate_asset_class_risk()` - Money Market ETFs → Cash

**`app.py`:**
- Entfernung XML-Parser-Support
- Nur noch CSV-Upload

### 📚 Dokumentation

- ✅ **CLAUDE.md**: Vollständige technische Dokumentation erstellt
- ✅ **README.md**: Aktualisiert mit ETF-Detail-Struktur
- ✅ **CHANGELOG_2026-02-04.md**: Detaillierte Änderungen

---

## [0.9.0] - 2026-02-03 - CSV-Parser

### ✨ Neue Features

- ✅ CSV-Parser für Portfolio Performance "Vermögensaufstellung"
- ✅ Sektor-Priorität aus PP Taxonomie (höchste Priorität)
- ✅ Multi-Portfolio/Konto Support
- ✅ Geldmarkt-ETF Erkennung via `Notiz`-Feld

### 🗑️ Entfernt

- ❌ XML-Parser (`src/xml_parser.py`)

---

## [0.8.0] - 2026-02-02 - Ticker-Sektor-Mapping

### ✨ Neue Features

- ✅ Dynamisches Ticker-zu-Sektor-Mapping mit Caching
- ✅ Management-Script (`manage_ticker_cache.py`)
- ✅ Yahoo Finance + OpenFIGI Integration
- ✅ 90 Tage Cache

---

## [0.7.0] - 2026-02-01 - Visualisierungs-Slider

### ✨ Neue Features

- ✅ User-konfigurierbare Limits für Treemap/Pie/Bar Charts
- ✅ Cash-Toggle für Einzelpositionen
- ✅ Ticker-Symbole in Visualisierungen
- ✅ Einheitliche Farben für "Other Holdings" (hellblau)

---

## [0.6.0] - 2026-01-31 - Automatische Wechselkurse

### ✨ Neue Features

- ✅ Automatische Wechselkurse von EZB-API
- ✅ 24h-Caching
- ✅ Statische Fallback-Rates

---

**Erstellt mit ❤️ für Portfolio-Optimierung**
