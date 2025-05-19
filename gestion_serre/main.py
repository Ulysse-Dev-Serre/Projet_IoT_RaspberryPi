# main.py
import sys
import os
import time
import logging
import logging.handlers # Pour FileHandler
import signal
import threading

# Ajouter le répertoire racine du projet au PYTHONPATH
# pour permettre les imports de modules dans 'src'
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from src.core.serre_logic import SerreController
    from src import config # S'assure que config.py est accessible et chargé
except ImportError as e:
    # Utiliser print ici car le logging n'est peut-être pas encore configuré
    print(f"ERREUR CRITIQUE: Impossible d'importer les modules nécessaires: {e}")
    print("Veuillez vous assurer que la structure de votre projet est correcte et que config.py existe.")
    print(f"PYTHONPATH actuel: {sys.path}")
    sys.exit(1)
except Exception as e:
    print(f"ERREUR CRITIQUE lors de l'initialisation des imports: {e}")
    sys.exit(1)

# --- Configuration centralisée du logging ---
# Cette section est basée sur votre sélection et nos améliorations.
try:
    log_level_str = config.LOG_LEVEL.upper()
    log_level = getattr(logging, log_level_str, logging.INFO) # Default to INFO if invalid
except AttributeError:
    print("AVERTISSEMENT: config.LOG_LEVEL non trouvé, utilisation du niveau INFO par défaut pour le logging.")
    log_level = logging.INFO

log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(threadName)s - %(message)s')

# Récupérer le logger racine pour y attacher les handlers.
# Cela évite les problèmes si basicConfig est appelé plusieurs fois ou par différents modules.
root_logger = logging.getLogger()
root_logger.setLevel(log_level) # Définir le niveau sur le logger racine. Les handlers peuvent avoir des niveaux plus restrictifs.

# Supprimer les handlers existants pour éviter la duplication si le script est rechargé (rare pour main.py mais bonne pratique)
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# Handler pour la console
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
# console_handler.setLevel(log_level) # Optionnel: le handler hérite du niveau du logger racine par défaut
root_logger.addHandler(console_handler)

# Handler pour le fichier
try:
    log_file_path = config.LOG_FILE_PATH

    # --- DÉBUT DE L'AJOUT ---
    # Obtenir le répertoire du fichier journal
    log_directory = os.path.dirname(log_file_path)
    # Si le chemin contient un répertoire (n'est pas juste un nom de fichier)
    # et que ce répertoire n'existe pas, le créer.
    if log_directory and not os.path.exists(log_directory):
        os.makedirs(log_directory)
        print(f"Répertoire de logs créé : {log_directory}")
    # --- FIN DE L'AJOUT ---

    file_handler = logging.FileHandler(log_file_path, mode='a') # 'a' pour append
    file_handler.setFormatter(log_formatter)
    # file_handler.setLevel(log_level) # Optionnel
    root_logger.addHandler(file_handler)
    print(f"Logging configuré. Console: ON, Fichier: '{log_file_path}' (Niveau: {logging.getLevelName(log_level)})")
except AttributeError:
    print("AVERTISSEMENT: config.LOG_FILE_PATH non trouvé. Logging fichier désactivé.")
except Exception as e:
    print(f"AVERTISSEMENT: Impossible de configurer le logging vers le fichier (config.LOG_FILE_PATH='{config.LOG_FILE_PATH if hasattr(config, 'LOG_FILE_PATH') else 'Non défini'}'): {e}")
    # L'application continuera avec le logging console uniquement.

main_logger = logging.getLogger(__name__) # Obtenir un logger spécifique pour ce module (main.py)
# --- Fin de la configuration du logging ---


# Variable globale pour le contrôleur afin qu'il soit accessible par le gestionnaire de signal
serre_controller_instance: SerreController | None = None
controller_thread: threading.Thread | None = None # Pour gérer le thread du contrôleur

def signal_handler(signum, frame):
    """
    Gère les signaux d'arrêt (SIGINT, SIGTERM) pour un arrêt propre.
    """
    signal_name = signal.Signals(signum).name if sys.platform != "win32" else f"Signal {signum}" # Windows ne nomme pas bien les signaux
    main_logger.info(f"Signal {signal_name} reçu. Arrêt en cours...")
    
    # Demander au contrôleur de s'arrêter
    if serre_controller_instance:
        # La méthode shutdown du contrôleur devrait idéalement changer un flag 'self.running = False'
        # pour que sa boucle principale se termine naturellement.
        serre_controller_instance.shutdown() 

    # Attendre que le thread du contrôleur se termine.
    # Le thread du contrôleur devrait appeler serre_controller_instance.shutdown()
    # dans son propre bloc finally s'il se termine par une exception.
    if controller_thread and controller_thread.is_alive():
        main_logger.info("Attente de la fin du thread du SerreController (max 10s)...")
        controller_thread.join(timeout=10) 
        if controller_thread.is_alive():
            main_logger.warning("Le thread du SerreController n'a pas pu être arrêté proprement dans le délai imparti.")
    
    main_logger.info("Application main.py terminée suite au signal.")
    sys.exit(0)

def run_controller():
    """
    Initialise et démarre le SerreController.
    """
    global serre_controller_instance, controller_thread

    main_logger.info("----------------------------------------------------")
    main_logger.info("--- Démarrage du Contrôleur de Serre (Mode CLI) ---")
    main_logger.info("----------------------------------------------------")
    main_logger.info(f"Mode Matériel (HARDWARE_ENV): {config.HARDWARE_ENV}")
    main_logger.info(f"Mode Base de Données (DB_ENV): {config.DB_ENV}")
    main_logger.info(f"Niveau de Log configuré: {logging.getLevelName(root_logger.getEffectiveLevel())}")
    main_logger.info(f"Logs écrits dans le fichier: {config.LOG_FILE_PATH if hasattr(config, 'LOG_FILE_PATH') and any(isinstance(h, logging.FileHandler) for h in root_logger.handlers) else 'Non configuré ou erreur'}")
    main_logger.info("Appuyez sur Ctrl+C pour arrêter.")

    try:
        serre_controller_instance = SerreController()
    except Exception as e:
        main_logger.critical(f"Échec de l'initialisation de SerreController: {e}", exc_info=True)
        sys.exit(1)

    # Démarrer la boucle principale du contrôleur dans son propre thread
    controller_thread = threading.Thread(target=serre_controller_instance.run, name="SerreControllerThread", daemon=True)
    controller_thread.start()

    # Boucle principale du script main.py pour garder le script actif et réceptif aux signaux
    while controller_thread.is_alive():
        try:
            time.sleep(1) 
        except KeyboardInterrupt:
            # Ce KeyboardInterrupt est pour le thread principal.
            # Le signal_handler devrait être appelé pour gérer l'arrêt proprement.
            main_logger.info("KeyboardInterrupt reçu dans la boucle principale de main.py. Le signal_handler devrait prendre le relais.")
            # On ne fait rien ici, on laisse le signal_handler faire son travail.
            # Si signal_handler n'est pas appelé (ex: Windows où Ctrl+C peut ne pas être un signal),
            # il faut une logique de secours.
            if sys.platform == "win32": # Gestion spécifique pour Windows si Ctrl+C ne déclenche pas SIGINT proprement
                signal_handler(signal.SIGINT, None) # Appeler manuellement
            break 
        except Exception as e: # Erreur inattendue dans cette boucle d'attente
            main_logger.error(f"Erreur dans la boucle principale de main.py: {e}", exc_info=True)
            signal_handler(signal.SIGTERM, None) # Tenter un arrêt propre
            break 

    # Si la boucle se termine parce que le thread du contrôleur n'est plus actif
    # (par exemple, si le contrôleur s'arrête de lui-même ou après une erreur dans son thread)
    if not controller_thread.is_alive():
        main_logger.info("Le thread du SerreController s'est terminé.")
        # S'assurer que le cleanup a été fait si le thread s'est terminé de manière inattendue
        # et que le signal_handler n'a pas déjà appelé shutdown().
        # La méthode shutdown() de SerreController devrait être idempotente.
        if serre_controller_instance:
             main_logger.info("Appel de shutdown sur SerreController au cas où (fin de main.py).")
             serre_controller_instance.shutdown()


if __name__ == "__main__":
    # Enregistrer les gestionnaires de signaux pour un arrêt propre
    # SIGINT est généralement déclenché par Ctrl+C.
    # SIGTERM est un signal d'arrêt plus générique (ex: `kill <pid>`).
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Sur Windows, SIGTERM n'est pas vraiment supporté de la même manière.
    # SIGBREAK (Ctrl+Break) peut être une alternative, ou gérer Ctrl+C via KeyboardInterrupt.
    # La gestion actuelle avec KeyboardInterrupt dans la boucle while et l'appel manuel
    # de signal_handler pour Windows devrait aider.

    main_logger.info(f"Lancement de l'application principale depuis {__file__}")
    try:
        run_controller()
    except SystemExit:
        # Permet à sys.exit(0) dans signal_handler de terminer proprement sans logger une erreur ici.
        main_logger.info("SystemExit attrapé, arrêt normal de l'application.")
    except Exception as e:
        main_logger.critical(f"Une erreur non gérée s'est produite dans __main__ et a atteint le plus haut niveau: {e}", exc_info=True)
        # Tentative d'arrêt propre en cas d'erreur catastrophique non gérée ailleurs
        if serre_controller_instance:
            try:
                main_logger.info("Tentative de shutdown du contrôleur après une erreur critique dans __main__.")
                serre_controller_instance.shutdown()
            except Exception as shutdown_err:
                main_logger.error(f"Erreur lors de la tentative de shutdown après une erreur critique: {shutdown_err}", exc_info=True)
        sys.exit(1) # S'assurer que le script se termine avec un code d'erreur
    finally:
        # Ce code sera exécuté même si sys.exit() est appelé, ou si une exception non gérée se produit.
        main_logger.info("Fin du bloc __main__ de main.py.")
        # Il est important que le pool de la base de données et les GPIOs soient nettoyés.
        # La méthode shutdown() du contrôleur est responsable de cela.
        # Si le signal_handler a déjà appelé shutdown, un deuxième appel devrait être sans effet (idempotent).



