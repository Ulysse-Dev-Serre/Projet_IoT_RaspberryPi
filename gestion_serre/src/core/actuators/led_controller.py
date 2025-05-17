# src/core/actuators/led_controller.py
from .base_actuator import BaseActuator
from datetime import datetime
import logging

class LedController(BaseActuator):
    """
    Contrôleur spécifique pour la gestion des LEDs.
    """
    def __init__(self, hardware_interface, config):
        super().__init__(hardware_interface, "leds")
        self.config = config # Contient HEURE_DEBUT_LEDS, HEURE_FIN_LEDS

    def _get_desired_automatic_state(self, current_sensor_data: dict) -> bool:
        """
        Détermine si les LEDs doivent être allumées en mode automatique.
        Les LEDs sont allumées pendant une plage horaire définie dans la configuration.
        `current_sensor_data` n'est pas utilisé ici mais est requis par la signature.
        """
        heure_actuelle = datetime.now().hour
        return self.config.HEURE_DEBUT_LEDS <= heure_actuelle < self.config.HEURE_FIN_LEDS

    def _control_hardware(self):
        """
        Active ou désactive les LEDs via l'interface matérielle.
        """
        if self.current_state:
            self.hardware.activer_leds()
            # logging.info("LEDs activées.")
        else:
            self.hardware.desactiver_leds()
            # logging.info("LEDs désactivées.")

    def update_state(self, current_sensor_data: dict) -> bool:
        """
        Met à jour l'état des LEDs et contrôle le matériel.
        """
        state_changed = super().update_state(current_sensor_data)
        if state_changed: # Si l'état a changé (déterminé par la classe de base)
            self._control_hardware() # Appliquer le nouvel état au matériel
            logging.info(f"LEDs: état changé. Manuel: {self.is_manual_mode}, Actif: {self.current_state}")
        return state_changed
