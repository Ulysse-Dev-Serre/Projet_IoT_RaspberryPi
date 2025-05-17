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
        SEUIL_CO2_MAX = 2000.0
        LOG_LEVEL = 'INFO'
        LOG_FILE_PATH = 'serre_controller_default.log'
        # Ajoutez d'autres attributs de config nécessaires avec des valeurs par défaut
        ACTIVE_DB_CONFIG = {} # Pourrait causer des problèmes si db_utils est utilisé sans config réelle
        BUFFER_SIZE_MAX = 10
        FLUSH_INTERVAL_BUFFER_SECONDES = 300

    config = MockConfig()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')


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
    # Fallback vers MockDatabaseManager si une autre erreur se produit
    class MockDatabaseManager:
        def __init__(self, *args, **kwargs): pass
        def add_sensor_data_to_buffer(self, *args, **kwargs): logging.debug("MockDatabaseManager: add_sensor_data_to_buffer appelé")
        def flush_buffer(self): logging.debug("MockDatabaseManager: flush_buffer appelé")
        def close_pool(self): logging.debug("MockDatabaseManager: close_pool appelé")
    DatabaseManager = MockDatabaseManager


# Le logging est configuré dans main.py ou app.py.
# Ici, on récupère juste le logger.
controller_logger = logging.getLogger(__name__)


class SerreController:
    def __init__(self):
        controller_logger.info("Initialisation de SerreController...")
        self.hardware = self._initialize_hardware()
        
        # S'assurer que db_manager est initialisé même si config.ACTIVE_DB_CONFIG est manquant
        try:
            if hasattr(config, 'ACTIVE_DB_CONFIG') and config.ACTIVE_DB_CONFIG:
                 self.db_manager = DatabaseManager() # DatabaseManager utilise config.ACTIVE_DB_CONFIG en interne
            else:
                controller_logger.warning("config.ACTIVE_DB_CONFIG non trouvé ou vide. Utilisation de MockDatabaseManager.")
                self.db_manager = MockDatabaseManager()
        except Exception as e:
            controller_logger.error(f"Erreur lors de l'initialisation de DatabaseManager: {e}. Utilisation de MockDatabaseManager.")
            self.db_manager = MockDatabaseManager()


        self.temperature = None
        self.humidite = None
        self.co2 = None
        self.last_sensor_read_success = False
        self.sensor_error_count = 0

        self.led_ctrl = LedController(self.hardware, config)
        self.humidifier_ctrl = HumidifierController(self.hardware, config)
        self.ventilation_ctrl = VentilationController(self.hardware, config)

        self.running = True 
        
        self.fast_read_thread = threading.Thread(target=self._fast_sensor_reading_loop, name="FastSensorReadThread", daemon=True)
        self.fast_read_thread.start()
        controller_logger.info("Thread de lecture rapide des capteurs démarré.")

    def _initialize_hardware(self):
        """Charge dynamiquement l'interface matérielle basée sur config.HARDWARE_ENV."""
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

    def _read_sensors_attempt(self) -> bool:
        """Tente de lire les capteurs une fois."""
        try:
            temp, hum, co2_val = self.hardware.lire_capteur()
            if temp is not None and hum is not None and co2_val is not None: # Vérifier que toutes les valeurs sont non-None
                self.temperature = temp
                self.humidite = hum
                self.co2 = co2_val
                return True
            # Si l'une des valeurs est None, considérer cela comme un échec partiel ou total
            controller_logger.warning(f"Données de capteur invalides (au moins une valeur None) reçues: T={temp}, H={hum}, CO2={co2_val}")
            return False
        except Exception as e:
            controller_logger.error(f"Erreur lors de la lecture des capteurs: {e}", exc_info=False) # exc_info=False pour ne pas spammer avec des tracebacks complets ici
            return False

    def _fast_sensor_reading_loop(self):
        error_streak = 0
        while self.running:
            if self._read_sensors_attempt():
                self.last_sensor_read_success = True
                error_streak = 0
                controller_logger.debug(f"Lecture rapide capteurs: T={self.temperature:.1f}, H={self.humidite:.1f}, CO2={self.co2:.0f}")
            else:
                self.last_sensor_read_success = False
                error_streak += 1
                if error_streak % 5 == 0: # Log plus sévèrement tous les 5 échecs
                    controller_logger.warning(f"Échec de lecture des capteurs {error_streak} fois de suite (lecture rapide).")
            time.sleep(config.INTERVALLE_LECTURE_RAPIDE_CAPTEURS_SECONDES)

    def _main_sensor_read_for_logic(self) -> bool:
        if self.last_sensor_read_success and all(x is not None for x in (self.temperature, self.humidite, self.co2)):
            controller_logger.debug("Utilisation des données de capteurs récentes de la lecture rapide pour la logique.")
            return True
        
        controller_logger.info("Tentative de lecture des capteurs pour la logique principale (données rapides non valides ou anciennes).")
        if self._read_sensors_attempt():
             return True # Les self.temperature etc. sont mis à jour par _read_sensors_attempt
        
        controller_logger.warning("Échec de la lecture synchrone des capteurs pour la logique principale.")
        return False


    def _get_current_sensor_values_for_actuators(self) -> dict:
        """Prépare le dictionnaire des valeurs de capteurs pour les contrôleurs d'actionneurs."""
        return {
            'temperature': self.temperature, # Peut être None si la lecture a échoué
            'humidite': self.humidite,
            'co2': self.co2
        }

    def update_logic(self):
        controller_logger.debug("Début du cycle de mise à jour logique.")
        sensor_data_valid_for_logic = self._main_sensor_read_for_logic()
        
        current_sensor_values = self._get_current_sensor_values_for_actuators()

        if sensor_data_valid_for_logic:
            self.sensor_error_count = 0
            controller_logger.info(f"Données capteurs pour logique: T={self.temperature:.1f}°C, H={self.humidite:.1f}%, CO2={self.co2:.0f}ppm")
        else:
            self.sensor_error_count += 1
            controller_logger.warning(f"Échec de lecture des capteurs pour la logique principale (compteur: {self.sensor_error_count}).")
            if self.sensor_error_count >= 5:
                 controller_logger.critical("Échec critique de lecture des capteurs à plusieurs reprises!")

        self.led_ctrl.update_state(current_sensor_values)
        self.humidifier_ctrl.update_state(current_sensor_values)
        self.ventilation_ctrl.update_state(current_sensor_values)

        status_leds = self.led_ctrl.get_status()
        status_humid = self.humidifier_ctrl.get_status()
        status_vent = self.ventilation_ctrl.get_status()

        self.db_manager.add_sensor_data_to_buffer(
            timestamp=datetime.now().replace(microsecond=0),
            temperature=self.temperature,
            humidity=self.humidite,
            co2=self.co2,
            humidifier_active=status_humid["is_active"],
            ventilation_active=status_vent["is_active"],
            leds_active=status_leds["is_active"],
            humidifier_on_duration=status_humid["on_duration_seconds"] if status_humid["is_active"] else None,
            humidifier_off_duration=status_humid["off_duration_seconds"] if not status_humid["is_active"] else None,
            ventilation_on_duration=status_vent["on_duration_seconds"] if status_vent["is_active"] else None,
            ventilation_off_duration=status_vent["off_duration_seconds"] if not status_vent["is_active"] else None
        )
        controller_logger.debug("Fin du cycle de mise à jour logique.")


    def run(self):
        controller_logger.info("SerreController démarré. Boucle principale active.")
        try:
            while self.running:
                self.update_logic()
                time.sleep(config.INTERVALLE_LECTURE_CAPTEURS_SECONDES)
        except KeyboardInterrupt: # Ne devrait pas arriver ici si le thread est daemon et main gère SIGINT
            controller_logger.info("Arrêt demandé par l'utilisateur (KeyboardInterrupt dans SerreController.run).")
        except Exception as e:
            controller_logger.critical(f"Erreur non gérée dans la boucle principale de SerreController: {e}", exc_info=True)
        finally:
            # Le shutdown est normalement appelé par le script principal (main.py ou app.py)
            # Mais si ce thread se termine de manière inattendue, on s'assure que self.running est False.
            self.running = False 
            controller_logger.info("Boucle principale de SerreController terminée.")


    def get_status(self) -> dict:
        status_leds = self.led_ctrl.get_status()
        status_humid = self.humidifier_ctrl.get_status()
        status_vent = self.ventilation_ctrl.get_status()
        
        # Formater les valeurs numériques pour l'affichage
        temp_display = f"{self.temperature:.1f}" if self.temperature is not None else "N/A"
        hum_display = f"{self.humidite:.1f}" if self.humidite is not None else "N/A"
        co2_display = f"{self.co2:.0f}" if self.co2 is not None else "N/A"

        return {
            "timestamp": datetime.now().replace(microsecond=0).strftime('%Y-%m-%d %H:%M:%S'),
            "temperature": temp_display,
            "humidite": hum_display,
            "co2": co2_display,
            "sensor_read_ok": self.last_sensor_read_success,
            "leds": status_leds,
            "humidifier": status_humid,
            "ventilation": status_vent,
        }

    def _force_actuator_update(self, actuator_controller):
        """Force la mise à jour d'un contrôleur d'actionneur spécifique."""
        current_sensor_values = self._get_current_sensor_values_for_actuators()
        if actuator_controller.update_state(current_sensor_values):
            controller_logger.info(f"État de {actuator_controller.device_name} mis à jour immédiatement (contrôle manuel).")
        # La mise à jour de la base de données se fera au prochain cycle de update_logic()

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
        self._force_actuator_update(self.led_ctrl) # Mettre à jour l'état immédiatement après passage en auto
        
        self.humidifier_ctrl.set_manual_mode(False)
        self._force_actuator_update(self.humidifier_ctrl)

        self.ventilation_ctrl.set_manual_mode(False)
        self._force_actuator_update(self.ventilation_ctrl)
        
        controller_logger.info("Tous les actionneurs sont repassés en mode automatique et leur état a été mis à jour.")

    def emergency_stop_all_actuators(self):
        controller_logger.warning("ARRÊT D'URGENCE ACTIVÉ")
        # Forcer l'état manuel OFF pour chaque actionneur et mettre à jour immédiatement
        self.led_ctrl.set_manual_mode(True, False)
        self._force_actuator_update(self.led_ctrl)
        
        self.humidifier_ctrl.set_manual_mode(True, False)
        self._force_actuator_update(self.humidifier_ctrl)

        self.ventilation_ctrl.set_manual_mode(True, False)
        self._force_actuator_update(self.ventilation_ctrl)
        
        controller_logger.info("Tous les actionneurs ont été désactivés (arrêt d'urgence).")


    def shutdown(self):
        controller_logger.info("Arrêt de SerreController...")
        self.running = False 
        
        if self.fast_read_thread and self.fast_read_thread.is_alive():
            controller_logger.info("Attente de la fin du thread de lecture rapide...")
            self.fast_read_thread.join(timeout=config.INTERVALLE_LECTURE_RAPIDE_CAPTEURS_SECONDES + 2) 
            if self.fast_read_thread.is_alive():
                controller_logger.warning("Le thread de lecture rapide n'a pas pu être arrêté proprement.")
        
        controller_logger.info("Vidage du buffer de la base de données avant l'arrêt...")
        self.db_manager.flush_buffer()
        self.db_manager.close_pool()
        
        if self.hardware:
            controller_logger.info("Nettoyage du matériel...")
            self.hardware.cleanup()
        
        controller_logger.info("SerreController arrêté.")



