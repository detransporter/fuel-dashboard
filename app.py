"""
Fuel Market Dashboard — Live data från EIA/FRED
Brent Crude · WTI · Diesel · Jet Fuel
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(page_title="Fuel Market Dashboard", page_icon="🛢️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;700;800&display=swap');
  html, body, [class*="css"] { font-family: 'Syne', sans-serif; background-color: #0a0e1a; color: #e8eaf0; }
  .main { background-color: #0a0e1a; }
  .metric-card { background: linear-gradient(135deg, #111827 0%, #1a2235 100%); border: 1px solid #2a3550; border-radius: 12px; padding: 20px 24px; margin-bottom: 12px; position: relative; overflow: hidden; }
  .metric-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--accent); }
  .metric-label { font-family: 'DM Mono', monospace; font-size: 11px; letter-spacing: 2px; text-transform: uppercase; color: #6b7fa3; margin-bottom: 6px; }
  .metric-value { font-size: 32px; font-weight: 800; color: #f0f4ff; line-height: 1.1; font-family: 'DM Mono', monospace; }
  .metric-delta-up   { color: #ef4444; font-size: 14px; font-family: 'DM Mono', monospace; }
  .metric-delta-down { color: #22c55e; font-size: 14px; font-family: 'DM Mono', monospace; }
  .metric-unit { font-size: 14px; color: #6b7fa3; margin-left: 4px; }
  .section-header { font-family: 'Syne', sans-serif; font-weight: 800; font-size: 13px; letter-spacing: 3px; text-transform: uppercase; color: #4a6fa5; border-bottom: 1px solid #1e2d45; padding-bottom: 8px; margin: 28px 0 16px 0; }
  .alert-box { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); border-left: 4px solid #ef4444; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; font-size: 13px; color: #fca5a5; }
  div[data-testid="metric-container"] { display: none; }
  footer { visibility: hidden; }
  #MainMenu { visibility: hidden; }
  h1 { font-family: 'Syne', sans-serif; font-weight: 800; color: #f0f4ff; }
</style>
""", unsafe_allow_html=True)

SERIES = {
    "Brent Crude ($/fat)":     {"ticker": "BZ=F", "fallback": "BRN=F", "unit": "$/fat", "color": "#f59e0b", "accent": "#f59e0b"},
    "WTI Crude ($/fat)":       {"ticker": "CL=F", "unit": "$/fat", "color": "#3b82f6", "accent": "#3b82f6"},
    "Diesel/ULSD ($/gallon)":  {"ticker": "HO=F", "unit": "$/gal", "color": "#8b5cf6", "accent": "#8b5cf6"},
    "Gasoline RBOB ($/gallon)":{"ticker": "RB=F", "unit": "$/gal", "color": "#06b6d4", "accent": "#06b6d4"},
}

SIM_PARAMS = {
    "Brent Crude ($/fat)":     {"s": 62,   "e": 94,   "v": 0.018},
    "WTI Crude ($/fat)":       {"s": 59,   "e": 91,   "v": 0.019},
    "Diesel/ULSD ($/gallon)":  {"s": 3.53, "e": 5.07, "v": 0.012},
    "Gasoline RBOB ($/gallon)":{"s": 2.10, "e": 3.20, "v": 0.015},
}

PERIODS = {
    "1D": {"days": 1,   "label": "1 dag",   "ds": 1,  "dl": 7},
    "1V": {"days": 7,   "label": "1 vecka", "ds": 1,  "dl": 7},
    "1M": {"days": 30,  "label": "1 månad", "ds": 7,  "dl": 30},
    "1Å": {"days": 365, "label": "1 år",    "ds": 7,  "dl": 30},
}

@st.cache_data(ttl=3600)
def fetch_yfinance(ticker, start_date):
    try:
        hist = yf.Ticker(ticker).history(start=start_date)
        if hist.empty:
            return None
        df = hist[["Close"]].rename(columns={"Close": "value"})
        df.index = df.index.tz_localize(None)
        df = df.resample("D").last().ffill()
        return df
    except Exception:
        return None

@st.cache_data(ttl=3600)
def fetch_fred_brent(api_key, start_date):
    try:
        r = requests.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={
                "series_id": "DCOILBRENTEU",
                "observation_start": start_date,
                "api_key": api_key,
                "file_type": "json",
            },
            timeout=10,
        )
        r.raise_for_status()
        obs = r.json().get("observations", [])
        df = pd.DataFrame(obs)[["date", "value"]]
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["value"])
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").resample("D").last().ffill()
        return df if not df.empty else None
    except Exception:
        return None

def pct_change(series, days):
    if len(series) < 2:
        return None
    recent = series.iloc[-1]
    past = series.iloc[max(0, len(series) - days)]
    return ((recent - past) / past) * 100 if past != 0 else None

def metric_card(label, value, unit, d1, d2, accent):
    vs = f"{value:,.2f}" if value is not None else "N/A"
    def dh(d, lbl):
        if d is None: return f'<span style="color:#6b7fa3">{lbl}: –</span>'
        cls = "metric-delta-up" if d > 0 else "metric-delta-down"
        return f'<span class="{cls}">{"▲" if d>0 else "▼"} {abs(d):.1f}% {lbl}</span>'
    st.markdown(f"""<div class="metric-card" style="--accent:{accent}">
      <div class="metric-label">{label}</div>
      <div class="metric-value">{vs}<span class="metric-unit">{unit}</span></div>
      <div style="margin-top:8px;display:flex;gap:16px;flex-wrap:wrap;">{dh(d1,"kort")}{dh(d2,"lång")}</div>
    </div>""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛢️ Fuel Dashboard")
    st.markdown("---")
    st.markdown("<div style='font-family:DM Mono,monospace;font-size:11px;color:#4a6fa5;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px'>Tidsperiod</div>", unsafe_allow_html=True)

    pkeys = list(PERIODS.keys())
    pidx  = st.radio("p", range(len(pkeys)), format_func=lambda i: pkeys[i],
                     index=3, horizontal=True, label_visibility="collapsed")
    pcfg  = PERIODS[pkeys[pidx]]
    days_back      = pcfg["days"]
    start_display  = (datetime.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    start_fetch    = (datetime.today() - timedelta(days=max(days_back+60, 90))).strftime("%Y-%m-%d")

    st.markdown("---")
    selected = st.multiselect("Visa instrument", list(SERIES.keys()), default=list(SERIES.keys()))
    st.markdown("---")
    show_corr = st.checkbox("Visa korrelationsmatris", value=True)
    show_vol  = st.checkbox("Visa volatilitet (30d rullande)", value=True)
    st.markdown("---")
    st.markdown(f"<div style='font-family:DM Mono,monospace;font-size:11px;color:#4a6fa5;line-height:1.8'>Datakälla: Yahoo Finance · yfinance<br>Uppdateras: 1h<br>Senast: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown(f"<h1 style='margin-bottom:4px'>Fuel Market Dashboard</h1><div style='font-family:DM Mono,monospace;font-size:12px;color:#4a6fa5;margin-bottom:24px'>BRENT · WTI · DIESEL/ULSD · GASOLINE RBOB — VY: {pcfg['label'].upper()}</div>", unsafe_allow_html=True)
st.markdown("<div class='alert-box'>⚠️ <strong>MARS 2026:</strong> Hormuzsundet stängt sedan 28 feb. Brent +50% YTD · Diesel +44% sedan jan · Jet fuel +11% v/v. IEA frigjorde 400 Mb från strategiska reserver.</div>", unsafe_allow_html=True)

# ── Fetch data ────────────────────────────────────────────────────────────────
full_store: dict = {}
disp_store: dict = {}

simulated_names = []

fred_api_key = st.secrets.get("FRED_API_KEY", "")

with st.spinner("Hämtar data..."):
    for name in selected:
        meta = SERIES[name]
        df = None

        # Brent: FRED primär, yfinance fallback
        if name == "Brent Crude ($/fat)" and fred_api_key:
            df = fetch_fred_brent(fred_api_key, start_fetch)

        # Övriga (och Brent-fallback): yfinance
        if df is None or df.empty:
            df = fetch_yfinance(meta["ticker"], start_fetch)
        if (df is None or df.empty) and "fallback" in meta:
            df = fetch_yfinance(meta["fallback"], start_fetch)

        if df is not None and not df.empty:
            full_store[name] = df
            disp_store[name] = df[df.index >= pd.to_datetime(start_display)]

# Per-instrument simulated fallback for any that still failed
np.random.seed(42)
sim_dates = pd.date_range(start=(datetime.today()-timedelta(days=365)).strftime("%Y-%m-%d"), end=datetime.today(), freq="B")
n = len(sim_dates)

for name in selected:
    if name not in full_store and name in SIM_PARAMS:
        p = SIM_PARAMS[name]
        t = np.linspace(p["s"], p["e"], n)
        noise = np.cumsum(np.random.normal(0, p["v"], n)) * p["s"]
        vals = t + noise * 0.3
        sp = max(0, n-18)
        vals[sp:] *= np.linspace(1.0, 1.12, n-sp)
        df = pd.DataFrame({"value": vals}, index=sim_dates)
        full_store[name] = df
        disp_store[name] = df[df.index >= pd.to_datetime(start_display)]
        simulated_names.append(name)

if simulated_names:
    st.warning(f"**Visar simulerad data** för: {', '.join(simulated_names)}. Live-hämtning misslyckades temporärt.")

# ── KPI cards ─────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Senaste priser</div>', unsafe_allow_html=True)
cols = st.columns(max(len(selected), 1))
for i, name in enumerate(selected):
    if name not in full_store: continue
    df_f = full_store[name]
    meta = SERIES[name]
    with cols[i]:
        metric_card(name, df_f["value"].iloc[-1] if not df_f.empty else None,
                    meta["unit"],
                    pct_change(df_f["value"], pcfg["ds"]),
                    pct_change(df_f["value"], pcfg["dl"]),
                    meta["accent"])

# ── Price chart ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Prisutveckling</div>', unsafe_allow_html=True)

if disp_store:
    normalize = st.toggle("Normalisera till index (start = 100)", value=False)
    fig = go.Figure()
    for name in selected:
        if name not in disp_store or disp_store[name].empty: continue
        df   = disp_store[name]
        meta = SERIES[name]
        vals = df["value"].copy()
        if normalize:
            vals = (vals / vals.iloc[0]) * 100
            hsuffix = " (index)"
        else:
            hsuffix = f" {meta['unit']}"
        mode = "lines+markers" if days_back <= 7 else "lines"
        fig.add_trace(go.Scatter(
            x=df.index, y=vals, name=name, mode=mode,
            line=dict(color=meta["color"], width=2.5),
            marker=dict(size=6) if days_back <= 7 else dict(size=0),
            hovertemplate=f"<b>{name}</b><br>%{{x|%Y-%m-%d}}<br>%{{y:.2f}}{hsuffix}<extra></extra>",
        ))

    # Hormuz marker (only if within display window)
    crisis = "2026-02-28"
    if pd.to_datetime(crisis) >= pd.to_datetime(start_display):
        fig.add_shape(type="line", x0=crisis, x1=crisis, y0=0, y1=1,
                      xref="x", yref="paper", line=dict(color="#ef4444", width=1.5, dash="dot"))
        fig.add_annotation(x=crisis, y=0.97, xref="x", yref="paper",
                           text="⚠ Hormuz-krisen", showarrow=False,
                           font=dict(color="#ef4444", size=11, family="DM Mono, monospace"),
                           xanchor="left", bgcolor="rgba(10,14,26,0.7)", borderpad=4)

    fig.update_layout(
        paper_bgcolor="#f8fafc", plot_bgcolor="#ffffff",
        font=dict(family="DM Mono, monospace", color="#334155", size=11),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor="#e2e8f0", linecolor="#e2e8f0", showgrid=True),
        yaxis=dict(gridcolor="#e2e8f0", linecolor="#e2e8f0", showgrid=True,
                   title="Pris (normaliserat)" if normalize else "Pris"),
        hovermode="x unified", height=420, margin=dict(l=60, r=20, t=40, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Volatility ────────────────────────────────────────────────────────────────
if show_vol and full_store:
    st.markdown('<div class="section-header">30-dagars rullande volatilitet (std dev %)</div>', unsafe_allow_html=True)
    fig_v = go.Figure()
    for name in selected:
        if name not in full_store: continue
        meta = SERIES[name]
        vol = (full_store[name]["value"].pct_change()*100).rolling(30).std()
        vol = vol[vol.index >= pd.to_datetime(start_display)]
        if vol.dropna().empty: continue
        fig_v.add_trace(go.Scatter(x=vol.index, y=vol, name=name,
                                   line=dict(color=meta["color"], width=2),
                                   hovertemplate=f"<b>{name}</b><br>%{{x|%Y-%m-%d}}<br>%{{y:.2f}}%<extra></extra>"))
    fig_v.update_layout(paper_bgcolor="#f8fafc", plot_bgcolor="#ffffff",
                        font=dict(family="DM Mono, monospace", color="#334155", size=11),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)"),
                        xaxis=dict(gridcolor="#e2e8f0", linecolor="#e2e8f0"),
                        yaxis=dict(gridcolor="#e2e8f0", linecolor="#e2e8f0", title="Std dev (%)"),
                        height=280, margin=dict(l=60, r=20, t=40, b=40))
    st.plotly_chart(fig_v, use_container_width=True)

# ── Correlation ───────────────────────────────────────────────────────────────
if show_corr and len(full_store) >= 2:
    st.markdown('<div class="section-header">Korrelationsmatris (dagliga prisförändringar)</div>', unsafe_allow_html=True)
    combined = pd.DataFrame({n: full_store[n]["value"] for n in selected if n in full_store}).dropna()
    corr = combined.pct_change().corr()
    short = {n: n.split(" (")[0] for n in corr.columns}
    corr.columns = [short[c] for c in corr.columns]
    corr.index   = [short[c] for c in corr.index]
    fig_c = go.Figure(go.Heatmap(z=corr.values, x=corr.columns.tolist(), y=corr.index.tolist(),
                                  colorscale=[[0,"#dbeafe"],[0.5,"#f1f5f9"],[1,"#f59e0b"]],
                                  zmin=-1, zmax=1, text=[[f"{v:.2f}" for v in row] for row in corr.values],
                                  texttemplate="%{text}", textfont=dict(family="DM Mono,monospace",size=13,color="#1e293b"), showscale=True))
    fig_c.update_layout(paper_bgcolor="#f8fafc", plot_bgcolor="#ffffff",
                        font=dict(family="DM Mono,monospace",color="#334155",size=12),
                        height=320, margin=dict(l=20,r=20,t=20,b=20))
    st.plotly_chart(fig_c, use_container_width=True)

# ── Raw data ──────────────────────────────────────────────────────────────────
with st.expander("📊 Rådata (vald period)"):
    raw = pd.DataFrame({n: disp_store[n]["value"] for n in selected if n in disp_store})
    if not raw.empty:
        st.dataframe(raw.tail(50).style.format("{:.2f}").background_gradient(cmap="YlOrRd", axis=0), use_container_width=True)

st.markdown(f"<hr style='border-color:#1a2540;margin-top:40px'><div style='font-family:DM Mono,monospace;font-size:11px;color:#2d3f5f;text-align:center;padding:16px'>Datakälla: Yahoo Finance · yfinance — SCM International · {datetime.now().strftime('%Y')}</div>", unsafe_allow_html=True)
