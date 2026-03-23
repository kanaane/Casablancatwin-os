# 🏙️ CasablancaTwin OS — Jumeau Numérique de Casablanca

> Système IoT complet simulant une ville intelligente  

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![MQTT](https://img.shields.io/badge/MQTT-Mosquitto-orange.svg)](https://mosquitto.org)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-red.svg)](https://streamlit.io)
[![MESA](https://img.shields.io/badge/Agents-MESA%203.x-green.svg)](https://mesa.readthedocs.io)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 Présentation

**CasablancaTwin OS** (Casablanca Twin Operating System) est le système d'exploitation du jumeau numérique de Casablanca. Il orchestre en temps réel :

- 📡 **Des flux de données IoT** — capteurs virtuels sur 4 zones de la ville
- 🌍 **Des données réelles** — météo et qualité de l'air via Open-Meteo API
- 👥 **Des agents citoyens** — simulation multi-agents MESA réactifs à l'environnement
- 📊 **Un dashboard interactif** — visualisation temps réel avec carte de Casablanca

Le projet démontre concrètement l'interaction entre les **3 dimensions le cyber, physique et sociale** :
> *Données physiques réelles (PM2.5 Open-Meteo) → influencent → comportements sociaux simulés (agents MESA)*

---

## 🗺️ Zones Simulées — Casablanca

| Zone | Coordonnées | Caractéristique |
|------|-------------|-----------------|
| **Centre** | 33.5731°N, 7.5898°W | Îlot de chaleur · trafic dense |
| **Maarif** | 33.5809°N, 7.6350°W | Quartier résidentiel calme |
| **Ain-Diab** | 33.5956°N, 7.6767°W | Bord de mer · air le plus propre |
| **Sidi-Maarouf** | 33.5342°N, 7.6414°W | Zone industrielle · plus polluée |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     PUBLISHERS (Sources)                     │
├──────────────────┬──────────────────┬───────────────────────┤
│  api_publisher   │  sim_publisher   │  citizen_publisher    │
│  ─────────────   │  ─────────────   │  ──────────────────   │
│  Météo + Air     │  Trafic + Énergie│  Agents MESA 50       │
│  (Open-Meteo)    │  + Bruit         │  citoyens simulés     │
│  RÉEL ✅         │  SIMULÉ 🔄       │  MULTI-AGENTS 🧑‍🤝‍🧑     │
│  60s/cycle       │  2s/cycle        │  10s/cycle            │
└────────┬─────────┴────────┬─────────┴──────────┬────────────┘
         │                  │                     │
         └──────────────────┼─────────────────────┘
                            ▼
              ┌─────────────────────────┐
              │   MQTT Broker           │
              │   Eclipse Mosquitto     │
              │   localhost:1883        │
              └────────────┬────────────┘
                           ▼
              ┌─────────────────────────┐
              │   data_collector_v2     │
              │   Subscriber MQTT       │
              │   → SQLite citytwin.db  │
              └────────────┬────────────┘
                           ▼
         ┌─────────────────────────────────────┐
         │           SQLite Database            │
         │  air_quality · traffic · energy      │
         │  noise · agents                      │
         │  +10 000 mesures / 24h               │
         └────────────────┬────────────────────┘
                          ▼
         ┌─────────────────────────────────────┐
         │           DASHBOARD                  │
         │  dashboard_v2.py → localhost:8501    │
         │  map.py          → localhost:8502    │
         │  6 onglets · carte Casablanca        │
         └─────────────────────────────────────┘
```

---

## 📁 Structure du Projet

```
citytwin-os/
├── simulator/
│   ├── api_publisher.py        # Données réelles Open-Meteo (air, météo)
│   ├── sim_publisher.py        # Simulation trafic, énergie, bruit
│   ├── citizen_publisher.py    # Agents citoyens MESA 3.x
│   └── data_collector_v2.py   # Subscriber MQTT → SQLite
├── dashboard/
│   ├── dashboard_v2.py         # Dashboard principal (6 onglets)
│   └── map.py                  # Carte interactive Casablanca
├── data/                       # SQLite (ignoré par Git)
├── requirements.txt
├── .gitignore
└── README.md
```

---

## ⚙️ Installation

### Prérequis
- Python 3.10+
- [Eclipse Mosquitto](https://mosquitto.org/download/) (broker MQTT)
- Git

### 1. Cloner le projet
```bash
git clone https://github.com/kanaane/Casablancatwin-os.git
cd Casablancatwin-os
```

### 2. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 3. Installer Mosquitto (Windows)
```
https://mosquitto.org/download/ → mosquitto-2.x.x-install-win64.exe
```

---

## 🚀 Lancement

Ouvrir **6 terminaux** dans l'ordre :

| Terminal | Commande | Rôle |
|----------|----------|------|
| 1 | `cd "C:\Program Files\mosquitto" && .\mosquitto.exe -v` | Broker MQTT |
| 2 | `python simulator/sim_publisher.py` | Trafic · Énergie · Bruit |
| 3 | `python simulator/api_publisher.py` | Météo · Air (Open-Meteo) |
| 4 | `python simulator/citizen_publisher.py` | Agents citoyens MESA |
| 5 | `python simulator/data_collector_v2.py` | Collecte → SQLite |
| 6 | `streamlit run dashboard/dashboard_v2.py` | Dashboard principal |

**Dashboard** → http://localhost:8501  
**Carte interactive** → `streamlit run dashboard/map.py --server.port 8502` → http://localhost:8502

---

## 📊 Données & Sources

| Donnée | Source | Type | Fréquence |
|--------|--------|------|-----------|
| Température · Humidité · Vent | Open-Meteo API | ✅ Réel | 60s |
| PM2.5 · NO2 · AQI | Open-Meteo Air Quality | ✅ Réel | 60s |
| Trafic · Congestion | Simulation météo-aware | 🔄 Simulé | 2s |
| Consommation énergie | Simulation | 🔄 Simulé | 2s |
| Niveau sonore | Simulation | 🔄 Simulé | 2s |
| Comportements citoyens | MESA Multi-Agents | 🧑‍🤝‍🧑 Simulé | 10s |

---

## 👥 Agents Citoyens (MESA)

**50 agents** répartis sur 4 zones avec 4 profils :

| Profil | Zone de travail | Comportement spécial |
|--------|----------------|----------------------|
| Travailleur | Sidi-Maarouf | Rush hour 7h-9h · 17h-20h |
| Étudiant | Maarif | Prend le transport si embouteillage |
| Retraité | Ain-Diab | Reste à domicile si PM2.5 > 25 µg/m³ |
| Commerçant | Centre | Présent toute la journée |

### Réactivité environnementale
- 🌧️ **Pluie** (humidité > 85%) → plus de voitures, moins de piétons
- 🌫️ **Pollution** (PM2.5 > 25) → retraités restent à domicile
- 🌡️ **Chaleur** (> 28°C) → consommation énergie ×1.5 (climatisation)

---

## 📈 Résultats

| Métrique | Valeur |
|----------|--------|
| Capteurs virtuels | 16 (4 zones × 4 types) |
| Agents citoyens | 50 |
| Tables SQLite | 5 (air, trafic, énergie, bruit, agents) |
| Mesures / 24h | +10 000 |
| APIs intégrées | Open-Meteo (gratuit, sans clé) |
| Coût hardware | **0€** |

---

## 🔗 Corrélation 

```
PM2.5 réel (Open-Meteo)     →   Retraités restent à domicile (MESA)
Pluie réelle (Open-Meteo)   →   Trafic simulé augmente
Chaleur réelle (Open-Meteo) →   Consommation énergie simulée ×1.5
```

> *Ce projet démontre que les données physiques réelles influencent directement les comportements sociaux simulés — c'est la boucle **Cyber-Physical-Social** 

---

## 🛠️ Technologies

| Catégorie | Technologies |
|-----------|-------------|
| **Langage** | Python 3.10+ |
| **IoT / MQTT** | Eclipse Mosquitto · paho-mqtt |
| **Simulation** | MESA 3.x (multi-agents) |
| **APIs** | Open-Meteo (météo + qualité de l'air) |
| **Base de données** | SQLite3 |
| **Dashboard** | Streamlit · Plotly · Folium |
| **Versionnement** | Git · GitHub |

---

## 👤 Auteur

Mohamed El Mahdi kanaane

GitHub : [@kanaane](https://github.com/kanaane)

---

## 📄 Licence

MIT License — voir [LICENSE](LICENSE)
