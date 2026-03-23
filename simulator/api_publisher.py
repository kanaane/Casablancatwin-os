"""
CityTwin OS — Module 5 : APIs réelles Casablanca
Données météo et qualité de l'air réelles + facteurs géographiques par zone
"""

import json
import time
import random
import requests
from datetime import datetime
import paho.mqtt.client as mqtt

# ─── Configuration ────────────────────────────────────────────────────────────

BROKER_HOST      = "localhost"
BROKER_PORT      = 1883
PUBLISH_INTERVAL = 60  # secondes

# Zones réelles de Casablanca avec coordonnées GPS
ZONES = {
    "centre": {
        "lat": 33.5731, "lon": -7.5898,
        "description": "Centre-ville dense · médina · boulevard Mohammed V"
    },
    "maarif": {
        "lat": 33.5809, "lon": -7.6350,
        "description": "Quartier résidentiel et commercial"
    },
    "ain-diab": {
        "lat": 33.5956, "lon": -7.6767,
        "description": "Bord de mer · corniche · résidentiel aisé"
    },
    "sidi-maarouf": {
        "lat": 33.5342, "lon": -7.6414,
        "description": "Zone industrielle et technologique · Casanearshore"
    },
}

# ─── Facteurs géographiques réalistes ────────────────────────────────────────
# Basés sur la vraie géographie et urbanisme de Casablanca

ZONE_FACTORS = {
    "centre": {
        # Centre-ville : dense, trafic intense, peu de végétation
        "pm25":        1.45,   # pollution élevée (trafic dense)
        "no2":         1.55,   # beaucoup de véhicules
        "temperature": +1.2,   # effet îlot de chaleur urbain
        "humidity":    -5.0,   # moins humide (béton)
        "wind":        0.70,   # vent bloqué par les immeubles
        "noise":       1.50,   # très bruyant
        "traffic":     1.60,   # trafic très dense
        "energy":      1.30,   # forte consommation (commerces, bureaux)
    },
    "maarif": {
        # Maarif : résidentiel et commercial, modéré
        "pm25":        1.10,
        "no2":         1.15,
        "temperature": +0.5,
        "humidity":    -2.0,
        "wind":        0.90,
        "noise":       1.20,
        "traffic":     1.20,
        "energy":      1.10,
    },
    "ain-diab": {
        # Ain Diab : bord de mer, vent marin, air plus propre
        "pm25":        0.65,   # air propre grâce à la brise marine
        "no2":         0.60,   # peu de trafic lourd
        "temperature": -0.8,   # plus frais (mer)
        "humidity":    +8.0,   # plus humide (océan Atlantique)
        "wind":        1.50,   # vent fort (exposition directe à l'Atlantique)
        "noise":       0.80,   # calme (résidentiel + bruit des vagues)
        "traffic":     0.70,   # peu de trafic
        "energy":      0.90,   # consommation modérée
    },
    "sidi-maarouf": {
        # Sidi Maarouf : zone industrielle + technologique
        "pm25":        1.70,   # industrie = pollution élevée
        "no2":         1.80,   # émissions industrielles
        "temperature": +1.5,   # chaleur industrielle
        "humidity":    -8.0,   # très sec
        "wind":        1.10,   # zone ouverte
        "noise":       1.40,   # bruit industriel
        "traffic":     1.35,   # camions et véhicules industriels
        "energy":      2.20,   # très forte consommation industrielle
    },
}

# ─── Open-Meteo API ───────────────────────────────────────────────────────────

def fetch_casablanca_base() -> dict:
    """
    Récupère 1 seule fois les données de base pour Casablanca
    puis on applique les facteurs par zone
    """
    try:
        weather_url = (
            "https://api.open-meteo.com/v1/forecast"
            "?latitude=33.5731&longitude=-7.5898"
            "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation"
            "&timezone=Africa/Casablanca"
        )
        weather  = requests.get(weather_url, timeout=10).json()
        current  = weather.get("current", {})

        air_url = (
            "https://air-quality-api.open-meteo.com/v1/air-quality"
            "?latitude=33.5731&longitude=-7.5898"
            "&current=pm2_5,carbon_monoxide,nitrogen_dioxide,european_aqi"
            "&timezone=Africa/Casablanca"
        )
        air      = requests.get(air_url, timeout=10).json()
        air_curr = air.get("current", {})

        return {
            "temperature": current.get("temperature_2m", 20.0) or 20.0,
            "humidity":    current.get("relative_humidity_2m", 65.0) or 65.0,
            "wind":        current.get("wind_speed_10m", 15.0) or 15.0,
            "rain":        current.get("precipitation", 0.0) or 0.0,
            "pm25":        air_curr.get("pm2_5", 10.0) or 10.0,
            "no2":         air_curr.get("nitrogen_dioxide", 20.0) or 20.0,
            "co":          air_curr.get("carbon_monoxide", 200.0) or 200.0,
            "aqi":         air_curr.get("european_aqi", 30) or 30,
            "ok":          True
        }

    except Exception as e:
        print(f"⚠️  Erreur API : {e} — utilisation valeurs de secours")
        return {
            "temperature": 19.0,
            "humidity":    70.0,
            "wind":        18.0,
            "rain":        0.0,
            "pm25":        12.0,
            "no2":         25.0,
            "co":          250.0,
            "aqi":         35,
            "ok":          False
        }


def apply_zone_factors(base: dict, zone: str) -> dict:
    """Applique les facteurs géographiques de chaque zone"""
    f     = ZONE_FACTORS[zone]
    noise = lambda: random.uniform(-0.05, 0.05)

    return {
        "pm25":        round(max(0, base["pm25"] * (f["pm25"] + noise())), 2),
        "no2":         round(max(0, base["no2"]  * (f["no2"]  + noise())), 2),
        "co2":         round(max(0, base["co"]   * (f["pm25"] + noise()) / 1000), 1),
        "temperature": round(base["temperature"] + f["temperature"] + random.uniform(-0.3, 0.3), 1),
        "humidity":    round(min(100, max(0, base["humidity"] + f["humidity"] + random.uniform(-2, 2))), 1),
        "wind_speed":  round(max(0, base["wind"] * (f["wind"] + noise())), 1),
        "aqi":         int(base["aqi"] * f["pm25"]),
        "rain":        base["rain"],
    }


def build_air_payload(zone: str, values: dict, source_ok: bool) -> dict:
    return {
        "sensor_id": f"api_air_{zone}",
        "type":      "air_quality",
        "zone":      zone,
        "source":    "open-meteo-real" if source_ok else "open-meteo-fallback",
        "timestamp": datetime.now().isoformat(),
        "values":    values,
        "status":    "real"
    }


def build_traffic_payload(zone: str, base: dict) -> dict:
    f      = ZONE_FACTORS[zone]
    hour   = datetime.now().hour
    rush   = 1.0 + 0.8 * (1 if 7 <= hour <= 9 or 17 <= hour <= 20 else 0)
    rain_f = 1.3 if base["rain"] > 0 else 1.0

    vehicles = int(random.uniform(10, 70) * f["traffic"] * rush * rain_f)
    speed    = round(random.uniform(15, 60) / (1 + rush * 0.3) / f["traffic"], 1)
    cong     = "high" if vehicles > 60 else "medium" if vehicles > 30 else "low"

    return {
        "sensor_id": f"api_traffic_{zone}",
        "type":      "traffic",
        "zone":      zone,
        "source":    "simulated-weather-aware",
        "timestamp": datetime.now().isoformat(),
        "values": {
            "vehicles_per_min": vehicles,
            "avg_speed_kmh":    speed,
            "congestion_level": cong,
            "pedestrians":      int(random.uniform(5, 40) * rush * (0.5 if base["rain"] > 0 else 1.0)),
            "rush_hour":        rush > 1.0,
            "rain_impact":      rain_f > 1.0
        },
        "status": "simulated"
    }


def build_energy_payload(zone: str, base: dict) -> dict:
    f      = ZONE_FACTORS[zone]
    hour   = datetime.now().hour
    heat_f = 1.3 if base["temperature"] > 28 else 1.0
    cold_f = 1.2 if base["temperature"] < 12 else 1.0
    peak_f = 1.4 if 7 <= hour <= 9 or 18 <= hour <= 22 else 1.0

    consumption = round(random.uniform(60, 400) * f["energy"] * heat_f * cold_f * peak_f, 2)
    solar       = round(random.uniform(0, 150) * (0.1 if base["rain"] > 0 else 1.0), 2)

    return {
        "sensor_id": f"api_energy_{zone}",
        "type":      "energy",
        "zone":      zone,
        "source":    "simulated-weather-aware",
        "timestamp": datetime.now().isoformat(),
        "values": {
            "consumption_kw":      consumption,
            "solar_production_kw": solar,
            "net_kw":              round(consumption - solar, 2),
            "voltage":             round(random.uniform(218, 222), 1),
            "frequency_hz":        round(random.uniform(49.9, 50.1), 2),
            "temp_factor":         heat_f > 1.0 or cold_f > 1.0
        },
        "status": "simulated"
    }


def build_noise_payload(zone: str, base: dict) -> dict:
    f      = ZONE_FACTORS[zone]
    hour   = datetime.now().hour
    time_f = 0.4 if hour < 6 or hour > 23 else 1.0
    rain_f = 0.8 if base["rain"] > 0 else 1.0

    db    = round(random.uniform(35, 80) * f["noise"] * time_f * rain_f, 1)
    level = "critical" if db > 75 else "high" if db > 60 else "normal"

    return {
        "sensor_id": f"api_noise_{zone}",
        "type":      "noise",
        "zone":      zone,
        "source":    "simulated-weather-aware",
        "timestamp": datetime.now().isoformat(),
        "values": {
            "decibels": db,
            "level":    level,
            "peak_db":  round(db + random.uniform(0, 8), 1)
        },
        "status": "simulated"
    }


# ─── Client MQTT ──────────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, rc):
    print("✅ API Publisher connecté" if rc == 0 else f"❌ Erreur : {rc}")


def run_api_publisher():
    print("=" * 60)
    print("  CityTwin OS · APIs réelles + simulation Casablanca")
    print("=" * 60)

    client = mqtt.Client(client_id="citytwin_api_publisher")
    client.on_connect = on_connect

    try:
        client.connect(BROKER_HOST, BROKER_PORT, 60)
        client.loop_start()
    except ConnectionRefusedError:
        print("❌ Broker MQTT indisponible.")
        return

    print(f"\n🌍 Casablanca — 4 zones · données réelles + simulation météo-aware")
    print(f"📡 Cycle toutes les {PUBLISH_INTERVAL}s\n")

    try:
        while True:
            print(f"🔄 {datetime.now().strftime('%H:%M:%S')} — Récupération Casablanca...")

            base      = fetch_casablanca_base()
            source_ok = base.pop("ok")

            print(f"🌡️  Base : {base['temperature']}°C | "
                  f"Humidité {base['humidity']}% | "
                  f"Vent {base['wind']} km/h | "
                  f"PM2.5 {base['pm25']} | "
                  f"{'🌧️  Pluie' if base['rain'] > 0 else '☀️  Sec'}\n")

            for zone in ZONES:
                air_values   = apply_zone_factors(base, zone)
                air_data     = build_air_payload(zone, air_values, source_ok)
                traffic_data = build_traffic_payload(zone, base)
                energy_data  = build_energy_payload(zone, base)
                noise_data   = build_noise_payload(zone, base)

                client.publish(f"citytwin/air/{zone}",     json.dumps(air_data),     qos=1)
                client.publish(f"citytwin/traffic/{zone}", json.dumps(traffic_data), qos=1)
                client.publish(f"citytwin/energy/{zone}",  json.dumps(energy_data),  qos=1)
                client.publish(f"citytwin/noise/{zone}",   json.dumps(noise_data),   qos=1)

                v = air_values
                print(f"  📍 {zone:<15} | "
                      f"temp={v['temperature']}°C | "
                      f"PM2.5={v['pm25']} | "
                      f"NO2={v['no2']} | "
                      f"AQI={v['aqi']} | "
                      f"vent={v['wind_speed']} km/h")

            print(f"\n✅ Prochain cycle dans {PUBLISH_INTERVAL}s\n")
            time.sleep(PUBLISH_INTERVAL)

    except KeyboardInterrupt:
        print("\n🛑 API Publisher arrêté.")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    run_api_publisher()
