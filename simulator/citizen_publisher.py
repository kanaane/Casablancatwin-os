"""
CityTwin OS — Module 4 : Simulation agents citoyens (MESA 3.x)
50 citoyens de Casablanca qui :
  - Se déplacent entre les zones (domicile → travail → commerces)
  - Réagissent à la pollution (restent chez eux si air mauvais)
  - Réagissent à la météo (voiture si pluie)
  - Consomment de l'énergie selon leurs activités
  - Publient leurs données sur MQTT → dashboard
"""

import json
import time
import random
import sqlite3
import paho.mqtt.client as mqtt
from datetime import datetime
from mesa import Agent, Model

# ─── Configuration ────────────────────────────────────────────────────────────

BROKER_HOST      = "localhost"
BROKER_PORT      = 1883
DATABASE         = "data/citytwin.db"
PUBLISH_INTERVAL = 10
N_AGENTS         = 50

ZONES    = ["centre", "maarif", "ain-diab", "sidi-maarouf"]
PROFILES = ["travailleur", "etudiant", "retraite", "commercant"]

WORK_ZONES = {
    "travailleur": "sidi-maarouf",
    "etudiant":    "maarif",
    "retraite":    "ain-diab",
    "commercant":  "centre",
}

# ─── Lecture environnement depuis SQLite ──────────────────────────────────────

def get_env_data() -> dict:
    env = {
        "pm25":        {z: 10.0 for z in ZONES},
        "temperature": {z: 20.0 for z in ZONES},
        "rain":        False,
        "congestion":  {z: "low" for z in ZONES}
    }
    try:
        conn = sqlite3.connect(DATABASE)
        for zone in ZONES:
            row = conn.execute(
                "SELECT pm25, temperature FROM air_quality WHERE zone=? ORDER BY id DESC LIMIT 1",
                (zone,)
            ).fetchone()
            if row:
                env["pm25"][zone]        = row[0]
                env["temperature"][zone] = row[1]

            row2 = conn.execute(
                "SELECT congestion_level FROM traffic WHERE zone=? ORDER BY id DESC LIMIT 1",
                (zone,)
            ).fetchone()
            if row2:
                env["congestion"][zone] = row2[0]

        row3 = conn.execute(
            "SELECT humidity FROM air_quality ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row3:
            env["rain"] = row3[0] > 85
        conn.close()
    except Exception as e:
        print(f"⚠️  Erreur lecture env : {e}")
    return env


# ─── Agent citoyen (MESA 3.x — plus de unique_id) ────────────────────────────

class CitizenAgent(Agent):

    def __init__(self, model):
        super().__init__(model)           # MESA 3.x : juste model
        self.profile      = random.choice(PROFILES)
        self.home_zone    = random.choice(ZONES)
        self.work_zone    = WORK_ZONES[self.profile]
        self.current_zone = self.home_zone
        self.state        = "domicile"
        self.using_car    = False
        self.energy_usage = 0.0
        self.stayed_home  = False

    def get_pm25(self) -> float:
        return self.model.env["pm25"].get(self.current_zone, 10.0)

    def get_congestion(self) -> str:
        return self.model.env["congestion"].get(self.current_zone, "low")

    def decide_transport(self) -> None:
        rain       = self.model.env["rain"]
        congestion = self.get_congestion()

        if rain:
            self.using_car = True
        elif congestion == "high" and self.profile == "etudiant":
            self.using_car = False
        elif self.profile == "retraite":
            self.using_car = False
        else:
            self.using_car = random.random() > 0.4

    def decide_stay_home(self) -> bool:
        pm25 = self.get_pm25()
        if pm25 > 25 and self.profile == "retraite":
            return True
        elif pm25 > 35:
            return True
        return False

    def compute_energy(self) -> float:
        base = {
            "domicile":   random.uniform(0.5, 2.0),
            "travail":    random.uniform(0.2, 0.8),
            "commercial": random.uniform(0.1, 0.3),
            "transport":  random.uniform(3.0, 8.0) if self.using_car else 0.1
        }
        temp         = self.model.env["temperature"].get(self.current_zone, 20.0)
        comfort      = 1.5 if temp > 28 or temp < 12 else 1.0
        return round(base.get(self.state, 0.5) * comfort, 2)

    def step(self):
        hour             = datetime.now().hour
        self.stayed_home = self.decide_stay_home()

        if self.stayed_home:
            self.state        = "domicile"
            self.current_zone = self.home_zone
            self.using_car    = False

        elif 7 <= hour <= 9:
            self.decide_transport()
            self.state        = "transport"
            self.current_zone = self.work_zone

        elif 9 < hour <= 17:
            self.state        = "travail"
            self.current_zone = self.work_zone

        elif 17 < hour <= 20:
            if random.random() > 0.5:
                self.state        = "commercial"
                self.current_zone = random.choice(ZONES)
            else:
                self.state        = "transport"
                self.current_zone = self.home_zone

        else:
            self.state        = "domicile"
            self.current_zone = self.home_zone
            self.using_car    = False

        self.energy_usage = self.compute_energy()


# ─── Modèle MESA 3.x ─────────────────────────────────────────────────────────

class CasablancaModel(Model):

    def __init__(self, n_agents: int):
        super().__init__()
        self.env = get_env_data()
        for _ in range(n_agents):
            CitizenAgent(self)
        print(f"✅ {n_agents} agents créés sur Casablanca")

    def step(self):
        self.env = get_env_data()
        self.agents.shuffle_do("step")

    def get_stats(self) -> dict:
        stats = {zone: {
            "population":    0,
            "using_car":     0,
            "stayed_home":   0,
            "energy_total":  0.0,
            "at_work":       0,
            "at_home":       0,
            "in_transport":  0,
            "in_commercial": 0,
        } for zone in ZONES}

        for agent in self.agents:
            z = agent.current_zone
            if z not in stats:
                continue
            stats[z]["population"]    += 1
            stats[z]["energy_total"]  += agent.energy_usage
            stats[z]["using_car"]     += 1 if agent.using_car    else 0
            stats[z]["stayed_home"]   += 1 if agent.stayed_home  else 0
            if agent.state == "travail":
                stats[z]["at_work"]       += 1
            elif agent.state == "domicile":
                stats[z]["at_home"]       += 1
            elif agent.state == "transport":
                stats[z]["in_transport"]  += 1
            elif agent.state == "commercial":
                stats[z]["in_commercial"] += 1

        for z in stats:
            stats[z]["energy_total"] = round(stats[z]["energy_total"], 2)

        return stats


# ─── MQTT ─────────────────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, rc):
    print("✅ Agent Publisher connecté" if rc == 0 else f"❌ Erreur : {rc}")


def run_agents():
    print("=" * 60)
    print("  CityTwin OS · Agents citoyens MESA 3.x")
    print(f"  {N_AGENTS} citoyens · 4 zones · Casablanca")
    print("=" * 60)

    client = mqtt.Client(client_id="citytwin_agent_publisher")
    client.on_connect = on_connect
    try:
        client.connect(BROKER_HOST, BROKER_PORT, 60)
        client.loop_start()
    except ConnectionRefusedError:
        print("❌ Broker MQTT indisponible.")
        return

    model = CasablancaModel(N_AGENTS)
    print(f"\n🏙️  Simulation démarrée — cycle toutes les {PUBLISH_INTERVAL}s\n")

    try:
        cycle = 0
        while True:
            cycle += 1
            model.step()
            stats = model.get_stats()

            print(f"─── Cycle {cycle} · {datetime.now().strftime('%H:%M:%S')} ───")
            for zone, s in stats.items():
                payload = {
                    "sensor_id": f"agents_{zone}",
                    "type":      "agents",
                    "zone":      zone,
                    "source":    "mesa-simulation",
                    "timestamp": datetime.now().isoformat(),
                    "values": {
                        "population":    s["population"],
                        "using_car":     s["using_car"],
                        "stayed_home":   s["stayed_home"],
                        "energy_kw":     s["energy_total"],
                        "at_work":       s["at_work"],
                        "at_home":       s["at_home"],
                        "in_transport":  s["in_transport"],
                        "in_commercial": s["in_commercial"],
                    },
                    "status": "simulated"
                }
                client.publish(f"citytwin/agents/{zone}", json.dumps(payload), qos=1)
                print(f"  👥 {zone:<15} | "
                      f"pop={s['population']} | "
                      f"🚗 {s['using_car']} voitures | "
                      f"🏠 {s['stayed_home']} restés (pollution) | "
                      f"⚡ {s['energy_total']} kW")
            print()
            time.sleep(PUBLISH_INTERVAL)

    except KeyboardInterrupt:
        print("\n🛑 Agents arrêtés.")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    run_agents()
