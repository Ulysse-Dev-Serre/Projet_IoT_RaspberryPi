# tests/core/actuators/test_humidifier_controller.py
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
import logging

# Importer la classe à tester
from src.core.actuators.humidifier_controller import HumidifierController
# Importer BaseActuator pour patcher sa méthode update_state dans certains tests
from src.core.actuators.base_actuator import BaseActuator
# Importer le module config pour accéder aux clés et valeurs par défaut
from src import config

# Désactiver les logs pour les tests afin de ne pas polluer la sortie,
# sauf si spécifiquement réactivé dans un test pour débogage.
logging.disable(logging.CRITICAL)

class TestHumidifierController(unittest.TestCase):

    def setUp(self):
        """
        Configuration initiale exécutée avant chaque test.
        """
        self.mock_hardware = MagicMock()  # Simule l'interface matérielle
        self.mock_serre_controller = MagicMock()  # Simule l'instance de SerreController

        # Configurer une valeur de retour par défaut pour get_setting.
        self.mock_serre_controller.get_setting.side_effect = \
            lambda key, default_value: default_value

        # Créer une instance de HumidifierController avec nos objets simulés
        self.controller = HumidifierController(
            hardware_interface=self.mock_hardware,
            controller_instance=self.mock_serre_controller
        )
        
        # Initialiser l'état de base de l'actionneur
        self.controller.current_state = False
        self.controller.is_manual_mode = False
        self.controller.last_special_session_done_today = False # Attribut spécifique à HumidifierController

    def test_initialization(self):
        """
        Teste si le contrôleur est initialisé avec les bons attributs de base.
        """
        self.assertEqual(self.controller.device_name, "humidifier")
        self.assertFalse(self.controller.current_state)
        self.assertFalse(self.controller.is_manual_mode)
        self.assertFalse(self.controller.last_special_session_done_today)
        self.assertIs(self.controller.hardware, self.mock_hardware)
        self.assertIs(self.controller.controller, self.mock_serre_controller)

    def test_control_hardware_activates_when_current_state_is_true(self):
        """
        Teste si hardware.activer_humidificateur() est appelé quand current_state devient True.
        """
        self.controller.current_state = True
        self.controller._control_hardware()
        self.mock_hardware.activer_humidificateur.assert_called_once()
        self.mock_hardware.desactiver_humidificateur.assert_not_called()

    def test_control_hardware_deactivates_when_current_state_is_false(self):
        """
        Teste si hardware.desactiver_humidificateur() est appelé quand current_state devient False.
        """
        self.controller.current_state = False
        self.controller._control_hardware()
        self.mock_hardware.desactiver_humidificateur.assert_called_once()
        self.mock_hardware.activer_humidificateur.assert_not_called()

    def _configure_settings_for_humidity_tests(self, seuil_on=75.0, seuil_off=85.0, heure_debut=8, heure_fin=22):
        """Méthode utilitaire pour mocker les retours de get_setting pour les tests d'humidité."""
        def mock_get_setting_values(key, default_value):
            if key == config.KEY_SEUIL_HUMIDITE_ON:
                return seuil_on
            if key == config.KEY_SEUIL_HUMIDITE_OFF:
                return seuil_off
            if key == config.KEY_HEURE_DEBUT_JOUR_OPERATION:
                return heure_debut
            if key == config.KEY_HEURE_FIN_JOUR_OPERATION:
                return heure_fin
            return default_value
        self.mock_serre_controller.get_setting.side_effect = mock_get_setting_values

    @patch('src.core.actuators.humidifier_controller.datetime')
    def test_get_desired_state_humidity_low_in_op_window(self, mock_datetime):
        """Humidité basse, DANS la fenêtre d'opération => humidificateur ON."""
        mock_datetime.now.return_value = datetime(2024, 5, 19, 10, 0, 0) # 10h00
        self._configure_settings_for_humidity_tests(seuil_on=75.0, seuil_off=85.0, heure_debut=8, heure_fin=22)
        
        sensor_data = {'humidite': 70.0} # Humidité < seuil_on
        desired_state = self.controller._get_desired_automatic_state(sensor_data)
        self.assertTrue(desired_state)

    @patch('src.core.actuators.humidifier_controller.datetime')
    def test_get_desired_state_humidity_high_in_op_window(self, mock_datetime):
        """Humidité haute, DANS la fenêtre d'opération => humidificateur OFF."""
        mock_datetime.now.return_value = datetime(2024, 5, 19, 10, 0, 0)
        self._configure_settings_for_humidity_tests(seuil_on=75.0, seuil_off=85.0, heure_debut=8, heure_fin=22)

        sensor_data = {'humidite': 90.0} # Humidité >= seuil_off
        desired_state = self.controller._get_desired_automatic_state(sensor_data)
        self.assertFalse(desired_state)

    @patch('src.core.actuators.humidifier_controller.datetime')
    def test_get_desired_state_humidity_between_thresholds_in_op_window_maintains_state(self, mock_datetime):
        """Humidité entre seuils, DANS la fenêtre d'opération => maintient l'état (hystérésis)."""
        mock_datetime.now.return_value = datetime(2024, 5, 19, 10, 0, 0)
        self._configure_settings_for_humidity_tests(seuil_on=75.0, seuil_off=85.0, heure_debut=8, heure_fin=22)
        sensor_data = {'humidite': 80.0} # Entre seuil_on et seuil_off

        # Cas 1: était ON, doit rester ON
        self.controller.current_state = True
        desired_state = self.controller._get_desired_automatic_state(sensor_data)
        self.assertTrue(desired_state, "Devrait rester ON (hystérésis)")

        # Cas 2: était OFF, doit rester OFF
        self.controller.current_state = False
        desired_state = self.controller._get_desired_automatic_state(sensor_data)
        self.assertFalse(desired_state, "Devrait rester OFF (hystérésis)")

    @patch('src.core.actuators.humidifier_controller.datetime')
    def test_get_desired_state_outside_operating_window(self, mock_datetime):
        """N'importe quelle humidité, HORS fenêtre d'opération => humidificateur OFF."""
        mock_datetime.now.return_value = datetime(2024, 5, 19, 6, 0, 0) # 6h00 (avant 8h)
        self._configure_settings_for_humidity_tests(heure_debut=8, heure_fin=22)
        
        sensor_data = {'humidite': 70.0} # Humidité basse
        desired_state = self.controller._get_desired_automatic_state(sensor_data)
        self.assertFalse(desired_state)

    @patch('src.core.actuators.humidifier_controller.logging.warning')
    def test_get_desired_state_humidity_is_none(self, mock_logging_warning):
        """Donnée humidité est None => humidificateur maintient son état actuel."""
        self.controller.current_state = True # Supposons qu'il était ON
        self._configure_settings_for_humidity_tests() # Assurer des settings valides
        sensor_data = {'humidite': None}
        
        with patch('src.core.actuators.humidifier_controller.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2024, 5, 19, 10, 0, 0) # Dans la fenêtre op
            desired_state = self.controller._get_desired_automatic_state(sensor_data)

        self.assertTrue(desired_state, "Devrait maintenir l'état ON si humidité est None")
        mock_logging_warning.assert_called_with(
            "Humidité non disponible pour HumidifierController, maintien de l'état."
        )
        
    @patch('src.core.actuators.humidifier_controller.datetime')
    def test_special_session_activates_humidifier(self, mock_datetime):
        """Teste si la session spéciale active l'humidificateur."""
        mock_datetime.now.return_value = datetime(2024, 5, 19, 21, 32, 0) # 21h32 (dans la session spéciale 21h30-21h35)
        self._configure_settings_for_humidity_tests(heure_debut=8, heure_fin=23) # Assurer qu'on est dans la fenêtre générale
        self.controller.last_special_session_done_today = False
        
        sensor_data = {'humidite': 90.0} # Humidité haute, normalement il serait OFF
        desired_state = self.controller._get_desired_automatic_state(sensor_data)
        self.assertTrue(desired_state, "Devrait être ON pendant la session spéciale, même si humidité haute.")

    @patch('src.core.actuators.humidifier_controller.datetime')
    def test_special_session_flag_reset_and_set(self, mock_datetime):
        """Teste la gestion du flag last_special_session_done_today."""
        self._configure_settings_for_humidity_tests(seuil_on=75, seuil_off=85, heure_debut=8, heure_fin=23)
        sensor_data_low_humidity = {'humidite': 70.0}
        sensor_data_high_humidity = {'humidite': 90.0}

        # 1. Simuler avant la session spéciale, le flag est False
        mock_datetime.now.return_value = datetime(2024, 5, 19, 20, 0, 0)
        self.controller.last_special_session_done_today = True # Forcer à True pour tester la réinitialisation
        self.controller._get_desired_automatic_state(sensor_data_low_humidity) # Appel pour potentiellement réinitialiser
        self.assertFalse(self.controller.last_special_session_done_today, "Flag aurait dû être réinitialisé avant la session.")

        # 2. Pendant la session spéciale, il s'active, le flag reste False
        mock_datetime.now.return_value = datetime(2024, 5, 19, 21, 32, 0)
        self.assertTrue(self.controller._get_desired_automatic_state(sensor_data_high_humidity))
        self.assertFalse(self.controller.last_special_session_done_today, "Flag ne doit pas changer pendant la session si activé.")

        # 3. Juste après la session spéciale, il se désactive (humidité haute), le flag devient True
        self.controller.current_state = True # Simuler qu'il était ON pendant la session
        mock_datetime.now.return_value = datetime(2024, 5, 19, 21, 36, 0) # Après 21h35
        self.assertFalse(self.controller._get_desired_automatic_state(sensor_data_high_humidity)) # Doit s'éteindre
        self.assertTrue(self.controller.last_special_session_done_today, "Flag aurait dû être mis à True après la session.")


    @patch.object(BaseActuator, 'update_state') 
    @patch.object(HumidifierController, '_control_hardware') 
    def test_update_state_calls_control_hardware_on_state_change(self, mock_control_hardware, mock_super_update_state):
        """Teste si _control_hardware est appelé quand l'état change."""
        mock_super_update_state.return_value = True 
        sensor_data = {'humidite': 70.0}

        state_actually_changed = self.controller.update_state(sensor_data)
        
        self.assertTrue(state_actually_changed)
        mock_super_update_state.assert_called_once_with(sensor_data)
        mock_control_hardware.assert_called_once()

    @patch.object(BaseActuator, 'update_state')
    @patch.object(HumidifierController, '_control_hardware')
    def test_update_state_no_call_to_control_hardware_if_no_state_change(self, mock_control_hardware, mock_super_update_state):
        """Teste si _control_hardware N'EST PAS appelé si l'état ne change pas."""
        mock_super_update_state.return_value = False
        sensor_data = {'humidite': 80.0}

        state_actually_changed = self.controller.update_state(sensor_data)

        self.assertFalse(state_actually_changed)
        mock_super_update_state.assert_called_once_with(sensor_data)
        mock_control_hardware.assert_not_called()

    @patch.object(HumidifierController, '_control_hardware')
    def test_manual_mode_overrides_automatic_logic(self, mock_control_hardware):
        """Teste si le mode manuel force l'état et appelle _control_hardware."""
        with patch.object(self.controller, '_get_desired_automatic_state', return_value=True): # Mode auto voudrait ON
            self.controller.set_manual_mode(True, False) # Mais on met en manuel OFF
            self.assertTrue(self.controller.is_manual_mode)
            self.assertFalse(self.controller.manual_state)
            
            self.controller.current_state = True # Simuler qu'il était ON avant le update
            
            state_changed = self.controller.update_state({'humidite': 70.0})

            self.assertTrue(state_changed)
            self.assertFalse(self.controller.current_state)
            mock_control_hardware.assert_called_once()

    def test_get_status_content(self):
        """Teste le contenu de base retourné par get_status."""
        self.controller.is_manual_mode = False
        self.controller.current_state = False
        
        mock_current_time = 2000.0
        self.controller.off_time_start = mock_current_time - 20.0 # Éteint depuis 20s
        self.controller.on_time_start = None

        with patch('time.time', return_value=mock_current_time):
            status = self.controller.get_status()
        
        self.assertFalse(status['is_active'])
        self.assertFalse(status['manual_mode'])
        self.assertEqual(status['off_duration_seconds'], 20.0)
        self.assertEqual(status['on_duration_seconds'], 0)


if __name__ == '__main__':
    # logging.disable(logging.NOTSET) # Décommenter pour voir les logs
    unittest.main()
