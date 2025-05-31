# tests/core/actuators/test_led_controller.py
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
import logging

# Importer la classe à tester
from src.core.actuators.led_controller import LedController
# Importer BaseActuator pour patcher sa méthode update_state dans certains tests
from src.core.actuators.base_actuator import BaseActuator
# Importer le module config pour accéder aux clés et valeurs par défaut
from src import config

# Désactiver les logs pour les tests afin de ne pas polluer la sortie,
# sauf si spécifiquement réactivé dans un test pour débogage.
logging.disable(logging.CRITICAL)

class TestLedController(unittest.TestCase):

    def setUp(self):
        """
        Configuration initiale exécutée avant chaque test.
        """
        self.mock_hardware = MagicMock()  # Simule l'interface matérielle
        self.mock_serre_controller = MagicMock()  # Simule l'instance de SerreController

        # Configurer une valeur de retour par défaut pour get_setting.
        self.mock_serre_controller.get_setting.side_effect = \
            lambda key, default_value: default_value

        # Créer une instance de LedController avec nos objets simulés
        self.controller = LedController(
            hardware_interface=self.mock_hardware,
            controller_instance=self.mock_serre_controller
        )
        
        # Initialiser l'état de base de l'actionneur
        self.controller.current_state = False
        self.controller.is_manual_mode = False

    def test_initialization(self):
        """
        Teste si le contrôleur est initialisé avec les bons attributs de base.
        """
        self.assertEqual(self.controller.device_name, "leds")
        self.assertFalse(self.controller.current_state)
        self.assertFalse(self.controller.is_manual_mode)
        self.assertIs(self.controller.hardware, self.mock_hardware)
        self.assertIs(self.controller.controller, self.mock_serre_controller)

    def test_control_hardware_activates_when_current_state_is_true(self):
        """
        Teste si hardware.activer_leds() est appelé quand current_state devient True.
        """
        self.controller.current_state = True
        self.controller._control_hardware()
        self.mock_hardware.activer_leds.assert_called_once()
        self.mock_hardware.desactiver_leds.assert_not_called()

    def test_control_hardware_deactivates_when_current_state_is_false(self):
        """
        Teste si hardware.desactiver_leds() est appelé quand current_state devient False.
        """
        self.controller.current_state = False
        self.controller._control_hardware()
        self.mock_hardware.desactiver_leds.assert_called_once()
        self.mock_hardware.activer_leds.assert_not_called()

    def _configure_settings_for_led_tests(self, heure_debut=8, heure_fin=20):
        """Méthode utilitaire pour mocker les retours de get_setting pour les tests des LEDs."""
        def mock_get_setting_values(key, default_value):
            if key == config.KEY_HEURE_DEBUT_LEDS:
                return heure_debut
            if key == config.KEY_HEURE_FIN_LEDS:
                return heure_fin
            return default_value
        self.mock_serre_controller.get_setting.side_effect = mock_get_setting_values

    @patch('src.core.actuators.led_controller.datetime')
    def test_get_desired_state_inside_led_window(self, mock_datetime):
        """LEDs ON: Heure actuelle DANS la fenêtre d'allumage."""
        mock_datetime.now.return_value = datetime(2024, 5, 19, 10, 0, 0) # 10h00
        self._configure_settings_for_led_tests(heure_debut=8, heure_fin=20)
        
        # current_sensor_data n'est pas utilisé par LedController pour _get_desired_automatic_state
        desired_state = self.controller._get_desired_automatic_state({}) 
        self.assertTrue(desired_state)

    @patch('src.core.actuators.led_controller.datetime')
    def test_get_desired_state_outside_led_window_before(self, mock_datetime):
        """LEDs OFF: Heure actuelle AVANT la fenêtre d'allumage."""
        mock_datetime.now.return_value = datetime(2024, 5, 19, 6, 0, 0) # 6h00
        self._configure_settings_for_led_tests(heure_debut=8, heure_fin=20)
        
        desired_state = self.controller._get_desired_automatic_state({})
        self.assertFalse(desired_state)

    @patch('src.core.actuators.led_controller.datetime')
    def test_get_desired_state_outside_led_window_after(self, mock_datetime):
        """LEDs OFF: Heure actuelle APRÈS la fenêtre d'allumage."""
        mock_datetime.now.return_value = datetime(2024, 5, 19, 21, 0, 0) # 21h00
        self._configure_settings_for_led_tests(heure_debut=8, heure_fin=20)
        
        desired_state = self.controller._get_desired_automatic_state({})
        self.assertFalse(desired_state)

    @patch('src.core.actuators.led_controller.datetime')
    def test_get_desired_state_led_window_crosses_midnight_inside_before_midnight(self, mock_datetime):
        """LEDs ON: Fenêtre traversant minuit, heure actuelle AVANT minuit (ex: 22h-6h, heure=23h)."""
        mock_datetime.now.return_value = datetime(2024, 5, 19, 23, 0, 0) # 23h00
        self._configure_settings_for_led_tests(heure_debut=22, heure_fin=6)
        
        desired_state = self.controller._get_desired_automatic_state({})
        self.assertTrue(desired_state)

    @patch('src.core.actuators.led_controller.datetime')
    def test_get_desired_state_led_window_crosses_midnight_inside_after_midnight(self, mock_datetime):
        """LEDs ON: Fenêtre traversant minuit, heure actuelle APRÈS minuit (ex: 22h-6h, heure=3h)."""
        mock_datetime.now.return_value = datetime(2024, 5, 19, 3, 0, 0) # 3h00
        self._configure_settings_for_led_tests(heure_debut=22, heure_fin=6)
        
        desired_state = self.controller._get_desired_automatic_state({})
        self.assertTrue(desired_state)

    @patch('src.core.actuators.led_controller.datetime')
    def test_get_desired_state_led_window_crosses_midnight_outside(self, mock_datetime):
        """LEDs OFF: Fenêtre traversant minuit, heure actuelle HORS fenêtre (ex: 22h-6h, heure=12h)."""
        mock_datetime.now.return_value = datetime(2024, 5, 19, 12, 0, 0) # 12h00
        self._configure_settings_for_led_tests(heure_debut=22, heure_fin=6)
        
        desired_state = self.controller._get_desired_automatic_state({})
        self.assertFalse(desired_state)

    @patch('src.core.actuators.led_controller.logging.error')
    def test_get_desired_state_invalid_hour_settings(self, mock_logging_error):
        """LEDs OFF: Si les settings d'heure sont invalides, utilise les défauts globaux."""
        # Simuler des settings invalides
        def mock_get_setting_invalid(key, default_value):
            if key == config.KEY_HEURE_DEBUT_LEDS:
                return "invalid_start"
            if key == config.KEY_HEURE_FIN_LEDS:
                return "invalid_end"
            return default_value
        self.mock_serre_controller.get_setting.side_effect = mock_get_setting_invalid
        
        with patch('src.core.actuators.led_controller.datetime') as mock_dt:
            # Mettre une heure qui serait ON avec les défauts globaux (ex: 10h pour 8h-20h)
            mock_dt.now.return_value = datetime(2024, 5, 19, 10, 0, 0) 
            desired_state = self.controller._get_desired_automatic_state({})
        
        # Vérifier que l'état est basé sur les valeurs par défaut globales de config.py
        # (config.HEURE_DEBUT_LEDS et config.HEURE_FIN_LEDS)
        expected_state_with_defaults = config.HEURE_DEBUT_LEDS <= 10 < config.HEURE_FIN_LEDS
        self.assertEqual(desired_state, expected_state_with_defaults)
        mock_logging_error.assert_called() # Vérifier qu'une erreur a été loggée

    @patch.object(BaseActuator, 'update_state') 
    @patch.object(LedController, '_control_hardware') 
    def test_update_state_calls_control_hardware_on_state_change(self, mock_control_hardware, mock_super_update_state):
        """Teste si _control_hardware est appelé quand l'état change."""
        mock_super_update_state.return_value = True 
        
        state_actually_changed = self.controller.update_state({}) # sensor_data non utilisé
        
        self.assertTrue(state_actually_changed)
        mock_super_update_state.assert_called_once_with({})
        mock_control_hardware.assert_called_once()

    @patch.object(BaseActuator, 'update_state')
    @patch.object(LedController, '_control_hardware')
    def test_update_state_no_call_to_control_hardware_if_no_state_change(self, mock_control_hardware, mock_super_update_state):
        """Teste si _control_hardware N'EST PAS appelé si l'état ne change pas."""
        mock_super_update_state.return_value = False
        
        state_actually_changed = self.controller.update_state({})

        self.assertFalse(state_actually_changed)
        mock_super_update_state.assert_called_once_with({})
        mock_control_hardware.assert_not_called()

    @patch.object(LedController, '_control_hardware')
    def test_manual_mode_overrides_automatic_logic(self, mock_control_hardware):
        """Teste si le mode manuel force l'état et appelle _control_hardware."""
        with patch.object(self.controller, '_get_desired_automatic_state', return_value=True): # Mode auto voudrait ON
            self.controller.set_manual_mode(True, False) # Mais on met en manuel OFF
            self.assertTrue(self.controller.is_manual_mode)
            self.assertFalse(self.controller.manual_state)
            
            self.controller.current_state = True # Simuler qu'il était ON avant le update
            
            state_changed = self.controller.update_state({})

            self.assertTrue(state_changed)
            self.assertFalse(self.controller.current_state)
            mock_control_hardware.assert_called_once()

    def test_get_status_content(self):
        """Teste le contenu de base retourné par get_status."""
        self.controller.is_manual_mode = True
        self.controller.current_state = True
        
        mock_current_time = 3000.0
        self.controller.on_time_start = mock_current_time - 30.0 # Allumé depuis 30s
        self.controller.off_time_start = None

        with patch('time.time', return_value=mock_current_time):
            status = self.controller.get_status()
        
        self.assertTrue(status['is_active'])
        self.assertTrue(status['manual_mode'])
        self.assertEqual(status['on_duration_seconds'], 30.0)
        self.assertEqual(status['off_duration_seconds'], 0)


if __name__ == '__main__':
    # logging.disable(logging.NOTSET) # Décommenter pour voir les logs
    unittest.main()
