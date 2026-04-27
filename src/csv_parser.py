"""
CSV Parser für Portfolio Performance Vermögensaufstellung
Parst die CSV-Exporte aus PP (viel einfacher als XML!)
"""

import pandas as pd
from typing import Dict, List
from datetime import datetime
from .ticker_sector_mapper import get_sector_for_ticker
from .diagnostics import get_diagnostics


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
    
    # Branchen-Spalte flexibel ermitteln (verschiedene PP-Export-Formate)
    sector_column = _find_sector_column(df.columns.tolist())
    if sector_column:
        print(f"DEBUG: Branchen-Spalte erkannt: '{sector_column}'")
    
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
            
            # Sektor/Branche aus CSV auslesen (Priorität 1) – nutzt flexibel erkannte Spalte
            sector = None
            if sector_column and sector_column in row.index and pd.notna(row.get(sector_column)):
                sector_value = str(row[sector_column]).strip()
                if sector_value and sector_value != '':
                    sector = _normalize_sector_name(sector_value)
                    print(f"DEBUG:   Branche aus CSV: {name} -> {sector} (Original: {sector_value})")
            
            # Fallback: Sektor aus Ticker ableiten (nur für Aktien, nicht für ETFs)
            if not sector and sec_type == 'Stock':
                sector = _get_sector_from_ticker(symbol)
                if sector:
                    print(f"DEBUG:   Branche aus Ticker: {name} ({symbol}) -> {sector}")
                else:
                    print(f"DEBUG:   ⚠️  Keine Branche gefunden für {name} (Ticker: {symbol}, kein Mapping)")
                    # Diagnose: Keine Branche gefunden
                    diagnostics = get_diagnostics()
                    diagnostics.add_warning(
                        'Branchen',
                        f'Keine Branche für Aktie "{name}" gefunden',
                        f'Ticker: {symbol if symbol else "nicht vorhanden"}. Die Aktie wird unter "Unknown" kategorisiert.'
                    )
            
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
            price_per_share = value / shares if shares else 0.0
            print(f"DEBUG:   Position: {name} ({sec_type}, {currency}, {sector}, {isin[:10] if isin else 'no ISIN'}) = {shares} × €{price_per_share:.2f} = €{value:.2f}")
    
    # Statistiken
    portfolio_data['total_positions'] = len(portfolio_data['positions'])
    portfolio_data['total_value'] = sum(pos['value'] for pos in portfolio_data['positions'])
    portfolio_data['etf_count'] = sum(1 for pos in portfolio_data['positions'] if pos['type'] == 'ETF')
    portfolio_data['stock_count'] = sum(1 for pos in portfolio_data['positions'] if pos['type'] == 'Stock')
    
    print(f"DEBUG: CSV-Parsing erfolgreich:")
    print(f"DEBUG:   {portfolio_data['total_positions']} Positionen")
    print(f"DEBUG:   Gesamtwert: €{portfolio_data['total_value']:.2f}")
    
    return portfolio_data


def _find_sector_column(column_names: List[str]) -> str:
    """
    Ermittelt die Branchen/Sektor-Spalte flexibel aus den CSV-Spaltennamen.
    Unterstützt verschiedene Portfolio-Performance-Export-Formate und Varianten.
    """
    if not column_names:
        return ''
    # Exakte Kandidaten (Reihenfolge: spezifisch → allgemein)
    exact_candidates = [
        'Branchen (GICS, Sektoren) (Ebene 1)',
        'Branchen (GICS, Sektoren)',
        'Branchen (GICS)',           # aktuelle Test-CSV / kürzere PP-Variante
        'Branche',
        'Sektor',
        'Sector',
    ]
    for cand in exact_candidates:
        if cand in column_names:
            return cand
    # Fallback: Spalte, deren Name "Branche", "Sektor", "Sector" oder "GICS" enthält (case-insensitive)
    keywords = ('branche', 'sektor', 'sector', 'gics')
    for col in column_names:
        if col and isinstance(col, str) and any(kw in col.lower() for kw in keywords):
            return col
    return ''


def _determine_security_type(name: str, symbol: str) -> str:
    """
    Bestimmt den Typ eines Wertpapiers basierend auf Name und Symbol.
    ETF-Erkennung zuerst, damit Geldmarkt-ETFs (XEON) und Commodity-ETCs (XGDU)
    als ETF expandiert werden – der tatsächliche Typ kommt aus den ETF-Details.
    """
    name_upper = name.upper()
    symbol_upper = symbol.upper() if symbol else ''

    # ETF-Erkennung zuerst (inkl. XEON, XGDU – Typ aus ETF-Details)
    etf_keywords = [
        'ETF', 'ETC', 'UCITS', 'INDEX FUND', 'TRACKER',
        'ISHARES', 'ISHSIII', 'ISHS', 'EUNL', 'XEON', 'XGDU',
        'VANGUARD', 'XTRACKERS', 'LYXOR', 'AMUNDI',
        'SPDR', 'INVESCO', 'WISDOMTREE', 'FRANKLIN',
        'MSCI WORLD', 'MSCI EM', 'MSCI EUROPE',
        'S&P 500', 'NASDAQ', 'DAX', 'STOXX',
    ]
    if any(keyword in name_upper or keyword in symbol_upper for keyword in etf_keywords):
        return 'ETF'

    # Reine Cash-Konten (keine Wertpapiere)
    money_market_keywords = ['LIQUIDITÄT', 'TAGESGELD', 'OVERNIGHT', 'MONEY MARKET', 'GELDMARKT', 'CASH FUND']
    if any(keyword in name_upper for keyword in money_market_keywords):
        return 'Cash'

    if 'GOLD' in name_upper or 'SILVER' in name_upper or 'COMMODITY' in name_upper:
        return 'Commodity'
    if 'BOND' in name_upper or 'ANLEIHE' in name_upper:
        return 'Bond'
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


def _normalize_sector_input(s: str) -> str:
    """
    Bereinigt Sektor-Eingabe für robusten Abgleich: Leerzeichen, Zeichenvarianten.
    """
    if not s or not isinstance(s, str):
        return ''
    s = s.strip()
    # Mehrfach-Leerzeichen auf eines
    while '  ' in s:
        s = s.replace('  ', ' ')
    # Typografische Varianten vereinheitlichen (für Abgleich)
    s = s.replace('\u00a0', ' ')   # geschütztes Leer
    s = s.replace('–', '-').replace('—', '-')  # En/Em-Dash -> Bindestrich
    s = s.replace('&', ' UND ').replace(' und ', ' UND ')
    s = s.strip()
    return s


def _normalize_sector_name(sector_name: str) -> str:
    """
    Normalisiert Sektornamen von Portfolio Performance (deutsch/verschiedene Formate)
    zu englischen Standardnamen. Robust gegen Leerzeichen, &/und, Umlaute-Varianten.
    """
    if not sector_name or not isinstance(sector_name, str):
        return sector_name or ''
    normalized = _normalize_sector_input(sector_name)
    sector_upper = normalized.upper()
    # Umlaut-Varianten für Abgleich (z. B. Export als "ue" statt "ü")
    sector_upper_ascii = sector_upper.replace('Ü', 'UE').replace('Ä', 'AE').replace('Ö', 'OE')
    
    # Mapping: deutsche/englische Bezeichnungen -> Standard (längere Keys zuerst für Teilstring-Match)
    sector_mapping = [
        # Technology
        ('INFORMATIONSTECHNOLOGIE', 'Technology'),
        ('INFORMATION TECHNOLOGY', 'Technology'),
        ('TECHNOLOGIE', 'Technology'),
        ('IT', 'Technology'),
        # Financial Services
        ('FINANZDIENSTLEISTUNGEN', 'Financial Services'),
        ('FINANZWESEN', 'Financial Services'),
        ('FINANCIALS', 'Financial Services'),
        ('FINANZEN', 'Financial Services'),
        # Healthcare
        ('GESUNDHEITSWESEN', 'Healthcare'),
        ('HEALTH CARE', 'Healthcare'),
        ('GESUNDHEIT', 'Healthcare'),
        # Consumer Cyclical (Nicht-Basiskonsumgüter)
        ('NICHT-BASISKONSUMGÜTER', 'Consumer Cyclical'),
        ('NICHT-BASISKONSUMGUETER', 'Consumer Cyclical'),
        ('NICHT BASISKONSUMGÜTER', 'Consumer Cyclical'),
        ('NICHT BASISKONSUMGUETER', 'Consumer Cyclical'),
        ('ZYKLISCHE KONSUMGÜTER', 'Consumer Cyclical'),
        ('ZYKLISCHE KONSUMGUETER', 'Consumer Cyclical'),
        ('CONSUMER DISCRETIONARY', 'Consumer Cyclical'),
        ('KONSUMGÜTER', 'Consumer Cyclical'),
        ('KONSUMGUETER', 'Consumer Cyclical'),
        # Consumer Staples
        ('BASISKONSUMGÜTER', 'Consumer Staples'),
        ('BASISKONSUMGUETER', 'Consumer Staples'),
        ('VERBRAUCHSGÜTER', 'Consumer Staples'),
        ('CONSUMER STAPLES', 'Consumer Staples'),
        # Energy
        ('ENERGIE', 'Energy'),
        ('ENERGY', 'Energy'),
        # Communication
        ('KOMMUNIKATIONSDIENSTE', 'Communication Services'),
        ('COMMUNICATION SERVICES', 'Communication Services'),
        ('KOMMUNIKATION', 'Communication Services'),
        ('TELEKOMMUNIKATION', 'Communication Services'),
        # Industrials
        ('INDUSTRIE', 'Industrials'),
        ('INDUSTRIALS', 'Industrials'),
        # Materials – Roh-, Hilfs- & Betriebsstoffe (mehrere Schreibweisen)
        ('ROH-, HILFS- UND BETRIEBSSTOFFE', 'Materials'),
        ('ROH-, HILFS- & BETRIEBSSTOFFE', 'Materials'),
        ('ROH HILFS BETRIEBSSTOFFE', 'Materials'),
        ('HILFS- UND BETRIEBSSTOFFE', 'Materials'),
        ('ROH- HILFS- UND BETRIEBSSTOFFE', 'Materials'),
        ('BETRIEBSSTOFFE', 'Materials'),
        ('HILFSSTOFFE', 'Materials'),
        ('ROHSTOFFE', 'Materials'),
        ('WERKSTOFFE', 'Materials'),
        ('MATERIALIEN', 'Materials'),
        ('MATERIALS', 'Materials'),
        ('GRUNDSTOFFE', 'Materials'),
        ('BASIC MATERIALS', 'Materials'),
        # Utilities
        ('VERSORGUNGSBETRIEBE', 'Utilities'),
        ('VERSORGER', 'Utilities'),
        ('UTILITIES', 'Utilities'),
        # Real Estate
        ('IMMOBILIEN', 'Real Estate'),
        ('REAL ESTATE', 'Real Estate'),
    ]
    
    # 1) Exakter Abgleich (Original und ASCII-Umlaut-Variante)
    for key, value in sector_mapping:
        if sector_upper == key or sector_upper_ascii == key:
            return value
    # 2) Teilstring: Key kommt in Eingabe vor (längere Keys zuerst)
    for key, value in sector_mapping:
        if key in sector_upper or key in sector_upper_ascii:
            return value
    
    return sector_name.strip().title() if sector_name else ''

