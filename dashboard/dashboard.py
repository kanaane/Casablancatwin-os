"""
CityTwin OS — Module 3 : Dashboard Streamlit
Affiche en temps réel les données IoT de la ville intelligente
"""

import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

# ─── Configuration page ───────────────────────────────────────────────────────

st.set_page_config(
    page_title="CityTwin OS",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .metric-card {
        background: #1e1e2e;
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid #313244;
    }
    .alert-high   { color: #f38ba8; font-weight: bold; }
    .alert-medium { color: #fab387; font-weight: bold; }
    .alert-normal { color: #a6e3a1; }
    h1 { color: #cdd6f4 !important; }
    .stMetric { background: #1e1e2e; border-radius: 8px; padding: 0.5rem; }
</style>
""", unsafe_allow_html=True)

DATABASE = "data/citytwin.db"

# ─── Fonctions de lecture SQLite ──────────────────────────────────────────────

@st.cache_resource
def get_connection():
    return sqlite3.connect(DATABASE, check_same_thread=False)

def load_data(table: str, limit: int = 200) -> pd.DataFrame:
    try:
        conn = get_connection()
        df = pd.read_sql_query(
            f"SELECT * FROM {table} ORDER BY id DESC LIMIT {limit}",
            conn
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df.sort_values("timestamp")
    except Exception as e:
        st.error(f"Erreur lecture {table} : {e}")
        return pd.DataFrame()

def load_latest(table: str) -> pd.DataFrame:
    """Dernière mesure par zone"""
    try:
        conn = get_connection()
        df = pd.read_sql_query(
            f"""SELECT * FROM {table}
                WHERE id IN (
                    SELECT MAX(id) FROM {table} GROUP BY zone
                )""",
            conn
        )
        return df
    except:
        return pd.DataFrame()

def count_alerts() -> dict:
    """Compte les anomalies dans les dernières 50 mesures"""
    alerts = {"air": 0, "traffic": 0, "noise": 0, "energy": 0}
    try:
        conn = get_connection()
        alerts["air"]     = pd.read_sql_query("SELECT COUNT(*) as n FROM air_quality WHERE pm25 > 20 ORDER BY id DESC LIMIT 50", conn)["n"][0]
        alerts["traffic"] = pd.read_sql_query("SELECT COUNT(*) as n FROM traffic WHERE congestion_level='high' ORDER BY id DESC LIMIT 50", conn)["n"][0]
        alerts["noise"]   = pd.read_sql_query("SELECT COUNT(*) as n FROM noise WHERE level='critical' ORDER BY id DESC LIMIT 50", conn)["n"][0]
        alerts["energy"]  = pd.read_sql_query("SELECT COUNT(*) as n FROM energy WHERE net_kw > 400 ORDER BY id DESC LIMIT 50", conn)["n"][0]
    except:
        pass
    return alerts

# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🏙️ CityTwin OS")
    st.caption("Jumeau numérique · Ville intelligente")
    st.divider()

    # Sélection de zone
    zones = ["Toutes les zones", "centre-ville", "quartier-nord", "quartier-sud", "zone-industrielle"]
    selected_zone = st.selectbox("Zone", zones)

    # Nombre de mesures
    n_points = st.slider("Historique (mesures)", 50, 500, 100)

    # Rafraîchissement automatique
    auto_refresh = st.toggle("Rafraîchissement auto", value=True)
    if auto_refresh:
        refresh_rate = st.slider("Intervalle (secondes)", 2, 30, 5)

    st.divider()
    st.caption(f"Dernière mise à jour : {datetime.now().strftime('%H:%M:%S')}")

# ─── Chargement des données ───────────────────────────────────────────────────

df_air     = load_data("air_quality", n_points)
df_traffic = load_data("traffic", n_points)
df_energy  = load_data("energy", n_points)
df_noise   = load_data("noise", n_points)

# Filtre par zone
if selected_zone != "Toutes les zones":
    df_air     = df_air[df_air["zone"] == selected_zone]
    df_traffic = df_traffic[df_traffic["zone"] == selected_zone]
    df_energy  = df_energy[df_energy["zone"] == selected_zone]
    df_noise   = df_noise[df_noise["zone"] == selected_zone]

latest_air     = load_latest("air_quality")
latest_traffic = load_latest("traffic")
latest_energy  = load_latest("energy")
alerts         = count_alerts()

# ─── Header ───────────────────────────────────────────────────────────────────

st.title("🏙️ CityTwin OS — Dashboard")
st.caption("Système de surveillance IoT en temps réel · Master CPS² · Université de Lyon")
st.divider()

# ─── KPIs principaux ──────────────────────────────────────────────────────────

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total = len(df_air) + len(df_traffic) + len(df_energy) + len(df_noise)
    st.metric("📡 Mesures totales", f"{total:,}", help="Nombre de mesures dans la base")

with col2:
    avg_pm25 = round(df_air["pm25"].mean(), 1) if not df_air.empty else 0
    delta_color = "inverse" if avg_pm25 > 15 else "normal"
    st.metric("💨 PM2.5 moyen", f"{avg_pm25} µg/m³", delta="⚠️ Élevé" if avg_pm25 > 15 else "✅ Normal", delta_color=delta_color)

with col3:
    avg_vehicles = int(df_traffic["vehicles_per_min"].mean()) if not df_traffic.empty else 0
    st.metric("🚗 Véhicules/min", avg_vehicles, help="Moyenne sur toutes les zones")

with col4:
    avg_energy = round(df_energy["consumption_kw"].mean(), 1) if not df_energy.empty else 0
    st.metric("⚡ Consommation", f"{avg_energy} kW", help="Consommation moyenne")

with col5:
    total_alerts = sum(alerts.values())
    st.metric("🚨 Alertes actives", total_alerts, delta="Voir détails" if total_alerts > 0 else "RAS", delta_color="inverse" if total_alerts > 0 else "normal")

st.divider()

# ─── Alertes ──────────────────────────────────────────────────────────────────

if sum(alerts.values()) > 0:
    st.subheader("🚨 Alertes en cours")
    acol1, acol2, acol3, acol4 = st.columns(4)
    with acol1:
        if alerts["air"] > 0:
            st.error(f"💨 Air : {alerts['air']} dépassements PM2.5")
    with acol2:
        if alerts["traffic"] > 0:
            st.warning(f"🚗 Trafic : {alerts['traffic']} embouteillages")
    with acol3:
        if alerts["noise"] > 0:
            st.error(f"🔊 Bruit : {alerts['noise']} niveaux critiques")
    with acol4:
        if alerts["energy"] > 0:
            st.warning(f"⚡ Énergie : {alerts['energy']} pics de consommation")
    st.divider()

# ─── Graphes principaux ───────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5 = st.tabs(["💨 Qualité de l'air", "🚗 Trafic", "⚡ Énergie", "🔊 Bruit", "🗺️ Vue d'ensemble"])

# ── Tab 1 : Air ───────────────────────────────────────────────────────────────
with tab1:
    if not df_air.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig = px.line(df_air, x="timestamp", y="pm25", color="zone",
                          title="PM2.5 (µg/m³) — Particules fines",
                          labels={"pm25": "PM2.5 µg/m³", "timestamp": "Heure"})
            fig.add_hline(y=20, line_dash="dash", line_color="red",
                          annotation_text="Seuil critique (20 µg/m³)")
            fig.update_layout(template="plotly_dark", height=350)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig2 = px.line(df_air, x="timestamp", y="co2", color="zone",
                           title="CO2 (ppm)",
                           labels={"co2": "CO2 ppm", "timestamp": "Heure"})
            fig2.add_hline(y=600, line_dash="dash", line_color="orange",
                           annotation_text="Seuil attention (600 ppm)")
            fig2.update_layout(template="plotly_dark", height=350)
            st.plotly_chart(fig2, use_container_width=True)

        # Dernières valeurs par zone
        st.subheader("Dernières mesures par zone")
        if not latest_air.empty:
            st.dataframe(
                latest_air[["zone", "pm25", "co2", "no2", "temperature", "humidity", "timestamp"]],
                use_container_width=True,
                hide_index=True
            )

# ── Tab 2 : Trafic ────────────────────────────────────────────────────────────
with tab2:
    if not df_traffic.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig = px.line(df_traffic, x="timestamp", y="vehicles_per_min", color="zone",
                          title="Véhicules par minute",
                          labels={"vehicles_per_min": "Véhicules/min", "timestamp": "Heure"})
            fig.update_layout(template="plotly_dark", height=350)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig2 = px.line(df_traffic, x="timestamp", y="avg_speed_kmh", color="zone",
                           title="Vitesse moyenne (km/h)",
                           labels={"avg_speed_kmh": "km/h", "timestamp": "Heure"})
            fig2.update_layout(template="plotly_dark", height=350)
            st.plotly_chart(fig2, use_container_width=True)

        # Pie chart congestion
        congestion_counts = df_traffic["congestion_level"].value_counts().reset_index()
        congestion_counts.columns = ["Niveau", "Count"]
        fig3 = px.pie(congestion_counts, values="Count", names="Niveau",
                      title="Répartition des niveaux de congestion",
                      color="Niveau",
                      color_discrete_map={"low": "#a6e3a1", "medium": "#fab387", "high": "#f38ba8"})
        fig3.update_layout(template="plotly_dark")
        st.plotly_chart(fig3, use_container_width=True)

# ── Tab 3 : Énergie ───────────────────────────────────────────────────────────
with tab3:
    if not df_energy.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig = px.line(df_energy, x="timestamp", y=["consumption_kw", "solar_production_kw"],
                          color_discrete_map={"consumption_kw": "#f38ba8", "solar_production_kw": "#a6e3a1"},
                          title="Consommation vs Production solaire (kW)",
                          labels={"value": "kW", "timestamp": "Heure", "variable": "Type"})
            fig.update_layout(template="plotly_dark", height=350)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig2 = px.area(df_energy, x="timestamp", y="net_kw", color="zone",
                           title="Bilan net par zone (kW)",
                           labels={"net_kw": "kW net", "timestamp": "Heure"})
            fig2.add_hline(y=0, line_color="white", line_width=1)
            fig2.update_layout(template="plotly_dark", height=350)
            st.plotly_chart(fig2, use_container_width=True)

# ── Tab 4 : Bruit ─────────────────────────────────────────────────────────────
with tab4:
    if not df_noise.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig = px.line(df_noise, x="timestamp", y="decibels", color="zone",
                          title="Niveau sonore (dB)",
                          labels={"decibels": "dB", "timestamp": "Heure"})
            fig.add_hline(y=75, line_dash="dash", line_color="red",
                          annotation_text="Seuil critique (75 dB)")
            fig.add_hline(y=60, line_dash="dash", line_color="orange",
                          annotation_text="Seuil attention (60 dB)")
            fig.update_layout(template="plotly_dark", height=400)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            noise_levels = df_noise["level"].value_counts().reset_index()
            noise_levels.columns = ["Niveau", "Count"]
            fig2 = px.bar(noise_levels, x="Niveau", y="Count",
                          title="Distribution des niveaux de bruit",
                          color="Niveau",
                          color_discrete_map={"normal": "#a6e3a1", "high": "#fab387", "critical": "#f38ba8"})
            fig2.update_layout(template="plotly_dark", height=400)
            st.plotly_chart(fig2, use_container_width=True)

# ── Tab 5 : Vue d'ensemble ────────────────────────────────────────────────────
with tab5:
    st.subheader("Comparaison des zones")

    if not df_air.empty and not df_traffic.empty:
        # Radar chart par zone
        zones_list = ["centre-ville", "quartier-nord", "quartier-sud", "zone-industrielle"]
        categories = ["Air (PM2.5)", "Trafic", "Énergie", "Bruit"]

        fig = go.Figure()
        colors = ["#89b4fa", "#a6e3a1", "#fab387", "#f38ba8"]

        for i, zone in enumerate(zones_list):
            air_val   = df_air[df_air["zone"] == zone]["pm25"].mean() if not df_air[df_air["zone"] == zone].empty else 0
            traf_val  = df_traffic[df_traffic["zone"] == zone]["vehicles_per_min"].mean() if not df_traffic[df_traffic["zone"] == zone].empty else 0
            ener_val  = df_energy[df_energy["zone"] == zone]["consumption_kw"].mean() if not df_energy[df_energy["zone"] == zone].empty else 0
            noise_val = df_noise[df_noise["zone"] == zone]["decibels"].mean() if not df_noise[df_noise["zone"] == zone].empty else 0

            # Normalisation 0-100
            values = [
                min(air_val / 25 * 100, 100),
                min(traf_val / 80 * 100, 100),
                min(ener_val / 500 * 100, 100),
                min(noise_val / 85 * 100, 100)
            ]

            fig.add_trace(go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill="toself",
                name=zone,
                line_color=colors[i],
                opacity=0.7
            ))

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            template="plotly_dark",
            title="Profil de chaque zone (normalisé 0-100)",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

    # Tableau récapitulatif
    st.subheader("Récapitulatif temps réel")
    summary_data = []
    for zone in ["centre-ville", "quartier-nord", "quartier-sud", "zone-industrielle"]:
        air_z   = df_air[df_air["zone"] == zone]
        traf_z  = df_traffic[df_traffic["zone"] == zone]
        ener_z  = df_energy[df_energy["zone"] == zone]
        noise_z = df_noise[df_noise["zone"] == zone]
        summary_data.append({
            "Zone": zone,
            "PM2.5 µg/m³": round(air_z["pm25"].mean(), 1) if not air_z.empty else "-",
            "Véhicules/min": int(traf_z["vehicles_per_min"].mean()) if not traf_z.empty else "-",
            "Consommation kW": round(ener_z["consumption_kw"].mean(), 1) if not ener_z.empty else "-",
            "Bruit dB": round(noise_z["decibels"].mean(), 1) if not noise_z.empty else "-",
        })

    st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

# ─── Auto-refresh ─────────────────────────────────────────────────────────────

if auto_refresh:
    import time
    time.sleep(refresh_rate)
    st.rerun()
