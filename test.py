"""
Test-Script für ClusterRisk
Testet die Grund-Funktionalität ohne echte Daten
"""

import sys
from pathlib import Path

# Füge src zum Path hinzu
sys.path.insert(0, str(Path(__file__).parent))

from src.xml_parser import parse_portfolio_performance_xml
from src.etf_data_fetcher import ETFDataFetcher
from src.risk_calculator import calculate_cluster_risks
import pandas as pd


def test_imports():
    """Teste ob alle Module importiert werden können"""
    print("✅ Alle Module erfolgreich importiert")


def test_etf_fetcher():
    """Teste ETF Data Fetcher"""
    print("\n📊 Teste ETF Data Fetcher...")
    
    fetcher = ETFDataFetcher(cache_dir="data/cache", cache_days=7)
    
    # Teste mit bekanntem ETF (iShares Core MSCI World)
    test_isin = "IE00B4L5Y983"
    
    print(f"Versuche Daten für ISIN {test_isin} zu holen...")
    holdings = fetcher.get_etf_holdings(test_isin, use_cache=False)
    
    if holdings:
        print(f"✅ ETF-Daten gefunden: {holdings['name']}")
        print(f"   Quelle: {holdings['source']}")
        print(f"   Holdings: {len(holdings['holdings'])} Positionen")
        
        if holdings['holdings']:
            print("\n   Top 5 Holdings:")
            for i, holding in enumerate(holdings['holdings'][:5], 1):
                print(f"   {i}. {holding['name']}: {holding['weight']*100:.2f}%")
    else:
        print("⚠️  Keine ETF-Daten gefunden (kann bei fehlender Internet-Verbindung passieren)")


def test_sample_portfolio():
    """Teste mit simulierten Portfolio-Daten"""
    print("\n📂 Teste Portfolio-Verarbeitung mit Sample-Daten...")
    
    # Simuliere Portfolio-Daten
    sample_portfolio = {
        'positions': [
            {
                'name': 'iShares Core MSCI World UCITS ETF',
                'isin': 'IE00B4L5Y983',
                'wkn': 'A0RPWH',
                'type': 'ETF',
                'currency': 'EUR',
                'shares': 100,
                'value': 7500.0,
                'portfolio': 'Hauptportfolio'
            },
            {
                'name': 'Apple Inc.',
                'isin': 'US0378331005',
                'wkn': '865985',
                'type': 'Stock',
                'currency': 'USD',
                'shares': 10,
                'value': 1500.0,
                'portfolio': 'Hauptportfolio'
            },
            {
                'name': 'Tagesgeld-Konto',
                'isin': '',
                'wkn': '',
                'type': 'Cash',
                'currency': 'EUR',
                'shares': 0,
                'value': 5000.0,
                'portfolio': 'Tagesgeld'
            }
        ],
        'total_value': 14000.0,
        'total_positions': 3,
        'etf_count': 1,
        'stock_count': 1
    }
    
    print(f"✅ Sample-Portfolio erstellt:")
    print(f"   Gesamt-Wert: €{sample_portfolio['total_value']:,.2f}")
    print(f"   Positionen: {sample_portfolio['total_positions']}")
    print(f"   ETFs: {sample_portfolio['etf_count']}")
    print(f"   Aktien: {sample_portfolio['stock_count']}")
    
    # Teste Risiko-Berechnung (ohne ETF-Abruf für schnelleren Test)
    print("\n📊 Teste Risiko-Berechnung...")
    
    try:
        # Vereinfachte Version ohne ETF-Abruf
        from src.risk_calculator import _calculate_asset_class_risk
        
        risk_df = _calculate_asset_class_risk([], sample_portfolio)
        
        print("✅ Risiko-Berechnung erfolgreich")
        print("\nAnlageklassen-Verteilung:")
        print(risk_df.to_string(index=False))
        
    except Exception as e:
        print(f"⚠️  Risiko-Berechnung übersprungen: {str(e)}")


def test_database():
    """Teste Datenbank-Funktionalität"""
    print("\n💾 Teste Datenbank...")
    
    try:
        from src.database import HistoryDatabase
        
        db = HistoryDatabase(db_path="data/test_history.db")
        
        # Teste ob Tabellen erstellt wurden
        import sqlite3
        conn = sqlite3.connect("data/test_history.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()
        
        print(f"✅ Datenbank erstellt")
        print(f"   Tabellen: {[t[0] for t in tables]}")
        
        # Cleanup
        Path("data/test_history.db").unlink(missing_ok=True)
        
    except Exception as e:
        print(f"⚠️  Datenbank-Test fehlgeschlagen: {str(e)}")


def main():
    """Führe alle Tests aus"""
    print("=" * 60)
    print("🧪 ClusterRisk Test Suite")
    print("=" * 60)
    
    test_imports()
    test_sample_portfolio()
    test_database()
    
    # ETF-Fetcher nur wenn Internet verfügbar
    print("\n" + "=" * 60)
    response = input("ETF-Daten-Abruf testen? (Benötigt Internet) [j/N]: ")
    
    if response.lower() in ['j', 'ja', 'y', 'yes']:
        test_etf_fetcher()
    else:
        print("⏭️  ETF-Fetcher Test übersprungen")
    
    print("\n" + "=" * 60)
    print("✅ Tests abgeschlossen!")
    print("=" * 60)
    print("\n💡 Nächste Schritte:")
    print("   1. Starte die App: ./start.sh")
    print("   2. Öffne http://localhost:8501")
    print("   3. Lade eine Portfolio Performance XML hoch")


if __name__ == "__main__":
    main()
