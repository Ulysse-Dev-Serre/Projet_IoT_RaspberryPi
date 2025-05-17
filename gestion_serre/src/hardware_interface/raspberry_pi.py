# src/hardware_interface/raspberry_pi.py
from .base_hardware import BaseHardware
import time
import logging

# Essayer d'importer les bibliothèques spécifiques au Raspberry Pi
try:
    import lgpio
    import board # Pour Adafruit CircuitPython
    import busio # Pour I2C
    import adafruit_scd30
    RASPBERRY_PI_LIBS_AVAILABLE = True
except ImportError as e:
    # Ce logger ne sera pas configuré par main.py si l'import échoue avant la config du logging
    print(f"AVERTISSEMENT: Bibliothèques Raspberry Pi non trouvées ({e}). RaspberryPiHardware ne fonctionnera pas correctement.")
    RASPBERRY_PI_LIBS_AVAILABLE = False
    # Définir des stubs pour que le reste du fichier ne plante pas à l'import si les libs sont manquantes
    class lgpio: pass
    class board: pass
    class busio: pass
    class adafruit_scd30: pass


# Configuration des broches GPIO
LEDS_PIN = 27
VENTILATION_PIN = 22
FAN_HUMIDI_PIN = 26
BRUMISATEUR_PIN = 13

class RaspberryPiHardware(BaseHardware):
    def __init__(self):
        super().__init__()
        # Obtenir un logger spécifique pour cette classe
        # Note: Le logging doit être configuré par le point d'entrée de l'application (main.py ou app.py)
        self.logger = logging.getLogger(__name__) # ex: src.hardware_interface.raspberry_pi

        if not RASPBERRY_PI_LIBS_AVAILABLE:
            self.logger.error("Impossible d'initialiser RaspberryPiHardware car les bibliothèques requises sont manquantes.")
            self.h = None
            self.scd = None
            return

        try:
            self.h = lgpio.gpiochip_open(0)
            self.logger.info("GPIO chip ouvert.")

            self.i2c = busio.I2C(board.SCL, board.SDA)
            self.logger.info("Bus I2C initialisé.")
            
            self.scd = adafruit_scd30.SCD30(self.i2c)
            self.logger.info("Capteur SCD30 contacté. Attente pour stabilisation...")
            time.sleep(2) # Délai augmenté pour la stabilisation initiale du SCD30

            # Tentative de lecture initiale pour "réveiller" ou vérifier le capteur
            try:
                if self.scd.data_available: # Vérifier si des données sont prêtes
                    self.logger.info(f"SCD30 prêt. Température initiale lue: {self.scd.temperature}°C")
                else:
                    self.logger.info("SCD30: Données non disponibles immédiatement après initialisation, c'est normal.")
            except Exception as e_init_read:
                self.logger.warning(f"SCD30: Problème lors de la lecture de vérification initiale: {e_init_read}")

            lgpio.gpio_claim_output(self.h, LEDS_PIN)
            lgpio.gpio_claim_output(self.h, VENTILATION_PIN)
            lgpio.gpio_claim_output(self.h, FAN_HUMIDI_PIN)
            lgpio.gpio_claim_output(self.h, BRUMISATEUR_PIN)
            self.logger.info("Broches GPIO réclamées en sortie.")

            lgpio.gpio_write(self.h, LEDS_PIN, 1)
            lgpio.gpio_write(self.h, VENTILATION_PIN, 1)
            lgpio.gpio_write(self.h, FAN_HUMIDI_PIN, 1)
            lgpio.gpio_write(self.h, BRUMISATEUR_PIN, 1)
            self.logger.info("Toutes les sorties GPIO initialisées à OFF.")
            
            self.logger.info("RaspberryPiHardware initialisé avec succès.")

        except Exception as e:
            self.logger.error(f"Erreur majeure lors de l'initialisation de RaspberryPiHardware: {e}", exc_info=True)
            self.h = None 
            self.scd = None
            # Il est important de propager l'erreur ou d'avoir un état clair d'échec
            # raise RuntimeError(f"Échec de l'initialisation du matériel RPi: {e}") from e

    def lire_capteur(self) -> tuple[float | None, float | None, float | None]:
        if not self.scd or not self.h: # Vérifier si l'initialisation a réussi
            self.logger.error("SCD30 ou GPIO non initialisé. Impossible de lire les capteurs.")
            return None, None, None

        max_essais = 3
        for essai in range(1, max_essais + 1):
            try:
                # Attendre que les données soient disponibles est crucial pour le SCD30
                if not self.scd.data_available:
                    self.logger.debug(f"SCD30: Données non disponibles (essai {essai}/{max_essais}). Attente de 2s...")
                    time.sleep(2) # Attendre que le capteur ait de nouvelles données
                    if not self.scd.data_available:
                        self.logger.warning(f"SCD30: Données toujours non disponibles après attente (essai {essai}/{max_essais}).")
                        if essai == max_essais: # Si c'est le dernier essai et toujours pas de données
                             self.logger.error("SCD30: Échec final, données non disponibles.")
                             return None, None, None
                        continue # Passer à l'essai suivant

                # Si les données sont disponibles, tenter de les lire
                temperature = self.scd.temperature
                humidite = self.scd.relative_humidity
                co2 = self.scd.CO2
                
                # Vérification de la validité (l'humidité est un bon indicateur)
                if humidite is not None and (0 <= humidite <= 100):
                    self.logger.debug(f"Capteurs lus (essai {essai}): T={temperature:.1f}°C, H={humidite:.1f}%, CO2={co2:.0f}ppm")
                    return temperature, humidite, co2
                else:
                    self.logger.warning(f"Lecture d'humidité invalide (None ou hors plage): {humidite} (essai {essai}/{max_essais})")
            
            except RuntimeError as e: # La bibliothèque Adafruit lève souvent RuntimeError pour les erreurs CRC/I2C
                self.logger.error(f"SCD30: Erreur RuntimeError lors de la lecture (essai {essai}/{max_essais}): {e}")
                if "CRC" in str(e):
                    self.logger.warning("SCD30: Erreur CRC détectée. Problème de communication I2C probable.")
            except Exception as e: # Autres exceptions
                self.logger.error(f"SCD30: Erreur inattendue lors de la lecture (essai {essai}/{max_essais}): {e}", exc_info=True)
            
            if essai < max_essais:
                time.sleep(1) # Petite pause avant le prochain essai général

        self.logger.error("Échec de la lecture des capteurs SCD30 après plusieurs tentatives.")
        return None, None, None

    def activer_leds(self):
        if self.h:
            lgpio.gpio_write(self.h, LEDS_PIN, 0)
            self.logger.info("LEDs activées (GPIO)")
        else:
            self.logger.warning("Tentative d'activer LEDs mais GPIO non initialisé.")

    def desactiver_leds(self):
        if self.h:
            lgpio.gpio_write(self.h, LEDS_PIN, 1)
            self.logger.info("LEDs désactivées (GPIO)")
        else:
            self.logger.warning("Tentative de désactiver LEDs mais GPIO non initialisé.")

    def activer_humidificateur(self):
        if self.h:
            lgpio.gpio_write(self.h, FAN_HUMIDI_PIN, 0)
            lgpio.gpio_write(self.h, BRUMISATEUR_PIN, 0)
            self.logger.info("Humidificateur activé (ventilateur + brumisateur GPIO)")
        else:
            self.logger.warning("Tentative d'activer humidificateur mais GPIO non initialisé.")

    def desactiver_humidificateur(self):
        if self.h:
            lgpio.gpio_write(self.h, FAN_HUMIDI_PIN, 1)
            lgpio.gpio_write(self.h, BRUMISATEUR_PIN, 1)
            self.logger.info("Humidificateur désactivé (GPIO)")
        else:
            self.logger.warning("Tentative de désactiver humidificateur mais GPIO non initialisé.")

    def activer_ventilation(self):
        if self.h:
            lgpio.gpio_write(self.h, VENTILATION_PIN, 0)
            self.logger.info("Ventilation activée (GPIO)")
        else:
            self.logger.warning("Tentative d'activer ventilation mais GPIO non initialisé.")

    def desactiver_ventilation(self):
        if self.h:
            lgpio.gpio_write(self.h, VENTILATION_PIN, 1)
            self.logger.info("Ventilation désactivée (GPIO)")
        else:
            self.logger.warning("Tentative de désactiver ventilation mais GPIO non initialisé.")

    def cleanup(self):
        if self.h:
            self.logger.info("Nettoyage des ressources RaspberryPiHardware...")
            self.desactiver_humidificateur()
            self.desactiver_ventilation()
            self.desactiver_leds()
            
            lgpio.gpiochip_close(self.h)
            self.h = None 
            self.logger.info("GPIO chip fermé.")
        else:
            self.logger.info("Cleanup appelé, mais GPIO non initialisé ou déjà fermé.")
        
        # La fermeture explicite de i2c n'est généralement pas nécessaire avec busio/Blinka
        # car elle est gérée à la fin du script ou par le garbage collector.
        # if hasattr(self, 'i2c') and self.i2c:
        #     try:
        #         self.i2c.deinit()
        #         self.logger.info("Bus I2C désinitialisé.")
        #     except Exception as e:
        #         self.logger.warning(f"Erreur lors de la désinitialisation I2C: {e}")
        self.logger.info("Ressources RaspberryPiHardware nettoyées.")


