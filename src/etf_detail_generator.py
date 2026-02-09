"""
ETF Detail Generator
Generiert ETF-Detail-CSV-Dateien automatisch durch Scraping von justETF.com
"""

import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import re
import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from .diagnostics import get_diagnostics


# Mapping von Ländern zu Währungen
COUNTRY_TO_CURRENCY = {
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


def _derive_currency_allocation(country_allocation: List[Dict]) -> List[Dict]:
    """
    Leitet Währungs-Allokation aus der Länder-Allokation ab.
    Eurozone-Länder werden zu EUR zusammengefasst.
    
    Args:
        country_allocation: Liste von {'name': 'US', 'weight': 70.8}
        
    Returns:
        Liste von {'name': 'USD', 'weight': 72.5}
    """
    currency_weights = {}
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
            # Versuche Teilstring-Matching
            matched = False
            for key, cur in COUNTRY_TO_CURRENCY.items():
                if key.lower() in country.lower() or country.lower() in key.lower():
                    currency_weights[cur] = currency_weights.get(cur, 0.0) + weight
                    matched = True
                    break
            if not matched:
                unmapped_weight += weight
    
    # Sortiere nach Gewicht (absteigend)
    result = [{'name': cur, 'weight': w} for cur, w in 
              sorted(currency_weights.items(), key=lambda x: x[1], reverse=True)]
    
    # "Other" für nicht zugeordnete Währungen
    if unmapped_weight > 0.1:  # Nur wenn > 0.1%
        result.append({'name': 'Other', 'weight': unmapped_weight})
    
    return result


class JustETFScraper:
    """Scraper für justETF.com mit Session-basiertem AJAX-Support"""
    
    BASE_URL = "https://www.justetf.com/en/etf-profile.html"
    
    USER_AGENT = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
        })
    
    def fetch_etf_data(self, isin: str) -> Optional[Dict]:
        """
        Holt vollständige ETF-Daten von justETF.
        
        Args:
            isin: ISIN des ETFs
            
        Returns:
            Dict mit name, metadata, holdings, countries, sectors oder None
        """
        try:
            # Hauptseite laden (setzt Cookies für AJAX-Calls)
            url = f"{self.BASE_URL}?isin={isin}"
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # ETF-Name
            name = self._parse_name(soup)
            if not name or name == "Unknown":
                print(f"  justETF: ETF nicht gefunden für ISIN {isin}")
                return None
            
            print(f"  justETF: ETF gefunden: {name}")
            
            # Metadaten parsen
            metadata = self._parse_metadata(soup)
            
            # Holdings parsen (von Hauptseite)
            holdings = self._parse_holdings(soup)
            
            # Länder-Allokation parsen (Hauptseite)
            countries = self._parse_countries(soup)
            
            # Sektoren-Allokation parsen (Hauptseite)
            sectors = self._parse_sectors(soup)
            
            # AJAX-Expansion für vollständige Listen
            expanded_countries = self._expand_countries_ajax(isin)
            if expanded_countries:
                countries = expanded_countries
            
            expanded_sectors = self._expand_sectors_ajax(isin)
            if expanded_sectors:
                sectors = expanded_sectors
            
            # Holdings-Datum
            holdings_date = self._parse_holdings_date(soup)
            
            return {
                'name': name,
                'isin': isin,
                'metadata': metadata,
                'holdings': holdings,
                'countries': countries,
                'sectors': sectors,
                'holdings_date': holdings_date,
                'source': 'justETF',
                'fetch_date': datetime.now().isoformat()
            }
            
        except requests.exceptions.RequestException as e:
            print(f"  justETF: Netzwerkfehler für {isin}: {e}")
            return None
        except Exception as e:
            print(f"  justETF: Fehler beim Parsen für {isin}: {e}")
            return None
    
    def _parse_name(self, soup: BeautifulSoup) -> str:
        """Parst den ETF-Namen"""
        # Versuche data-testid zuerst
        title = soup.find('h1')
        if title:
            return title.get_text(strip=True)
        
        # Fallback: h1 mit Klasse
        title = soup.find('h1', class_='h2')
        if title:
            return title.get_text(strip=True)
        
        return "Unknown"
    
    def _parse_metadata(self, soup: BeautifulSoup) -> Dict:
        """Parst ETF-Metadaten (TER, Fondswährung, Replikation etc.)"""
        metadata = {}
        
        # Suche die Info-Tabelle
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    
                    if 'ter' in key or 'total expense' in key or 'gesamtkosten' in key:
                        # TER extrahieren: "0.20%" -> "0.20"
                        match = re.search(r'([\d.,]+)\s*%', value)
                        if match:
                            metadata['ter'] = match.group(1).replace(',', '.')
                    elif 'fund currency' in key or 'fondswährung' in key:
                        metadata['currency'] = value
                    elif 'replication' in key or 'replikation' in key:
                        metadata['replication'] = value
                    elif 'fund size' in key or 'fondsgröße' in key:
                        metadata['fund_size'] = value
                    elif 'distribution' in key or 'ausschüttung' in key or 'ertragsverwendung' in key:
                        metadata['distribution'] = value
                    elif 'fund domicile' in key or 'fondsdomizil' in key:
                        metadata['domicile'] = value
                    elif 'index' in key and 'index' == key.strip():
                        metadata['index'] = value
        
        return metadata
    
    def _parse_holdings(self, soup: BeautifulSoup) -> List[Dict]:
        """Parst Top Holdings"""
        holdings = []
        
        # Versuche data-testid Selektoren
        rows = soup.find_all('tr', attrs={'data-testid': 'etf-holdings_top-holdings_row'})
        
        if rows:
            for row in rows:
                name_elem = row.find(attrs={'data-testid': re.compile(r'.*top-holdings.*name')})
                weight_elem = row.find(attrs={'data-testid': re.compile(r'.*top-holdings.*percentage')})
                
                if name_elem and weight_elem:
                    name = name_elem.get_text(strip=True)
                    weight_text = weight_elem.get_text(strip=True)
                    weight = self._parse_percentage(weight_text)
                    
                    # ISIN aus Link extrahieren
                    isin = None
                    link = name_elem.find('a') if name_elem.name != 'a' else name_elem
                    if link is None:
                        link = row.find('a', attrs={'data-testid': re.compile(r'.*top-holdings.*link')})
                    if link and link.get('href'):
                        href = link.get('href', '')
                        # Format: /stock-profiles/IE00B4L5Y983
                        isin_match = re.search(r'/stock-profiles/([A-Z0-9]{12})', href)
                        if isin_match:
                            isin = isin_match.group(1)
                    
                    if weight is not None:
                        holding = {'name': name, 'weight': weight}
                        if isin:
                            holding['isin'] = isin
                        holdings.append(holding)
        
        # Fallback: Generisches Tabellen-Parsing
        if not holdings:
            holdings = self._parse_holdings_fallback(soup)
        
        return holdings
    
    def _parse_holdings_fallback(self, soup: BeautifulSoup) -> List[Dict]:
        """Fallback Holdings-Parsing über generische Tabellen-Suche"""
        holdings = []
        
        # Suche nach Holdings-Tabelle (häufig die erste table in einem Holdings-Abschnitt)
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            if len(rows) < 2:
                continue
            
            # Prüfe ob das eine Holdings-Tabelle sein könnte
            header = rows[0].get_text(strip=True).lower()
            if 'holding' in header or 'position' in header or 'name' in header:
                for row in rows[1:]:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        name = cols[0].get_text(strip=True)
                        weight = self._parse_percentage(cols[1].get_text(strip=True))
                        if weight is not None and name:
                            holdings.append({'name': name, 'weight': weight})
                
                if holdings:
                    break
        
        return holdings
    
    def _parse_countries(self, soup: BeautifulSoup) -> List[Dict]:
        """Parst Länder-Allokation"""
        countries = []
        
        rows = soup.find_all('tr', attrs={'data-testid': 'etf-holdings_countries_row'})
        
        if rows:
            for row in rows:
                name_elem = row.find(attrs={'data-testid': re.compile(r'.*countries.*name')})
                weight_elem = row.find(attrs={'data-testid': re.compile(r'.*countries.*percentage')})
                
                if name_elem and weight_elem:
                    name = name_elem.get_text(strip=True)
                    weight = self._parse_percentage(weight_elem.get_text(strip=True))
                    
                    if weight is not None:
                        countries.append({'name': name, 'weight': weight})
        
        return countries
    
    def _parse_sectors(self, soup: BeautifulSoup) -> List[Dict]:
        """Parst Sektor-Allokation"""
        sectors = []
        
        rows = soup.find_all('tr', attrs={'data-testid': 'etf-holdings_sectors_row'})
        
        if rows:
            for row in rows:
                name_elem = row.find(attrs={'data-testid': re.compile(r'.*sectors.*name')})
                weight_elem = row.find(attrs={'data-testid': re.compile(r'.*sectors.*percentage')})
                
                if name_elem and weight_elem:
                    name = name_elem.get_text(strip=True)
                    weight = self._parse_percentage(weight_elem.get_text(strip=True))
                    
                    if weight is not None:
                        sectors.append({'name': name, 'weight': weight})
        
        return sectors
    
    def _parse_holdings_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Parst das Holdings-Referenzdatum"""
        date_elem = soup.find(attrs={'data-testid': 'tl_etf-holdings_reference-date'})
        if date_elem:
            return date_elem.get_text(strip=True)
        return None
    
    def _expand_countries_ajax(self, isin: str) -> Optional[List[Dict]]:
        """
        Holt vollständige Länderliste via Wicket AJAX-Call.
        justETF zeigt standardmäßig nur Top 5 Länder an.
        """
        try:
            url = (
                f"{self.BASE_URL}?"
                f"0-1.0-holdingsSection-countries-loadMoreCountries"
                f"&isin={isin}&_wicket=1"
            )
            
            headers = {
                'X-Requested-With': 'XMLHttpRequest',
                'Wicket-Ajax': 'true',
                'Wicket-Ajax-BaseURL': f'en/etf-profile.html?isin={isin}',
                'Accept': 'application/xml, text/xml, */*; q=0.01',
                'Referer': f'{self.BASE_URL}?isin={isin}',
            }
            
            response = self.session.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return None
            
            # Wicket AJAX Response ist XML mit CDATA
            countries = self._parse_wicket_ajax_table(response.text, 'countries')
            
            if countries:
                print(f"  justETF AJAX: {len(countries)} Länder geladen")
                return countries
                
        except Exception as e:
            print(f"  justETF AJAX Countries fehlgeschlagen: {e}")
        
        return None
    
    def _expand_sectors_ajax(self, isin: str) -> Optional[List[Dict]]:
        """
        Holt vollständige Sektorenliste via Wicket AJAX-Call.
        """
        try:
            url = (
                f"{self.BASE_URL}?"
                f"0-1.0-holdingsSection-sectors-loadMoreSectors"
                f"&isin={isin}&_wicket=1"
            )
            
            headers = {
                'X-Requested-With': 'XMLHttpRequest',
                'Wicket-Ajax': 'true',
                'Wicket-Ajax-BaseURL': f'en/etf-profile.html?isin={isin}',
                'Accept': 'application/xml, text/xml, */*; q=0.01',
                'Referer': f'{self.BASE_URL}?isin={isin}',
            }
            
            response = self.session.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return None
            
            sectors = self._parse_wicket_ajax_table(response.text, 'sectors')
            
            if sectors:
                print(f"  justETF AJAX: {len(sectors)} Sektoren geladen")
                return sectors
                
        except Exception as e:
            print(f"  justETF AJAX Sectors fehlgeschlagen: {e}")
        
        return None
    
    def _parse_wicket_ajax_table(self, xml_text: str, data_type: str) -> Optional[List[Dict]]:
        """
        Parst Wicket AJAX XML-Response und extrahiert Tabellendaten.
        
        Die Response enthält CDATA-Abschnitte mit HTML-Tabellen.
        """
        try:
            # Versuche XML zu parsen
            root = ET.fromstring(xml_text)
            
            items = []
            
            # Suche CDATA in component-Elementen
            for component in root.iter('component'):
                cdata = component.text
                if not cdata:
                    continue
                
                # Parse HTML aus CDATA
                inner_soup = BeautifulSoup(cdata, 'html.parser')
                
                # Suche Tabellenzeilen
                rows = inner_soup.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        name = cells[0].get_text(strip=True)
                        weight = self._parse_percentage(cells[1].get_text(strip=True))
                        
                        if name and weight is not None:
                            items.append({'name': name, 'weight': weight})
            
            # Auch data-testid basiertes Parsing versuchen
            if not items:
                inner_soup = BeautifulSoup(xml_text, 'html.parser')
                testid_key = f'etf-holdings_{data_type}_row'
                rows = inner_soup.find_all('tr', attrs={'data-testid': testid_key})
                
                for row in rows:
                    name_elem = row.find(attrs={'data-testid': re.compile(f'.*{data_type}.*name')})
                    weight_elem = row.find(attrs={'data-testid': re.compile(f'.*{data_type}.*percentage')})
                    
                    if name_elem and weight_elem:
                        name = name_elem.get_text(strip=True)
                        weight = self._parse_percentage(weight_elem.get_text(strip=True))
                        
                        if weight is not None:
                            items.append({'name': name, 'weight': weight})
            
            return items if items else None
            
        except ET.ParseError:
            # Fallback: Versuche als HTML zu parsen
            try:
                soup = BeautifulSoup(xml_text, 'html.parser')
                items = []
                
                for row in soup.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        name = cells[0].get_text(strip=True)
                        weight = self._parse_percentage(cells[1].get_text(strip=True))
                        
                        if name and weight is not None:
                            items.append({'name': name, 'weight': weight})
                
                return items if items else None
            except Exception:
                return None
    
    @staticmethod
    def _parse_percentage(text: str) -> Optional[float]:
        """Parst einen Prozentstring in eine Fließkommazahl"""
        if not text:
            return None
        
        # Verschiedene Formate: "24.5%", "24,5 %", "24.5 %"
        match = re.search(r'([\d.,]+)\s*%?', text.strip())
        if match:
            try:
                value = match.group(1).replace(',', '.')
                return float(value)
            except ValueError:
                return None
        return None


def generate_etf_detail_file(
    isin: str, 
    ticker: str,
    etf_type: str = 'Stock',
    region: str = '',
    proxy_isin: str = '',
    output_dir: str = 'data/etf_details'
) -> Tuple[bool, str, Optional[Dict]]:
    """
    Generiert eine ETF-Detail-CSV-Datei durch Scraping von justETF.
    
    Bei Swap-ETFs kann eine Proxy-ISIN eines physisch replizierenden ETFs
    auf denselben Index angegeben werden. Die Allokations- und Holdings-Daten
    werden dann vom Proxy gescrapet, die Metadaten bleiben die des eigentlichen ETFs.
    
    Args:
        isin: ISIN des ETFs
        ticker: Ticker-Symbol (wird als Dateiname verwendet)
        etf_type: ETF-Typ (Stock, Bond, Money Market, Commodity)
        region: Region (z.B. "World", "USA", "Europe")
        proxy_isin: Proxy-ISIN für Swap-ETFs (physischer ETF auf denselben Index)
        output_dir: Ausgabeverzeichnis
        
    Returns:
        Tuple von (Erfolg, Statusmeldung, gescrapte Daten)
    """
    diagnostics = get_diagnostics()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    filepath = output_path / f"{ticker}.csv"
    
    print(f"\n{'='*60}")
    print(f"ETF-Detail-Generator: {isin} → {ticker}.csv")
    if proxy_isin:
        print(f"  Proxy-ISIN: {proxy_isin}")
    print(f"{'='*60}")
    
    scraper = JustETFScraper()
    
    # 1. Metadaten vom eigentlichen ETF scrapen
    print(f"Scrape justETF für ISIN {isin} (Metadaten)...")
    own_data = scraper.fetch_etf_data(isin)
    
    if not own_data:
        msg = f"Keine Daten von justETF für ISIN {isin} erhalten"
        diagnostics.add_warning('ETF-Daten', msg, 
            'Mögliche Ursachen: ISIN ungültig oder justETF nicht erreichbar.')
        return False, msg, None
    
    etf_name = own_data.get('name', 'Unknown')
    own_metadata = own_data.get('metadata', {})
    currency = own_metadata.get('currency', 'USD')
    ter = own_metadata.get('ter', '')
    index_name = own_metadata.get('index', '')
    
    # 2. Bestimme Datenquelle für Allokationen/Holdings
    scrape_isin = isin
    source = 'justETF (auto-generated)'
    used_proxy = False
    
    if proxy_isin:
        # Proxy explizit angegeben → direkt verwenden
        scrape_isin = proxy_isin
        source = f'justETF (via Proxy: {proxy_isin})'
        used_proxy = True
        print(f"Verwende Proxy-ISIN {proxy_isin} für Allokationen...")
    else:
        # Kein Proxy → prüfe ob die eigenen Daten brauchbar sind
        own_holdings = own_data.get('holdings', [])
        own_countries = own_data.get('countries', [])
        own_sectors = own_data.get('sectors', [])
        quality = _check_data_quality(own_holdings, own_countries, own_sectors, etf_name, isin)
        
        if not quality['is_unusable']:
            # Eigene Daten sind gut → direkt verwenden
            pass
        else:
            # Daten nicht brauchbar und kein Proxy → abbrechen
            msg = quality['reason']
            hint = (
                f'Tipp: Setze eine Proxy-ISIN eines physisch replizierenden ETFs '
                f'auf denselben Index (z.B. in der Sidebar unter "Neuen ETF hinzufügen").'
            )
            diagnostics.add_warning('ETF-Daten', msg, hint)
            
            if filepath.exists():
                msg += f'\n  Bestehende Datei {filepath} wurde NICHT überschrieben.'
            
            return False, msg, own_data
    
    # 3. Daten von der Scrape-ISIN holen (eigene oder Proxy)
    if used_proxy:
        print(f"Scrape justETF für Proxy-ISIN {scrape_isin} (Allokationen/Holdings)...")
        proxy_data = scraper.fetch_etf_data(scrape_isin)
        
        if not proxy_data:
            msg = f"Keine Daten von justETF für Proxy-ISIN {scrape_isin} erhalten"
            diagnostics.add_warning('ETF-Daten', msg,
                'Die Proxy-ISIN konnte nicht aufgelöst werden. Prüfe die ISIN.')
            return False, msg, own_data
        
        holdings = proxy_data.get('holdings', [])
        countries = proxy_data.get('countries', [])
        sectors = proxy_data.get('sectors', [])
        
        # Qualitätsprüfung der Proxy-Daten
        quality = _check_data_quality(holdings, countries, sectors, etf_name, scrape_isin)
        if quality['is_unusable']:
            msg = f"Proxy-ISIN {scrape_isin} liefert ebenfalls keine brauchbaren Daten: {quality['reason']}"
            diagnostics.add_warning('ETF-Daten', msg,
                'Wähle einen anderen Proxy-ETF (physisch replizierend, gleicher Index).')
            return False, msg, own_data
    else:
        holdings = own_data.get('holdings', [])
        countries = own_data.get('countries', [])
        sectors = own_data.get('sectors', [])
    
    # Warnungen für teilweise fehlende Daten
    quality = _check_data_quality(holdings, countries, sectors, etf_name, scrape_isin)
    for warning in quality.get('warnings', []):
        diagnostics.add_warning('ETF-Daten', warning,
            f'Bitte prüfe/ergänze die generierte Datei data/etf_details/{ticker}.csv manuell.')
    
    # 4. Währungs-Allokation aus Ländern ableiten
    currency_allocation = _derive_currency_allocation(countries)
    
    # 5. "Other Holdings" berechnen
    total_holdings_weight = sum(h['weight'] for h in holdings)
    other_weight = max(0, 100.0 - total_holdings_weight)
    
    # 6. Holdings mit Sektor/Land/Währung anreichern
    enriched_holdings = _enrich_holdings(holdings, countries)
    
    # 7. CSV-Datei schreiben
    _write_etf_detail_csv(
        filepath=filepath,
        isin=isin,
        name=etf_name,
        ticker=ticker,
        etf_type=etf_type,
        region=region,
        currency=currency,
        ter=ter,
        index_name=index_name,
        countries=countries,
        sectors=sectors,
        currency_allocation=currency_allocation,
        holdings=enriched_holdings,
        other_weight=other_weight,
        source=source,
        proxy_isin=proxy_isin
    )
    
    # 8. ISIN-Ticker-Map aktualisieren
    _update_isin_ticker_map(isin, ticker, etf_name)
    
    proxy_info = f" (via Proxy {proxy_isin})" if proxy_isin else ""
    msg = (
        f"ETF-Detail-Datei generiert: {filepath}{proxy_info}\n"
        f"  Name: {etf_name}\n"
        f"  Holdings: {len(holdings)}\n"
        f"  Länder: {len(countries)}\n"
        f"  Sektoren: {len(sectors)}\n"
        f"  Währungen (abgeleitet): {len(currency_allocation)}"
    )
    print(msg)
    
    return True, msg, own_data


def _check_data_quality(
    holdings: List[Dict],
    countries: List[Dict],
    sectors: List[Dict],
    etf_name: str,
    isin: str
) -> Dict:
    """
    Prüft die Qualität der gescrapten Daten.
    
    Erkennt typische Probleme:
    - Swap-ETFs: Holdings sind andere ETFs statt Aktien
    - Fehlende Allokationen: Keine Länder/Sektoren
    - Zu wenige Daten
    
    Returns:
        Dict mit: is_unusable (bool), reason (str), warnings (List[str])
    """
    warnings = []
    
    # Keywords die auf ETFs/Fonds in den Holdings hindeuten
    etf_keywords = [
        'etf', 'ucits', 'ishares', 'vanguard', 'xtrackers', 'amundi',
        'spdr', 'invesco', 'lyxor', 'dws', 'fund', 'fonds',
    ]
    
    # Prüfe ob Holdings andere ETFs/Fonds sind (typisch für Swap-ETFs)
    if holdings:
        etf_holdings_count = 0
        for h in holdings:
            name_lower = h['name'].lower()
            if any(kw in name_lower for kw in etf_keywords):
                etf_holdings_count += 1
        
        etf_ratio = etf_holdings_count / len(holdings)
        
        if etf_ratio > 0.5:
            return {
                'is_unusable': True,
                'reason': (
                    f'Swap-ETF erkannt: {etf_holdings_count} von {len(holdings)} Holdings '
                    f'sind andere ETFs/Fonds. justETF zeigt für Swap-ETFs keine echten '
                    f'Aktien-Holdings an.'
                ),
                'warnings': []
            }
    
    # Keine Holdings UND keine Allokationen = komplett unbrauchbar
    if not holdings and not countries and not sectors:
        return {
            'is_unusable': True,
            'reason': f'Keine verwertbaren Daten für {etf_name} ({isin}) erhalten.',
            'warnings': []
        }
    
    # Warnungen für teilweise fehlende Daten
    if not countries:
        warnings.append(f'Keine Länder-Allokation für {etf_name} ({isin}) gefunden.')
    
    if not sectors:
        warnings.append(f'Keine Sektor-Allokation für {etf_name} ({isin}) gefunden.')
    
    if not holdings:
        warnings.append(
            f'Keine Holdings für {etf_name} ({isin}) gefunden. '
            f'Möglicherweise ein synthetischer ETF.'
        )
    
    return {
        'is_unusable': False,
        'reason': '',
        'warnings': warnings
    }


def _enrich_holdings(holdings: List[Dict], countries: List[Dict]) -> List[Dict]:
    """
    Reichert Holdings mit Währung und Land an, basierend auf ISIN.
    
    Args:
        holdings: Liste der gescrapten Holdings
        countries: Länder-Allokation (für Kontext)
        
    Returns:
        Angereicherte Holdings-Liste
    """
    enriched = []
    
    for holding in holdings:
        entry = {
            'name': holding['name'],
            'weight': holding['weight'],
            'currency': 'USD',  # Default
            'sector': 'Unknown',
            'country': '',
        }
        
        # ISIN-basierte Anreicherung
        isin = holding.get('isin', '')
        if isin and len(isin) >= 2:
            country_code = isin[:2]
            entry['country'] = country_code
            entry['currency'] = COUNTRY_TO_CURRENCY.get(country_code, 'USD')
        
        enriched.append(entry)
    
    return enriched


def _write_etf_detail_csv(
    filepath: Path,
    isin: str,
    name: str,
    ticker: str,
    etf_type: str,
    region: str,
    currency: str,
    ter: str,
    countries: List[Dict],
    sectors: List[Dict],
    currency_allocation: List[Dict],
    holdings: List[Dict],
    other_weight: float,
    source: str = 'justETF (auto-generated)',
    proxy_isin: str = '',
    index_name: str = ''
):
    """Schreibt die ETF-Detail-CSV-Datei im korrekten Format"""
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    lines = []
    
    # Metadata
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
    lines.append(f'Source,{source}')
    lines.append('')
    
    # Country Allocation
    lines.append('# Country Allocation (%)')
    lines.append('Country,Weight')
    for c in countries:
        lines.append(f'{c["name"]},{c["weight"]:.1f}')
    lines.append('')
    
    # Sector Allocation
    lines.append('# Sector Allocation (%)')
    lines.append('Sector,Weight')
    for s in sectors:
        lines.append(f'{s["name"]},{s["weight"]:.1f}')
    lines.append('')
    
    # Currency Allocation (abgeleitet)
    lines.append('# Currency Allocation (%) - auto-derived from countries')
    lines.append('Currency,Weight')
    for cur in currency_allocation:
        lines.append(f'{cur["name"]},{cur["weight"]:.1f}')
    lines.append('')
    
    # Top Holdings (csv.writer für korrekte Komma-Behandlung in Firmennamen)
    lines.append('# Top Holdings')
    lines.append('')  # Platzhalter, wird durch csv.writer ersetzt
    
    # Schreibe Datei: Erst die Zeilen bis vor Holdings, dann Holdings via csv.writer
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        # Alles bis zum Holdings-Platzhalter schreiben
        f.write('\n'.join(lines[:-1]))
        f.write('\n')
        
        # Holdings als korrekte CSV mit Quoting schreiben
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['Name', 'Weight', 'Currency', 'Sector', 'Country', 'ISIN'])
        
        for h in holdings:
            writer.writerow([
                h['name'],
                f'{h["weight"]:.2f}',
                h['currency'],
                h['sector'],
                h['country'],
                h.get('isin', '')
            ])
        
        # Other Holdings Eintrag
        if other_weight > 0.1:
            writer.writerow(['Other Holdings', f'{other_weight:.2f}', 'Mixed', 'Diversified', 'Mixed', ''])
        
        f.write('\n')
    
    print(f"  Datei geschrieben: {filepath}")


def _update_isin_ticker_map(isin: str, ticker: str, name: str):
    """Aktualisiert die ISIN-Ticker-Map (fügt hinzu oder aktualisiert)"""
    map_path = Path('data/etf_isin_ticker_map.csv')
    
    # Bestehende Einträge laden
    existing_entries = []
    isin_exists = False
    
    if map_path.exists():
        with open(map_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    if row[0] == 'ISIN':  # Header
                        continue
                    if row[0] == isin:
                        # Existierenden Eintrag aktualisieren
                        existing_entries.append([isin, ticker, name])
                        isin_exists = True
                    else:
                        existing_entries.append(row)
    
    # Neuen Eintrag hinzufügen wenn nicht vorhanden
    if not isin_exists:
        existing_entries.append([isin, ticker, name])
    
    # Datei schreiben
    with open(map_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ISIN', 'Ticker', 'Name'])
        writer.writerows(existing_entries)
    
    print(f"  ISIN-Ticker-Map aktualisiert: {isin} → {ticker}")


def preview_etf_data(isin: str) -> Optional[Dict]:
    """
    Holt ETF-Daten von justETF ohne Datei zu schreiben (Vorschau).
    
    Args:
        isin: ISIN des ETFs
        
    Returns:
        Dict mit gescrapten Daten oder None
    """
    scraper = JustETFScraper()
    data = scraper.fetch_etf_data(isin)
    
    if data and data.get('countries'):
        data['currency_allocation_derived'] = _derive_currency_allocation(data['countries'])
    
    return data


def get_etf_detail_status(etf_details_dir: str = 'data/etf_details') -> List[Dict]:
    """
    Listet alle vorhandenen ETF-Detail-Dateien mit ihrem Aktualitätsstatus.
    
    Returns:
        Liste von Dicts mit: ticker, isin, name, type, last_updated, days_old, is_stale
    """
    details_path = Path(etf_details_dir)
    if not details_path.exists():
        return []
    
    # ISIN-Ticker-Map laden für Reverse-Lookup
    isin_map = _load_isin_ticker_map()
    
    results = []
    
    for csv_file in sorted(details_path.glob('*.csv')):
        ticker = csv_file.stem
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Einfaches Metadata-Parsing – nur im Metadata-Bereich lesen
            # (stoppt bei der nächsten Section, um z.B. "Name,Weight,..." im Holdings-Header zu ignorieren)
            isin = ''
            name = ''
            etf_type = 'Stock'
            index_name = ''
            region = ''
            last_updated = ''
            source = ''
            proxy_isin = ''
            in_metadata = True  # Beginnt im Metadata-Bereich
            
            for line in content.split('\n'):
                line = line.strip()
                
                # Section-Header erkennen (beendet Metadata-Bereich)
                if line in ('COUNTRY_ALLOCATION', 'SECTOR_ALLOCATION', 'CURRENCY_ALLOCATION', 'TOP_HOLDINGS'):
                    in_metadata = False
                elif line.startswith('# Country Allocation') or line.startswith('# Sector Allocation') or \
                     line.startswith('# Currency Allocation') or line.startswith('# Top Holdings'):
                    in_metadata = False
                
                if not in_metadata:
                    continue
                
                if line.startswith('ISIN,'):
                    isin = line.split(',', 1)[1].strip()
                elif line.startswith('Name,'):
                    name = line.split(',', 1)[1].strip()
                elif line.startswith('Type,'):
                    etf_type = line.split(',', 1)[1].strip()
                elif line.startswith('Index,'):
                    index_name = line.split(',', 1)[1].strip()
                elif line.startswith('Region,'):
                    region = line.split(',', 1)[1].strip()
                elif line.startswith('Last Updated,'):
                    last_updated = line.split(',', 1)[1].strip()
                elif line.startswith('Source,'):
                    source = line.split(',', 1)[1].strip()
                elif line.startswith('Proxy ISIN,'):
                    proxy_isin = line.split(',', 1)[1].strip()
            
            # Source bestimmen: auto, proxy, manual
            if proxy_isin:
                data_source = 'proxy'
            elif source and ('auto' in source.lower() or 'justetf' in source.lower()):
                data_source = 'auto'
            else:
                data_source = 'manual'
            
            # Alter berechnen
            days_old = None
            is_stale = False
            
            if last_updated:
                try:
                    updated_date = datetime.strptime(last_updated, '%Y-%m-%d')
                    days_old = (datetime.now() - updated_date).days
                    is_stale = days_old > 30
                except ValueError:
                    pass
            
            results.append({
                'ticker': ticker,
                'isin': isin,
                'name': name,
                'type': etf_type,
                'index': index_name,
                'region': region,
                'last_updated': last_updated,
                'days_old': days_old,
                'is_stale': is_stale,
                'source': source,
                'data_source': data_source,  # 'auto', 'proxy', 'manual'
                'proxy_isin': proxy_isin,
                'file': str(csv_file),
            })
            
        except Exception as e:
            results.append({
                'ticker': ticker,
                'isin': '',
                'name': f'Fehler: {e}',
                'type': '',
                'region': '',
                'last_updated': '',
                'days_old': None,
                'is_stale': True,
                'file': str(csv_file),
            })
    
    return results


def update_etf_detail_file(ticker: str, etf_details_dir: str = 'data/etf_details') -> Tuple[bool, str]:
    """
    Aktualisiert eine bestehende ETF-Detail-Datei durch erneutes Scraping.
    Übernimmt ISIN, Typ, Region und Proxy-ISIN aus der bestehenden Datei.
    
    Manuelle Dateien (Source ohne 'justETF'/'auto') werden NICHT aktualisiert.
    
    Args:
        ticker: Ticker-Symbol der zu aktualisierenden Datei
        etf_details_dir: Verzeichnis der Detail-Dateien
        
    Returns:
        Tuple von (Erfolg, Statusmeldung)
    """
    filepath = Path(etf_details_dir) / f"{ticker}.csv"
    
    if not filepath.exists():
        return False, f"Datei {filepath} existiert nicht"
    
    # Bestehende Metadaten lesen (nur aus Metadata-Bereich)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        isin = ''
        etf_type = 'Stock'
        region = ''
        source = ''
        proxy_isin = ''
        in_metadata = True
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Section-Header erkennen (beendet Metadata-Bereich)
            if line in ('COUNTRY_ALLOCATION', 'SECTOR_ALLOCATION', 'CURRENCY_ALLOCATION', 'TOP_HOLDINGS'):
                in_metadata = False
            elif line.startswith('# Country Allocation') or line.startswith('# Sector Allocation') or \
                 line.startswith('# Currency Allocation') or line.startswith('# Top Holdings'):
                in_metadata = False
            
            if not in_metadata:
                break
            
            if line.startswith('ISIN,'):
                isin = line.split(',', 1)[1].strip()
            elif line.startswith('Type,'):
                etf_type = line.split(',', 1)[1].strip()
            elif line.startswith('Region,'):
                region = line.split(',', 1)[1].strip()
            elif line.startswith('Source,'):
                source = line.split(',', 1)[1].strip()
            elif line.startswith('Proxy ISIN,'):
                proxy_isin = line.split(',', 1)[1].strip()
        
        if not isin:
            return False, f"Keine ISIN in {filepath} gefunden"
        
        # Manuelle Dateien nicht automatisch aktualisieren
        is_auto = source and ('auto' in source.lower() or 'justetf' in source.lower() or 'proxy' in source.lower())
        if not is_auto and source:
            return False, f"{ticker}: Manuell gepflegt (Source: {source}) – übersprungen"
        
    except Exception as e:
        return False, f"Fehler beim Lesen von {filepath}: {e}"
    
    # Neu generieren mit bestehenden Metadaten
    success, msg, _ = generate_etf_detail_file(
        isin=isin,
        ticker=ticker,
        etf_type=etf_type,
        region=region,
        proxy_isin=proxy_isin,
        output_dir=etf_details_dir
    )
    
    return success, msg


def batch_update_etf_details(
    etf_details_dir: str = 'data/etf_details',
    only_stale: bool = True,
    progress_callback=None
) -> List[Dict]:
    """
    Aktualisiert mehrere ETF-Detail-Dateien auf einmal.
    
    Args:
        etf_details_dir: Verzeichnis der Detail-Dateien
        only_stale: Nur veraltete Dateien (>30 Tage) aktualisieren
        progress_callback: Optional - Callback(current, total, ticker) für Fortschritt
        
    Returns:
        Liste von Ergebnis-Dicts: {ticker, success, message}
    """
    import time
    
    status_list = get_etf_detail_status(etf_details_dir)
    
    # Manuelle Dateien aus Batch-Update ausschließen
    auto_list = [s for s in status_list if s.get('data_source') != 'manual']
    
    if only_stale:
        to_update = [s for s in auto_list if s['is_stale']]
    else:
        to_update = auto_list
    
    if not to_update:
        return []
    
    results = []
    
    for i, etf_info in enumerate(to_update):
        ticker = etf_info['ticker']
        
        if progress_callback:
            progress_callback(i, len(to_update), ticker)
        
        success, msg = update_etf_detail_file(ticker, etf_details_dir)
        
        results.append({
            'ticker': ticker,
            'name': etf_info['name'],
            'success': success,
            'message': msg
        })
        
        # Rate Limiting: 2 Sekunden Pause zwischen Requests
        if i < len(to_update) - 1:
            time.sleep(2)
    
    return results


def _load_isin_ticker_map() -> Dict[str, str]:
    """Lädt die ISIN-Ticker-Map als Dict {ISIN: Ticker}"""
    map_path = Path('data/etf_isin_ticker_map.csv')
    result = {}
    
    if map_path.exists():
        with open(map_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2 and row[0] != 'ISIN':
                    result[row[0]] = row[1]
    
    return result
