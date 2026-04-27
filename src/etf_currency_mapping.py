"""
Shared country-to-currency mapping and derivation logic.

Extracted here to break the circular import between etf_detail_generator
and etf_detail_writer.
"""

from typing import Dict, List


COUNTRY_TO_CURRENCY: Dict[str, str] = {
    # Nordamerika
    'United States': 'USD', 'US': 'USD', 'USA': 'USD',
    'Canada': 'CAD', 'CA': 'CAD',
    'Mexico': 'MXN', 'MX': 'MXN',

    # Europa (EUR-Zone)
    'Germany': 'EUR', 'DE': 'EUR', 'Deutschland': 'EUR',
    'France': 'EUR', 'FR': 'EUR', 'Frankreich': 'EUR',
    'Netherlands': 'EUR', 'NL': 'EUR', 'Niederlande': 'EUR',
    'Italy': 'EUR', 'IT': 'EUR', 'Italien': 'EUR',
    'Spain': 'EUR', 'ES': 'EUR', 'Spanien': 'EUR',
    'Belgium': 'EUR', 'BE': 'EUR', 'Belgien': 'EUR',
    'Austria': 'EUR', 'AT': 'EUR', 'Österreich': 'EUR',
    'Finland': 'EUR', 'FI': 'EUR', 'Finnland': 'EUR',
    'Ireland': 'EUR', 'IE': 'EUR', 'Irland': 'EUR',
    'Portugal': 'EUR', 'PT': 'EUR',
    'Greece': 'EUR', 'GR': 'EUR', 'Griechenland': 'EUR',
    'Luxembourg': 'EUR', 'LU': 'EUR', 'Luxemburg': 'EUR',
    'Slovakia': 'EUR', 'SK': 'EUR',
    'Slovenia': 'EUR', 'SI': 'EUR',
    'Estonia': 'EUR', 'EE': 'EUR',
    'Latvia': 'EUR', 'LV': 'EUR',
    'Lithuania': 'EUR', 'LT': 'EUR',
    'Cyprus': 'EUR', 'CY': 'EUR',
    'Malta': 'EUR', 'MT': 'EUR',
    'Croatia': 'EUR', 'HR': 'EUR',
    'Eurozone': 'EUR', 'EU': 'EUR',

    # Europa (Nicht-EUR)
    'United Kingdom': 'GBP', 'GB': 'GBP', 'UK': 'GBP', 'Großbritannien': 'GBP',
    'Switzerland': 'CHF', 'CH': 'CHF', 'Schweiz': 'CHF',
    'Sweden': 'SEK', 'SE': 'SEK', 'Schweden': 'SEK',
    'Norway': 'NOK', 'NO': 'NOK', 'Norwegen': 'NOK',
    'Denmark': 'DKK', 'DK': 'DKK', 'Dänemark': 'DKK',
    'Poland': 'PLN', 'PL': 'PLN', 'Polen': 'PLN',
    'Czech Republic': 'CZK', 'CZ': 'CZK', 'Czechia': 'CZK',
    'Hungary': 'HUF', 'HU': 'HUF', 'Ungarn': 'HUF',
    'Romania': 'RON', 'RO': 'RON', 'Rumänien': 'RON',
    'Turkey': 'TRY', 'TR': 'TRY', 'Türkei': 'TRY',
    'Russia': 'RUB', 'RU': 'RUB', 'Russland': 'RUB',
    'Iceland': 'ISK', 'IS': 'ISK',

    # Asien
    'Japan': 'JPY', 'JP': 'JPY',
    'China': 'CNY', 'CN': 'CNY',
    'Hong Kong': 'HKD', 'HK': 'HKD', 'Hongkong': 'HKD',
    'South Korea': 'KRW', 'KR': 'KRW', 'Korea': 'KRW',
    'Taiwan': 'TWD', 'TW': 'TWD',
    'India': 'INR', 'IN': 'INR', 'Indien': 'INR',
    'Singapore': 'SGD', 'SG': 'SGD', 'Singapur': 'SGD',
    'Indonesia': 'IDR', 'ID': 'IDR', 'Indonesien': 'IDR',
    'Thailand': 'THB', 'TH': 'THB',
    'Malaysia': 'MYR', 'MY': 'MYR',
    'Philippines': 'PHP', 'PH': 'PHP', 'Philippinen': 'PHP',
    'Vietnam': 'VND', 'VN': 'VND',
    'Pakistan': 'PKR', 'PK': 'PKR',
    'Bangladesh': 'BDT', 'BD': 'BDT',
    'Sri Lanka': 'LKR', 'LK': 'LKR',

    # Ozeanien
    'Australia': 'AUD', 'AU': 'AUD', 'Australien': 'AUD',
    'New Zealand': 'NZD', 'NZ': 'NZD', 'Neuseeland': 'NZD',

    # Naher Osten
    'Saudi Arabia': 'SAR', 'SA': 'SAR', 'Saudi-Arabien': 'SAR',
    'United Arab Emirates': 'AED', 'AE': 'AED',
    'Israel': 'ILS', 'IL': 'ILS',
    'Qatar': 'QAR', 'QA': 'QAR',
    'Kuwait': 'KWD', 'KW': 'KWD',

    # Südamerika
    'Brazil': 'BRL', 'BR': 'BRL', 'Brasilien': 'BRL',
    'Argentina': 'ARS', 'AR': 'ARS', 'Argentinien': 'ARS',
    'Chile': 'CLP', 'CL': 'CLP',
    'Colombia': 'COP', 'CO': 'COP', 'Kolumbien': 'COP',
    'Peru': 'PEN', 'PE': 'PEN',

    # Afrika
    'South Africa': 'ZAR', 'ZA': 'ZAR', 'Südafrika': 'ZAR',
    'Nigeria': 'NGN', 'NG': 'NGN',
    'Kenya': 'KES', 'KE': 'KES',
    'Egypt': 'EGP', 'EG': 'EGP', 'Ägypten': 'EGP',
    'Morocco': 'MAD', 'MA': 'MAD', 'Marokko': 'MAD',
}


def derive_currency_allocation(country_allocation: List[Dict]) -> List[Dict]:
    """Derive currency allocation from country allocation.

    Eurozone countries are aggregated into EUR. Entries where country is
    'other' or unknown are collected and emitted as 'Other' when > 0.1%.

    Args:
        country_allocation: list of {'name': str, 'weight': float}

    Returns:
        list of {'name': currency_code, 'weight': float}, sorted descending by weight
    """
    currency_weights: Dict[str, float] = {}
    unmapped_weight = 0.0

    for entry in country_allocation:
        country = entry['name']
        weight = entry['weight']
        currency = COUNTRY_TO_CURRENCY.get(country)

        if currency:
            currency_weights[currency] = currency_weights.get(currency, 0.0) + weight
        elif country.lower() == 'other':
            unmapped_weight += weight
        else:
            matched = False
            for key, cur in COUNTRY_TO_CURRENCY.items():
                if key.lower() in country.lower() or country.lower() in key.lower():
                    currency_weights[cur] = currency_weights.get(cur, 0.0) + weight
                    matched = True
                    break
            if not matched:
                unmapped_weight += weight

    result = [
        {'name': cur, 'weight': w}
        for cur, w in sorted(currency_weights.items(), key=lambda x: x[1], reverse=True)
    ]
    if unmapped_weight > 0.1:
        result.append({'name': 'Other', 'weight': unmapped_weight})
    return result
