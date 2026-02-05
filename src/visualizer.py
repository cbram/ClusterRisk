"""
Visualizer
Erstellt interaktive Visualisierungen für Klumpenrisiken
"""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd
from typing import Dict, Optional
from config import RISK_THRESHOLDS


def create_visualizations(risk_data: Dict, category: str, max_treemap: int = 30, max_pie: int = 10, max_bar: int = 30, risk_thresholds: Optional[Dict] = None):
    """
    Erstellt Visualisierungen für eine Risiko-Kategorie
    
    Args:
        risk_data: Risiko-Daten
        category: Kategorie ('asset_class', 'sector', 'currency', 'positions')
        max_treemap: Maximale Anzahl Positionen in Treemap
        max_pie: Maximale Anzahl Positionen in Pie Chart
        max_bar: Maximale Anzahl Positionen in Bar Chart
        risk_thresholds: Optional custom risk thresholds (None = use defaults from config)
    """
    
    # Hole Schwellenwerte (custom oder defaults)
    if risk_thresholds is None:
        thresholds = RISK_THRESHOLDS.get(category, {'high': 10.0, 'medium': 5.0})
    else:
        thresholds = risk_thresholds.get(category, {'high': 10.0, 'medium': 5.0})
    
    df = risk_data[category]
    
    if df.empty:
        st.warning(f"Keine Daten für {category} verfügbar.")
        return
    
    # Layout: 2 Spalten
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Treemap
        st.subheader("Treemap Visualisierung")
        _create_treemap(df, category, max_items=max_treemap)
    
    with col2:
        # Pie Chart
        st.subheader("Verteilung")
        _create_pie_chart(df, category, max_items=max_pie)
    
    # Volle Breite für Balkendiagramm
    st.subheader("Detaillierte Übersicht")
    _create_bar_chart(df, category, thresholds, max_items=max_bar)
    
    # Tabelle
    st.subheader("Daten-Tabelle")
    _display_table(df, category, thresholds)


def _create_treemap(df: pd.DataFrame, category: str, max_items: int = 30):
    """
    Erstellt eine Treemap-Visualisierung
    
    Args:
        df: DataFrame mit Daten
        category: Kategorie der Daten
        max_items: Maximale Anzahl anzuzeigender Items
    """
    # Spalten-Namen mapping
    label_col, value_col = _get_column_names(category)
    
    # Nur Top N für bessere Übersicht
    df_plot = df.head(max_items).copy()
    
    # Für Einzelpositionen: Verwende Ticker statt langer Namen
    if category == 'positions' and 'Ticker' in df_plot.columns:
        # Erstelle Label: Ticker (falls vorhanden), sonst Name (gekürzt)
        df_plot['Display_Label'] = df_plot.apply(
            lambda row: row['Ticker'] if row['Ticker'] and row['Ticker'].strip() else row['Position'][:25], 
            axis=1
        )
        plot_label = 'Display_Label'
    else:
        plot_label = label_col
    
    # Farben: "Other Holdings" = hellblau, sonst bunte Plotly-Farben
    color_discrete_map = {}
    for idx, row in df_plot.iterrows():
        label = row[label_col]
        if 'Other Holdings' in str(label):
            color_discrete_map[label] = 'lightblue'
    
    # IMMER discrete colors verwenden (buntes Design wie bei Einzelpositionen)
    if category == 'positions' and color_discrete_map:
        # Für Positionen mit Other Holdings: Verwende Original-Namen für Farb-Mapping
        df_plot['Color_Key'] = df_plot[label_col]
        fig = px.treemap(
            df_plot,
            path=[plot_label],
            values=value_col,
            color='Color_Key',
            color_discrete_map=color_discrete_map,
            hover_data={
                label_col: True,  # Zeige vollen Namen im Hover
                value_col: ':,.2f',
                'Anteil (%)': ':.2f',
                'Ticker': True if 'Ticker' in df_plot.columns else False
            }
        )
    else:
        # Buntes Design für alle Kategorien (kein Risiko-Farbschema)
        fig = px.treemap(
            df_plot,
            path=[plot_label],
            values=value_col,
            color=label_col if not color_discrete_map else label_col,
            color_discrete_map=color_discrete_map if color_discrete_map else None,
            hover_data={
                label_col: True if category == 'positions' else False,
                value_col: ':,.2f',
                'Anteil (%)': ':.2f'
            }
        )
    
    # Formatierung: Name, Wert (2 Dezimalstellen), Prozent (2 Dezimalstellen)
    fig.update_traces(
        texttemplate="<b>%{label}</b><br>€ %{value:,.2f}<br>%{percentRoot:.2%}",
        textfont_size=12
    )
    
    fig.update_layout(
        height=500,
        margin=dict(t=10, l=10, r=10, b=10),
        showlegend=False
    )
    
    st.plotly_chart(fig, width='stretch', key=f"treemap_{category}")


def _create_pie_chart(df: pd.DataFrame, category: str, max_items: int = 10):
    """
    Erstellt ein Kreisdiagramm
    
    Args:
        df: DataFrame mit Daten
        category: Kategorie der Daten
        max_items: Maximale Anzahl anzuzeigender Items (Rest wird als "Sonstige" zusammengefasst)
    """
    label_col, value_col = _get_column_names(category)
    
    # Top N + "Sonstige"
    df_plot = df.head(max_items).copy()
    
    if len(df) > max_items:
        others_value = df.iloc[max_items:][value_col].sum()
        others_row = pd.DataFrame([{
            label_col: 'Sonstige',
            value_col: others_value,
            'Anteil (%)': (others_value / df[value_col].sum()) * 100
        }])
        if 'Ticker' in df.columns:
            others_row['Ticker'] = ''
        df_plot = pd.concat([df_plot, others_row], ignore_index=True)
    
    # Für Einzelpositionen: Verwende Ticker statt langer Namen
    if category == 'positions' and 'Ticker' in df_plot.columns:
        # Erstelle Label: Ticker (falls vorhanden), sonst Name (gekürzt)
        df_plot['Display_Label'] = df_plot.apply(
            lambda row: row['Ticker'] if row['Ticker'] and row['Ticker'].strip() else row['Position'][:20], 
            axis=1
        )
        plot_label = 'Display_Label'
        original_label = label_col
    else:
        plot_label = label_col
        original_label = label_col
    
    # Erstelle Farbzuordnung für "Other Holdings"
    color_map = {}
    for label in df_plot[original_label]:
        if 'Other Holdings' in str(label):
            color_map[label] = '#87CEEB'  # Sky Blue / Hellblau
    
    # Erstelle Pie Chart
    if color_map and category == 'positions':
        # Mit speziellen Farben für Other Holdings (Positionen)
        df_plot['Color_Key'] = df_plot[original_label]
        fig = px.pie(
            df_plot,
            names=plot_label,
            values=value_col,
            hole=0.4,
            color='Color_Key',
            color_discrete_map=color_map
        )
        # Hover-Daten manuell hinzufügen mit vollem Namen
        fig.update_traces(
            hovertemplate='<b>%{label}</b><br>Name: ' + df_plot[original_label].astype(str) + '<br>Wert: €%{value:,.2f}<br>Anteil: %{percent}<extra></extra>'
        )
    elif color_map:
        # Mit speziellen Farben für Other Holdings (andere Kategorien)
        fig = px.pie(
            df_plot,
            names=plot_label,
            values=value_col,
            hole=0.4,
            color=original_label,
            color_discrete_map=color_map
        )
        # Hover-Daten manuell hinzufügen
        fig.update_traces(
            hovertemplate='<b>%{label}</b><br>Wert: €%{value:,.2f}<br>Anteil: %{percent}<extra></extra>'
        )
    else:
        # Standard Farben
        fig = px.pie(
            df_plot,
            names=plot_label,
            values=value_col,
            hole=0.4,
            hover_data={'Anteil (%)': ':.2f'}
        )
    
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        textfont_size=10
    )
    
    fig.update_layout(
        height=400,
        showlegend=False,
        margin=dict(t=10, l=10, r=10, b=10)
    )
    
    st.plotly_chart(fig, width='stretch', key=f"pie_{category}")


def _create_bar_chart(df: pd.DataFrame, category: str, thresholds: Dict, max_items: int = 30):
    """
    Erstellt ein horizontales Balkendiagramm
    
    Args:
        df: DataFrame mit Daten
        category: Kategorie der Daten
        thresholds: Risiko-Schwellenwerte (dict mit 'high' und 'medium')
        max_items: Maximale Anzahl anzuzeigender Items
    """
    label_col, value_col = _get_column_names(category)
    
    # Top N
    df_plot = df.head(max_items).copy()
    
    # Hole Schwellenwerte
    high_threshold = thresholds.get('high', 10.0)
    medium_threshold = thresholds.get('medium', 5.0)
    
    # Farbe basierend auf Risiko UND "Other Holdings"
    colors = []
    for idx, row in df_plot.iterrows():
        label = row[label_col]
        anteil = row['Anteil (%)']
        
        if 'Other Holdings' in str(label):
            colors.append('#87CEEB')  # Sky Blue / Hellblau für Other Holdings
        elif anteil > high_threshold:
            colors.append('red')  # Rot für hohes Risiko
        elif anteil > medium_threshold:
            colors.append('orange')  # Orange für mittleres Risiko
        else:
            colors.append('lightgray')  # Grau für normale Positionen
    
    fig = go.Figure(data=[
        go.Bar(
            y=df_plot[label_col],
            x=df_plot['Anteil (%)'],
            orientation='h',
            marker_color=colors,
            text=df_plot['Anteil (%)'].apply(lambda x: f'{x:.2f}%'),
            textposition='auto',
            hovertemplate='<b>%{y}</b><br>Anteil: %{x:.2f}%<br>Wert: €%{customdata:,.2f}<extra></extra>',
            customdata=df_plot[value_col]
        )
    ])
    
    fig.update_layout(
        xaxis_title="Anteil am Portfolio (%)",
        yaxis_title="",
        height=max(400, len(df_plot) * 20),
        showlegend=False,
        yaxis={'categoryorder': 'total ascending'}
    )
    
    # Risiko-Linien (beide Schwellenwerte)
    fig.add_vline(x=high_threshold, line_dash="dash", line_color="red", 
                  annotation_text=f"{high_threshold:.0f}% Hohes Risiko", 
                  annotation_position="top right")
    
    if medium_threshold > 0 and medium_threshold < high_threshold:
        fig.add_vline(x=medium_threshold, line_dash="dot", line_color="orange", 
                      annotation_text=f"{medium_threshold:.0f}% Mittleres Risiko", 
                      annotation_position="bottom right")
    
    st.plotly_chart(fig, width='stretch', key=f"bar_{category}")


def _display_table(df: pd.DataFrame, category: str, thresholds: Dict):
    """
    Zeigt eine formatierte Tabelle an
    
    Args:
        df: DataFrame mit Daten
        category: Kategorie der Daten
        thresholds: Risiko-Schwellenwerte (dict mit 'high' und 'medium')
    """
    # Formatierung mit korrektem Dtype-Handling
    df_display = df.copy()
    
    # Konvertiere zu Object-Dtype vor String-Formatierung
    df_display['Wert (€)'] = df_display['Wert (€)'].astype(object)
    df_display['Anteil (%)'] = df_display['Anteil (%)'].astype(object)
    
    # Wert formatieren
    df_display['Wert (€)'] = df['Wert (€)'].apply(lambda x: f'€ {x:,.2f}')
    df_display['Anteil (%)'] = df['Anteil (%)'].apply(lambda x: f'{x:.2f}%')
    
    # Hole Schwellenwerte
    high_threshold = thresholds.get('high', 10.0)
    medium_threshold = thresholds.get('medium', 5.0)
    
    # Risiko-Kennzeichnung mit kategorie-spezifischen Schwellenwerten
    def highlight_risk(row):
        anteil = float(row['Anteil (%)'].replace('%', '').replace(',', '.'))
        if anteil > high_threshold:
            return ['background-color: #ffcccc'] * len(row)
        elif anteil > medium_threshold:
            return ['background-color: #fff9cc'] * len(row)
        else:
            return [''] * len(row)
    
    styled_df = df_display.style.apply(highlight_risk, axis=1)
    
    st.dataframe(styled_df, width='stretch', height=400)
    
    # Statistiken
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Anzahl Positionen",
            len(df)
        )
    
    with col2:
        # Positionen über Schwellenwert
        high_risk = len(df[df['Anteil (%)'] > high_threshold])
        st.metric(
            f"Positionen > {high_threshold:.0f}%",
            high_risk,
            delta=f"{'⚠️ Hohes Risiko' if high_risk > 0 else '✅ OK'}"
        )
    
    with col3:
        # Top 5 Konzentration
        top5_concentration = df.head(5)['Anteil (%)'].sum()
        st.metric(
            "Top-5 Konzentration",
            f"{top5_concentration:.1f}%"
        )


def _get_column_names(category: str) -> tuple:
    """
    Gibt die Spalten-Namen für Label und Value zurück
    """
    mapping = {
        'asset_class': ('Anlageklasse', 'Wert (€)'),
        'sector': ('Sektor', 'Wert (€)'),
        'currency': ('Währung', 'Wert (€)'),
        'country': ('Land', 'Wert (€)'),
        'positions': ('Position', 'Wert (€)')
    }
    
    return mapping.get(category, ('Name', 'Wert (€)'))
