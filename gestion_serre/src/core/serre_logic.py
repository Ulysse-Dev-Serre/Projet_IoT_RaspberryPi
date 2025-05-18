# src/core/serre_logic.py
import json
import os
import threading
import logging
import time 
from datetime import datetime
import importlib

# Importer le module config (qui contient DEFAULT_SETTINGS et USER_SETTINGS_FILE)
import config 

from .actuators.led_controller import LedController
from .actuators.humidifier_controller import HumidifierController
from .actuators.ventilation_controller import VentilationController

try:
    from ..utils.db_utils import DatabaseManager
except ImportError:
    logging.warning("DatabaseManager non trouvé dans src.utils.db_utils. Utilisation de MockDatabaseManager.")
    class MockDatabaseManager:
        def __init__(self, *args, **kwargs): pass
        def add_sensor_data_to_buffer(self, *args, **kwargs): logging.debug("MockDM: add_sensor_data_to_buffer")
        def flush_buffer(self): logging.debug("MockDM: flush_buffer")
        def close_pool(self): logging.debug("MockDM: close_pool")
    DatabaseManager = MockDatabaseManager
except Exception as e: # Attraper d'autres erreurs d'import possibles pour DatabaseManager
    logging.error(f"Erreur inattendue lors de l'import de DatabaseManager: {e}. Utilisation de MockDatabaseManager.")
    class MockDatabaseManager: # Fallback
        def __init__(self, *args, **kwargs): pass
        def add_sensor_data_to_buffer(self, *args, **kwargs): logging.debug("MockDM: add_sensor_data_to_buffer")
        def flush_buffer(self): logging.debug("MockDM: flush_buffer")
        def close_pool(self): logging.debug("MockDM: close_pool")
    DatabaseManager = MockDatabaseManager


controller_logger = logging.getLogger(__name__)

class SerreController:
    def __init__(self):
        controller_logger.info("Initialisation de SerreController...")
        self.hardware = self._initialize_hardware() 
        self.db_manager = self._initialize_db_manager()

        # --- DÉBUT: Gestion centralisée des configurations ---
        self.settings = {}  # Dictionnaire pour tenir les configurations actuelles
        self.settings_lock = threading.Lock() # Pour un accès thread-safe
        self._load_settings() # Charger les configurations au démarrage
        # --- FIN: Gestion centralisée des configurations ---

        # Store pour les données capteurs (comme avant)
        self._latest_sensor_data_store = {
            "timestamp": 0, "temperature": None, "humidite": None,
            "co2": None, "is_valid": False
        }
        self._sensor_data_lock = threading.Lock()
        self.last_sensor_read_error_logged = False 
        
        # Événements pour la gestion des threads (comme avant)
        self._running = threading.Event(); self._running.set() 
        self._first_valid_sensor_data_event = threading.Event()

        # MODIFIÉ: Passer 'self' (l'instance de SerreController) aux contrôleurs d'actionneurs.
        # Ils pourront ainsi appeler self.get_setting('NOM_PARAMETRE').
        self.led_ctrl = LedController(self.hardware, self) 
        self.humidifier_ctrl = HumidifierController(self.hardware, self)
        self.ventilation_ctrl = VentilationController(self.hardware, self)

        # Démarrage des threads (comme avant)
        self._sensor_acquisition_thread = threading.Thread(
            target=self._sensor_acquisition_loop, name="SensorAcquisitionThread", daemon=True)
        self._controller_logic_thread = threading.Thread(
            target=self._controller_logic_loop, name="SerreControllerLogicThread", daemon=True)

        controller_logger.info("Démarrage du Thread d'acquisition des capteurs...")
        self._sensor_acquisition_thread.start()
        controller_logger.info("Démarrage du Thread de logique du contrôleur...")
        self._controller_logic_thread.start()

    def _initialize_db_manager(self):
        """Initialise et retourne le gestionnaire de base de données."""
        try:
            if hasattr(config, 'ACTIVE_DB_CONFIG') and config.ACTIVE_DB_CONFIG:
                 return DatabaseManager()
            else:
                controller_logger.warning("config.ACTIVE_DB_CONFIG non trouvé ou vide. Utilisation de MockDatabaseManager.")
                return MockDatabaseManager() 
        except Exception as e:
            controller_logger.error(f"Erreur lors de l'initialisation de DatabaseManager: {e}. Utilisation de MockDatabaseManager.")
            return MockDatabaseManager()

    def _initialize_hardware(self):
        """Charge dynamiquement l'interface matérielle basée sur config.HARDWARE_ENV."""
        hardware_interface_module_path_root = 'src.hardware_interface'
        # S'assurer que config.HARDWARE_ENV est bien défini
        hardware_env = getattr(config, 'HARDWARE_ENV', 'mock') # Fallback sur 'mock' si non défini

        if hardware_env == 'raspberry_pi':
            try:
                module_path = f'{hardware_interface_module_path_root}.raspberry_pi'
                hw_module = importlib.import_module(module_path)
                HardwareInterface = hw_module.RaspberryPiHardware
                controller_logger.info("Utilisation de RaspberryPiHardware.")
            except ImportError as e:
                controller_logger.error(f"Erreur importation RaspberryPiHardware: {e}. Fallback sur MockHardware.")
                module_path = f'{hardware_interface_module_path_root}.mock_hardware'
                hw_module = importlib.import_module(module_path)
                HardwareInterface = hw_module.MockHardware
        else: # mock ou autre
            module_path = f'{hardware_interface_module_path_root}.mock_hardware'
            hw_module = importlib.import_module(module_path)
            HardwareInterface = hw_module.MockHardware
            controller_logger.info(f"Utilisation de {hardware_env}Hardware (ou MockHardware par défaut).")
        return HardwareInterface()

    # --- NOUVELLES MÉTHODES ET LOGIQUE MODIFIÉE POUR LA GESTION DES CONFIGURATIONS ---

    def _ensure_data_directory_exists(self):
        """S'assure que le répertoire spécifié dans USER_SETTINGS_FILE existe."""
        settings_file_path = config.USER_SETTINGS_FILE
        data_dir = os.path.dirname(settings_file_path)
        if data_dir and not os.path.exists(data_dir): 
            try:
                os.makedirs(data_dir)
                controller_logger.info(f"Répertoire '{data_dir}' créé pour les configurations utilisateur.")
            except OSError as e:
                controller_logger.error(f"Impossible de créer le répertoire '{data_dir}': {e}")
                return False
        return True

    def _load_settings(self):
        """Charge les configurations depuis user_settings.json, fallback sur DEFAULT_SETTINGS."""
        if not self._ensure_data_directory_exists():
            controller_logger.warning("Impossible d'assurer l'existence du répertoire des settings. Utilisation des défauts uniquement en mémoire.")
            with self.settings_lock:
                self.settings = config.DEFAULT_SETTINGS.copy()
            controller_logger.info(f"Configurations actives (défauts uniquement car répertoire data inaccessible): {self.settings}")
            return

        current_loaded_settings = config.DEFAULT_SETTINGS.copy() 
        settings_file_path = config.USER_SETTINGS_FILE

        try:
            if os.path.exists(settings_file_path) and os.path.getsize(settings_file_path) > 0:
                with open(settings_file_path, 'r', encoding='utf-8') as f:
                    user_settings_from_file = json.load(f)
                    for key, value in user_settings_from_file.items():
                        if key in current_loaded_settings: 
                            default_type = type(current_loaded_settings[key])
                            try:
                                if default_type == bool and isinstance(value, str):
                                    current_loaded_settings[key] = value.lower() in ['true', '1', 'yes', 'on', 'vrai']
                                elif default_type == bool and isinstance(value, int): # Accepter 0/1 pour bool
                                    current_loaded_settings[key] = bool(value)
                                else:
                                    current_loaded_settings[key] = default_type(value)
                            except (ValueError, TypeError) as cast_error:
                                controller_logger.warning(f"Erreur de casting pour la clé '{key}' (valeur: '{value}', type attendu: {default_type}): {cast_error}. Utilisation de la valeur par défaut pour cette clé.")
                        else:
                            controller_logger.warning(f"Clé '{key}' dans '{settings_file_path}' non reconnue, ignorée.")
                    controller_logger.info(f"Configurations chargées et fusionnées depuis '{settings_file_path}'.")
            else:
                controller_logger.info(f"'{settings_file_path}' non trouvé ou vide. Utilisation des configurations par défaut et création/mise à jour du fichier.")
                with open(settings_file_path, 'w', encoding='utf-8') as f: 
                    json.dump(current_loaded_settings, f, indent=4, ensure_ascii=False)
        except (IOError, json.JSONDecodeError) as e:
            controller_logger.error(f"Erreur lors du chargement/création de '{settings_file_path}': {e}. Utilisation des configurations par défaut strictes.")
            current_loaded_settings = config.DEFAULT_SETTINGS.copy()

        with self.settings_lock:
            self.settings = current_loaded_settings
        controller_logger.info(f"Configurations actives finales: {self.settings}")


    def _save_settings(self):
        """Sauvegarde les configurations actuelles (self.settings) dans USER_SETTINGS_FILE."""
        if not self._ensure_data_directory_exists():
            controller_logger.error("Impossible de sauvegarder les settings, le répertoire n'a pas pu être assuré.")
            return False
            
        with self.settings_lock:
            settings_to_save = self.settings.copy()
        try:
            with open(config.USER_SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings_to_save, f, indent=4, ensure_ascii=False)
            controller_logger.info(f"Configurations sauvegardées dans '{config.USER_SETTINGS_FILE}'.")
            return True
        except IOError as e:
            controller_logger.error(f"Erreur lors de la sauvegarde des configurations dans '{config.USER_SETTINGS_FILE}': {e}")
            return False

    def get_setting(self, key: str, default_override=None):
        """Récupère une valeur de configuration de manière thread-safe."""
        with self.settings_lock:
            value_from_memory = self.settings.get(key) # Peut être None si la clé n'est pas là
        
        if value_from_memory is not None:
            return value_from_memory
        
        # Si non trouvé dans self.settings (mémoire), vérifier dans config.DEFAULT_SETTINGS
        if key in config.DEFAULT_SETTINGS:
            return config.DEFAULT_SETTINGS[key]
            
        # Sinon, utiliser le default_override fourni à cette méthode
        if default_override is not None:
            return default_override
        
        controller_logger.warning(f"Clé de setting '{key}' non trouvée dans les settings actifs ni dans les défauts, et aucun default_override fourni.")
        return None # Ou lever une exception selon la criticité

    def get_all_settings(self) -> dict:
        """Récupère une copie de toutes les configurations actuelles, fusionnées avec les défauts."""
        with self.settings_lock:
            # Commencer avec une copie des défauts pour s'assurer que toutes les clés attendues sont présentes
            complete_settings = config.DEFAULT_SETTINGS.copy()
            # Mettre à jour/écraser avec les settings actuellement en mémoire (ceux de user_settings.json ou modifiés)
            complete_settings.update(self.settings) 
            return complete_settings

    def update_settings(self, new_settings_to_update: dict) -> bool:
        """
        Met à jour une ou plusieurs configurations.
        Valide les clés et tente une conversion de type basée sur DEFAULT_SETTINGS.
        Sauvegarde toutes les configurations après mise à jour si des changements ont eu lieu.
        """
        if not isinstance(new_settings_to_update, dict):
            controller_logger.error("Mise à jour des settings échouée: les nouvelles données ne sont pas un dictionnaire.")
            return False

        controller_logger.info(f"Demande de mise à jour des configurations avec: {new_settings_to_update}")
        
        settings_actually_changed = False
        
        with self.settings_lock:
            # Faire une copie des settings actuels pour la comparaison et la modification
            # Cela garantit que nous travaillons sur une base qui inclut déjà les settings chargés/défauts.
            # self.settings est déjà le résultat de la fusion lors du _load_settings.
            temp_current_settings = self.settings.copy()

            for key, received_value in new_settings_to_update.items():
                if key in config.DEFAULT_SETTINGS: # Clé valide car présente dans les défauts de référence
                    default_value_for_type_check = config.DEFAULT_SETTINGS[key]
                    default_type = type(default_value_for_type_check)
                    
                    value_before_update = temp_current_settings.get(key) # Valeur actuelle avant modification

                    casted_value = None
                    try:
                        # Logique de conversion de type améliorée
                        if default_type == bool:
                            if isinstance(received_value, str):
                                casted_value = received_value.lower() in ['true', 'on', '1', 'yes', 'vrai']
                            elif isinstance(received_value, (int, float)): # Accepter 0/1 pour bool
                                casted_value = bool(received_value)
                            else: # Déjà un booléen
                                casted_value = bool(received_value)
                        elif default_type == int:
                            casted_value = int(float(received_value)) # Permet "70.0" -> 70
                        elif default_type == float:
                            casted_value = float(received_value)
                        else: # Pour str ou autres types (suppose que c'est déjà le bon type ou str)
                            casted_value = default_type(received_value)

                        # Vérifier si la valeur a réellement changé
                        if value_before_update != casted_value:
                            temp_current_settings[key] = casted_value # Mettre à jour dans la copie temporaire
                            settings_actually_changed = True
                            controller_logger.info(f"Setting '{key}' sera mis à jour de '{value_before_update}' à '{casted_value}'.")
                        else:
                            controller_logger.debug(f"Setting '{key}' inchangé (valeur: '{casted_value}').")
                            
                    except (ValueError, TypeError) as e:
                        controller_logger.warning(f"Valeur '{received_value}' pour clé '{key}' invalide ou type incorrect (attendu {default_type}): {e}. Setting non modifié.")
                else:
                    controller_logger.warning(f"Clé de configuration inconnue '{key}' ignorée lors de la mise à jour.")
            
            if settings_actually_changed:
                self.settings = temp_current_settings # Appliquer les changements à self.settings
                controller_logger.info(f"Configurations en mémoire après mise à jour: {self.settings}")
        
        if settings_actually_changed:
            return self._save_settings() # Sauvegarder si des changements ont été appliqués
        elif not new_settings_to_update:
             controller_logger.info("Aucun setting fourni pour la mise à jour.")
             return False 
        else:
             controller_logger.info("Aucun changement effectif des settings après validation/comparaison.")
             return True # Considéré comme un succès car aucune erreur, même si rien n'a changé.

    # --- FIN DES NOUVELLES MÉTHODES POUR LA GESTION DES CONFIGURATIONS ---

    # Les boucles _sensor_acquisition_loop et _controller_logic_loop
    # ainsi que les autres méthodes (run, get_status, _force_actuator_update,
    # set_manual_mode, shutdown) sont reprises de la version précédente
    # qui fonctionnait correctement au niveau de la temporisation et de la logique des threads.
    # Les contrôleurs d'actionneurs devront être adaptés pour utiliser self.get_setting().

    def _sensor_acquisition_loop(self):
        intervalle_rapide = config.INTERVALLE_LECTURE_RAPIDE_CAPTEURS_SECONDES # Non dynamique pour l'instant
        controller_logger.info(f"SensorAcquisitionThread: Boucle d'acquisition active (intervalle: {intervalle_rapide}s).")
        while self._running.is_set():
            loop_start_time = time.time()
            try:
                temp, hum, co2_val = self.hardware.lire_capteur()
                with self._sensor_data_lock:
                    self._latest_sensor_data_store["timestamp"] = time.time() 
                    if temp is not None and hum is not None and co2_val is not None:
                        self._latest_sensor_data_store["temperature"] = temp
                        self._latest_sensor_data_store["humidite"] = hum
                        self._latest_sensor_data_store["co2"] = co2_val
                        self._latest_sensor_data_store["is_valid"] = True
                        if not self._first_valid_sensor_data_event.is_set():
                            self._first_valid_sensor_data_event.set() 
                            controller_logger.info("SensorAcquisitionThread: Première lecture valide des capteurs obtenue.")
                        if self.last_sensor_read_error_logged:
                            controller_logger.info("SensorAcquisitionThread: Lecture des capteurs réussie après une erreur précédente.")
                            self.last_sensor_read_error_logged = False
                        controller_logger.debug(f"SensorAcquisitionThread: Acquisition T={temp:.1f}, H={hum:.1f}, CO2={co2_val:.0f}")
                    else:
                        # Si une lecture est partielle, marquer comme non valide pour cette itération
                        # mais conserver les anciennes valeurs valides dans le store pour get_status
                        self._latest_sensor_data_store["is_valid"] = False 
                        if not self.last_sensor_read_error_logged:
                            controller_logger.warning(f"SensorAcquisitionThread: Données de capteur invalides/partielles: T={temp}, H={hum}, CO2={co2_val}")
                            self.last_sensor_read_error_logged = True
            except Exception as e: 
                with self._sensor_data_lock: self._latest_sensor_data_store["is_valid"] = False
                controller_logger.error(f"SensorAcquisitionThread: Erreur acquisition: {e}", exc_info=True)
                self.last_sensor_read_error_logged = True

            elapsed_time = time.time() - loop_start_time
            wait_time = intervalle_rapide - elapsed_time
            if wait_time > 0:
                chunk = 0.5; slept_duration = 0
                while slept_duration < wait_time and self._running.is_set():
                    time_to_sleep_this_chunk = min(chunk, wait_time - slept_duration)
                    time.sleep(time_to_sleep_this_chunk)
                    slept_duration += time_to_sleep_this_chunk
        controller_logger.info("SensorAcquisitionThread: Boucle terminée.")

    def _get_current_sensor_values_for_actuators(self) -> dict:
        with self._sensor_data_lock:
            if self._latest_sensor_data_store["is_valid"]:
                return {
                    'temperature': self._latest_sensor_data_store["temperature"],
                    'humidite': self._latest_sensor_data_store["humidite"],
                    'co2': self._latest_sensor_data_store["co2"]
                }
            else: # Retourner None pour les valeurs si la dernière lecture n'était pas valide
                return {'temperature': None, 'humidite': None, 'co2': None}


    def _controller_logic_loop(self):
        intervalle_logique = config.INTERVALLE_LECTURE_CAPTEURS_SECONDES # Non dynamique pour l'instant
        controller_logger.info(f"SerreControllerLogicThread: Boucle de logique active (intervalle principal: {intervalle_logique}s).")
        
        initial_wait_timeout = config.INTERVALLE_LECTURE_RAPIDE_CAPTEURS_SECONDES * 6 
        controller_logger.info(f"SerreControllerLogicThread: En attente de la première lecture valide des capteurs (max {initial_wait_timeout}s)...")
        if not self._first_valid_sensor_data_event.wait(timeout=initial_wait_timeout): 
            controller_logger.warning(f"SerreControllerLogicThread: Délai d'attente pour la première lecture valide dépassé.")
        else:
            controller_logger.info("SerreControllerLogicThread: Première lecture valide des capteurs reçue. Démarrage de la logique principale.")

        sensor_error_streak_for_logic = 0 
        while self._running.is_set():
            loop_start_time = time.time()
            current_sensor_values_for_logic = self._get_current_sensor_values_for_actuators()

            if all(v is not None for v in current_sensor_values_for_logic.values()):
                sensor_error_streak_for_logic = 0
                controller_logger.info(
                    f"SerreControllerLogicThread: Données capteurs pour logique: T={current_sensor_values_for_logic['temperature']:.1f}°C, "
                    f"H={current_sensor_values_for_logic['humidite']:.1f}%, "
                    f"CO2={current_sensor_values_for_logic['co2']:.0f}ppm"
                )
            else:
                sensor_error_streak_for_logic += 1
                controller_logger.warning(f"SerreControllerLogicThread: Échec de récupération de données capteurs valides pour la logique (série: {sensor_error_streak_for_logic}).")
                if sensor_error_streak_for_logic >= 5: 
                     controller_logger.critical("SerreControllerLogicThread: Échec critique de récupération des données valides!")
                     sensor_error_streak_for_logic = 0 

            # Les contrôleurs d'actionneurs utiliseront self.get_setting() en interne via l'instance 'self' passée
            self.led_ctrl.update_state(current_sensor_values_for_logic)
            self.humidifier_ctrl.update_state(current_sensor_values_for_logic)
            self.ventilation_ctrl.update_state(current_sensor_values_for_logic)
            
            status_leds = self.led_ctrl.get_status()
            status_humid = self.humidifier_ctrl.get_status()
            status_vent = self.ventilation_ctrl.get_status()
            self.db_manager.add_sensor_data_to_buffer(
                timestamp=datetime.now().replace(microsecond=0),
                temperature=current_sensor_values_for_logic['temperature'], 
                humidity=current_sensor_values_for_logic['humidite'],      
                co2=current_sensor_values_for_logic['co2'],                
                humidifier_active=status_humid["is_active"],
                ventilation_active=status_vent["is_active"],
                leds_active=status_leds["is_active"],
                humidifier_on_duration=status_humid["on_duration_seconds"] if status_humid["is_active"] else None,
                humidifier_off_duration=status_humid["off_duration_seconds"] if not status_humid["is_active"] else None,
                ventilation_on_duration=status_vent["on_duration_seconds"] if status_vent["is_active"] else None,
                ventilation_off_duration=status_vent["off_duration_seconds"] if not status_vent["is_active"] else None
            )

            elapsed_time = time.time() - loop_start_time
            wait_time = intervalle_logique - elapsed_time
            if wait_time > 0:
                controller_logger.debug(f"SerreControllerLogicThread: Intervalle: {intervalle_logique}s. Boucle: {elapsed_time:.2f}s. Attente: {wait_time:.2f}s.")
                chunk = 0.5; slept_duration = 0
                while slept_duration < wait_time and self._running.is_set():
                    time_to_sleep_this_chunk = min(chunk, wait_time - slept_duration)
                    time.sleep(time_to_sleep_this_chunk)
                    slept_duration += time_to_sleep_this_chunk
            elif wait_time <= 0: # Correction: était elif wait_time <=0 :
                controller_logger.warning(f"SerreControllerLogicThread: Boucle trop longue ({elapsed_time:.2f}s vs intervalle {intervalle_logique}s).")
        controller_logger.info("SerreControllerLogicThread: Boucle terminée.")

    def get_status(self) -> dict:
        status_leds = self.led_ctrl.get_status()
        status_humid = self.humidifier_ctrl.get_status()
        status_vent = self.ventilation_ctrl.get_status()
        
        temp_display, hum_display, co2_display, sensor_ok = "N/A", "N/A", "N/A", False

        with self._sensor_data_lock:
            temp = self._latest_sensor_data_store["temperature"]
            hum = self._latest_sensor_data_store["humidite"]
            co2_val = self._latest_sensor_data_store["co2"] 
            sensor_ok = self._latest_sensor_data_store["is_valid"]

            if sensor_ok:
                temp_display = f"{temp:.1f}" if temp is not None else "N/A"
                hum_display = f"{hum:.1f}" if hum is not None else "N/A"
                co2_display = f"{co2_val:.0f}" if co2_val is not None else "N/A"
        
        # Les settings ne sont plus retournés ici directement,
        # ils seront accessibles via une route API dédiée /api/settings
        return {
            "timestamp": datetime.now().replace(microsecond=0).strftime('%Y-%m-%d %H:%M:%S'),
            "temperature": temp_display, "humidite": hum_display, "co2": co2_display,
            "sensor_read_ok": sensor_ok,
            "leds": status_leds, "humidifier": status_humid, "ventilation": status_vent
        }
    
    def run(self):
        controller_logger.info("SerreController.run() appelé. Les threads internes gèrent les opérations.")
        try:
            while self._running.is_set():
                time.sleep(1) 
        except KeyboardInterrupt:
            controller_logger.info("KeyboardInterrupt reçu dans SerreController.run(). Demande d'arrêt via shutdown().")
            self.shutdown() 

    def _force_actuator_update(self, actuator_controller):
        current_sensor_values = self._get_current_sensor_values_for_actuators()
        if actuator_controller.update_state(current_sensor_values): 
            actuator_controller._control_hardware() 
            controller_logger.info(f"État de {actuator_controller.device_name} mis à jour et matériel commandé (contrôle manuel).")

    def set_leds_manual_mode(self, active: bool, state_if_manual: bool = False):
        self.led_ctrl.set_manual_mode(active, state_if_manual)
        controller_logger.info(f"LEDs mode manuel {'activé' if active else 'désactivé'}" + (f" avec état {state_if_manual}" if active else ""))
        self._force_actuator_update(self.led_ctrl)

    def set_humidifier_manual_mode(self, active: bool, state_if_manual: bool = False):
        self.humidifier_ctrl.set_manual_mode(active, state_if_manual)
        controller_logger.info(f"Humidificateur mode manuel {'activé' if active else 'désactivé'}" + (f" avec état {state_if_manual}" if active else ""))
        self._force_actuator_update(self.humidifier_ctrl)

    def set_ventilation_manual_mode(self, active: bool, state_if_manual: bool = False):
        self.ventilation_ctrl.set_manual_mode(active, state_if_manual)
        controller_logger.info(f"Ventilation mode manuel {'activé' if active else 'désactivé'}" + (f" avec état {state_if_manual}" if active else ""))
        self._force_actuator_update(self.ventilation_ctrl)

    def set_all_auto_mode(self):
        self.led_ctrl.set_manual_mode(False)
        self._force_actuator_update(self.led_ctrl)
        self.humidifier_ctrl.set_manual_mode(False)
        self._force_actuator_update(self.humidifier_ctrl)
        self.ventilation_ctrl.set_manual_mode(False)
        self._force_actuator_update(self.ventilation_ctrl)
        controller_logger.info("Tous les actionneurs sont repassés en mode automatique et leur état a été mis à jour.")

    def emergency_stop_all_actuators(self):
        controller_logger.warning("ARRÊT D'URGENCE ACTIVÉ")
        self.led_ctrl.set_manual_mode(True, False); self._force_actuator_update(self.led_ctrl)
        self.humidifier_ctrl.set_manual_mode(True, False); self._force_actuator_update(self.humidifier_ctrl)
        self.ventilation_ctrl.set_manual_mode(True, False); self._force_actuator_update(self.ventilation_ctrl)
        controller_logger.info("Tous les actionneurs ont été désactivés (arrêt d'urgence).")

    def shutdown(self):
        controller_logger.info("Arrêt de SerreController...")
        if not self._running.is_set(): 
            controller_logger.info("SerreController.shutdown() appelé mais déjà en cours d'arrêt ou arrêté.")
            return 
        self._running.clear() 
        threads_to_join = []
        if hasattr(self, '_sensor_acquisition_thread') and self._sensor_acquisition_thread.is_alive():
            threads_to_join.append(self._sensor_acquisition_thread)
        if hasattr(self, '_controller_logic_thread') and self._controller_logic_thread.is_alive():
            threads_to_join.append(self._controller_logic_thread)

        for thread in threads_to_join:
            join_timeout = max(config.INTERVALLE_LECTURE_RAPIDE_CAPTEURS_SECONDES, config.INTERVALLE_LECTURE_CAPTEURS_SECONDES) + 10 # Donner une marge
            controller_logger.info(f"Attente de la fin du thread {thread.name} (max {join_timeout}s)...") 
            thread.join(timeout=join_timeout) 
            if thread.is_alive():
                controller_logger.warning(f"Le thread {thread.name} n'a pas pu être arrêté proprement dans le délai imparti.")
        
        controller_logger.info("Vidage du buffer de la base de données avant l'arrêt...")
        if hasattr(self, 'db_manager') and self.db_manager: 
            self.db_manager.flush_buffer()
            self.db_manager.close_pool()
        
        if self.hardware:
            controller_logger.info("Nettoyage du matériel...")
            self.hardware.cleanup()
        
        controller_logger.info("SerreController arrêté.")








