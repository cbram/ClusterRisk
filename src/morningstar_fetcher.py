"""
Morningstar Fetcher (Option B – direkte API-Integration)

Ruft die Morningstar EMEA API direkt auf, um für eine ISIN
ETF-Details im ClusterRisk-Format bereitzustellen.

Wichtige Hinweise:
- Es wird KEIN offizieller Developer-Account verwendet.
- Das Bearer-Token wird wie im pp-portfolio-classifier aus der
  öffentlichen Morningstar-Webseite (PortfolioSAL) extrahiert.
- Nutzung und Rate-Limits müssen im Zweifel mit Morningstar-AGBs
  abgeglichen werden.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, List, Optional

import requests


MORNINGSTAR_DOMAIN_DEFAULT = "de"
MORNINGSTAR_ECINT_BASE = "https://www.emea-api.morningstar.com/ecint/v1"

_BEARER_TOKEN: Optional[str] = None
_BEARER_DOMAIN: Optional[str] = None


def _get_bearer_token(domain: str = MORNINGSTAR_DOMAIN_DEFAULT) -> str:
    """
    Holt das Bearer-Token aus der öffentlichen Morningstar-Webseite.

    Nach Vorbild von pp-portfolio-classifier:
    - Aufruf von https://www.morningstar.{domain}/Common/funds/snapshot/PortfolioSAL.aspx
    - Regex auf `const maasToken = "..."`.
    """
    global _BEARER_TOKEN, _BEARER_DOMAIN

    if _BEARER_TOKEN and _BEARER_DOMAIN == domain:
        return _BEARER_TOKEN

    url = f"https://www.morningstar.{domain}/Common/funds/snapshot/PortfolioSAL.aspx"
    headers = {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0 Safari/537.36"
        ),
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()

    m = re.search(r'const maasToken\s*=\s*\"(.+?)\"', resp.text)
    if not m:
        raise RuntimeError("Konnte maasToken auf der Morningstar-Seite nicht finden.")

    _BEARER_TOKEN = m.group(1)
    _BEARER_DOMAIN = domain
    return _BEARER_TOKEN


def _get_headers(domain: str = MORNINGSTAR_DOMAIN_DEFAULT) -> Dict[str, str]:
    token = _get_bearer_token(domain)
    return {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "authorization": f"Bearer {token}",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0 Safari/537.36"
        ),
    }


def _asset_type_to_etf_type(allocations: Dict[str, float], security_name: str = "") -> str:
    """
    Aus Morningstar-Asset-Allocation ETF-Typ ableiten.
    Fallback: Name-basierte Erkennung für Geldmarkt/Commodity (z.B. XEON, XGDU).
    """
    stocks = allocations.get("Stocks", 0.0)
    bonds = allocations.get("Bonds", 0.0)
    cash = allocations.get("Cash", 0.0)

    if stocks >= 0.5:
        return "Stock"
    if bonds >= 0.5:
        return "Bond"
    if cash >= 0.5:
        return "Money Market"
    if stocks > 0 or bonds > 0:
        return "Stock"

    # Name-basierte Erkennung (Morningstar liefert oft 0 für Spezial-ETFs)
    name_lower = (security_name or "").lower()
    if any(kw in name_lower for kw in ("overnight", "money market", "cash", "tagesgeld", "liquidität")):
        return "Money Market"
    if any(kw in name_lower for kw in ("gold", "physical gold", "commodity", "etc ", "etf gold")):
        return "Commodity"
    if "swap" in name_lower and ("rate" in name_lower or "overnight" in name_lower):
        return "Money Market"

    return "Other"


# Bond Sector Codes (Morningstar GlobalBondSectorBreakdownLevel1) → lesbare Namen
# Quelle: pp-portfolio-classifier map Bond Sector
BOND_SECTOR_MAP = {
    "10": "Government",
    "20": "Municipal",
    "30": "Corporate",
    "40": "Securitized",
    "50": "Cash",
    "60": "Derivative",
}


def _merge_weights(pairs: List[tuple]) -> List[Dict]:
    """
    [(name, weight_dezimal)] -> [{name, weight}] mit zusammengefassten Namen.
    """
    acc: Dict[str, float] = {}
    for name, w in pairs:
        if not name:
            continue
        acc[name] = acc.get(name, 0.0) + float(w)
    return [{"name": n, "weight": v} for n, v in acc.items() if v > 0]


def get_etf_details_from_morningstar(
    isin: str, domain: str = MORNINGSTAR_DOMAIN_DEFAULT
) -> Optional[Dict]:
    """
    Holt ETF-Details für eine ISIN direkt von der Morningstar-API.

    Rückgabeformat ist kompatibel zu `ETFDetailsParser.parse_etf_file`:
    - 'type'
    - 'country_allocation': [{'name', 'weight'}] (weight in Dezimal 0..1)
    - 'sector_allocation': [{'name', 'weight'}]
    - 'currency_allocation': [] (aktuell leer – Currency Allocation wird
      bei uns aus Ländern abgeleitet)
    - 'holdings': [{'name','weight','currency','sector','country','isin'}]
    """
    try:
        headers = _get_headers(domain)
    except Exception as e:
        print(f"⚠️  Morningstar-Token konnte nicht geholt werden: {e}")
        return None

    url = f"{MORNINGSTAR_ECINT_BASE}/securities/{isin}"
    base_params = {
        "idtype": "ISIN",
        "currencyId": "EUR",
        "responseViewFormat": "json",
        "languageId": "en-UK",
    }

    # 1. ITsnapshot: volle Struktur (Country, Sector, AssetAllocations) – aber nur 10 Holdings
    try:
        resp = requests.get(
            url, params={**base_params, "viewid": "ITsnapshot"}, headers=headers, timeout=15
        )
    except Exception as e:
        print(f"⚠️  Fehler beim Abruf der Morningstar-API für {isin}: {e}")
        return None

    if resp.status_code != 200:
        print(f"⚠️  Morningstar-API {resp.status_code} für {isin}")
        return None

    try:
        data = resp.json()
    except Exception as e:
        print(f"⚠️  Ungültige JSON-Antwort von Morningstar für {isin}: {e}")
        return None

    if not isinstance(data, list) or not data:
        return None

    sec = data[0]
    portfolios = sec.get("Portfolios") or []
    portfolio = portfolios[0] if portfolios else {}

    # 2. Top25: mehr Holdings (25 statt 10); ITsnapshot liefert keine Country/Sector
    try:
        resp2 = requests.get(
            url, params={**base_params, "viewid": "Top25"}, headers=headers, timeout=15
        )
        if resp2.status_code == 200:
            data2 = resp2.json()
            if isinstance(data2, list) and data2:
                p2 = (data2[0].get("Portfolios") or [{}])[0]
                extra_holdings = p2.get("PortfolioHoldings", [])
                if len(extra_holdings) > len(portfolio.get("PortfolioHoldings", [])):
                    portfolio["PortfolioHoldings"] = extra_holdings
    except Exception:
        pass  # First request already succeeded; proceed with up to 10 holdings.

    # Asset-Type → ETF-Typ
    asset_type_alloc: Dict[str, float] = {}
    for entry in portfolio.get("AssetAllocations", []):
        if entry.get("Type") != "MorningStarDefault" or entry.get("SalePosition") != "N":
            continue
        breakdowns = entry.get("BreakdownValues") or entry.get("BreakdownValue") or []
        for b in breakdowns:
            code = str(b.get("Type") or "")
            try:
                val = float(b.get("Value"))
            except (TypeError, ValueError):
                continue
            weight = val / 100.0
            # Mapping wie in pp-portfolio-classifier
            code_map = {
                "1": "Stocks",
                "3": "Bonds",
                "7": "Cash",
                "2": "Other",
                "4": "Other",
                "5": "Other",
                "6": "Other",
                "8": "Other",
                "99": "Other",
            }
            name = code_map.get(code, "Other")
            asset_type_alloc[name] = asset_type_alloc.get(name, 0.0) + weight

    security_name = sec.get("Name", "")
    etf_type = _asset_type_to_etf_type(asset_type_alloc, security_name)

    # Country Allocation
    country_pairs: List[tuple] = []
    for ce in portfolio.get("CountryExposure", []):
        breakdowns = ce.get("BreakdownValues") or []
        for b in breakdowns:
            name = b.get("Name") or b.get("Type")
            try:
                val = float(b.get("Value"))
            except (TypeError, ValueError):
                continue
            country_pairs.append((name, val / 100.0))
    country_allocation = _merge_weights(country_pairs)

    # Sector Allocation (Aktien- und ggf. Bond-Sektoren)
    sector_pairs: List[tuple] = []
    for se in portfolio.get("GlobalStockSectorBreakdown", []):
        breakdowns = se.get("BreakdownValues") or []
        for b in breakdowns:
            name = b.get("Name") or b.get("Type")
            try:
                val = float(b.get("Value"))
            except (TypeError, ValueError):
                continue
            sector_pairs.append((name, val / 100.0))
    # Bond-Sektoren: API liefert Type als Code (10, 20, 30, …) → mappen
    for se in portfolio.get("GlobalBondSectorBreakdownLevel1", []):
        breakdowns = se.get("BreakdownValues") or []
        for b in breakdowns:
            raw = b.get("Name") or b.get("Type")
            name = BOND_SECTOR_MAP.get(str(raw), raw) if raw is not None else None
            try:
                val = float(b.get("Value"))
            except (TypeError, ValueError):
                continue
            if name:
                sector_pairs.append((name, val / 100.0))
    sector_allocation = _merge_weights(sector_pairs)

    # Holdings (inkl. Swaps/Derivate ohne ISIN, z.B. XEON)
    holdings: List[Dict] = []
    for h in portfolio.get("PortfolioHoldings", []):
        name = h.get("SecurityName") or h.get("Name") or ""
        if not name:
            continue
        try:
            val = float(h.get("Weighting"))
        except (TypeError, ValueError):
            continue
        weight = val / 100.0
        currency = h.get("CurrencyId") or ""
        sector = (
            h.get("GlobalStockSectorName")
            or h.get("SectorName")
            or h.get("GlobalStockSector")
            or "Unknown"
        )
        country = h.get("CountryName") or h.get("CountryId") or ""
        holdings.append(
            {
                "name": name,
                "weight": weight,
                "currency": currency,
                "sector": sector,
                "country": country,
                "isin": h.get("ISIN") or "",
            }
        )

    # Keine nützlichen Daten (z.B. XGDU: Morningstar hat keine Portfolio-Struktur)
    if not holdings and not country_allocation:
        return None

    return {
        "isin": isin,
        "name": sec.get("Name", ""),
        "type": etf_type or "Stock",
        "index": "",  # Optional später ergänzbar
        "region": "",
        "currency": sec.get("CurrencyId", "EUR"),
        "ter": str(sec.get("OngoingCharge", "")),
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "proxy_isin": "",
        "data_source": "Morningstar (auto)",
        "country_allocation": country_allocation,
        "sector_allocation": sector_allocation,
        "currency_allocation": [],  # Wird in ClusterRisk aus Ländern abgeleitet
        "holdings": holdings,
        "source": "morningstar_api",
    }


