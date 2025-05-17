# src/api/app.py
import sys
import os
import threading
import logging
import signal # Pour gérer l'arrêt propre

# Ajouter le répertoire racine du projet au PYTHONPATH pour faciliter les imports
# Cela suppose que app.py est dans src/api/
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from flask import Flask, jsonify, render_template, request, redirect, url_for
    from src.core.serre_logic import SerreController
    import config # Importer directement depuis la racine (grâce au sys.path.insert)
except ImportError as e:
    print(f"Erreur d'importation: {e}. Assurez-vous que toutes les dépendances sont installées et que config.py est à la racine.")
    sys.exit(1)

# Configuration du logging pour Flask (peut être plus élaborée)
logging.basicConfig(level=config.LOG_LEVEL, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
flask_logger = logging.getLogger(__name__) # Logger spécifique pour ce module

app = Flask(__name__, template_folder='templates')

# Instanciation du contrôleur de la serre
# SerreController gère maintenant sa propre initialisation matérielle et DB
try:
    controller = SerreController()
except Exception as e:
    flask_logger.error(f"Erreur critique lors de l'initialisation de SerreController: {e}", exc_info=True)
    # Gérer l'échec de l'initialisation (par exemple, ne pas démarrer Flask ou mode dégradé)
    # Pour l'instant, on laisse planter si le contrôleur ne peut pas démarrer.
    # Dans un cas réel, on pourrait avoir une page d'erreur.
    raise

@app.route('/')
def index():
    """Affiche la page principale avec l'état actuel de la serre."""
    # Pas besoin de passer le status ici, car il sera récupéré par JavaScript via /status
    return render_template('index.html')

@app.route('/status', methods=['GET'])
def get_status():
    """Retourne l'état actuel de la serre au format JSON."""
    try:
        status = controller.get_status()
        return jsonify(status)
    except Exception as e:
        flask_logger.error(f"Erreur lors de la récupération du statut: {e}", exc_info=True)
        return jsonify({"error": "Erreur interne du serveur lors de la récupération du statut"}), 500

# --- Routes pour le contrôle manuel ---
@app.route('/control/leds', methods=['POST'])
def control_leds_route():
    try:
        action = request.form.get('action', 'toggle') # 'on', 'off', 'toggle'
        flask_logger.info(f"Requête de contrôle LEDs reçue: action='{action}'")
        
        current_status = controller.led_ctrl.get_status()
        is_manual = True # On passe toujours en manuel pour une action directe
        new_state = False

        if action == 'on':
            new_state = True
        elif action == 'off':
            new_state = False
        elif action == 'toggle':
            new_state = not current_status["is_active"]
        else:
            return jsonify({"success": False, "message": "Action non valide"}), 400

        controller.set_leds_manual_mode(is_manual, new_state)
        # La mise à jour de l'état matériel est gérée par le contrôleur d'actionneur
        # Forcer une mise à jour immédiate de la logique pour refléter le changement peut être utile
        # controller.led_ctrl.update_state(controller.get_status()) # Passer les données capteurs actuelles
        
        flask_logger.info(f"LEDs: mode manuel={is_manual}, état demandé={new_state}")
        return jsonify({"success": True, "message": f"LEDs {'allumées' if new_state else 'éteintes'}", "leds_active": new_state, "manual_mode": is_manual})
    except Exception as e:
        flask_logger.error(f"Erreur lors du contrôle des LEDs: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur interne du serveur"}), 500


@app.route('/control/humidifier', methods=['POST'])
def control_humidifier_route():
    try:
        action = request.form.get('action', 'toggle')
        flask_logger.info(f"Requête de contrôle Humidificateur reçue: action='{action}'")

        current_status = controller.humidifier_ctrl.get_status()
        is_manual = True
        new_state = False

        if action == 'on':
            new_state = True
        elif action == 'off':
            new_state = False
        elif action == 'toggle':
            new_state = not current_status["is_active"]
        else:
            return jsonify({"success": False, "message": "Action non valide"}), 400
            
        controller.set_humidifier_manual_mode(is_manual, new_state)
        flask_logger.info(f"Humidificateur: mode manuel={is_manual}, état demandé={new_state}")
        return jsonify({"success": True, "message": f"Humidificateur {'activé' if new_state else 'désactivé'}", "humidifier_active": new_state, "manual_mode": is_manual})
    except Exception as e:
        flask_logger.error(f"Erreur lors du contrôle de l'humidificateur: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur interne du serveur"}), 500

@app.route('/control/ventilation', methods=['POST'])
def control_ventilation_route():
    try:
        action = request.form.get('action', 'toggle')
        flask_logger.info(f"Requête de contrôle Ventilation reçue: action='{action}'")

        current_status = controller.ventilation_ctrl.get_status()
        is_manual = True
        new_state = False

        if action == 'on':
            new_state = True
        elif action == 'off':
            new_state = False
        elif action == 'toggle':
            new_state = not current_status["is_active"]
        else:
            return jsonify({"success": False, "message": "Action non valide"}), 400

        controller.set_ventilation_manual_mode(is_manual, new_state)
        flask_logger.info(f"Ventilation: mode manuel={is_manual}, état demandé={new_state}")
        return jsonify({"success": True, "message": f"Ventilation {'activée' if new_state else 'désactivée'}", "ventilation_active": new_state, "manual_mode": is_manual})
    except Exception as e:
        flask_logger.error(f"Erreur lors du contrôle de la ventilation: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur interne du serveur"}), 500

# --- Routes pour les modes globaux ---
@app.route('/control/auto_mode', methods=['POST'])
def set_auto_mode_route():
    """Repasse tous les actionneurs en mode automatique."""
    try:
        controller.set_all_auto_mode()
        flask_logger.info("Tous les actionneurs sont repassés en mode automatique.")
        return jsonify({"success": True, "message": "Mode automatique activé pour tous les appareils."})
    except Exception as e:
        flask_logger.error(f"Erreur lors du passage en mode auto: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur interne du serveur"}), 500

@app.route('/control/emergency_stop', methods=['POST'])
def emergency_stop_route():
    """Arrête tous les actionneurs immédiatement."""
    try:
        controller.emergency_stop_all_actuators()
        flask_logger.warning("Arrêt d'urgence activé via API.")
        return jsonify({"success": True, "message": "Arrêt d'urgence effectué. Tous les appareils sont désactivés."})
    except Exception as e:
        flask_logger.error(f"Erreur lors de l'arrêt d'urgence: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erreur interne du serveur"}), 500

# --- Gestion de l'arrêt propre ---
def shutdown_server(signum, frame):
    flask_logger.info("Signal d'arrêt reçu. Arrêt du serveur Flask et du contrôleur...")
    # Il n'y a pas de méthode simple pour arrêter proprement le serveur de développement Flask
    # de cette manière. La meilleure approche est d'arrêter le processus.
    # controller.shutdown() sera appelé dans le bloc finally de la boucle principale.
    # Pour un serveur de production (comme Gunicorn), le signal est géré par le serveur lui-même.
    flask_logger.info("Le contrôleur sera arrêté par le bloc finally de __main__.")
    sys.exit(0) # Ceci arrêtera le processus, déclenchant le finally.

controller_thread = None

if __name__ == "__main__":
    flask_logger.info(f"Démarrage de l'application Flask sur {config.APP_HOST}:{config.APP_PORT}")
    flask_logger.info(f"Mode matériel: {config.HARDWARE_ENV}, Mode base de données: {config.DB_ENV}")

    # Démarrer le SerreController dans un thread séparé
    flask_logger.info("Démarrage du thread SerreController...")
    controller_thread = threading.Thread(target=controller.run, daemon=True)
    controller_thread.start()

    # Gérer les signaux d'arrêt pour un cleanup propre
    signal.signal(signal.SIGINT, shutdown_server)  # Ctrl+C
    signal.signal(signal.SIGTERM, shutdown_server) # kill

    try:
        # Utiliser use_reloader=False pour éviter que le code ne s'exécute deux fois en mode debug
        # et pour mieux contrôler le thread du contrôleur.
        app.run(host=config.APP_HOST, port=config.APP_PORT, debug=config.APP_DEBUG_MODE, use_reloader=False)
    except KeyboardInterrupt:
        flask_logger.info("Arrêt du serveur Flask demandé par KeyboardInterrupt.")
    except Exception as e:
        flask_logger.error(f"Erreur lors de l'exécution du serveur Flask: {e}", exc_info=True)
    finally:
        flask_logger.info("Nettoyage avant la fermeture de l'application Flask...")
        if controller:
            controller.shutdown() # S'assurer que le contrôleur est bien arrêté
        if controller_thread and controller_thread.is_alive():
            flask_logger.info("Attente de la fin du thread SerreController...")
            controller_thread.join(timeout=10) # Attendre jusqu'à 10 secondes
            if controller_thread.is_alive():
                flask_logger.warning("Le thread SerreController n'a pas pu être arrêté proprement dans le délai imparti.")
        flask_logger.info("Application Flask terminée.")
