"""
ETF Detail Writer
Speichert ETF-Details (von Morningstar oder Fetcher) im einheitlichen CSV-Format.
"""

import csv
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from .etf_detail_generator import COUNTRY_TO_CURRENCY, _derive_currency_allocation


def _derive_currency_from_holdings(holdings: List[Dict]) -> List[Dict]:
    """Leitet Währungs-Allokation aus Holdings ab (falls country_allocation fehlt)."""
    currency_weights: Dict[str, float] = {}
    for h in holdings:
        cur = h.get('currency') or 'USD'
        w = float(h.get('weight', 0))
        currency_weights[cur] = currency_weights.get(cur, 0.0) + w
    return [{'name': c, 'weight': w} for c, w in sorted(currency_weights.items(), key=lambda x: -x[1]) if w > 0]


def _derive_allocations_from_holdings(holdings: List[Dict]) -> tuple:
    """Leitet Country- und Sektor-Allokation aus Holdings ab."""
    country_weights: Dict[str, float] = {}
    sector_weights: Dict[str, float] = {}
    for h in holdings:
        c = h.get('country') or 'Other'
        s = h.get('sector') or 'Unknown'
        w = float(h.get('weight', 0))
        if c:
            country_weights[c] = country_weights.get(c, 0.0) + w
        if s:
            sector_weights[s] = sector_weights.get(s, 0.0) + w
    countries = [{'name': k, 'weight': v} for k, v in sorted(country_weights.items(), key=lambda x: -x[1]) if v > 0]
    sectors = [{'name': k, 'weight': v} for k, v in sorted(sector_weights.items(), key=lambda x: -x[1]) if v > 0]
    return countries, sectors


def _normalize_holding(h: Dict) -> Dict:
    """Stellt sicher, dass eine Holding alle benötigten Felder hat."""
    return {
        'name': h.get('name', ''),
        'weight': float(h.get('weight', 0)),
        'currency': h.get('currency', 'USD'),
        'sector': h.get('sector', 'Unknown'),
        'country': h.get('country', ''),
        'isin': h.get('isin', ''),
    }


def save_etf_detail_file(
    details: Dict,
    ticker: str,
    source_label: str = "Morningstar (auto)",
    etf_details_dir: str = "data/etf_details",
) -> Path:
    """
    Speichert ETF-Details im einheitlichen CSV-Format.

    Args:
        details: Dict mit isin, name, type, country_allocation, sector_allocation,
                 currency_allocation (optional), holdings
        ticker: Ticker-Symbol (Dateiname)
        source_label: Quelle für Metadata (z.B. "Morningstar (auto)" oder "justETF (Fallback)")
        etf_details_dir: Zielverzeichnis

    Returns:
        Path zur geschriebenen Datei
    """
    output_path = Path(etf_details_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    safe_ticker = Path(ticker).name  # Strip any directory components to prevent path traversal
    filepath = output_path / f"{safe_ticker}.csv"

    isin = details.get('isin', '')
    name = details.get('name', 'Unknown')
    etf_type = details.get('type', 'Stock')
    region = details.get('region', '')
    currency = details.get('currency', 'EUR')
    ter = str(details.get('ter', ''))
    proxy_isin = details.get('proxy_isin', '')
    index_name = details.get('index', '')

    countries = details.get('country_allocation') or []
    sectors = details.get('sector_allocation') or []
    currency_allocation = details.get('currency_allocation') or []
    holdings_raw = details.get('holdings', [])

    # Holdings normalisieren
    holdings = [_normalize_holding(h) for h in holdings_raw if h.get('name') and float(h.get('weight', 0)) > 0]

    # Allokationen ableiten falls fehlend
    if not countries and holdings:
        countries, sectors = _derive_allocations_from_holdings(holdings)
    if not sectors and holdings:
        _, sectors = _derive_allocations_from_holdings(holdings)
    if not currency_allocation:
        if countries:
            currency_allocation = _derive_currency_allocation(countries)
        elif holdings:
            currency_allocation = _derive_currency_from_holdings(holdings)

    # Other Holdings Gewicht
    top_weight = sum(h['weight'] for h in holdings)
    other_weight = max(0.0, 1.0 - top_weight)

    today = datetime.now().strftime('%Y-%m-%d')
    lines = []

    lines.append('# ETF Metadata')
    lines.append(f'ISIN,{isin}')
    lines.append(f'Name,{name}')
    lines.append(f'Ticker,{ticker}')
    lines.append(f'Type,{etf_type}')
    if index_name:
        lines.append(f'Index,{index_name}')
    lines.append(f'Region,{region}')
    lines.append(f'Currency,{currency}')
    lines.append(f'TER,{ter}')
    if proxy_isin:
        lines.append(f'Proxy ISIN,{proxy_isin}')
    lines.append(f'Last Updated,{today}')
    lines.append(f'Source,{source_label}')
    lines.append('')

    lines.append('# Country Allocation (%)')
    lines.append('Country,Weight')
    for c in countries:
        lines.append(f'{c["name"]},{c["weight"] * 100:.1f}')
    lines.append('')

    lines.append('# Sector Allocation (%)')
    lines.append('Sector,Weight')
    for s in sectors:
        lines.append(f'{s["name"]},{s["weight"] * 100:.1f}')
    lines.append('')

    lines.append('# Currency Allocation (%)')
    lines.append('Currency,Weight')
    for cur in currency_allocation:
        lines.append(f'{cur["name"]},{cur["weight"] * 100:.1f}')
    lines.append('')

    lines.append('# Top Holdings')
    lines.append('')

    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        f.write('\n'.join(lines))

        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['Name', 'Weight', 'Currency', 'Sector', 'Country', 'ISIN'])
        for h in holdings:
            writer.writerow([
                h['name'],
                f'{h["weight"] * 100:.2f}',
                h['currency'],
                h['sector'],
                h['country'],
                h.get('isin', ''),
            ])
        if other_weight > 0.01:
            writer.writerow(['Other Holdings', f'{other_weight * 100:.2f}', 'Mixed', 'Diversified', 'Mixed', ''])
        f.write('\n')

    _update_isin_ticker_map(isin, ticker, name)
    return filepath


def _update_isin_ticker_map(isin: str, ticker: str, name: str) -> None:
    """Aktualisiert die ISIN-Ticker-Map (fügt hinzu oder aktualisiert)."""
    map_path = Path('data/etf_isin_ticker_map.csv')
    map_path.parent.mkdir(parents=True, exist_ok=True)

    existing_entries: List[List[str]] = []
    isin_exists = False

    if map_path.exists():
        with open(map_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    if row[0] == 'ISIN':
                        continue
                    if row[0] == isin:
                        existing_entries.append([isin, ticker, name])
                        isin_exists = True
                    else:
                        existing_entries.append(row)

    if not isin_exists:
        existing_entries.append([isin, ticker, name])

    with open(map_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ISIN', 'Ticker', 'Name'])
        writer.writerows(existing_entries)
