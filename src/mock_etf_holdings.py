"""
Mock ETF Holdings für Testing
Enthält bekannte Top-10 Holdings von populären ETFs
"""

MOCK_ETF_HOLDINGS = {
    'IE00B4L5Y983': {  # iShares Core MSCI World UCITS ETF
        'name': 'iShares Core MSCI World UCITS ETF',
        'holdings': [
            # Top 15 Holdings (Stand: Feb 2026, justETF)
            {'name': 'Apple Inc', 'weight': 0.0498, 'currency': 'USD', 'sector': 'Technology', 'industry': 'Consumer Electronics', 'country': 'US'},
            {'name': 'NVIDIA Corp', 'weight': 0.0467, 'currency': 'USD', 'sector': 'Technology', 'industry': 'Semiconductors', 'country': 'US'},
            {'name': 'Microsoft Corp', 'weight': 0.0395, 'currency': 'USD', 'sector': 'Technology', 'industry': 'Software', 'country': 'US'},
            {'name': 'Amazon.com Inc', 'weight': 0.0228, 'currency': 'USD', 'sector': 'Consumer Cyclical', 'industry': 'Internet Retail', 'country': 'US'},
            {'name': 'Meta Platforms Inc', 'weight': 0.0163, 'currency': 'USD', 'sector': 'Communication Services', 'industry': 'Internet Content & Information', 'country': 'US'},
            {'name': 'Alphabet Inc Class A', 'weight': 0.0141, 'currency': 'USD', 'sector': 'Communication Services', 'industry': 'Internet Content & Information', 'country': 'US'},
            {'name': 'Alphabet Inc Class C', 'weight': 0.0123, 'currency': 'USD', 'sector': 'Communication Services', 'industry': 'Internet Content & Information', 'country': 'US'},
            {'name': 'Broadcom Inc', 'weight': 0.0108, 'currency': 'USD', 'sector': 'Technology', 'industry': 'Semiconductors', 'country': 'US'},
            {'name': 'Tesla Inc', 'weight': 0.0099, 'currency': 'USD', 'sector': 'Consumer Cyclical', 'industry': 'Auto Manufacturers', 'country': 'US'},
            {'name': 'Berkshire Hathaway Inc', 'weight': 0.0095, 'currency': 'USD', 'sector': 'Financial Services', 'industry': 'Insurance', 'country': 'US'},
            {'name': 'Eli Lilly and Co', 'weight': 0.0088, 'currency': 'USD', 'sector': 'Healthcare', 'industry': 'Drug Manufacturers', 'country': 'US'},
            {'name': 'JPMorgan Chase & Co', 'weight': 0.0081, 'currency': 'USD', 'sector': 'Financial Services', 'industry': 'Banks', 'country': 'US'},
            {'name': 'Walmart Inc', 'weight': 0.0074, 'currency': 'USD', 'sector': 'Consumer Staples', 'industry': 'Discount Stores', 'country': 'US'},
            {'name': 'Visa Inc', 'weight': 0.0069, 'currency': 'USD', 'sector': 'Financial Services', 'industry': 'Credit Services', 'country': 'US'},
            {'name': 'UnitedHealth Group Inc', 'weight': 0.0065, 'currency': 'USD', 'sector': 'Healthcare', 'industry': 'Healthcare Plans', 'country': 'US'},
            # Rest als "Others" - Mix aus verschiedenen Sektoren (wird pro ETF einzeln ausgewiesen)
            {'name': 'Other Holdings (>1400 positions)', 'weight': 0.6906, 'currency': 'Mixed', 'sector': 'Diversified', 'industry': 'Diversified', 'country': 'Mixed'}
        ],
        'source': 'Mock Data (justETF Feb 2026)',
        'fetch_date': '2026-02-04'
    },
    'IE00B8GKDB10': {  # Vanguard FTSE All-World High Dividend Yield UCITS ETF
        'name': 'Vanguard FTSE All-World High Dividend Yield UCITS ETF',
        'holdings': [
            # Basierend auf Sektor-Gewichtung: Financials 29.73%, Industrials 12.04%, Healthcare 11.02%
            {'name': 'JPMorgan Chase & Co', 'weight': 0.0195, 'currency': 'USD', 'sector': 'Financial Services', 'industry': 'Banks', 'country': 'US'},
            {'name': 'Johnson & Johnson', 'weight': 0.0187, 'currency': 'USD', 'sector': 'Healthcare', 'industry': 'Drug Manufacturers', 'country': 'US'},
            {'name': 'Exxon Mobil Corp', 'weight': 0.0176, 'currency': 'USD', 'sector': 'Energy', 'industry': 'Oil & Gas', 'country': 'US'},
            {'name': 'Procter & Gamble Co', 'weight': 0.0164, 'currency': 'USD', 'sector': 'Consumer Defensive', 'industry': 'Household Products', 'country': 'US'},
            {'name': 'Bank of America Corp', 'weight': 0.0153, 'currency': 'USD', 'sector': 'Financial Services', 'industry': 'Banks', 'country': 'US'},
            {'name': 'AbbVie Inc', 'weight': 0.0142, 'currency': 'USD', 'sector': 'Healthcare', 'industry': 'Drug Manufacturers', 'country': 'US'},
            {'name': 'Coca-Cola Co', 'weight': 0.0138, 'currency': 'USD', 'sector': 'Consumer Defensive', 'industry': 'Beverages', 'country': 'US'},
            {'name': 'Chevron Corp', 'weight': 0.0131, 'currency': 'USD', 'sector': 'Energy', 'industry': 'Oil & Gas', 'country': 'US'},
            {'name': 'PepsiCo Inc', 'weight': 0.0125, 'currency': 'USD', 'sector': 'Consumer Defensive', 'industry': 'Beverages', 'country': 'US'},
            {'name': 'Merck & Co Inc', 'weight': 0.0119, 'currency': 'USD', 'sector': 'Healthcare', 'industry': 'Drug Manufacturers', 'country': 'US'},
            {'name': 'Pfizer Inc', 'weight': 0.0112, 'currency': 'USD', 'sector': 'Healthcare', 'industry': 'Drug Manufacturers', 'country': 'US'},
            {'name': 'Cisco Systems Inc', 'weight': 0.0105, 'currency': 'USD', 'sector': 'Technology', 'industry': 'Communication Equipment', 'country': 'US'},
            # Rest als "Others" - diversifiziert nach Sektor-Gewichtung
            {'name': 'Other Holdings (>1800 positions)', 'weight': 0.8253, 'currency': 'Mixed', 'sector': 'Diversified', 'industry': 'Diversified', 'country': 'Mixed'}
        ],
        'source': 'Mock Data (Vanguard Feb 2026)',
        'fetch_date': '2026-02-04'
    },
    'IE00B3RBWM25': {  # Vanguard FTSE All-World UCITS ETF
        'name': 'Vanguard FTSE All-World UCITS ETF',
        'holdings': [
            {'name': 'Apple Inc', 'weight': 0.0445, 'currency': 'USD', 'sector': 'Technology', 'industry': 'Consumer Electronics', 'country': 'US'},
            {'name': 'Microsoft Corp', 'weight': 0.0391, 'currency': 'USD', 'sector': 'Technology', 'industry': 'Software', 'country': 'US'},
            {'name': 'Amazon.com Inc', 'weight': 0.0201, 'currency': 'USD', 'sector': 'Consumer Cyclical', 'industry': 'Internet Retail', 'country': 'US'},
            {'name': 'NVIDIA Corp', 'weight': 0.0198, 'currency': 'USD', 'sector': 'Technology', 'industry': 'Semiconductors', 'country': 'US'},
            {'name': 'Alphabet Inc Class A', 'weight': 0.0125, 'currency': 'USD', 'sector': 'Communication Services', 'industry': 'Internet Content & Information', 'country': 'US'},
            {'name': 'Meta Platforms Inc', 'weight': 0.0149, 'currency': 'USD', 'sector': 'Communication Services', 'industry': 'Internet Content & Information', 'country': 'US'},
            {'name': 'Alphabet Inc Class C', 'weight': 0.0109, 'currency': 'USD', 'sector': 'Communication Services', 'industry': 'Internet Content & Information', 'country': 'US'},
            {'name': 'Tesla Inc', 'weight': 0.0131, 'currency': 'USD', 'sector': 'Consumer Cyclical', 'industry': 'Auto Manufacturers', 'country': 'US'},
            {'name': 'Berkshire Hathaway Inc', 'weight': 0.0128, 'currency': 'USD', 'sector': 'Financial Services', 'industry': 'Insurance', 'country': 'US'},
            {'name': 'Broadcom Inc', 'weight': 0.0095, 'currency': 'USD', 'sector': 'Technology', 'industry': 'Semiconductors', 'country': 'US'},
            {'name': 'Other Holdings (>3900 positions)', 'weight': 0.8028, 'currency': 'Mixed', 'sector': 'Diversified', 'industry': 'Diversified', 'country': 'Mixed'}
        ],
        'source': 'Mock Data',
        'fetch_date': '2024-01-01'
    },
    'IE00BK5BQT80': {  # Vanguard FTSE All-World UCITS ETF (Acc)
        'name': 'Vanguard FTSE All-World UCITS ETF (Acc)',
        'holdings': [
            {'name': 'Apple Inc', 'weight': 0.0445, 'currency': 'USD', 'sector': 'Technology', 'industry': 'Consumer Electronics', 'country': 'US'},
            {'name': 'Microsoft Corp', 'weight': 0.0391, 'currency': 'USD', 'sector': 'Technology', 'industry': 'Software', 'country': 'US'},
            {'name': 'Amazon.com Inc', 'weight': 0.0201, 'currency': 'USD', 'sector': 'Consumer Cyclical', 'industry': 'Internet Retail', 'country': 'US'},
            {'name': 'NVIDIA Corp', 'weight': 0.0198, 'currency': 'USD', 'sector': 'Technology', 'industry': 'Semiconductors', 'country': 'US'},
            {'name': 'Alphabet Inc Class A', 'weight': 0.0125, 'currency': 'USD', 'sector': 'Communication Services', 'industry': 'Internet Content & Information', 'country': 'US'},
            {'name': 'Meta Platforms Inc', 'weight': 0.0149, 'currency': 'USD', 'sector': 'Communication Services', 'industry': 'Internet Content & Information', 'country': 'US'},
            {'name': 'Alphabet Inc Class C', 'weight': 0.0109, 'currency': 'USD', 'sector': 'Communication Services', 'industry': 'Internet Content & Information', 'country': 'US'},
            {'name': 'Tesla Inc', 'weight': 0.0131, 'currency': 'USD', 'sector': 'Consumer Cyclical', 'industry': 'Auto Manufacturers', 'country': 'US'},
            {'name': 'Berkshire Hathaway Inc', 'weight': 0.0128, 'currency': 'USD', 'sector': 'Financial Services', 'industry': 'Insurance', 'country': 'US'},
            {'name': 'Broadcom Inc', 'weight': 0.0095, 'currency': 'USD', 'sector': 'Technology', 'industry': 'Semiconductors', 'country': 'US'},
            {'name': 'Other Holdings (>3900 positions)', 'weight': 0.8028, 'currency': 'Mixed', 'sector': 'Diversified', 'industry': 'Diversified', 'country': 'Mixed'}
        ],
        'source': 'Mock Data',
        'fetch_date': '2024-01-01'
    }
}


def get_mock_holdings(isin: str):
    """
    Gibt Mock-Holdings für bekannte ETFs zurück
    """
    if isin in MOCK_ETF_HOLDINGS:
        data = MOCK_ETF_HOLDINGS[isin].copy()
        data['isin'] = isin
        return data
    return None
