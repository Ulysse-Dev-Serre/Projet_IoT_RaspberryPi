# src/hardware_interface/mock_hardware.py
from .base_hardware import BaseHardware
import random
import time
import logging

class MockHardware(BaseHardware):
    """
    Implémentation simulée (mock) de l'interface matérielle.
    Utilisée pour les tests et le développement sur des machines
    qui n'ont pas le matériel réel (ex: Windows, macOS).
    """
    def __init__(self):
        super().__init__()
        self._leds_on = False
        self._humidifier_on = False
        self._ventilation_on = False
        
        # Simuler des valeurs de capteurs initiales
        self._temperature = random.uniform(18, 22)
        self._humidite = random.uniform(65, 75)
        self._co2 = random.uniform(400, 800)
        
        logging.info("MockHardware initialisé.")

    def lire_capteur(self) -> tuple[float | None, float | None, float | None]:
        # Simuler des variations légères des capteurs à chaque lecture
        self._temperature += random.uniform(-0.2, 0.2)
        self._humidite += random.uniform(-1, 1)
        self._co2 += random.uniform(-20, 20)

        # S'assurer que les valeurs restent dans des plages réalistes
        self._temperature = max(10, min(self._temperature, 35)) # Entre 10°C et 35°C
        self._humidite = max(30, min(self._humidite, 99))    # Entre 30% et 99%
        self._co2 = max(300, min(self._co2, 3000))          # Entre 300ppm et 3000ppm
        
        # Simuler un échec de lecture occasionnel (1 fois sur 20)
        # if random.randint(1, 20) == 1:
        #     logging.warning("MOCK: Échec simulé de lecture des capteurs.")
        #     return None, None, None
            
        logging.debug(f"MOCK Capteurs lus: T={self._temperature:.1f}°C, H={self._humidite:.1f}%, CO2={self._co2:.0f}ppm")
        return self._temperature, self._humidite, self._co2

    def activer_leds(self):
        if not self._leds_on:
            self._leds_on = True
            logging.info("MOCK: LEDs activées.")

    def desactiver_leds(self):
        if self._leds_on:
            self._leds_on = False
            logging.info("MOCK: LEDs désactivées.")

    def activer_humidificateur(self):
        if not self._humidifier_on:
            self._humidifier_on = True
            # En mode mock, l'humidité devrait augmenter quand l'humidificateur est actif
            self._humidite += random.uniform(2, 5) # Augmentation plus marquée
            self._humidite = min(self._humidite, 99)
            logging.info("MOCK: Humidificateur activé.")

    def desactiver_humidificateur(self):
        if self._humidifier_on:
            self._humidifier_on = False
            logging.info("MOCK: Humidificateur désactivé.")

    def activer_ventilation(self):
        if not self._ventilation_on:
            self._ventilation_on = True
            # En mode mock, le CO2 devrait diminuer et l'humidité pourrait légèrement baisser
            self._co2 -= random.uniform(50, 150) # Baisse plus marquée
            self._co2 = max(300, self._co2)
            self._humidite -= random.uniform(0.5, 1.5)
            self._humidite = max(30, self._humidite)
            logging.info("MOCK: Ventilation activée.")

    def desactiver_ventilation(self):
        if self._ventilation_on:
            self._ventilation_on = False
            logging.info("MOCK: Ventilation désactivée.")

    def cleanup(self):
        logging.info("MOCK: Nettoyage des ressources matérielles simulées effectué.")
        # Rien de spécifique à faire pour le mock, mais la méthode doit exister.
        pass
