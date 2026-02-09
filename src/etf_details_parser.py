"""
ETF Details Parser
Parst die neuen ETF-Detail-CSV-Dateien mit Metadata, Holdings, Sektor-, Länder- und Währungsverteilung
"""

import csv
import io
import pandas as pd
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta
from .diagnostics import get_diagnostics


class ETFDetailsParser:
    """Parser für ETF-Detail-CSV-Dateien"""
    
    def __init__(self, etf_details_dir: str = "data/etf_details"):
        self.etf_details_dir = Path(etf_details_dir)
        self.etf_details_dir.mkdir(parents=True, exist_ok=True)
    
    def parse_etf_file(self, ticker: str) -> Optional[Dict]:
        """
        Parst eine ETF-Detail-Datei
        
        Args:
            ticker: Ticker-Symbol des ETFs (z.B. "AEEM", "EUNL")
            
        Returns:
            Dictionary mit allen ETF-Details oder None
        """
        filepath = self.etf_details_dir / f"{ticker}.csv"
        
        if not filepath.exists():
            print(f"⚠️  ETF-Detail-Datei nicht gefunden: {filepath}")
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse Sections
            sections = self._split_sections(content)
            
            # Metadata
            metadata = self._parse_metadata(sections.get('metadata', ''))
            
            # Country Allocation
            country_allocation = self._parse_allocation(sections.get('country', ''))
            
            # Sector Allocation
            sector_allocation = self._parse_allocation(sections.get('sector', ''))
            
            # Currency Allocation (optional)
            currency_allocation = self._parse_allocation(sections.get('currency', ''))
            
            # Top Holdings
            holdings = self._parse_holdings(sections.get('holdings', ''))
            
            # Prüfe "Last Updated" Datum und warne wenn veraltet
            last_updated = metadata.get('Last Updated')
            if last_updated:
                self._check_data_freshness(ticker, metadata.get('Name'), last_updated)
            
            return {
                'ticker': ticker,
                'isin': metadata.get('ISIN'),
                'name': metadata.get('Name'),
                'type': metadata.get('Type', 'Stock'),
                'index': metadata.get('Index', ''),
                'region': metadata.get('Region'),
                'currency': metadata.get('Currency'),
                'ter': metadata.get('TER'),
                'last_updated': last_updated,
                'proxy_isin': metadata.get('Proxy ISIN', ''),
                'data_source': metadata.get('Source', ''),
                'country_allocation': country_allocation,
                'sector_allocation': sector_allocation,
                'currency_allocation': currency_allocation,
                'holdings': holdings,
                'source': 'etf_details_csv',
                'file': str(filepath)
            }
        
        except Exception as e:
            print(f"❌ Fehler beim Parsen von {filepath}: {e}")
            # Diagnose: Fehler beim Parsen
            diagnostics = get_diagnostics()
            diagnostics.add_error(
                'ETF-Daten',
                f'Fehler beim Parsen der ETF-Detail-Datei "{ticker}.csv"',
                f'Details: {str(e)}'
            )
            return None
    
    def _split_sections(self, content: str) -> Dict[str, str]:
        """
        Teilt CSV-Inhalt in Sections auf.
        
        Unterstützt zwei Formate:
        - Format A (mit #): "# ETF Metadata", "# Country Allocation (%)", etc.
        - Format B (ohne #): "METADATA", "COUNTRY_ALLOCATION", etc.
        """
        sections = {}
        current_section = None
        current_content = []
        
        # Section-Header Mapping: verschiedene Formate → interner Key
        section_patterns = {
            'metadata': ['# ETF Metadata', 'METADATA'],
            'country': ['# Country Allocation', 'COUNTRY_ALLOCATION'],
            'sector': ['# Sector Allocation', 'SECTOR_ALLOCATION'],
            'currency': ['# Currency Allocation', 'CURRENCY_ALLOCATION'],
            'holdings': ['# Top Holdings', 'TOP_HOLDINGS'],
        }
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Prüfe ob Zeile ein Section-Header ist
            matched_section = None
            for section_key, patterns in section_patterns.items():
                for pattern in patterns:
                    if line.startswith(pattern) or line == pattern:
                        matched_section = section_key
                        break
                if matched_section:
                    break
            
            if matched_section:
                # Vorherige Section speichern
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content)
                current_section = matched_section
                current_content = []
            elif line and not line.startswith('#'):
                current_content.append(line)
        
        # Letzte Section speichern
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _parse_metadata(self, content: str) -> Dict:
        """Parst Metadata-Section"""
        metadata = {}
        for line in content.split('\n'):
            if ',' in line:
                key, value = line.split(',', 1)
                metadata[key.strip()] = value.strip()
        return metadata
    
    def _parse_allocation(self, content: str) -> list:
        """Parst Allocation-Section (Country/Sector/Currency)"""
        if not content:
            return []
        
        # csv.reader verwenden für korrekte Komma-Behandlung
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        
        if len(rows) < 2:
            return []
        
        # Header überspringen
        data = []
        for row in rows[1:]:
            if len(row) >= 2:
                name = row[0].strip()
                try:
                    weight = float(row[1].strip())
                    data.append({'name': name, 'weight': weight / 100.0})  # In Dezimal umwandeln
                except ValueError:
                    continue
        
        return data
    
    def _parse_holdings(self, content: str) -> list:
        """
        Parst Holdings-Section.
        
        Verwendet csv.reader für korrekte Behandlung von Kommas in Firmennamen
        (z.B. "Amazon.com, Inc." oder "Alphabet, Inc. A").
        
        Unterstützt verschiedene Spaltenreihenfolgen anhand des Headers:
        - Format A: Name,Weight,Currency,Sector,Country,ISIN
        - Format B: Name,Weight,Currency,Sector,Industry,Country
        """
        if not content:
            return []
        
        lines = content.split('\n')
        if len(lines) < 2:
            return []
        
        # csv.reader verwenden für korrekte Komma-Behandlung (Quoting)
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        
        if len(rows) < 2:
            return []
        
        # Header parsen für dynamische Spaltenzuordnung
        header = [h.strip().lower() for h in rows[0]]
        
        # Spalten-Indizes bestimmen
        col_map = {}
        for i, col in enumerate(header):
            if col == 'name':
                col_map['name'] = i
            elif col == 'weight':
                col_map['weight'] = i
            elif col == 'currency':
                col_map['currency'] = i
            elif col == 'sector':
                col_map['sector'] = i
            elif col == 'country':
                col_map['country'] = i
            elif col == 'industry':
                col_map['industry'] = i
            elif col == 'isin':
                col_map['isin'] = i
        
        # Mindestens Name und Weight müssen vorhanden sein
        if 'name' not in col_map or 'weight' not in col_map:
            # Fallback: Feste Positionen (Kompatibilität)
            col_map = {'name': 0, 'weight': 1, 'currency': 2, 'sector': 3, 'country': 4}
            if len(header) >= 6:
                col_map['isin'] = 5
        
        holdings = []
        
        for parts in rows[1:]:
            if not parts or not any(p.strip() for p in parts):
                continue
            
            min_cols = max(col_map.values()) + 1
            
            if len(parts) >= min_cols:
                try:
                    holding = {
                        'name': parts[col_map['name']].strip(),
                        'weight': float(parts[col_map['weight']].strip()) / 100.0,  # In Dezimal umwandeln
                    }
                    
                    if 'currency' in col_map and col_map['currency'] < len(parts):
                        holding['currency'] = parts[col_map['currency']].strip()
                    
                    if 'sector' in col_map and col_map['sector'] < len(parts):
                        holding['sector'] = parts[col_map['sector']].strip()
                    
                    if 'country' in col_map and col_map['country'] < len(parts):
                        holding['country'] = parts[col_map['country']].strip()
                    
                    if 'industry' in col_map and col_map['industry'] < len(parts):
                        holding['industry'] = parts[col_map['industry']].strip()
                    
                    if 'isin' in col_map and col_map['isin'] < len(parts):
                        holding['isin'] = parts[col_map['isin']].strip()
                    
                    holdings.append(holding)
                except (ValueError, IndexError) as e:
                    print(f"⚠️  Fehler beim Parsen von Holding: {parts} - {e}")
                    continue
        
        return holdings
    
    def _check_data_freshness(self, ticker: str, etf_name: str, last_updated_str: str):
        """
        Prüft ob die ETF-Daten aktuell sind (< 30 Tage alt)
        
        justETF aktualisiert Daten monatlich, daher warnen wir nach 30 Tagen.
        
        Args:
            ticker: Ticker-Symbol des ETFs
            etf_name: Name des ETFs
            last_updated_str: Datum-String im Format YYYY-MM-DD
        """
        try:
            last_updated = datetime.strptime(last_updated_str, '%Y-%m-%d')
            today = datetime.now()
            days_old = (today - last_updated).days
            
            # Warnung wenn älter als 30 Tage (passend zu justETF monatlichem Update-Zyklus)
            if days_old > 30:
                diagnostics = get_diagnostics()
                diagnostics.add_warning(
                    'ETF-Daten',
                    f'Veraltete ETF-Zusammensetzung: {etf_name} ({ticker})',
                    f'Letzte Aktualisierung: {last_updated_str} ({days_old} Tage alt). '
                    f'Empfehlung: Aktualisiere über "🔄 ETF-Details" in der Sidebar oder manuell in data/etf_details/{ticker}.csv.'
                )
                print(f"⚠️  Veraltete ETF-Daten: {ticker} ({days_old} Tage alt)")
        except ValueError:
            # Ungültiges Datumsformat
            diagnostics = get_diagnostics()
            diagnostics.add_warning(
                'ETF-Daten',
                f'Ungültiges "Last Updated" Datum für {etf_name} ({ticker})',
                f'Datum: "{last_updated_str}". Erwartet: YYYY-MM-DD'
            )
    
    def get_etf_by_isin(self, isin: str, ticker_map: Dict[str, str]) -> Optional[Dict]:
        """
        Hole ETF-Details anhand der ISIN
        
        Args:
            isin: ISIN des ETFs
            ticker_map: Dictionary ISIN -> Ticker
            
        Returns:
            ETF-Details oder None
        """
        ticker = ticker_map.get(isin)
        if not ticker:
            return None
        
        return self.parse_etf_file(ticker)
    
    def list_available_etfs(self) -> list:
        """Liste alle verfügbaren ETF-Detail-Dateien"""
        etf_files = list(self.etf_details_dir.glob("*.csv"))
        return [f.stem for f in etf_files]  # Nur Dateinamen ohne .csv


# Globale Instanz
_parser = None

def get_etf_details_parser() -> ETFDetailsParser:
    """Hole globale Parser-Instanz (Singleton)"""
    global _parser
    if _parser is None:
        _parser = ETFDetailsParser()
    return _parser
