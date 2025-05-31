# src/core/actuators/humidifier_controller.py
from .base_actuator import BaseActuator
from datetime import datetime
import logging
from src import config # Importer le module config depuis src

class HumidifierController(BaseActuator):
    """
    Contrôleur spécifique pour la gestion de l'humidificateur.
    Utilise les configurations dynamiques fournies par SerreController
    et les valeurs par défaut globales de src.config.
    """
    def __init__(self, hardware_interface, controller_instance):
        super().__init__(hardware_interface, "humidifier")
        self.controller = controller_instance
        self.last_special_session_done_today = False

    def _get_desired_automatic_state(self, current_sensor_data: dict) -> bool:
        """
        Détermine si l'humidificateur doit être actif en mode automatique.
        """
        humidite = current_sensor_data.get('humidite')

        # Récupérer les settings dynamiques via SerreController.
        # Utiliser les constantes globales de config comme fallback.
        seuil_humidite_on_setting = self.controller.get_setting(
            config.KEY_SEUIL_HUMIDITE_ON,
            config.SEUIL_HUMIDITE_ON # Valeur par défaut globale de config.py
        )
        seuil_humidite_off_setting = self.controller.get_setting(
            config.KEY_SEUIL_HUMIDITE_OFF,
            config.SEUIL_HUMIDITE_OFF # Valeur par défaut globale de config.py
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
            seuil_humidite_on = float(seuil_humidite_on_setting)
            seuil_humidite_off = float(seuil_humidite_off_setting)
            heure_debut_operation = int(heure_debut_operation_setting)
            heure_fin_operation = int(heure_fin_operation_setting)

            if not (0 <= heure_debut_operation <= 23 and 0 <= heure_fin_operation <= 23):
                logging.warning(
                    f"HumidifierController: Horaires d'opération invalides. "
                    f"Utilisation des défauts globaux: {config.HEURE_DEBUT_JOUR_OPERATION}-{config.HEURE_FIN_JOUR_OPERATION}."
                )
                heure_debut_operation = config.HEURE_DEBUT_JOUR_OPERATION
                heure_fin_operation = config.HEURE_FIN_JOUR_OPERATION
        except (ValueError, TypeError) as e:
            logging.error(
                f"HumidifierController: Erreur de conversion des settings: {e}. "
                f"Utilisation des valeurs par défaut globaux."
            )
            seuil_humidite_on = config.SEUIL_HUMIDITE_ON
            seuil_humidite_off = config.SEUIL_HUMIDITE_OFF
            heure_debut_operation = config.HEURE_DEBUT_JOUR_OPERATION
            heure_fin_operation = config.HEURE_FIN_JOUR_OPERATION

        if humidite is None:
            logging.warning("Humidité non disponible pour HumidifierController, maintien de l'état.")
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

        # Logique de la session spéciale (exemple fixe, pourrait être rendue configurable)
        if heure_actuelle >= heure_debut_operation and self.last_special_session_done_today:
             self.last_special_session_done_today = False
             logging.info("HumidifierController: Réinitialisation du flag de session spéciale d'humidification.")
        
        is_special_session_time = (heure_actuelle == 21 and 30 <= now.minute < 35)
        if is_special_session_time and not self.last_special_session_done_today:
            logging.info("HumidifierController: En session spéciale d'humidification. Activation.")
            return True
        
        if humidite < seuil_humidite_on:
            return True
        elif humidite >= seuil_humidite_off:
            if (heure_actuelle == 21 and now.minute >= 35) and not self.last_special_session_done_today:
                self.last_special_session_done_today = True
                logging.info("HumidifierController: Session spéciale d'humidification marquée comme terminée (extinction après).")
            return False
        else:
            return self.current_state

    def _control_hardware(self):
        if self.current_state:
            self.hardware.activer_humidificateur()
        else:
            self.hardware.desactiver_humidificateur()

    def update_state(self, current_sensor_data: dict) -> bool:
        state_changed = super().update_state(current_sensor_data)
        if state_changed:
            self._control_hardware()
            logging.info(f"Humidificateur: état changé. Manuel: {self.is_manual_mode}, Actif: {self.current_state}, Hum: {current_sensor_data.get('humidite')}")
        return state_changed

