# Änderungen 2026-02-04: ETF-Detail-Struktur

## Zusammenfassung

Das Tool wurde erweitert um **strukturierte ETF-Detail-Dateien** zu unterstützen. Diese ermöglichen eine präzisere Analyse mit vollständigen Sektor-, Länder- und Währungsverteilungen pro ETF.

## Neue Dateien

### ETF-Detail-Dateien erstellt:

1. **`data/etf_details/AEEM.csv`** - Amundi MSCI Emerging Markets (LU1681045370)
2. **`data/etf_details/AUM5.csv`** - Amundi S&P 500 Swap (LU1681048804)
3. **`data/etf_details/GERD.csv`** - L&G Gerd Kommer Multifactor Equity (IE0001UQQ933)
4. **`data/etf_details/VGWD.csv`** - Vanguard FTSE All-World High Dividend Yield (IE00B8GKDB10)
5. **`data/etf_details/EUNL.csv`** - iShares Core MSCI World (IE00B4L5Y983)
6. **`data/etf_details/XEON.csv`** - Xtrackers EUR Overnight Rate Swap (LU0290358497)

### ISIN-Mapping:

- **`data/etf_isin_ticker_map.csv`** - Verknüpft ISINs mit Ticker-Symbolen

### Parser & Dokumentation:

- **`src/etf_details_parser.py`** - Bereits vorhanden, wird jetzt genutzt
- **`CLAUDE.md`** - Vollständige technische Dokumentation

## Geänderte Dateien

### `src/risk_calculator.py`

**Änderungen:**
1. Import von `etf_details_parser` hinzugefügt
2. Neue Funktion `_load_isin_ticker_map()` - Lädt ISIN-zu-Ticker-Mapping
3. `calculate_cluster_risks()` erweitert:
   - Lädt ISIN-Ticker-Map beim Start
   - Übergibt Map an `_expand_etf_holdings()`
4. `_expand_etf_holdings()` komplett überarbeitet:
   - **Priorität 1**: Versucht ETF-Detail-Datei zu laden (via Ticker aus Map)
   - **Priorität 2**: Fallback zu bisherigem Fetcher (user_etf_holdings, Mock, APIs)
   - Extrahiert `etf_type` aus Metadata (z.B. "Money Market")
   - Setzt `sector_source = 'etf_details'` für mittlere Priorität
5. `_calculate_asset_class_risk()` erweitert:
   - Money Market ETFs (via `etf_type`) werden als `Cash` klassifiziert
6. Sektor-Priorität aktualisiert:
   - `etf_details` wird wie `isin` behandelt (Priorität 1)

**Vorteile:**
- ETF-Detail-Dateien haben Vorrang vor Legacy-Quellen
- Korrekte Behandlung von Geldmarkt-ETFs als Cash
- Vollständige Allokationsdaten für bessere "Other Holdings" Behandlung

### `README.md`

**Änderungen:**
1. Neuer Abschnitt "ETF-Detail-Dateien" mit vollständiger Dokumentation
2. Format-Beispiel für neue Struktur
3. Erklärung der ISIN-zu-Ticker-Mapping
4. Aktualisierte Datenquellen-Priorität
5. Aktualisierte Projektstruktur (neuer Ordner `data/etf_details/`)
6. Aktualisierte TODO-Liste

**Neue Struktur dokumentiert:**
```
METADATA
COUNTRY_ALLOCATION
SECTOR_ALLOCATION
CURRENCY_ALLOCATION
TOP_HOLDINGS
```

### `CLAUDE.md` (NEU)

**Inhalt:**
- Vollständige technische Dokumentation
- Architektur-Übersicht und Datenfluss
- Detaillierte Beschreibung aller Module
- Datenstrukturen und Schnittstellen
- Neue ETF-Detail-Struktur erklärt
- Prioritäten und Konfliktauflösung
- Performance-Optimierungen
- Bekannte Limitierungen und Lösungen
- Changelog

## Funktionale Änderungen

### 1. ETF-Typ-Klassifizierung

**Vorher:**
- Geldmarkt-ETFs wurden via `Notiz`-Feld in PP CSV erkannt
- Fehleranfällig und inkonsistent

**Nachher:**
- ETF-Typ wird in Metadata gespeichert (`Type: Money Market`)
- Automatische Klassifizierung als `Cash` in Anlageklassen-Ansicht
- Unabhängig von PP-Eingaben

### 2. "Other Holdings" Behandlung

**Vorher:**
- "Other Holdings" hatte keine Sektor/Land/Währung-Informationen
- Wurde als "Diversified" behandelt

**Nachher:**
- Gesamt-Allokationen (Sektor/Land/Währung) aus ETF-Detail-Dateien
- In Einzelpositionen: "Other Holdings - {ETF Name}" pro ETF
- In Sektor/Land/Währung: Verwendung der Gesamt-Allokation für "Other" Teil

### 3. Datenquellen-Hierarchie

**Neue Priorität:**
1. **ETF-Detail-Dateien** (strukturiert, vollständig)
2. **User CSV** (Legacy, Fallback)
3. **Mock-Daten** (statisch)
4. **API-Fetcher** (unzuverlässig)

## Migration

### Bestehende ETFs zu neuer Struktur migrieren:

**Für jeden ETF in `user_etf_holdings.csv`:**

1. Ticker-Symbol ermitteln (aus PP oder Börse)
2. ETF-Detail-Datei erstellen: `data/etf_details/{TICKER}.csv`
3. Metadata hinzufügen (ISIN, Name, Ticker, Type, Currency, TER)
4. Top 10-15 Holdings aus `user_etf_holdings.csv` kopieren
5. Sektor/Land/Währungs-Allokationen ergänzen (von ETF-Anbieter Website)
6. ISIN-Mapping in `etf_isin_ticker_map.csv` eintragen

**Datenquellen für Allokationen:**
- [justETF.com](https://www.justetf.com) - Beste Quelle für EU-ETFs
- [extraETF.com](https://extraetf.com)
- Offizielle ETF-Anbieter (iShares, Vanguard, Amundi, Xtrackers)

## Testing

**Getestet mit:**
- 6 ETFs erfolgreich migriert (AEEM, AUM5, GERD, VGWD, EUNL, XEON)
- Verschiedene ETF-Typen (Stock, Money Market)
- Verschiedene Regionen (World, EM, Europe, US)

**Zu testen:**
- [ ] Integration mit echtem Portfolio
- [ ] Fallback zu Legacy-Quellen funktioniert
- [ ] Korrekte Klassifizierung von Money Market ETFs
- [ ] "Other Holdings" wird korrekt zugeordnet

## Offene Aufgaben

1. **Migration restlicher ETFs:**
   - IE00B0M62Q58 - iShares MSCI World Quality Dividend ESG
   - IE00BJ0KDQ92 - Xtrackers MSCI World Quality Dividend
   - Weitere ETFs aus `user_etf_holdings.csv`

2. **Allokations-Nutzung:**
   - Implementierung der Nutzung von Country/Sector/Currency Allocations
   - Für "Other Holdings" Teil in Sektor/Land/Währung-Ansichten
   - Aktuell werden nur Top Holdings verwendet

3. **UI-Erweiterung:**
   - Web-Interface zum Pflegen von ETF-Detail-Dateien
   - Upload von ETF-Factsheets (PDF-Parsing?)
   - Automatische Extraktion von Allokationsdaten

4. **Validierung:**
   - Schema-Validierung für ETF-Detail-Dateien
   - Warnung bei fehlenden Allokationsdaten
   - Plausibilitätsprüfungen (Summe = 100%)

## Vorteile der neuen Struktur

✅ **Vollständigkeit:** Alle ETF-Daten an einem Ort
✅ **Struktur:** Klare Sections, einfach zu parsen
✅ **Wartbarkeit:** Eine Datei pro ETF, übersichtlich
✅ **Erweiterbar:** Einfach neue Felder hinzufügen (z.B. Replizierung, Ausschüttung)
✅ **Typ-Safety:** ETF-Typ explizit definiert
✅ **Allokationen:** Vollständige Sektor/Land/Währungsverteilungen
✅ **Konsistenz:** Einheitliches Format für alle ETFs

## Breaking Changes

⚠️ **Keine Breaking Changes!**

- Bestehende `user_etf_holdings.csv` wird weiterhin unterstützt (Fallback)
- Bisherige Datenquellen funktionieren weiter
- Neue Struktur ist optional, aber empfohlen

---

**Status:** ✅ Implementiert und dokumentiert
**Nächster Schritt:** Migration weiterer ETFs zu neuer Struktur
