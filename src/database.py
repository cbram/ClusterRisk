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
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df['total_value'] = df['total_value'].apply(lambda x: f'€ {x:,.2f}')
            
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
