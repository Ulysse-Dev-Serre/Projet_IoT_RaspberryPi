# config.py
import os
import logging

# --- Configuration de l'Environnement et de la Base de Données ---
HARDWARE_ENV = os.getenv('HARDWARE_ENV', 'mock')
DB_ENV = os.getenv('DB_ENV', 'test')

# S'assurer que ce sont bien des dictionnaires
DB_CONFIG_PROD = {
    "database": os.getenv('DB_NAME_PROD', "serre_connectee"), # Clé renommée pour clarté
    "user": os.getenv('DB_USER_PROD', "ulysse"), 
    "password": os.getenv('DB_PASSWORD_PROD', "1234"),
    "host": os.getenv('DB_HOST_PROD', "localhost"),
    "port": os.getenv('DB_PORT_PROD', "5432"),
    "client_encoding": "UTF8"
}

DB_CONFIG_TEST = {
    "database": os.getenv('DB_NAME_TEST', "serre_test"), # Clé renommée pour clarté
    "user": os.getenv('DB_USER_TEST', "ulysse"),
    "password": os.getenv('DB_PASSWORD_TEST', "1234"),
    "host": os.getenv('DB_HOST_TEST', "10.0.0.216"), 
    "port": os.getenv('DB_PORT_TEST', "5432"),
    "client_encoding": "UTF8"
}

# Sélection de la configuration DB active
if DB_ENV == 'prod':
    ACTIVE_DB_CONFIG = DB_CONFIG_PROD
else: # Par défaut 'test' ou toute autre valeur
    ACTIVE_DB_CONFIG = DB_CONFIG_TEST

# --- Constantes pour les Intervalles et Buffers ---
INTERVALLE_LECTURE_CAPTEURS_SECONDES = 60
INTERVALLE_LECTURE_RAPIDE_CAPTEURS_SECONDES = 15
FLUSH_INTERVAL_BUFFER_SECONDES = 300
BUFFER_SIZE_MAX = 10

# --- Configuration du Logging ---
LOG_FILE_PATH = 'data/logs/serre_controller.log'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

# --- Configuration de l'Application Flask ---
APP_HOST = '0.0.0.0'
APP_PORT = 5000
APP_DEBUG_MODE = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']

# --- CHEMIN VERS LE FICHIER DES CONFIGURATIONS UTILISATEUR ---
USER_SETTINGS_FILE = os.path.join('data', 'user_settings.json')

# --- VALEURS PAR DÉFAUT POUR LES PARAMÈTRES CONFIGURABLES PAR L'UTILISATEUR VIA L'UI ---
DEFAULT_SETTINGS = {
    "HEURE_DEBUT_LEDS": 8,
    "HEURE_FIN_LEDS": 20,
    "SEUIL_HUMIDITE_ON": 75.0,
    "SEUIL_HUMIDITE_OFF": 84.9,
    "SEUIL_CO2_MAX": 1200.0,
    "HEURE_DEBUT_JOUR_OPERATION": 8,
    "HEURE_FIN_JOUR_OPERATION": 22
}

# Logger pour ce module
_config_module_logger = logging.getLogger("config_module") # Nom unique pour le logger
if not _config_module_logger.hasHandlers():
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _handler.setFormatter(_formatter)
    _config_module_logger.addHandler(_handler)
    _config_module_logger.setLevel(LOG_LEVEL) # Utiliser LOG_LEVEL défini plus haut

_config_module_logger.info(f"Configuration (config.py) chargée: HARDWARE_ENV='{HARDWARE_ENV}', DB_ENV='{DB_ENV}'")
_config_module_logger.info(f"ACTIVE_DB_CONFIG type: {type(ACTIVE_DB_CONFIG)}, value: {ACTIVE_DB_CONFIG}") # Log pour vérifier
_config_module_logger.info(f"Fichier de paramètres utilisateur attendu à: {USER_SETTINGS_FILE}")
_config_module_logger.info(f"Paramètres par défaut pour l'UI chargés: {DEFAULT_SETTINGS}")


