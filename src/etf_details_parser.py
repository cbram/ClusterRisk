"""
ETF Details Parser
Parst die neuen ETF-Detail-CSV-Dateien mit Metadata, Holdings, Sektor-, Länder- und Währungsverteilung
"""

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
                'region': metadata.get('Region'),
                'currency': metadata.get('Currency'),
                'ter': metadata.get('TER'),
                'last_updated': last_updated,
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
        """Teilt CSV-Inhalt in Sections auf"""
        sections = {}
        current_section = None
        current_content = []
        
        for line in content.split('\n'):
            line = line.strip()
            
            if line.startswith('# ETF Metadata'):
                current_section = 'metadata'
                current_content = []
            elif line.startswith('# Country Allocation'):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'country'
                current_content = []
            elif line.startswith('# Sector Allocation'):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'sector'
                current_content = []
            elif line.startswith('# Currency Allocation'):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'currency'
                current_content = []
            elif line.startswith('# Top Holdings'):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = 'holdings'
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
        
        lines = content.split('\n')
        if len(lines) < 2:
            return []
        
        # Header überspringen
        data = []
        for line in lines[1:]:
            if ',' in line:
                parts = line.split(',')
                if len(parts) >= 2:
                    name = parts[0].strip()
                    try:
                        weight = float(parts[1].strip())
                        data.append({'name': name, 'weight': weight / 100.0})  # In Dezimal umwandeln
                    except ValueError:
                        continue
        
        return data
    
    def _parse_holdings(self, content: str) -> list:
        """Parst Holdings-Section"""
        if not content:
            return []
        
        lines = content.split('\n')
        if len(lines) < 2:
            return []
        
        # Parse as CSV
        holdings = []
        header = lines[0].split(',')
        
        for line in lines[1:]:
            if not line.strip():
                continue
            
            parts = line.split(',')
            if len(parts) >= 5:
                try:
                    holding = {
                        'name': parts[0].strip(),
                        'weight': float(parts[1].strip()) / 100.0,  # In Dezimal umwandeln
                        'currency': parts[2].strip(),
                        'sector': parts[3].strip(),
                        'country': parts[4].strip()
                    }
                    if len(parts) >= 6:
                        holding['isin'] = parts[5].strip()
                    holdings.append(holding)
                except (ValueError, IndexError) as e:
                    print(f"⚠️  Fehler beim Parsen von Holding: {line} - {e}")
                    continue
        
        return holdings
    
    def _check_data_freshness(self, ticker: str, etf_name: str, last_updated_str: str):
        """
        Prüft ob die ETF-Daten aktuell sind (< 90 Tage alt)
        
        Args:
            ticker: Ticker-Symbol des ETFs
            etf_name: Name des ETFs
            last_updated_str: Datum-String im Format YYYY-MM-DD
        """
        try:
            last_updated = datetime.strptime(last_updated_str, '%Y-%m-%d')
            today = datetime.now()
            days_old = (today - last_updated).days
            
            # Warnung wenn älter als 90 Tage (ein Quartal)
            if days_old > 90:
                diagnostics = get_diagnostics()
                diagnostics.add_warning(
                    'ETF-Daten',
                    f'Veraltete ETF-Zusammensetzung: {etf_name} ({ticker})',
                    f'Letzte Aktualisierung: {last_updated_str} ({days_old} Tage alt). '
                    f'Empfehlung: Aktualisiere data/etf_details/{ticker}.csv mit aktuellen Daten.'
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
