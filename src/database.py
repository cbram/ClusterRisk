"""
Database Module
Verwaltet Historie der Portfolio-Analysen
"""

import sqlite3
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class HistoryDatabase:
    """
    SQLite-Datenbank für Portfolio-Historie
    """
    
    def __init__(self, db_path: str = "data/history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """
        Initialisiert die Datenbank-Struktur
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Analysen-Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    total_value REAL NOT NULL,
                    total_positions INTEGER NOT NULL,
                    etf_count INTEGER NOT NULL,
                    stock_count INTEGER NOT NULL,
                    risk_data TEXT NOT NULL
                )
            """)
            
            # Index für schnellere Abfragen
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON analyses(timestamp)
            """)
            
            conn.commit()
    
    def save_analysis(self, portfolio_data: Dict, risk_data: Dict):
        """
        Speichert eine Analyse in der Historie
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Risk-Data als JSON serialisieren (DataFrames -> Dict)
            risk_data_serialized = {}
            for key, value in risk_data.items():
                if isinstance(value, pd.DataFrame):
                    risk_data_serialized[key] = value.to_dict('records')
                else:
                    risk_data_serialized[key] = value
            
            cursor.execute("""
                INSERT INTO analyses (
                    timestamp, total_value, total_positions, 
                    etf_count, stock_count, risk_data
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                portfolio_data['total_value'],
                portfolio_data['total_positions'],
                portfolio_data['etf_count'],
                portfolio_data['stock_count'],
                json.dumps(risk_data_serialized)
            ))
            
            conn.commit()
    
    def get_all_analyses(self) -> pd.DataFrame:
        """
        Holt alle gespeicherten Analysen
        
        Returns:
            DataFrame mit Analyse-Übersicht
        """
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT 
                    id,
                    timestamp,
                    total_value,
                    total_positions,
                    etf_count,
                    stock_count
                FROM analyses
                ORDER BY timestamp DESC
            """
            
            df = pd.read_sql_query(query, conn)
            
            if not df.empty:
                # Timestamp formatieren
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df['Datum'] = df['timestamp'].dt.strftime('%d.%m.%Y %H:%M')
                
                # Wert formatieren
                df['Gesamt-Wert'] = df['total_value'].apply(lambda x: f'€ {x:,.2f}')
                
                # Spalten umbenennen und neu ordnen
                df = df.rename(columns={
                    'id': 'ID',
                    'total_positions': 'Positionen',
                    'etf_count': 'ETFs',
                    'stock_count': 'Aktien'
                })
                
                # Nur relevante Spalten zurückgeben
                df = df[['ID', 'Datum', 'Gesamt-Wert', 'Positionen', 'ETFs', 'Aktien']]
            
            return df
    
    def get_analysis(self, analysis_id: int) -> Optional[Dict]:
        """
        Holt eine spezifische Analyse
        
        Args:
            analysis_id: ID der Analyse
        
        Returns:
            Dict mit vollständigen Analyse-Daten
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT risk_data
                FROM analyses
                WHERE id = ?
            """, (analysis_id,))
            
            row = cursor.fetchone()
            
            if row:
                return json.loads(row[0])
        
        return None
    
    def get_timeline_data(self, category: str = 'total_value') -> pd.DataFrame:
        """
        Holt Zeitreihen-Daten für Verlaufsdiagramme
        
        Args:
            category: 'total_value' oder spezifische Position
        
        Returns:
            DataFrame mit Zeitreihen
        """
        with sqlite3.connect(self.db_path) as conn:
            if category == 'total_value':
                query = """
                    SELECT timestamp, total_value as value
                    FROM analyses
                    ORDER BY timestamp
                """
                df = pd.read_sql_query(query, conn)
            else:
                # TODO: Implementiere für spezifische Positionen
                df = pd.DataFrame()
            
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            return df


# Globale Datenbank-Instanz
_db = HistoryDatabase()


def save_to_history(portfolio_data: Dict, risk_data: Dict):
    """
    Convenience-Funktion zum Speichern in der Historie
    """
    _db.save_analysis(portfolio_data, risk_data)


def get_history() -> pd.DataFrame:
    """
    Convenience-Funktion zum Abrufen der Historie
    """
    return _db.get_all_analyses()


def get_timeline(category: str = 'total_value') -> pd.DataFrame:
    """
    Convenience-Funktion für Zeitreihen-Daten
    """
    return _db.get_timeline_data(category)


def get_history_timeseries() -> Optional[Dict]:
    """
    Lädt alle Historie-Einträge und extrahiert strukturierte Zeitreihen-Daten
    für Charts (Portfolio-Wert, Anlageklassen, Währungen, Top-5-Konzentration).
    
    Returns:
        Dict mit Zeitreihen-DataFrames oder None wenn < 2 Einträge
    """
    try:
        with sqlite3.connect(_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, total_value, risk_data
                FROM analyses
                ORDER BY timestamp ASC
            """)
            rows = cursor.fetchall()
        
        if len(rows) < 2:
            return None
        
        # Datenstrukturen vorbereiten
        timestamps = []
        total_values = []
        top5_concentrations = []
        asset_class_rows = []
        currency_rows = []
        sector_rows = []
        
        for timestamp_str, total_value, risk_data_json in rows:
            timestamp = pd.to_datetime(timestamp_str)
            timestamps.append(timestamp)
            total_values.append(total_value)
            
            risk_data = json.loads(risk_data_json)
            
            # Top-5 Konzentration aus positions
            positions = risk_data.get('positions', [])
            # Sortiere nach Anteil (%) absteigend
            positions_sorted = sorted(positions, key=lambda x: x.get('Anteil (%)', 0), reverse=True)
            top5_sum = sum(p.get('Anteil (%)', 0) for p in positions_sorted[:5])
            top5_concentrations.append(top5_sum)
            
            # Anlageklassen
            asset_row = {'timestamp': timestamp}
            for entry in risk_data.get('asset_class', []):
                name = entry.get('Anlageklasse', 'Unknown')
                asset_row[name] = entry.get('Anteil (%)', 0)
            asset_class_rows.append(asset_row)
            
            # Währungen (Top 4 + Sonstige)
            currency_entries = risk_data.get('currency', [])
            currency_sorted = sorted(currency_entries, key=lambda x: x.get('Anteil (%)', 0), reverse=True)
            currency_row = {'timestamp': timestamp}
            for i, entry in enumerate(currency_sorted):
                name = entry.get('Währung', 'Unknown')
                if i < 4:
                    currency_row[name] = entry.get('Anteil (%)', 0)
                else:
                    currency_row['Sonstige'] = currency_row.get('Sonstige', 0) + entry.get('Anteil (%)', 0)
            currency_rows.append(currency_row)
            
            # Sektoren (Top 5 + Sonstige)
            sector_entries = risk_data.get('sector', [])
            sector_sorted = sorted(sector_entries, key=lambda x: x.get('Anteil (%)', 0), reverse=True)
            sector_row = {'timestamp': timestamp}
            for i, entry in enumerate(sector_sorted):
                name = entry.get('Sektor', 'Unknown')
                if i < 5:
                    sector_row[name] = entry.get('Anteil (%)', 0)
                else:
                    sector_row['Sonstige'] = sector_row.get('Sonstige', 0) + entry.get('Anteil (%)', 0)
            sector_rows.append(sector_row)
        
        # DataFrames erstellen
        portfolio_df = pd.DataFrame({
            'timestamp': timestamps,
            'Gesamt-Wert (€)': total_values,
            'Top-5 Konzentration (%)': top5_concentrations
        })
        
        asset_class_df = pd.DataFrame(asset_class_rows).fillna(0)
        currency_df = pd.DataFrame(currency_rows).fillna(0)
        sector_df = pd.DataFrame(sector_rows).fillna(0)
        
        return {
            'portfolio': portfolio_df,
            'asset_class': asset_class_df,
            'currency': currency_df,
            'sector': sector_df
        }
    
    except Exception as e:
        print(f"Fehler beim Laden der Zeitreihen: {e}")
        return None


def delete_analysis(analysis_id: int) -> bool:
    """
    Löscht eine Analyse aus der Historie
    
    Args:
        analysis_id: ID der zu löschenden Analyse
        
    Returns:
        True wenn erfolgreich gelöscht, False sonst
    """
    try:
        with sqlite3.connect(_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Fehler beim Löschen der Analyse {analysis_id}: {e}")
        return False


def clear_all_history() -> bool:
    """
    Löscht alle Analysen aus der Historie
    
    Returns:
        True wenn erfolgreich, False sonst
    """
    try:
        with sqlite3.connect(_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM analyses")
            conn.commit()
            # VACUUM um Speicherplatz freizugeben
            cursor.execute("VACUUM")
            conn.commit()
            return True
    except Exception as e:
        print(f"Fehler beim Löschen aller Analysen: {e}")
        return False


def vacuum_database() -> bool:
    """
    Komprimiert die Datenbank und gibt gelöschten Speicherplatz frei
    
    Returns:
        True wenn erfolgreich, False sonst
    """
    try:
        with sqlite3.connect(_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("VACUUM")
            conn.commit()
            return True
    except Exception as e:
        print(f"Fehler beim VACUUM: {e}")
        return False
