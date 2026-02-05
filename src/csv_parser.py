"""
CSV Parser für Portfolio Performance Vermögensaufstellung
Parst die CSV-Exporte aus PP (viel einfacher als XML!)
"""

import pandas as pd
from typing import Dict, List
from datetime import datetime
from .ticker_sector_mapper import get_sector_for_ticker


def parse_portfolio_csv(filepath: str) -> Dict:
    """
    Parst Portfolio Performance CSV-Export (Vermögensaufstellung)
    
    Format:
        Bestand;Name;Symbol;Kurs;Marktwert;Anteil in %;Notiz
        10;APPLE INC;AAPL;USD 269,48;2.279,86;12,78;
        "";Testkonto;;;3.298,15;18,49;
    
    Returns:
        Dict mit 'positions', 'total_value', etc.
    """
    print(f"DEBUG: Parsing CSV: {filepath}")
    
    # Lese CSV mit Semikolon als Separator
    df = pd.read_csv(filepath, sep=';', encoding='utf-8')
    
    print(f"DEBUG: CSV geladen - {len(df)} Zeilen")
    
    # Portfolio-Daten initialisieren
    portfolio_data = {
        'positions': [],
        'total_value': 0.0,
        'total_positions': 0,
        'etf_count': 0,
        'stock_count': 0,
        'parse_date': datetime.now().isoformat()
    }
    
    # Zeilen durchgehen
    for idx, row in df.iterrows():
        # Überspringe Summen-Zeilen
        if pd.isna(row['Name']) or 'Summe' in str(row['Name']):
            continue
        
        name = str(row['Name']).strip()
        
        # Prüfe ob es Cash ist (kein Bestand, nur Marktwert)
        bestand_str = str(row['Bestand']).strip()
        
        # Prüfe Notiz-Feld für spezielle Marker
        notiz = ''
        if 'Notiz' in row and pd.notna(row['Notiz']):
            notiz = str(row['Notiz']).strip().upper()
        
        # Cash-Erkennung: Leerer Bestand ODER Name enthält "Konto" ODER Notiz="CASH"/"GELDMARKT"
        is_cash = (not bestand_str or bestand_str == '' or bestand_str == '""' or 
                   'konto' in name.lower() or 'cash' in name.lower() or
                   notiz in ['CASH', 'GELDMARKT', 'TAGESGELD'])
        
        if is_cash:
            # Das ist ein Cash-Konto
            marktwert_str = str(row['Marktwert']).replace('.', '').replace(',', '.')
            try:
                value = float(marktwert_str)
            except:
                continue
            
            portfolio_data['positions'].append({
                'name': name,
                'isin': '',
                'wkn': '',
                'type': 'Cash',
                'currency': 'EUR',
                'ticker_symbol': '',
                'shares': 0,
                'value': value,
                'portfolio': 'Cash',
                'sector_from_pp': None
            })
            print(f"DEBUG:   Cash-Position: {name} = €{value:.2f}")
        
        else:
            # Das ist ein Wertpapier
            try:
                shares = float(bestand_str.replace(',', '.'))
            except:
                continue
            
            # Marktwert parsen (Format: "2.279,86")
            marktwert_str = str(row['Marktwert']).replace('.', '').replace(',', '.')
            try:
                value = float(marktwert_str)
            except:
                continue
            
            # Symbol/Ticker
            symbol = str(row['Symbol']).strip() if pd.notna(row['Symbol']) else ''
            
            # ISIN (falls vorhanden)
            isin = ''
            if 'ISIN' in row and pd.notna(row['ISIN']):
                isin = str(row['ISIN']).strip()
            
            # Währung aus Kurs-Feld extrahieren (Format: "USD 269,48" oder "148,314")
            kurs_str = str(row['Kurs']).strip()
            currency = 'EUR'  # Default
            if ' ' in kurs_str:
                # Format: "USD 269,48"
                currency_part = kurs_str.split(' ')[0].strip()
                if len(currency_part) == 3 and currency_part.isupper():
                    currency = currency_part
            
            # Prüfe Notiz-Feld für spezielle Marker
            notiz = ''
            if 'Notiz' in row and pd.notna(row['Notiz']):
                notiz = str(row['Notiz']).strip().upper()
            
            # Typ bestimmen
            sec_type = _determine_security_type(name, symbol)
            
            # Override: Falls Notiz "CASH" oder "GELDMARKT" enthält -> als Cash behandeln
            if notiz and any(keyword in notiz for keyword in ['CASH', 'GELDMARKT', 'TAGESGELD']):
                sec_type = 'Cash'
                print(f"DEBUG:   Notiz-Override: {name} -> Cash (Notiz: {notiz})")
            
            # Sektor/Branche aus CSV auslesen (Priorität 1)
            sector = None
            sector_column_names = [
                'Branchen (GICS, Sektoren) (Ebene 1)',
                'Branchen (GICS, Sektoren)',  # Variante ohne "(Ebene 1)"
                'Branche',
                'Sektor',
                'Sector'
            ]
            for col_name in sector_column_names:
                if col_name in row and pd.notna(row[col_name]):
                    sector_value = str(row[col_name]).strip()
                    if sector_value and sector_value != '':
                        sector = _normalize_sector_name(sector_value)
                        print(f"DEBUG:   Branche aus CSV: {name} -> {sector} (Original: {sector_value})")
                        break
            
            # Fallback: Sektor aus Ticker ableiten (nur für Aktien, nicht für ETFs)
            if not sector and sec_type == 'Stock':
                sector = _get_sector_from_ticker(symbol)
                if sector:
                    print(f"DEBUG:   Branche aus Ticker: {name} ({symbol}) -> {sector}")
                else:
                    print(f"DEBUG:   ⚠️  Keine Branche gefunden für {name} (Ticker: {symbol}, kein Mapping)")
            
            portfolio_data['positions'].append({
                'name': name,
                'isin': isin,  # ISIN aus CSV
                'wkn': '',
                'type': sec_type,
                'currency': currency,  # Währung aus Kurs-Feld extrahiert
                'ticker_symbol': symbol,
                'shares': shares,
                'value': value,
                'portfolio': 'Portfolio',
                'sector_from_pp': sector  # Sektor aus Ticker-Mapping
            })
            print(f"DEBUG:   Position: {name} ({sec_type}, {currency}, {sector}, {isin[:10] if isin else 'no ISIN'}) = {shares} × €{value/shares:.2f} = €{value:.2f}")
    
    # Statistiken
    portfolio_data['total_positions'] = len(portfolio_data['positions'])
    portfolio_data['total_value'] = sum(pos['value'] for pos in portfolio_data['positions'])
    portfolio_data['etf_count'] = sum(1 for pos in portfolio_data['positions'] if pos['type'] == 'ETF')
    portfolio_data['stock_count'] = sum(1 for pos in portfolio_data['positions'] if pos['type'] == 'Stock')
    
    print(f"DEBUG: CSV-Parsing erfolgreich:")
    print(f"DEBUG:   {portfolio_data['total_positions']} Positionen")
    print(f"DEBUG:   Gesamtwert: €{portfolio_data['total_value']:.2f}")
    
    return portfolio_data


def _determine_security_type(name: str, symbol: str) -> str:
    """
    Bestimmt den Typ eines Wertpapiers basierend auf Name und Symbol
    """
    name_upper = name.upper()
    symbol_upper = symbol.upper() if symbol else ''
    
    # Geldmarkt-ETFs als Cash behandeln
    money_market_keywords = [
        'MONEY MARKET', 'GELDMARKT', 'OVERNIGHT', 'LIQUIDITY', 
        'LIQUIDITÄT', 'TAGESGELD', 'CASH FUND', 'XEON'
    ]
    if any(keyword in name_upper for keyword in money_market_keywords):
        return 'Cash'
    
    # ETF-Erkennung
    etf_keywords = [
        'ETF', 'UCITS', 'INDEX FUND', 'TRACKER',
        'ISHARES', 'ISHSIII', 'ISHS', 'EUNL',
        'VANGUARD', 'XTRACKERS', 'LYXOR', 'AMUNDI',
        'SPDR', 'INVESCO', 'WISDOMTREE', 'FRANKLIN',
        'MSCI WORLD', 'MSCI EM', 'MSCI EUROPE',
        'S&P 500', 'NASDAQ', 'DAX', 'STOXX'
    ]
    
    if any(keyword in name_upper or keyword in symbol_upper for keyword in etf_keywords):
        return 'ETF'
    elif 'GOLD' in name_upper or 'SILVER' in name_upper or 'COMMODITY' in name_upper:
        return 'Commodity'
    elif 'BOND' in name_upper or 'ANLEIHE' in name_upper:
        return 'Bond'
    else:
        return 'Stock'


def _get_sector_from_ticker(ticker: str) -> str:
    """
    Gibt den Sektor für einen Ticker zurück.
    Nutzt intelligentes Caching mit API-Fallback.
    """
    if not ticker:
        return None
    
    # Nutze den neuen Mapper mit Cache
    sector = get_sector_for_ticker(ticker, use_cache=True)
    
    # Wenn "Unknown" zurückkommt, gib None zurück (für Fallback-Logik)
    return sector if sector != 'Unknown' else None


def _normalize_sector_name(sector_name: str) -> str:
    """
    Normalisiert Sektornamen von Portfolio Performance (deutsch) 
    zu englischen Standardnamen.
    """
    sector_upper = sector_name.upper()
    
    # Mapping deutscher GICS-Sektoren (aus Portfolio Performance) zu englischen Namen
    sector_mapping = {
        # Exakte Namen aus Portfolio Performance Screenshot
        'INFORMATIONSTECHNOLOGIE': 'Technology',
        'TECHNOLOGIE': 'Technology',
        'IT': 'Technology',
        
        'FINANZWESEN': 'Financial Services',
        'FINANZEN': 'Financial Services',
        'FINANCIALS': 'Financial Services',
        
        'GESUNDHEITSWESEN': 'Healthcare',
        'GESUNDHEIT': 'Healthcare',
        'HEALTH CARE': 'Healthcare',
        
        'NICHT-BASISKONSUMGÜTER': 'Consumer Cyclical',
        'ZYKLISCHE KONSUMGÜTER': 'Consumer Cyclical',
        'CONSUMER DISCRETIONARY': 'Consumer Cyclical',
        'KONSUMGÜTER': 'Consumer Cyclical',
        
        'BASISKONSUMGÜTER': 'Consumer Staples',
        'VERBRAUCHSGÜTER': 'Consumer Staples',
        'CONSUMER STAPLES': 'Consumer Staples',
        
        'ENERGIE': 'Energy',
        'ENERGY': 'Energy',
        
        'KOMMUNIKATIONSDIENSTE': 'Communication Services',
        'KOMMUNIKATION': 'Communication Services',
        'COMMUNICATION SERVICES': 'Communication Services',
        'TELEKOMMUNIKATION': 'Communication Services',
        
        'INDUSTRIE': 'Industrials',
        'INDUSTRIALS': 'Industrials',
        
        # "Roh-, Hilfs- & Betriebsstoffe" aus dem Screenshot
        'ROH-, HILFS- & BETRIEBSSTOFFE': 'Materials',
        'ROHSTOFFE': 'Materials',
        'WERKSTOFFE': 'Materials',
        'MATERIALIEN': 'Materials',
        'MATERIALS': 'Materials',
        
        # "Versorgungsbetriebe" aus dem Screenshot
        'VERSORGUNGSBETRIEBE': 'Utilities',
        'VERSORGER': 'Utilities',
        'UTILITIES': 'Utilities',
        
        'IMMOBILIEN': 'Real Estate',
        'REAL ESTATE': 'Real Estate',
    }
    
    # Suche nach exakter Übereinstimmung
    if sector_upper in sector_mapping:
        return sector_mapping[sector_upper]
    
    # Fallback: Originalnamen zurückgeben (in Title Case)
    return sector_name.title()

