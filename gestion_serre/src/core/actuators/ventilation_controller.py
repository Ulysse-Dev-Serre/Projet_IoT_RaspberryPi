# src/core/actuators/ventilation_controller.py
from .base_actuator import BaseActuator
from datetime import datetime
import logging
import config # Importer config pour accéder à DEFAULT_SETTINGS pour les fallbacks

class VentilationController(BaseActuator):
    """
    Contrôleur spécifique pour la gestion de la ventilation.
    Utilise les configurations dynamiques fournies par SerreController.
    """
    def __init__(self, hardware_interface, controller_instance): # Modifié
        super().__init__(hardware_interface, "ventilation")
        self.controller = controller_instance # Stocker l'instance de SerreController

    def _get_desired_automatic_state(self, current_sensor_data: dict) -> bool:
        """
        Détermine si la ventilation doit être active en mode automatique.
        Basé sur le niveau de CO2 et les plages horaires d'opération.
        """
        co2 = current_sensor_data.get('co2')

        # Récupérer les settings dynamiques
        default_seuil_co2_max = config.DEFAULT_SETTINGS.get('SEUIL_CO2_MAX', 2000.0)
        default_heure_debut_op = config.DEFAULT_SETTINGS.get('HEURE_DEBUT_JOUR_OPERATION', 8)
        default_heure_fin_op = config.DEFAULT_SETTINGS.get('HEURE_FIN_JOUR_OPERATION', 22)

        seuil_co2_max = self.controller.get_setting('SEUIL_CO2_MAX', default_seuil_co2_max)
        heure_debut_operation = self.controller.get_setting('HEURE_DEBUT_JOUR_OPERATION', default_heure_debut_op)
        heure_fin_operation = self.controller.get_setting('HEURE_FIN_JOUR_OPERATION', default_heure_fin_op)

        try:
            seuil_co2_max = float(seuil_co2_max)
            heure_debut_operation = int(heure_debut_operation)
            heure_fin_operation = int(heure_fin_operation)
            # Valider les plages horaires
            if not (0 <= heure_debut_operation <= 23 and 0 <= heure_fin_operation <= 23):
                logging.warning(f"VentilationController: Horaires d'opération invalides. Utilisation des défauts.")
                heure_debut_operation = default_heure_debut_op
                heure_fin_operation = default_heure_fin_op
        except (ValueError, TypeError) as e:
            logging.error(f"VentilationController: Erreur de conversion des settings: {e}. Utilisation des valeurs par défaut.")
            seuil_co2_max = default_seuil_co2_max
            heure_debut_operation = default_heure_debut_op
            heure_fin_operation = default_heure_fin_op

        if co2 is None:
            logging.warning("CO2 non disponible pour VentilationController, maintien de l'état.")
            return self.current_state 

        now = datetime.now()
        heure_actuelle = now.hour

        # Logique de la plage horaire d'opération générale
        in_operation_window = False
        if heure_debut_operation <= heure_fin_operation: # Ex: 8h à 22h
            in_operation_window = heure_debut_operation <= heure_actuelle < heure_fin_operation
        else: # Traverse minuit (ex: 22h à 8h du matin)
            in_operation_window = heure_actuelle >= heure_debut_operation or heure_actuelle < heure_fin_operation
        
        if not in_operation_window:
            # logging.debug(f"Ventilation: Hors plage horaire d'opération ({heure_debut_operation}-{heure_fin_operation}). Actuel: {heure_actuelle}. OFF.")
            return False

        # Logique basée sur le seuil de CO2
        if co2 > seuil_co2_max:
            return True
        else:
            # Pas d'hystérésis explicite pour la ventilation dans le code original.
            # On pourrait en ajouter un si besoin (ex: seuil_co2_min pour éteindre)
            return False 

    def _control_hardware(self):
        """
        Active ou désactive la ventilation via l'interface matérielle.
        """
        if self.current_state:
            self.hardware.activer_ventilation()
        else:
            self.hardware.desactiver_ventilation()
    
    def update_state(self, current_sensor_data: dict) -> bool:
        """
        Met à jour l'état de la ventilation et contrôle le matériel.
        """
        state_changed = super().update_state(current_sensor_data)
        if state_changed:
            self._control_hardware()
            logging.info(f"Ventilation: état changé. Manuel: {self.is_manual_mode}, Actif: {self.current_state}, CO2: {current_sensor_data.get('co2')}")
        return state_changed

