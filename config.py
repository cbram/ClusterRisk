# Risiko-Schwellenwerte (kategorie-spezifisch)
# Diese Werte basieren auf Portfolio-Best-Practices
RISK_THRESHOLDS = {
    'asset_class': {
        'high': 75.0,      # > 75% einer Anlageklasse = hohes Risiko
        'medium': 50.0,    # 50-75% = mittleres Risiko
    },
    'sector': {
        'high': 25.0,      # > 25% in einem Sektor = hohes Risiko
        'medium': 15.0,    # 15-25% = mittleres Risiko
    },
    'currency': {
        'high': 80.0,      # > 80% in einer Währung = hohes Risiko
        'medium': 60.0,    # 60-80% = mittleres Risiko
    },
    'country': {
        'high': 50.0,      # > 50% in einem Land = hohes Risiko
        'medium': 30.0,    # 30-50% = mittleres Risiko
    },
    'positions': {
        'high': 10.0,      # > 10% in einer Position = hohes Risiko
        'medium': 5.0,     # 5-10% = mittleres Risiko
    }
}


# Farben für Visualisierungen
COLORS = {
    'high_risk': '#ffcccc',
    'medium_risk': '#fff9cc',
    'low_risk': '#ccffcc',
    'primary': '#FF4B4B',
    'secondary': '#0068C9'
}
