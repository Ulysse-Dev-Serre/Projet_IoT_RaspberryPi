# src/api/app.py
import sys
import os
import threading
import logging
import signal 
import time

# Ajouter le répertoire racine du projet au PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from flask import Flask, jsonify, render_template, request
    from src.core.serre_logic import SerreController
    from src import config 
except ImportError as e:
    print(f"Erreur d'importation critique dans app.py: {e}.")
    sys.exit(1)

# Configuration du logging
log_level_str = getattr(config, 'LOG_LEVEL', 'INFO').upper()
log_level = getattr(logging, log_level_str, logging.INFO)
log_file_dir = os.path.dirname(config.LOG_FILE_PATH)

if log_file_dir and not os.path.exists(log_file_dir):
    try: 
        os.makedirs(log_file_dir)
    except OSError as e_mkdir:
        print(f"AVERTISSEMENT: Impossible de créer le répertoire de logs {log_file_dir}: {e_mkdir}")

log_handlers = [logging.StreamHandler(sys.stdout)]
if hasattr(config, 'LOG_FILE_PATH') and config.LOG_FILE_PATH:
    try:
        if not os.path.exists(log_file_dir) and log_file_dir:
             os.makedirs(log_file_dir)
        log_handlers.append(logging.FileHandler(config.LOG_FILE_PATH, mode='a'))
    except Exception as e_fh:
        print(f"AVERTISSEMENT: Impossible d'ouvrir le fichier log {config.LOG_FILE_PATH}: {e_fh}")

logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(levelname)s - %(name)s - %(threadName)s - %(message)s',
    handlers=log_handlers
)
flask_logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates')

# --- Variable globale pour l'état d'arrêt ---
SHUTDOWN_REQUESTED = threading.Event()

# Instanciation du contrôleur de la serre
try:
    controller = SerreController()
except Exception as e:
    flask_logger.critical(f"Erreur critique lors de l'initialisation de SerreController: {e}", exc_info=True)
    # Si le contrôleur ne peut pas démarrer, il est préférable d'arrêter l'application Flask.
    # On pourrait lever l'exception pour arrêter le script, ou appeler sys.exit(1)
    print("ERREUR CRITIQUE: SerreController n'a pas pu être initialisé. Arrêt de l'application.")
    sys.exit(1)


# --- Routes (inchangées) ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/status', methods=['GET'])
def get_status_route():
    try:
        current_status = controller.get_status()
        return jsonify(current_status)
    except Exception as e:
        flask_logger.error(f"Erreur lors de la récupération du statut: {e}", exc_info=True)
        return jsonify({"error": "Erreur interne du serveur lors de la récupération du statut"}), 500

@app.route('/api/settings', methods=['GET'])
def get_settings_route_api():
    try:
        current_settings = controller.get_all_settings() 
        return jsonify(current_settings)
    except Exception as e:
        flask_logger.error(f"Erreur lors de la récupération des configurations: {e}", exc_info=True)
        return jsonify({"error": "Erreur interne du serveur"}), 500

@app.route('/api/settings', methods=['POST'])
def update_settings_route_api():
    try:
        new_settings_data = request.json
        if not new_settings_data:
            return jsonify({"success": False, "message": "Aucune donnée de configuration fournie."}), 400
        flask_logger.info(f"Requête de mise à jour des configurations reçue: {new_settings_data}")
        if controller.update_settings(new_settings_data):
            flask_logger.info("Configurations mises à jour avec succès.")
            return jsonify({"success": True, "message": "Configurations mises à jour avec succès."})
        else:
            flask_logger.warning("Échec de la mise à jour des configurations (validation ou sauvegarde échouée).")
            return jsonify({"success": False, "message": "Échec de la mise à jour des configurations."}), 400
    except Exception as e:
        flask_logger.error(f"Erreur lors de la mise à jour des configurations: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur interne du serveur"}), 500

# Contrôles des actionneurs (inchangés)
@app.route('/control/leds', methods=['POST'])
def control_leds_route():
    try:
        action = request.form.get('action', 'toggle') 
        current_status = controller.led_ctrl.get_status()
        new_state = not current_status["is_active"] if action == 'toggle' else (action == 'on')
        controller.set_leds_manual_mode(True, new_state)
        updated_status = controller.led_ctrl.get_status()
        return jsonify({"success": True, "message": f"LEDs {'allumées' if new_state else 'éteintes'}", "leds_active": updated_status["is_active"], "manual_mode": updated_status["manual_mode"]})
    except Exception as e:
        flask_logger.error(f"Erreur contrôle LEDs: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur"}), 500

@app.route('/control/humidifier', methods=['POST'])
def control_humidifier_route():
    try:
        action = request.form.get('action', 'toggle')
        current_status = controller.humidifier_ctrl.get_status()
        new_state = not current_status["is_active"] if action == 'toggle' else (action == 'on')
        controller.set_humidifier_manual_mode(True, new_state)
        updated_status = controller.humidifier_ctrl.get_status()
        return jsonify({"success": True, "message": f"Humidificateur {'activé' if new_state else 'désactivé'}", "humidifier_active": updated_status["is_active"], "manual_mode": updated_status["manual_mode"]})
    except Exception as e:
        flask_logger.error(f"Erreur contrôle Humidificateur: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur"}), 500

@app.route('/control/ventilation', methods=['POST'])
def control_ventilation_route():
    try:
        action = request.form.get('action', 'toggle')
        current_status = controller.ventilation_ctrl.get_status()
        new_state = not current_status["is_active"] if action == 'toggle' else (action == 'on')
        controller.set_ventilation_manual_mode(True, new_state)
        updated_status = controller.ventilation_ctrl.get_status()
        return jsonify({"success": True, "message": f"Ventilation {'activée' if new_state else 'désactivée'}", "ventilation_active": updated_status["is_active"], "manual_mode": updated_status["manual_mode"]})
    except Exception as e:
        flask_logger.error(f"Erreur contrôle Ventilation: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur"}), 500

@app.route('/control/auto_mode', methods=['POST'])
def set_auto_mode_route():
    try:
        controller.set_all_auto_mode()
        return jsonify({"success": True, "message": "Mode automatique global activé."})
    except Exception as e:
        flask_logger.error(f"Erreur mode auto: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur"}), 500

@app.route('/control/emergency_stop', methods=['POST'])
def emergency_stop_route():
    try:
        controller.emergency_stop_all_actuators()
        return jsonify({"success": True, "message": "Arrêt d'urgence effectué."})
    except Exception as e:
        flask_logger.error(f"Erreur arrêt d'urgence: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur serveur"}), 500


# --- Gestion de l'arrêt propre ---
controller_main_thread_instance = None 

def perform_shutdown_tasks():
    """Effectue les tâches de nettoyage pour SerreController."""
    if controller: 
        flask_logger.info("perform_shutdown_tasks: Appel de controller.shutdown()...")
        controller.shutdown() 
    
    global controller_main_thread_instance
    if controller_main_thread_instance and controller_main_thread_instance.is_alive():
        flask_logger.info("perform_shutdown_tasks: Attente de la fin du thread SerreController.run()...")
        controller_main_thread_instance.join(timeout=15) 
        if controller_main_thread_instance.is_alive():
            flask_logger.warning("perform_shutdown_tasks: Le thread SerreController.run() n'a pas pu être arrêté proprement.")
        else:
            flask_logger.info("perform_shutdown_tasks: Thread SerreController.run() terminé.")
    else:
        flask_logger.info("perform_shutdown_tasks: Thread SerreController.run() non actif ou non initialisé.")

def signal_handler_flask(signum, frame):
    """Gère SIGINT et SIGTERM pour Flask."""
    if SHUTDOWN_REQUESTED.is_set():
        flask_logger.info("Signal d'arrêt déjà reçu, en cours de traitement.")
        return
    SHUTDOWN_REQUESTED.set() 

    signal_name = signal.Signals(signum).name if sys.platform != "win32" else f"Signal {signum}"
    flask_logger.warning(f"Signal {signal_name} reçu. Tentative d'arrêt propre de Flask...")

    perform_shutdown_tasks()
    
    flask_logger.info("Signal handler: Tâches de nettoyage terminées.")
    
    # Tenter de demander au serveur Werkzeug de s'arrêter.
    # Cette fonction est généralement disponible uniquement dans le contexte d'une requête.
    # Une autre approche est de faire en sorte que app.run() se termine.
    # func = request.environ.get('werkzeug.server.shutdown')
    # if func:
    #     flask_logger.info("Tentative d'arrêt du serveur Werkzeug via sa fonction de shutdown...")
    #     func()
    # else:
    #     flask_logger.info("Fonction de shutdown de Werkzeug non disponible. Levée de SystemExit pour arrêter le thread principal.")
    
    # Lever SystemExit est une manière plus propre de demander l'arrêt du thread principal
    # où app.run() est appelé, par rapport à os._exit().
    raise SystemExit("Arrêt demandé par signal.")


if __name__ == "__main__":
    flask_logger.info(f"Démarrage de l'application Flask sur {config.APP_HOST}:{config.APP_PORT}")
    flask_logger.info(f"Mode matériel: {getattr(config, 'HARDWARE_ENV', 'N/A')}, Mode base de données: {getattr(config, 'DB_ENV', 'N/A')}")

    if controller: 
        flask_logger.info("Démarrage du thread pour SerreController.run()...")
        controller_main_thread_instance = threading.Thread(target=controller.run, name="SerreControllerRunThread", daemon=True)
        controller_main_thread_instance.start()
    else:
        # Cette condition est maintenant gérée par le sys.exit(1) plus haut si controller n'est pas initialisé.
        pass

    signal.signal(signal.SIGINT, signal_handler_flask) 
    signal.signal(signal.SIGTERM, signal_handler_flask)

    try:
        flask_logger.info(f"Lancement de app.run() sur {config.APP_HOST}:{config.APP_PORT}")
        app.run(host=config.APP_HOST, port=config.APP_PORT, debug=config.APP_DEBUG_MODE, use_reloader=False)
    
    except SystemExit as e: 
        flask_logger.info(f"Serveur Flask arrêté suite à SystemExit: {e}")
    except KeyboardInterrupt: 
        flask_logger.info("Serveur Flask interrompu par KeyboardInterrupt (devrait être géré par signal_handler_flask).")
        if not SHUTDOWN_REQUESTED.is_set():
            SHUTDOWN_REQUESTED.set()
            perform_shutdown_tasks() 
    except Exception as e:
        flask_logger.critical(f"Erreur non gérée lors de l'exécution du serveur Flask: {e}", exc_info=True)
        if not SHUTDOWN_REQUESTED.is_set():
            SHUTDOWN_REQUESTED.set()
            perform_shutdown_tasks() 
    finally:
        flask_logger.info("Bloc finally de __main__ dans app.py atteint.")
        # S'assurer que le cleanup est tenté si l'arrêt n'a pas été initié correctement
        if not SHUTDOWN_REQUESTED.is_set(): 
            flask_logger.info("Arrêt non initié par signal ou exception gérée, appel de perform_shutdown_tasks depuis finally.")
            SHUTDOWN_REQUESTED.set() # Marquer comme demandé pour éviter boucle si perform_shutdown_tasks échoue
            perform_shutdown_tasks()
        
        flask_logger.info("Application Flask (app.py) terminée.")




