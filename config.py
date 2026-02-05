# Beispiel ETF-ISINs und Ticker-Mappings
# Füge hier deine eigenen ETFs hinzu für bessere Daten-Abruf-Erfolgsquoten

# Format: 'ISIN': 'Yahoo Finance Ticker'

ISIN_TICKER_MAP = {
    # iShares
    'IE00B4L5Y983': 'IWDA.AS',        # iShares Core MSCI World UCITS ETF
    'IE00B4L5YC18': 'IEMA.AS',        # iShares MSCI Emerging Markets UCITS ETF
    'IE00B0M62Q58': 'IMEU.L',         # iShares MSCI Europe UCITS ETF
    'IE00B14X4M10': 'IUSA.L',         # iShares Core S&P 500 UCITS ETF
    'IE00B53SZB19': 'INAA.L',         # iShares NASDAQ 100 UCITS ETF
    
    # Vanguard
    'IE00B3RBWM25': 'VWRL.L',         # Vanguard FTSE All-World UCITS ETF
    'IE00BK5BQT80': 'VWCE.DE',        # Vanguard FTSE All-World UCITS ETF Acc
    'IE00B3XXRP09': 'VUAA.L',         # Vanguard S&P 500 UCITS ETF
    'IE00BK5BQV03': 'VUSA.L',         # Vanguard S&P 500 UCITS ETF Acc
    
    # Xtrackers
    'LU0274208692': 'XMWO.DE',        # Xtrackers MSCI World UCITS ETF
    'IE00BJ0KDQ92': 'XMME.L',         # Xtrackers MSCI Emerging Markets UCITS ETF
    
    # SPDR
    'IE00B6YX5C33': 'SPPW.L',         # SPDR MSCI World UCITS ETF
    'IE00BFG1K274': 'SPYY.L',         # SPDR S&P 500 UCITS ETF
    
    # Amundi
    'LU1681043599': 'CW8.PA',         # Amundi MSCI World UCITS ETF
    
    # Weitere kannst du hier hinzufügen...
}


# Bekannte Sektor-Mappings für ETFs
# Falls ETF-Holdings keine Sektor-Infos liefern
ETF_SECTOR_MAP = {
    'Technology': [
        'IE00B3XXRP09',  # Tech-lastige ETFs
    ],
    'HealthCare': [
        # Gesundheits-ETFs
    ],
    # Weitere Sektoren...
}


# Cache-Konfiguration
CACHE_CONFIG = {
    'default_days': 7,
    'max_days': 30,
    'min_days': 1
}


# API-Konfiguration
API_CONFIG = {
    'timeout': 10,  # Sekunden
    'max_retries': 3,
    'retry_delay': 2  # Sekunden
}


# Risiko-Schwellenwerte
RISK_THRESHOLDS = {
    'high': 10.0,      # > 10% = hohes Risiko
    'medium': 5.0,     # 5-10% = mittleres Risiko
    'low': 0.0         # < 5% = niedriges Risiko
}


# Farben für Visualisierungen
COLORS = {
    'high_risk': '#ffcccc',
    'medium_risk': '#fff9cc',
    'low_risk': '#ccffcc',
    'primary': '#FF4B4B',
    'secondary': '#0068C9'
}
