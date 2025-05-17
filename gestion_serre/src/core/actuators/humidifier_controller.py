# src/core/actuators/humidifier_controller.py
from .base_actuator import BaseActuator
from datetime import datetime
import time
import logging

class HumidifierController(BaseActuator):
    """
    Contrôleur spécifique pour la gestion de l'humidificateur.
    """
    def __init__(self, hardware_interface, config):
        super().__init__(hardware_interface, "humidifier")
        self.config = config # Contient SEUIL_HUMIDITE_ON, SEUIL_HUMIDITE_OFF, etc.
        self.last_special_session_done_today = False # Pour la session spéciale 21h30-21h35

    def _get_desired_automatic_state(self, current_sensor_data: dict) -> bool:
        """
        Détermine si l'humidificateur doit être actif en mode automatique.
        Prend en compte l'humidité, les plages horaires et une session spéciale.
        """
        humidite = current_sensor_data.get('humidite')
        if humidite is None:
            logging.warning("Humidité non disponible pour HumidifierController, maintien de l'état.")
            return self.current_state # Maintient l'état actuel si pas de lecture d'humidité

        now = datetime.now()
        heure_actuelle = now.hour
        minute_actuelle = now.minute

        # Réinitialiser le drapeau de la session spéciale après minuit ou à un certain moment
        # Ici, on le réinitialise si on est après 8h du matin et qu'il était fait.
        if heure_actuelle >= 8 and self.last_special_session_done_today:
             self.last_special_session_done_today = False
             logging.info("Réinitialisation du flag de session spéciale d'humidification.")

        # Conditions de fonctionnement automatique
        # 1. Hors plage horaire principale (nuit : 22h à 8h) -> OFF
        if 22 <= heure_actuelle or heure_actuelle < 8:
            return False

        # 2. Session spéciale (ex: 21h30 à 21h35) -> ON, si pas déjà faite aujourd'hui
        is_special_session_time = (heure_actuelle == 21 and 30 <= minute_actuelle < 35)
        if is_special_session_time and not self.last_special_session_done_today:
            # Ne pas marquer comme fait ici, seulement si l'humidificateur s'éteint APRÈS cette session
            # ou si la session se termine et qu'il était ON.
            return True
        
        # Si la session spéciale est terminée et l'humidificateur était ON à cause de cela,
        # il doit s'éteindre si les autres conditions ne le maintiennent pas ON.
        # Et on marque la session comme faite.
        if not is_special_session_time and self.current_state and \
           (heure_actuelle == 21 and minute_actuelle >= 35) and \
           not self.last_special_session_done_today:
            # Vérifie si la raison pour laquelle il était ON était la session spéciale
            # Ceci est un peu délicat, car on ne sait pas pourquoi il était ON.
            # On suppose que si on est juste après la session et qu'il est ON,
            # on peut marquer la session comme faite.
            # Une meilleure approche serait de savoir si la *décision* de l'allumer
            # était due à la session spéciale.
            # Pour simplifier, on le marque fait si on sort de la plage horaire
            # et qu'il était actif.
            pass # La logique ci-dessous déterminera s'il doit s'éteindre.


        # 3. Logique basée sur les seuils d'humidité
        if humidite < self.config.SEUIL_HUMIDITE_ON:
            return True
        elif humidite >= self.config.SEUIL_HUMIDITE_OFF:
            # Si on éteint l'humidificateur et que c'était pendant/après la session spéciale,
            # marquer la session comme faite.
            if is_special_session_time or \
               (heure_actuelle == 21 and minute_actuelle >= 35 and not self.last_special_session_done_today):
                self.last_special_session_done_today = True
                logging.info("Session spéciale d'humidification marquée comme terminée.")
            return False
        else:
            # Hystérésis: maintenir l'état actuel si entre les deux seuils
            return self.current_state

    def _control_hardware(self):
        """
        Active ou désactive l'humidificateur via l'interface matérielle.
        """
        if self.current_state:
            self.hardware.activer_humidificateur()
            # logging.info("Humidificateur activé.")
        else:
            self.hardware.desactiver_humidificateur()
            # logging.info("Humidificateur désactivé.")

    def update_state(self, current_sensor_data: dict) -> bool:
        """
        Met à jour l'état de l'humidificateur et contrôle le matériel.
        """
        state_changed = super().update_state(current_sensor_data)
        if state_changed:
            self._control_hardware()
            logging.info(f"Humidificateur: état changé. Manuel: {self.is_manual_mode}, Actif: {self.current_state}, Hum: {current_sensor_data.get('humidite')}")
        return state_changed
