"""
Risk Calculator
Berechnet Klumpenrisiken über verschiedene Dimensionen
"""

import pandas as pd
from typing import Dict, List
from pathlib import Path
from src.etf_data_fetcher import ETFDataFetcher, get_stock_info
from src.etf_details_parser import get_etf_details_parser
from src.diagnostics import get_diagnostics
from src.morningstar_fetcher import get_etf_details_from_morningstar
from src.etf_detail_writer import save_etf_detail_file


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


def calculate_cluster_risks(
    portfolio_data: Dict,
    etf_update_interval_days: int = 30,
) -> Dict:
    """
    Berechnet Klumpenrisiken über alle Dimensionen

    Args:
        portfolio_data: Geparste Portfolio-Daten
        etf_update_interval_days: Nach wie vielen Tagen ETF-Daten (Dateien + API-Cache)
            aktualisiert werden (1–90). Steuert sowohl ETF-Detail-Dateien als auch Fetcher-Cache.

    Returns:
        Dict mit Risiko-Analysen für alle Dimensionen
    """
    if not portfolio_data.get('positions') or portfolio_data.get('total_value', 0) == 0:
        raise ValueError("Portfolio enthält keine Positionen oder hat einen Gesamtwert von 0.")

    fetcher = ETFDataFetcher(cache_days=etf_update_interval_days)
    isin_ticker_map = _load_isin_ticker_map()
    expanded_positions, etf_resolution = _expand_etf_holdings(
        portfolio_data, fetcher, isin_ticker_map, etf_update_interval_days
    )
    
    # Validierung: Summe der expandierten Positionen = Portfolio-Gesamtwert
    expanded_sum = sum(p['value'] for p in expanded_positions)
    portfolio_total = portfolio_data['total_value']
    if abs(expanded_sum - portfolio_total) > max(1.0, portfolio_total * 0.001):
        diagnostics = get_diagnostics()
        diagnostics.add_warning(
            'Berechnung',
            f'Expansion-Summe weicht vom Portfolio ab',
            f'Expandiert: €{expanded_sum:,.2f} vs Portfolio: €{portfolio_total:,.2f}. Prüfe ETF-Detail-Dateien.'
        )
    
    # Klumpenrisiken berechnen
    risk_data = {
        'asset_class': _calculate_asset_class_risk(expanded_positions, portfolio_data),
        'sector': _calculate_sector_risk(expanded_positions),
        'currency': _calculate_currency_risk(expanded_positions),
        'currency_with_commodities': _calculate_currency_risk_with_commodities(expanded_positions),
        'country': _calculate_country_risk(expanded_positions),
        'positions': _calculate_position_risk(expanded_positions),
        'total_value': portfolio_data['total_value'],
        'etf_resolution': etf_resolution,
    }
    
    return risk_data


def _expand_etf_holdings(
    portfolio_data: Dict,
    fetcher: ETFDataFetcher,
    isin_ticker_map: Dict[str, str],
    etf_update_interval_days: int = 30,
) -> tuple:
    """
    Expandiert ETF-Positionen in ihre einzelnen Holdings.

    Datei-First: Lokale ETF-Detail-CSV wird genutzt. Wenn veraltet oder fehlend,
    werden Daten von Morningstar (oder Fetcher als Fallback) geholt und in eine
    CSV-Datei gespeichert.

    Returns:
        (expanded: List[Dict], etf_resolution: List[Dict])
        etf_resolution: [{'isin','ticker','name','source'}] mit source in file|morningstar|fetcher|failed
    """
    expanded = []
    etf_resolution: List[Dict] = []
    etf_parser = get_etf_details_parser()

    for position in portfolio_data['positions']:
        if position['type'] == 'ETF' and position.get('isin'):
            isin = position['isin']
            ticker = isin_ticker_map.get(isin) or position.get('ticker_symbol', '') or '?'
            name = position.get('name', '')
            ticker_for_file = ticker if ticker and ticker != '?' else f"ETF_{isin.replace(' ', '')[:12]}"

            etf_details = None
            source = 'failed'

            # 1. Lokale Datei: nutzen wenn vorhanden und nicht veraltet
            if ticker_for_file and not etf_parser.is_file_stale(ticker_for_file, etf_update_interval_days):
                etf_details = etf_parser.parse_etf_file(ticker_for_file)
                if etf_details:
                    source = 'file'

            # 2. Morningstar: holen, speichern, nutzen
            if not etf_details:
                ms_details = get_etf_details_from_morningstar(isin)
                if ms_details:
                    try:
                        save_etf_detail_file(ms_details, ticker_for_file, source_label="Morningstar (auto)")
                    except Exception as e:
                        print(f"⚠️  Konnte ETF-Detail-Datei nicht speichern: {e}")
                    etf_details = ms_details
                    source = 'morningstar'

            # 3. Fetcher-Fallback: holen, in unser Format konvertieren, speichern, nutzen
            if not etf_details:
                holdings_data = fetcher.get_etf_holdings(
                    isin, use_cache=True, ticker_symbol=position.get('ticker_symbol', '')
                )
                if holdings_data and holdings_data.get('holdings'):
                    # Typ ableiten: Commodity (XGDU), Money Market (XEON)
                    fetcher_type = 'Stock'
                    fetcher_name = holdings_data.get('name', name)
                    fetcher_holdings = holdings_data['holdings']
                    if any('physical gold' in (h.get('name') or '').lower() for h in fetcher_holdings):
                        fetcher_type = 'Commodity'
                    elif any(kw in (fetcher_name or '').lower() for kw in ('gold', 'physical gold', 'etc ', 'commodity')):
                        fetcher_type = 'Commodity'
                    elif any(kw in (h.get('name') or '').lower() for h in fetcher_holdings for kw in ('overnight', 'swap', 'rate')):
                        fetcher_type = 'Money Market'
                    elif any(kw in (fetcher_name or '').lower() for kw in ('overnight', 'money market', 'geldmarkt', 'xeon')):
                        fetcher_type = 'Money Market'
                    fetcher_details = {
                        'isin': isin,
                        'name': fetcher_name,
                        'type': fetcher_type,
                        'region': '',
                        'currency': 'EUR',
                        'ter': '',
                        'country_allocation': [],
                        'sector_allocation': [],
                        'currency_allocation': [],
                        'holdings': [
                            {
                                'name': h['name'],
                                'weight': h['weight'],
                                'currency': h.get('currency') or ('None' if fetcher_type == 'Commodity' else ('EUR' if fetcher_type == 'Money Market' else 'USD')),
                                'sector': h.get('sector') or ('Commodity' if fetcher_type == 'Commodity' else ('Cash' if fetcher_type == 'Money Market' else 'Unknown')),
                                'country': h.get('country', ''),
                                'isin': h.get('isin', ''),
                            }
                            for h in fetcher_holdings
                        ],
                    }
                    try:
                        save_etf_detail_file(
                            fetcher_details, ticker_for_file, source_label=f"{holdings_data.get('source', 'Fetcher')} (Fallback)"
                        )
                    except Exception as e:
                        print(f"⚠️  Konnte ETF-Detail-Datei nicht speichern: {e}")
                    etf_details = fetcher_details
                    source = 'fetcher'

            if etf_details:
                etf_resolution.append({'isin': isin, 'ticker': ticker_for_file, 'name': name, 'source': source})
                _expand_positions_using_etf_details(etf_details, position, portfolio_data, expanded, ticker_for_file)
            else:
                etf_resolution.append({'isin': isin, 'ticker': ticker_for_file, 'name': name, 'source': 'failed'})
                diagnostics = get_diagnostics()
                diagnostics.add_warning(
                    'ETF-Daten',
                    f'ETF "{name}" konnte nicht aufgelöst werden',
                    f'ISIN: {isin}. Morningstar und Fetcher lieferten keine Daten.',
                )
                expanded.append({
                    'name': position['name'],
                    'type': position['type'],
                    'value': position['value'],
                    'weight_in_portfolio': position['value'] / portfolio_data['total_value'],
                    'currency': position['currency'],
                    'source_etf': None,
                    'original_type': 'ETF',
                    'sector': 'ETF',
                    'industry': 'ETF',
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
                        # Diagnose: Keine Branche für Aktie gefunden
                        diagnostics = get_diagnostics()
                        diagnostics.add_warning(
                            'Branchen',
                            f'Keine Branche für Aktie "{position["name"]}" gefunden',
                            f'ISIN: {position.get("isin", "nicht vorhanden")}. Die Aktie wird unter "Unknown" kategorisiert.'
                        )
                
                else:
                    # PRIORITÄT 3: Fallback auf Unknown (CSV ohne Mapping)
                    pos_info['sector'] = 'Unknown'
                    pos_info['industry'] = 'Unknown'
                    pos_info['sector_source'] = 'none'
                    print(f"DEBUG: ⚠️  No sector info for {position['name']} (no CSV sector, no ISIN)")
                    # Diagnose: Keine Branche für Aktie gefunden
                    diagnostics = get_diagnostics()
                    diagnostics.add_warning(
                        'Branchen',
                        f'Keine Branche für Aktie "{position["name"]}" gefunden',
                        f'Weder CSV-Branche noch ISIN vorhanden. Die Aktie wird unter "Unknown" kategorisiert.'
                    )
            
            else:
                pos_info['sector'] = position['type']
                pos_info['industry'] = position['type']
            
            expanded.append(pos_info)
    
    return expanded, etf_resolution


def _expand_positions_using_etf_details(
    etf_details: Dict,
    position: Dict,
    portfolio_data: Dict,
    expanded: List[Dict],
    source_etf_ticker: str = '',
) -> None:
    """
    Gemeinsame Logik zum Aufschlüsseln eines ETFs anhand eines ETF-Detail-Dicts.

    Wird sowohl für lokal gespeicherte ETF-Detail-Dateien als auch für
    live von der Morningstar-API geholte Details verwendet.
    """
    # Sammle Währungsverteilung der Top Holdings (zur späteren Berechnung von "Other Holdings")
    top_holdings_currency_distribution: Dict[str, float] = {}
    other_holdings_entry = None
    sector_allocation = etf_details.get('sector_allocation') or []
    # Holdings mit Unknown/Diversified Sektor für spätere Zuordnung aus sector_allocation sammeln
    unknown_sector_holdings = []

    # Holdings aus Detail-Quelle verarbeiten
    for holding in etf_details.get('holdings', []):
        try:
            holding_weight = float(holding.get('weight', 0.0))
        except (TypeError, ValueError):
            holding_weight = 0.0
        if holding_weight <= 0:
            continue

        holding_value = position['value'] * holding_weight

        # Währung: Holding-Währung oder ETF-Währung (bei leerem Holding z.B. Money Market)
        holding_currency = holding.get('currency') or etf_details.get('currency', 'EUR')
        holding_sector = holding.get('sector', 'Unknown')
        holding_country = holding.get('country', '')

        # Normalisiere Sektor-Namen (etf_type für Cash/Derivative: Bond vs Stock)
        holding_sector = _normalize_sector_name(holding_sector, etf_details.get('type', 'Stock'))

        # Holding-Name: Bei "Other Holdings" den ETF-Namen hinzufügen
        holding_name = holding.get('name', '')
        is_other_holdings = 'Other Holdings' in holding_name or 'other holdings' in holding_name.lower()

        if is_other_holdings:
            # "Other Holdings" speichern für spätere Verarbeitung
            holding_name = f"Other Holdings - {position['name']}"
            other_holdings_entry = {
                'name': holding_name,
                'weight': holding_weight,
                'value': holding_value,
                'sector': holding_sector,
                'country': holding_country
            }
            continue  # Erstmal überspringen, später verarbeiten

        # Sammle Währung der Top Holdings
        if holding_currency not in top_holdings_currency_distribution:
            top_holdings_currency_distribution[holding_currency] = 0.0
        top_holdings_currency_distribution[holding_currency] += holding_weight

        # Reguläre Holding-Verarbeitung (nicht "Other Holdings")
        holding_info = {
            'name': holding_name,
            'type': etf_details.get('type', 'Stock'),  # Type aus Metadata
            'value': holding_value,
            'weight_in_portfolio': holding_value / portfolio_data['total_value'],
            'currency': holding_currency,
            'country': holding_country,
            'source_etf': position['name'],
            'source_etf_ticker': source_etf_ticker,
            'original_type': 'ETF_Holding',
            'sector': holding_sector,
            'industry': holding_sector,
            'sector_source': 'etf_details',  # MITTLERE PRIORITÄT
            'etf_type': etf_details.get('type', 'Stock')  # ETF-Typ (Money Market, Stock, etc.)
        }
        # Wenn Sektor unbekannt/diversified und Sector Allocation vorhanden: später zuordnen
        if sector_allocation and holding_sector in ('Unknown', 'Diversified'):
            unknown_sector_holdings.append((holding_value, holding_info))
        else:
            expanded.append(holding_info)
            print(f"DEBUG:     Added holding: {holding_name} = €{holding_value:.2f} ({holding_currency}, {holding_sector})")

    # Sektor aus sector_allocation für Holdings mit Unknown/Diversified zuweisen
    if sector_allocation and unknown_sector_holdings:
        assigned_sectors = _assign_sectors_from_allocation(
            unknown_sector_holdings, sector_allocation, position['value'],
            etf_details.get('type', 'Stock')
        )
        for (_, holding_info), sector_name in zip(unknown_sector_holdings, assigned_sectors):
            holding_info['sector'] = sector_name
            holding_info['industry'] = sector_name
            expanded.append(holding_info)
            print(f"DEBUG:     Added holding (sector from allocation): {holding_info['name']} = €{holding_info['value']:.2f} ({holding_info['currency']}, {sector_name})")

    # Verarbeite "Other Holdings": einheitlich nach Sektor, Währung und Land aus Allokationen
    if other_holdings_entry:
        sector_alloc_list = etf_details.get('sector_allocation') or []
        currency_alloc_list = etf_details.get('currency_allocation') or []
        country_alloc_list = etf_details.get('country_allocation') or []
        other_value = other_holdings_entry['value']

        # Sektor-Gewichte: aus Sector Allocation, auf Summe 1 normalisiert
        # (Morningstar-Daten können >100% pro Kategorie liefern)
        if sector_alloc_list:
            etf_type = etf_details.get('type', 'Stock')
            raw_sector = [
                (_normalize_sector_name(s['name'], etf_type), s['weight'])
                for s in sector_alloc_list if s.get('weight', 0) > 0
            ]
            total_s = sum(w for _, w in raw_sector)
            sector_weights = [(n, w / total_s) for n, w in raw_sector] if total_s > 0 else [('Diversified', 1.0)]
        else:
            sector_weights = [('Diversified', 1.0)]

        # Währungs-Gewichte für "Other": Gesamt-ETF minus Top-Holdings, normalisiert
        if currency_alloc_list:
            other_currency_weights: Dict[str, float] = {}
            for c in currency_alloc_list:
                total_c = c['weight']
                top_c = top_holdings_currency_distribution.get(c['name'], 0.0)
                other_c = max(0.0, total_c - top_c)
                if other_c > 0.001:
                    other_currency_weights[c['name']] = other_c
            total_other_currency = sum(other_currency_weights.values())
            if total_other_currency > 0:
                currency_weights = [(cur, w / total_other_currency) for cur, w in other_currency_weights.items()]
            else:
                currency_weights = [('Mixed', 1.0)]
        else:
            currency_weights = [('Mixed', 1.0)]

        # Länder-Gewichte: aus Country Allocation, auf Summe 1 normalisiert
        # (Morningstar-Daten können >100% pro Land liefern)
        if country_alloc_list:
            raw_country = [
                (_allocation_country_name_to_code(c['name']), c['weight'])
                for c in country_alloc_list if c.get('weight', 0) > 0
            ]
            total_c = sum(w for _, w in raw_country)
            country_weights = [(code, w / total_c) for code, w in raw_country] if total_c > 0 else [('Other', 1.0)]
        else:
            country_weights = [('Other', 1.0)]

        # Eine Zeile pro (Sektor, Währung, Land) – alle drei Ansichten (Branche, Währung, Land) korrekt
        print(f"DEBUG:     Processing Other Holdings: {len(sector_weights)}×{len(currency_weights)}×{len(country_weights)} Kombinationen (Sektor×Währung×Land)")
        for (sector_name_norm, s_w) in sector_weights:
            for (currency_name, c_w) in currency_weights:
                for (country_code, country_w) in country_weights:
                    part_value = other_value * s_w * c_w * country_w
                    if part_value < 0.001:  # Rundungsrausch vermeiden, aber keine Werte verlieren
                        continue
                    holding_info = {
                        'name': other_holdings_entry['name'],
                        'type': etf_details.get('type', 'Stock'),
                        'value': part_value,
                        'weight_in_portfolio': part_value / portfolio_data['total_value'],
                        'currency': currency_name,
                        'country': country_code,
                        'source_etf': position['name'],
                        'source_etf_ticker': source_etf_ticker,
                        'original_type': 'ETF_Holding',
                        'sector': sector_name_norm,
                        'industry': sector_name_norm,
                        'sector_source': 'etf_details',
                        'etf_type': etf_details.get('type', 'Stock')
                    }
                    expanded.append(holding_info)


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
        
        # ETF-Holdings: Anlageklasse aus etf_type (Bond → Bond, Money Market → Cash, Stock → Stock)
        if asset_class == 'ETF_Holding':
            asset_class = position.get('etf_type', 'Stock')
        
        # Money Market ETFs werden als Cash dargestellt
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
            'Anteil (%)': round((value / total_value) * 100, 1)
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
        # Money-Market-Holdings (z.B. TRS €STR) mit Unknown → Cash (für Cash-Checkbox-Filter)
        if sector == 'Unknown' and position.get('etf_type') == 'Money Market':
            sector = 'Cash'
        
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
            'Anteil (%)': round((value / total_value) * 100, 1)
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
            'Anteil (%)': round((value / total_value_with_currency_risk) * 100, 1) if total_value_with_currency_risk > 0 else 0.0
        }
        for currency, value in currencies.items()
    ])
    if len(df) > 0:
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
            'Anteil (%)': round((value / total_value) * 100, 1)
        }
        for currency, value in currencies.items()
    ]
    
    # Commodities hinzufügen wenn vorhanden
    if commodity_value > 0:
        rows.append({
            'Währung': 'Commodity (kein Währungsrisiko)',
            'Wert (€)': commodity_value,
            'Anteil (%)': round((commodity_value / total_value) * 100, 1)
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
        
        # 1. Prüfe explizites Country-Feld (aus User CSV / ETF-Holdings)
        #    Morningstar liefert hier Klarnamen ("United States") oder ISO-3 ("USA"),
        #    daher erst durch _allocation_country_name_to_code normalisieren.
        if 'country' in position and position['country']:
            country_code = _allocation_country_name_to_code(position['country'])
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
            currency = position.get('currency', '') or (
                'EUR' if position.get('etf_type') == 'Money Market' else ''
            )
            country_name = _currency_to_country(currency)
        
        if not country_name or country_name == 'Unbekannt':
            country_name = 'Unbekannt'
        
        if country_name not in countries:
            countries[country_name] = 0.0
        countries[country_name] += position['value']
    
    df = pd.DataFrame([
        {
            'Land': country,
            'Wert (€)': value,
            'Anteil (%)': round((value / total_value) * 100, 1)
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


def _allocation_country_name_to_code(name: str) -> str:
    """
    Normalizes any country identifier (full English/German name, ISO-3, ISO-2)
    to an ISO 3166-1 Alpha-2 code for consistent country-risk aggregation.
    Unknown values map to 'Other' instead of guessing via string slicing.
    """
    if not name or not name.strip():
        return 'Other'
    name_clean = name.strip()
    allocation_to_code = {
        'United States': 'US', 'USA': 'US', 'US': 'US',
        'Germany': 'DE', 'DEU': 'DE', 'DE': 'DE', 'Deutschland': 'DE',
        'United Kingdom': 'GB', 'GBR': 'GB', 'UK': 'GB', 'GB': 'GB', 'Großbritannien': 'GB',
        'Canada': 'CA', 'CAN': 'CA', 'CA': 'CA', 'Kanada': 'CA',
        'Switzerland': 'CH', 'CHE': 'CH', 'CH': 'CH', 'Schweiz': 'CH',
        'France': 'FR', 'FRA': 'FR', 'FR': 'FR', 'Frankreich': 'FR',
        'Australia': 'AU', 'AUS': 'AU', 'AU': 'AU', 'Australien': 'AU',
        'Japan': 'JP', 'JPN': 'JP', 'JP': 'JP',
        'Netherlands': 'NL', 'NLD': 'NL', 'NL': 'NL', 'Niederlande': 'NL',
        'Ireland': 'IE', 'IRL': 'IE', 'IE': 'IE', 'Irland': 'IE',
        'Italy': 'IT', 'ITA': 'IT', 'IT': 'IT', 'Italien': 'IT',
        'Spain': 'ES', 'ESP': 'ES', 'ES': 'ES', 'Spanien': 'ES',
        'Austria': 'AT', 'AUT': 'AT', 'AT': 'AT', 'Österreich': 'AT',
        'Belgium': 'BE', 'BEL': 'BE', 'BE': 'BE', 'Belgien': 'BE',
        'Sweden': 'SE', 'SWE': 'SE', 'SE': 'SE', 'Schweden': 'SE',
        'Denmark': 'DK', 'DNK': 'DK', 'DK': 'DK', 'Dänemark': 'DK',
        'Norway': 'NO', 'NOR': 'NO', 'NO': 'NO', 'Norwegen': 'NO',
        'Finland': 'FI', 'FIN': 'FI', 'FI': 'FI', 'Finnland': 'FI',
        'Luxembourg': 'LU', 'LUX': 'LU', 'LU': 'LU', 'Luxemburg': 'LU',
        'China': 'CN', 'CHN': 'CN', 'CN': 'CN',
        'South Korea': 'KR', 'Korea': 'KR', 'KOR': 'KR', 'KR': 'KR', 'Südkorea': 'KR',
        'Hong Kong': 'HK', 'HKG': 'HK', 'HK': 'HK', 'Hongkong': 'HK',
        'Singapore': 'SG', 'SGP': 'SG', 'SG': 'SG', 'Singapur': 'SG',
        'Brazil': 'BR', 'BRA': 'BR', 'BR': 'BR', 'Brasilien': 'BR',
        'India': 'IN', 'IND': 'IN', 'IN': 'IN', 'Indien': 'IN',
        'South Africa': 'ZA', 'ZAF': 'ZA', 'ZA': 'ZA', 'Südafrika': 'ZA',
        'Mexico': 'MX', 'MEX': 'MX', 'MX': 'MX', 'Mexiko': 'MX',
        'Russia': 'RU', 'RUS': 'RU', 'RU': 'RU', 'Russland': 'RU',
        'Poland': 'PL', 'POL': 'PL', 'PL': 'PL', 'Polen': 'PL',
        'Czech Republic': 'CZ', 'CZE': 'CZ', 'CZ': 'CZ', 'Tschechien': 'CZ',
        'Greece': 'GR', 'GRC': 'GR', 'GR': 'GR', 'Griechenland': 'GR',
        'Portugal': 'PT', 'PRT': 'PT', 'PT': 'PT',
        'Taiwan': 'TW', 'TWN': 'TW', 'TW': 'TW',
        'New Zealand': 'NZ', 'NZL': 'NZ', 'NZ': 'NZ', 'Neuseeland': 'NZ',
        'Thailand': 'TH', 'THA': 'TH', 'TH': 'TH',
        'Malaysia': 'MY', 'MYS': 'MY', 'MY': 'MY',
        'Indonesia': 'ID', 'IDN': 'ID', 'ID': 'ID', 'Indonesien': 'ID',
        'Other': 'Other', 'Mixed': 'Other', 'Cash': 'Other',
    }
    return allocation_to_code.get(name_clean, 'Other')


def _country_code_to_name(code: str) -> str:
    """
    Konvertiert ISO 3166-1 Alpha-2 Ländercode (oder 3-Buchstaben) zu Ländername
    """
    if not code:
        return 'Unbekannt'
    code = code.strip().upper()
    # 3-Buchstaben-Codes zu Alpha-2 normalisieren (z.B. USA→US, GBR→GB)
    code_3_to_2 = {
        'USA': 'US', 'GBR': 'GB', 'CHE': 'CH', 'DEU': 'DE', 'FRA': 'FR',
        'ITA': 'IT', 'ESP': 'ES', 'NLD': 'NL', 'BEL': 'BE', 'AUT': 'AT',
        'IRL': 'IE', 'LUX': 'LU', 'JPN': 'JP', 'CHN': 'CN', 'AUS': 'AU',
        'CAN': 'CA', 'KOR': 'KR', 'HKG': 'HK', 'SGP': 'SG', 'BRA': 'BR',
        'IND': 'IN', 'ZAF': 'ZA', 'MEX': 'MX', 'RUS': 'RU', 'POL': 'PL',
    }
    if len(code) == 3 and code in code_3_to_2:
        code = code_3_to_2[code]
    country_map = {
        'US': 'USA',
        'Other': 'Sonstige',
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
        # Money-Market-Holdings mit kryptischem Namen (TRS, Swap, €STR): Ticker statt Name
        elif (position.get('etf_type') == 'Money Market'
              and position.get('source_etf_ticker')
              and _is_cryptic_money_market_holding(name)):
            display_name = position['source_etf_ticker']
        else:
            display_name = name
        
        sector_for_pos = position.get('sector', 'Unknown')
        if sector_for_pos == 'Unknown' and position.get('etf_type') == 'Money Market':
            sector_for_pos = 'Cash'
        if name_normalized not in positions:
            ticker_val = position.get('ticker_symbol', '') or (
                position.get('source_etf_ticker', '') if (
                    position.get('etf_type') == 'Money Market' and _is_cryptic_money_market_holding(name)
                ) else ''
            )
            positions[name_normalized] = {
                'display_name': display_name,
                'ticker': ticker_val,
                'value': 0.0,
                'sources': [],
                'sector': sector_for_pos,
                'type': position.get('type', 'Unknown'),
                'sector_priority': 0  # 0=niedrig (ETF), 1=mittel (ISIN), 2=hoch (CSV)
            }
        
        # Ticker-Symbol aktualisieren wenn vorhanden und noch nicht gesetzt
        if position.get('ticker_symbol') and not positions[name_normalized]['ticker']:
            positions[name_normalized]['ticker'] = position.get('ticker_symbol', '')
        elif (position.get('source_etf_ticker') and not positions[name_normalized]['ticker']
              and position.get('etf_type') == 'Money Market' and _is_cryptic_money_market_holding(name)):
            positions[name_normalized]['ticker'] = position['source_etf_ticker']
        
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
            positions[name_normalized]['sector'] = sector_for_pos
            positions[name_normalized]['sector_priority'] = new_priority
            print(f"DEBUG: Sector override for {name}: {position.get('sector')} (priority {new_priority})")
    
    # DataFrame erstellen
    df = pd.DataFrame([
        {
            'Position': data['display_name'],
            'Ticker': data.get('ticker', ''),  # Ticker-Symbol
            'Wert (€)': data['value'],
            'Anteil (%)': round((data['value'] / total_value) * 100, 1),
            'Sektor': data['sector'],
            'Typ': data['type'],
            'Quellen': ', '.join(data['sources']) if data['sources'] else 'Direkt'
        }
        for name, data in positions.items()
    ])
    
    df = df.sort_values('Wert (€)', ascending=False).reset_index(drop=True)
    
    return df


def _is_cryptic_money_market_holding(name: str) -> bool:
    """Erkennt kryptische Money-Market-Holding-Namen (TRS, Swap, €STR, etc.)"""
    if not name:
        return False
    n = name.lower()
    return any(kw in n for kw in ('trs ', 'trs solactive', 'swap', 'overnight', '€str', 'estr', 'rate swap'))


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


def _assign_sectors_from_allocation(
    holdings_with_values: List[tuple],
    sector_allocation: List[Dict],
    etf_total_value: float,
    etf_type: str = 'Stock',
) -> List[str]:
    """
    Ordnet Holdings ohne Sektor (Unknown/Diversified) den Sektoren aus sector_allocation
    per Greedy-Zuordnung zu, sodass die Sektor-Summen ungefähr den Allokationsgewichten entsprechen.
    holdings_with_values: Liste von (value, ...) – nur value wird genutzt
    Returns: Liste der zugewiesenen Sektornamen (gleiche Reihenfolge wie holdings_with_values)
    """
    if not sector_allocation or not holdings_with_values:
        return ['Unknown'] * len(holdings_with_values)
    # Ziel pro Sektor (Anteil * Gesamtwert der Holdings)
    total_unknown_value = sum(h[0] for h in holdings_with_values)
    sector_targets = [
        (s['name'], s['weight'] * total_unknown_value)
        for s in sector_allocation
        if s.get('weight', 0) > 0
    ]
    sector_targets.sort(key=lambda x: -x[1])  # absteigend nach Zielwert
    # Greedy: Holding (nach Wert absteigend) dem Sektor zuordnen, der am meisten fehlt
    holdings_sorted = sorted(enumerate(holdings_with_values), key=lambda x: -x[1][0])
    sector_sums = {s[0]: 0.0 for s in sector_targets}
    assigned = ['Unknown'] * len(holdings_with_values)
    for idx, (value, _) in holdings_sorted:
        best_sector = None
        best_gap = -1
        for s_name, s_target in sector_targets:
            gap = s_target - sector_sums[s_name]
            if gap > best_gap:
                best_gap = gap
                best_sector = s_name
        if best_sector:
            assigned[idx] = _normalize_sector_name(best_sector, etf_type)
            sector_sums[best_sector] += value
    return assigned


def _normalize_sector_name(sector: str, etf_type: str = '') -> str:
    """
    Normalisiert Branchennamen zu einheitlichen Kategorien.

    etf_type: 'Bond' = Bond-ETF (Cash/Derivative → Bonds: …), sonst Aktien-ETF
    (Cash/Derivative bei Aktien-ETFs = Kassenbestand/Swap-Replikation, keine Anleihen)
    """
    if not sector or sector == 'Unknown':
        return 'Unknown'
    
    # Morningstar Bond-Sector-Codes (10=Government, 30=Corporate, 60=Derivative, …)
    bond_sector_codes = {
        '10': 'Bonds: Government', '20': 'Bonds: Municipal', '30': 'Bonds: Corporate',
        '40': 'Bonds: Securitized', '50': 'Bonds: Cash', '60': 'Bonds: Derivative',
    }
    if str(sector).strip() in bond_sector_codes:
        return bond_sector_codes[str(sector).strip()]

    # Morningstar Stock-Sektor-Codes (GECS: 101–311)
    stock_sector_codes = {
        '101': 'Materials', '102': 'Consumer Cyclical', '103': 'Financial Services',
        '104': 'Real Estate', '205': 'Consumer Staples', '206': 'Healthcare',
        '207': 'Utilities', '308': 'Communication Services', '309': 'Energy',
        '310': 'Industrials', '311': 'Technology',
    }
    if str(sector).strip() in stock_sector_codes:
        return stock_sector_codes[str(sector).strip()]

    s_check = str(sector).strip().lower()
    is_bond_etf = (etf_type or '').lower() == 'bond'

    # Cash/Derivative: Nur bei Bond-ETFs als "Bonds:" prefixen
    # Bei Aktien-ETFs (EUNL etc.) = Kassenbestand/Swap-Replikation, keine Anleihen
    if s_check in ('cash', 'derivative'):
        return f'Bonds: {sector.strip().title()}' if is_bond_etf else sector.strip().title()

    # Explizit bond-spezifische Namen (z.B. "Bonds/Cash" von Morningstar)
    if s_check in ('bonds/cash', 'bonds/cash & equivalents'):
        return 'Bonds: Cash'

    # Bond-Sektoren als Namen (nur für Bond-ETFs relevant)
    bond_sector_names = {
        'government': 'Bonds: Government', 'municipal': 'Bonds: Municipal',
        'corporate': 'Bonds: Corporate', 'securitized': 'Bonds: Securitized',
    }
    if is_bond_etf and s_check in bond_sector_names:
        return bond_sector_names[s_check]

    # Eingabe bereinigen (Leerzeichen, &/und)
    s = sector.strip()
    while '  ' in s:
        s = s.replace('  ', ' ')
    s = s.replace('&', ' und ').replace('–', '-').replace('—', '-')
    sector_lower = s.lower()
    sector_lower_ascii = sector_lower.replace('ü', 'ue').replace('ä', 'ae').replace('ö', 'oe')
    
    # Mapping: Verschiedene Namen -> Einheitlicher Name (längere Keys zuerst für Teilstring-Match)
    sector_mapping = [
        # Technologie / IT
        ('informationstechnologie', 'Technology'),
        ('information technology', 'Technology'),
        ('technology', 'Technology'),
        ('tech', 'Technology'),
        ('software', 'Technology'),
        ('semiconductors', 'Technology'),
        # Kommunikation
        ('kommunikationsdienste', 'Communication Services'),
        ('communication services', 'Communication Services'),
        ('telekommunikation', 'Communication Services'),
        ('telecommunication', 'Communication Services'),
        ('telecommunications', 'Communication Services'),
        ('media', 'Communication Services'),
        ('medien', 'Communication Services'),
        # Finanzen
        ('finanzdienstleistungen', 'Financial Services'),
        ('finanzwesen', 'Financial Services'),
        ('financial services', 'Financial Services'),
        ('financials', 'Financial Services'),
        ('finanzen', 'Financial Services'),
        ('banks', 'Financial Services'),
        ('banken', 'Financial Services'),
        ('insurance', 'Financial Services'),
        ('versicherungen', 'Financial Services'),
        # Gesundheit
        ('gesundheitswesen', 'Healthcare'),
        ('healthcare', 'Healthcare'),
        ('health care', 'Healthcare'),
        ('gesundheit', 'Healthcare'),
        ('pharma', 'Healthcare'),
        ('biotechnology', 'Healthcare'),
        ('biotechnologie', 'Healthcare'),
        # Konsumgüter zyklisch (Nicht-Basiskonsumgüter)
        ('zyklische konsumgüter', 'Consumer Cyclical'),
        ('zyklische konsumgueter', 'Consumer Cyclical'),
        ('nicht-basiskonsumgüter', 'Consumer Cyclical'),
        ('nicht-basiskonsumgueter', 'Consumer Cyclical'),
        ('nicht basiskonsumgüter', 'Consumer Cyclical'),
        ('nicht basiskonsumgueter', 'Consumer Cyclical'),
        ('consumer cyclical', 'Consumer Cyclical'),
        ('consumer discretionary', 'Consumer Cyclical'),
        ('retail', 'Consumer Cyclical'),
        ('einzelhandel', 'Consumer Cyclical'),
        # Konsumgüter nicht-zyklisch
        ('basiskonsumgüter', 'Consumer Staples'),
        ('basiskonsumgueter', 'Consumer Staples'),
        ('consumer staples', 'Consumer Staples'),
        ('consumer defensive', 'Consumer Staples'),
        ('nahrungsmittel', 'Consumer Staples'),
        ('food', 'Consumer Staples'),
        # Industrie
        ('industrie', 'Industrials'),
        ('industrials', 'Industrials'),
        ('industrial', 'Industrials'),
        # Energie
        ('energie', 'Energy'),
        ('energy', 'Energy'),
        ('öl & gas', 'Energy'),
        ('oil & gas', 'Energy'),
        # Materialien / Roh-, Hilfs- & Betriebsstoffe
        ('roh-, hilfs- und betriebsstoffe', 'Materials'),
        ('roh-, hilfs- & betriebsstoffe', 'Materials'),
        ('hilfs- und betriebsstoffe', 'Materials'),
        ('betriebsstoffe', 'Materials'),
        ('hilfsstoffe', 'Materials'),
        ('rohstoffe', 'Materials'),
        ('materialien', 'Materials'),
        ('materials', 'Materials'),
        ('grundstoffe', 'Materials'),
        ('basic materials', 'Materials'),
        ('werkstoffe', 'Materials'),
        # Immobilien
        ('immobilien', 'Real Estate'),
        ('real estate', 'Real Estate'),
        # Versorgung
        ('versorgungsbetriebe', 'Utilities'),
        ('utilities', 'Utilities'),
        ('versorger', 'Utilities'),
        # Sonstiges (rohstoffe hier nur wenn nicht schon Materials)
        ('diversified', 'Diversified'),
        ('diversifiziert', 'Diversified'),
        ('cash', 'Cash'),
        ('etf', 'ETF'),
        ('commodity', 'Commodity'),
    ]
    
    for key, value in sector_mapping:
        if key in sector_lower or key in sector_lower_ascii:
            return value
    
    return sector.strip().title() if sector else 'Unknown'
