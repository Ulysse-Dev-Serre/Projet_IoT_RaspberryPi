# src/core/actuators/led_controller.py
from .base_actuator import BaseActuator
from datetime import datetime
import logging
from src import config # Importer le module config depuis src

class LedController(BaseActuator):
    """
    Contrôleur spécifique pour la gestion des LEDs.
    Utilise les configurations dynamiques fournies par SerreController
    et les valeurs par défaut globales de src.config.
    """
    def __init__(self, hardware_interface, controller_instance):
        super().__init__(hardware_interface, "leds")
        self.controller = controller_instance

    def _get_desired_automatic_state(self, current_sensor_data: dict) -> bool:
        """
        Détermine si les LEDs doivent être allumées en mode automatique.
        Les LEDs sont allumées pendant une plage horaire définie.
        `current_sensor_data` n'est pas utilisé ici mais est requis par la signature.
        """
        heure_actuelle = datetime.now().hour

        # Récupérer les horaires depuis les settings dynamiques via SerreController.
        # Utiliser les constantes globales de config (initialisées depuis DEFAULT_SETTINGS) comme fallback.
        heure_debut_leds_setting = self.controller.get_setting(
            config.KEY_HEURE_DEBUT_LEDS,
            config.HEURE_DEBUT_LEDS # Valeur par défaut globale de config.py
        )
        heure_fin_leds_setting = self.controller.get_setting(
            config.KEY_HEURE_FIN_LEDS,
            config.HEURE_FIN_LEDS # Valeur par défaut globale de config.py
        )

        try:
            heure_debut_leds = int(heure_debut_leds_setting)
            heure_fin_leds = int(heure_fin_leds_setting)
            
            if not (0 <= heure_debut_leds <= 23 and 0 <= heure_fin_leds <= 23):
                logging.warning(
                    f"LedController: Horaires invalides (debut: {heure_debut_leds}, fin: {heure_fin_leds}). "
                    f"Utilisation des défauts globaux: {config.HEURE_DEBUT_LEDS}-{config.HEURE_FIN_LEDS}."
                )
                heure_debut_leds = config.HEURE_DEBUT_LEDS
                heure_fin_leds = config.HEURE_FIN_LEDS

        except (ValueError, TypeError) as e:
            logging.error(
                f"LedController: Erreur de conversion des heures pour les LEDs "
                f"(valeurs: '{heure_debut_leds_setting}', '{heure_fin_leds_setting}'): {e}. "
                f"Utilisation des valeurs par défaut globaux."
            )
            heure_debut_leds = config.HEURE_DEBUT_LEDS
            heure_fin_leds = config.HEURE_FIN_LEDS
        
        if heure_debut_leds <= heure_fin_leds:
            return heure_debut_leds <= heure_actuelle < heure_fin_leds
        else:
            return heure_actuelle >= heure_debut_leds or heure_actuelle < heure_fin_leds

    def _control_hardware(self):
        """
        Active ou désactive les LEDs via l'interface matérielle.
        """
        if self.current_state:
            self.hardware.activer_leds()
        else:
            self.hardware.desactiver_leds()

    def update_state(self, current_sensor_data: dict) -> bool:
        """
        Met à jour l'état des LEDs et contrôle le matériel.
        """
        state_changed = super().update_state(current_sensor_data)
        if state_changed: 
            self._control_hardware() 
            logging.info(f"LEDs: état changé. Manuel: {self.is_manual_mode}, Actif: {self.current_state}")
        return state_changed
