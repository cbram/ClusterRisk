"""
Diagnostics System
Sammelt Warnungen und Fehler während des Parsings und der Analyse
"""

from typing import List, Dict
from enum import Enum


class DiagnosticLevel(Enum):
    """Schweregrad der Diagnose-Meldung"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class DiagnosticsCollector:
    """
    Sammelt Diagnose-Meldungen während des Parsing- und Analyse-Prozesses
    """
    
    def __init__(self):
        self.messages: List[Dict] = []
    
    def add_info(self, category: str, message: str, details: str = None):
        """Füge Info-Meldung hinzu"""
        self._add_message(DiagnosticLevel.INFO, category, message, details)
    
    def add_warning(self, category: str, message: str, details: str = None):
        """Füge Warn-Meldung hinzu"""
        self._add_message(DiagnosticLevel.WARNING, category, message, details)
    
    def add_error(self, category: str, message: str, details: str = None):
        """Füge Fehler-Meldung hinzu"""
        self._add_message(DiagnosticLevel.ERROR, category, message, details)
    
    def _add_message(self, level: DiagnosticLevel, category: str, message: str, details: str = None):
        """Interne Methode zum Hinzufügen einer Meldung"""
        self.messages.append({
            'level': level,
            'category': category,
            'message': message,
            'details': details
        })
    
    def has_warnings(self) -> bool:
        """Prüfe ob Warnungen vorhanden sind"""
        return any(msg['level'] == DiagnosticLevel.WARNING for msg in self.messages)
    
    def has_errors(self) -> bool:
        """Prüfe ob Fehler vorhanden sind"""
        return any(msg['level'] == DiagnosticLevel.ERROR for msg in self.messages)
    
    def get_warnings(self) -> List[Dict]:
        """Hole alle Warnungen"""
        return [msg for msg in self.messages if msg['level'] == DiagnosticLevel.WARNING]
    
    def get_errors(self) -> List[Dict]:
        """Hole alle Fehler"""
        return [msg for msg in self.messages if msg['level'] == DiagnosticLevel.ERROR]
    
    def get_by_category(self, category: str) -> List[Dict]:
        """Hole alle Meldungen einer Kategorie"""
        return [msg for msg in self.messages if msg['category'] == category]
    
    def get_summary(self) -> Dict:
        """Erstelle Zusammenfassung der Diagnosen"""
        return {
            'total': len(self.messages),
            'errors': len(self.get_errors()),
            'warnings': len(self.get_warnings()),
            'infos': len([msg for msg in self.messages if msg['level'] == DiagnosticLevel.INFO])
        }
    
    def clear(self):
        """Lösche alle gesammelten Meldungen"""
        self.messages = []


# Globale Instanz für einfache Verwendung
_global_collector = DiagnosticsCollector()


def get_diagnostics() -> DiagnosticsCollector:
    """Hole die globale Diagnostics-Instanz"""
    return _global_collector


def reset_diagnostics():
    """Setze die globale Diagnostics-Instanz zurück"""
    _global_collector.clear()
