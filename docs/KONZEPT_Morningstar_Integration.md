# Konzept: Integration von pp-portfolio-classifier / Morningstar-API für ClusterRisk

**Stand:** 2026-03-02  
**Referenz:** [pp-portfolio-classifier (new-api-branch)](https://github.com/Alfons1Qto12/pp-portfolio-classifier/tree/new-api-branch)

---

## 1. Ausgangslage

### 1.1 ClusterRisk heute

- **Input:** Vermögensaufstellung aus Portfolio Performance (CSV).
- **ETF-Auflösung:** Priorität 1 = **ETF-Detail-Dateien** (`data/etf_details/{TICKER}.csv`), Priorität 2 = **API-Fetcher** (justETF-Scraping, extraETF, iShares, Yahoo Finance).
- **ETF-Detail-Format:** Pro ETF eine CSV mit Metadata, Country/Sector/Currency Allocation und Top Holdings (Name, Weight, Currency, Sector, Country, ISIN).
- **Generierung:** justETF-Scraper in `etf_detail_generator.py`; bei Swap-ETFs optional Proxy-ISIN.

### 1.2 Was pp-portfolio-classifier bietet

Das Projekt nutzt die **Morningstar EMEA Direct Web API** (ISIN-basiert, gut dokumentiert):

- **Eine API pro ISIN:** `https://www.emea-api.morningstar.com/ecint/v1/securities/{isin}` mit Parametern `idtype=ISIN`, `viewid=ITsnapshot` (bzw. `Top10`/`Top25`/`Allholdings` für Holdings).
- **Kein API-Key:** Bearer-Token wird aus der Morningstar-Webseite (z. B. morningstar.de) aus einer Session gelesen.
- **Daten pro Fonds/ETF:**
  - **Asset Type** (Stocks, Bonds, Cash, Other)
  - **Stock Style** (Large/Mid/Small, Value/Blend/Growth)
  - **Stock Sector** (Technology, Financial Services, …) – GICS-ähnlich
  - **Bond Style / Bond Sector** (für Renten-ETFs)
  - **Region** (North America, Europe Developed, Japan, …)
  - **Country** (feine Länderverteilung, viele Länder)
  - **Holdings** (SecurityName, Weighting, ISIN) – Anzahl konfigurierbar (0, 10, 25, 50, 100, 1000, 3200)
- **Aktien:** Klassifikation für Einzelaktien (Sektor, Region, Land) über dieselbe API bzw. SAL-Service.
- **Zusätzlich:** Optionale Berechnung der deutschen Vorabpauschale; Export in `pp_data_fetched.csv` (ISIN, Taxonomy, Classification, Percentage, Name).

**Vorteile für uns:**

- **Stabilere Datenquelle:** Dokumentierte API statt Web-Scraping.
- **ISIN als Schlüssel:** Passt zu unserem Workflow (ISIN aus PP-CSV → Auflösung).
- **Mehr Länder/Sektoren:** Morningstar liefert viele Länder und ein klares Sektor-Schema.
- **Renten-ETFs:** Bond Style/Sector und Country/Region für Anleihen-ETFs.
- **Viele Holdings:** Bis 3200 Holdings pro Fonds möglich (für uns z. B. 50–100 sinnvoll).
- **Einheitliche Taxonomie:** Gleiche Begriffe für Sektor/Region/Country wie in vielen PP-Setups.

---

## 2. Ziele der Integration

1. **ETF-Datenqualität verbessern:** Morningstar als weitere (oder primäre) Quelle für ETF-Detail-Daten.
2. **Abdeckung erweitern:** ETFs/Fonds, die bei justETF fehlen oder unvollständig sind, über Morningstar abdecken.
3. **Renten-ETFs:** Bond-ETFs sauber nach Anlageklasse/Sektor/Land auflösen.
4. **Optional:** Einzelaktien mit Sektor/Region/Land aus Morningstar anreichern (z. B. für `ticker_sector_mapper` oder zukünftige Erweiterungen).

---

## 3. Zwei Integrationspfade

### Option A: pp-portfolio-classifier als externes Tool („CSV-Brücke“) ✅ umgesetzt

**Idee:** pp-portfolio-classifier läuft getrennt; ClusterRisk liest dessen Ausgabe und erzeugt daraus unsere ETF-Detail-CSVs.

**Ablauf:**

1. User legt eine PP-XML-Kopie (oder eine Minimal-XML nur mit den relevanten Wertpapieren) an.
2. User führt aus:  
   `python portfolio-classifier.py portfolio.xml -top_holdings 50 -bonds_in_funds`
3. Das Script erzeugt `pp_data_fetched.csv` (Format: `ISIN,Taxonomy,Classification,Percentage,Name`).
4. **Neues ClusterRisk-Modul:** z. B. `src/morningstar_csv_importer.py`:
   - Liest `pp_data_fetched.csv`.
   - Gruppiert nach ISIN.
   - Mappt Taxonomien auf unser Format (s. Abschnitt 4).
   - Schreibt/aktualisiert `data/etf_details/{TICKER}.csv` (Ticker aus `etf_isin_ticker_map.csv`).

**Vorteile:**

- Keine Änderung an der Morningstar-/PP-Logik; Nutzung des bestehenden, gepflegten Scripts.
- Kein Bearer-Token-Handling in ClusterRisk.
- Einfacher erster Schritt.

**Nachteile:**

- Zwei Schritte für den User (Classifier laufen lassen, dann ClusterRisk).
- Abhängigkeit von PP-XML; reine „nur ISIN-Liste“-Nutzung erfordert ggf. eine Dummy-XML.
- Holdings in `pp_data_fetched.csv` sind nur als „Holding“-Taxonomy mit Classification=SecurityName, Percentage=Weight – weitere Felder (ISIN, Sector, Country pro Holding) müssten ggf. aus dem Script ausgegeben oder anders bezogen werden.

**Geeignet für:** Schnellen Nutzen ohne Python-Refactoring im Classifier; wenn User ohnehin mit PP-XML arbeitet.

**Implementierung (Stand 2026-03-02):** Modul `src/morningstar_csv_importer.py`; Aufruf per CLI (`python -m src.morningstar_csv_importer [pp_data_fetched.csv]`) oder in der Streamlit-Sidebar unter „🔄 ETF-Details“ → „📥 Aus Morningstar (pp-portfolio-classifier) importieren“ (Datei-Upload).

---

### Option B: Morningstar-API direkt in ClusterRisk (empfohlen für langfristige Qualität)

**Idee:** Die gleiche Morningstar-API wie im pp-portfolio-classifier in ClusterRisk nutzen – als neuer Fetcher, der unser bestehendes ETF-Detail-Format befüllt.

**Ablauf:**

1. **Neues Modul** `src/morningstar_fetcher.py` (oder Erweiterung von `etf_data_fetcher.py`):
   - Bearer-Token von Morningstar-Webseite besorgen (wie im Classifier).
   - Für gegebene ISIN: Aufruf  
     `GET https://www.emea-api.morningstar.com/ecint/v1/securities/{isin}`  
     mit `viewid=ITsnapshot`, ggf. weitere Aufrufe für Holdings mit `viewid=Top25`/`Allholdings` und Limit 50/100.
   - Response (JSON) parsen: Asset Allocations, GlobalStockSectorBreakdown, RegionalExposure, CountryExposure, PortfolioHoldings.
   - Mapping auf unsere Struktur (Metadata, Country/Sector/Currency Allocation, Top Holdings).
2. **Priorität in `risk_calculator.py` / ETF-Auflösung:**
   - Weiter: 1) ETF-Detail-Datei, 2) **neu:** Morningstar (wenn kein lokales CSV oder User wünscht „immer frische Daten“), 3) justETF/andere Fetcher.
   - Oder konfigurierbar: „Quelle für ETF-Daten: Lokal → Morningstar → justETF …“.
3. **ETF-Detail-Generator (Streamlit):** Optional „Von Morningstar laden“-Button: ISIN (+ Ticker) eingeben → Morningstar abfragen → gleiche CSV-Struktur wie justETF-Generator schreiben (inkl. Proxy-ISIN-Logik nur wo nötig).

**Vorteile:**

- Eine Umgebung (ClusterRisk), ein Workflow.
- Volle Kontrolle über Mapping und Format; Holdings können mit ISIN/Sektor/Land angereichert werden (aus API-Response).
- Kann als Fallback oder Hauptquelle für ETFs dienen; Renten-ETFs direkt unterstützt.
- Später: gleiche API für Aktien-Klassifikation (Sektor/Region/Country) nutzbar.

**Nachteile:**

- Implementierungsaufwand (Token-Handling, JSON-Pfade, Mappings).
- Rechtliche/Nutzungsbedingungen der Morningstar-API prüfen (gleiche wie beim Classifier).

**Geeignet für:** Saubere, nachhaltige Integration und beste UX.

---

## 4. Daten-Mapping Morningstar → ClusterRisk

### 4.1 Taxonomie-Mapping

| Morningstar (pp-portfolio-classifier) | ClusterRisk ETF-Detail-CSV |
|--------------------------------------|----------------------------|
| **Asset Type** (1=Stocks, 3=Bonds, 7=Cash, …) | Metadata `Type`: Stock, Bond, Money Market, Commodity |
| **Stock Sector** (101–311, map_stock_sector_1) | Sector Allocation; Namen normalisieren (s. u.) |
| **Region** (map_region_1 / map_region_2) | Nur indirekt; Country bleibt primär |
| **Country** (ISO-3 oder -2, map_country_1) | Country Allocation; Länderbezeichnungen vereinheitlichen |
| **Holding** (SecurityName, Weighting, ggf. ISIN) | Top Holdings: Name, Weight; Currency/Sector/Country aus ISIN-Lookup oder aus API wenn vorhanden |

### 4.2 Sektor-Normalisierung

Morningstar (GICS-ähnlich) → unsere Bezeichnungen (inkl. bestehende `_normalize_sector_name`):

- Basic Materials → Basic Materials / Rohstoffe
- Consumer Cyclical → Consumer Discretionary / Cyclical
- Consumer Defensive → Consumer Staples
- Financial Services → Financials
- Communication Services → Telecommunication / Communication
- Real Estate, Healthcare, Technology, etc. → direkt oder 1:1 übernehmen und in `_normalize_sector_name` ergänzen.

Bestehende Normalisierung in `risk_calculator._normalize_sector_name` erweitern, damit beide Quellen (justETF + Morningstar) auf dieselben Sektor-Labels abgebildet werden.

### 4.3 Währungs-Allokation

Morningstar liefert **keine** explizite Currency Allocation. Wie bei justETF:

- **Country Allocation** nutzen und über festes **Country → Currency**-Mapping (wie in `etf_detail_generator.COUNTRY_TO_CURRENCY`) die Currency Allocation ableiten.
- Optional: Für Holdings mit ISIN die Handelswährung aus ISIN/Land ableiten und Top-Holdings-Währungen für „Other Holdings“ verwenden.

### 4.4 Holdings

- **Name:** SecurityName aus `PortfolioHoldings`.
- **Weight:** Weighting (in %); ggf. von „long equity“ auf „net“ umrechnen (Classifier macht das bereits).
- **ISIN:** Wenn in der API pro Holding vorhanden, übernehmen; sonst leer oder nachträglich per OpenFIGI/Yahoo ergänzen.
- **Currency/Sector/Country:** Aus API wenn vorhanden; sonst aus ISIN (erste 2 Zeichen = Land) und unserem Sektor-Cache.

---

## 5. Implementierungs-Vorschläge

### Phase 1 – CSV-Brücke (Option A, geringer Aufwand)

1. **`src/morningstar_csv_importer.py`** (neu):
   - Eingabe: Pfad zu `pp_data_fetched.csv` (nach Lauf von pp-portfolio-classifier).
   - ISIN → Ticker über `data/etf_isin_ticker_map.csv`.
   - Zeilen nach ISIN/Taxonomy gruppieren, in unsere Section-Struktur (Metadata, Country, Sector, Currency, Holdings) überführen.
   - Schreiben von `data/etf_details/{TICKER}.csv` im bestehenden Format.
2. **Dokumentation:** In README/CLAUDE.md beschreiben: „ETF-Daten aus Morningstar: pp-portfolio-classifier ausführen, dann Importer auf `pp_data_fetched.csv` anwenden.“

**Einschränkung:** `pp_data_fetched.csv` enthält pro Holding nur „Holding“ als Taxonomy mit Name und Percentage; ISIN/Sektor pro Holding fehlen in der CSV. Für Phase 1 reicht das für Top-Holdings-Namen und Gewichte; Sektor/Land/Currency für „Other“ aus Country/Sector Allocation.

### Phase 2 – Direkte API (Option B)

1. **`src/morningstar_fetcher.py`** (neu):
   - Token-Beschaffung (wie im Classifier: Request an morningstar.de, Regex auf `maasToken`).
   - GET `ecint/v1/securities/{isin}` mit viewid ITsnapshot; optional zweiter Aufruf mit viewid für Holdings (Top25/Allholdings, Limit z. B. 50).
   - JSON mit jsonpath oder festen Pfaden auswerten (Referenz: taxonomies-Dict im Classifier).
   - Rückgabe als Dict im **gleichen** Format wie `etf_details_parser.parse_etf_file()` (bzw. wie von `etf_detail_generator` erzeugt).
2. **Integration in `risk_calculator._expand_etf_holdings`:**
   - Nach „ETF-Detail-Datei nicht gefunden“: Optional Morningstar aufrufen; bei Erfolg Ergebnis cachen (z. B. als temporäre ETF-Detail-Datei oder in-memory) und wie eine Detail-Datei verwenden.
3. **Streamlit:** Im ETF-Detail-Generator eine Quelle „Morningstar“ anbieten (neben justETF); gleiche CSV-Ausgabe wie bisher.

### Phase 3 – Optional

- **Renten-ETFs:** Bond Style/Sector in Metadata oder eigene Section, falls wir Anlageklassen-Darstellung verfeinern wollen.
- **Aktien:** Morningstar für Einzelaktien (Sektor/Region/Country) anbinden und in `ticker_sector_mapper` oder Risiko-Logik nutzen.
- **Proxy-ISIN:** Bei Swap-ETFs in ClusterRisk Proxy-ISIN hinterlegen; Morningstar-Fetcher ruft mit Proxy-ISIN auf (wie Classifier #PPC:ISIN2).

---

## 6. Abhängigkeiten und Risiken

### 6.1 Abhängigkeiten

- **pp-portfolio-classifier (Option A):** Python 3, `requests`, `jsonpath_ng`, `beautifulsoup4`, `jinja2`, `requests_cache`. Kein API-Key.
- **Option B:** In ClusterRisk nur `requests` (und ggf. `jsonpath_ng` oder reines JSON-Parsing). Kein API-Key; Token aus Webseite.

### 6.2 Rechtliches / Nutzungsbedingungen

- Morningstar-API ist über die öffentliche Webseite (Bearer aus Session) nutzbar; dennoch: **Nutzungsbedingungen und robots.txt von Morningstar prüfen** und respektieren.
- Rate-Limiting: Wie im Classifier mit Cache (z. B. 2 Minuten requests_cache); bei uns zusätzlich persistenter Cache (z. B. 7 Tage wie bei anderen Fetcher) und sparsame Abfragen (nur bei fehlender Detail-Datei oder auf Knopfdruck).

### 6.3 Technische Risiken

- **API-Änderungen:** Morningstar könnte Pfade/Parameter ändern. Durch Nutzung der gleichen API wie der aktiv gepflegte Classifier ist das Risiko begrenzt; trotzdem Abstraktion (eigenes Modul) und Unit-Tests mit gespeicherten Response-Samples.
- **Token abgelaufen:** Token-Handling robust implementieren (Refresh bei 401, klare Fehlermeldung für den User).

---

## 7. Empfehlung

- **Kurzfristig:** **Phase 1 (Option A)** umsetzen – `morningstar_csv_importer.py` für `pp_data_fetched.csv`. Geringer Aufwand, sofort Nutzen für Nutzer, die den Classifier ohnehin verwenden oder ausprobieren wollen.
- **Mittelfristig:** **Phase 2 (Option B)** anvisieren – direkter Morningstar-Fetcher in ClusterRisk, als zweite Quelle nach lokalen ETF-Detail-Dateien. So wird die Abdeckung und Stabilität der ETF-Daten spürbar verbessert, ohne den User durch ein zweites Tool zu führen.
- **Dokumentation:** In CLAUDE.md und README beide Wege („ETF-Daten aus justETF“, „ETF-Daten aus Morningstar (Classifier oder integrierter Fetcher)“) beschreiben und das Sektor-/Länder-Mapping zentral dokumentieren.

---

## 8. Referenzen

- [pp-portfolio-classifier, new-api-branch](https://github.com/Alfons1Qto12/pp-portfolio-classifier/tree/new-api-branch)
- [Morningstar Direct Web Services – Investment Details](https://developer.morningstar.com/direct-web-services/documentation/direct-web-services/security-details/investment-details)
- ClusterRisk: `CLAUDE.md`, `src/etf_detail_generator.py`, `src/etf_details_parser.py`, `src/risk_calculator.py` (Priorität ETF-Daten, Sektor-Normalisierung)
