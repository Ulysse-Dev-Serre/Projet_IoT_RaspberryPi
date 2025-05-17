# src/core/actuators/ventilation_controller.py
from .base_actuator import BaseActuator
from datetime import datetime
import logging

class VentilationController(BaseActuator):
    """
    Contrôleur spécifique pour la gestion de la ventilation.
    """
    def __init__(self, hardware_interface, config):
        super().__init__(hardware_interface, "ventilation")
        self.config = config # Contient SEUIL_CO2_MAX, etc.

    def _get_desired_automatic_state(self, current_sensor_data: dict) -> bool:
        """
        Détermine si la ventilation doit être active en mode automatique.
        Basé sur le niveau de CO2 et les plages horaires.
        """
        co2 = current_sensor_data.get('co2')
        if co2 is None:
            logging.warning("CO2 non disponible pour VentilationController, maintien de l'état.")
            return self.current_state # Maintient l'état actuel

        now = datetime.now()
        heure_actuelle = now.hour

        # Hors plage horaire principale (nuit : 22h à 8h) -> OFF
        if 22 <= heure_actuelle or heure_actuelle < 8:
            return False

        # Logique basée sur le seuil de CO2
        # Note: La logique originale était `self.co2 > self.SEUIL_CO2_MAX`.
        # Si le CO2 est haut, on ventile. Si bas, on arrête.
        # Pas d'hystérésis explicite dans le code original pour la ventilation,
        # donc on active si > SEUIL_CO2_MAX, sinon on désactive.
        if co2 > self.config.SEUIL_CO2_MAX:
            return True
        else:
            return False # Désactiver si le CO2 est en dessous du seuil max

    def _control_hardware(self):
        """
        Active ou désactive la ventilation via l'interface matérielle.
        """
        if self.current_state:
            self.hardware.activer_ventilation()
            # logging.info("Ventilation activée.")
        else:
            self.hardware.desactiver_ventilation()
            # logging.info("Ventilation désactivée.")
    
    def update_state(self, current_sensor_data: dict) -> bool:
        """
        Met à jour l'état de la ventilation et contrôle le matériel.
        """
        state_changed = super().update_state(current_sensor_data)
        if state_changed:
            self._control_hardware()
            logging.info(f"Ventilation: état changé. Manuel: {self.is_manual_mode}, Actif: {self.current_state}, CO2: {current_sensor_data.get('co2')}")
        return state_changed
