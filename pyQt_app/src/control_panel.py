from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QLabel, QFrame, QGridLayout, QWidget#uniquement pour les teste 


class ControlPanelWindow(QWidget): #hérite de QWidget
    def __init__(self, parent=None):
        super().__init__(parent) # Appel au constructeur de QWidget
        
        
        self.initSpecificUI()

    def initSpecificUI(self):
        # États initiaux des appareils
        self.leds_on = False
        self.humidificateur_on = False
        self.ventilation_on = False

        # Layout principal pour toute la fenêtre LAYOUT = Position
        main_position = QVBoxLayout(self) # Appliquer le layout directement au widget
        
        #-------------------------BOUTON APAREILLE------------------------------------
        # crée une "boîte" conceptuelle pour grouper les boutons avec QFrame 
        boutons_appareils = QFrame(self) 
        boutons_appareils.setFrameShape(QFrame.Shape.StyledPanel)
        position_boutons_appareils = QVBoxLayout(boutons_appareils)

        # Créez les boutons et connectez-les aux méthodes appropriées
        self.button_leds = QPushButton()
        self.button_leds.clicked.connect(self.changer_etat_leds)
        position_boutons_appareils.addWidget(self.button_leds)

        self.button_humidificateur = QPushButton()
        self.button_humidificateur.clicked.connect(self.changer_etat_humidificateur)
        position_boutons_appareils.addWidget(self.button_humidificateur)

        self.button_ventilation = QPushButton()
        self.button_ventilation.clicked.connect(self.changer_etat_ventilation)
        position_boutons_appareils.addWidget(self.button_ventilation)

        # Créez un label pour afficher l'état des appareils
        self.status_label = QLabel("État des appareils")
        position_boutons_appareils.addWidget(self.status_label)

         #------------------------BOUTON ARRET D'URGENCE/MODE AUTOMATIQUE -------------------------
        self.button_mode_auto = QPushButton("mode automatique")
        self.button_mode_auto.clicked.connect(self.basculer_mode_automatique)
        position_boutons_appareils.addWidget(self.button_mode_auto)

        self.button_arret_urgence = QPushButton("ARRÊT D'URGENCE")
        self.button_arret_urgence.clicked.connect(self.activer_arret_urgence)
        position_boutons_appareils.addWidget(self.button_arret_urgence)


        main_position.addWidget(boutons_appareils) # Ajoute le QFrame au layout principal
        self.update_button_texts()

        #----------------------- 



        #----------------------AFFICHER CONDITION ACTUELLE-------------------------------
        conditions_group = QFrame(self)
        conditions_group.setFrameShape(QFrame.Shape.StyledPanel)
        conditions_position = QGridLayout(conditions_group) # Utiliser QGridLayout pour un meilleur alignement

        # nom des label pour afficher les conditions de la serre
        nom_label_temp = QLabel("Température:", conditions_group)
        nom_label_hum = QLabel("Humidité:", conditions_group)
        nom_label_co2 = QLabel("CO2:", conditions_group)

         # Labels pour afficher les valeurs des conditions (avec placeholders)
        self.label_valeur_temperature = QLabel("-- °C", conditions_group)
        self.label_valeur_humidite = QLabel("-- %", conditions_group)
        self.label_valeur_co2 = QLabel("-- ppm", conditions_group)

        # positionner les affichage de dconditions
        conditions_position.addWidget(nom_label_temp, 0, 0) # Ligne 0, Colonne 0
        conditions_position.addWidget(self.label_valeur_temperature, 0, 1)

        conditions_position.addWidget(nom_label_hum, 1, 0)
        conditions_position.addWidget(self.label_valeur_humidite, 1,1 )

        conditions_position.addWidget(nom_label_co2, 2, 0)
        conditions_position.addWidget(self.label_valeur_co2, 2, 1)

        main_position.addWidget(conditions_group)
        self.update_affichage_conditions()
        



   
   # ==================Méthode pour mettre à jour le texte des boutons=================
    def update_button_texts(self):
        self.button_leds.setText(f"Leds: {'ON' if self.leds_on else 'OFF'}")
        self.button_humidificateur.setText(f"Humidificateur: {'ON' if self.humidificateur_on else 'OFF'}")
        self.button_ventilation.setText(f"Ventilation: {'ON' if self.ventilation_on else 'OFF'}")

    #  Méthodes pour gérer les clics sur les boutons et afficher le bon message
    def changer_etat_leds(self):
        self.leds_on = not self.leds_on
        self.update_button_texts()
        message = "Leds allumées." if self.leds_on else "Leds éteintes."
        self.status_label.setText(message)

    def changer_etat_humidificateur(self):
        self.humidificateur_on = not self.humidificateur_on
        self.update_button_texts()
        message = "Humidificateur activé." if self.humidificateur_on else "Humidificateur désactivé."
        self.status_label.setText(message)

    def changer_etat_ventilation(self):
        self.ventilation_on = not self.ventilation_on
        self.update_button_texts()
        message = "Ventilation activée." if self.ventilation_on else "Ventilation désactivée."
        self.status_label.setText(message)

    # Méthode pour le mode automatique
    def basculer_mode_automatique(self):
        self.mode_automatique_active = not self.mode_automatique_active

        self.update_button_texts() # Met à jour le texte du bouton mode auto

        message = "Mode Automatique activé." if self.mode_automatique_active else "Mode Automatique désactivé."
        self.status_label.setText(message)
        # TODO: Appel API pour activer/désactiver le mode automatique sur le RPi

    # Méthode pour l'arret d'urgence
    def activer_arret_urgence(self):
        self.leds_on = False
        self.humidificateur_on = False
        self.ventilation_on = False
        self.mode_automatique_active = False

        self.update_button_texts() # Met à jour le texte des boutons

        message = "ARRÊT D'URGENCE ACTIVÉ ! Tous les systèmes désactivés."
        self.status_label.setText(message)
         # TODO: Appel API critique pour initier l'arrêt d'urgence sur le RPi.




    #=================== Afficher les condition de la serre ===================
    def update_affichage_conditions(self, temperature="", humidite="", co2=""):
        self.label_valeur_temperature.setText(f"{temperature:} °C")
        self.label_valeur_humidite.setText(f"{humidite:} %")
        self.label_valeur_co2.setText(f"{co2:} ppm")





# Pour tester cette fenêtre seule (si vous n'avez pas encore main.py ou base_window.py configuré)
if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication

    # Définition minimale de BaseWindow pour le test
    class BaseWindow(QWidget):
        DEFAULT_WINDOW_X = 300
        DEFAULT_WINDOW_Y = 300
        DEFAULT_WINDOW_WIDTH = 380 # Ajusté pour le contenu
        DEFAULT_WINDOW_HEIGHT = 280 # Ajusté pour le contenu
        def __init__(self, title="Application", parent=None):
            super().__init__(parent)
            self.setWindowTitle(title)
            self.setGeometry(BaseWindow.DEFAULT_WINDOW_X,
                             BaseWindow.DEFAULT_WINDOW_Y,
                             BaseWindow.DEFAULT_WINDOW_WIDTH,
                             BaseWindow.DEFAULT_WINDOW_HEIGHT)
            self.initSpecificUI() # Important d'appeler ceci
        def initSpecificUI(self):
            # Les classes filles doivent implémenter cela
            pass

    app = QApplication(sys.argv)
    main_window = ControlPanelWindow()
    main_window.show()
    # Exemple de mise à jour des conditions après un délai pour voir le changement
    # Dans une vraie application, cela viendrait de données réelles.
    from PyQt6.QtCore import QTimer
    QTimer.singleShot(2000, lambda: main_window.update_affichage_conditions(temperature=22.5655, humidite=58.2, co2=450))
    sys.exit(app.exec())



    def afficher_condition_serre(self):
        # Ici, vous pouvez ajouter la logique pour afficher les conditions de la serre
        # Par exemple, vous pouvez récupérer les données des capteurs et les afficher
        pass