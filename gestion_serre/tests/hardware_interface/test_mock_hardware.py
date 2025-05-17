# tests/unit/test_mock_hardware.py
import pytest # Pytest sera automatiquement disponible si installé

# Assurez-vous que le chemin vers 'src' est géré pour les imports.
# Si vous lancez pytest depuis la racine du projet, cela devrait fonctionner.
# Sinon, des ajustements de PYTHONPATH ou des conftest.py peuvent être nécessaires.
from src.hardware_interface.mock_hardware import MockHardware

def test_mock_hardware_initialization():
    """Teste l'initialisation de MockHardware."""
    mock_hw = MockHardware()
    assert mock_hw is not None, "MockHardware devrait s'initialiser."
    # Vérifier les états initiaux des actionneurs simulés
    assert not mock_hw._leds_on, "LEDs devraient être éteintes à l'initialisation."
    assert not mock_hw._humidifier_on, "Humidificateur devrait être éteint à l'initialisation."
    assert not mock_hw._ventilation_on, "Ventilation devrait être éteinte à l'initialisation."

def test_mock_lire_capteur_returns_valid_format():
    """Teste si lire_capteur retourne le format attendu (tuple de 3 floats/None)."""
    mock_hw = MockHardware()
    result = mock_hw.lire_capteur()
    assert isinstance(result, tuple), "lire_capteur devrait retourner un tuple."
    assert len(result) == 3, "Le tuple devrait contenir 3 éléments (temp, hum, co2)."
    
    temp, hum, co2 = result
    # Vérifie que les valeurs sont soit des floats (ou int pour co2), soit None en cas d'échec simulé (si implémenté)
    assert isinstance(temp, (float, type(None))), "La température doit être un float ou None."
    assert isinstance(hum, (float, type(None))), "L'humidité doit être un float ou None."
    assert isinstance(co2, (float, type(None))), "Le CO2 doit être un float ou None." # CO2 est float dans MockHardware

def test_mock_led_control():
    """Teste l'activation et la désactivation des LEDs simulées."""
    mock_hw = MockHardware()
    
    # Vérifier l'état initial
    assert not mock_hw._leds_on, "Initialement, les LEDs simulées devraient être éteintes."

    # Activer les LEDs
    mock_hw.activer_leds()
    assert mock_hw._leds_on, "Après activer_leds(), les LEDs simulées devraient être allumées."

    # Désactiver les LEDs
    mock_hw.desactiver_leds()
    assert not mock_hw._leds_on, "Après desactiver_leds(), les LEDs simulées devraient être éteintes."

# Vous ajouteriez des tests similaires pour l'humidificateur et la ventilation.