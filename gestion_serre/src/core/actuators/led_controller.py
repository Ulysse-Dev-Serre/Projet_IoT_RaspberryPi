# src/core/actuators/led_controller.py
from .base_actuator import BaseActuator
from datetime import datetime
import logging
import config # Importer config pour accéder à DEFAULT_SETTINGS pour les fallbacks

class LedController(BaseActuator):
    """
    Contrôleur spécifique pour la gestion des LEDs.
    Utilise les configurations dynamiques fournies par SerreController.
    """
    def __init__(self, hardware_interface, controller_instance): # Modifié: controller_instance au lieu de config
        super().__init__(hardware_interface, "leds")
        self.controller = controller_instance # Stocker l'instance de SerreController
        # self.config n'est plus utilisé directement ici pour les paramètres dynamiques

    def _get_desired_automatic_state(self, current_sensor_data: dict) -> bool:
        """
        Détermine si les LEDs doivent être allumées en mode automatique.
        Les LEDs sont allumées pendant une plage horaire définie dans les configurations utilisateur.
        `current_sensor_data` n'est pas utilisé ici mais est requis par la signature.
        """
        heure_actuelle = datetime.now().hour

        # Récupérer les horaires depuis les settings dynamiques via SerreController
        # Utiliser les valeurs de config.DEFAULT_SETTINGS comme fallback robuste
        default_heure_debut = config.DEFAULT_SETTINGS.get('HEURE_DEBUT_LEDS', 8) # Valeur par défaut si la clé est absente
        default_heure_fin = config.DEFAULT_SETTINGS.get('HEURE_FIN_LEDS', 20)

        heure_debut_leds_setting = self.controller.get_setting('HEURE_DEBUT_LEDS', default_heure_debut)
        heure_fin_leds_setting = self.controller.get_setting('HEURE_FIN_LEDS', default_heure_fin)

        try:
            # S'assurer que les heures sont des entiers
            heure_debut_leds = int(heure_debut_leds_setting)
            heure_fin_leds = int(heure_fin_leds_setting)
            
            # Validation simple des plages horaires
            if not (0 <= heure_debut_leds <= 23 and 0 <= heure_fin_leds <= 23):
                logging.warning(f"LedController: Horaires invalides (debut: {heure_debut_leds}, fin: {heure_fin_leds}). Utilisation des défauts: {default_heure_debut}-{default_heure_fin}.")
                heure_debut_leds = default_heure_debut
                heure_fin_leds = default_heure_fin

        except (ValueError, TypeError) as e:
            logging.error(f"LedController: Erreur de conversion des heures pour les LEDs (valeurs: '{heure_debut_leds_setting}', '{heure_fin_leds_setting}'): {e}. Utilisation des valeurs par défaut.")
            heure_debut_leds = default_heure_debut
            heure_fin_leds = default_heure_fin
        
        # Logique d'allumage
        # Gère le cas où la plage horaire traverse minuit (ex: 22h à 6h)
        if heure_debut_leds <= heure_fin_leds:
            # Plage horaire normale (ex: 8h à 20h)
            return heure_debut_leds <= heure_actuelle < heure_fin_leds
        else:
            # Plage horaire qui traverse minuit (ex: 20h à 6h du matin)
            # LEDs allumées si heure_actuelle >= heure_debut_leds OU heure_actuelle < heure_fin_leds
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
        # current_sensor_data n'est pas utilisé par _get_desired_automatic_state pour les LEDs,
        # mais est passé pour respecter la signature de la classe de base.
        state_changed = super().update_state(current_sensor_data)
        if state_changed: 
            self._control_hardware() 
            logging.info(f"LEDs: état changé. Manuel: {self.is_manual_mode}, Actif: {self.current_state}")
        return state_changed
