# src/utils/db_utils.py
import psycopg2
from psycopg2 import pool
import logging
import time
from datetime import datetime

# Tenter d'importer la configuration ACTIVE_DB_CONFIG et les paramètres du buffer
try:
    from config import ACTIVE_DB_CONFIG, BUFFER_SIZE_MAX, FLUSH_INTERVAL_BUFFER_SECONDES
except ImportError:
    logging.critical("Fichier config.py ou configurations de base de données/buffer manquantes!")
    # Définir des valeurs par défaut pour éviter un crash immédiat, mais l'application sera limitée.
    ACTIVE_DB_CONFIG = {} # Vide, causera une erreur à la connexion mais évite NameError
    BUFFER_SIZE_MAX = 10
    FLUSH_INTERVAL_BUFFER_SECONDES = 300
    # Il serait préférable de lever une exception ici si la config est essentielle.
    # raise ImportError("Configuration de base de données non trouvée dans config.py")


class DatabaseManager:
    def __init__(self):
        self.db_pool = None
        self.data_buffer = []
        self.last_flush_time = time.time()
        
        if not ACTIVE_DB_CONFIG: # Si la config est vide (erreur d'import)
            logging.error("Configuration de la base de données (ACTIVE_DB_CONFIG) est vide. DatabaseManager ne pourra pas se connecter.")
            return

        try:
            # minconn = 1, maxconn = 5 (ou configurable)
            self.db_pool = psycopg2.pool.SimpleConnectionPool(1, 5, **ACTIVE_DB_CONFIG)
            logging.info(f"Pool de connexions à la base de données initialisé pour '{ACTIVE_DB_CONFIG.get('database')}' sur '{ACTIVE_DB_CONFIG.get('host')}'.")
            self._test_connection()
        except psycopg2.Error as e:
            logging.error(f"Erreur lors de l'initialisation du pool de connexions PostgreSQL: {e}")
            self.db_pool = None # S'assurer que le pool est None en cas d'échec
        except Exception as e: # Attraper d'autres exceptions potentielles (ex: config malformée)
            logging.error(f"Erreur inattendue lors de l'initialisation de DatabaseManager: {e}")
            self.db_pool = None


    def _test_connection(self):
        """Tente d'obtenir et de remettre une connexion pour tester le pool."""
        if not self.db_pool:
            return
        conn = None
        try:
            conn = self.db_pool.getconn()
            if conn:
                logging.info("Connexion à la base de données réussie (test initial).")
            else:
                logging.error("Échec de l'obtention d'une connexion depuis le pool (test initial).")
        except psycopg2.Error as e:
            logging.error(f"Échec du test de connexion à la base de données: {e}")
        finally:
            if conn:
                self.db_pool.putconn(conn)

    def add_sensor_data_to_buffer(self, timestamp: datetime, temperature: float | None, humidity: float | None, co2: float | None,
                                  humidifier_active: bool, ventilation_active: bool, leds_active: bool,
                                  humidifier_on_duration: float | None, humidifier_off_duration: float | None,
                                  ventilation_on_duration: float | None, ventilation_off_duration: float | None):
        """
        Ajoute un enregistrement de données de capteurs au buffer.
        Les durées sont en secondes.
        """
        record = (
            timestamp,
            round(temperature, 1) if temperature is not None else None,
            round(humidity, 1) if humidity is not None else None,
            round(co2, 0) if co2 is not None else None, # CO2 souvent en entier
            humidifier_active,
            ventilation_active,
            leds_active,
            round(humidifier_on_duration, 1) if humidifier_on_duration is not None else None,
            round(humidifier_off_duration, 1) if humidifier_off_duration is not None else None,
            round(ventilation_on_duration, 1) if ventilation_on_duration is not None else None,
            round(ventilation_off_duration, 1) if ventilation_off_duration is not None else None
        )
        self.data_buffer.append(record)
        logging.debug(f"Donnée ajoutée au buffer. Taille actuelle: {len(self.data_buffer)}")

        # Vérifier s'il faut vider le buffer (taille ou temps écoulé)
        current_time = time.time()
        if len(self.data_buffer) >= BUFFER_SIZE_MAX or \
           (current_time - self.last_flush_time) >= FLUSH_INTERVAL_BUFFER_SECONDES:
            self.flush_buffer()

    def flush_buffer(self):
        """
        Insère toutes les données du buffer dans la base de données.
        """
        if not self.data_buffer:
            return

        if not self.db_pool:
            logging.error("Pool de connexions non disponible. Impossible de vider le buffer.")
            # Conserver les données dans le buffer pour une tentative ultérieure ?
            # Ou les logger/sauvegarder ailleurs ? Pour l'instant, on les garde.
            return

        conn = None
        max_retries = 2 # Nombre de nouvelles tentatives en cas d'échec de connexion/commit
        attempt = 0
        
        # Copier le buffer actuel pour le traitement, et vider le buffer principal
        # pour accepter de nouvelles données pendant que celles-ci sont insérées.
        # Ceci est une approche simple. Pour une robustesse accrue, des mécanismes de file d'attente
        # plus complexes pourraient être nécessaires.
        buffer_to_flush = list(self.data_buffer)
        self.data_buffer.clear() # Vider le buffer principal
        
        logging.info(f"Tentative d'insertion de {len(buffer_to_flush)} enregistrements depuis le buffer.")

        while attempt <= max_retries:
            try:
                conn = self.db_pool.getconn()
                if not conn:
                    logging.error("Impossible d'obtenir une connexion depuis le pool.")
                    # Remettre les données dans le buffer si la connexion échoue ?
                    # self.data_buffer.extend(buffer_to_flush) # Risque de duplication si clear() a déjà eu lieu
                    # Pour l'instant, on logue l'erreur. Les données dans buffer_to_flush seront perdues pour ce cycle.
                    return

                with conn.cursor() as cur:
                    # Assurez-vous que le nombre de %s correspond au nombre de colonnes
                    # et à l'ordre des champs dans votre table `sensor_data`.
                    # La table doit avoir 11 colonnes comme les 11 %s.
                    sql_insert_query = """
                        INSERT INTO sensor_data (
                            timestamp, temperature, humidity, co2,
                            humidifier_active, ventilation_active, leds_active,
                            humidifier_on_duration_seconds, humidifier_off_duration_seconds,
                            ventilation_on_duration_seconds, ventilation_off_duration_seconds
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    # executemany est plus performant pour les insertions multiples
                    cur.executemany(sql_insert_query, buffer_to_flush)
                conn.commit()
                logging.info(f"{len(buffer_to_flush)} enregistrements insérés avec succès dans sensor_data.")
                self.last_flush_time = time.time()
                return # Sortir de la boucle et de la fonction après succès

            except psycopg2.Error as e:
                logging.error(f"Erreur lors de l'insertion dans la base de données (tentative {attempt + 1}/{max_retries + 1}): {e}")
                if conn:
                    try:
                        conn.rollback() # Annuler la transaction en cas d'erreur
                    except psycopg2.Error as rb_err:
                        logging.error(f"Erreur lors du rollback: {rb_err}")
                
                attempt += 1
                if attempt <= max_retries:
                    logging.info(f"Nouvel essai dans {2**attempt} secondes...") # Backoff exponentiel simple
                    time.sleep(2**attempt) 
                else:
                    logging.critical(f"Échec définitif de l'insertion de {len(buffer_to_flush)} enregistrements après {max_retries + 1} tentatives.")
                    # Que faire des données non insérées ? Les logger ? Les sauvegarder dans un fichier ?
                    # Pour l'instant, elles sont perdues après les tentatives.
                    # Vous pourriez les remettre dans self.data_buffer si vous voulez réessayer plus tard,
                    # mais attention à la taille du buffer.
                    # Exemple: self.data_buffer.extend(buffer_to_flush) # Risque de grossir indéfiniment
                    return # Abandonner après les tentatives
            except Exception as e: # Autres erreurs non-psycopg2
                logging.critical(f"Erreur inattendue lors du vidage du buffer: {e}")
                # Gérer le rollback si la connexion a été établie
                if conn:
                    try: conn.rollback()
                    except: pass
                return # Abandonner
            finally:
                if conn:
                    self.db_pool.putconn(conn) # Toujours remettre la connexion au pool

    def close_pool(self):
        """Ferme toutes les connexions dans le pool."""
        if self.db_pool:
            # Vider une dernière fois le buffer avant de fermer
            logging.info("Vidage final du buffer avant la fermeture du pool de connexions...")
            self.flush_buffer()
            
            self.db_pool.closeall()
            logging.info("Pool de connexions à la base de données fermé.")
            self.db_pool = None

# Exemple d'utilisation (pourrait être dans des tests unitaires)
if __name__ == '__main__':
    # Configuration minimale pour le test (normalement dans config.py)
    ACTIVE_DB_CONFIG = {
        "database": "serre_test", "user": "ulysse", "password": "1234",
        "host": "localhost", "port": "5432", "client_encoding": "UTF8"
    }
    BUFFER_SIZE_MAX = 3 
    FLUSH_INTERVAL_BUFFER_SECONDES = 5 

    logging.basicConfig(level=logging.DEBUG)
    
    db_manager = DatabaseManager()
    if db_manager.db_pool: # S'assurer que le pool est initialisé
        print("DatabaseManager initialisé. Ajout de données de test...")
        try:
            db_manager.add_sensor_data_to_buffer(datetime.now(), 20.1, 60.5, 800, True, False, True, 120, None, None, 300)
            time.sleep(1)
            db_manager.add_sensor_data_to_buffer(datetime.now(), 20.5, 61.0, 850, True, True, True, 180, None, 60, None)
            time.sleep(1)
            db_manager.add_sensor_data_to_buffer(datetime.now(), 21.0, 60.0, 750, False, True, True, None, 30, 120, None) # Ceci devrait déclencher un flush (BUFFER_SIZE_MAX = 3)
            
            print(f"Buffer après 3 ajouts (devrait être vide si flush OK): {len(db_manager.data_buffer)}")

            time.sleep(7) # Attendre plus que FLUSH_INTERVAL_BUFFER_SECONDES
            db_manager.add_sensor_data_to_buffer(datetime.now(), 19.0, 65.5, 900, True, False, False, 30, None, None, 600) # Ceci devrait déclencher un flush par temps
            print(f"Buffer après attente et 1 ajout (devrait être vide si flush OK): {len(db_manager.data_buffer)}")

        finally:
            print("Fermeture du pool de connexions.")
            db_manager.close_pool()
    else:
        print("Échec de l'initialisation de DatabaseManager. Vérifiez la configuration et la connexion à la base de données.")

