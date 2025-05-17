from logic_hardware.serre_logic import SerreController  # Importer la classe
from logic_hardware import hardware
import time
from datetime import datetime
import threading

#======= Test Ventilation =================
def test_efficacite_ventilation(controller):
    """Teste l'efficacité de la ventilation en mesurant le CO2 toutes les minutes."""
    print("Test de l'efficacité de la ventilation démarré...")
    
    # Désactiver tout au début
    hardware.desactiver_humidificateur()
    hardware.desactiver_ventilation()

    # Durée du test et intervalle
    DUREE_TEST_MINUTES = 10
    INTERVALLE_AFFICHAGE_SECONDES = 60

    # Phase 1 : Mesure initiale sans ventilation (2 minutes)
    print("\nMesure initiale du CO2 (ventilation désactivée) pendant 2 minutes...")
    for i in range(2):
        controller.read_sensors()
        if controller.co2 is not None:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] CO2 = {controller.co2:.1f} ppm (ventilation désactivée)")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Erreur de lecture du capteur CO2")
        time.sleep(INTERVALLE_AFFICHAGE_SECONDES)

    # Phase 2 : Activer la ventilation et mesurer
    print("\nActivation de la ventilation, mesure du CO2 pendant", DUREE_TEST_MINUTES - 2, "minutes...")
    hardware.activer_ventilation()
    for i in range(DUREE_TEST_MINUTES - 2):
        controller.read_sensors()
        if controller.co2 is not None:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] CO2 = {controller.co2:.1f} ppm (ventilation active)")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Erreur de lecture du capteur CO2")
        time.sleep(INTERVALLE_AFFICHAGE_SECONDES)

    # Fin du test
    hardware.desactiver_ventilation()
    hardware.cleanup()
    print("\nTest de l'efficacité de la ventilation terminé.")




def main():
    print("Démarrage de terminal.py - Mode automatique")
    hardware.desactiver_humidificateur()
    hardware.desactiver_ventilation()

    # Créer une instance du contrôleur
    controller = SerreController(60)  # Intervalle fixé à 60s
    controller.brumisateur_off_time = time.time()  
    controller.ventilation_off_time = time.time()
    time.sleep(2)  # Délai initial

    # Lancer la logique dans un thread séparé
    logic_thread = threading.Thread(target=controller.run, daemon=True)
    logic_thread.start()

    last_status = None  # Pour éviter les répétitions inutiles

    try:
        while True:
            status = controller.get_status()  # Appeler sur l’instance
            temperature = status["temperature"]
            humidite = status["humidite"]
            co2 = status["co2"]
            humidificateur_actif = status["humidificateur_actif"]
            ventilation_actif = status["ventilation_actif"]
            

            # Afficher uniquement si les données ont changé ou s’il y a une transition
            current_status = (humidite, temperature, co2, humidificateur_actif, ventilation_actif)
            if (humidite is not None or co2 is not None) and (last_status != current_status or status["transition"] is not None):
                message = (
                    f"Humidité={humidite:.1f}%, Température={temperature:.1f}°C, "
                    f"CO2={co2:.1f}ppm [{datetime.now().strftime('%H:%M:%S')}] "
                    f"humidificateur {'actif' if humidificateur_actif else 'désactivé'} - "
                    f"ventilation {'actif' if ventilation_actif else 'désactivée'}"
                )
                print(message)
                last_status = current_status
            
                

            # Affichage des transitions

            if status["transition"] is not None:
                transition = status["transition"]

                if transition["type"] == "humidificateur_actif":  # Transition humidificateur ON
                    transition_message = (
                        f"Humidité={transition['humidite']:.1f}%, Température={transition['temperature']:.1f}°C, "
                        f"CO2={transition['co2']:.1f}ppm [{transition['timestamp']}] "
                        f"humidificateur actif et a été désactivé {transition['duree_eteint_min']:.0f} minutes"
                    )
                elif transition["type"] == "humidificateur_desactiver":  # Transition humidificateur OFF
                    transition_message = (
                        f"Humidité={transition['humidite']:.1f}%, Température={transition['temperature']:.1f}°C, "
                        f"CO2={transition['co2']:.1f}ppm [{transition['timestamp']}] "
                        f"humidificateur désactivé et a fonctionné {transition['duree_allume_min']:.0f} minutes"
                    )
                    #-----------------------------------------------------------------------------------------------
                elif transition["type"] == "ventilation_actif":  # Transition ventilation ON
                    transition_message = (
                        f"Humidité={transition['humidite']:.1f}%, Température={transition['temperature']:.1f}°C, "
                        f"CO2={transition['co2']:.1f}ppm [{transition['timestamp']}] "
                        f"ventilation activée et a été désactivée {transition['duree_eteint_min']:.0f} minutes"
                    )
                elif transition["type"] == "ventilation_desactiver":  # Transition ventilation OFF
                    transition_message = (
                        f"Humidité={transition['humidite']:.1f}%, Température={transition['temperature']:.1f}°C, "
                        f"CO2={transition['co2']:.1f}ppm [{transition['timestamp']}] "
                        f"ventilation désactivée et a fonctionné {transition['duree_allume_min']:.0f} minutes"
                    )
                print(transition_message)

            time.sleep(1)  # Petite pause pour éviter une boucle trop rapide


    except KeyboardInterrupt:
        print("\nInterruption par l’utilisateur.")
        hardware.cleanup()
       


if __name__ == "__main__":
    main()