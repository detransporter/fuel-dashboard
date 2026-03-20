# 🛢️ Fuel Market Dashboard

Realtids-dashboard för råolja, diesel och jetfuel. Live-data från FRED (Federal Reserve Bank of St. Louis).

## Instruments som visas
- **Brent Crude** — Global referenspris för råolja
- **WTI Crude** — West Texas Intermediate
- **US Diesel** — Retail dieselpris USA
- **Jet Fuel (Gulf Coast)** — Kerosen/jetfuel

## Snabbstart

### 1. Installera dependencies
```bash
cd fuel_dashboard
pip install -r requirements.txt
```

### 2. Skaffa gratis FRED API-nyckel (rekommenderas)
Gå till: https://fred.stlouisfed.org/docs/api/api_key.html
- Skapa gratis konto
- Generera API-nyckel
- Klistra in i dashboardens sidofält

> **OBS:** Utan API-nyckel visas simulerad data baserad på verkliga marknadsnivåer.

### 3. Starta dashboarden
```bash
streamlit run app.py
```

Öppnas automatiskt på: http://localhost:8501

## Funktioner
- ✅ Live-priser med %-förändring (1v / 1m)
- ✅ Interaktivt linjediagram med zoom
- ✅ Normaliserat index-läge (jämför relativ rörelse)
- ✅ 30-dagars rullande volatilitet
- ✅ Korrelationsmatris
- ✅ Rådata-tabell med heatmap
- ✅ Hormuz-krismarkering på grafen
- ✅ Mörkt, professionellt tema

## FRED Series IDs (öppna data)
| Instrument | Series ID |
|---|---|
| Brent Crude | DCOILBRENTEU |
| WTI Crude | DCOILWTICO |
| US Diesel | GASDESW |
| Jet Fuel Gulf Coast | WJFUELUSGULF |

## Anpassning
Redigera `SERIES`-dictionaryn i `app.py` för att lägga till fler instrument.
