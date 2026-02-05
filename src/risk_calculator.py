"""
Risk Calculator
Berechnet Klumpenrisiken über verschiedene Dimensionen
"""

import pandas as pd
from typing import Dict, List
from pathlib import Path
from src.etf_data_fetcher import ETFDataFetcher, get_stock_info
from src.etf_details_parser import get_etf_details_parser


def _load_isin_ticker_map() -> Dict[str, str]:
    """Lädt ISIN-zu-Ticker-Mapping aus CSV"""
    map_file = Path("data/etf_isin_ticker_map.csv")
    
    if not map_file.exists():
        print("⚠️  ISIN-Ticker-Mapping nicht gefunden: data/etf_isin_ticker_map.csv")
        return {}
    
    try:
        df = pd.read_csv(map_file)
        return dict(zip(df['ISIN'], df['Ticker']))
    except Exception as e:
        print(f"❌ Fehler beim Laden des ISIN-Ticker-Mappings: {e}")
        return {}


def calculate_cluster_risks(portfolio_data: Dict, use_cache: bool = True, cache_days: int = 7) -> Dict:
    """
    Berechnet Klumpenrisiken über alle Dimensionen
    
    Args:
        portfolio_data: Geparste Portfolio-Daten
        use_cache: Cache für ETF-Daten verwenden
        cache_days: Cache-Alter in Tagen
    
    Returns:
        Dict mit Risiko-Analysen für alle Dimensionen
    """
    
    fetcher = ETFDataFetcher(cache_days=cache_days)
    
    # ISIN-zu-Ticker-Mapping laden
    isin_ticker_map = _load_isin_ticker_map()
    
    # Alle Positionen mit ETF-Durchschau aufschlüsseln
    expanded_positions = _expand_etf_holdings(portfolio_data, fetcher, use_cache, isin_ticker_map)
    
    # Klumpenrisiken berechnen
    risk_data = {
        'asset_class': _calculate_asset_class_risk(expanded_positions, portfolio_data),
        'sector': _calculate_sector_risk(expanded_positions),
        'currency': _calculate_currency_risk(expanded_positions),
        'currency_with_commodities': _calculate_currency_risk_with_commodities(expanded_positions),
        'country': _calculate_country_risk(expanded_positions),
        'positions': _calculate_position_risk(expanded_positions),
        'total_value': portfolio_data['total_value']
    }
    
    return risk_data


def _expand_etf_holdings(portfolio_data: Dict, fetcher: ETFDataFetcher, use_cache: bool, isin_ticker_map: Dict[str, str]) -> List[Dict]:
    """
    Expandiert ETF-Positionen in ihre einzelnen Holdings
    
    Returns:
        Liste aller Einzelpositionen (inkl. aufgeschlüsselte ETFs)
    """
    expanded = []
    etf_parser = get_etf_details_parser()
    
    print(f"DEBUG: Expanding {len(portfolio_data['positions'])} positions...")
    
    for position in portfolio_data['positions']:
        print(f"DEBUG: Processing {position['name']} (Type: {position['type']})")
        
        if position['type'] == 'ETF' and position['isin']:
            print(f"DEBUG:   ETF detected with ISIN: {position['isin']}")
            
            # PRIORITÄT 1: Versuche ETF-Detail-Datei zu laden
            ticker = isin_ticker_map.get(position['isin'])
            etf_details = None
            
            if ticker:
                print(f"DEBUG:   Trying ETF detail file for ticker: {ticker}")
                etf_details = etf_parser.parse_etf_file(ticker)
            
            # Falls ETF-Detail-Datei vorhanden, verwende diese
            if etf_details:
                print(f"DEBUG:   ✅ ETF resolved via detail file! {len(etf_details['holdings'])} holdings found")
                
                # Sammle Währungsverteilung der Top Holdings (zur späteren Berechnung von "Other Holdings")
                top_holdings_currency_distribution = {}
                other_holdings_entry = None
                
                # Holdings aus Detail-Datei verarbeiten
                for holding in etf_details['holdings']:
                    holding_value = position['value'] * holding['weight']
                    
                    holding_currency = holding.get('currency', 'USD')
                    holding_sector = holding.get('sector', 'Unknown')
                    holding_country = holding.get('country', '')
                    
                    # Normalisiere Sektor-Namen
                    holding_sector = _normalize_sector_name(holding_sector)
                    
                    # Holding-Name: Bei "Other Holdings" den ETF-Namen hinzufügen
                    holding_name = holding['name']
                    is_other_holdings = 'Other Holdings' in holding_name or 'other holdings' in holding_name.lower()
                    
                    if is_other_holdings:
                        # "Other Holdings" speichern für spätere Verarbeitung
                        holding_name = f"Other Holdings - {position['name']}"
                        other_holdings_entry = {
                            'name': holding_name,
                            'weight': holding['weight'],
                            'value': holding_value,
                            'sector': holding_sector,
                            'country': holding_country
                        }
                        continue  # Erstmal überspringen, später verarbeiten
                    
                    # Sammle Währung der Top Holdings
                    if holding_currency not in top_holdings_currency_distribution:
                        top_holdings_currency_distribution[holding_currency] = 0.0
                    top_holdings_currency_distribution[holding_currency] += holding['weight']
                    
                    # Reguläre Holding-Verarbeitung (nicht "Other Holdings")
                    holding_info = {
                        'name': holding_name,
                        'type': etf_details.get('type', 'Stock'),  # Type aus Metadata
                        'value': holding_value,
                        'weight_in_portfolio': holding_value / portfolio_data['total_value'],
                        'currency': holding_currency,
                        'country': holding_country,
                        'source_etf': position['name'],
                        'original_type': 'ETF_Holding',
                        'sector': holding_sector,
                        'industry': holding_sector,
                        'sector_source': 'etf_details',  # MITTLERE PRIORITÄT
                        'etf_type': etf_details.get('type', 'Stock')  # ETF-Typ (Money Market, Stock, etc.)
                    }
                    
                    expanded.append(holding_info)
                    print(f"DEBUG:     Added holding: {holding_name} = €{holding_value:.2f} ({holding_currency}, {holding_sector})")
                
                # Verarbeite "Other Holdings" mit Currency Allocation
                if other_holdings_entry and etf_details.get('currency_allocation'):
                    print(f"DEBUG:     Processing Other Holdings with currency allocation")
                    
                    # Berechne Währungsverteilung für "Other Holdings"
                    # = ETF Gesamt-Währungsverteilung - Top Holdings Währungen
                    for currency_alloc in etf_details['currency_allocation']:
                        currency_name = currency_alloc['name']
                        # Gewicht der Währung im GESAMTEN ETF
                        total_currency_weight = currency_alloc['weight']
                        
                        # Gewicht der Währung in den Top Holdings
                        top_holdings_weight = top_holdings_currency_distribution.get(currency_name, 0.0)
                        
                        # Gewicht für "Other Holdings" = Gesamt - Top Holdings
                        other_currency_weight = total_currency_weight - top_holdings_weight
                        
                        # Überspringe wenn negativ oder sehr klein
                        if other_currency_weight <= 0.001:  # < 0.1%
                            continue
                        
                        # Berechne Wert für diese Währung in "Other Holdings"
                        # other_currency_weight ist bereits als Anteil am GESAMTEN ETF
                        # other_holdings_entry['value'] ist der Gesamtwert von "Other Holdings"
                        # Anteil dieser Währung an "Other Holdings"
                        currency_weight_in_other = other_currency_weight / other_holdings_entry['weight']
                        currency_value = other_holdings_entry['value'] * currency_weight_in_other
                        
                        holding_info = {
                            'name': other_holdings_entry['name'],
                            'type': etf_details.get('type', 'Stock'),
                            'value': currency_value,
                            'weight_in_portfolio': currency_value / portfolio_data['total_value'],
                            'currency': currency_name,
                            'country': other_holdings_entry['country'] if other_holdings_entry['country'] else 'Mixed',
                            'source_etf': position['name'],
                            'original_type': 'ETF_Holding',
                            'sector': other_holdings_entry['sector'],
                            'industry': other_holdings_entry['sector'],
                            'sector_source': 'etf_details',
                            'etf_type': etf_details.get('type', 'Stock')
                        }
                        
                        expanded.append(holding_info)
                        print(f"DEBUG:     Added Other Holdings ({currency_name}): €{currency_value:.2f} ({other_currency_weight*100:.1f}% of total ETF, {currency_weight_in_other*100:.1f}% of Other Holdings)")
                
                elif other_holdings_entry:
                    # Kein Currency Allocation vorhanden, nutze "Mixed"
                    print(f"DEBUG:     ⚠️  No currency allocation found, using Mixed for Other Holdings")
                    holding_info = {
                        'name': other_holdings_entry['name'],
                        'type': etf_details.get('type', 'Stock'),
                        'value': other_holdings_entry['value'],
                        'weight_in_portfolio': other_holdings_entry['value'] / portfolio_data['total_value'],
                        'currency': 'Mixed',
                        'country': other_holdings_entry['country'] if other_holdings_entry['country'] else 'Mixed',
                        'source_etf': position['name'],
                        'original_type': 'ETF_Holding',
                        'sector': other_holdings_entry['sector'],
                        'industry': other_holdings_entry['sector'],
                        'sector_source': 'etf_details',
                        'etf_type': etf_details.get('type', 'Stock')
                    }
                    expanded.append(holding_info)
                    print(f"DEBUG:     Added Other Holdings (Mixed): €{other_holdings_entry['value']:.2f}")
            
            # PRIORITÄT 2: Fallback zu bisherigem Fetcher (user_etf_holdings.csv, Mock, APIs)
            else:
                print(f"DEBUG:   No detail file found, falling back to fetcher...")
                # ETF auflösen via Fetcher
                ticker_symbol = position.get('ticker_symbol', '')
                holdings_data = fetcher.get_etf_holdings(
                    position['isin'], 
                    use_cache=use_cache,
                    ticker_symbol=ticker_symbol
                )
                
                if holdings_data and 'holdings' in holdings_data:
                    print(f"DEBUG:   ✅ ETF resolved via fetcher! {len(holdings_data['holdings'])} holdings found")
                    # Jede Holding als eigene Position
                    for holding in holdings_data['holdings']:
                        holding_value = position['value'] * holding['weight']
                        
                        # Währung der Holding verwenden (nicht die des ETFs!)
                        holding_currency = holding.get('currency', 'USD')  # Default USD für US-Aktien
                        holding_sector = holding.get('sector', 'Unknown')
                        holding_industry = holding.get('industry', 'Unknown')
                        holding_country = holding.get('country', '')  # Optional: Ländercode aus CSV
                        
                        # Normalisiere Sektor-Namen
                        holding_sector = _normalize_sector_name(holding_sector)
                        
                        # Holding-Name: Bei "Other Holdings" den ETF-Namen hinzufügen
                        holding_name = holding['name']
                        if 'Other Holdings' in holding_name or 'other holdings' in holding_name.lower():
                            holding_name = f"Other Holdings - {position['name']}"
                        
                        # Holding-Informationen abrufen
                        holding_info = {
                            'name': holding_name,
                            'type': 'Stock',  # Holdings sind meistens Aktien
                            'value': holding_value,
                            'weight_in_portfolio': holding_value / portfolio_data['total_value'],
                            'currency': holding_currency,  # Währung der einzelnen Aktie!
                            'country': holding_country,  # Ländercode falls vorhanden
                            'source_etf': position['name'],
                            'original_type': 'ETF_Holding',
                            'sector': holding_sector,
                            'industry': holding_industry,
                            'sector_source': 'etf'  # NIEDRIGE PRIORITÄT (aus ETF)
                        }
                        
                        expanded.append(holding_info)
                        print(f"DEBUG:     Added holding: {holding_name} = €{holding_value:.2f} ({holding_currency}, {holding_sector})")
                else:
                    print(f"DEBUG:   ⚠️  ETF could not be resolved - treating as whole")
                    # ETF konnte nicht aufgelöst werden - als Ganzes behandeln
                    expanded.append({
                        'name': position['name'],
                        'type': position['type'],
                        'value': position['value'],
                        'weight_in_portfolio': position['value'] / portfolio_data['total_value'],
                        'currency': position['currency'],
                        'source_etf': None,
                        'original_type': 'ETF',
                        'sector': 'ETF',
                        'industry': 'ETF'
                    })
        
        else:
            # Direkte Positionen (Aktien, Rohstoffe, Cash)
            pos_info = {
                'name': position['name'],
                'type': position['type'],
                'value': position['value'],
                'weight_in_portfolio': position['value'] / portfolio_data['total_value'],
                'currency': position['currency'],
                'isin': position.get('isin', ''),  # ISIN mitgeben!
                'ticker_symbol': position.get('ticker_symbol', ''),  # Ticker mitgeben!
                'source_etf': None,
                'original_type': position['type']
            }
            
            # Für Aktien: Sektor/Branche abrufen
            if position['type'] == 'Stock':
                # PRIORITÄT 1: Sektor aus Portfolio Performance Taxonomie oder CSV-Mapping
                if 'sector_from_pp' in position and position['sector_from_pp']:
                    pos_info['sector'] = _normalize_sector_name(position['sector_from_pp'])
                    pos_info['industry'] = _normalize_sector_name(position['sector_from_pp'])
                    pos_info['sector_source'] = 'csv'  # HÖCHSTE PRIORITÄT
                    print(f"DEBUG: Using PP sector for {position['name']}: {position['sector_from_pp']} -> {pos_info['sector']}")
                
                # PRIORITÄT 2: Versuche über ISIN (nur wenn vorhanden)
                elif position.get('isin'):
                    # Bestimme Handelswährung basierend auf ISIN
                    pos_info['currency'] = _get_stock_currency(position['isin'], position['currency'])
                    
                    stock_info = get_stock_info(position['isin'])
                    if stock_info:
                        pos_info['sector'] = _normalize_sector_name(stock_info.get('sector', 'Unknown'))
                        pos_info['industry'] = _normalize_sector_name(stock_info.get('industry', 'Unknown'))
                        pos_info['sector_source'] = 'isin'  # MITTLERE PRIORITÄT
                        print(f"DEBUG: Using ISIN sector for {position['name']}: {pos_info['sector']}")
                    else:
                        pos_info['sector'] = 'Unknown'
                        pos_info['industry'] = 'Unknown'
                        pos_info['sector_source'] = 'none'
                        print(f"DEBUG: ⚠️  No sector found for {position['name']} (ISIN: {position.get('isin')})")
                
                else:
                    # PRIORITÄT 3: Fallback auf Unknown (CSV ohne Mapping)
                    pos_info['sector'] = 'Unknown'
                    pos_info['industry'] = 'Unknown'
                    pos_info['sector_source'] = 'none'
                    print(f"DEBUG: ⚠️  No sector info for {position['name']} (no CSV sector, no ISIN)")
            
            else:
                pos_info['sector'] = position['type']
                pos_info['industry'] = position['type']
            
            expanded.append(pos_info)
    
    return expanded


def _calculate_asset_class_risk(expanded_positions: List[Dict], portfolio_data: Dict) -> pd.DataFrame:
    """
    Berechnet Klumpenrisiko nach Anlageklasse
    Verwendet expanded_positions, damit ETFs nach ihrem Inhalt klassifiziert werden
    """
    asset_classes = {}
    total_value = sum(pos['value'] for pos in expanded_positions)
    
    for position in expanded_positions:
        # Verwende den Typ aus expanded_positions (ETFs sind bereits aufgelöst)
        asset_class = position.get('type', 'Unknown')
        
        # "ETF_Holding" wird zu "Stock" (Holdings sind meist Aktien)
        if asset_class == 'ETF_Holding':
            asset_class = 'Stock'
        
        # Money Market ETFs werden zu Cash
        if position.get('etf_type') == 'Money Market':
            asset_class = 'Cash'
        
        if asset_class not in asset_classes:
            asset_classes[asset_class] = 0.0
        
        asset_classes[asset_class] += position['value']
    
    # DataFrame erstellen
    df = pd.DataFrame([
        {
            'Anlageklasse': asset_class,
            'Wert (€)': value,
            'Anteil (%)': (value / total_value) * 100
        }
        for asset_class, value in asset_classes.items()
    ])
    
    df = df.sort_values('Wert (€)', ascending=False).reset_index(drop=True)
    
    return df


def _calculate_sector_risk(expanded_positions: List[Dict]) -> pd.DataFrame:
    """
    Berechnet Klumpenrisiko nach Branche/Sektor
    """
    sectors = {}
    total_value = sum(pos['value'] for pos in expanded_positions)
    
    for position in expanded_positions:
        sector = position.get('sector', 'Unknown')
        
        # Überspringe "Diversified" und "ETF" - diese sind keine echten Branchen
        if sector in ['Diversified', 'ETF']:
            continue
        
        if sector not in sectors:
            sectors[sector] = 0.0
        
        sectors[sector] += position['value']
    
    # DataFrame erstellen
    df = pd.DataFrame([
        {
            'Sektor': sector,
            'Wert (€)': value,
            'Anteil (%)': (value / total_value) * 100
        }
        for sector, value in sectors.items()
    ])
    
    df = df.sort_values('Wert (€)', ascending=False).reset_index(drop=True)
    
    return df


def _calculate_currency_risk(expanded_positions: List[Dict]) -> pd.DataFrame:
    """
    Berechnet Klumpenrisiko nach Währung
    
    WICHTIG: Commodities (Gold, Silber, etc.) haben KEIN Währungsrisiko
    und werden daher nicht in die Berechnung einbezogen.
    """
    currencies = {}
    total_value_with_currency_risk = 0.0  # Nur Positionen mit echtem Währungsrisiko
    
    for position in expanded_positions:
        # Überspringe Commodities - sie haben kein Währungsrisiko
        if position.get('type') == 'Commodity':
            print(f"DEBUG: Skipping {position['name']} (Commodity) from currency risk")
            continue
        
        currency = position.get('currency', 'EUR')
        
        if currency not in currencies:
            currencies[currency] = 0.0
        
        currencies[currency] += position['value']
        total_value_with_currency_risk += position['value']
    
    # DataFrame erstellen (Prozentsätze basierend nur auf Positionen mit Währungsrisiko)
    df = pd.DataFrame([
        {
            'Währung': currency,
            'Wert (€)': value,
            'Anteil (%)': (value / total_value_with_currency_risk) * 100 if total_value_with_currency_risk > 0 else 0
        }
        for currency, value in currencies.items()
    ])
    
    df = df.sort_values('Wert (€)', ascending=False).reset_index(drop=True)
    
    return df


def _calculate_currency_risk_with_commodities(expanded_positions: List[Dict]) -> pd.DataFrame:
    """
    Berechnet Klumpenrisiko nach Währung INKLUSIVE Commodities
    
    Commodities werden als separate Kategorie "Commodity (kein Währungsrisiko)" angezeigt.
    Dies ist optional für die Visualisierung.
    """
    currencies = {}
    commodity_value = 0.0
    total_value = sum(pos['value'] for pos in expanded_positions)
    
    for position in expanded_positions:
        # Commodities separat sammeln
        if position.get('type') == 'Commodity':
            commodity_value += position['value']
            continue
        
        currency = position.get('currency', 'EUR')
        
        if currency not in currencies:
            currencies[currency] = 0.0
        
        currencies[currency] += position['value']
    
    # DataFrame erstellen
    rows = [
        {
            'Währung': currency,
            'Wert (€)': value,
            'Anteil (%)': (value / total_value) * 100
        }
        for currency, value in currencies.items()
    ]
    
    # Commodities hinzufügen wenn vorhanden
    if commodity_value > 0:
        rows.append({
            'Währung': 'Commodity (kein Währungsrisiko)',
            'Wert (€)': commodity_value,
            'Anteil (%)': (commodity_value / total_value) * 100
        })
    
    df = pd.DataFrame(rows)
    df = df.sort_values('Wert (€)', ascending=False).reset_index(drop=True)
    
    return df


def _calculate_country_risk(expanded_positions: List[Dict]) -> pd.DataFrame:
    """
    Berechnet Klumpenrisiko nach Land (basierend auf ISIN oder Handelsplatz)
    """
    countries = {}
    total_value = sum(pos['value'] for pos in expanded_positions)
    
    for position in expanded_positions:
        # Überspringe ETFs die nicht aufgelöst wurden und "Diversified" Holdings
        if position.get('sector') in ['ETF', 'Diversified']:
            continue
        
        # Land ermitteln (Priorität: explizit > ISIN > Währung)
        country_name = None
        
        # 1. Prüfe explizites Country-Feld (aus User CSV - höchste Priorität!)
        if 'country' in position and position['country']:
            country_code = position['country']
            country_name = _country_code_to_name(country_code)
        
        # 2. Für Cash und Geldmarkt-ETFs: IMMER Währung verwenden (nicht ISIN!)
        #    Cash hat oft keine ISIN, oder eine LU-ISIN die irreführend ist
        if not country_name and position.get('type') == 'Cash':
            currency = position.get('currency', 'EUR')
            country_name = _currency_to_country(currency)
        
        # 3. Versuche aus ISIN (für direkte Positionen wie Aktien)
        if not country_name or country_name.startswith('Unbekannt'):
            isin = position.get('isin', '')
            if isin and len(isin) >= 2:
                country_code = isin[:2]
                country_name = _country_code_to_name(country_code)
        
        # 4. Für ETF-Holdings ohne explizites Land: Verwende Währung als Proxy
        if not country_name or country_name.startswith('Unbekannt'):
            currency = position.get('currency', '')
            # Map Currency zu Land (für ETF-Holdings ohne ISIN)
            country_name = _currency_to_country(currency)
        
        if not country_name:
            country_name = 'Unbekannt'
        
        if country_name not in countries:
            countries[country_name] = 0.0
        countries[country_name] += position['value']
    
    df = pd.DataFrame([
        {
            'Land': country,
            'Wert (€)': value,
            'Anteil (%)': (value / total_value) * 100
        }
        for country, value in countries.items()
    ])
    
    df = df.sort_values('Wert (€)', ascending=False).reset_index(drop=True)
    
    return df


def _currency_to_country(currency: str) -> str:
    """
    Mapped Währung zu wahrscheinlichstem Land
    Wird für ETF-Holdings verwendet, die keine ISIN haben
    """
    currency_country_map = {
        'USD': 'USA',
        'EUR': 'Eurozone',  # Geändert von "Europa (EUR)" zu "Eurozone"
        'GBP': 'Großbritannien',
        'CHF': 'Schweiz',
        'JPY': 'Japan',
        'CAD': 'Kanada',
        'AUD': 'Australien',
        'CNY': 'China',
        'HKD': 'Hongkong',
        'SGD': 'Singapur',
        'KRW': 'Südkorea',
        'BRL': 'Brasilien',
        'INR': 'Indien',
        'ZAR': 'Südafrika',
        'MXN': 'Mexiko',
        'SEK': 'Schweden',
        'DKK': 'Dänemark',
        'NOK': 'Norwegen',
        'PLN': 'Polen',
        'CZK': 'Tschechien',
        'TWD': 'Taiwan',
        'Mixed': 'Diversifiziert'
    }
    return currency_country_map.get(currency, 'Unbekannt')


def _country_code_to_name(code: str) -> str:
    """
    Konvertiert ISO 3166-1 Alpha-2 Ländercode zu Ländername
    """
    country_map = {
        'US': 'USA',
        'DE': 'Deutschland',
        'GB': 'Großbritannien',
        'FR': 'Frankreich',
        'CH': 'Schweiz',
        'NL': 'Niederlande',
        'IE': 'Irland',
        'LU': 'Luxemburg',
        'IT': 'Italien',
        'ES': 'Spanien',
        'AT': 'Österreich',
        'BE': 'Belgien',
        'SE': 'Schweden',
        'DK': 'Dänemark',
        'NO': 'Norwegen',
        'FI': 'Finnland',
        'CA': 'Kanada',
        'JP': 'Japan',
        'AU': 'Australien',
        'CN': 'China',
        'HK': 'Hongkong',
        'SG': 'Singapur',
        'KR': 'Südkorea',
        'BR': 'Brasilien',
        'IN': 'Indien',
        'ZA': 'Südafrika',
        'MX': 'Mexiko',
        'RU': 'Russland',
        'PL': 'Polen',
        'CZ': 'Tschechien',
        'GR': 'Griechenland',
        'PT': 'Portugal',
    }
    return country_map.get(code, f'Unbekannt ({code})')


def _calculate_position_risk(expanded_positions: List[Dict]) -> pd.DataFrame:
    """
    Berechnet Klumpenrisiko nach Einzelpositionen
    Dies ist die wichtigste Analyse - zeigt echte Exposition inkl. ETF-Durchschau
    """
    # Positionen nach Namen gruppieren (normalisiert für besseres Matching)
    positions = {}
    total_value = sum(pos['value'] for pos in expanded_positions)
    
    for position in expanded_positions:
        # Normalisiere Namen für besseres Matching
        name = position['name']
        name_normalized = _normalize_position_name(name)
        
        # Spezialfall: Alle Cash-Positionen zusammenfassen
        if position.get('type') == 'Cash':
            name_normalized = 'cash_all'  # Einheitlicher Key für alle Cash
            display_name = 'Cash'  # Einheitlicher Anzeigename
        else:
            display_name = name
        
        if name_normalized not in positions:
            positions[name_normalized] = {
                'display_name': display_name,
                'ticker': position.get('ticker_symbol', ''),  # Ticker-Symbol speichern
                'value': 0.0,
                'sources': [],
                'sector': position.get('sector', 'Unknown'),
                'type': position.get('type', 'Unknown'),
                'sector_priority': 0  # 0=niedrig (ETF), 1=mittel (ISIN), 2=hoch (CSV)
            }
        
        # Ticker-Symbol aktualisieren wenn vorhanden und noch nicht gesetzt
        if position.get('ticker_symbol') and not positions[name_normalized]['ticker']:
            positions[name_normalized]['ticker'] = position.get('ticker_symbol', '')
        
        positions[name_normalized]['value'] += position['value']
        
        # Source ETF hinzufügen wenn vorhanden
        if position.get('source_etf'):
            if position['source_etf'] not in positions[name_normalized]['sources']:
                positions[name_normalized]['sources'].append(position['source_etf'])
        
        # KONFLIKTRESOLUTION: Höchste Priorität gewinnt
        # Priorität 2: Direktposition aus CSV (sector_source == 'csv')
        # Priorität 1: ISIN-basiert oder ETF-Details (sector_source == 'isin' oder 'etf_details')
        # Priorität 0: Aus ETF-Holdings (sector_source == 'etf' oder None)
        current_priority = positions[name_normalized]['sector_priority']
        new_priority = 0  # Default: ETF
        
        # Prüfe ob Position aus CSV stammt (höchste Priorität)
        if position.get('sector_source') == 'csv':
            new_priority = 2
        elif position.get('sector_source') in ['isin', 'etf_details']:
            new_priority = 1
        
        # Wenn neue Position höhere Priorität hat, überschreibe Sektor
        if new_priority > current_priority:
            positions[name_normalized]['sector'] = position.get('sector', 'Unknown')
            positions[name_normalized]['sector_priority'] = new_priority
            print(f"DEBUG: Sector override for {name}: {position.get('sector')} (priority {new_priority})")
    
    # DataFrame erstellen
    df = pd.DataFrame([
        {
            'Position': data['display_name'],
            'Ticker': data.get('ticker', ''),  # Ticker-Symbol
            'Wert (€)': data['value'],
            'Anteil (%)': (data['value'] / total_value) * 100,
            'Sektor': data['sector'],
            'Typ': data['type'],
            'Quellen': ', '.join(data['sources']) if data['sources'] else 'Direkt'
        }
        for name, data in positions.items()
    ])
    
    df = df.sort_values('Wert (€)', ascending=False).reset_index(drop=True)
    
    return df


def _normalize_position_name(name: str) -> str:
    """
    Normalisiert Positionsnamen für besseres Matching
    
    Beispiel:
    - "APPLE INC" -> "apple inc"
    - "Apple Inc" -> "apple inc"
    - "Apple Inc." -> "apple inc"
    """
    if not name:
        return ''
    
    # Kleinschreibung, trimmen, mehrfache Leerzeichen entfernen
    normalized = name.lower().strip()
    normalized = ' '.join(normalized.split())
    
    # Entferne gängige Suffixe
    suffixes = [' inc.', ' inc', ' corp.', ' corp', ' ltd.', ' ltd', 
                ' plc', ' ag', ' se', ' sa', ' co.', ' co',
                ' class a', ' class b', ' class c']
    
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)].strip()
    
    return normalized


def _get_stock_currency(isin: str, default_currency: str) -> str:
    """
    Bestimmt die Handelswährung einer Aktie basierend auf der ISIN
    
    Die ersten 2 Zeichen der ISIN geben das Herkunftsland an:
    US = USD, GB = GBP, DE = EUR, FR = EUR, etc.
    """
    if not isin or len(isin) < 2:
        return default_currency
    
    country_code = isin[:2].upper()
    
    # Mapping: Ländercode -> Hauptwährung
    currency_map = {
        'US': 'USD',  # USA
        'CA': 'CAD',  # Kanada
        'GB': 'GBP',  # UK
        'CH': 'CHF',  # Schweiz
        'JP': 'JPY',  # Japan
        'CN': 'CNY',  # China
        'HK': 'HKD',  # Hong Kong
        'AU': 'AUD',  # Australien
        'KR': 'KRW',  # Südkorea
        'IN': 'INR',  # Indien
        'BR': 'BRL',  # Brasilien
        'ZA': 'ZAR',  # Südafrika
        # Eurozone
        'DE': 'EUR', 'FR': 'EUR', 'IT': 'EUR', 'ES': 'EUR',
        'NL': 'EUR', 'BE': 'EUR', 'AT': 'EUR', 'IE': 'EUR',
        'PT': 'EUR', 'FI': 'EUR', 'GR': 'EUR', 'LU': 'EUR',
        # Nordeuropa (nicht Euro)
        'SE': 'SEK',  # Schweden
        'NO': 'NOK',  # Norwegen
        'DK': 'DKK',  # Dänemark
        'PL': 'PLN',  # Polen
        'CZ': 'CZK',  # Tschechien
        'HU': 'HUF',  # Ungarn
    }
    
    return currency_map.get(country_code, default_currency)


def _normalize_sector_name(sector: str) -> str:
    """
    Normalisiert Branchennamen zu einheitlichen Kategorien
    
    Mappt verschiedene Bezeichnungen (deutsch/englisch, verschiedene Standards)
    auf einheitliche Namen.
    """
    if not sector or sector == 'Unknown':
        return 'Unknown'
    
    sector_lower = sector.lower().strip()
    
    # Mapping: Verschiedene Namen -> Einheitlicher Name
    sector_mapping = {
        # Technologie / IT
        'informationstechnologie': 'Technology',
        'technology': 'Technology',
        'information technology': 'Technology',
        'tech': 'Technology',
        'software': 'Technology',
        'semiconductors': 'Technology',
        
        # Kommunikation
        'kommunikationsdienste': 'Communication Services',
        'communication services': 'Communication Services',
        'telekommunikation': 'Communication Services',
        'telecommunications': 'Communication Services',
        'media': 'Communication Services',
        'medien': 'Communication Services',
        
        # Finanzen
        'finanzwesen': 'Financial Services',
        'financial services': 'Financial Services',
        'financials': 'Financial Services',
        'finanzen': 'Financial Services',
        'banks': 'Financial Services',
        'banken': 'Financial Services',
        'insurance': 'Financial Services',
        'versicherungen': 'Financial Services',
        
        # Gesundheit
        'gesundheitswesen': 'Healthcare',
        'healthcare': 'Healthcare',
        'health care': 'Healthcare',
        'gesundheit': 'Healthcare',
        'pharma': 'Healthcare',
        'biotechnology': 'Healthcare',
        'biotechnologie': 'Healthcare',
        
        # Konsumgüter zyklisch
        'zyklische konsumgüter': 'Consumer Cyclical',
        'consumer cyclical': 'Consumer Cyclical',
        'consumer discretionary': 'Consumer Cyclical',
        'nicht-basiskonsumgüter': 'Consumer Cyclical',
        'retail': 'Consumer Cyclical',
        'einzelhandel': 'Consumer Cyclical',
        
        # Konsumgüter nicht-zyklisch
        'basiskonsumgüter': 'Consumer Staples',
        'consumer staples': 'Consumer Staples',
        'consumer defensive': 'Consumer Staples',
        'nahrungsmittel': 'Consumer Staples',
        'food': 'Consumer Staples',
        
        # Industrie
        'industrie': 'Industrials',
        'industrials': 'Industrials',
        'industrial': 'Industrials',
        
        # Energie
        'energie': 'Energy',
        'energy': 'Energy',
        'öl & gas': 'Energy',
        'oil & gas': 'Energy',
        
        # Materialien / Grundstoffe
        'materialien': 'Materials',
        'materials': 'Materials',
        'grundstoffe': 'Materials',
        'basic materials': 'Materials',
        
        # Immobilien
        'immobilien': 'Real Estate',
        'real estate': 'Real Estate',
        
        # Versorgung
        'versorgungsbetriebe': 'Utilities',
        'utilities': 'Utilities',
        'versorger': 'Utilities',
        
        # Sonstiges
        'diversified': 'Diversified',
        'diversifiziert': 'Diversified',
        'cash': 'Cash',
        'etf': 'ETF',
        'commodity': 'Commodity',
        'rohstoffe': 'Commodity',
    }
    
    # Suche nach Mapping
    for key, value in sector_mapping.items():
        if key in sector_lower:
            return value
    
    # Fallback: Kapitalisiere ersten Buchstaben
    return sector.title()
