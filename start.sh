#!/bin/bash

# ClusterRisk - Lokaler Start-Script
# Dieses Script startet die ClusterRisk App lokal auf dem Mac

echo "🚀 ClusterRisk wird gestartet..."
echo ""

# Prüfe ob Python installiert ist
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 ist nicht installiert!"
    echo "Bitte installiere Python 3.9 oder höher."
    exit 1
fi

# Prüfe ob Virtual Environment existiert
if [ ! -d "venv" ]; then
    echo "📦 Erstelle Virtual Environment..."
    python3 -m venv venv
    echo "✅ Virtual Environment erstellt"
fi

# Aktiviere Virtual Environment
echo "🔧 Aktiviere Virtual Environment..."
source venv/bin/activate

# Installiere/Update Dependencies
echo "📥 Installiere Dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Prüfe ob Installation erfolgreich war
if [ $? -ne 0 ]; then
    echo "❌ Fehler bei der Installation der Dependencies!"
    exit 1
fi

echo "✅ Dependencies installiert"
echo ""
echo "🌐 Starte ClusterRisk Web-App..."
echo ""
echo "📊 Die App läuft auf: http://localhost:8501"
echo "⌨️  Zum Beenden: Ctrl+C"
echo ""

# Starte Streamlit
streamlit run app.py
