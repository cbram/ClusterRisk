"""
ETF Data Fetcher
Ruft ETF-Zusammensetzungen von verschiedenen Quellen ab
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from typing import Dict, List, Optional
import yfinance as yf
from pathlib import Path
import json
from datetime import datetime, timedelta
import time
from src.mock_etf_holdings import get_mock_holdings
from src.user_etf_holdings import get_user_holdings_manager


class ETFDataFetcher:
    """
    Fetcher für ETF-Zusammensetzungsdaten aus verschiedenen Quellen
    """
    
    def __init__(self, cache_dir: str = "data/cache", cache_days: int = 7):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_days = cache_days
    
    def get_etf_holdings(self, isin: str, use_cache: bool = True, ticker_symbol: str = '') -> Optional[Dict]:
        """
        Holt die Zusammensetzung eines ETFs
        
        Args:
            isin: ISIN des ETFs
            use_cache: Verwende gecachte Daten wenn verfügbar
            ticker_symbol: Optional - Ticker-Symbol aus Portfolio Performance
        
        Returns:
            Dict mit Holdings-Daten oder None
        """
        
        print(f"DEBUG: Fetching ETF holdings for {isin}...")
        if ticker_symbol:
            print(f"DEBUG:   Ticker symbol from PP: {ticker_symbol}")
        
        # Cache prüfen
        if use_cache:
            cached_data = self._load_from_cache(isin)
            if cached_data:
                print(f"DEBUG:   ✅ Loaded from cache: {len(cached_data.get('holdings', []))} holdings")
                return cached_data
        
        # Verschiedene Quellen probieren
        holdings = None
        
        # 0. Prüfe User-definierte Holdings (höchste Priorität!)
        user_mgr = get_user_holdings_manager()
        holdings = user_mgr.get_holdings(isin)
        if holdings:
            print(f"DEBUG:   ✅ Using user-defined holdings: {len(holdings.get('holdings', []))} holdings")
            return holdings
        
        # 1. Versuche justETF
        print(f"DEBUG:   Trying justETF...")
        holdings = self._fetch_from_justetf(isin)
        
        # 2. Fallback: extraETF
        if not holdings:
            print(f"DEBUG:   Trying extraETF...")
            holdings = self._fetch_from_extraetf(isin)
        
        # 3. Fallback: iShares direkt (für iShares ETFs)
        if not holdings:
            print(f"DEBUG:   Trying iShares...")
            holdings = self._fetch_from_ishares(isin)
        
        # 4. Fallback: Yahoo Finance
        if not holdings:
            print(f"DEBUG:   Trying Yahoo Finance...")
            # Nutze Ticker-Symbol aus PP falls vorhanden
            holdings = self._fetch_from_yahoo(isin, ticker_symbol=ticker_symbol)
        
        # 5. Fallback: Mock Data für bekannte ETFs
        if not holdings:
            print(f"DEBUG:   Trying Mock Data...")
            holdings = get_mock_holdings(isin)
            if holdings:
                print(f"DEBUG:   ✅ Using mock data for {isin}: {len(holdings.get('holdings', []))} holdings")
        
        # Cache speichern
        if holdings:
            self._save_to_cache(isin, holdings)
        else:
            print(f"DEBUG:   ❌ No holdings found for {isin}")
        
        return holdings
    
    def _fetch_from_justetf(self, isin: str) -> Optional[Dict]:
        """
        Holt Daten von justETF.com
        """
        try:
            url = f"https://www.justetf.com/de/etf-profile.html?isin={isin}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # ETF-Name
            name_elem = soup.find('h1', {'class': 'h2'})
            etf_name = name_elem.text.strip() if name_elem else "Unknown"
            
            # Holdings extrahieren
            holdings = []
            holdings_table = soup.find('table', {'class': 'table'})
            
            if holdings_table:
                rows = holdings_table.find_all('tr')[1:]  # Header überspringen
                
                for row in rows[:50]:  # Top 50 Holdings
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        company = cols[0].text.strip()
                        weight_text = cols[1].text.strip().replace('%', '').replace(',', '.')
                        
                        try:
                            weight = float(weight_text)
                            holdings.append({
                                'name': company,
                                'weight': weight / 100.0  # Als Dezimal
                            })
                        except ValueError:
                            continue
            
            if holdings:
                return {
                    'isin': isin,
                    'name': etf_name,
                    'holdings': holdings,
                    'source': 'justETF',
                    'fetch_date': datetime.now().isoformat()
                }
        
        except Exception as e:
            print(f"justETF fetch failed for {isin}: {str(e)}")
        
        return None
    
    def _fetch_from_extraetf(self, isin: str) -> Optional[Dict]:
        """
        Holt Daten von extraETF.com
        """
        try:
            url = f"https://de.extraetf.com/etf-profile/{isin}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # ETF-Name
            name_elem = soup.find('h1')
            etf_name = name_elem.text.strip() if name_elem else "Unknown"
            
            # Holdings extrahieren (ähnliche Logik wie justETF)
            holdings = []
            # TODO: Implementiere spezifisches Parsing für extraETF
            
            if holdings:
                return {
                    'isin': isin,
                    'name': etf_name,
                    'holdings': holdings,
                    'source': 'extraETF',
                    'fetch_date': datetime.now().isoformat()
                }
        
        except Exception as e:
            print(f"extraETF fetch failed for {isin}: {str(e)}")
        
        return None
    
    def _fetch_from_ishares(self, isin: str) -> Optional[Dict]:
        """
        Holt Daten direkt von iShares (für iShares ETFs)
        """
        try:
            # iShares API endpoint
            url = f"https://www.ishares.com/uk/individual/en/products/etf-investments"
            # TODO: Implementiere iShares API Zugriff
            
            pass
        
        except Exception as e:
            print(f"iShares fetch failed for {isin}: {str(e)}")
        
        return None
    
    def _fetch_from_yahoo(self, isin: str, ticker_symbol: str = '') -> Optional[Dict]:
        """
        Holt Daten von Yahoo Finance (funktioniert für viele ETFs)
        
        Args:
            isin: ISIN des ETFs
            ticker_symbol: Optional - Ticker aus Portfolio Performance (bevorzugt!)
        """
        try:
            # 1. Verwende Ticker aus PP wenn vorhanden (höchste Priorität!)
            if ticker_symbol:
                ticker_to_use = ticker_symbol
                print(f"  Using ticker from PP: {ticker_to_use}")
            else:
                # 2. Fallback: ISIN zu Ticker konvertieren
                ticker_to_use = self._isin_to_ticker(isin)
                if not ticker_to_use:
                    return None
                print(f"  Converted ISIN to ticker: {ticker_to_use}")
            
            print(f"  Fetching holdings for {isin} via Yahoo Finance ({ticker_to_use})...")
            
            ticker = yf.Ticker(ticker_to_use)
            
            # Yahoo Finance hat leider keine ETF-Holdings für europäische ETFs
            # Wir können nur die Info holen
            try:
                info = ticker.info
                if info and 'longName' in info:
                    print(f"  ✅ ETF found on Yahoo: {info.get('longName', 'Unknown')}")
                    print(f"  ⚠️  But Yahoo Finance doesn't provide holdings for European ETFs")
                    return None
            except Exception as e:
                print(f"  ❌ Yahoo Finance lookup failed: {str(e)}")
                return None
        
        except Exception as e:
            print(f"Yahoo Finance fetch failed for {isin}: {str(e)}")
        
        return None
    
    def _isin_to_ticker(self, isin: str) -> Optional[str]:
        """
        Konvertiert ISIN zu Yahoo Finance Ticker
        """
        # Bekannte Mappings (manuell gepflegt für häufige ETFs)
        isin_to_ticker_map = {
            # iShares
            'IE00B4L5Y983': 'EUNL.DE',  # iShares Core MSCI World UCITS ETF
            'IE00B4L5YC18': 'EIMI.DE',  # iShares MSCI Emerging Markets
            'IE00B3RBWM25': 'VWRL.L',   # Vanguard FTSE All-World
            'IE00BK5BQT80': 'VWCE.DE',  # Vanguard FTSE All-World (Acc)
            'IE00B8GKDB10': 'VHYL.L',   # Vanguard FTSE All-World High Dividend Yield
            'IE00B4X9L533': 'HMWO.DE',  # HSBC MSCI World
            'IE00BZ56RG20': 'XDWD.DE',  # Xtrackers MSCI World
            'LU1681045370': 'GERD.DE',  # Amundi MSCI Germany
            'LU0274208692': 'DBXD.DE',  # Xtrackers DAX UCITS ETF
            'IE00B4L5YX21': 'IQQH.DE',  # iShares MSCI Japan
            'LU0328475792': 'DBXJ.DE',  # Xtrackers MSCI Japan
            'IE00B14X4M10': 'EUNA.DE',  # iShares MSCI North America
            'IE00B53SZB19': 'CSNDX.L',  # iShares NASDAQ 100
            'IE00B3XXRP09': 'VUSA.L',   # Vanguard S&P 500
            'IE00B5BMR087': 'CSPX.L',   # iShares Core S&P 500
        }
        
        # 1. Prüfe ob in Map
        if isin in isin_to_ticker_map:
            return isin_to_ticker_map[isin]
        
        # 2. Versuche OpenFIGI API (kostenlos, offiziell für ISIN→Ticker Mapping)
        try:
            openfigi_url = "https://api.openfigi.com/v3/mapping"
            headers = {'Content-Type': 'application/json'}
            payload = [{"idType": "ID_ISIN", "idValue": isin}]
            
            response = requests.post(openfigi_url, json=payload, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0 and 'data' in data[0]:
                    for item in data[0]['data']:
                        # Suche nach Yahoo Finance kompatiblen Tickern
                        ticker = item.get('ticker')
                        exchange = item.get('exchCode')
                        
                        if ticker and exchange:
                            # Konvertiere Exchange zu Yahoo-Suffix
                            yahoo_suffix = self._exchange_to_yahoo_suffix(exchange)
                            if yahoo_suffix:
                                yahoo_ticker = f"{ticker}.{yahoo_suffix}" if yahoo_suffix else ticker
                                print(f"  ✅ Found via OpenFIGI: {isin} → {yahoo_ticker}")
                                return yahoo_ticker
        except Exception as e:
            print(f"  OpenFIGI lookup failed: {str(e)}")
        
        # 3. Fallback: Versuche typische Ticker-Formate basierend auf ISIN
        country_code = isin[:2]
        possible_tickers = []
        
        if country_code == 'LU':
            # Luxemburg ETFs oft an deutschen Börsen mit eigenem Symbol
            # Kann nicht automatisch gemappt werden - braucht manuelle Eingabe
            pass
        elif country_code == 'IE':
            # Irische ETFs oft in London (.L) oder Deutschland (.DE)
            possible_tickers.extend([f"{isin}.L", f"{isin}.DE"])
        elif country_code == 'DE':
            possible_tickers.append(f"{isin}.DE")
        
        print(f"  ⚠️  No ticker found for ISIN {isin} - add to manual mapping")
        return None
    
    def _exchange_to_yahoo_suffix(self, exchange_code: str) -> Optional[str]:
        """
        Konvertiert Exchange-Codes zu Yahoo Finance Suffixen
        """
        exchange_map = {
            'GY': 'DE',  # XETRA → .DE
            'GR': 'DE',  # Frankfurt → .DE  
            'LN': 'L',   # London → .L
            'US': '',    # US → kein Suffix
            'SW': 'SW',  # Swiss → .SW
            'PA': 'PA',  # Paris → .PA
            'AS': 'AS',  # Amsterdam → .AS
        }
        return exchange_map.get(exchange_code)
    
    def _load_from_cache(self, isin: str) -> Optional[Dict]:
        """
        Lädt ETF-Daten aus dem Cache
        """
        cache_file = self.cache_dir / f"{isin}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Prüfe Alter des Cache
            fetch_date = datetime.fromisoformat(data['fetch_date'])
            age_days = (datetime.now() - fetch_date).days
            
            if age_days <= self.cache_days:
                return data
        
        except Exception as e:
            print(f"Cache load failed for {isin}: {str(e)}")
        
        return None
    
    def _save_to_cache(self, isin: str, data: Dict):
        """
        Speichert ETF-Daten im Cache
        """
        cache_file = self.cache_dir / f"{isin}.json"
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            print(f"Cache save failed for {isin}: {str(e)}")


def get_stock_info(isin: str) -> Optional[Dict]:
    """
    Holt Informationen zu einer Einzelaktie (Branche, Sektor, etc.)
    
    Args:
        isin: ISIN der Aktie
    
    Returns:
        Dict mit Aktien-Informationen
    """
    try:
        # Versuche über verschiedene Quellen
        ticker_symbol = _isin_to_ticker_simple(isin)
        
        if ticker_symbol:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            
            return {
                'isin': isin,
                'name': info.get('longName', 'Unknown'),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'country': info.get('country', 'Unknown'),
                'currency': info.get('currency', 'EUR')
            }
    
    except Exception as e:
        print(f"Stock info fetch failed for {isin}: {str(e)}")
    
    return None


def _isin_to_ticker_simple(isin: str) -> Optional[str]:
    """
    Vereinfachte ISIN zu Ticker Konvertierung
    """
    # TODO: Erweitere diese Funktion oder nutze eine API
    return None
