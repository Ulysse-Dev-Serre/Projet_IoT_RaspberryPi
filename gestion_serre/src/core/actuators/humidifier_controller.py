# src/core/actuators/humidifier_controller.py
from .base_actuator import BaseActuator
from datetime import datetime
import logging
import config # Importer config pour accéder à DEFAULT_SETTINGS pour les fallbacks

class HumidifierController(BaseActuator):
    """
    Contrôleur spécifique pour la gestion de l'humidificateur.
    Utilise les configurations dynamiques fournies par SerreController.
    """
    def __init__(self, hardware_interface, controller_instance): # Modifié
        super().__init__(hardware_interface, "humidifier")
        self.controller = controller_instance # Stocker l'instance de SerreController
        # La gestion de last_special_session_done_today reste locale au contrôleur d'humidificateur
        # car elle n'est pas un paramètre utilisateur direct, mais une logique interne.
        # Si vous voulez rendre la session spéciale configurable (activée/désactivée, horaires),
        # ces paramètres seraient lus via self.controller.get_setting().
        self.last_special_session_done_today = False 

    def _get_desired_automatic_state(self, current_sensor_data: dict) -> bool:
        """
        Détermine si l'humidificateur doit être actif en mode automatique.
        Prend en compte l'humidité, les plages horaires et une session spéciale (si activée).
        """
        humidite = current_sensor_data.get('humidite')

        # Récupérer les settings dynamiques
        default_seuil_on = config.DEFAULT_SETTINGS.get('SEUIL_HUMIDITE_ON', 75.0)
        default_seuil_off = config.DEFAULT_SETTINGS.get('SEUIL_HUMIDITE_OFF', 85.0)
        default_heure_debut_op = config.DEFAULT_SETTINGS.get('HEURE_DEBUT_JOUR_OPERATION', 8)
        default_heure_fin_op = config.DEFAULT_SETTINGS.get('HEURE_FIN_JOUR_OPERATION', 22)

        seuil_humidite_on = self.controller.get_setting('SEUIL_HUMIDITE_ON', default_seuil_on)
        seuil_humidite_off = self.controller.get_setting('SEUIL_HUMIDITE_OFF', default_seuil_off)
        heure_debut_operation = self.controller.get_setting('HEURE_DEBUT_JOUR_OPERATION', default_heure_debut_op)
        heure_fin_operation = self.controller.get_setting('HEURE_FIN_JOUR_OPERATION', default_heure_fin_op)
        
        # Exemple si la session spéciale était configurable :
        # special_session_enabled = self.controller.get_setting('HUMIDIFIER_SPECIAL_SESSION_ENABLED', False)
        # special_session_start_h = self.controller.get_setting('HUMIDIFIER_SPECIAL_SESSION_START_H', 21)
        # special_session_start_m = self.controller.get_setting('HUMIDIFIER_SPECIAL_SESSION_START_M', 30)
        # special_session_duration_m = self.controller.get_setting('HUMIDIFIER_SPECIAL_SESSION_DURATION_MINUTES', 5)

        try:
            seuil_humidite_on = float(seuil_humidite_on)
            seuil_humidite_off = float(seuil_humidite_off)
            heure_debut_operation = int(heure_debut_operation)
            heure_fin_operation = int(heure_fin_operation)
            # Valider les plages horaires
            if not (0 <= heure_debut_operation <= 23 and 0 <= heure_fin_operation <= 23):
                logging.warning(f"HumidifierController: Horaires d'opération invalides. Utilisation des défauts.")
                heure_debut_operation = default_heure_debut_op
                heure_fin_operation = default_heure_fin_op
        except (ValueError, TypeError) as e:
            logging.error(f"HumidifierController: Erreur de conversion des settings: {e}. Utilisation des valeurs par défaut.")
            seuil_humidite_on = default_seuil_on
            seuil_humidite_off = default_seuil_off
            heure_debut_operation = default_heure_debut_op
            heure_fin_operation = default_heure_fin_op

        if humidite is None:
            logging.warning("Humidité non disponible pour HumidifierController, maintien de l'état.")
            return self.current_state

        now = datetime.now()
        heure_actuelle = now.hour
        # minute_actuelle = now.minute # Nécessaire si la session spéciale est plus fine

        # Logique de la plage horaire d'opération générale
        # Gère le cas où la plage horaire traverse minuit
        in_operation_window = False
        if heure_debut_operation <= heure_fin_operation:
            in_operation_window = heure_debut_operation <= heure_actuelle < heure_fin_operation
        else: # Traverse minuit (ex: 22h à 8h)
            in_operation_window = heure_actuelle >= heure_debut_operation or heure_actuelle < heure_fin_operation
        
        if not in_operation_window:
            # logging.debug(f"Humidifier: Hors plage horaire d'opération ({heure_debut_operation}-{heure_fin_operation}). Actuel: {heure_actuelle}. OFF.")
            return False # Toujours OFF hors de la fenêtre d'opération

        # Logique de la session spéciale (si vous l'implémentez de manière configurable)
        # Pour l'instant, la logique de session spéciale de 21h30-21h35 est conservée comme avant,
        # mais elle devrait idéalement aussi utiliser les heures configurables.
        # Réinitialiser le drapeau de la session spéciale
        if heure_actuelle >= heure_debut_operation and self.last_special_session_done_today: # Ex: après 8h
             self.last_special_session_done_today = False
             logging.info("HumidifierController: Réinitialisation du flag de session spéciale d'humidification.")
        
        is_special_session_time = (heure_actuelle == 21 and 30 <= now.minute < 35) # Exemple fixe
        if is_special_session_time and not self.last_special_session_done_today:
            logging.info("HumidifierController: En session spéciale d'humidification. Activation.")
            return True
        
        # Logique basée sur les seuils d'humidité (hystérésis)
        if humidite < seuil_humidite_on:
            return True
        elif humidite >= seuil_humidite_off:
            # Si on éteint et que c'était après la fin d'une session spéciale, marquer comme faite.
            if (heure_actuelle == 21 and now.minute >= 35) and not self.last_special_session_done_today:
                # Cette condition est un peu approximative pour détecter la fin de la session spéciale
                # Elle suppose que si on éteint après 21h35, la session a eu lieu.
                self.last_special_session_done_today = True
                logging.info("HumidifierController: Session spéciale d'humidification marquée comme terminée (extinction après).")
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
        else:
            self.hardware.desactiver_humidificateur()

    def update_state(self, current_sensor_data: dict) -> bool:
        """
        Met à jour l'état de l'humidificateur et contrôle le matériel.
        """
        state_changed = super().update_state(current_sensor_data)
        if state_changed:
            self._control_hardware()
            logging.info(f"Humidificateur: état changé. Manuel: {self.is_manual_mode}, Actif: {self.current_state}, Hum: {current_sensor_data.get('humidite')}")
        return state_changed

