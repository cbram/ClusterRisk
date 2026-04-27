"""
Morningstar CSV Importer (Option A – CSV-Brücke)

Liest die Ausgabe von pp-portfolio-classifier (pp_data_fetched.csv) und erzeugt
daraus ETF-Detail-CSVs im ClusterRisk-Format (data/etf_details/{TICKER}.csv).

Nutzung in der App:
- pp_data_fetched.csv einmal in der Sidebar hochladen & speichern (data/pp_data_fetched.csv).
- Pro ETF: „Aktualisieren“ (justETF) oder „Von Morningstar“ (aus der gespeicherten CSV).
- „Alle von Morningstar“ aktualisiert alle in der Map vorhandenen ISINs aus der CSV.
- Alter des letzten Downloads = „Last Updated“ in der generierten Datei (wie bei justETF).

Format pp_data_fetched.csv: ISIN,Taxonomy,Classification,Percentage,Name
  - Percentage ist dezimal (0.0–1.0).
  - Name = Fondsname (gleich für alle Zeilen einer ISIN).
"""

# Standardpfad der gespeicherten Morningstar-CSV (Sidebar-Upload)
PP_DATA_FETCHED_PATH = "data/pp_data_fetched.csv"

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from collections import defaultdict

from .etf_detail_generator import COUNTRY_TO_CURRENCY


# Morningstar-Sektoren → ClusterRisk-Sektor (abgestimmt mit risk_calculator._normalize_sector_name)
SECTOR_NORMALIZE = {
    'basic materials': 'Basic Materials',
    'consumer cyclical': 'Consumer Cyclical',
    'consumer defensive': 'Consumer Staples',
    'financial services': 'Financials',
    'communication services': 'Telecommunication',
    'health care': 'Health Care',
    'healthcare': 'Health Care',
    'consumer discretionary': 'Consumer Discretionary',
    'industrials': 'Industrials',
    'technology': 'Technology',
    'energy': 'Energy',
    'utilities': 'Utilities',
    'real estate': 'Real Estate',
    'materials': 'Basic Materials',
}


def _normalize_sector(classification: str) -> str:
    """Morningstar-Sektor auf ClusterRisk-Sektor abbilden."""
    if not classification or not classification.strip():
        return 'Other'
    key = classification.strip().lower()
    return SECTOR_NORMALIZE.get(key, classification.strip())


def _asset_type_to_etf_type(allocations: Dict[str, float]) -> str:
    """
    Aus Asset-Type-Allokationen den ETF-Typ für Metadata ableiten.
    Priorität: Stocks > Bonds > Cash > Other.
    """
    stocks = allocations.get('Stocks', 0.0) + allocations.get('Stock', 0.0)
    bonds = allocations.get('Bonds', 0.0) + allocations.get('Bond', 0.0)
    cash = allocations.get('Cash', 0.0)
    if stocks >= 0.5:
        return 'Stock'
    if bonds >= 0.5:
        return 'Bond'
    if cash >= 0.5:
        return 'Money Market'
    if stocks > 0 or bonds > 0:
        return 'Stock'  # Mischfonds
    return 'Other'


def _derive_currency_allocation(country_weights: List[tuple]) -> List[Dict]:
    """
    Währungsallokation aus Länderallokation ableiten (wie etf_detail_generator).
    country_weights: [(country_name, weight_dezimal), ...]
    """
    currency_weights: Dict[str, float] = {}
    other_weight = 0.0
    for country_name, weight in country_weights:
        currency = COUNTRY_TO_CURRENCY.get(country_name)
        if not currency:
            # Versuche Varianten (z. B. "United States" vs "US")
            for k, v in COUNTRY_TO_CURRENCY.items():
                if k.upper() == country_name.upper() or country_name.upper() in k.upper():
                    currency = v
                    break
        if currency:
            currency_weights[currency] = currency_weights.get(currency, 0.0) + weight
        else:
            other_weight += weight
    result = [{'name': c, 'weight': round(w * 100, 1)} for c, w in sorted(currency_weights.items(), key=lambda x: -x[1])]
    if other_weight > 0:
        result.append({'name': 'Other', 'weight': round(other_weight * 100, 1)})
    return result


def load_pp_data_fetched(csv_path: str) -> List[Dict]:
    """
    Liest pp_data_fetched.csv und gibt Zeilen als Liste von Dicts zurück.
    Keys: isin, taxonomy, classification, percentage, name
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {path}")
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header or len(header) < 5:
            raise ValueError("Ungültiges Format: Erwarte mindestens ISIN,Taxonomy,Classification,Percentage,Name")
        for row in reader:
            if len(row) < 5:
                continue
            try:
                pct = float(row[3].strip())
            except ValueError:
                continue
            rows.append({
                'isin': row[0].strip(),
                'taxonomy': row[1].strip(),
                'classification': row[2].strip(),
                'percentage': pct,
                'name': row[4].strip() if len(row) > 4 else '',
            })
    return rows


def update_single_etf_from_pp_csv(
    csv_path: str,
    isin: str,
    ticker: str,
    etf_name: str,
    output_dir: str = "data/etf_details",
    source_label: str = "Morningstar (pp-portfolio-classifier)",
) -> tuple:
    """
    Aktualisiert eine einzelne ETF-Detail-Datei aus pp_data_fetched.csv.
    Wird vom „Von Morningstar“-Button in der App aufgerufen.

    Returns:
        (success: bool, message: str)
    """
    path = Path(csv_path)
    if not path.exists():
        return False, "pp_data_fetched.csv nicht gefunden. Bitte zuerst in der Sidebar speichern."
    try:
        rows = load_pp_data_fetched(csv_path)
    except Exception as e:
        return False, str(e)
    rows_for_isin = [r for r in rows if r['isin'] == isin]
    if not rows_for_isin:
        return False, f"ISIN {isin} nicht in pp_data_fetched.csv enthalten."
    by_isin = build_etf_data_by_isin(rows_for_isin)
    if isin not in by_isin:
        return False, "Keine gültigen Daten für diese ISIN."
    data = by_isin[isin]
    name = data.get('name') or etf_name or ticker
    write_etf_detail_csv(
        isin=isin,
        ticker=ticker,
        etf_name=name,
        data=data,
        output_dir=output_dir,
        source_label=source_label,
    )
    return True, "Aktualisiert (Morningstar)."


def load_isin_ticker_map(map_path: str = "data/etf_isin_ticker_map.csv") -> Dict[str, tuple]:
    """
    Lädt ISIN -> (Ticker, Name) aus data/etf_isin_ticker_map.csv.
    Returns: { isin: (ticker, name) }
    """
    path = Path(map_path)
    if not path.exists():
        return {}
    result = {}
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            isin = (row.get('ISIN') or '').strip()
            ticker = (row.get('Ticker') or '').strip()
            name = (row.get('Name') or '').strip()
            if isin and ticker:
                result[isin] = (ticker, name)
    return result


def build_etf_data_by_isin(rows: List[Dict]) -> Dict[str, Dict]:
    """
    Gruppiert Zeilen nach ISIN und baut pro ISIN ein Struktur-Dict
    wie es unser ETF-Detail-Format erwartet (ohne Ticker).
    """
    by_isin: Dict[str, Dict] = defaultdict(lambda: {
        'name': '',
        'asset_type': {},
        'country': [],
        'sector': [],
        'region': [],
        'holding': [],
    })
    for r in rows:
        isin = r['isin']
        tax = r['taxonomy']
        classification = r['classification']
        pct = r['percentage']
        name = r['name']
        if name and not by_isin[isin]['name']:
            by_isin[isin]['name'] = name
        if tax == 'Asset Type':
            by_isin[isin]['asset_type'][classification] = by_isin[isin]['asset_type'].get(classification, 0) + pct
        elif tax == 'Country':
            by_isin[isin]['country'].append((classification, pct))
        elif tax in ('Stock Sector', 'Bond Sector'):
            norm = _normalize_sector(classification)
            by_isin[isin]['sector'].append((norm, pct))
        elif tax == 'Region':
            by_isin[isin]['region'].append((classification, pct))
        elif tax == 'Holding':
            by_isin[isin]['holding'].append((classification, pct))
    return dict(by_isin)


def write_etf_detail_csv(
    isin: str,
    ticker: str,
    etf_name: str,
    data: Dict,
    output_dir: str = "data/etf_details",
    source_label: str = "Morningstar (pp-portfolio-classifier)",
) -> Path:
    """
    Schreibt eine ETF-Detail-CSV im ClusterRisk-Format.
    data: Aus build_etf_data_by_isin (keys: name, asset_type, country, sector, region, holding).
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    filepath = out_dir / f"{ticker}.csv"
    today = datetime.now().strftime('%Y-%m-%d')
    etf_type = _asset_type_to_etf_type(data.get('asset_type', {}))
    country_list = data.get('country', [])
    # Sektoren nach Namen zusammenfassen (Summe der Gewichte)
    sector_merged: Dict[str, float] = {}
    for name, w in data.get('sector', []):
        sector_merged[name] = sector_merged.get(name, 0.0) + w
    sector_list = list(sector_merged.items())
    holding_list = data.get('holding', [])
    currency_alloc = _derive_currency_allocation(country_list)

    lines = [
        "# ETF Metadata",
        f"ISIN,{isin}",
        f"Name,{etf_name}",
        f"Ticker,{ticker}",
        f"Type,{etf_type}",
        "Index,",
        "Region,World",
        "Currency,EUR",
        "TER,",
        f"Last Updated,{today}",
        f"Source,{source_label}",
        "",
        "# Country Allocation (%)",
        "Country,Weight",
    ]
    for name, w in sorted(country_list, key=lambda x: -x[1]):
        lines.append(f"{name},{w * 100:.1f}")
    lines.extend(["", "# Sector Allocation (%)", "Sector,Weight"])
    for name, w in sorted(sector_list, key=lambda x: -x[1]):
        lines.append(f"{name},{w * 100:.1f}")
    lines.extend(["", "# Currency Allocation (%) - derived from countries", "Currency,Weight"])
    for c in currency_alloc:
        lines.append(f"{c['name']},{c['weight']:.1f}")
    lines.extend(["", "# Top Holdings", "Name,Weight,Currency,Sector,Country,ISIN"])
    for name, w in holding_list:
        # pp_data_fetched liefert pro Holding nur Name und Gewicht
        lines.append(f'"{name}",{w * 100:.2f},,Unknown,,')
    # Optional: "Other Holdings" wenn Summe < 100%
    holding_sum = sum(w for _, w in holding_list)
    if holding_list and holding_sum < 0.999:
        other_pct = (1.0 - holding_sum) * 100
        lines.append(f"Other Holdings,{other_pct:.2f},Mixed,Diversified,Mixed,")
    lines.append("")

    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        f.write('\n'.join(lines))
    return filepath


def import_pp_data_fetched(
    csv_path: str,
    output_dir: str = "data/etf_details",
    isin_ticker_map_path: str = "data/etf_isin_ticker_map.csv",
    source_label: str = "Morningstar (pp-portfolio-classifier)",
) -> Dict[str, Any]:
    """
    Hauptfunktion: Liest pp_data_fetched.csv, mappt auf Ticker und schreibt ETF-Detail-CSVs.

    Returns:
        {
            'written': [ (isin, ticker, filepath), ... ],
            'skipped_no_ticker': [ isin, ... ],
            'errors': [ message, ... ],
        }
    """
    result = {'written': [], 'skipped_no_ticker': [], 'errors': []}
    try:
        rows = load_pp_data_fetched(csv_path)
    except Exception as e:
        result['errors'].append(str(e))
        return result
    if not rows:
        result['errors'].append("Keine gültigen Zeilen in der CSV.")
        return result

    isin_to_ticker = load_isin_ticker_map(isin_ticker_map_path)
    by_isin = build_etf_data_by_isin(rows)
    # Sicherstellen, dass Fondsname aus erster Zeile pro ISIN genutzt wird
    for r in rows:
        isin = r['isin']
        if r['name'] and isin in by_isin and not by_isin[isin]['name']:
            by_isin[isin]['name'] = r['name']

    for isin, data in by_isin.items():
        if isin not in isin_to_ticker:
            result['skipped_no_ticker'].append(isin)
            continue
        ticker, map_name = isin_to_ticker[isin]
        etf_name = data['name'] or map_name or isin
        try:
            path = write_etf_detail_csv(
                isin=isin,
                ticker=ticker,
                etf_name=etf_name,
                data=data,
                output_dir=output_dir,
                source_label=source_label,
            )
            result['written'].append((isin, ticker, str(path)))
        except Exception as e:
            result['errors'].append(f"{isin} ({ticker}): {e}")

    return result


def main():
    """CLI: python -m src.morningstar_csv_importer [pp_data_fetched.csv]"""
    import argparse
    parser = argparse.ArgumentParser(
        description='Importiert pp_data_fetched.csv (pp-portfolio-classifier) nach data/etf_details/'
    )
    parser.add_argument(
        'input_csv',
        nargs='?',
        default='pp_data_fetched.csv',
        help='Pfad zu pp_data_fetched.csv (Standard: pp_data_fetched.csv im aktuellen Verzeichnis)',
    )
    parser.add_argument(
        '-o', '--output-dir',
        default='data/etf_details',
        help='Ausgabeverzeichnis für ETF-Detail-CSVs',
    )
    parser.add_argument(
        '-m', '--map',
        default='data/etf_isin_ticker_map.csv',
        help='Pfad zur ISIN-Ticker-Map CSV',
    )
    args = parser.parse_args()
    res = import_pp_data_fetched(
        csv_path=args.input_csv,
        output_dir=args.output_dir,
        isin_ticker_map_path=args.map,
    )
    for isin, ticker, path in res['written']:
        print(f"  OK: {isin} → {ticker} → {path}")
    for isin in res['skipped_no_ticker']:
        print(f"  Übersprungen (kein Ticker in Map): {isin}")
    for msg in res['errors']:
        print(f"  Fehler: {msg}")
    if res['written']:
        print(f"\n{len(res['written'])} ETF(s) nach {args.output_dir}/ geschrieben.")
    if res['skipped_no_ticker']:
        print(f"{len(res['skipped_no_ticker'])} ISIN(s) nicht in {args.map} – bitte Ticker eintragen.")


if __name__ == '__main__':
    main()
