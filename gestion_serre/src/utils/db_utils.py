# src/utils/db_utils.py
import psycopg2
from psycopg2 import pool
import logging
import time
from datetime import datetime

# Essayer d'importer les configurations spécifiques.
# Si cela échoue, des valeurs par défaut locales à ce module seront utilisées.
try:
    from src.config import ACTIVE_DB_CONFIG, BUFFER_SIZE_MAX, FLUSH_INTERVAL_BUFFER_SECONDES
    # Si l'import réussit, ces variables sont disponibles globalement dans ce module.
    # Et ACTIVE_DB_CONFIG devrait être un dictionnaire.
except ImportError:
    # Configurer un logging basique minimal si ce module est importé avant la configuration principale du logging
    if not logging.getLogger().hasHandlers(): # Vérifier si des handlers sont déjà configurés
        logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    logging.critical("CRITICAL (db_utils.py): config.py non trouvé ou variables DB/Buffer manquantes! Utilisation de valeurs par défaut internes.")
    ACTIVE_DB_CONFIG = {}  # Fallback: un dictionnaire vide EST un mapping.
    BUFFER_SIZE_MAX = 10
    FLUSH_INTERVAL_BUFFER_SECONDES = 300

# Logger spécifique pour ce module
db_logger = logging.getLogger("db_utils") # Renommé pour éviter conflit avec le logger 'root' des logs utilisateur

class DatabaseManager:
    def __init__(self):
        self.db_pool = None
        self.data_buffer = []
        self.last_flush_time = time.time()
        
        # --- AJOUT DE LOGS DE DIAGNOSTIC ---
        db_logger.info(f"Attempting to initialize DatabaseManager. Type of ACTIVE_DB_CONFIG: {type(ACTIVE_DB_CONFIG)}")
        db_logger.info(f"Value of ACTIVE_DB_CONFIG: {ACTIVE_DB_CONFIG}")
        # --- FIN AJOUT DE LOGS DE DIAGNOSTIC ---

        if not isinstance(ACTIVE_DB_CONFIG, dict): # Vérification explicite
            db_logger.error(f"CRITICAL ERROR: ACTIVE_DB_CONFIG is not a dictionary (it's a {type(ACTIVE_DB_CONFIG)}). DatabaseManager cannot proceed.")
            return
        
        if not ACTIVE_DB_CONFIG: 
            db_logger.error("Configuration de la base de données (ACTIVE_DB_CONFIG) est vide (mais est un dict). DatabaseManager ne pourra pas se connecter sans paramètres.")
            # On pourrait retourner ici, mais on laisse psycopg2 lever l'erreur si les paramètres sont insuffisants.
            # return 

        try:
            self.db_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1, 
                maxconn=5, 
                **ACTIVE_DB_CONFIG # C'est ici que l'erreur se produit si ACTIVE_DB_CONFIG n'est pas un mapping
            )
            db_logger.info(f"Pool de connexions à la base de données initialisé pour '{ACTIVE_DB_CONFIG.get('database')}' sur '{ACTIVE_DB_CONFIG.get('host')}'.")
            self._test_connection() 
        except TypeError as te: 
            db_logger.error(f"Erreur de type lors de l'initialisation du pool de connexions (vérifiez les arguments passés à SimpleConnectionPool): {te}", exc_info=True)
            self.db_pool = None
        except psycopg2.Error as e: 
            db_logger.error(f"Erreur psycopg2 lors de l'initialisation du pool de connexions: {e}", exc_info=True) # Ajout exc_info
            self.db_pool = None 
        except Exception as e: 
            db_logger.error(f"Erreur inattendue lors de l'initialisation de DatabaseManager: {e}", exc_info=True)
            self.db_pool = None

    def _test_connection(self):
        if not self.db_pool:
            db_logger.warning("Test de connexion annulé: le pool de connexions n'est pas initialisé.")
            return
        conn = None
        try:
            conn = self.db_pool.getconn()
            if conn:
                db_logger.info("Connexion à la base de données réussie (test initial du pool).")
            else:
                db_logger.error("Échec de l'obtention d'une connexion depuis le pool (test initial).")
        except psycopg2.Error as e:
            db_logger.error(f"Échec du test de connexion à la base de données via le pool: {e}")
        finally:
            if conn and self.db_pool: 
                self.db_pool.putconn(conn)

    def add_sensor_data_to_buffer(self, timestamp: datetime, temperature: float | None, humidity: float | None, co2: float | None,
                                  humidifier_active: bool, ventilation_active: bool, leds_active: bool,
                                  humidifier_on_duration: float | None, humidifier_off_duration: float | None,
                                  ventilation_on_duration: float | None, ventilation_off_duration: float | None):
        record = (
            timestamp,
            round(temperature, 1) if temperature is not None else None,
            round(humidity, 1) if humidity is not None else None,
            round(co2, 0) if co2 is not None else None, 
            humidifier_active,
            ventilation_active,
            leds_active,
            round(humidifier_on_duration, 1) if humidifier_on_duration is not None else None,
            round(humidifier_off_duration, 1) if humidifier_off_duration is not None else None,
            round(ventilation_on_duration, 1) if ventilation_on_duration is not None else None,
            round(ventilation_off_duration, 1) if ventilation_off_duration is not None else None
        )
        self.data_buffer.append(record)
        db_logger.debug(f"Donnée ajoutée au buffer DB. Taille actuelle: {len(self.data_buffer)}")

        current_time = time.time()
        
        buffer_max_size = BUFFER_SIZE_MAX 
        flush_interval_seconds = FLUSH_INTERVAL_BUFFER_SECONDES

        if len(self.data_buffer) >= buffer_max_size or \
           (current_time - self.last_flush_time) >= flush_interval_seconds:
            self.flush_buffer()

    def flush_buffer(self):
        if not self.data_buffer:
            return

        if not self.db_pool:
            db_logger.error("Pool de connexions DB non disponible. Impossible de vider le buffer.")
            return

        conn = None
        max_retries = 2
        attempt = 0
        
        buffer_to_flush = list(self.data_buffer) 
        
        db_logger.info(f"Tentative d'insertion de {len(buffer_to_flush)} enregistrements depuis le buffer DB.")

        while attempt <= max_retries:
            try:
                conn = self.db_pool.getconn()
                if not conn:
                    db_logger.error("Impossible d'obtenir une connexion depuis le pool pour flush_buffer.")
                    return

                with conn.cursor() as cur:
                    sql_insert_query = """
                        INSERT INTO sensor_data (
                            timestamp, temperature, humidity, co2,
                            humidifier_active, ventilation_active, leds_active,
                            humidifier_on_duration_seconds, humidifier_off_duration_seconds,
                            ventilation_on_duration_seconds, ventilation_off_duration_seconds
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cur.executemany(sql_insert_query, buffer_to_flush)
                conn.commit()
                db_logger.info(f"{len(buffer_to_flush)} enregistrements insérés avec succès dans sensor_data.")
                self.data_buffer.clear() 
                self.last_flush_time = time.time()
                return 

            except psycopg2.Error as e:
                db_logger.error(f"Erreur DB lors de l'insertion (tentative {attempt + 1}/{max_retries + 1}): {e}")
                if conn: 
                    try: conn.rollback() 
                    except psycopg2.Error as rb_err: db_logger.error(f"Erreur lors du rollback: {rb_err}")
                
                attempt += 1
                if attempt <= max_retries:
                    sleep_time = 2**attempt 
                    db_logger.info(f"Nouvel essai d'insertion DB dans {sleep_time} secondes...") 
                    time.sleep(sleep_time) 
                else:
                    db_logger.critical(f"Échec définitif de l'insertion de {len(buffer_to_flush)} enregistrements après {max_retries + 1} tentatives.")
                    return 
            except Exception as e: 
                db_logger.critical(f"Erreur inattendue lors du vidage du buffer DB: {e}", exc_info=True)
                if conn:
                    try: conn.rollback()
                    except: pass 
                return 
            finally:
                if conn and self.db_pool: 
                    self.db_pool.putconn(conn) 

    def close_pool(self):
        if self.db_pool:
            db_logger.info("Vidage final du buffer DB avant la fermeture du pool de connexions...")
            self.flush_buffer() 
            
            self.db_pool.closeall()
            db_logger.info("Pool de connexions à la base de données fermé.")
            self.db_pool = None 
        else:
            db_logger.info("Tentative de fermeture du pool DB, mais il n'était pas initialisé ou déjà fermé.")








