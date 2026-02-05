#!/usr/bin/env python3
"""
Ticker-Sektor Cache Management Tool
Verwalte den Ticker-zu-Sektor Cache
"""

import sys
from pathlib import Path

# Sicherstellen, dass src importiert werden kann
sys.path.insert(0, str(Path(__file__).parent))

from src.ticker_sector_mapper import get_mapper
import json


def show_stats():
    """Zeige Cache-Statistiken"""
    mapper = get_mapper()
    stats = mapper.get_cache_stats()
    
    print("\n📊 Ticker-Sektor Cache Statistiken")
    print("=" * 50)
    print(f"Gesamt-Einträge: {stats['total']}")
    print(f"\nQuellen:")
    for source, count in stats['by_source'].items():
        print(f"  - {source}: {count}")
    
    if stats['oldest']:
        print(f"\nÄltester Eintrag: {stats['oldest']}")
    if stats['newest']:
        print(f"Neuester Eintrag: {stats['newest']}")


def list_cache():
    """Liste alle Cache-Einträge"""
    mapper = get_mapper()
    
    print("\n📋 Alle Cache-Einträge")
    print("=" * 50)
    
    # Sortiere nach Ticker
    sorted_tickers = sorted(mapper.cache.items())
    
    for ticker, data in sorted_tickers:
        sector = data.get('sector', 'Unknown')
        source = data.get('source', 'unknown')
        timestamp = data.get('timestamp', 'N/A')[:10]  # Nur Datum
        
        print(f"{ticker:15} → {sector:25} ({source}, {timestamp})")


def add_ticker(ticker: str, sector: str):
    """Füge einen Ticker manuell hinzu"""
    mapper = get_mapper()
    mapper.manual_update(ticker, sector)
    print(f"\n✅ {ticker} → {sector} hinzugefügt")


def remove_ticker(ticker: str):
    """Entferne einen Ticker aus dem Cache"""
    mapper = get_mapper()
    ticker = ticker.upper().strip()
    
    if ticker in mapper.cache:
        del mapper.cache[ticker]
        mapper._save_cache()
        print(f"\n✅ {ticker} aus Cache entfernt")
    else:
        print(f"\n❌ {ticker} nicht im Cache gefunden")


def clear_cache():
    """Lösche den kompletten Cache"""
    mapper = get_mapper()
    
    response = input("\n⚠️  Willst du wirklich den kompletten Cache löschen? (ja/nein): ")
    if response.lower() in ['ja', 'yes', 'j', 'y']:
        mapper.clear_cache()
        print("✅ Cache gelöscht")
    else:
        print("❌ Abgebrochen")


def fetch_ticker(ticker: str):
    """Hole Sektor für einen Ticker (mit API-Call)"""
    mapper = get_mapper()
    
    print(f"\n🔍 Hole Sektor für {ticker}...")
    sector = mapper.get_sector(ticker, use_cache=False)  # Force API call
    print(f"✅ {ticker} → {sector}")


def main():
    """Hauptfunktion"""
    
    if len(sys.argv) < 2:
        print("""
Ticker-Sektor Cache Management Tool

Verwendung:
    python manage_ticker_cache.py <command> [args]

Befehle:
    stats               Zeige Cache-Statistiken
    list                Liste alle Einträge
    add <TICKER> <SECTOR>   Füge Ticker hinzu
    remove <TICKER>     Entferne Ticker
    clear               Lösche kompletten Cache
    fetch <TICKER>      Hole Sektor von API (force refresh)

Beispiele:
    python manage_ticker_cache.py stats
    python manage_ticker_cache.py list
    python manage_ticker_cache.py add AAPL Technology
    python manage_ticker_cache.py remove AAPL
    python manage_ticker_cache.py fetch TSLA
        """)
        return
    
    command = sys.argv[1].lower()
    
    if command == 'stats':
        show_stats()
    
    elif command == 'list':
        list_cache()
    
    elif command == 'add':
        if len(sys.argv) < 4:
            print("❌ Fehler: Ticker und Sektor erforderlich")
            print("Beispiel: python manage_ticker_cache.py add AAPL Technology")
            return
        ticker = sys.argv[2]
        sector = ' '.join(sys.argv[3:])  # Erlaubt Sektoren mit Leerzeichen
        add_ticker(ticker, sector)
    
    elif command == 'remove':
        if len(sys.argv) < 3:
            print("❌ Fehler: Ticker erforderlich")
            return
        ticker = sys.argv[2]
        remove_ticker(ticker)
    
    elif command == 'clear':
        clear_cache()
    
    elif command == 'fetch':
        if len(sys.argv) < 3:
            print("❌ Fehler: Ticker erforderlich")
            return
        ticker = sys.argv[2]
        fetch_ticker(ticker)
    
    else:
        print(f"❌ Unbekannter Befehl: {command}")
        print("Nutze 'python manage_ticker_cache.py' ohne Argumente für Hilfe")


if __name__ == "__main__":
    main()
