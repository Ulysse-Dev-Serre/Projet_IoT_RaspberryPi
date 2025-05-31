# src/core/actuators/ventilation_controller.py
from .base_actuator import BaseActuator
from datetime import datetime
import logging
from src import config # Importer le module config depuis src

class VentilationController(BaseActuator):
    """
    Contrôleur spécifique pour la gestion de la ventilation.
    Utilise les configurations dynamiques fournies par SerreController
    et les valeurs par défaut globales de src.config.
    """
    def __init__(self, hardware_interface, controller_instance):
        super().__init__(hardware_interface, "ventilation")
        self.controller = controller_instance

    def _get_desired_automatic_state(self, current_sensor_data: dict) -> bool:
        """
        Détermine si la ventilation doit être active en mode automatique.
        """
        # La clé pour lire la valeur CO2 est 'co2' par défaut, tel que défini dans config.CO2_SENSOR_INSTANCE_NAME
        # Si vous rendez KEY_NOM_CAPTEUR_CO2 dynamique (ex: "MonCapteurCO2"), il faudrait lire :
        # co2_sensor_key = self.controller.get_setting(config.KEY_NOM_CAPTEUR_CO2, config.CO2_SENSOR_INSTANCE_NAME)
        # co2 = current_sensor_data.get(co2_sensor_key)
        co2 = current_sensor_data.get(config.CO2_SENSOR_INSTANCE_NAME) # Utilise la valeur de config

        # Récupérer les settings dynamiques via SerreController.
        # Utiliser les constantes globales de config comme fallback.
        seuil_co2_max_setting = self.controller.get_setting(
            config.KEY_SEUIL_CO2_MAX,
            config.CO2_MAX_THRESHOLD # Valeur par défaut globale de config.py
        )
        heure_debut_operation_setting = self.controller.get_setting(
            config.KEY_HEURE_DEBUT_JOUR_OPERATION,
            config.HEURE_DEBUT_JOUR_OPERATION # Valeur par défaut globale de config.py
        )
        heure_fin_operation_setting = self.controller.get_setting(
            config.KEY_HEURE_FIN_JOUR_OPERATION,
            config.HEURE_FIN_JOUR_OPERATION # Valeur par défaut globale de config.py
        )

        try:
            seuil_co2_max = float(seuil_co2_max_setting)
            heure_debut_operation = int(heure_debut_operation_setting)
            heure_fin_operation = int(heure_fin_operation_setting)

            if not (0 <= heure_debut_operation <= 23 and 0 <= heure_fin_operation <= 23):
                logging.warning(
                    f"VentilationController: Horaires d'opération invalides. "
                    f"Utilisation des défauts globaux: {config.HEURE_DEBUT_JOUR_OPERATION}-{config.HEURE_FIN_JOUR_OPERATION}."
                )
                heure_debut_operation = config.HEURE_DEBUT_JOUR_OPERATION
                heure_fin_operation = config.HEURE_FIN_JOUR_OPERATION
        except (ValueError, TypeError) as e:
            logging.error(
                f"VentilationController: Erreur de conversion des settings: {e}. "
                f"Utilisation des valeurs par défaut globaux."
            )
            seuil_co2_max = config.CO2_MAX_THRESHOLD
            heure_debut_operation = config.HEURE_DEBUT_JOUR_OPERATION
            heure_fin_operation = config.HEURE_FIN_JOUR_OPERATION

        if co2 is None:
            logging.warning(f"CO2 non disponible pour VentilationController (clé attendue: '{config.CO2_SENSOR_INSTANCE_NAME}'), maintien de l'état.")
            return self.current_state 

        now = datetime.now()
        heure_actuelle = now.hour

        in_operation_window = False
        if heure_debut_operation <= heure_fin_operation:
            in_operation_window = heure_debut_operation <= heure_actuelle < heure_fin_operation
        else: 
            in_operation_window = heure_actuelle >= heure_debut_operation or heure_actuelle < heure_fin_operation
        
        if not in_operation_window:
            return False

        if co2 > seuil_co2_max:
            return True
        else:
            return False 

    def _control_hardware(self):
        if self.current_state:
            self.hardware.activer_ventilation()
        else:
            self.hardware.desactiver_ventilation()
    
    def update_state(self, current_sensor_data: dict) -> bool:
        state_changed = super().update_state(current_sensor_data)
        if state_changed:
            self._control_hardware()
            logging.info(f"Ventilation: état changé. Manuel: {self.is_manual_mode}, Actif: {self.current_state}, CO2: {current_sensor_data.get(config.CO2_SENSOR_INSTANCE_NAME)}")
        return state_changed


