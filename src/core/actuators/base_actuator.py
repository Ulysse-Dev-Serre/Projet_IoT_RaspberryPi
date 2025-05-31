# src/core/actuators/base_actuator.py
from abc import ABC, abstractmethod
import time

class BaseActuator(ABC):
    """
    Classe de base abstraite pour tous les contrôleurs d'actionneurs de la serre.
    """
    def __init__(self, hardware_interface, device_name: str):
        self.hardware = hardware_interface
        self.device_name = device_name
        self.is_manual_mode = False
        self.manual_state = False  # État souhaité en mode manuel (True pour ON, False pour OFF)
        self.current_state = False # État actuel de l'appareil (True pour ON, False pour OFF)
        self.last_state_change_time = time.time()
        self.on_time_start = None
        self.off_time_start = None
        self.last_transition_info = None

    @abstractmethod
    def _get_desired_automatic_state(self, current_sensor_data: dict) -> bool:
        """
        Détermine l'état souhaité de l'actionneur en mode automatique
        basé sur les données des capteurs et la configuration.
        Doit être implémenté par les classes filles.
        """
        pass

    def update_state(self, current_sensor_data: dict) -> bool:
        """
        Met à jour l'état de l'actionneur (ON/OFF) en fonction du mode (manuel/auto)
        et des conditions actuelles.
        Retourne True si l'état a changé, False sinon.
        """
        previous_state = self.current_state
        desired_state = False

        if self.is_manual_mode:
            desired_state = self.manual_state
        else:
            desired_state = self._get_desired_automatic_state(current_sensor_data)

        state_changed = False
        if desired_state != self.current_state:
            self.current_state = desired_state
            state_changed = True
            self.last_state_change_time = time.time()
            # Logique de transition spécifique à l'appareil (gérée dans les classes filles si besoin)
            # self._handle_state_transition(previous_state, desired_state, current_sensor_data)
            
            # Mise à jour des temps ON/OFF
            if self.current_state: # Si l'appareil s'allume
                self.on_time_start = time.time()
                if self.off_time_start:
                    duration_off = self.on_time_start - self.off_time_start
                    self.last_transition_info = {
                        "type": f"{self.device_name}_on",
                        "duration_off_seconds": round(duration_off, 1),
                        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                self.off_time_start = None
            else: # Si l'appareil s'éteint
                self.off_time_start = time.time()
                if self.on_time_start:
                    duration_on = self.off_time_start - self.on_time_start
                    self.last_transition_info = {
                        "type": f"{self.device_name}_off",
                        "duration_on_seconds": round(duration_on, 1),
                        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                self.on_time_start = None
        else:
            # Réinitialiser last_transition_info si aucun changement d'état
            # pour ne pas le renvoyer plusieurs fois
            self.last_transition_info = None


        # Commande matérielle (sera plus spécifique dans les classes filles)
        # self._control_hardware(self.current_state)
        return state_changed


    def set_manual_mode(self, manual_mode_active: bool, desired_state_if_manual: bool = False):
        """
        Active ou désactive le mode manuel pour cet actionneur.
        """
        self.is_manual_mode = manual_mode_active
        if self.is_manual_mode:
            self.manual_state = desired_state_if_manual
        # La mise à jour de l'état réel se fera lors du prochain appel à update_state()

    def get_status(self) -> dict:
        """
        Retourne l'état actuel de l'actionneur et les informations de durée.
        """
        on_duration = 0
        off_duration = 0

        if self.current_state and self.on_time_start: # Actuellement ON
            on_duration = time.time() - self.on_time_start
        elif not self.current_state and self.off_time_start: # Actuellement OFF
            off_duration = time.time() - self.off_time_start
        
        status = {
            "is_active": self.current_state,
            "manual_mode": self.is_manual_mode,
            "on_duration_seconds": round(on_duration, 1),
            "off_duration_seconds": round(off_duration, 1),
        }
        # Inclure et réinitialiser les informations de transition si elles existent
        if self.last_transition_info:
            status["last_transition"] = self.last_transition_info
            # self.last_transition_info = None # Déplacé dans update_state pour s'assurer qu'il est consommé
        return status

    def get_last_transition_info(self):
        """ Récupère la dernière information de transition et la réinitialise. """
        info = self.last_transition_info
        self.last_transition_info = None # Réinitialise après récupération
        return info

    @abstractmethod
    def _control_hardware(self):
        """
        Méthode spécifique pour interagir avec le matériel.
        Doit être implémenté par les classes filles.
        """
        pass
