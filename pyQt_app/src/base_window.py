from PyQt6.QtWidgets import QMainWindow, QTabWidget # QWidget, QVBoxLayout ne sont plus nécessaires ici
from control_panel import ControlPanelWindow # ControlPanelWindow est importé

class BaseWindow(QMainWindow):
    def __init__(self, title="Application", parent=None): # title est optionnel
        super().__init__(parent)
        # self.api_client n'est plus initialisé ou nécessaire ici

        self.setWindowTitle("Contrôle de Serre Connectée")
        self.setGeometry(1100, 60, 700, 600)
        self._init_ui()
        # self._start_periodic_updates() # Si vous l'utilisez, définissez cette méthode

    def _init_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # MODIFICATION : On n'essaie plus de passer api_client
        self.dashboard_tab = ControlPanelWindow() # Crée ControlPanelWindow sans argument api_client
        self.tabs.addTab(self.dashboard_tab, "Tableau de Bord")

        #self.settings_tab = SettingsTab(self.api_client, self)
        #self.tabs.addTab(self.settings_tab, "Configurations")
        
       # self.history_tab = HistoryTab(self.db_client, self)
        #self.tabs.addTab(self.history_tab, "Historique & Graphiques")























        self.initSpecificUI()

    def initSpecificUI(self):
        # Cette méthode sera redéfinie (override) par les classes filles
        pass