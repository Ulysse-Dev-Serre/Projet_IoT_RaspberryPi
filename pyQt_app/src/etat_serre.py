# import logging pour la gestion d'erreur eventuellemnt

class EtatSerre:
    def __init__(self):
        # Etat initiaux des appareils
        self._leds_on = False
        self._humidificateur_on = False
        self._ventilation_on = False
        self._mode_automatique_global_active = True
        self._etat_urgence = False 

        # Valeur des capteur (placeholders)
        self._current_temp = "--"
        self._current_humidity = "--"
        self._current_co2 = "--"

    # --- Getters 
    def get_leds_etat(self) -> bool:
        return self._leds_on
    def get_humidificateur_etat(self) -> bool:
        return self._humidificateur_on
    def get_ventilation_etat(self) -> bool:
        return self._ventilation_on
    def get_mode_automatique(self) -> bool:
        return self._mode_automatique_global_active
    def get_etat_urgence(self) -> bool:
        return self._etat_urgence
    
    def get_current_temp(self) -> str:
        return self._current_temp
    def get_current_humidity(self) -> str:
        return self._current_humidity
    def get_current_co2(self) -> str:
        return self._current_co2
    
    # setter
    def set_current_temp(self, nouvelle_temp: str):
        self._current_temp = nouvelle_temp
    def set_current_humidity(self, nouvelle_humidite: str):
        self._current_humidity = nouvelle_humidite
    def set_current_co2(self, nouveau_co2: str):
        self._current_co2 = nouveau_co2

    # --- Méthode interne pour gérer la sortie de l'état d'urgence ---
    def _verifier_et_lever_urgence_si_necessaire(self):
        if self._etat_urgence:
            self._etat_urgence = False

    
    def set_leds_etat(self, nouvel_etat_on: bool):
        if nouvel_etat_on: # Si on essaie d'allumer
            self._verifier_et_lever_urgence_si_necessaire() # Lève l'urgence si elle était active
        self._leds_on = nouvel_etat_on
        # TODO: Appel API pour LEDs et tou les autre avec self._leds_on

    def set_humidificateur_etat(self, nouvel_etat_on: bool):
        if nouvel_etat_on: 
            self._verifier_et_lever_urgence_si_necessaire()
        self._humidificateur_on = nouvel_etat_on

    def set_ventilation_etat(self, nouvel_etat_on: bool):
        if nouvel_etat_on: 
            self._verifier_et_lever_urgence_si_necessaire()
        self._ventilation_on = nouvel_etat_on

    def set_mode_automatique(self, nouvel_etat_actif: bool):
        if nouvel_etat_actif: 
            self._verifier_et_lever_urgence_si_necessaire()
        self._mode_automatique_global_active = nouvel_etat_actif
        

    # --- Setter pour l'état d'urgence / "Tout Fermer" ---
    def set_etat_urgence(self, activer_urgence: bool):
        # Si on demande d'activer l'urgence alors qu'elle l'est déjà, ou de la désactiver alors qu'elle l'est déjà
        if self._etat_urgence == activer_urgence:
            return

        self._etat_urgence = activer_urgence
        
        if self._etat_urgence: 
            print("Modèle: État d'urgence (Tout Fermer) ACTIVÉ.")
            
            # Forcer l'arrêt de tous les systèmes.
            if self._leds_on: self.set_leds_etat(False)
            if self._humidificateur_on: self.set_humidificateur_etat(False)
            if self._ventilation_on: self.set_ventilation_etat(False)
            if self._mode_automatique_global_active: self.set_mode_automatique(False)
            print("Modèle: Tous les systèmes ont reçu l'ordre de s'arrêter.")
        else:
            # Ce bloc est maintenant principalement atteint si on appelle set_etat_urgence(False) explicitement
            print("Modèle: État d'urgence DÉSACTIVÉ.")

    