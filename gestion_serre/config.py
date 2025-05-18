# config.py
import os

# Configuration de l'environnement matériel : 'raspberry_pi' ou 'mock'
# Vous pouvez définir cette variable d'environnement avant de lancer votre application.
# Exemple: HARDWARE_ENV=raspberry_pi python src/api/app.py
HARDWARE_ENV = os.getenv('HARDWARE_ENV', 'mock')  # Par défaut 'mock'

# Configuration de l'environnement de la base de données : 'prod' ou 'test'
DB_ENV = os.getenv('DB_ENV', 'test') # Par défaut 'test'

# Configurations de la base de données
DB_CONFIG_PROD = {
    "database": "serre_connectee",
    "user": os.getenv('DB_USER_PROD', "ulysse"), # Utiliser des variables d'environnement pour les identifiants
    "password": os.getenv('DB_PASSWORD_PROD', "1234"),
    "host": os.getenv('DB_HOST_PROD', "localhost"),
    "port": os.getenv('DB_PORT_PROD', "5432"),
    "client_encoding": "UTF8"
}

DB_CONFIG_TEST = {
    "database": "serre_test",
    "user": os.getenv('DB_USER_TEST', "ulysse"),
    "password": os.getenv('DB_PASSWORD_TEST', "1234"),
    "host": os.getenv('DB_HOST_TEST', "10.0.0.216"), # Exemple d'IP pour une BD de test
    "port": os.getenv('DB_PORT_TEST', "5432"),
    "client_encoding": "UTF8"
}

ACTIVE_DB_CONFIG = DB_CONFIG_PROD if DB_ENV == 'prod' else DB_CONFIG_TEST

# Seuils et paramètres de la serre
SEUIL_HUMIDITE_ON = 75.0
SEUIL_HUMIDITE_OFF = 84.9  # Hystérésis: s'éteint à une valeur plus haute que celle d'allumage
SEUIL_CO2_MAX = 1200.0 # ppm - Ajustez selon les besoins de vos champignons

# Horaires pour les LEDs (mode automatique)
HEURE_DEBUT_LEDS = 8  # 8h du matin
HEURE_FIN_LEDS = 20   # 20h (8h du soir)

# Intervalles de temps (en secondes)
INTERVALLE_LECTURE_CAPTEURS_SECONDES = 60  # Pour la logique principale et la sauvegarde BD
INTERVALLE_LECTURE_RAPIDE_CAPTEURS_SECONDES = 15 # Pour l'affichage en temps réel (API status)

# Configuration du buffer de la base de données
FLUSH_INTERVAL_BUFFER_SECONDES = 300  # Vidage du buffer toutes les 5 minutes
BUFFER_SIZE_MAX = 10  # Nombre d'enregistrements avant vidage forcé du buffer

# Configuration du logging
LOG_FILE_PATH = 'data/logs/serre_controller.log' # Chemin vers le fichier de log
LOG_LEVEL = 'INFO' # Niveaux: DEBUG, INFO, WARNING, ERROR, CRITICAL


# Autres configurations spécifiques à l'application
APP_HOST = '0.0.0.0'
APP_PORT = 5000
APP_DEBUG_MODE = False # Mettre à True seulement pour le développement

print(f"Configuration chargée: HARDWARE_ENV='{HARDWARE_ENV}', DB_ENV='{DB_ENV}'")
