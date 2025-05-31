# tests/core/actuators/test_ventilation_controller.py
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
import logging

from src.core.actuators.ventilation_controller import VentilationController
# Importer BaseActuator pour patcher sa méthode update_state dans certains tests
from src.core.actuators.base_actuator import BaseActuator
from src import config # Importer le module config depuis src

# Désactiver les logs pour les tests afin de ne pas polluer la sortie,
# sauf si spécifiquement réactivé dans un test pour débogage.
logging.disable(logging.CRITICAL)

class TestVentilationController(unittest.TestCase):

    def setUp(self):
        """
        Configuration initiale exécutée avant chaque test.
        """
        self.mock_hardware = MagicMock() # Simule l'interface matérielle
        self.mock_serre_controller = MagicMock() # Simule l'instance de SerreController

        # Configurer une valeur de retour par défaut pour get_setting.
        # La fonction lambda ici retournera la valeur_defaut_globale fournie à get_setting
        # si la clé spécifique n'est pas "mockée" différemment dans un test.
        self.mock_serre_controller.get_setting.side_effect = \
            lambda key, default_value: default_value

        # Créer une instance de VentilationController avec nos objets simulés
        self.controller = VentilationController(
            hardware_interface=self.mock_hardware, # Nom de paramètre corrigé
            controller_instance=self.mock_serre_controller
        )
        
        # Initialiser l'état de base de l'actionneur
        self.controller.current_state = False
        self.controller.is_manual_mode = False

    def test_initialization(self):
        """
        Teste si le contrôleur est initialisé avec les bons attributs de base.
        """
        self.assertEqual(self.controller.device_name, "ventilation")
        self.assertFalse(self.controller.current_state)
        self.assertFalse(self.controller.is_manual_mode)
        self.assertIs(self.controller.hardware, self.mock_hardware)
        self.assertIs(self.controller.controller, self.mock_serre_controller)

    def test_control_hardware_activates_when_current_state_is_true(self):
        """
        Teste si hardware.activer_ventilation() est appelé quand current_state devient True.
        """
        self.controller.current_state = True
        self.controller._control_hardware()
        self.mock_hardware.activer_ventilation.assert_called_once()
        self.mock_hardware.desactiver_ventilation.assert_not_called()

    def test_control_hardware_deactivates_when_current_state_is_false(self):
        """
        Teste si hardware.desactiver_ventilation() est appelé quand current_state devient False.
        """
        self.controller.current_state = False
        self.controller._control_hardware()
        self.mock_hardware.desactiver_ventilation.assert_called_once()
        self.mock_hardware.activer_ventilation.assert_not_called()

    @patch('src.core.actuators.ventilation_controller.datetime')
    def test_get_desired_state_co2_high_in_operating_window(self, mock_datetime):
        """
        CO2 élevé, DANS la fenêtre d'opération => ventilation ON.
        """
        mock_datetime.now.return_value = datetime(2024, 5, 19, 10, 0, 0) # 10h00
        
        # Simuler les retours de get_setting pour ce test spécifique
        def mock_get_setting_values(key, default_value):
            if key == config.KEY_SEUIL_CO2_MAX:
                return 1000.0
            if key == config.KEY_HEURE_DEBUT_JOUR_OPERATION:
                return 8
            if key == config.KEY_HEURE_FIN_JOUR_OPERATION:
                return 22
            return default_value # Important pour les autres clés non mockées explicitement
        self.mock_serre_controller.get_setting.side_effect = mock_get_setting_values

        sensor_data = {config.CO2_SENSOR_INSTANCE_NAME: 1200.0} # CO2 > seuil
        
        desired_state = self.controller._get_desired_automatic_state(sensor_data)
        self.assertTrue(desired_state)

    @patch('src.core.actuators.ventilation_controller.datetime')
    def test_get_desired_state_co2_low_in_operating_window(self, mock_datetime):
        """
        CO2 bas, DANS la fenêtre d'opération => ventilation OFF.
        """
        mock_datetime.now.return_value = datetime(2024, 5, 19, 10, 0, 0)
        def mock_get_setting_values(key, default_value):
            if key == config.KEY_SEUIL_CO2_MAX:
                return 1000.0
            if key == config.KEY_HEURE_DEBUT_JOUR_OPERATION:
                return 8
            if key == config.KEY_HEURE_FIN_JOUR_OPERATION:
                return 22
            return default_value
        self.mock_serre_controller.get_setting.side_effect = mock_get_setting_values

        sensor_data = {config.CO2_SENSOR_INSTANCE_NAME: 800.0} # CO2 < seuil
        desired_state = self.controller._get_desired_automatic_state(sensor_data)
        self.assertFalse(desired_state)

    @patch('src.core.actuators.ventilation_controller.datetime')
    def test_get_desired_state_outside_operating_window(self, mock_datetime):
        """
        N'importe quel CO2, HORS fenêtre d'opération => ventilation OFF.
        """
        mock_datetime.now.return_value = datetime(2024, 5, 19, 6, 0, 0) # 6h00 (avant 8h)
        def mock_get_setting_values(key, default_value):
            # Pas besoin de mocker KEY_SEUIL_CO2_MAX ici car la fenêtre horaire devrait court-circuiter
            if key == config.KEY_HEURE_DEBUT_JOUR_OPERATION:
                return 8
            if key == config.KEY_HEURE_FIN_JOUR_OPERATION:
                return 22
            return default_value
        self.mock_serre_controller.get_setting.side_effect = mock_get_setting_values

        sensor_data = {config.CO2_SENSOR_INSTANCE_NAME: 1200.0}
        desired_state = self.controller._get_desired_automatic_state(sensor_data)
        self.assertFalse(desired_state)

    @patch('src.core.actuators.ventilation_controller.logging.warning') 
    def test_get_desired_state_co2_is_none(self, mock_logging_warning):
        """
        Donnée CO2 est None => ventilation maintient son état actuel.
        """
        self.controller.current_state = True # Supposons qu'elle était ON
        # Assurer que les settings d'heure sont valides pour ne pas interférer
        def mock_get_setting_hours(key, default_value):
            if key == config.KEY_HEURE_DEBUT_JOUR_OPERATION: return 8
            if key == config.KEY_HEURE_FIN_JOUR_OPERATION: return 22
            return default_value
        self.mock_serre_controller.get_setting.side_effect = mock_get_setting_hours
        
        sensor_data = {config.CO2_SENSOR_INSTANCE_NAME: None} 
        
        with patch('src.core.actuators.ventilation_controller.datetime') as mock_dt: # Mocker l'heure pour être dans la fenêtre
            mock_dt.now.return_value = datetime(2024, 5, 19, 10, 0, 0)
            desired_state = self.controller._get_desired_automatic_state(sensor_data)

        self.assertTrue(desired_state, "Devrait maintenir l'état ON si CO2 est None et dans la fenêtre op.")
        mock_logging_warning.assert_called_with(
            f"CO2 non disponible pour VentilationController (clé attendue: '{config.CO2_SENSOR_INSTANCE_NAME}'), maintien de l'état."
        )

    @patch.object(BaseActuator, 'update_state') 
    @patch.object(VentilationController, '_control_hardware') 
    def test_update_state_calls_control_hardware_on_state_change(self, mock_control_hardware, mock_super_update_state):
        """
        Teste si _control_hardware est appelé quand l'état change.
        """
        mock_super_update_state.return_value = True 
        sensor_data = {config.CO2_SENSOR_INSTANCE_NAME: 1200.0}

        state_actually_changed = self.controller.update_state(sensor_data)
        
        self.assertTrue(state_actually_changed)
        mock_super_update_state.assert_called_once_with(sensor_data)
        mock_control_hardware.assert_called_once()

    @patch.object(BaseActuator, 'update_state')
    @patch.object(VentilationController, '_control_hardware')
    def test_update_state_no_call_to_control_hardware_if_no_state_change(self, mock_control_hardware, mock_super_update_state):
        """
        Teste si _control_hardware N'EST PAS appelé si l'état ne change pas.
        """
        mock_super_update_state.return_value = False 
        sensor_data = {config.CO2_SENSOR_INSTANCE_NAME: 800.0}

        state_actually_changed = self.controller.update_state(sensor_data)

        self.assertFalse(state_actually_changed)
        mock_super_update_state.assert_called_once_with(sensor_data)
        mock_control_hardware.assert_not_called()

    @patch.object(VentilationController, '_control_hardware')
    def test_manual_mode_overrides_automatic_logic(self, mock_control_hardware):
        """
        Teste si le mode manuel force l'état et appelle _control_hardware.
        """
        with patch.object(self.controller, '_get_desired_automatic_state', return_value=True): # Mode auto voudrait ON
            self.controller.set_manual_mode(True, False) # Mais on met en manuel OFF
            self.assertTrue(self.controller.is_manual_mode)
            self.assertFalse(self.controller.manual_state)
            
            self.controller.current_state = True # Simuler qu'il était ON avant le update
            
            state_changed = self.controller.update_state({config.CO2_SENSOR_INSTANCE_NAME: 500})

            self.assertTrue(state_changed, "L'état aurait dû changer pour refléter le mode manuel OFF.")
            self.assertFalse(self.controller.current_state, "L'état devrait être False (manuel OFF).")
            mock_control_hardware.assert_called_once() 

    def test_get_status_content(self):
        """Teste le contenu de base retourné par get_status."""
        self.controller.is_manual_mode = True
        self.controller.current_state = True
        
        # Mocker time.time pour contrôler la durée
        # On simule que l'actionneur est ON depuis 10 secondes
        mock_current_time = 1000.0
        self.controller.on_time_start = mock_current_time - 10.0 # Démarré il y a 10s
        self.controller.off_time_start = None # S'assurer qu'il n'est pas considéré comme OFF

        with patch('time.time', return_value=mock_current_time):
            status = self.controller.get_status()
        
        self.assertTrue(status['is_active'])
        self.assertTrue(status['manual_mode'])
        self.assertEqual(status['on_duration_seconds'], 10.0)
        self.assertEqual(status['off_duration_seconds'], 0)


if __name__ == '__main__':
    # logging.disable(logging.NOTSET) # Décommenter pour voir les logs pendant l'exécution directe
    unittest.main()

