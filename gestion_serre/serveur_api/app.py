import sys
sys.path.append(r'C:\Users\ulyss\Documents\OvoOx-GreenHouse\Raspberry_pi')
from flask import Flask, jsonify, render_template, request
from logic_hardware.serre_logic import SerreController, hardware # import special vu la modificcation dans le fichier serre_logic.py
import threading

#from logic_hardware import hardware
 

app = Flask(__name__)
controller = SerreController(interval=60)  # Intervalle reste à 60, mais n’affecte pas les actions manuelles

@app.route('/status', methods=['GET'])
def get_status():
    status = controller.get_status()
    return jsonify(status)

@app.route('/')
def index():
    status = controller.get_status()
    return render_template('index.html', status=status)

@app.route('/control_humidifier', methods=['POST'])
def control_humidifier():
    data = request.form
    running = data.get('running') == 'true'
    controller.running_humidificateur = running
    controller.manual_humidificateur = True
    controller.control_humidifier()  # Applique immédiatement
    controller.update()  # Met à jour toute la logique immédiatement
    return jsonify({"success": True, "humidificateur_actif": running})

@app.route('/control_ventilation', methods=['POST'])
def control_ventilation():
    data = request.form
    running = data.get('running') == 'true'
    controller.running_ventilation = running
    controller.manual_ventilation = True
    controller.control_ventilation()  # Applique immédiatement
    controller.update()  # Met à jour toute la logique immédiatement
    return jsonify({"success": True, "ventilation_actif": running})

@app.route('/control_leds', methods=['POST'])
def control_leds():
    data = request.form
    running = data.get('running') == 'true'
    controller.running_leds = running
    controller.manual_leds = True
    controller.control_leds()  # Applique immédiatement
    controller.update()  # Met à jour toute la logique immédiatement
    return jsonify({"success": True, "leds_actif": running})

@app.route('/stop', methods=['POST'])
def stop():
    controller.running_humidificateur = False
    controller.running_ventilation = False
    controller.running_leds = False
    controller.manual_humidificateur = False
    controller.manual_ventilation = False
    controller.manual_leds = False
    hardware.cleanup()
    controller.update()  # Met à jour toute la logique immédiatement
    return jsonify({"success": True, "message": "Arrêt d’urgence effectué"})

@app.route('/auto_mode', methods=['POST'])
def auto_mode():
    controller.manual_humidificateur = False
    controller.manual_ventilation = False
    controller.manual_leds = False
    controller.update()  # Met à jour toute la logique immédiatement
    return jsonify({"success": True, "message": "Retour au mode automatique"})

if __name__ == "__main__":
    thread = threading.Thread(target=controller.run, daemon=True)
    thread.start()
    app.run(host='0.0.0.0', port=5000, debug=False)