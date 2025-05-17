# src/hardware_interface/base_hardware.py
from abc import ABC, abstractmethod

class BaseHardware(ABC):
    """
    Classe de base abstraite pour l'interface matérielle de la serre.
    Définit les méthodes que toutes les implémentations matérielles (réelles ou mock)
    doivent fournir.
    """

    def __init__(self):
        """Initialise l'interface matérielle."""
        pass

    @abstractmethod
    def lire_capteur(self) -> tuple[float | None, float | None, float | None]:
        """
        Lit les données des capteurs.

        Returns:
            tuple[float | None, float | None, float | None]: Un tuple contenant
            la température (°C), l'humidité relative (%), et le niveau de CO2 (ppm).
            Retourne None pour une valeur si la lecture échoue.
        """
        pass

    @abstractmethod
    def activer_leds(self):
        """Active le système d'éclairage (LEDs)."""
        pass

    @abstractmethod
    def desactiver_leds(self):
        """Désactive le système d'éclairage (LEDs)."""
        pass

    @abstractmethod
    def activer_humidificateur(self):
        """Active l'humidificateur (ventilateur et brumisateur)."""
        pass

    @abstractmethod
    def desactiver_humidificateur(self):
        """Désactive l'humidificateur."""
        pass

    @abstractmethod
    def activer_ventilation(self):
        """Active le système de ventilation."""
        pass

    @abstractmethod
    def desactiver_ventilation(self):
        """Désactive le système de ventilation."""
        pass

    @abstractmethod
    def cleanup(self):
        """
        Nettoie et libère les ressources matérielles utilisées (ex: broches GPIO).
        Appelée lors de l'arrêt de l'application.
        """
        pass
