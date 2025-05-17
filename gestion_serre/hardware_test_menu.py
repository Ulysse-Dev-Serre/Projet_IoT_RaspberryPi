# hardware_test_menu.py
import sys
import os
import time
import logging

# Ajouter le répertoire racine du projet au PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    # On importe directement l'implémentation RaspberryPiHardware
    # Ce script est destiné à être exécuté UNIQUEMENT sur le Raspberry Pi.
    from src.hardware_interface.raspberry_pi import RaspberryPiHardware, RASPBERRY_PI_LIBS_AVAILABLE
    # import config # Pas strictement nécessaire ici car on force RaspberryPiHardware
except ImportError as e:
    print(f"ERREUR: Impossible d'importer les modules nécessaires: {e}")
    print("Assurez-vous que ce script est dans le répertoire racine du projet et que la structure est correcte.")
    sys.exit(1)
except Exception as e:
    print(f"ERREUR CRITIQUE lors de l'initialisation des imports: {e}")
    sys.exit(1)

# Configuration simple du logging pour ce script de test
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def display_menu():
    """Affiche le menu des options de test."""
    print("\n--- Menu de Test Matériel pour Serre (Raspberry Pi) ---")
    print("Capteur SCD30:")
    print("  1. Lire les données du capteur (Température, Humidité, CO2)")
    print("LEDs:")
    print("  2. Allumer les LEDs")
    print("  3. Éteindre les LEDs")
    print("Humidificateur:")
    print("  4. Activer l'humidificateur (ventilateur + brumisateur)")
    print("  5. Désactiver l'humidificateur")
    print("Ventilation:")
    print("  6. Activer la ventilation")
    print("  7. Désactiver la ventilation")
    print("Général:")
    print("  8. Tout éteindre et nettoyer les GPIOs")
    print("  0. Quitter")
    print("-------------------------------------------------------")

def main():
    logger.info("Démarrage du script de test matériel interactif pour Raspberry Pi.")
    
    if not RASPBERRY_PI_LIBS_AVAILABLE:
        logger.error("Les bibliothèques Raspberry Pi ne sont pas disponibles. Ce script ne peut pas fonctionner.")
        print("\nERREUR: Ce script nécessite les bibliothèques spécifiques au Raspberry Pi (lgpio, Adafruit-Blinka, etc.).")
        print("Veuillez l'exécuter sur un Raspberry Pi où ces bibliothèques sont installées.")
        return

    try:
        hardware = RaspberryPiHardware()
        if hardware.h is None or (hasattr(hardware, 'scd') and hardware.scd is None and RASPBERRY_PI_LIBS_AVAILABLE): # Vérifier si l'initialisation a échoué
             logger.error("L'initialisation de RaspberryPiHardware semble avoir échoué (h ou scd est None).")
             print("\nERREUR: L'initialisation du matériel a échoué. Vérifiez les logs précédents.")
             return
        logger.info("Interface RaspberryPiHardware initialisée.")
    except Exception as e:
        logger.error(f"Échec de l'initialisation de RaspberryPiHardware: {e}", exc_info=True)
        print(f"\nERREUR: Impossible d'initialiser le matériel Raspberry Pi: {e}")
        print("Vérifiez les connexions matérielles et les permissions GPIO.")
        return

    try:
        while True:
            display_menu()
            choice = input("Votre choix: ")

            if choice == '1':
                logger.info("Test: Lecture du capteur SCD30...")
                temp, hum, co2 = hardware.lire_capteur()
                if temp is not None and hum is not None and co2 is not None:
                    print(f"  => Température: {temp:.2f}°C, Humidité: {hum:.2f}%, CO2: {co2:.0f} ppm")
                else:
                    print("  => Échec de la lecture des données du capteur.")
            
            elif choice == '2':
                logger.info("Test: Allumage des LEDs...")
                hardware.activer_leds()
                print("  => Commande d'allumage des LEDs envoyée.")
            
            elif choice == '3':
                logger.info("Test: Extinction des LEDs...")
                hardware.desactiver_leds()
                print("  => Commande d'extinction des LEDs envoyée.")

            elif choice == '4':
                logger.info("Test: Activation de l'humidificateur...")
                hardware.activer_humidificateur()
                print("  => Commande d'activation de l'humidificateur envoyée.")

            elif choice == '5':
                logger.info("Test: Désactivation de l'humidificateur...")
                hardware.desactiver_humidificateur()
                print("  => Commande de désactivation de l'humidificateur envoyée.")

            elif choice == '6':
                logger.info("Test: Activation de la ventilation...")
                hardware.activer_ventilation()
                print("  => Commande d'activation de la ventilation envoyée.")

            elif choice == '7':
                logger.info("Test: Désactivation de la ventilation...")
                hardware.desactiver_ventilation()
                print("  => Commande de désactivation de la ventilation envoyée.")
            
            elif choice == '8':
                logger.info("Test: Tout éteindre et nettoyer...")
                hardware.cleanup() 
                print("  => Commande de nettoyage des GPIOs envoyée. Tous les appareils devraient être éteints.")
                print("     Pour de nouveaux tests, veuillez redémarrer le script car le GPIO chip est fermé.")
                # Après cleanup, l'objet hardware n'est plus utilisable sans réinitialisation.
                break # Sortir de la boucle après cleanup.
            
            elif choice == '0':
                logger.info("Arrêt du script de test matériel.")
                break
            
            else:
                print("  => Choix invalide. Veuillez réessayer.")
            
            time.sleep(0.1) 

    except KeyboardInterrupt:
        logger.info("Interruption par l'utilisateur (Ctrl+C).")
    except Exception as e:
        logger.error(f"Une erreur inattendue s'est produite: {e}", exc_info=True)
        print(f"\nERREUR INATTENDUE: {e}")
    finally:
        logger.info("Nettoyage final avant de quitter...")
        # S'assurer que cleanup est appelé si l'objet hardware a été initialisé et n'a pas déjà été nettoyé
        if 'hardware' in locals() and hardware and hasattr(hardware, 'h') and hardware.h is not None:
            hardware.cleanup()
            print("Nettoyage des GPIOs effectué.")
        logger.info("Script de test matériel terminé.")

if __name__ == "__main__":
    main()
