# src/config.py
import os
import logging

# --- Définition du répertoire de base du projet ---
# Cela aide à construire des chemins absolus pour les fichiers de données et de logs,
# ce qui est plus robuste que les chemins relatifs.
# __file__ est le chemin vers ce fichier config.py (src/config.py)
# os.path.dirname(__file__) est le répertoire src/
# os.path.dirname(os.path.dirname(__file__)) est le répertoire racine du projet (gestion_serre/)
PROJECT_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Configuration de l'Environnement ---
HARDWARE_ENV = os.getenv('HARDWARE_ENV', 'raspberry_pi') # Défaut à 'raspberry_pi'
DB_ENV = os.getenv('DB_ENV', 'prod')

# --- Configurations de la Base de Données ---
DB_CONFIG_PROD = {
    "database": os.getenv('DB_NAME_PROD', "serre_connectee"),
    "user": os.getenv('DB_USER_PROD', "ulysse"),
    "password": os.getenv('DB_PASSWORD_PROD', "1234"),
    "host": os.getenv('DB_HOST_PROD', "localhost"),
    "port": os.getenv('DB_PORT_PROD', "5432"),
    "client_encoding": "UTF8"
}

DB_CONFIG_TEST = {
    "database": os.getenv('DB_NAME_TEST', "serre_test"),
    "user": os.getenv('DB_USER_TEST', "ulysse"),
    "password": os.getenv('DB_PASSWORD_TEST', "1234"),
    "host": os.getenv('DB_HOST_TEST', "10.0.0.216"),
    "port": os.getenv('DB_PORT_TEST', "5432"),
    "client_encoding": "UTF8"
}

ACTIVE_DB_CONFIG = DB_CONFIG_PROD if DB_ENV == 'prod' else DB_CONFIG_TEST

# --- Constantes pour les Intervalles et Buffers (Base de Données) ---
INTERVALLE_LECTURE_CAPTEURS_SECONDES = 60
INTERVALLE_LECTURE_RAPIDE_CAPTEURS_SECONDES = 15 # Pour le thread d'acquisition
FLUSH_INTERVAL_BUFFER_SECONDES = 300
BUFFER_SIZE_MAX = 10

# --- Configuration du Logging ---
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
# Chemin de log construit de manière plus robuste
LOG_FILE_PATH = os.path.join(PROJECT_ROOT_DIR, 'data', 'logs', 'serre_controller.log')

# --- Configuration de l'Application Flask ---
APP_HOST = '0.0.0.0'
APP_PORT = 5000
APP_DEBUG_MODE = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']

# --- NOMS DES CLÉS DE CONFIGURATION (pour la cohérence) ---
# Utilisés comme clés dans DEFAULT_SETTINGS et lus depuis user_settings.json
KEY_HEURE_DEBUT_LEDS = "HEURE_DEBUT_LEDS"
KEY_HEURE_FIN_LEDS = "HEURE_FIN_LEDS"
KEY_SEUIL_HUMIDITE_ON = "SEUIL_HUMIDITE_ON"
KEY_SEUIL_HUMIDITE_OFF = "SEUIL_HUMIDITE_OFF"
KEY_SEUIL_CO2_MAX = "SEUIL_CO2_MAX"
KEY_HEURE_DEBUT_JOUR_OPERATION = "HEURE_DEBUT_JOUR_OPERATION"
KEY_HEURE_FIN_JOUR_OPERATION = "HEURE_FIN_JOUR_OPERATION"

# Clés pour les broches GPIO et noms/identifiants de capteurs
KEY_PIN_LEDS = "PIN_LEDS"
KEY_PIN_VENTILATION = "PIN_VENTILATION"
KEY_PIN_FAN_HUMIDIFICATEUR = "PIN_FAN_HUMIDIFICATEUR"
KEY_PIN_BRUMISATEUR = "PIN_BRUMISATEUR"
KEY_NOM_CAPTEUR_CO2 = "NOM_CAPTEUR_CO2" # Nom utilisé pour récupérer la valeur CO2 du dict des capteurs
# Ajoutez d'autres clés pour les noms de capteurs si nécessaire (ex: KEY_NOM_CAPTEUR_TEMPERATURE_HUMIDITE)

# --- VALEURS PAR DÉFAUT POUR TOUS LES PARAMÈTRES ---
# Ce dictionnaire sert de base et est surchargé par user_settings.json
DEFAULT_SETTINGS = {
    KEY_HEURE_DEBUT_LEDS: 8,
    KEY_HEURE_FIN_LEDS: 20,
    KEY_SEUIL_HUMIDITE_ON: 75.0,
    KEY_SEUIL_HUMIDITE_OFF: 84.9,
    KEY_SEUIL_CO2_MAX: 1200.0,
    KEY_HEURE_DEBUT_JOUR_OPERATION: 0, # Heure de début générale des opérations (ex: humidificateur, ventilation)
    KEY_HEURE_FIN_JOUR_OPERATION: 24,   # Heure de fin générale des opérations

    # Valeurs par défaut pour les broches (numérotation BCM pour Raspberry Pi)
    KEY_PIN_LEDS: 27,
    KEY_PIN_VENTILATION: 22,
    KEY_PIN_FAN_HUMIDIFICATEUR: 26,
    KEY_PIN_BRUMISATEUR: 13,

    # Valeur par défaut pour le nom/clé du capteur CO2 dans le dictionnaire de données des capteurs
    # (ex: si les données des capteurs sont {'MonCapteurCO2': 600, ...})
    # Si les données sont plus simples comme {'co2': 600}, cette clé n'est pas cruciale pour la lecture
    # mais peut être utilisée pour la configuration ou l'affichage.
    # Pour l'instant, vos actuateurs lisent directement `current_sensor_data.get('co2')`.
    # Si vous voulez rendre la clé 'co2' elle-même configurable, il faudrait adapter les actuateurs.
    # Gardons-le pour l'information et la cohérence.
    KEY_NOM_CAPTEUR_CO2: "co2" # Correspond à la clé 'co2' que les actuateurs utilisent actuellement
}

# --- CHEMIN VERS LE FICHIER DES CONFIGURATIONS UTILISATEUR ---
USER_SETTINGS_FILE = os.path.join(PROJECT_ROOT_DIR, 'data', 'user_settings.json')

# --- EXPOSITION DES CONSTANTES AU NIVEAU DU MODULE ---
# Ces variables sont initialisées avec les valeurs de DEFAULT_SETTINGS.
# Elles peuvent être utilisées pour les valeurs par défaut dans les constructeurs
# ou pour un accès direct dans les tests.
# La logique principale dans les actuateurs devrait toujours privilégier
# `self.controller.get_setting(KEY_XXX, DEFAULT_XXX)` pour obtenir la valeur la plus à jour
# (qui inclut les surcharges de user_settings.json).

# Paramètres de fonctionnement
HEURE_DEBUT_LEDS = DEFAULT_SETTINGS[KEY_HEURE_DEBUT_LEDS]
HEURE_FIN_LEDS = DEFAULT_SETTINGS[KEY_HEURE_FIN_LEDS]
SEUIL_HUMIDITE_ON = DEFAULT_SETTINGS[KEY_SEUIL_HUMIDITE_ON]
SEUIL_HUMIDITE_OFF = DEFAULT_SETTINGS[KEY_SEUIL_HUMIDITE_OFF]
CO2_MAX_THRESHOLD = DEFAULT_SETTINGS[KEY_SEUIL_CO2_MAX] # Alias pour la ventilation
HEURE_DEBUT_JOUR_OPERATION = DEFAULT_SETTINGS[KEY_HEURE_DEBUT_JOUR_OPERATION]
HEURE_FIN_JOUR_OPERATION = DEFAULT_SETTINGS[KEY_HEURE_FIN_JOUR_OPERATION]

# Broches GPIO (utilisées par raspberry_pi.py et potentiellement les tests)
PIN_LEDS = DEFAULT_SETTINGS[KEY_PIN_LEDS]
VENTILATION_OUTPUT_PIN = DEFAULT_SETTINGS[KEY_PIN_VENTILATION] # Alias pour la ventilation
PIN_FAN_HUMIDIFICATEUR = DEFAULT_SETTINGS[KEY_PIN_FAN_HUMIDIFICATEUR]
PIN_BRUMISATEUR = DEFAULT_SETTINGS[KEY_PIN_BRUMISATEUR]

# Noms/Identifiants de capteurs (utilisés par les tests et potentiellement les constructeurs)
CO2_SENSOR_INSTANCE_NAME = DEFAULT_SETTINGS[KEY_NOM_CAPTEUR_CO2] # Alias pour la ventilation

# --- Logger pour ce module de configuration ---
_config_module_logger = logging.getLogger("src.config") # Nom plus spécifique
# Assurer une configuration minimale du logger si ce module est importé avant la config principale du logging
if not _config_module_logger.hasHandlers() and not logging.getLogger().hasHandlers():
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _handler.setFormatter(_formatter)
    _config_module_logger.addHandler(_handler)
    # Le niveau sera défini par la configuration globale du logging dans main.py ou app.py
    # mais on peut en mettre un par défaut ici si nécessaire.
    _config_module_logger.setLevel(LOG_LEVEL if LOG_LEVEL else logging.INFO)


_config_module_logger.info(f"Configuration (src/config.py) chargée: HARDWARE_ENV='{HARDWARE_ENV}', DB_ENV='{DB_ENV}'")
_config_module_logger.info(f"ACTIVE_DB_CONFIG: {ACTIVE_DB_CONFIG}")
_config_module_logger.info(f"Fichier de paramètres utilisateur attendu à: {USER_SETTINGS_FILE}")
_config_module_logger.info(f"Valeurs par défaut (DEFAULT_SETTINGS) chargées.")




