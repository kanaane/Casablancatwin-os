"""
CityTwin OS — sim_publisher.py : Simulateur trafic, énergie, bruit
Simule UNIQUEMENT les données non disponibles via API gratuite :
  ✅ Trafic        → pas d'API gratuite temps réel
  ✅ Énergie       → ONEE Maroc pas d'API publique
  ✅ Bruit         → pas de réseau de capteurs public

  ❌ Qualité de l'air → géré par api_publisher.py (Open-Meteo)
  ❌ Météo            → géré par api_publisher.py (Open-Meteo)
"""

import json
import time
import random
import math
from datetime import datetime
import paho.mqtt.client as mqtt

# ─── Configuration ────────────────────────────────────────────────────────────

BROKER_HOST      = "localhost"
BROKER_PORT      = 1883
PUBLISH_INTERVAL = 2  # secondes

# Zones Casablanca — identiques à api_publisher.py
ZONES = ["centre", "maarif", "ain-diab", "sidi-maarouf"]

# ─── Facteurs par zone (cohérents avec api_publisher.py) ──────────────────────

ZONE_FACTORS = {
    "centre":        {"traffic": 1.60, "energy": 1.30, "noise": 1.50},
    "maarif":        {"traffic": 1.20, "energy": 1.10, "noise": 1.20},
    "ain-diab":      {"traffic": 0.70, "energy": 0.90, "noise": 0.80},
    "sidi-maarouf":  {"traffic": 1.35, "energy": 2.20, "noise": 1.40},
}

# ─── Facteur horaire ──────────────────────────────────────────────────────────

def get_hour_factor() -> float:
    """Rush hour Casablanca : 7h-9h et 17h-20h"""
    hour = datetime.now().hour
    if 7 <= hour <= 9 or 17 <= hour <= 20:
        return 0.8 + random.uniform(0.1, 0.2)   # heure de pointe
    elif 0 <= hour <= 5:
        return 0.1 + random.uniform(0.0, 0.1)   # nuit calme
    else:
        return 0.4 + random.uniform(0.0, 0.2)   # heure normale

# ─── Générateurs ──────────────────────────────────────────────────────────────

def generate_traffic(zone: str) -> dict:
    f        = ZONE_FACTORS[zone]["traffic"]
    factor   = get_hour_factor()
    vehicles = int(random.uniform(5, 80) * f * factor)
    speed    = round(random.uniform(10, 60) / (1 + factor * f * 0.3), 1)
    cong     = "high" if vehicles > 60 else "medium" if vehicles > 30 else "low"

    return {
        "sensor_id": f"sim_traffic_{zone}",
        "type":      "traffic",
        "zone":      zone,
        "source":    "simulated",
        "timestamp": datetime.now().isoformat(),
        "values": {
            "vehicles_per_min": vehicles,
            "avg_speed_kmh":    speed,
            "congestion_level": cong,
            "pedestrians":      int(random.uniform(0, 40) * factor)
        },
        "status": "simulated"
    }


def generate_energy(zone: str) -> dict:
    f       = ZONE_FACTORS[zone]["energy"]
    factor  = get_hour_factor()
    # Pic énergie matin (7-9h) et soir (18-22h)
    hour    = datetime.now().hour
    peak    = 1.4 if 7 <= hour <= 9 or 18 <= hour <= 22 else 1.0

    consumption = round(random.uniform(50, 400) * f * factor * peak, 2)
    solar       = round(random.uniform(0, 150) * (factor * 0.8), 2)

    return {
        "sensor_id": f"sim_energy_{zone}",
        "type":      "energy",
        "zone":      zone,
        "source":    "simulated",
        "timestamp": datetime.now().isoformat(),
        "values": {
            "consumption_kw":      consumption,
            "solar_production_kw": solar,
            "net_kw":              round(consumption - solar, 2),
            "voltage":             round(random.uniform(218, 222), 1),  # réseau Maroc 220V
            "frequency_hz":        round(random.uniform(49.9, 50.1), 2)
        },
        "status": "simulated"
    }


def generate_noise(zone: str) -> dict:
    f      = ZONE_FACTORS[zone]["noise"]
    factor = get_hour_factor()
    db     = round(random.uniform(35, 80) * f * factor, 1)
    level  = "critical" if db > 75 else "high" if db > 60 else "normal"

    return {
        "sensor_id": f"sim_noise_{zone}",
        "type":      "noise",
        "zone":      zone,
        "source":    "simulated",
        "timestamp": datetime.now().isoformat(),
        "values": {
            "decibels": db,
            "level":    level,
            "peak_db":  round(db + random.uniform(0, 8), 1)
        },
        "status": "simulated"
    }


# ─── Publication MQTT ─────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, rc):
    print("✅ Simulateur connecté au broker MQTT" if rc == 0 else f"❌ Erreur : {rc}")


def run_simulator():
    client = mqtt.Client(client_id="citytwin_sim_publisher")
    client.on_connect = on_connect

    try:
        client.connect(BROKER_HOST, BROKER_PORT, 60)
        client.loop_start()
    except ConnectionRefusedError:
        print("❌ Broker MQTT indisponible. Lance Mosquitto d'abord.")
        return

    generators = [generate_traffic, generate_energy, generate_noise]
    topics     = ["traffic",        "energy",         "noise"]

    print("=" * 55)
    print("  CityTwin OS · Simulateur (trafic, énergie, bruit)")
    print("  Qualité de l'air → api_publisher.py")
    print("=" * 55)
    print(f"📡 Publication toutes les {PUBLISH_INTERVAL}s\n")

    try:
        while True:
            for zone in ZONES:
                for gen, topic in zip(generators, topics):
                    data    = gen(zone)
                    payload = json.dumps(data, ensure_ascii=False)
                    client.publish(f"citytwin/{topic}/{zone}", payload, qos=1)
                    print(f"📤 [{topic}][{zone}] {data['values']}")

            print(f"─── {datetime.now().strftime('%H:%M:%S')} ───\n")
            time.sleep(PUBLISH_INTERVAL)

    except KeyboardInterrupt:
        print("\n🛑 Simulateur arrêté.")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    run_simulator()
