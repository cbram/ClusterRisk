"""
Ticker-zu-Sektor Mapping mit automatischem Caching und API-Fallback
"""

import json
import requests
from pathlib import Path
from datetime import datetime, timedelta
import yfinance as yf
from typing import Dict, Optional, Tuple

class TickerSectorMapper:
    """
    Verwaltet Ticker-zu-Sektor-Zuordnungen mit lokalem Cache und API-Fallback
    """
    
    def __init__(self, cache_file: str = "data/ticker_sector_cache.json"):
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache = self._load_cache()
        
        # Sektor-Normalisierung (Yahoo Finance -> Standard)
        self.sector_mapping = {
            'Technology': 'Technology',
            'Financial Services': 'Financial Services',
            'Healthcare': 'Healthcare',
            'Consumer Cyclical': 'Consumer Cyclical',
            'Consumer Defensive': 'Consumer Staples',
            'Industrials': 'Industrials',
            'Basic Materials': 'Materials',
            'Energy': 'Energy',
            'Utilities': 'Utilities',
            'Real Estate': 'Real Estate',
            'Communication Services': 'Communication Services',
            'Communications': 'Communication Services',
            'Consumer Discretionary': 'Consumer Cyclical',
            'Consumer Staples': 'Consumer Staples',
            'Materials': 'Materials',
            'Information Technology': 'Technology',
            'Financials': 'Financial Services',
            'Health Care': 'Healthcare',
        }
    
    def _load_cache(self) -> Dict:
        """Lade Cache aus JSON-Datei"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    print(f"✅ Ticker-Sektor-Cache geladen: {len(cache)} Einträge")
                    return cache
            except Exception as e:
                print(f"⚠️  Fehler beim Laden des Caches: {e}")
                return {}
        return {}
    
    def _save_cache(self):
        """Speichere Cache in JSON-Datei"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
            print(f"💾 Ticker-Sektor-Cache gespeichert: {len(self.cache)} Einträge")
        except Exception as e:
            print(f"⚠️  Fehler beim Speichern des Caches: {e}")
    
    def _normalize_sector(self, sector: str) -> str:
        """Normalisiere Sektor-Namen"""
        if not sector:
            return 'Unknown'
        return self.sector_mapping.get(sector, sector)
    
    def _is_cache_valid(self, ticker: str, max_age_days: int = 90) -> bool:
        """Prüfe ob Cache-Eintrag noch gültig ist"""
        if ticker not in self.cache:
            return False
        
        entry = self.cache[ticker]
        if 'timestamp' not in entry:
            return False
        
        timestamp = datetime.fromisoformat(entry['timestamp'])
        age = datetime.now() - timestamp
        return age.days < max_age_days
    
    def _fetch_from_yahoo(self, ticker: str) -> Optional[str]:
        """Hole Sektor von Yahoo Finance"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            sector = info.get('sector')
            if sector:
                print(f"  📡 Yahoo Finance: {ticker} -> {sector}")
                return self._normalize_sector(sector)
            
        except Exception as e:
            print(f"  ⚠️  Yahoo Finance Fehler für {ticker}: {e}")
        
        return None
    
    def _fetch_from_openfigi(self, ticker: str) -> Optional[str]:
        """Hole Sektor von OpenFIGI API"""
        try:
            # OpenFIGI API
            url = "https://api.openfigi.com/v3/mapping"
            headers = {'Content-Type': 'application/json'}
            
            payload = [{
                "idType": "TICKER",
                "idValue": ticker,
                "exchCode": "US"  # US Exchange als Standard
            }]
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0 and 'data' in data[0]:
                    figi_data = data[0]['data'][0]
                    sector = figi_data.get('marketSector')
                    if sector:
                        print(f"  📡 OpenFIGI: {ticker} -> {sector}")
                        return self._normalize_sector(sector)
        
        except Exception as e:
            print(f"  ⚠️  OpenFIGI Fehler für {ticker}: {e}")
        
        return None
    
    def get_sector(self, ticker: str, use_cache: bool = True, max_age_days: int = 90) -> str:
        """
        Hole Sektor für einen Ticker
        
        Args:
            ticker: Ticker-Symbol (z.B. "AAPL", "MSFT")
            use_cache: Nutze Cache wenn verfügbar
            max_age_days: Maximales Alter des Cache-Eintrags in Tagen
            
        Returns:
            Sektor-Name oder "Unknown"
        """
        if not ticker:
            return 'Unknown'
        
        # Ticker normalisieren (Großbuchstaben)
        ticker = ticker.upper().strip()
        
        # 1. Prüfe Cache
        if use_cache and self._is_cache_valid(ticker, max_age_days):
            sector = self.cache[ticker].get('sector', 'Unknown')
            print(f"  💾 Cache-Hit: {ticker} -> {sector}")
            return sector
        
        # 2. Hole von Yahoo Finance
        sector = self._fetch_from_yahoo(ticker)
        
        # 3. Fallback: OpenFIGI
        if not sector or sector == 'Unknown':
            sector = self._fetch_from_openfigi(ticker)
        
        # 4. Fallback: Unknown
        if not sector:
            sector = 'Unknown'
            print(f"  ❓ Kein Sektor gefunden für {ticker}")
        
        # 5. Speichere im Cache
        self.cache[ticker] = {
            'sector': sector,
            'timestamp': datetime.now().isoformat(),
            'source': 'yahoo' if sector != 'Unknown' else 'unknown'
        }
        self._save_cache()
        
        return sector
    
    def get_sectors_batch(self, tickers: list, use_cache: bool = True) -> Dict[str, str]:
        """
        Hole Sektoren für mehrere Tickers auf einmal
        
        Args:
            tickers: Liste von Ticker-Symbolen
            use_cache: Nutze Cache wenn verfügbar
            
        Returns:
            Dictionary mit Ticker -> Sektor Zuordnungen
        """
        results = {}
        
        for ticker in tickers:
            if ticker:
                results[ticker] = self.get_sector(ticker, use_cache=use_cache)
        
        return results
    
    def manual_update(self, ticker: str, sector: str):
        """
        Manuelles Update eines Ticker-Sektor-Mappings
        
        Args:
            ticker: Ticker-Symbol
            sector: Sektor-Name
        """
        ticker = ticker.upper().strip()
        sector = self._normalize_sector(sector)
        
        self.cache[ticker] = {
            'sector': sector,
            'timestamp': datetime.now().isoformat(),
            'source': 'manual'
        }
        self._save_cache()
        print(f"✏️  Manual Update: {ticker} -> {sector}")
    
    def clear_cache(self):
        """Lösche kompletten Cache"""
        self.cache = {}
        self._save_cache()
        print("🗑️  Cache gelöscht")
    
    def get_cache_stats(self) -> Dict:
        """Hole Cache-Statistiken"""
        if not self.cache:
            return {
                'total': 0,
                'by_source': {},
                'oldest': None,
                'newest': None
            }
        
        sources = {}
        timestamps = []
        
        for ticker, entry in self.cache.items():
            source = entry.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
            
            if 'timestamp' in entry:
                timestamps.append(datetime.fromisoformat(entry['timestamp']))
        
        return {
            'total': len(self.cache),
            'by_source': sources,
            'oldest': min(timestamps).isoformat() if timestamps else None,
            'newest': max(timestamps).isoformat() if timestamps else None
        }


# Globale Instanz für einfachen Import
_mapper = None

def get_mapper() -> TickerSectorMapper:
    """Hole globale Mapper-Instanz (Singleton)"""
    global _mapper
    if _mapper is None:
        _mapper = TickerSectorMapper()
    return _mapper


def get_sector_for_ticker(ticker: str, use_cache: bool = True) -> str:
    """
    Convenience-Funktion: Hole Sektor für einen Ticker
    
    Args:
        ticker: Ticker-Symbol
        use_cache: Nutze Cache wenn verfügbar
        
    Returns:
        Sektor-Name oder "Unknown"
    """
    mapper = get_mapper()
    return mapper.get_sector(ticker, use_cache=use_cache)
