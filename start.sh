#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV="$SCRIPT_DIR/venv"
HASH_FILE="$VENV/.requirements_hash"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"

# Create venv if missing
if [ ! -d "$VENV" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV"
fi

source "$VENV/bin/activate"

# Install requirements only if requirements.txt changed
CURRENT_HASH="$(md5 -q "$REQUIREMENTS" 2>/dev/null || md5sum "$REQUIREMENTS" | cut -d' ' -f1)"
if [ ! -f "$HASH_FILE" ] || [ "$CURRENT_HASH" != "$(cat "$HASH_FILE")" ]; then
    echo "Installing requirements..."
    pip install -q --upgrade pip
    pip install -q -r "$REQUIREMENTS"
    echo "$CURRENT_HASH" > "$HASH_FILE"
    echo "Requirements up to date."
fi

echo "Starting ClusterRisk on http://localhost:8501"
streamlit run "$SCRIPT_DIR/app.py"
