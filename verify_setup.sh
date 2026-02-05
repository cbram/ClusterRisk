#!/bin/bash

# ClusterRisk - Setup Verification Script
# Prüft ob alle Komponenten korrekt installiert sind

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                   ClusterRisk - Setup Verification                           ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

ERRORS=0
WARNINGS=0

# Funktion für Success-Meldungen
success() {
    echo "✅ $1"
}

# Funktion für Error-Meldungen
error() {
    echo "❌ $1"
    ERRORS=$((ERRORS + 1))
}

# Funktion für Warning-Meldungen
warning() {
    echo "⚠️  $1"
    WARNINGS=$((WARNINGS + 1))
}

# Funktion für Info-Meldungen
info() {
    echo "ℹ️  $1"
}

echo "🔍 Prüfe System-Requirements..."
echo ""

# Python Version prüfen
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 9 ]; then
        success "Python $PYTHON_VERSION gefunden"
    else
        error "Python $PYTHON_VERSION ist zu alt (benötigt: 3.9+)"
    fi
else
    error "Python 3 nicht gefunden"
fi

# Pip prüfen
if command -v pip3 &> /dev/null; then
    success "pip3 gefunden"
else
    warning "pip3 nicht gefunden (wird für Installation benötigt)"
fi

# Docker prüfen (optional)
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
    success "Docker $DOCKER_VERSION gefunden"
else
    info "Docker nicht gefunden (optional, nur für Container-Deployment)"
fi

# Docker Compose prüfen (optional)
if command -v docker-compose &> /dev/null; then
    success "Docker Compose gefunden"
else
    info "Docker Compose nicht gefunden (optional)"
fi

echo ""
echo "📂 Prüfe Projekt-Struktur..."
echo ""

# Haupt-Dateien prüfen
REQUIRED_FILES=(
    "app.py"
    "requirements.txt"
    "config.py"
    "start.sh"
    "Dockerfile"
    "docker-compose.yml"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        success "$file vorhanden"
    else
        error "$file fehlt"
    fi
done

# Source-Code prüfen
REQUIRED_SRC_FILES=(
    "src/__init__.py"
    "src/xml_parser.py"
    "src/etf_data_fetcher.py"
    "src/risk_calculator.py"
    "src/visualizer.py"
    "src/export.py"
    "src/database.py"
)

for file in "${REQUIRED_SRC_FILES[@]}"; do
    if [ -f "$file" ]; then
        success "$file vorhanden"
    else
        error "$file fehlt"
    fi
done

# Verzeichnisse prüfen
REQUIRED_DIRS=(
    "src"
    "data"
    "data/cache"
    ".streamlit"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        success "Verzeichnis $dir vorhanden"
    else
        error "Verzeichnis $dir fehlt"
    fi
done

echo ""
echo "📦 Prüfe Python Dependencies..."
echo ""

# Virtual Environment prüfen
if [ -d "venv" ]; then
    success "Virtual Environment existiert"
    
    # Aktiviere venv und prüfe Packages
    source venv/bin/activate 2>/dev/null
    
    if [ $? -eq 0 ]; then
        # Prüfe wichtige Packages
        PACKAGES=("streamlit" "pandas" "plotly" "lxml" "requests" "openpyxl")
        
        for package in "${PACKAGES[@]}"; do
            if python3 -c "import $package" 2>/dev/null; then
                success "Package $package installiert"
            else
                warning "Package $package nicht installiert"
            fi
        done
        
        deactivate 2>/dev/null
    else
        warning "Virtual Environment konnte nicht aktiviert werden"
    fi
else
    info "Virtual Environment nicht erstellt (wird bei erstem Start erstellt)"
fi

echo ""
echo "🔐 Prüfe Berechtigungen..."
echo ""

# start.sh Berechtigungen
if [ -x "start.sh" ]; then
    success "start.sh ist ausführbar"
else
    warning "start.sh ist nicht ausführbar"
    info "Lösung: chmod +x start.sh"
fi

# Daten-Verzeichnis Schreibrechte
if [ -w "data" ]; then
    success "data/ Verzeichnis ist beschreibbar"
else
    error "data/ Verzeichnis ist nicht beschreibbar"
fi

echo ""
echo "📊 Statistiken..."
echo ""

# Python Code Zeilen
if command -v wc &> /dev/null; then
    TOTAL_LINES=$(find . -name "*.py" -type f -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}')
    info "Python Code: ~$TOTAL_LINES Zeilen"
fi

# Dateien
FILE_COUNT=$(find . -type f | wc -l)
info "Gesamt-Dateien: $FILE_COUNT"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Ergebnis
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo "🎉 Perfekt! Setup ist vollständig."
    echo ""
    echo "🚀 Nächster Schritt:"
    echo "   ./start.sh"
    echo ""
    EXIT_CODE=0
elif [ $ERRORS -eq 0 ]; then
    echo "✅ Setup ist vollständig (mit $WARNINGS Warnungen)."
    echo ""
    echo "🚀 Nächster Schritt:"
    echo "   ./start.sh"
    echo ""
    EXIT_CODE=0
else
    echo "❌ Setup unvollständig: $ERRORS Fehler, $WARNINGS Warnungen"
    echo ""
    echo "🔧 Bitte behebe die Fehler vor dem Start."
    echo ""
    EXIT_CODE=1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exit $EXIT_CODE
