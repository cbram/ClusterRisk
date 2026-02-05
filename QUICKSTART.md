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

## 📋 Erste Schritte

1. **Portfolio Performance XML exportieren**
   - Öffne Portfolio Performance
   - Datei → Exportieren → XML
   - Speichere die Datei

2. **App öffnen**
   - Browser öffnet sich automatisch
   - Falls nicht: http://localhost:8501

3. **XML hochladen**
   - Klicke auf "Browse files"
   - Wähle deine XML-Datei

4. **Analysen erkunden**
   - Tabs: Anlageklasse, Branche, Währung, Einzelpositionen
   - Exportiere Ergebnisse als Excel/LibreOffice

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

### Cache-Dauer anpassen

In der App-Sidebar kannst du die Cache-Dauer für ETF-Daten einstellen (1-30 Tage).

### Eigene ETF-Mappings hinzufügen

Bearbeite `src/etf_data_fetcher.py` und füge deine ISINs hinzu:

```python
isin_to_ticker_map = {
    'DEINE_ISIN': 'TICKER',
    # z.B.
    'IE00B4L5Y983': 'IWDA.AS',
}
```

## 📊 Verzeichnisstruktur

```
ClusterRisk/
├── app.py              # Hauptanwendung
├── start.sh            # Start-Script (macOS)
├── requirements.txt    # Python Dependencies
├── Dockerfile          # Docker Image
├── docker-compose.yml  # Docker Compose Config
├── src/                # Source Code
│   ├── xml_parser.py
│   ├── etf_data_fetcher.py
│   ├── risk_calculator.py
│   ├── visualizer.py
│   ├── export.py
│   └── database.py
└── data/               # Daten & Cache
    ├── cache/          # ETF-Daten Cache
    └── history.db      # Analyse-Historie
```

## ❓ Troubleshooting

### "Module not found" Fehler

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### ETF-Daten werden nicht gefunden

- Cache löschen: `rm -rf data/cache/*`
- ISIN-zu-Ticker Mapping in `src/etf_data_fetcher.py` hinzufügen

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

- [ ] Erste Analyse durchführen
- [ ] Export als Excel/LibreOffice testen
- [ ] Cache-Einstellungen optimieren
- [ ] Docker-Deployment auf Unraid (optional)
- [ ] Historie-Funktion nutzen

Viel Erfolg mit deiner Portfolio-Analyse! 📊
