[English](#english) | [Français](#francais)

<a id="english"></a>

# 🍄 Smart Mushroom Greenhouse - Raspberry Pi IoT Project

An automated control system for a mushroom greenhouse, powered by Raspberry Pi.

---

## 🎯 Project Vision

This project explores the **Internet of Things (IoT)** in agriculture, combining food self-sufficiency with technological innovation. Designed as a smart management system for a mushroom greenhouse, it provides automated environmental control (temperature, humidity, CO2) through connected sensors and actuators.

Beyond greenhouse control, this project serves as an **experimentation platform** for developing skills in several areas:

- Frontend applications (Electron desktop, Flutter mobile)
- Artificial intelligence (video analysis, voice assistant)
- Optimization through data analysis
- Modern software architecture (SOLID, microservices)

---

## ✨ Features

### Automated Control

- 📊 **Real-time monitoring**: Temperature, humidity, CO2 (SCD30 sensor)
- 💡 **Smart lighting**: LEDs with configurable schedules
- 💧 **Humidity management**: Humidifier with configurable thresholds
- 🌬️ **Adaptive ventilation**: Automatic exhaust based on CO2 levels

### Control Modes

- 🤖 **Automatic mode**: Autonomous management based on configured settings
- 🎮 **Manual mode**: Direct control through the CLI menu or API
- 🔌 **Simulation**: Mock mode for development without hardware

### Full REST API

- 🌐 **FastAPI**: Modern API with built-in Swagger documentation
- 🔐 **Authentication**: API key authentication (X-API-Key)
- 📱 **Cross-platform**: Compatible with Electron, Flutter, React, Vue, etc.
- 📈 **Historical data**: Data export for analysis

---

## 🏗️ Architecture

```text
Backend (Raspberry Pi)
├── Sensors → SensorService → Orchestrator → ActuatorCoordinator → Actuators
├── Configuration → ConfigurationManager → user_settings.json
├── Data → DataPersistence → SQLite
└── REST API → FastAPI (monitoring + control)
```

**SOLID principles**: A modular architecture with specialized services to make maintenance and future development easier.

---

## 🚀 Quick Start

### Installation

```bash
# Clone the project
git clone https://github.com/Ulysse-Dev-Serre/Projet_IoT_RaspberryPi.git
cd Projet_IoT_RaspberryPi

# Create and activate a virtual environment
python3 -m venv myenv
source myenv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
# Simulation mode (no hardware required)
export HARDWARE_ENV=mock
python main.py

# Hardware mode (with connected devices)
export HARDWARE_ENV=raspberry_pi
export API_KEY="your-secret-key"
python main.py
```

The API documentation will be available at: `http://<RASPBERRY_PI_IP>:5000/docs`

📖 **Full setup guide**: [docs/1-fundation/SETUP.md](docs/1-fundation/SETUP.md)

---

## 📚 Documentation

The detailed documentation linked below is in French.

### Getting Started

- **[docs/1-fundation/SETUP.md](docs/1-fundation/SETUP.md)** - Step-by-step installation
- **[docs/1-fundation/ARCHITECTURE.md](docs/1-fundation/ARCHITECTURE.md)** - Code structure
- **[docs/1-fundation/HARDWARE.md](docs/1-fundation/HARDWARE.md)** - Hardware configuration

### Development

- **[docs/FRONTEND_CONNECT.md](docs/FRONTEND_CONNECT.md)** - ⭐ Connect a frontend application
- **[docs/2-logic/CORE_LOGIC.md](docs/2-logic/CORE_LOGIC.md)** - Business logic
- **[docs/3-api/API_GUIDE.md](docs/3-api/API_GUIDE.md)** - REST API

### Reference

- **[docs/1-fundation/COMMANDES_UTILES.md](docs/1-fundation/COMMANDES_UTILES.md)** - Command reference
- **[docs/INDEX.md](docs/INDEX.md)** - Full documentation index

---

## 🧪 Tests

```bash
# API tests (9 automated tests)
python scripts/test_api_simple.py

# Unit tests
pytest

# Hardware test
python scripts/hardware_test_menu.py
```

---

## 🛠️ Technology Stack

**Backend**:

- Python 3.9+
- FastAPI (REST API)
- SQLite (database)
- lgpio (GPIO control)

**Hardware**:

- Raspberry Pi 5
- SCD30 sensor (I2C)
- 4-channel relay module
- LEDs, fan, ultrasonic humidifier

**Architecture**:

- SOLID principles
- Observer pattern (sensors → orchestrator)
- Dependency injection (orchestrator → API)
- Thread safety (locks for concurrent control)

---

## 🚀 Future Improvements

- [ ] WebSocket for real-time updates (replacing polling)
- [ ] React/Vue web interface
- [ ] Flutter mobile application
- [ ] Electron desktop application
- [ ] AI video analysis (mushroom growth detection)
- [ ] Voice assistant (status, control)
- [ ] Machine learning (environmental optimization)
- [ ] Analytics dashboard with charts
- [ ] CSV/PDF data export
- [ ] Push notifications (alerts)

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the project
2. Create a branch (`git checkout -b feature/improvement`)
3. Commit your changes (`git commit -m 'Add feature X'`)
4. Push to the branch (`git push origin feature/improvement`)
5. Open a pull request

---

## 📄 License

This project is licensed under the [MIT License](LICENSE.md).

---

## 👤 Author

Developed by **Ulysse** as part of studies in systems development.

A project combining a passion for food self-sufficiency and technological innovation.

---

## 🔗 Useful Links

- **Full documentation**: [docs/INDEX.md](docs/INDEX.md)
- **Frontend guide**: [docs/FRONTEND_CONNECT.md](docs/FRONTEND_CONNECT.md)
- **Swagger API documentation**: `http://<RASPBERRY_PI_IP>:5000/docs`
- **Repository**: [GitHub](https://github.com/Ulysse-Dev-Serre/Projet_IoT_RaspberryPi)

---

⭐ **Star this project** if you find it useful!

---

<a id="francais"></a>

[↑ English](#english)

# 🍄 Serre Connectée - Projet IoT Raspberry Pi

Système de contrôle automatisé pour serre à champignons, propulsé par Raspberry Pi.

---

## 🎯 Vision du Projet

Ce projet explore l'**Internet des Objets (IoT)** appliqué à l'agriculture, en combinant autosuffisance alimentaire et innovation technologique. Conçu comme un système de gestion intelligent pour une serre à champignons, il offre un contrôle automatisé de l'environnement (température, humidité, CO2) via des capteurs et actionneurs connectés.

Au-delà du contrôle de serre, ce projet sert de **plateforme d'expérimentation** pour développer des compétences variées :
- Applications frontend (Electron desktop, Flutter mobile)
- Intelligence artificielle (analyse vidéo, assistant vocal)
- Optimisation par analyse de données
- Architecture logicielle moderne (SOLID, microservices)

---

## ✨ Fonctionnalités

### Contrôle Automatisé

- 📊 **Monitoring en temps réel** : Température, humidité, CO2 (capteur SCD30)
- 💡 **Éclairage intelligent** : LEDs programmables par plage horaire
- 💧 **Gestion de l'humidité** : Humidificateur à seuils configurables
- 🌬️ **Ventilation adaptative** : Extraction automatique selon niveau CO2

### Modes de Contrôle

- 🤖 **Mode automatique** : Gestion autonome selon paramètres configurés
- 🎮 **Mode manuel** : Contrôle direct via menu CLI ou API
- 🔌 **Simulation** : Mode mock pour développement sans matériel

### API REST Complète

- 🌐 **FastAPI** : API moderne avec documentation Swagger intégrée
- 🔐 **Authentification** : Sécurisé par token (X-API-Key)
- 📱 **Multi-plateforme** : Compatible Electron, Flutter, React, Vue, etc.
- 📈 **Historique** : Export des données pour analyse

---

## 🏗️ Architecture

```
Backend (Raspberry Pi)
├── Capteurs → SensorService → Orchestrateur → ActuatorCoordinator → Actionneurs
├── Configuration → ConfigurationManager → user_settings.json
├── Données → DataPersistence → SQLite
└── API REST → FastAPI (monitoring + contrôle)
```

**Principe SOLID** : Architecture modulaire avec services spécialisés, facilitant la maintenance et l'évolution.

---

## 🚀 Quick Start

### Installation

```bash
# Cloner le projet
git clone https://github.com/Ulysse-Dev-Serre/Projet_IoT_RaspberryPi.git
cd Projet_IoT_RaspberryPi

# Environnement virtuel
python3 -m venv myenv
source myenv/bin/activate

# Dépendances
pip install -r requirements.txt
```

### Lancement

```bash
# Mode simulation (sans matériel)
export HARDWARE_ENV=mock
python main.py

# Mode réel (avec matériel connecté)
export HARDWARE_ENV=raspberry_pi
export API_KEY="votre-cle-secrete"
python main.py
```

L'API sera accessible sur : `http://<IP_RASPBERRY>:5000/docs`

📖 **Guide complet** : [docs/1-fundation/SETUP.md](docs/1-fundation/SETUP.md)

---

## 📚 Documentation

### Pour Démarrer

- **[docs/1-fundation/SETUP.md](docs/1-fundation/SETUP.md)** - Installation pas à pas
- **[docs/1-fundation/ARCHITECTURE.md](docs/1-fundation/ARCHITECTURE.md)** - Structure du code
- **[docs/1-fundation/HARDWARE.md](docs/1-fundation/HARDWARE.md)** - Configuration matérielle

### Pour Développer

- **[docs/FRONTEND_CONNECT.md](docs/FRONTEND_CONNECT.md)** - ⭐ Connecter une app frontend
- **[docs/2-logic/CORE_LOGIC.md](docs/2-logic/CORE_LOGIC.md)** - Logique métier
- **[docs/3-api/API_GUIDE.md](docs/3-api/API_GUIDE.md)** - API REST

### Pour Référence

- **[docs/1-fundation/COMMANDES_UTILES.md](docs/1-fundation/COMMANDES_UTILES.md)** - Toutes les commandes
- **[docs/INDEX.md](docs/INDEX.md)** - Navigation complète

---

## 🧪 Tests

```bash
# Tests API (9 tests automatiques)
python scripts/test_api_simple.py

# Tests unitaires
pytest

# Test matériel
python scripts/hardware_test_menu.py
```

---

## 🛠️ Stack Technique

**Backend** :
- Python 3.9+
- FastAPI (API REST)
- SQLite (base de données)
- lgpio (contrôle GPIO)

**Matériel** :
- Raspberry Pi 5
- Capteur SCD30 (I2C)
- Relais 4 canaux
- LEDs, ventilateur, humidificateur ultrasonique

**Architecture** :
- SOLID principles
- Observer pattern (capteurs → orchestrateur)
- Dependency injection (orchestrateur → API)
- Thread-safe (verrous pour contrôle concurrent)

---

## 🚀 Évolutions Futures

- [ ] WebSocket pour temps réel (remplacer polling)
- [ ] Interface web React/Vue
- [ ] Application mobile Flutter
- [ ] Application desktop Electron
- [ ] IA analyse vidéo (détection croissance champignons)
- [ ] Assistant vocal (statut, contrôle)
- [ ] Machine learning (optimisation environnement)
- [ ] Dashboard analytics avec graphiques
- [ ] Export CSV/PDF des données
- [ ] Notifications push (alertes)

---

## 🤝 Contribuer

Les contributions sont bienvenues !

1. Fork le projet
2. Créez une branche (`git checkout -b feature/amelioration`)
3. Committez vos changements (`git commit -m 'Ajout fonctionnalité X'`)
4. Push vers la branche (`git push origin feature/amelioration`)
5. Ouvrez une Pull Request

---

## 📄 Licence

Ce projet est sous licence [MIT](LICENSE.md).

---

## 👤 Auteur

Développé par **Ulysse** dans le cadre d'études en développement de systèmes.

Projet combinant passion pour l'autosuffisance alimentaire et innovation technologique.

---

## 🔗 Liens Utiles

- **Documentation complète** : [docs/INDEX.md](docs/INDEX.md)
- **Guide frontend** : [docs/FRONTEND_CONNECT.md](docs/FRONTEND_CONNECT.md)
- **API Swagger** : `http://<IP_RASPBERRY>:5000/docs`
- **Repository** : [GitHub](https://github.com/Ulysse-Dev-Serre/Projet_IoT_RaspberryPi)

---

⭐ **Star ce projet** si vous le trouvez utile !
