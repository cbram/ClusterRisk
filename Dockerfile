FROM python:3.11-slim

# Arbeitsverzeichnis
WORKDIR /app

# System-Dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App-Code kopieren
COPY . .

# Daten-Verzeichnisse erstellen
RUN mkdir -p data/cache data

# Port freigeben
EXPOSE 8501

# Health Check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Streamlit Konfiguration
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# App starten
CMD ["streamlit", "run", "app.py"]
