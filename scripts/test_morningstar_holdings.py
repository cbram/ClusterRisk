#!/usr/bin/env python3
"""
Test: Prüft, ob die Morningstar EMEA API mehr als 10 Holdings liefert.
Verwendet den gleichen Token-Mechanismus wie der Fetcher (kein Account nötig).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import re

MORNINGSTAR_ECINT_BASE = "https://www.emea-api.morningstar.com/ecint/v1"
TEST_ISIN = "IE00B4L5Y983"  # iShares Core MSCI World (EUNL)


def get_token():
    url = "https://www.morningstar.de/Common/funds/snapshot/PortfolioSAL.aspx"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    m = re.search(r'const maasToken\s*=\s*"(.+?)"', resp.text)
    if not m:
        raise RuntimeError("Token nicht gefunden")
    return m.group(1)


def fetch_holdings(viewid: str, limit: int | None = None) -> tuple[list, dict]:
    token = get_token()
    url = f"{MORNINGSTAR_ECINT_BASE}/securities/{TEST_ISIN}"
    params = {
        "idtype": "ISIN",
        "viewid": viewid,
        "currencyId": "EUR",
        "responseViewFormat": "json",
        "languageId": "en-UK",
    }
    if limit is not None:
        params["limit"] = limit

    resp = requests.get(
        url,
        params=params,
        headers={"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    if resp.status_code != 200:
        return [], {"error": f"HTTP {resp.status_code}"}

    data = resp.json()
    if not isinstance(data, list) or not data:
        return [], {"error": "Leere Response"}

    sec = data[0]
    portfolios = sec.get("Portfolios") or []
    portfolio = portfolios[0] if portfolios else {}
    holdings = portfolio.get("PortfolioHoldings", [])

    meta = {
        "portfolios": len(portfolios),
        "raw_holdings_count": len(holdings),
        "has_country": bool(portfolio.get("CountryExposure")),
        "has_sector": bool(portfolio.get("GlobalStockSectorBreakdown")),
    }
    return holdings, meta


def main():
    print("Morningstar EMEA API – Holdings-Test (kein Account nötig, Token von Webseite)")
    print("=" * 60)
    print(f"Test-ISIN: {TEST_ISIN} (iShares Core MSCI World)")
    print()

    viewids_to_try = [
        "ITsnapshot",
        "Top25",
        "Top50",
        "Allholdings",
        "PortfolioHoldings",
    ]

    for viewid in viewids_to_try:
        print(f"viewid={viewid}:")
        holdings, meta = fetch_holdings(viewid)
        if "error" in meta:
            print(f"  -> {meta['error']}")
        else:
            extra = []
            if meta.get("has_country"):
                extra.append("Country")
            if meta.get("has_sector"):
                extra.append("Sector")
            suffix = f" (+ {', '.join(extra)})" if extra else ""
            print(f"  -> {len(holdings)} Holdings{suffix}")
            if holdings:
                for i, h in enumerate(holdings[:3]):
                    print(f"     {i+1}. {h.get('SecurityName', h.get('Name', '?'))[:40]} ({h.get('Weighting', 0):.2f}%)")
                if len(holdings) > 3:
                    print(f"     ... +{len(holdings)-3} weitere")
        print()

    # Zusätzlich: Limit-Parameter mit ITsnapshot testen
    print("ITsnapshot mit limit=50:")
    holdings, meta = fetch_holdings("ITsnapshot", limit=50)
    if "error" in meta:
        print(f"  -> {meta['error']}")
    else:
        print(f"  -> {len(holdings)} Holdings")
    print()

    print("Fazit: ITsnapshot liefert die Portfolio-Struktur inkl. Holdings.")
    print("Andere viewids könnten 404 oder andere Struktur liefern.")


if __name__ == "__main__":
    main()
