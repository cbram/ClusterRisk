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


def _cap_df_with_sonstige(df: pd.DataFrame, max_items: int, label_col: str, value_col: str) -> pd.DataFrame:
    """Top max_items Zeilen; Rest als eine Zeile „Sonstige“ mit summiertem Wert und Anteil (%)."""
    if len(df) <= max_items:
        return df.head(max_items).copy()
    head = df.head(max_items).copy()
    tail = df.iloc[max_items:]
    others_value = float(tail[value_col].sum())
    if 'Anteil (%)' in tail.columns:
        others_anteil = round(float(tail['Anteil (%)'].sum()), 1)
    else:
        total = float(df[value_col].sum()) or 1.0
        others_anteil = round((others_value / total) * 100, 1)
    row: Dict = {label_col: 'Sonstige', value_col: others_value, 'Anteil (%)': others_anteil}
    if 'Ticker' in df.columns:
        row['Ticker'] = ''
    return pd.concat([head, pd.DataFrame([row])], ignore_index=True)


def _add_display_label_positions(df_plot: pd.DataFrame, label_col: str, max_chars: int = 25) -> pd.DataFrame:
    """Kürzt Labels für positions-Treemap/Pie (Ticker oder Positionsname)."""
    if label_col != 'Position' or 'Ticker' not in df_plot.columns:
        return df_plot
    max_len = max_chars
    df_plot = df_plot.copy()
    df_plot['Display_Label'] = df_plot.apply(
        lambda row: row['Ticker'] if row['Ticker'] and str(row['Ticker']).strip()
        else str(row['Position'])[:max_len],
        axis=1
    )
    return df_plot


# Einheitliche Farbgebung in Treemap, Pie und Bar-Chart (Wiedererkennungswert)
OTHER_HOLDINGS_COLOR = '#87CEEB'   # Hellblau für "Other Holdings"
# Bunte Palette für alle übrigen Items (gleiche Reihenfolge = gleiche Farbe in allen Charts)
ITEM_PALETTE = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
    '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5', '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5',
]


def _build_unified_color_map(df: pd.DataFrame, label_col: str) -> Dict[str, str]:
    """
    Baut eine einheitliche Label→Farbe-Zuordnung aus den Daten.
    "Other Holdings" immer hellblau, alle anderen bunt aus der Palette (deterministisch).
    """
    # Reihenfolge: so wie im DataFrame, damit konsistent
    seen = set()
    unique_ordered = []
    for v in df[label_col]:
        if v not in seen:
            seen.add(v)
            unique_ordered.append(v)
    color_map = {}
    palette_idx = 0
    for label in unique_ordered:
        if 'Other Holdings' in str(label):
            color_map[label] = OTHER_HOLDINGS_COLOR
        else:
            color_map[label] = ITEM_PALETTE[palette_idx % len(ITEM_PALETTE)]
            palette_idx += 1
    return color_map


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
    
    label_col, _ = _get_column_names(category)
    color_map = _build_unified_color_map(df, label_col)
    
    # Layout: 2 Spalten
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Treemap
        st.subheader("Treemap Visualisierung")
        _create_treemap(df, category, max_items=max_treemap, color_map=color_map)
    
    with col2:
        # Pie Chart
        st.subheader("Verteilung")
        _create_pie_chart(df, category, max_items=max_pie, color_map=color_map)
    
    # Volle Breite für Balkendiagramm
    st.subheader("Detaillierte Übersicht")
    _create_bar_chart(df, category, thresholds, max_items=max_bar, color_map=color_map)
    
    # Tabelle
    st.subheader("Daten-Tabelle")
    _display_table(df, category, thresholds)


def _create_treemap(df: pd.DataFrame, category: str, max_items: int = 30, color_map: Optional[Dict[str, str]] = None):
    """
    Erstellt eine Treemap-Visualisierung.
    color_map: Einheitliche Label→Farbe (aus _build_unified_color_map).
    Prozent = Spalte Anteil (%) (Anteil am Gesamtportfolio), nicht Plotly-intern.
    """
    label_col, value_col = _get_column_names(category)
    df_plot = _cap_df_with_sonstige(df, max_items, label_col, value_col)
    plot_label = label_col
    if category == 'positions' and 'Ticker' in df_plot.columns:
        df_plot = _add_display_label_positions(df_plot, label_col, max_chars=25)
        plot_label = 'Display_Label'
    
    color_discrete_map = {k: v for k, v in (color_map or {}).items() if k in df_plot[label_col].values}
    if 'Sonstige' in df_plot[label_col].values and 'Sonstige' not in color_discrete_map:
        n = len(color_discrete_map)
        color_discrete_map['Sonstige'] = ITEM_PALETTE[n % len(ITEM_PALETTE)]
    
    if category == 'positions' and color_discrete_map:
        df_plot = df_plot.copy()
        df_plot['Color_Key'] = df_plot[label_col]
        fig = px.treemap(
            df_plot,
            path=[plot_label],
            values=value_col,
            color='Color_Key',
            color_discrete_map=color_discrete_map,
            hover_data={
                label_col: True,
                value_col: ':,.2f',
                'Anteil (%)': ':.1f',
                'Ticker': True if 'Ticker' in df_plot.columns else False
            }
        )
    else:
        fig = px.treemap(
            df_plot,
            path=[plot_label],
            values=value_col,
            color=label_col,
            color_discrete_map=color_discrete_map,
            hover_data={
                label_col: True if category == 'positions' else False,
                value_col: ':,.2f',
                'Anteil (%)': ':.1f'
            }
        )
    
    # hover_data injects Anteil (%) into customdata at index 2 (after label_col and value_col),
    # correctly aligned to Plotly's internal label order — which differs from the DataFrame order.
    if category == 'positions':
        fig.update_traces(
            texttemplate="<b>%{label}</b><br>€ %{value:,.2f}<br>%{customdata[2]:.1f}%",
            hovertemplate=(
                '<b>%{customdata[0]}</b><br>Wert: €%{value:,.2f}<br>'
                'Anteil: %{customdata[2]:.1f}%<extra></extra>'
            ),
            textfont_size=12
        )
    else:
        fig.update_traces(
            texttemplate="<b>%{label}</b><br>€ %{value:,.2f}<br>%{customdata[2]:.1f}%",
            hovertemplate=(
                '<b>%{label}</b><br>Wert: €%{value:,.2f}<br>Anteil: %{customdata[2]:.1f}%<extra></extra>'
            ),
            textfont_size=12
        )
    
    fig.update_layout(
        height=500,
        margin=dict(t=10, l=10, r=10, b=10),
        showlegend=False
    )
    
    st.plotly_chart(fig, width='stretch', key=f"treemap_{category}")


def _create_pie_chart(df: pd.DataFrame, category: str, max_items: int = 10, color_map: Optional[Dict[str, str]] = None):
    """
    Erstellt ein Kreisdiagramm.
    color_map: Einheitliche Label→Farbe (aus _build_unified_color_map).
    Prozent = Spalte Anteil (%) (Anteil am Gesamtportfolio).
    """
    label_col, value_col = _get_column_names(category)
    df_plot = _cap_df_with_sonstige(df, max_items, label_col, value_col)
    plot_label = label_col
    original_label = label_col
    if category == 'positions' and 'Ticker' in df_plot.columns:
        df_plot = _add_display_label_positions(df_plot, label_col, max_chars=20)
        plot_label = 'Display_Label'
    
    pie_color_map = dict(color_map) if color_map else {}
    if 'Sonstige' in df_plot[original_label].values and 'Sonstige' not in pie_color_map:
        n = len(pie_color_map)
        pie_color_map['Sonstige'] = ITEM_PALETTE[n % len(ITEM_PALETTE)]
    for label in df_plot[original_label].unique():
        if label not in pie_color_map:
            pie_color_map[label] = OTHER_HOLDINGS_COLOR if 'Other Holdings' in str(label) else ITEM_PALETTE[len(pie_color_map) % len(ITEM_PALETTE)]
    
    if pie_color_map and category == 'positions':
        df_plot = df_plot.copy()
        df_plot['Color_Key'] = df_plot[original_label]
        fig = px.pie(
            df_plot,
            names=plot_label,
            values=value_col,
            hole=0.4,
            color='Color_Key',
            color_discrete_map=pie_color_map
        )
        anteile = df_plot['Anteil (%)'].astype(float)
        full_names = df_plot[original_label].astype(str)
        custom = list(zip(anteile, full_names))
        fig.update_traces(
            customdata=custom,
            hovertemplate=(
                '<b>%{customdata[1]}</b><br>Wert: €%{value:,.2f}<br>'
                'Anteil: %{customdata[0]:.1f}%<extra></extra>'
            ),
            texttemplate='%{label}<br>%{customdata[0]:.1f}%',
            textinfo='text',
        )
    elif pie_color_map:
        fig = px.pie(
            df_plot,
            names=plot_label,
            values=value_col,
            hole=0.4,
            color=original_label,
            color_discrete_map=pie_color_map
        )
        anteile = df_plot['Anteil (%)'].astype(float).values.reshape(-1, 1)
        fig.update_traces(
            customdata=anteile,
            hovertemplate=(
                '<b>%{label}</b><br>Wert: €%{value:,.2f}<br>Anteil: %{customdata[0]:.1f}%<extra></extra>'
            ),
            texttemplate='%{label}<br>%{customdata[0]:.1f}%',
            textinfo='text',
        )
    else:
        fig = px.pie(
            df_plot,
            names=plot_label,
            values=value_col,
            hole=0.4,
            hover_data={'Anteil (%)': ':.1f'}
        )
        anteile = df_plot['Anteil (%)'].astype(float).values.reshape(-1, 1)
        fig.update_traces(
            customdata=anteile,
            texttemplate='%{label}<br>%{customdata[0]:.1f}%',
            textinfo='text',
            hovertemplate=(
                '<b>%{label}</b><br>Wert: €%{value:,.2f}<br>Anteil: %{customdata[0]:.1f}%<extra></extra>'
            ),
        )
    
    fig.update_traces(
        textposition='inside',
        textfont_size=10
    )
    
    fig.update_layout(
        height=400,
        showlegend=False,
        margin=dict(t=10, l=10, r=10, b=10)
    )
    
    st.plotly_chart(fig, width='stretch', key=f"pie_{category}")


def _create_bar_chart(df: pd.DataFrame, category: str, thresholds: Dict, max_items: int = 30, color_map: Optional[Dict[str, str]] = None):
    """
    Erstellt ein horizontales Balkendiagramm.
    color_map: Einheitliche Label→Farbe (aus _build_unified_color_map).
    Wie Treemap/Pie: bei mehr als max_items eine „Sonstige“-Zeile.
    """
    label_col, value_col = _get_column_names(category)
    df_plot = _cap_df_with_sonstige(df, max_items, label_col, value_col)
    color_map = color_map or {}
    if 'Sonstige' in df_plot[label_col].values and 'Sonstige' not in color_map:
        color_map = dict(color_map)
        n = len(color_map)
        color_map['Sonstige'] = ITEM_PALETTE[n % len(ITEM_PALETTE)]
    colors = [color_map.get(row[label_col], ITEM_PALETTE[i % len(ITEM_PALETTE)]) for i, (_, row) in enumerate(df_plot.iterrows())]
    
    fig = go.Figure(data=[
        go.Bar(
            y=df_plot[label_col],
            x=df_plot['Anteil (%)'],
            orientation='h',
            marker_color=colors,
            text=df_plot['Anteil (%)'].apply(lambda x: f'{x:.1f}%'),
            textposition='auto',
            hovertemplate='<b>%{y}</b><br>Anteil: %{x:.1f}%<br>Wert: €%{customdata:,.2f}<extra></extra>',
            customdata=df_plot[value_col]
        )
    ])
    
    fig.update_layout(
        xaxis_title="Anteil am Portfolio (%)",
        yaxis_title="",
        height=max(400, len(df_plot) * 20),
        showlegend=False,
        yaxis={'categoryorder': 'total ascending'},
        margin=dict(t=10, l=10, r=10, b=10)
    )
    
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
    df_display['Anteil (%)'] = df['Anteil (%)'].apply(lambda x: f'{x:.1f}%')
    
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
    
    # Statistiken (ohne Risiko-Ausweis)
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "Anzahl Positionen",
            len(df)
        )
    
    with col2:
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
