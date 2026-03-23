"""
CityTwin OS — Carte interactive Casablanca
Affiche en temps réel les données IoT sur la vraie carte de Casablanca
"""

import sqlite3
import pandas as pd
import folium
import streamlit as st
from streamlit_folium import st_folium
from datetime import datetime
import time

# ─── Configuration ────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CityTwin OS · Carte",
    page_icon="🗺️",
    layout="wide"
)

DATABASE = "data/citytwin.db"

# Coordonnées réelles des zones de Casablanca
ZONES_COORDS = {
    "centre": {
        "lat": 33.5731, "lon": -7.5898,
        "label": "Centre-ville",
        "description": "Médina · Boulevard Mohammed V"
    },
    "maarif": {
        "lat": 33.5809, "lon": -7.6350,
        "label": "Maarif",
        "description": "Quartier résidentiel et commercial"
    },
    "ain-diab": {
        "lat": 33.5956, "lon": -7.6767,
        "label": "Ain Diab",
        "description": "Corniche · Bord de mer Atlantique"
    },
    "sidi-maarouf": {
        "lat": 33.5342, "lon": -7.6414,
        "label": "Sidi Maarouf",
        "description": "Zone industrielle · Casanearshore"
    },
}

# ─── Lecture SQLite ───────────────────────────────────────────────────────────

@st.cache_resource
def get_conn():
    return sqlite3.connect(DATABASE, check_same_thread=False)

def load_latest(table: str) -> pd.DataFrame:
    try:
        conn = get_conn()
        df = pd.read_sql_query(
            f"""SELECT * FROM {table}
                WHERE id IN (SELECT MAX(id) FROM {table} GROUP BY zone)""",
            conn
        )
        return df
    except:
        return pd.DataFrame()

# ─── Couleurs selon niveau ────────────────────────────────────────────────────

def pm25_color(pm25: float) -> str:
    if pm25 < 10:   return "#2ecc71"   # vert   — bon
    elif pm25 < 15: return "#f1c40f"   # jaune  — modéré
    elif pm25 < 25: return "#e67e22"   # orange — mauvais
    else:           return "#e74c3c"   # rouge  — dangereux

def congestion_color(level: str) -> str:
    return {"low": "#2ecc71", "medium": "#f1c40f", "high": "#e74c3c"}.get(level, "#95a5a6")

def pm25_label(pm25: float) -> str:
    if pm25 < 10:   return "🟢 Bon"
    elif pm25 < 15: return "🟡 Modéré"
    elif pm25 < 25: return "🟠 Mauvais"
    else:           return "🔴 Dangereux"

# ─── Construction de la carte ─────────────────────────────────────────────────

def build_map(df_air, df_traffic, df_energy, df_agents) -> folium.Map:

    # Carte centrée sur Casablanca
    m = folium.Map(
        location=[33.5731, -7.5898],
        zoom_start=12,
        tiles="CartoDB dark_matter"
    )

    for zone, coords in ZONES_COORDS.items():

        # Récupérer les données de cette zone
        air_row     = df_air[df_air["zone"] == zone].iloc[0]     if not df_air.empty     and zone in df_air["zone"].values     else None
        traf_row    = df_traffic[df_traffic["zone"] == zone].iloc[0] if not df_traffic.empty and zone in df_traffic["zone"].values else None
        energy_row  = df_energy[df_energy["zone"] == zone].iloc[0]  if not df_energy.empty  and zone in df_energy["zone"].values  else None
        agents_row  = df_agents[df_agents["zone"] == zone].iloc[0]  if not df_agents.empty  and zone in df_agents["zone"].values  else None

        # Couleur selon PM2.5
        pm25  = air_row["pm25"]               if air_row  is not None else 10.0
        color = pm25_color(pm25)

        # Taille du cercle selon population agents
        population = int(agents_row["population"]) if agents_row is not None else 10
        radius     = 300 + population * 30

        # ── Cercle de zone ──
        folium.Circle(
            location=[coords["lat"], coords["lon"]],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.3,
            weight=2,
        ).add_to(m)

        # ── Popup détaillé ──
        popup_html = f"""
        <div style="font-family: sans-serif; min-width: 220px; color: #333;">
            <h3 style="margin:0 0 8px; color:#2c3e50">{coords['label']}</h3>
            <p style="color:#7f8c8d; margin:0 0 10px; font-size:12px">{coords['description']}</p>
            <hr style="margin:8px 0">

            <b>💨 Qualité de l'air</b><br>
            PM2.5 : <b>{pm25} µg/m³</b> — {pm25_label(pm25)}<br>
            NO2 : {round(air_row['no2'], 1) if air_row is not None else '-'} µg/m³<br>
            Température : {air_row['temperature'] if air_row is not None else '-'}°C<br>
            Humidité : {air_row['humidity'] if air_row is not None else '-'}%<br>
            <hr style="margin:8px 0">

            <b>🚗 Trafic</b><br>
            Véhicules/min : <b>{int(traf_row['vehicles_per_min']) if traf_row is not None else '-'}</b><br>
            Vitesse : {traf_row['avg_speed_kmh'] if traf_row is not None else '-'} km/h<br>
            Congestion : <span style="color:{congestion_color(traf_row['congestion_level']) if traf_row is not None else '#95a5a6'}">
                ■ {traf_row['congestion_level'].upper() if traf_row is not None else '-'}
            </span><br>
            <hr style="margin:8px 0">

            <b>⚡ Énergie</b><br>
            Consommation : {round(energy_row['consumption_kw'], 1) if energy_row is not None else '-'} kW<br>
            Solaire : {round(energy_row['solar_production_kw'], 1) if energy_row is not None else '-'} kW<br>
            <hr style="margin:8px 0">

            <b>👥 Citoyens</b><br>
            Population : <b>{population}</b><br>
            Au travail : {int(agents_row['at_work']) if agents_row is not None else '-'}<br>
            En transport : {int(agents_row['in_transport']) if agents_row is not None else '-'}<br>
            Voitures : {int(agents_row['using_car']) if agents_row is not None else '-'}<br>
            Restés (pollution) : <b style="color:#e74c3c">{int(agents_row['stayed_home']) if agents_row is not None else '-'}</b>
        </div>
        """

        folium.Marker(
            location=[coords["lat"], coords["lon"]],
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=f"{coords['label']} · PM2.5={pm25} · {population} citoyens",
            icon=folium.DivIcon(
                html=f"""
                <div style="
                    background:{color};
                    border:2px solid white;
                    border-radius:50%;
                    width:16px; height:16px;
                    box-shadow: 0 0 8px {color};
                "></div>
                """,
                icon_size=(16, 16),
                icon_anchor=(8, 8)
            )
        ).add_to(m)

        # ── Label de zone ──
        folium.Marker(
            location=[coords["lat"] + 0.008, coords["lon"]],
            icon=folium.DivIcon(
                html=f"""
                <div style="
                    color:white;
                    font-size:11px;
                    font-weight:bold;
                    font-family:sans-serif;
                    text-shadow: 1px 1px 2px black;
                    white-space:nowrap;
                ">{coords['label']}</div>
                """,
                icon_size=(120, 20),
                icon_anchor=(60, 0)
            )
        ).add_to(m)

    # ── Légende ──
    legend_html = """
    <div style="
        position: fixed; bottom: 30px; left: 30px;
        background: rgba(0,0,0,0.8);
        border-radius: 8px; padding: 12px;
        color: white; font-family: sans-serif;
        font-size: 12px; z-index: 1000;
        border: 1px solid rgba(255,255,255,0.2);
    ">
        <b>🏙️ CityTwin OS · Casablanca</b><br><br>
        <b>Couleur = PM2.5</b><br>
        <span style="color:#2ecc71">■</span> Bon (&lt;10 µg/m³)<br>
        <span style="color:#f1c40f">■</span> Modéré (10-15)<br>
        <span style="color:#e67e22">■</span> Mauvais (15-25)<br>
        <span style="color:#e74c3c">■</span> Dangereux (&gt;25)<br><br>
        <b>Taille = Population</b><br>
        Cliquez sur un marqueur pour les détails
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m

# ─── Interface Streamlit ──────────────────────────────────────────────────────

st.title("🗺️ CityTwin OS — Carte temps réel")
st.caption("Casablanca · Jumeau numérique · Master CPS² · Université de Lyon")

# Sidebar
with st.sidebar:
    st.title("🗺️ Carte Casablanca")
    st.divider()
    auto_refresh = st.toggle("Rafraîchissement auto", value=True)
    if auto_refresh:
        refresh_rate = st.slider("Intervalle (secondes)", 10, 60, 15)
    st.divider()
    st.caption(f"Mise à jour : {datetime.now().strftime('%H:%M:%S')}")

# KPIs rapides
df_air     = load_latest("air_quality")
df_traffic = load_latest("traffic")
df_energy  = load_latest("energy")
df_agents  = load_latest("agents")

if not df_air.empty:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        avg_pm25 = round(df_air["pm25"].mean(), 1)
        st.metric("💨 PM2.5 moyen", f"{avg_pm25} µg/m³",
                  delta="⚠️ Élevé" if avg_pm25 > 15 else "✅ Bon",
                  delta_color="inverse" if avg_pm25 > 15 else "normal")
    with col2:
        worst = df_air.loc[df_air["pm25"].idxmax(), "zone"]
        st.metric("🔴 Zone la plus polluée", worst.capitalize())
    with col3:
        best = df_air.loc[df_air["pm25"].idxmin(), "zone"]
        st.metric("🟢 Zone la plus propre", best.capitalize())
    with col4:
        if not df_agents.empty:
            total_stayed = int(df_agents["stayed_home"].sum())
            st.metric("🏠 Restés (pollution)", total_stayed,
                      delta="⚠️ Pollution" if total_stayed > 5 else "✅ Normal",
                      delta_color="inverse" if total_stayed > 5 else "normal")

st.divider()

# Carte
m = build_map(df_air, df_traffic, df_energy, df_agents)
st_folium(m, width=None, height=600, returned_objects=[])

# Auto-refresh
if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
