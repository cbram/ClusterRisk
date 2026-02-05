"""
Wechselkurs-Manager
Ruft aktuelle Wechselkurse von der Europäischen Zentralbank ab
"""

import requests
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import Dict, Optional


class ExchangeRateManager:
    """
    Verwaltet Wechselkurse mit Caching
    Verwendet die EZB-API für aktuelle Kurse
    """
    
    def __init__(self, cache_dir: str = "data/cache", cache_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_hours = cache_hours
        self.cache_file = self.cache_dir / "exchange_rates.json"
        self.rates = None
    
    def get_rate(self, from_currency: str, to_currency: str = 'EUR') -> float:
        """
        Holt Wechselkurs von Fremdwährung zu EUR
        
        Args:
            from_currency: Quellwährung (z.B. 'USD')
            to_currency: Zielwährung (immer 'EUR')
        
        Returns:
            Wechselkurs (1 from_currency = X EUR)
        """
        if from_currency == to_currency:
            return 1.0
        
        # Lade Kurse (aus Cache oder API)
        if self.rates is None:
            self.rates = self._load_rates()
        
        # Hole Kurs
        rate = self.rates.get(from_currency)
        
        if rate is None:
            print(f"⚠️  Kein Wechselkurs für {from_currency} verfügbar, verwende 1.0")
            return 1.0
        
        return rate
    
    def _load_rates(self) -> Dict[str, float]:
        """
        Lädt Wechselkurse aus Cache oder von der API
        """
        # Versuche aus Cache zu laden
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                
                # Prüfe Alter
                cache_time = datetime.fromisoformat(data['timestamp'])
                age_hours = (datetime.now() - cache_time).total_seconds() / 3600
                
                if age_hours < self.cache_hours:
                    print(f"📊 Wechselkurse aus Cache geladen (Alter: {age_hours:.1f}h)")
                    return data['rates']
            
            except Exception as e:
                print(f"Cache-Fehler: {str(e)}")
        
        # Lade von API
        print("🌐 Lade aktuelle Wechselkurse von EZB...")
        rates = self._fetch_from_ecb()
        
        if rates:
            # Speichere im Cache
            self._save_to_cache(rates)
            return rates
        
        # Fallback: Statische Kurse
        print("⚠️  EZB-API nicht verfügbar, verwende statische Wechselkurse")
        return self._get_fallback_rates()
    
    def _fetch_from_ecb(self) -> Optional[Dict[str, float]]:
        """
        Holt aktuelle Wechselkurse von der EZB
        """
        try:
            # EZB Daily Rates API
            url = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse XML
            from lxml import etree
            tree = etree.fromstring(response.content)
            
            # Namespace für EZB XML
            ns = {'gesmes': 'http://www.gesmes.org/xml/2002-08-01',
                  'ecb': 'http://www.ecb.int/vocabulary/2002-08-01/eurofxref'}
            
            rates = {}
            
            # Finde alle Währungen
            for cube in tree.xpath('//ecb:Cube[@currency]', namespaces=ns):
                currency = cube.get('currency')
                rate_str = cube.get('rate')
                
                if currency and rate_str:
                    # EZB gibt: 1 EUR = X Fremdwährung
                    # Wir brauchen: 1 Fremdwährung = X EUR
                    rate = 1.0 / float(rate_str)
                    rates[currency] = rate
            
            if rates:
                print(f"✅ {len(rates)} Wechselkurse von EZB geladen")
                return rates
        
        except Exception as e:
            print(f"EZB-API Fehler: {str(e)}")
        
        return None
    
    def _get_fallback_rates(self) -> Dict[str, float]:
        """
        Statische Fallback-Wechselkurse
        """
        return {
            'USD': 0.847,   # 1 USD = 0.847 EUR
            'GBP': 1.168,   # 1 GBP = 1.168 EUR
            'CHF': 1.06,    # 1 CHF = 1.06 EUR
            'JPY': 0.0056,  # 1 JPY = 0.0056 EUR
            'CAD': 0.63,    # 1 CAD = 0.63 EUR
            'AUD': 0.61,    # 1 AUD = 0.61 EUR
            'CNY': 0.117,   # 1 CNY = 0.117 EUR
            'HKD': 0.108,   # 1 HKD = 0.108 EUR
            'SEK': 0.088,   # 1 SEK = 0.088 EUR
            'NOK': 0.086,   # 1 NOK = 0.086 EUR
            'DKK': 0.134,   # 1 DKK = 0.134 EUR
            'PLN': 0.23,    # 1 PLN = 0.23 EUR
            'CZK': 0.039,   # 1 CZK = 0.039 EUR
        }
    
    def _save_to_cache(self, rates: Dict[str, float]):
        """
        Speichert Wechselkurse im Cache
        """
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'rates': rates
            }
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Cache-Speicherung fehlgeschlagen: {str(e)}")
