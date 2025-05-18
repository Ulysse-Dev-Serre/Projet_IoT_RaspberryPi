# src/core/serre_logic.py
import time
from datetime import datetime
import logging
import threading
import importlib

try:
    import config
except ImportError:
    logging.error("Fichier config.py non trouvé. Veuillez vous assurer qu'il existe et est accessible.")
    class MockConfig:
        HARDWARE_ENV = 'mock'
        INTERVALLE_LECTURE_CAPTEURS_SECONDES = 60 
        INTERVALLE_LECTURE_RAPIDE_CAPTEURS_SECONDES = 15
        HEURE_DEBUT_LEDS = 8
        HEURE_FIN_LEDS = 20
        SEUIL_HUMIDITE_ON = 75.0
        SEUIL_HUMIDITE_OFF = 84.9
        SEUIL_CO2_MAX = 1200.0
        LOG_LEVEL = 'INFO'
        LOG_FILE_PATH = 'serre_controller_default.log'
        ACTIVE_DB_CONFIG = {}
        BUFFER_SIZE_MAX = 10
        FLUSH_INTERVAL_BUFFER_SECONDES = 300

    config = MockConfig()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(threadName)s - %(message)s')


from .actuators.led_controller import LedController
from .actuators.humidifier_controller import HumidifierController
from .actuators.ventilation_controller import VentilationController

try:
    from ..utils.db_utils import DatabaseManager
except ImportError:
    logging.warning("DatabaseManager non trouvé dans src.utils.db_utils. Les données ne seront pas sauvegardées.")
    class MockDatabaseManager:
        def __init__(self, *args, **kwargs): pass
        def add_sensor_data_to_buffer(self, *args, **kwargs): logging.debug("MockDatabaseManager: add_sensor_data_to_buffer appelé")
        def flush_buffer(self): logging.debug("MockDatabaseManager: flush_buffer appelé")
        def close_pool(self): logging.debug("MockDatabaseManager: close_pool appelé")
    DatabaseManager = MockDatabaseManager
except Exception as e:
    logging.error(f"Erreur lors de l'import de DatabaseManager: {e}")
    class MockDatabaseManager: 
        def __init__(self, *args, **kwargs): pass
        def add_sensor_data_to_buffer(self, *args, **kwargs): logging.debug("MockDatabaseManager: add_sensor_data_to_buffer appelé")
        def flush_buffer(self): logging.debug("MockDatabaseManager: flush_buffer appelé")
        def close_pool(self): logging.debug("MockDatabaseManager: close_pool appelé")
    DatabaseManager = MockDatabaseManager


controller_logger = logging.getLogger(__name__)


class SerreController:
    def __init__(self):
        controller_logger.info("Initialisation de SerreController...")
        self.hardware = self._initialize_hardware()

        try:
            if hasattr(config, 'ACTIVE_DB_CONFIG') and config.ACTIVE_DB_CONFIG:
                 self.db_manager = DatabaseManager()
            else:
                controller_logger.warning("config.ACTIVE_DB_CONFIG non trouvé ou vide. Utilisation de MockDatabaseManager.")
                self.db_manager = MockDatabaseManager()
        except Exception as e:
            controller_logger.error(f"Erreur lors de l'initialisation de DatabaseManager: {e}. Utilisation de MockDatabaseManager.")
            self.db_manager = MockDatabaseManager()

        self._latest_sensor_data_store = {
            "timestamp": 0,
            "temperature": None,
            "humidite": None,
            "co2": None,
            "is_valid": False
        }
        self._sensor_data_lock = threading.Lock()
        self.last_sensor_read_error_logged = False 

        self.led_ctrl = LedController(self.hardware, config)
        self.humidifier_ctrl = HumidifierController(self.hardware, config)
        self.ventilation_ctrl = VentilationController(self.hardware, config)

        self._running = threading.Event() 
        self._running.set() 

        self._first_valid_sensor_data_event = threading.Event()

        self._sensor_acquisition_thread = threading.Thread(
            target=self._sensor_acquisition_loop,
            name="SensorAcquisitionThread",
            daemon=True
        )
        self._controller_logic_thread = threading.Thread(
            target=self._controller_logic_loop,
            name="SerreControllerLogicThread",
            daemon=True
        )

        controller_logger.info("Démarrage du Thread d'acquisition des capteurs...")
        self._sensor_acquisition_thread.start()
        controller_logger.info("Démarrage du Thread de logique du contrôleur...")
        self._controller_logic_thread.start()


    def _initialize_hardware(self):
        hardware_interface_module_path_root = 'src.hardware_interface'
        if config.HARDWARE_ENV == 'raspberry_pi':
            try:
                module_path = f'{hardware_interface_module_path_root}.raspberry_pi'
                hardware_module = importlib.import_module(module_path)
                HardwareInterface = hardware_module.RaspberryPiHardware
                controller_logger.info("Utilisation de RaspberryPiHardware.")
            except ImportError as e:
                controller_logger.error(f"Erreur importation RaspberryPiHardware: {e}. Fallback sur MockHardware.")
                module_path = f'{hardware_interface_module_path_root}.mock_hardware'
                hardware_module = importlib.import_module(module_path)
                HardwareInterface = hardware_module.MockHardware
        elif config.HARDWARE_ENV == 'mock':
            module_path = f'{hardware_interface_module_path_root}.mock_hardware'
            hardware_module = importlib.import_module(module_path)
            HardwareInterface = hardware_module.MockHardware
            controller_logger.info("Utilisation de MockHardware.")
        else:
            controller_logger.error(f"Configuration HARDWARE_ENV invalide: {config.HARDWARE_ENV}. Utilisation de MockHardware par défaut.")
            module_path = f'{hardware_interface_module_path_root}.mock_hardware'
            hardware_module = importlib.import_module(module_path)
            HardwareInterface = hardware_module.MockHardware
        
        return HardwareInterface()

    def _sensor_acquisition_loop(self):
        controller_logger.info(f"SensorAcquisitionThread: Boucle d'acquisition des capteurs active (intervalle: {config.INTERVALLE_LECTURE_RAPIDE_CAPTEURS_SECONDES}s).")
        while self._running.is_set():
            loop_start_time = time.time()
            try:
                temp, hum, co2_val = self.hardware.lire_capteur()
                
                with self._sensor_data_lock:
                    self._latest_sensor_data_store["timestamp"] = time.time() # Mettre à jour le timestamp même en cas d'erreur partielle
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
                        self._latest_sensor_data_store["is_valid"] = False
                        # Conserver les anciennes valeurs valides si la lecture actuelle est partielle/invalide
                        # pour éviter que get_status ne montre N/A trop souvent si une seule valeur est None.
                        # La logique des actionneurs utilise déjà la vérification "all(v is not None ...)"
                        if not self.last_sensor_read_error_logged:
                            controller_logger.warning(f"SensorAcquisitionThread: Données de capteur invalides/partielles (au moins une valeur None): T={temp}, H={hum}, CO2={co2_val}")
                            self.last_sensor_read_error_logged = True
            
            except RuntimeError as e: 
                with self._sensor_data_lock:
                    self._latest_sensor_data_store["is_valid"] = False
                if not self.last_sensor_read_error_logged:
                    controller_logger.error(f"SensorAcquisitionThread: Erreur RuntimeError lors de l'acquisition: {e}")
                    self.last_sensor_read_error_logged = True
            except Exception as e:
                with self._sensor_data_lock:
                    self._latest_sensor_data_store["is_valid"] = False
                if not self.last_sensor_read_error_logged:
                    controller_logger.error(f"SensorAcquisitionThread: Erreur inattendue lors de l'acquisition: {e}", exc_info=False)
                    self.last_sensor_read_error_logged = True
            
            # Calcul du temps de pause pour respecter l'intervalle
            elapsed_time = time.time() - loop_start_time
            wait_time = config.INTERVALLE_LECTURE_RAPIDE_CAPTEURS_SECONDES - elapsed_time
            if wait_time > 0:
                # Utiliser time.sleep() mais vérifier _running pour une sortie rapide si nécessaire
                # Dormir par petits morceaux pour vérifier _running plus souvent
                chunk = 0.5 # vérifier toutes les 0.5 secondes
                slept_duration = 0
                while slept_duration < wait_time and self._running.is_set():
                    time_to_sleep_this_chunk = min(chunk, wait_time - slept_duration)
                    time.sleep(time_to_sleep_this_chunk)
                    slept_duration += time_to_sleep_this_chunk
            # Si wait_time <= 0, la boucle a pris plus de temps, on continue immédiatement si _running est toujours vrai.

        controller_logger.info("SensorAcquisitionThread: Boucle d'acquisition des capteurs terminée.")

    def _get_current_sensor_values_for_actuators(self) -> dict:
        with self._sensor_data_lock:
            # Toujours retourner une structure, même si les données sont invalides,
            # pour que les appelants n'aient pas à gérer un retour None pour le dictionnaire entier.
            return {
                'temperature': self._latest_sensor_data_store["temperature"] if self._latest_sensor_data_store["is_valid"] else None,
                'humidite': self._latest_sensor_data_store["humidite"] if self._latest_sensor_data_store["is_valid"] else None,
                'co2': self._latest_sensor_data_store["co2"] if self._latest_sensor_data_store["is_valid"] else None
            }


    def _controller_logic_loop(self):
        controller_logger.info(f"SerreControllerLogicThread: Boucle de logique du contrôleur active (intervalle principal: {config.INTERVALLE_LECTURE_CAPTEURS_SECONDES}s).")
        
        controller_logger.info("SerreControllerLogicThread: En attente de la première lecture valide des capteurs...")
        # Attendre un peu plus longtemps pour la première lecture valide
        initial_wait_timeout = config.INTERVALLE_LECTURE_RAPIDE_CAPTEURS_SECONDES * 6 
        if not self._first_valid_sensor_data_event.wait(timeout=initial_wait_timeout): 
            controller_logger.warning(f"SerreControllerLogicThread: Délai d'attente ({initial_wait_timeout}s) pour la première lecture valide dépassé. Démarrage avec des données potentiellement invalides.")
        else:
            controller_logger.info("SerreControllerLogicThread: Première lecture valide des capteurs reçue. Démarrage de la logique principale.")

        sensor_error_streak_for_logic = 0 

        while self._running.is_set():
            loop_start_time = time.time()
            controller_logger.debug("SerreControllerLogicThread: Début du cycle de mise à jour logique et DB.")
            
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
                     controller_logger.critical("SerreControllerLogicThread: Échec critique de récupération des données capteurs valides à plusieurs reprises pour la logique!")
                     sensor_error_streak_for_logic = 0 

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
            controller_logger.debug("SerreControllerLogicThread: Fin du cycle de mise à jour logique et DB.")
            
            elapsed_time = time.time() - loop_start_time
            wait_time = config.INTERVALLE_LECTURE_CAPTEURS_SECONDES - elapsed_time
            
            if wait_time > 0:
                controller_logger.debug(f"SerreControllerLogicThread: Intervalle de base {config.INTERVALLE_LECTURE_CAPTEURS_SECONDES}s. Temps écoulé: {elapsed_time:.2f}s. Attente pour {wait_time:.2f}s.")
                # Utiliser time.sleep() mais vérifier _running pour une sortie rapide si nécessaire
                chunk = 0.5 # vérifier toutes les 0.5 secondes
                slept_duration = 0
                while slept_duration < wait_time and self._running.is_set():
                    time_to_sleep_this_chunk = min(chunk, wait_time - slept_duration)
                    time.sleep(time_to_sleep_this_chunk) # Remplacer self._running.wait par time.sleep
                    slept_duration += time_to_sleep_this_chunk
            elif wait_time <=0 : # Correction de la condition
                controller_logger.warning(f"SerreControllerLogicThread: La boucle de logique a pris plus de temps ({elapsed_time:.2f}s) que l'intervalle configuré ({config.INTERVALLE_LECTURE_CAPTEURS_SECONDES}s). Exécution immédiate.")
        
        controller_logger.info("SerreControllerLogicThread: Boucle de logique du contrôleur terminée.")

    def run(self):
        controller_logger.info("SerreController.run() appelé. Les threads internes gèrent les opérations.")
        try:
            while self._running.is_set():
                time.sleep(1) # Remplacer self._running.wait par time.sleep
        except KeyboardInterrupt:
            controller_logger.info("KeyboardInterrupt reçu dans SerreController.run(). Demande d'arrêt via shutdown().")
            self.shutdown() 

    def get_status(self) -> dict:
        status_leds = self.led_ctrl.get_status()
        status_humid = self.humidifier_ctrl.get_status()
        status_vent = self.ventilation_ctrl.get_status()
        
        temp_display, hum_display, co2_display, sensor_ok = "N/A", "N/A", "N/A", False

        with self._sensor_data_lock:
            # Utiliser directement les valeurs stockées, car is_valid est mis à jour en conséquence
            temp = self._latest_sensor_data_store["temperature"]
            hum = self._latest_sensor_data_store["humidite"]
            co2 = self._latest_sensor_data_store["co2"]
            sensor_ok = self._latest_sensor_data_store["is_valid"] # Utiliser directement is_valid

            if sensor_ok:
                temp_display = f"{temp:.1f}"
                hum_display = f"{hum:.1f}"
                co2_display = f"{co2:.0f}"
            # Si non 'ok', les valeurs par défaut "N/A" sont conservées

        return {
            "timestamp": datetime.now().replace(microsecond=0).strftime('%Y-%m-%d %H:%M:%S'),
            "temperature": temp_display,
            "humidite": hum_display,
            "co2": co2_display,
            "sensor_read_ok": sensor_ok,
            "leds": status_leds,
            "humidifier": status_humid,
            "ventilation": status_vent,
        }

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
        self.led_ctrl.set_manual_mode(True, False)
        self._force_actuator_update(self.led_ctrl)
        
        self.humidifier_ctrl.set_manual_mode(True, False)
        self._force_actuator_update(self.humidifier_ctrl)

        self.ventilation_ctrl.set_manual_mode(True, False)
        self._force_actuator_update(self.ventilation_ctrl)
        
        controller_logger.info("Tous les actionneurs ont été désactivés (arrêt d'urgence).")

    def shutdown(self):
        controller_logger.info("Arrêt de SerreController...")
        if not self._running.is_set(): 
            controller_logger.info("SerreController.shutdown() appelé mais déjà en cours d'arrêt ou arrêté.")
            return 
            
        self._running.clear() 

        threads_to_join = []
        if hasattr(self, '_sensor_acquisition_thread') and self._sensor_acquisition_thread and self._sensor_acquisition_thread.is_alive():
            threads_to_join.append(self._sensor_acquisition_thread)
        if hasattr(self, '_controller_logic_thread') and self._controller_logic_thread and self._controller_logic_thread.is_alive():
            threads_to_join.append(self._controller_logic_thread)

        for thread in threads_to_join:
            controller_logger.info(f"Attente de la fin du thread {thread.name} (max {config.INTERVALLE_LECTURE_RAPIDE_CAPTEURS_SECONDES + 10}s)...") # Augmenté légèrement le timeout
            thread.join(timeout=config.INTERVALLE_LECTURE_RAPIDE_CAPTEURS_SECONDES + 10) 
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






