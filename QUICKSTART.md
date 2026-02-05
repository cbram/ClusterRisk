# ClusterRisk - Quick Start Guide

## 🚀 Schnellstart (macOS)

### Methode 1: Start-Script (Empfohlen)

```bash
cd /Users/chbram/Documents/Arduino/ClusterRisk
./start.sh
```

Das Script:
- Erstellt automatisch ein Virtual Environment
- Installiert alle Dependencies
- Startet die App auf http://localhost:8501

### Methode 2: Manuell

```bash
cd /Users/chbram/Documents/Arduino/ClusterRisk

# Virtual Environment erstellen (nur beim ersten Mal)
python3 -m venv venv
source venv/bin/activate

# Dependencies installieren (nur beim ersten Mal)
pip install -r requirements.txt

# App starten
streamlit run app.py
```

### Methode 3: Docker

```bash
cd /Users/chbram/Documents/Arduino/ClusterRisk
docker-compose up -d
```

# ClusterRisk - Quick Start Guide

## 🚀 Schnellstart (macOS)

### Voraussetzungen

1. **Portfolio Performance** installieren
   - Download: https://www.portfolio-performance.info/
   - Kostenlose Open-Source Depot-Verwaltung
   - Wird benötigt für CSV-Export

2. **Python 3.9+** (auf macOS meist vorinstalliert)
   ```bash
   python3 --version
   ```

### Methode 1: Start-Script (Empfohlen)

```bash
cd /Users/chbram/Documents/Arduino/ClusterRisk
./start.sh
```

Das Script:
- Erstellt automatisch ein Virtual Environment
- Installiert alle Dependencies
- Startet die App auf http://localhost:8501

### Methode 2: Manuell

```bash
cd /Users/chbram/Documents/Arduino/ClusterRisk

# Virtual Environment erstellen (nur beim ersten Mal)
python3 -m venv venv
source venv/bin/activate

# Dependencies installieren (nur beim ersten Mal)
pip install -r requirements.txt

# App starten
streamlit run app.py
```

### Methode 3: Docker

```bash
cd /Users/chbram/Documents/Arduino/ClusterRisk
docker-compose up -d
```

## 📋 Erste Schritte

### 1. Portfolio Performance CSV exportieren

1. Öffne **Portfolio Performance**
2. Gehe zu **Berichte** → **Vermögensaufstellung**
3. Aktiviere folgende Spalten (rechts oben):
   - ✅ Bestand
   - ✅ Name
   - ✅ Symbol (Ticker)
   - ✅ ISIN
   - ✅ Kurs
   - ✅ Marktwert
   - ✅ Branchen (GICS, Sektoren)
4. Klicke auf **Daten Exportieren** → **CSV**
5. Speichere die Datei

### 2. App öffnen

- Browser öffnet sich automatisch
- Falls nicht: http://localhost:8501

### 3. CSV hochladen

- Klicke auf **"Browse files"** in der Sidebar
- Wähle deine **Portfolio Performance CSV-Datei**
- Die Analyse startet automatisch

### 4. Analysen erkunden

- **Anlageklasse**: Verteilung nach Asset-Typen
- **Branche/Sektor**: Branchen-Exposition
- **Währung**: Währungsrisiko (mit Commodities-Toggle)
- **Land**: Geografisches Risiko
- **Einzelpositionen**: Detaillierte Exposition inkl. ETF-Durchschau

### 5. Export

- Wähle Format: Excel oder LibreOffice
- Klicke Download-Button
- Datei enthält alle Analysen

## 🐳 Unraid Deployment

### Installation

1. **Docker Image bauen (auf deinem Mac)**
```bash
cd /Users/chbram/Documents/Arduino/ClusterRisk
docker build -t clusterrisk:latest .
```

2. **Image exportieren**
```bash
docker save clusterrisk:latest > clusterrisk.tar
```

3. **Auf Unraid hochladen**
   - Kopiere `clusterrisk.tar` auf deinen Unraid Server
   - Lade es: `docker load < clusterrisk.tar`

4. **Container erstellen**
   - Community Applications → Add Container
   - Name: `ClusterRisk`
   - Repository: `clusterrisk:latest`
   - Port: `8501:8501`
   - Volume: `/mnt/user/appdata/clusterrisk/data:/app/data`

### Alternative: Docker Compose auf Unraid

Kopiere `docker-compose.yml` auf deinen Unraid Server und starte:

```bash
docker-compose up -d
```

## 🔧 Konfiguration

### ETF-Detail-Dateien pflegen

**Empfohlen:** Erstelle für deine ETFs Detail-Dateien in `data/etf_details/`

Beispiel: `data/etf_details/EUNL.csv`
```csv
METADATA
ISIN,IE00B4L5Y983
Name,iShares Core MSCI World
Ticker,EUNL
Type,Stock
...
```

Siehe [README.md](README.md) für vollständiges Format.

### Cache-Dauer anpassen

In der App-Sidebar kannst du die Cache-Dauer für ETF-Daten einstellen (1-30 Tage).

### Visualisierungs-Limits

In der Sidebar kannst du anpassen:
- **Treemap**: 10-100 Positionen (Standard: 30)
- **Pie Chart**: 5-30 Positionen (Standard: 10)
- **Bar Chart**: 10-100 Positionen (Standard: 30)

### Toggles

- **Cash ausblenden** (Einzelpositionen): Fokus auf investierte Positionen
- **Commodities einblenden** (Währung): Zeigt Rohstoffe optional

## 📊 Verzeichnisstruktur

```
ClusterRisk/
├── app.py              # Hauptanwendung
├── start.sh            # Start-Script (macOS)
├── requirements.txt    # Python Dependencies
├── Dockerfile          # Docker Image
├── docker-compose.yml  # Docker Compose Config
├── src/                # Source Code
│   ├── csv_parser.py          # Portfolio Performance CSV Parser
│   ├── etf_details_parser.py  # ETF-Detail-Dateien Parser
│   ├── risk_calculator.py     # Klumpenrisiko-Berechnung
│   ├── visualizer.py          # Visualisierungen
│   ├── export.py              # Export-Funktionen
│   ├── database.py            # Historie-Verwaltung
│   └── ...
└── data/               # Daten & Cache
    ├── etf_details/    # ETF-Detail-Dateien (empfohlen)
    ├── cache/          # ETF & Wechselkurs Cache
    └── history.db      # Analyse-Historie
```

## ❓ Troubleshooting

### "Module not found" Fehler

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "Portfolio erfolgreich geladen: 0 Positionen"

- **Prüfe CSV-Format**: Muss von Portfolio Performance "Vermögensaufstellung" exportiert sein
- **Prüfe Spalten**: Benötigt: Bestand, Name, Symbol, ISIN, Kurs, Marktwert
- **Testdatei**: Nutze `Testdepot.csv` zum Testen

### ETF wird nicht aufgelöst

- **Erstelle ETF-Detail-Datei**: Siehe [README.md](README.md) "ETF-Detail-Dateien"
- **Fallback**: `data/user_etf_holdings.csv` pflegen
- **Cache löschen**: `rm -rf data/cache/*`

### Port bereits belegt

Ändere den Port in `docker-compose.yml` oder starte Streamlit mit:

```bash
streamlit run app.py --server.port 8502
```

## 📞 Support

Bei Problemen:
1. Prüfe die Logs
2. Lösche den Cache
3. Erstelle ein GitHub Issue

## 🎯 Nächste Schritte

- ✅ Erste Analyse mit deinem Portfolio durchführen
- ✅ ETF-Detail-Dateien für deine ETFs erstellen (siehe README.md)
- ✅ Export als Excel/LibreOffice testen
- ✅ Cache-Einstellungen optimieren
- ✅ Docker-Deployment auf Unraid (optional)
- ✅ Historie-Funktion nutzen für Entwicklungs-Tracking

Vollständige Dokumentation in [README.md](README.md) und [CLAUDE.md](CLAUDE.md).

Viel Erfolg mit deiner Portfolio-Analyse! 📊
