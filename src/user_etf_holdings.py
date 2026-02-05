"""
User ETF Holdings Manager
Ermöglicht benutzerdefinierte ETF-Holdings via CSV-Import
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Optional
import json


class UserETFHoldingsManager:
    """
    Verwaltet benutzerdefinierte ETF-Holdings
    """
    
    def __init__(self, user_holdings_file: str = "data/user_etf_holdings.csv"):
        self.user_holdings_file = Path(user_holdings_file)
        self.holdings_cache = {}
        self._load_user_holdings()
    
    def _load_user_holdings(self):
        """
        Lädt benutzerdefinierte ETF-Holdings aus CSV
        """
        if not self.user_holdings_file.exists():
            return
        
        try:
            df = pd.read_csv(self.user_holdings_file)
            
            # Erwartetes Format:
            # ISIN, ETF_Name, Holding_Name, Weight, Currency, Sector, Industry, Country (optional)
            
            if df.empty:
                return
            
            # Gruppiere nach ISIN
            for isin, group in df.groupby('ISIN'):
                holdings = []
                etf_name = group['ETF_Name'].iloc[0]
                
                for _, row in group.iterrows():
                    # Weight ist IMMER in Prozent (z.B. 0.96 = 0.96%, 8.5 = 8.5%)
                    weight_percent = float(row['Weight'])
                    weight_decimal = weight_percent / 100.0  # Konvertiere zu Dezimal (0.96% -> 0.0096)
                    
                    holding_dict = {
                        'name': row['Holding_Name'],
                        'weight': weight_decimal,
                        'currency': row.get('Currency', 'USD'),
                        'sector': row.get('Sector', 'Unknown'),
                        'industry': row.get('Industry', 'Unknown')
                    }
                    
                    # Country ist optional - wenn vorhanden, hinzufügen
                    if 'Country' in row and pd.notna(row['Country']):
                        holding_dict['country'] = row['Country']
                    
                    holdings.append(holding_dict)
                
                # Berechne Gesamtgewicht der definierten Holdings
                total_weight = sum(h['weight'] for h in holdings)
                
                # Wenn Gesamtgewicht < 100%, füge "Other Holdings" hinzu
                if total_weight < 0.999:  # Kleine Toleranz für Rundungsfehler
                    other_weight = 1.0 - total_weight
                    holdings.append({
                        'name': 'Other Holdings',
                        'weight': other_weight,
                        'currency': 'Mixed',
                        'sector': 'Diversified',
                        'industry': 'Diversified'
                    })
                    print(f"  ℹ️  Added 'Other Holdings' for {etf_name}: {other_weight*100:.2f}%")
                
                self.holdings_cache[isin] = {
                    'isin': isin,
                    'name': etf_name,
                    'holdings': holdings,
                    'source': 'User CSV',
                    'fetch_date': 'Manual'
                }
            
            print(f"✅ Loaded {len(self.holdings_cache)} ETFs from user holdings file")
        
        except Exception as e:
            print(f"⚠️  Error loading user holdings: {str(e)}")
    
    def get_holdings(self, isin: str) -> Optional[Dict]:
        """
        Gibt Holdings für eine ISIN zurück (falls vorhanden)
        """
        return self.holdings_cache.get(isin)
    
    def add_etf_from_csv(self, csv_content: str) -> int:
        """
        Fügt ETF-Holdings aus CSV-Content hinzu
        
        Returns:
            Anzahl der hinzugefügten ETFs
        """
        try:
            # Parse CSV
            from io import StringIO
            df = pd.read_csv(StringIO(csv_content))
            
            # Validiere Format
            required_cols = ['ISIN', 'ETF_Name', 'Holding_Name', 'Weight']
            if not all(col in df.columns for col in required_cols):
                raise ValueError(f"CSV muss folgende Spalten enthalten: {', '.join(required_cols)}")
            
            # Speichere in Datei
            if self.user_holdings_file.exists():
                # Append zu existierender Datei
                existing_df = pd.read_csv(self.user_holdings_file)
                combined_df = pd.concat([existing_df, df], ignore_index=True)
                combined_df.to_csv(self.user_holdings_file, index=False)
            else:
                # Erstelle neue Datei
                self.user_holdings_file.parent.mkdir(parents=True, exist_ok=True)
                df.to_csv(self.user_holdings_file, index=False)
            
            # Reload Cache
            self._load_user_holdings()
            
            return len(df['ISIN'].unique())
        
        except Exception as e:
            print(f"Error adding ETFs from CSV: {str(e)}")
            return 0
    
    def create_template_csv(self) -> str:
        """
        Erstellt eine Template-CSV für Benutzer
        """
        template = """ISIN,ETF_Name,Holding_Name,Weight,Currency,Sector,Industry,Country
LU1681045370,Amundi MSCI Germany,SAP SE,8.5,EUR,Technology,Software,DE
LU1681045370,Amundi MSCI Germany,Siemens AG,7.2,EUR,Industrials,Conglomerate,DE
LU1681045370,Amundi MSCI Germany,Allianz SE,6.8,EUR,Financial Services,Insurance,DE
LU1681045370,Amundi MSCI Germany,Deutsche Telekom AG,5.9,EUR,Communication Services,Telecom,DE
LU1681045370,Amundi MSCI Germany,Mercedes-Benz Group AG,5.2,EUR,Consumer Cyclical,Auto Manufacturers,DE
LU1681045370,Amundi MSCI Germany,Other Holdings,66.4,EUR,Diversified,Diversified,DE
"""
        return template


# Globale Instanz
_user_holdings_manager = None

def get_user_holdings_manager() -> UserETFHoldingsManager:
    """
    Gibt die globale User Holdings Manager Instanz zurück
    """
    global _user_holdings_manager
    if _user_holdings_manager is None:
        _user_holdings_manager = UserETFHoldingsManager()
    return _user_holdings_manager
