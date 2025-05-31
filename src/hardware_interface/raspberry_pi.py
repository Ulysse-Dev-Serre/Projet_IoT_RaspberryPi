# src/hardware_interface/raspberry_pi.py
from .base_hardware import BaseHardware
import time
import logging
from src import config # Importer le module config depuis src

# Essayer d'importer les bibliothèques spécifiques au Raspberry Pi
try:
    import lgpio
    import board # Pour Adafruit CircuitPython
    import busio # Pour I2C
    import adafruit_scd30
    RASPBERRY_PI_LIBS_AVAILABLE = True
except ImportError as e:
    # Ce logger ne sera pas configuré par main.py si l'import échoue avant la config du logging
    # Utiliser print pour s'assurer que le message est visible en cas d'échec précoce.
    print(f"AVERTISSEMENT (raspberry_pi.py): Bibliothèques Raspberry Pi non trouvées ({e}). RaspberryPiHardware ne fonctionnera pas correctement.")
    RASPBERRY_PI_LIBS_AVAILABLE = False
    # Définir des stubs pour que le reste du fichier ne plante pas à l'import si les libs sont manquantes
    # et pour permettre l'exécution en mode mock sans ces bibliothèques.
    class lgpio: pass
    class board: pass
    class busio: pass
    class adafruit_scd30: pass

# Les définitions de broches GPIO en dur sont maintenant SUPPRIMÉES d'ici.
# Elles sont récupérées depuis src/config.py

class RaspberryPiHardware(BaseHardware):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__) # ex: src.hardware_interface.raspberry_pi

        if not RASPBERRY_PI_LIBS_AVAILABLE:
            self.logger.error("Impossible d'initialiser RaspberryPiHardware car les bibliothèques requises sont manquantes.")
            self.h = None # Handle pour lgpio
            self.scd = None # Instance du capteur SCD30
            return

        try:
            # Initialisation du GPIO via lgpio
            self.h = lgpio.gpiochip_open(0)
            self.logger.info("GPIO chip (lgpio) ouvert.")

            # Initialisation du bus I2C et du capteur SCD30
            self.i2c = busio.I2C(board.SCL, board.SDA) # Utilise les pins SCL/SDA par défaut de board
            self.logger.info("Bus I2C initialisé.")
            
            self.scd = adafruit_scd30.SCD30(self.i2c)
            self.logger.info("Capteur SCD30 contacté. Attente pour stabilisation...")
            time.sleep(2) # Délai pour la stabilisation initiale du SCD30

            try:
                if self.scd.data_available:
                    self.logger.info(f"SCD30 prêt. Température initiale lue: {self.scd.temperature:.1f}°C")
                else:
                    self.logger.info("SCD30: Données non disponibles immédiatement après initialisation.")
            except Exception as e_init_read:
                self.logger.warning(f"SCD30: Problème lors de la lecture de vérification initiale: {e_init_read}")

            # Réclamer les broches GPIO en sortie en utilisant les valeurs de config
            # Note: la valeur 0 pour lgpio.gpio_write signifie ON (typiquement pour un relais actif bas)
            # et 1 signifie OFF. Ajustez si votre logique de relais est inversée.
            lgpio.gpio_claim_output(self.h, config.PIN_LEDS)
            lgpio.gpio_claim_output(self.h, config.VENTILATION_OUTPUT_PIN)
            lgpio.gpio_claim_output(self.h, config.PIN_FAN_HUMIDIFICATEUR)
            lgpio.gpio_claim_output(self.h, config.PIN_BRUMISATEUR)
            self.logger.info("Broches GPIO réclamées en sortie selon la configuration.")

            # Initialiser toutes les sorties à OFF (état logique 1 pour lgpio si relais actif bas)
            lgpio.gpio_write(self.h, config.PIN_LEDS, 1)
            lgpio.gpio_write(self.h, config.VENTILATION_OUTPUT_PIN, 1)
            lgpio.gpio_write(self.h, config.PIN_FAN_HUMIDIFICATEUR, 1)
            lgpio.gpio_write(self.h, config.PIN_BRUMISATEUR, 1)
            self.logger.info("Toutes les sorties GPIO initialisées à OFF (logique 1).")
            
            self.logger.info("RaspberryPiHardware initialisé avec succès.")

        except Exception as e:
            self.logger.error(f"Erreur majeure lors de l'initialisation de RaspberryPiHardware: {e}", exc_info=True)
            if hasattr(self, 'h') and self.h is not None: # Tenter de fermer le chip GPIO si ouvert
                lgpio.gpiochip_close(self.h)
            self.h = None 
            self.scd = None
            # Il est important de propager l'erreur ou d'avoir un état clair d'échec
            # raise RuntimeError(f"Échec de l'initialisation du matériel RPi: {e}") from e

    def lire_capteur(self) -> tuple[float | None, float | None, float | None]:
        if not self.scd or not self.h:
            self.logger.error("SCD30 ou GPIO non initialisé. Impossible de lire les capteurs.")
            return None, None, None

        max_essais = 3
        for essai in range(1, max_essais + 1):
            try:
                if not self.scd.data_available:
                    self.logger.debug(f"SCD30: Données non disponibles (essai {essai}/{max_essais}). Attente de 2s...")
                    time.sleep(2)
                    if not self.scd.data_available:
                        self.logger.warning(f"SCD30: Données toujours non disponibles après attente (essai {essai}/{max_essais}).")
                        if essai == max_essais:
                             self.logger.error("SCD30: Échec final, données non disponibles.")
                             return None, None, None
                        continue

                temperature = self.scd.temperature
                humidite = self.scd.relative_humidity
                co2 = self.scd.CO2
                
                if humidite is not None and (0 <= humidite <= 100) and \
                   temperature is not None and co2 is not None: # Ajout de vérifications pour temp et co2
                    self.logger.debug(f"Capteurs lus (essai {essai}): T={temperature:.1f}°C, H={humidite:.1f}%, CO2={co2:.0f}ppm")
                    return temperature, humidite, co2
                else:
                    self.logger.warning(f"Lecture de capteur invalide ou partielle (essai {essai}/{max_essais}): T={temperature}, H={humidite}, CO2={co2}")
            
            except RuntimeError as e:
                self.logger.error(f"SCD30: Erreur RuntimeError lors de la lecture (essai {essai}/{max_essais}): {e}")
                if "CRC" in str(e):
                    self.logger.warning("SCD30: Erreur CRC détectée. Problème de communication I2C probable.")
            except Exception as e:
                self.logger.error(f"SCD30: Erreur inattendue lors de la lecture (essai {essai}/{max_essais}): {e}", exc_info=True)
            
            if essai < max_essais:
                time.sleep(1)

        self.logger.error("Échec de la lecture des capteurs SCD30 après plusieurs tentatives.")
        return None, None, None

    def _control_gpio(self, pin: int, state: bool, action_name: str):
        """Méthode utilitaire pour contrôler une broche GPIO."""
        if self.h:
            # Convertir l'état booléen (True=ON, False=OFF) en logique lgpio (0=ON, 1=OFF)
            gpio_value = 0 if state else 1
            lgpio.gpio_write(self.h, pin, gpio_value)
            status_text = "activé(e)" if state else "désactivé(e)"
            self.logger.info(f"{action_name} {status_text} (GPIO {pin} mis à {gpio_value})")
        else:
            self.logger.warning(f"Tentative de contrôler {action_name} mais GPIO non initialisé.")

    def activer_leds(self):
        self._control_gpio(config.PIN_LEDS, True, "LEDs")

    def desactiver_leds(self):
        self._control_gpio(config.PIN_LEDS, False, "LEDs")

    def activer_humidificateur(self):
        # L'humidificateur peut impliquer plusieurs broches (ventilateur + brumisateur)
        self._control_gpio(config.PIN_FAN_HUMIDIFICATEUR, True, "Ventilateur humidificateur")
        self._control_gpio(config.PIN_BRUMISATEUR, True, "Brumisateur")
        # Note: Le logger de _control_gpio logguera chaque action séparément.
        # On peut ajouter un log global si nécessaire.
        self.logger.info("Humidificateur (ensemble) activé.")


    def desactiver_humidificateur(self):
        self._control_gpio(config.PIN_FAN_HUMIDIFICATEUR, False, "Ventilateur humidificateur")
        self._control_gpio(config.PIN_BRUMISATEUR, False, "Brumisateur")
        self.logger.info("Humidificateur (ensemble) désactivé.")

    def activer_ventilation(self):
        self._control_gpio(config.VENTILATION_OUTPUT_PIN, True, "Ventilation")

    def desactiver_ventilation(self):
        self._control_gpio(config.VENTILATION_OUTPUT_PIN, False, "Ventilation")

    def cleanup(self):
        if self.h:
            self.logger.info("Nettoyage des ressources RaspberryPiHardware...")
            # Assurer que tous les actuateurs sont désactivés
            self.desactiver_leds()
            self.desactiver_humidificateur()
            self.desactiver_ventilation()
            
            # Libérer les broches (non strictement nécessaire avec gpiochip_close pour les sorties, mais bonne pratique)
            # lgpio.gpio_free(self.h, config.PIN_LEDS)
            # ... (pour les autres pins si claim_output les réserve exclusivement)

            lgpio.gpiochip_close(self.h)
            self.h = None 
            self.logger.info("GPIO chip (lgpio) fermé.")
        else:
            self.logger.info("Cleanup appelé, mais GPIO non initialisé ou déjà fermé.")
        
        # La fermeture/désinitialisation de I2C et SCD30 n'est généralement pas
        # gérée explicitement de cette manière avec Blinka/CircuitPython,
        # mais si des méthodes deinit() existent, elles pourraient être appelées ici.
        self.logger.info("Ressources RaspberryPiHardware nettoyées (ou tentative).")



