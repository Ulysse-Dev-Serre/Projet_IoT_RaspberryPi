# Gestion de Serre Connectée (Partie du Projet OvoOx-GreenHouse)

Ce projet est le système de contrôle backend pour une serre à champignons automatisée, développé en Python. Il est conçu pour fonctionner sur un Raspberry Pi, gérer des capteurs (température, humidité, CO2), et contrôler des actionneurs (LEDs, humidificateur, ventilation) afin de maintenir des conditions optimales pour la culture.

## Fonctionnalités Principales

* Lecture des données de capteurs (SCD30 pour température, humidité, CO2).
* Contrôle automatisé des LEDs basé sur des plages horaires.
* Contrôle automatisé de l'humidificateur basé sur des seuils d'humidité et des plages horaires.
* Contrôle automatisé de la ventilation basé sur des seuils de CO2 et des plages horaires.
* Modes de contrôle manuel pour chaque actionneur via une API web.
* Enregistrement des données de capteurs et de l'état des actionneurs dans une base de données PostgreSQL.
* Interface web simple (via Flask) pour visualiser l'état et contrôler les appareils.
* Architecture modulaire pour faciliter la maintenance et l'évolution.
* Support pour le matériel réel (Raspberry Pi avec GPIO/I2C) et un mode simulé (`mock`) pour le développement et les tests sur d'autres plateformes.

## Prérequis

* Python 3.9+
* Raspberry Pi (pour le déploiement avec matériel réel, testé sur Raspberry Pi OS)
* Capteur SCD30 (pour température, humidité, CO2)
* Relais pour contrôler les actionneurs (LEDs, ventilateur, brumisateur)
* Base de données PostgreSQL (accessible localement ou à distance)
* Git (pour la gestion de version)

## Structure du Projet (`gestion_serre/`)

```
gestion_serre/
│
├── config.py               # Fichier de configuration central (seuils, identifiants BD, etc.)
├── main.py                 # Point d'entrée pour lancer le contrôleur en mode autonome (CLI)
├── hardware_test_menu.py   # Script pour tester manuellement le matériel sur Raspberry Pi
├── requirements.txt        # Dépendances Python du projet
├── serre_controller.log    # Fichier de log par défaut
│
├── src/                    # Code source de l'application
│   ├── api/                # Application Flask (API web et interface)
│   │   ├── app.py
│   │   └── templates/
│   │       └── index.html
│   ├── core/               # Logique métier principale
│   │   ├── serre_logic.py  # SerreController principal
│   │   └── actuators/      # Contrôleurs pour chaque actionneur
│   ├── hardware_interface/ # Abstraction matérielle (réel et mock)
│   │   ├── raspberry_pi.py
│   │   └── mock_hardware.py
│   └── utils/              # Utilitaires (ex: gestion BD, config logging)
│       └── db_utils.py
│
└── tests/                  # Tests automatisés (pytest)
    ├── unit/               # Tests unitaires
    └── integration/        # Tests d'intégration
```

## Installation et Configuration

1.  **Cloner le dépôt principal (si ce n'est pas déjà fait) :**
    ```bash
    git clone [https://github.com/Ulysse-Dev-Serre/Projet-OvoOx-GreenHouse.git](https://github.com/Ulysse-Dev-Serre/Projet-OvoOx-GreenHouse.git)
    cd Projet-OvoOx-GreenHouse/gestion_serre
    ```

2.  **Créer un environnement virtuel Python et l'activer :**
    ```bash
    python3 -m venv myenv
    source myenv/bin/activate  # Sur Linux/macOS
    # myenv\Scripts\activate    # Sur Windows
    ```

3.  **Installer les dépendances :**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurer `config.py` :**
    * Copiez ou adaptez `config.py` si nécessaire.
    * Les configurations principales sont gérées par des **variables d'environnement** pour plus de flexibilité, avec des valeurs par défaut dans `config.py`.

5.  **Configuration des Variables d'Environnement (Crucial !) :**
    Avant de lancer l'application, définissez les variables d'environnement suivantes dans votre terminal :

    * `HARDWARE_ENV`:
        * `mock`: (Défaut) Utilise le matériel simulé. Idéal pour le développement sur PC.
        * `raspberry_pi`: Utilise le matériel réel sur un Raspberry Pi.
    * `DB_ENV`:
        * `test`: (Défaut) Utilise la configuration `DB_CONFIG_TEST` de `config.py`.
        * `prod`: Utilise la configuration `DB_CONFIG_PROD` de `config.py`.
    * `DB_USER_PROD`, `DB_PASSWORD_PROD`, `DB_HOST_PROD`, etc. (et leurs équivalents `_TEST`):
        Peuvent être définis pour surcharger les identifiants de base de données directement, bien que les valeurs par défaut soient dans `config.py`.

    **Exemple sur Linux/macOS (pour Raspberry Pi avec matériel réel et BD de production) :**
    ```bash
    export HARDWARE_ENV=raspberry_pi
    export DB_ENV=prod
    export DB_USER_PROD="votre_user_prod"
    export DB_PASSWORD_PROD="votre_mdp_prod"
    ```
    **Exemple sur Windows PowerShell (pour développement avec mock et BD de test) :**
    ```powershell
    $env:HARDWARE_ENV="mock"
    $env:DB_ENV="test"
    ```

6.  **Base de Données PostgreSQL :**
    * Assurez-vous que votre serveur PostgreSQL est en cours d'exécution et accessible.
    * Créez les bases de données (`serre_connectee`, `serre_test`) et l'utilisateur si nécessaire.
    * Créez la table `sensor_data`. Vous pouvez utiliser le script `Donnees.sql`  la structure suivante :
        ```sql
        CREATE TABLE sensor_data (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            temperature DOUBLE PRECISION,
            humidity DOUBLE PRECISION,
            co2 DOUBLE PRECISION,
            humidifier_active BOOLEAN,
            ventilation_active BOOLEAN,
            leds_active BOOLEAN,
            humidifier_on_duration_seconds DOUBLE PRECISION,
            humidifier_off_duration_seconds DOUBLE PRECISION,
            ventilation_on_duration_seconds DOUBLE PRECISION,
            ventilation_off_duration_seconds DOUBLE PRECISION
        );
        ```
        *(Assurez-vous que les noms de colonnes correspondent à ceux utilisés dans `src/utils/db_utils.py`)*

## Utilisation

### 1. Test Manuel du Matériel (sur Raspberry Pi uniquement)

Ce script permet de vérifier chaque composant matériel individuellement.
```bash
# Assurez-vous que l'environnement virtuel est activé
# Pas besoin de HARDWARE_ENV pour ce script, il force l'utilisation du matériel RPi.
python hardware_test_menu.py
```
Suivez les instructions du menu.

### 2. Lancer le Contrôleur de Serre en Mode Autonome (CLI)

Cela lance la logique de la serre sans l'interface web. Les logs s'affichent en console et dans `serre_controller.log`.
```bash
# Définir HARDWARE_ENV et DB_ENV selon les besoins
# Exemple:
# export HARDWARE_ENV=raspberry_pi
# export DB_ENV=prod

python main.py
```
Appuyez sur `Ctrl+C` pour arrêter.

### 3. Lancer le Contrôleur de Serre avec l'Interface Web (Flask)

Cela lance la logique de la serre ET le serveur web Flask.
```bash
# Définir HARDWARE_ENV et DB_ENV selon les besoins
# Exemple:
# export HARDWARE_ENV=raspberry_pi
# export DB_ENV=prod

python src/api/app.py
```
Accédez à l'interface via votre navigateur à l'adresse affichée (par défaut `http://0.0.0.0:5000` ou `http://<IP_DU_RASPBERRY_PI>:5000`).

## Tests Automatisés (pytest)

Pour exécuter les tests unitaires et d'intégration (à développer) :
```bash
# Depuis la racine du dossier gestion_serre, avec l'environnement virtuel activé
pytest
```

## Contribuer

Les contributions sont les bienvenues ! Veuillez ouvrir une issue pour discuter des changements majeurs.

## Licence

Ce projet est sous licence [MIT](LICENSE.md) ().














