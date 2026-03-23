"""
CityTwin OS — Module 2 : Subscriber MQTT + Stockage SQLite
Reçoit les données des capteurs via MQTT et les stocke en base de données
"""

import json
import sqlite3
from datetime import datetime
import paho.mqtt.client as mqtt

# ─── Configuration ────────────────────────────────────────────────────────────

BROKER_HOST  = "localhost"
BROKER_PORT  = 1883
TOPIC        = "citytwin/#"   # écoute tous les topics CityTwin
DATABASE     = "data/citytwin.db"

# ─── Base de données SQLite ───────────────────────────────────────────────────

def init_database(db_path: str):
    """Crée les tables si elles n'existent pas encore"""
    import os
    os.makedirs("data", exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Table qualité de l'air
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS air_quality (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id   TEXT,
            zone        TEXT,
            timestamp   TEXT,
            pm25        REAL,
            co2         REAL,
            no2         REAL,
            temperature REAL,
            humidity    REAL
        )
    """)

    # Table trafic
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS traffic (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id        TEXT,
            zone             TEXT,
            timestamp        TEXT,
            vehicles_per_min INTEGER,
            avg_speed_kmh    REAL,
            congestion_level TEXT,
            pedestrians      INTEGER
        )
    """)

    # Table énergie
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS energy (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id            TEXT,
            zone                 TEXT,
            timestamp            TEXT,
            consumption_kw       REAL,
            solar_production_kw  REAL,
            net_kw               REAL,
            voltage              REAL,
            frequency_hz         REAL
        )
    """)

    # Table bruit
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS noise (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id TEXT,
            zone      TEXT,
            timestamp TEXT,
            decibels  REAL,
            level     TEXT,
            peak_db   REAL
        )
    """)

    # Table agents citoyens
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id      TEXT,
            zone           TEXT,
            timestamp      TEXT,
            population     INTEGER,
            using_car      INTEGER,
            stayed_home    INTEGER,
            energy_kw      REAL,
            at_work        INTEGER,
            at_home        INTEGER,
            in_transport   INTEGER,
            in_commercial  INTEGER
        )
    """)

    conn.commit()
    conn.close()
    print(f"✅ Base de données initialisée : {db_path}")


def save_to_db(db_path: str, data: dict):
    """Insère une mesure dans la bonne table selon son type"""
    conn   = sqlite3.connect(db_path)
    cursor = conn.cursor()
    sensor_type = data.get("type")
    v = data.get("values", {})

    if sensor_type == "air_quality":
        cursor.execute("""
            INSERT INTO air_quality
            (sensor_id, zone, timestamp, pm25, co2, no2, temperature, humidity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["sensor_id"], data["zone"], data["timestamp"],
            v["pm25"], v["co2"], v["no2"], v["temperature"], v["humidity"]
        ))

    elif sensor_type == "traffic":
        cursor.execute("""
            INSERT INTO traffic
            (sensor_id, zone, timestamp, vehicles_per_min, avg_speed_kmh, congestion_level, pedestrians)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data["sensor_id"], data["zone"], data["timestamp"],
            v["vehicles_per_min"], v["avg_speed_kmh"], v["congestion_level"], v["pedestrians"]
        ))

    elif sensor_type == "energy":
        cursor.execute("""
            INSERT INTO energy
            (sensor_id, zone, timestamp, consumption_kw, solar_production_kw, net_kw, voltage, frequency_hz)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["sensor_id"], data["zone"], data["timestamp"],
            v["consumption_kw"], v["solar_production_kw"], v["net_kw"],
            v["voltage"], v["frequency_hz"]
        ))

    elif sensor_type == "noise":
        cursor.execute("""
            INSERT INTO noise
            (sensor_id, zone, timestamp, decibels, level, peak_db)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["sensor_id"], data["zone"], data["timestamp"],
            v["decibels"], v["level"], v["peak_db"]
        ))

    elif sensor_type == "agents":
        cursor.execute("""
            INSERT INTO agents
            (sensor_id, zone, timestamp, population, using_car, stayed_home,
             energy_kw, at_work, at_home, in_transport, in_commercial)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["sensor_id"], data["zone"], data["timestamp"],
            v["population"], v["using_car"], v["stayed_home"],
            v["energy_kw"], v["at_work"], v["at_home"],
            v["in_transport"], v["in_commercial"]
        ))

    conn.commit()
    conn.close()

# ─── Callbacks MQTT ───────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Subscriber connecté au broker MQTT")
        client.subscribe(TOPIC)
        print(f"👂 Écoute sur : {TOPIC}\n")
    else:
        print(f"❌ Erreur connexion : code {rc}")


def on_message(client, userdata, msg):
    """Appelé à chaque message reçu"""
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        save_to_db(DATABASE, data)

        # Affichage console avec alerte si anomalie
        zone  = data.get("zone", "?")
        stype = data.get("type", "?")
        v     = data.get("values", {})

        # Détection d'anomalies simples
        alert = ""
        if stype == "air_quality" and v.get("pm25", 0) > 20:
            alert = "⚠️  PM2.5 élevé !"
        elif stype == "traffic" and v.get("congestion_level") == "high":
            alert = "🚗 Embouteillage !"
        elif stype == "noise" and v.get("level") == "critical":
            alert = "🔊 Bruit critique !"
        elif stype == "energy" and v.get("net_kw", 0) > 400:
            alert = "⚡ Consommation élevée !"

        print(f"💾 [{stype}][{zone}] {v} {alert}")

    except Exception as e:
        print(f"❌ Erreur traitement message : {e}")


# ─── Lancement ────────────────────────────────────────────────────────────────

def run_subscriber():
    print("=" * 55)
    print("  CityTwin OS · Subscriber MQTT + SQLite")
    print("=" * 55)

    init_database(DATABASE)

    client = mqtt.Client(client_id="citytwin_subscriber")
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER_HOST, BROKER_PORT, 60)
        print(f"\n📡 Connexion à {BROKER_HOST}:{BROKER_PORT}...")
        client.loop_forever()  # tourne indéfiniment
    except KeyboardInterrupt:
        print("\n🛑 Subscriber arrêté.")
        client.disconnect()
    except ConnectionRefusedError:
        print("❌ Broker MQTT indisponible. Lance Mosquitto d'abord.")


if __name__ == "__main__":
    run_subscriber()
