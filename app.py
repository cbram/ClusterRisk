"""
ClusterRisk - Portfolio Klumpenrisiko Analyse Tool
Analysiert Portfolios aus Portfolio Performance und visualisiert Klumpenrisiken
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import warnings

# Unterdrücke Pandas FutureWarnings (kommen von Plotly, nicht von uns)
warnings.filterwarnings('ignore', category=FutureWarning, module='plotly')

# Sicherstellen, dass src importiert werden kann
sys.path.insert(0, str(Path(__file__).parent))

from src.csv_parser import parse_portfolio_csv
from src.risk_calculator import calculate_cluster_risks
from src.visualizer import create_visualizations
from src.export import export_to_calc
from src.database import save_to_history, get_history, delete_analysis, clear_all_history
from src.diagnostics import get_diagnostics, reset_diagnostics

# Seiten-Konfiguration
st.set_page_config(
    page_title="ClusterRisk - Portfolio Analyse",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Titel und Beschreibung
st.title("📊 ClusterRisk - Portfolio Klumpenrisiko Analyse")
st.markdown("""
Analysiere dein Investment-Portfolio auf Klumpenrisiken über verschiedene Dimensionen:
- **Anlageklasse** (Tagesgeld, ETFs, Rohstoffe, Aktien)
- **Branche/Sektor**
- **Währung**
- **Einzelpositionen** (mit ETF-Durchschau)
""")

# Sidebar
with st.sidebar:
    st.header("⚙️ Einstellungen")
    
    # File Upload
    uploaded_file = st.file_uploader(
        "Portfolio Performance CSV hochladen",
        type=['csv'],
        help="Exportiere dein Portfolio aus Portfolio Performance als CSV (Vermögensaufstellung)"
    )
    
    # Format-Info
    if uploaded_file:
        st.caption(f"📄 Dateiformat: CSV")
    
    st.divider()
    
    # ETF Datenquelle
    st.subheader("ETF Datenquellen")
    use_cache = st.checkbox(
        "Cache verwenden", 
        value=True, 
        help="Gecacht werden: ETF-Holdings (von APIs), Währungskurse (ECB), Ticker-Sektor-Mappings. ETF-Detail-Dateien (data/etf_details/) werden NICHT gecacht und sind immer aktuell."
    )
    cache_days = st.slider(
        "Cache-Dauer (Tage)", 
        1, 30, 7,
        help="Wie lange sollen abgerufene Daten gecacht werden? ETF-Detail-Dateien sind hiervon nicht betroffen."
    )
    
    st.divider()
    
    # Visualisierungs-Optionen
    st.subheader("Visualisierung")
    max_positions_treemap = st.slider(
        "Max. Positionen in Treemap", 
        min_value=10, 
        max_value=100, 
        value=30,
        step=5,
        help="Anzahl der Positionen, die in der Treemap angezeigt werden (größere Werte können unübersichtlich werden)"
    )
    max_positions_pie = st.slider(
        "Max. Positionen in Pie Chart", 
        min_value=5, 
        max_value=30, 
        value=10,
        step=5,
        help="Anzahl der Positionen im Kreisdiagramm (Rest wird als 'Sonstige' zusammengefasst)"
    )
    max_positions_bar = st.slider(
        "Max. Positionen in Bar Chart", 
        min_value=10, 
        max_value=100, 
        value=30,
        step=10,
        help="Anzahl der Positionen im Balkendiagramm"
    )
    
    st.divider()
    
    # Risikoschwellen
    st.subheader("🎯 Risikoschwellen")
    use_auto_thresholds = st.checkbox(
        "Automatische Schwellen verwenden", 
        value=True,
        help="Verwendet kategorie-spezifische Schwellenwerte basierend auf Portfolio-Best-Practices"
    )
    
    if use_auto_thresholds:
        # Standard-Schwellenwerte aus config.py
        risk_thresholds = None  # Signal für Visualizer, Defaults zu nutzen
        st.caption("📊 Automatisch: Anlageklasse 75%, Sektor 25%, Währung 80%, Land 50%, Einzelpos. 10%")
    else:
        # Manuelle Anpassung in Expander
        with st.expander("✏️ Risikoschwellen manuell anpassen"):
            st.markdown("**Hohes Risiko ab...**")
            
            col1, col2 = st.columns(2)
            with col1:
                threshold_asset_class = st.slider(
                    "Anlageklasse", 
                    min_value=10, 
                    max_value=100, 
                    value=75,
                    step=5,
                    help="Ab welchem Prozentsatz gilt eine Anlageklasse als zu konzentriert?"
                )
                threshold_sector = st.slider(
                    "Sektor", 
                    min_value=5, 
                    max_value=50, 
                    value=25,
                    step=5,
                    help="Ab welchem Prozentsatz gilt ein Sektor als zu konzentriert?"
                )
                threshold_currency = st.slider(
                    "Währung", 
                    min_value=10, 
                    max_value=100, 
                    value=80,
                    step=5,
                    help="Ab welchem Prozentsatz gilt eine Währung als zu konzentriert?"
                )
            
            with col2:
                threshold_country = st.slider(
                    "Land", 
                    min_value=10, 
                    max_value=100, 
                    value=50,
                    step=5,
                    help="Ab welchem Prozentsatz gilt ein Land als zu konzentriert?"
                )
                threshold_positions = st.slider(
                    "Einzelpositionen", 
                    min_value=1, 
                    max_value=30, 
                    value=10,
                    step=1,
                    help="Ab welchem Prozentsatz gilt eine Einzelposition als zu konzentriert?"
                )
            
            # Erstelle Dictionary für custom thresholds
            risk_thresholds = {
                'asset_class': {'high': threshold_asset_class, 'medium': threshold_asset_class * 0.66},
                'sector': {'high': threshold_sector, 'medium': threshold_sector * 0.6},
                'currency': {'high': threshold_currency, 'medium': threshold_currency * 0.75},
                'country': {'high': threshold_country, 'medium': threshold_country * 0.6},
                'positions': {'high': threshold_positions, 'medium': threshold_positions * 0.5}
            }
    
    st.divider()
    
    # Export Optionen
    st.subheader("Export")
    export_format = st.selectbox(
        "Format",
        ["Excel (.xlsx)", "LibreOffice (.ods)", "Beide"],
        index=0
    )

# Hauptbereich
if uploaded_file is None:
    st.info("👆 Bitte lade eine Portfolio Performance CSV-Datei hoch, um zu beginnen.")
    
    # Beispiel zeigen
    with st.expander("ℹ️ Wie exportiere ich aus Portfolio Performance?"):
        st.markdown("""
        ### CSV-Export (Vermögensaufstellung)
        1. Öffne Portfolio Performance
        2. Gehe zu **Berichte** → **Vermögensaufstellung**
        3. Klicke auf **Export** → **CSV**
        4. Lade die CSV-Datei hier hoch
        
        ### Wichtig:
        - Die CSV sollte folgende Spalten enthalten: Bestand, Name, Symbol, Kurs, Marktwert, ISIN
        - Optional: Spalte "Branchen (GICS, Sektoren)" für Branchenzuordnung
        - Optional: Spalte "Notiz" für spezielle Marker (z.B. "Geldmarkt ETF" für Cash-Klassifizierung)
        
        **Hinweis:** CSV ist einfacher und schneller!
        """)

else:
    # Datei verarbeiten (nur CSV)
    # Reset Diagnostics vor neuem Parsing
    reset_diagnostics()
    
    with st.spinner("📂 Portfolio Performance CSV wird gelesen..."):
        try:
            portfolio_data = parse_portfolio_csv(uploaded_file)
            
            st.success(f"✅ Portfolio erfolgreich geladen: {portfolio_data['total_positions']} Positionen")
            
            # Portfolio Übersicht
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Gesamt-Wert", f"€ {portfolio_data['total_value']:,.2f}")
            with col2:
                st.metric("Positionen", portfolio_data['total_positions'])
            with col3:
                st.metric("ETFs", portfolio_data['etf_count'])
            with col4:
                st.metric("Einzelaktien", portfolio_data['stock_count'])
            
        except Exception as e:
            st.error(f"❌ Fehler beim Lesen der Datei: {str(e)}")
            st.stop()
    
    # ETF-Daten abrufen und Risiken berechnen
    with st.spinner("🔍 ETF-Zusammensetzungen werden abgerufen und Klumpenrisiken berechnet..."):
        try:
            risk_data = calculate_cluster_risks(
                portfolio_data,
                use_cache=use_cache,
                cache_days=cache_days
            )
            
            st.success("✅ Klumpenrisiken erfolgreich berechnet!")
            
            # Zeige Diagnose-Meldungen (Warnungen und Fehler)
            diagnostics = get_diagnostics()
            summary = diagnostics.get_summary()
            
            if summary['warnings'] > 0 or summary['errors'] > 0:
                st.divider()
                
                # Erstelle Expander für Diagnosen
                with st.expander(f"⚠️ {summary['warnings']} Warnung(en) und {summary['errors']} Fehler gefunden - Hier klicken für Details", expanded=(summary['errors'] > 0)):
                    # Fehler anzeigen (falls vorhanden)
                    errors = diagnostics.get_errors()
                    if errors:
                        st.error(f"**{len(errors)} Fehler:**")
                        for err in errors:
                            st.markdown(f"**{err['category']}:** {err['message']}")
                            if err['details']:
                                st.caption(err['details'])
                    
                    # Warnungen anzeigen
                    warnings = diagnostics.get_warnings()
                    if warnings:
                        st.warning(f"**{len(warnings)} Warnung(en):**")
                        
                        # Gruppiere Warnungen nach Kategorie
                        warnings_by_category = {}
                        for warn in warnings:
                            cat = warn['category']
                            if cat not in warnings_by_category:
                                warnings_by_category[cat] = []
                            warnings_by_category[cat].append(warn)
                        
                        # Zeige Warnungen gruppiert
                        for category, warns in warnings_by_category.items():
                            st.markdown(f"**{category}** ({len(warns)} Problem(e)):")
                            for warn in warns:
                                st.markdown(f"- {warn['message']}")
                                if warn['details']:
                                    st.caption(f"  ℹ️ {warn['details']}")
                            st.markdown("")  # Leerzeile zwischen Kategorien
            
        except Exception as e:
            st.error(f"❌ Fehler bei der Risikoberechnung: {str(e)}")
            st.stop()
    
    # Tabs für verschiedene Analysen
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Anlageklasse",
        "🏭 Branche",
        "💱 Währung",
        "🌍 Land",
        "📈 Einzelpositionen",
        "📋 Detaildaten",
        "🕐 Historie"
    ])
    
    with tab1:
        st.subheader("Klumpenrisiko nach Anlageklasse")
        create_visualizations(risk_data, "asset_class", max_treemap=max_positions_treemap, max_pie=max_positions_pie, max_bar=max_positions_bar, risk_thresholds=risk_thresholds)
    
    with tab2:
        st.subheader("Klumpenrisiko nach Branche/Sektor")
        create_visualizations(risk_data, "sector", max_treemap=max_positions_treemap, max_pie=max_positions_pie, max_bar=max_positions_bar, risk_thresholds=risk_thresholds)
    
    with tab3:
        st.subheader("Klumpenrisiko nach Währung")
        st.markdown("*Commodities (Gold, etc.) haben kein Währungsrisiko und werden optional angezeigt*")
        
        # Toggle für Commodities ein/aus
        col1, col2 = st.columns([3, 1])
        with col2:
            include_commodities = st.checkbox("Commodities einblenden", value=False, key="include_commodities_currency")
        
        # Wähle die richtige Datenquelle
        if include_commodities:
            st.info("💡 **Hinweis:** Commodities werden als separate Kategorie 'Commodity (kein Währungsrisiko)' angezeigt.")
            # Erstelle temporäres risk_data mit Commodities
            risk_data_with_commodities = risk_data.copy()
            risk_data_with_commodities['currency'] = risk_data['currency_with_commodities']
            create_visualizations(risk_data_with_commodities, "currency", max_treemap=max_positions_treemap, max_pie=max_positions_pie, max_bar=max_positions_bar, risk_thresholds=risk_thresholds)
        else:
            create_visualizations(risk_data, "currency", max_treemap=max_positions_treemap, max_pie=max_positions_pie, max_bar=max_positions_bar, risk_thresholds=risk_thresholds)
    
    with tab4:
        st.subheader("Klumpenrisiko nach Land")
        st.markdown("*Basierend auf ISIN-Ländercode (erste 2 Zeichen)*")
        create_visualizations(risk_data, "country", max_treemap=max_positions_treemap, max_pie=max_positions_pie, max_bar=max_positions_bar, risk_thresholds=risk_thresholds)
    
    with tab5:
        st.subheader("Klumpenrisiko nach Einzelpositionen")
        st.markdown("*Inkl. ETF-Durchschau: Jede Aktie in ETFs wird einzeln aufgeschlüsselt*")
        
        # Toggle für Cash ein/aus
        col1, col2 = st.columns([3, 1])
        with col2:
            exclude_cash = st.checkbox("Cash ausblenden", value=False, key="exclude_cash_positions")
        
        # Filtere Cash wenn gewünscht
        if exclude_cash:
            positions_filtered = risk_data['positions'][risk_data['positions']['Position'] != 'Cash'].copy()
            # Neuberechnung der Prozente ohne Cash (pandas-safe)
            total_without_cash = positions_filtered['Wert (€)'].sum()
            positions_filtered.loc[:, 'Anteil (%)'] = (positions_filtered['Wert (€)'] / total_without_cash * 100).round(2)
            
            # Erstelle temporäres risk_data für Visualisierung
            risk_data_filtered = risk_data.copy()
            risk_data_filtered['positions'] = positions_filtered
            create_visualizations(risk_data_filtered, "positions", max_treemap=max_positions_treemap, max_pie=max_positions_pie, max_bar=max_positions_bar, risk_thresholds=risk_thresholds)
        else:
            create_visualizations(risk_data, "positions", max_treemap=max_positions_treemap, max_pie=max_positions_pie, max_bar=max_positions_bar, risk_thresholds=risk_thresholds)
    
    with tab6:
        st.subheader("Detaillierte Daten")
        
        # Export-Buttons
        col1, col2 = st.columns(2)
        with col1:
            if export_format in ["Excel (.xlsx)", "Beide"]:
                xlsx_data = export_to_calc(risk_data, format='xlsx')
                st.download_button(
                    label="📥 Als Excel (.xlsx) herunterladen",
                    data=xlsx_data,
                    file_name="portfolio_klumpenrisiko.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        
        with col2:
            if export_format in ["LibreOffice (.ods)", "Beide"]:
                ods_data = export_to_calc(risk_data, format='ods')
                st.download_button(
                    label="📥 Als LibreOffice (.ods) herunterladen",
                    data=ods_data,
                    file_name="portfolio_klumpenrisiko.ods",
                    mime="application/vnd.oasis.opendocument.spreadsheet"
                )
        
        # Daten-Tabellen anzeigen
        st.markdown("---")
        
        # Speichern-Button
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("💾 In Historie speichern", type="primary", use_container_width=True):
                save_to_history(portfolio_data, risk_data)
                st.success("✅ Analyse gespeichert!")
                st.rerun()  # Aktualisiere die Seite damit Historie-Tab sich aktualisiert
        
        st.markdown("---")
        
        for category in ["asset_class", "sector", "currency", "country", "positions"]:
            with st.expander(f"📊 {category.replace('_', ' ').title()}-Daten"):
                df = risk_data[category]
                st.dataframe(df, width='stretch', height=400)
        
        # Zusätzlich: Währung mit Commodities
        with st.expander("📊 Währung (mit Commodities)-Daten"):
            df = risk_data['currency_with_commodities']
            st.dataframe(df, width='stretch', height=400)
    
    with tab7:
        st.subheader("📈 Analyse-Historie")
        
        history = get_history()
        if not history.empty:
            # Aktionen oberhalb der Tabelle
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("🗑️ Alle löschen", type="secondary", use_container_width=True):
                    if clear_all_history():
                        st.success("✅ Alle Analysen gelöscht!")
                        st.rerun()
                    else:
                        st.error("❌ Fehler beim Löschen")
            
            # Füge Checkbox-Spalte hinzu
            history_with_selection = history.copy()
            history_with_selection.insert(0, '🗑️', False)
            
            # Interaktive Tabelle mit Checkboxen
            edited_df = st.data_editor(
                history_with_selection,
                use_container_width=True,
                hide_index=True,
                column_config={
                    '🗑️': st.column_config.CheckboxColumn(
                        '🗑️',
                        help="Zum Löschen auswählen",
                        default=False
                    ),
                    'ID': st.column_config.NumberColumn('ID', disabled=True),
                    'Datum': st.column_config.TextColumn('Datum', disabled=True),
                    'Gesamt-Wert': st.column_config.TextColumn('Gesamt-Wert', disabled=True),
                    'Positionen': st.column_config.NumberColumn('Positionen', disabled=True),
                    'ETFs': st.column_config.NumberColumn('ETFs', disabled=True),
                    'Aktien': st.column_config.NumberColumn('Aktien', disabled=True)
                },
                disabled=['ID', 'Datum', 'Gesamt-Wert', 'Positionen', 'ETFs', 'Aktien']
            )
            
            # Prüfe welche Zeilen ausgewählt wurden
            selected_ids = edited_df[edited_df['🗑️'] == True]['ID'].tolist()
            
            # Lösch-Button erscheint nur wenn Auswahl vorhanden
            if selected_ids:
                st.markdown("---")
                col1, col2, col3 = st.columns([2, 1, 2])
                with col2:
                    if st.button(
                        f"🗑️ {len(selected_ids)} Auswahl löschen",
                        type="primary",
                        use_container_width=True
                    ):
                        deleted_count = 0
                        for analysis_id in selected_ids:
                            if delete_analysis(int(analysis_id)):
                                deleted_count += 1
                        
                        st.success(f"✅ {deleted_count} Analyse(n) gelöscht!")
                        st.rerun()
            
            # Statistiken
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Gespeicherte Analysen", len(history))
            with col2:
                if len(history) > 0:
                    first_date = pd.to_datetime(history['Datum'].iloc[-1], format='%d.%m.%Y %H:%M')
                    st.metric("Erste Analyse", first_date.strftime('%d.%m.%Y'))
            with col3:
                if len(history) > 0:
                    last_date = pd.to_datetime(history['Datum'].iloc[0], format='%d.%m.%Y %H:%M')
                    st.metric("Letzte Analyse", last_date.strftime('%d.%m.%Y'))
        else:
            st.info("📭 Noch keine Analysen gespeichert. Klicke auf '💾 In Historie speichern' im Tab 'Detaildaten', um Analysen zu speichern.")

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.8em;'>
    ClusterRisk v1.0 | Entwickelt für Portfolio-Analyse mit ETF-Durchschau
</div>
""", unsafe_allow_html=True)
