# tests/core/test_serre_logic.py
import unittest
from unittest.mock import MagicMock, patch, mock_open, call
import os
import json
import time 

from src.core.serre_logic import SerreController
from src.hardware_interface.mock_hardware import MockHardware
from src.utils.db_utils import DatabaseManager
from src.core.actuators.led_controller import LedController
from src.core.actuators.humidifier_controller import HumidifierController
from src.core.actuators.ventilation_controller import VentilationController
from src import config as global_real_config

import logging
logging.disable(logging.CRITICAL)

class TestSerreController(unittest.TestCase):

    @patch('src.core.serre_logic.open', new_callable=mock_open)
    @patch('src.core.serre_logic.os.path.exists')
    @patch('src.core.serre_logic.os.makedirs') 
    @patch('src.core.serre_logic.threading.Thread')
    # NOUS ALLONS PATCHER _initialize_hardware DIRECTEMENT PLUS TARD
    # @patch('src.core.serre_logic.importlib.import_module') 
    @patch('src.core.serre_logic.DatabaseManager') 
    @patch('src.core.serre_logic.VentilationController')
    @patch('src.core.serre_logic.HumidifierController')
    @patch('src.core.serre_logic.LedController')
    @patch('src.core.serre_logic.config') 
    def setUp(self, mock_config_in_serre_logic, mock_led_ctrl_constructor, 
              mock_humid_ctrl_constructor, mock_vent_ctrl_constructor,
              mock_db_manager_constructor, mock_thread_constructor, 
              mock_makedirs, mock_path_exists, mock_file_open):
        
        self.mock_config_module = mock_config_in_serre_logic
        self.mock_led_ctrl_constructor = mock_led_ctrl_constructor
        self.mock_humid_ctrl_constructor = mock_humid_ctrl_constructor
        self.mock_vent_ctrl_constructor = mock_vent_ctrl_constructor
        self.mock_db_manager_constructor = mock_db_manager_constructor
        # self.mock_import_module = mock_import_module # Plus besoin si on patche _initialize_hardware
        self.mock_thread_constructor = mock_thread_constructor
        self.mock_makedirs = mock_makedirs
        self.mock_path_exists = mock_path_exists
        self.mock_file_open = mock_file_open

        # Configurer le mock du module 'config'
        self.mock_config_module.DEFAULT_SETTINGS = global_real_config.DEFAULT_SETTINGS.copy()
        for key_const, val_const in global_real_config.DEFAULT_SETTINGS.items():
            setattr(self.mock_config_module, key_const, val_const)
            for attr_name, attr_value in global_real_config.__dict__.items():
                if attr_name.startswith("KEY_"):
                    setattr(self.mock_config_module, attr_name, attr_value)
        self.mock_config_module.USER_SETTINGS_FILE = "fake/path/user_settings.json"
        self.mock_config_module.INTERVALLE_LECTURE_RAPIDE_CAPTEURS_SECONDES = 1
        self.mock_config_module.INTERVALLE_LECTURE_CAPTEURS_SECONDES = 1
        self.mock_config_module.ACTIVE_DB_CONFIG = {'test_db_active': True} 

        # Mocks pour les constructeurs des dépendances
        self.mock_db_manager_instance = MagicMock(spec=DatabaseManager)
        self.mock_db_manager_constructor.return_value = self.mock_db_manager_instance
        self.mock_led_ctrl_instance = MagicMock(spec=LedController)
        self.mock_led_ctrl_constructor.return_value = self.mock_led_ctrl_instance
        self.mock_humid_ctrl_instance = MagicMock(spec=HumidifierController)
        self.mock_humid_ctrl_constructor.return_value = self.mock_humid_ctrl_instance
        self.mock_vent_ctrl_instance = MagicMock(spec=VentilationController)
        self.mock_vent_ctrl_constructor.return_value = self.mock_vent_ctrl_instance

        # Mocks pour les threads
        self.mock_sensor_thread = MagicMock()
        self.mock_logic_thread = MagicMock()
        # Préparer une liste pour side_effect, car chaque instanciation de SerreController créera 2 threads
        self.thread_side_effects = [self.mock_sensor_thread, self.mock_logic_thread] * 10 # Assez pour plusieurs tests

        # Instance de matériel mockée que _initialize_hardware devra retourner
        self.mock_hardware_instance = MagicMock(spec=MockHardware)


    # Patch _initialize_hardware pour ce test spécifique (et potentiellement d'autres)
    @patch.object(SerreController, '_initialize_hardware')
    def test_initialization_default_settings(self, mock_initialize_hardware):
        # Configurer le mock de _initialize_hardware pour qu'il retourne notre instance mockée
        mock_initialize_hardware.return_value = self.mock_hardware_instance
        
        self.mock_path_exists.return_value = False 
        self.mock_file_open.reset_mock() 
        
        self.mock_sensor_thread.reset_mock()
        self.mock_logic_thread.reset_mock()
        self.mock_thread_constructor.side_effect = [self.mock_sensor_thread, self.mock_logic_thread]

        controller = SerreController() 

        mock_initialize_hardware.assert_called_once() # Vérifier que notre méthode patchée a été appelée
        self.assertIs(controller.hardware, self.mock_hardware_instance)
        self.assertEqual(controller.settings, self.mock_config_module.DEFAULT_SETTINGS)
        self.mock_file_open.assert_called_with(self.mock_config_module.USER_SETTINGS_FILE, 'w', encoding='utf-8')
        
        self.mock_sensor_thread.start.assert_called_once() 
        self.mock_logic_thread.start.assert_called_once()



if __name__ == '__main__':
    logging.disable(logging.NOTSET)
    unittest.main()



