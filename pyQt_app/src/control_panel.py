from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout, QWidget#uniquement pour les teste 
from etat_serre import EtatSerre # Import de la classe EtatSerre

class ControlPanelWindow(QWidget): #hérite de QWidget
    def __init__(self, parent=None):
        super().__init__(parent) # Appel au constructeur de QWidget
        self.etat = EtatSerre() # Instance de la classe EtatSerre
        self._init_ui()

    def _init_ui(self): # États initiaux des appareils

        #                      CREATION DES CONTENEURS                         
        main_layout_vertical = QVBoxLayout(self) # 1 boite Vertical en bas
        layout_rangee_du_haut = QHBoxLayout() #  2 boîtes horizontal cote a cote en haut

        #------------------------BOITE DE CONTROLE-------------------------
        boite_controle = QFrame(self)                                
        boite_controle.setFrameShape(QFrame.Shape.StyledPanel)                # <-- Ajout de la bordure
        position_boutons_appareils = QVBoxLayout(boite_controle)              # <-- position_boutons_appareils
        #-------------------------BOITE DES CONDITIONS-------------------------
        boite_condition = QFrame(self)
        boite_condition.setFrameShape(QFrame.Shape.StyledPanel)
        conditions_position = QGridLayout(boite_condition) # 
        #-------------------------BOITE DES SEUILS-------------------------
        boite_config = QFrame(self)
        boite_config.setFrameShape(QFrame.Shape.StyledPanel) 
        layout_interne_seuils = QVBoxLayout(boite_config)
        layout_interne_seuils.addWidget(QLabel("Zone pour la configuration des seuils")) 
        boite_config.setMinimumHeight(100) # Pour qu'elle soit visible même vide



        # CONTENUE DE LA BOITE DE CONTROLE (ajouté à position_boutons_appareils)
        self.button_leds = QPushButton()
        self.button_leds.clicked.connect(self._changer_etat_leds)
        position_boutons_appareils.addWidget(self.button_leds)

        self.button_humidificateur = QPushButton()
        self.button_humidificateur.clicked.connect(self._changer_etat_humidificateur)
        position_boutons_appareils.addWidget(self.button_humidificateur)

        self.button_ventilation = QPushButton()
        self.button_ventilation.clicked.connect(self._changer_etat_ventilation)
        position_boutons_appareils.addWidget(self.button_ventilation)
                                                 #----------------------------
        self.status_label = QLabel("État des appareils")
        position_boutons_appareils.addWidget(self.status_label)

        self.button_mode_auto = QPushButton()
        self.button_mode_auto.clicked.connect(self._basculer_mode_automatique)
        position_boutons_appareils.addWidget(self.button_mode_auto)

        self.button_arret_urgence = QPushButton()   
        self.button_arret_urgence.clicked.connect(self._basculer_etat_urgence) 
        position_boutons_appareils.addWidget(self.button_arret_urgence)

        # CONTENUE DE LA BOITE DES CONDITIONS
        nom_label_temp = QLabel("Température:", boite_condition)
        nom_label_hum = QLabel("Humidité:", boite_condition)
        nom_label_co2 = QLabel("CO2:", boite_condition)

        self.label_valeur_temperature = QLabel("-- °C", boite_condition)
        self.label_valeur_humidite = QLabel("-- %", boite_condition)
        self.label_valeur_co2 = QLabel("-- ppm", boite_condition)
        
        conditions_position.addWidget(nom_label_temp, 0, 0)              #<---- positionner les affichages des conditions
        conditions_position.addWidget(self.label_valeur_temperature, 0, 1)
        conditions_position.addWidget(nom_label_hum, 1, 0)
        conditions_position.addWidget(self.label_valeur_humidite, 1,1 )
        conditions_position.addWidget(nom_label_co2, 2, 0)
        conditions_position.addWidget(self.label_valeur_co2, 2, 1)

        # CONTENUE DE LA BOITE DES SEUILS
        #blablabla
        #blablabla
        #blablabla


        # ASSEMBLAGE DES BOÎTES DANS LES LAYOUTS DE LA FENÊTRE
        layout_rangee_du_haut.addWidget(boite_controle)              #<--  deux premières boîtes au layout horizontal de la rangée du haut
        layout_rangee_du_haut.addWidget(boite_condition)

        main_layout_vertical.addLayout(layout_rangee_du_haut)        #<--  ajout de la rangée du haut au layout vertical principal
        main_layout_vertical.addWidget(boite_config)                 #<--  ajout de la boîte de configuration en dessous
        main_layout_vertical.addStretch(1)                           #<-- Ajoute un espace flexible en bas

        # Mettre à jour les textes initiaux des boutons/labels
        self._actualiser_toute_interface_depuis_modele()


        # --- Méthodes pour mettre à jour l'interface ---
    def _actualiser_toute_interface_depuis_modele(self):
        """Rafraîchit tous les éléments de l'UI basés sur l'état du modèle."""
        self._actualiser_textes_boutons()
        self._actualiser_affichage_conditions()
        
        # Gère l'affichage spécifique du status_label en cas d'urgence
        if self.etat.get_etat_urgence():
            self.status_label.setText("ARRÊT D'URGENCE ACTIF !")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            # Si on sort de l'urgence, et que le message d'urgence était affiché,
            # on met un message neutre. Sinon, on ne touche pas au message
            # qui a pu être mis par une autre action (ex: "Leds allumées").
            current_text = self.status_label.text()
            if "ARRÊT D'URGENCE ACTIF !" in current_text : 
                 self.status_label.setText("Système prêt.") 
            self.status_label.setStyleSheet("") # Réinitialise le style

    def _actualiser_textes_boutons(self):
        """Met à jour le texte des boutons en fonction de l'état du modèle."""
        self.button_leds.setText(f"Leds: {'ALLUMÉES' if self.etat.get_leds_etat() else 'ÉTEINTES'}")
        self.button_humidificateur.setText(f"Humidificateur: {'ACTIVÉ' if self.etat.get_humidificateur_etat() else 'DÉSACTIVÉ'}")
        self.button_ventilation.setText(f"Ventilation: {'ACTIVÉE' if self.etat.get_ventilation_etat() else 'DÉSACTIVÉE'}")
        self.button_mode_auto.setText(f"Mode Auto: {'ACTIF' if self.etat.get_mode_automatique() else 'INACTIF'}")
        
        if self.etat.get_etat_urgence():
            self.button_arret_urgence.setText("RÉARMER SYSTÈME")
            self.button_arret_urgence.setStyleSheet("background-color: #FFBF00; color: black; font-weight: bold;")
        else:
            self.button_arret_urgence.setText("ARRÊT D'URGENCE")
            self.button_arret_urgence.setStyleSheet("")

    def _actualiser_affichage_conditions(self):
        """Met à jour les labels des capteurs depuis le modèle."""
        self.label_valeur_temperature.setText(f"{self.etat.get_current_temp()} °C")
        self.label_valeur_humidite.setText(f"{self.etat.get_current_humidity()} %")
        self.label_valeur_co2.setText(f"{self.etat.get_current_co2()} ppm")

    # --- MÉTHODES DE GESTION DES ÉVÉNEMENTS (SLOTS) ---
    # Ce sont vos méthodes, elles sont bien structurées.
    # La principale modification est l'appel à _actualiser_toute_interface_depuis_modele()
    # à la fin de chaque méthode pour garantir la cohérence de l'UI.

    def _changer_etat_leds(self):
        etat_actuel = self.etat.get_leds_etat()
        nouvel_etat = not etat_actuel
        self.etat.set_leds_etat(nouvel_etat)
        # Le message de statut est mis à jour de manière conditionnelle
        if not self.etat.get_etat_urgence(): 
            self.status_label.setText(f"Leds {'allumées' if nouvel_etat else 'éteintes'}.")
        self._actualiser_toute_interface_depuis_modele()

    def _changer_etat_humidificateur(self):
        etat_actuel = self.etat.get_humidificateur_etat()
        nouvel_etat = not etat_actuel
        self.etat.set_humidificateur_etat(nouvel_etat)
        if not self.etat.get_etat_urgence():
            self.status_label.setText(f"Humidificateur {'activé' if nouvel_etat else 'désactivé'}.")
        self._actualiser_toute_interface_depuis_modele()

    def _changer_etat_ventilation(self):
        etat_actuel = self.etat.get_ventilation_etat()
        nouvel_etat = not etat_actuel
        self.etat.set_ventilation_etat(nouvel_etat)
        if not self.etat.get_etat_urgence():
            self.status_label.setText(f"Ventilation {'activée' if nouvel_etat else 'désactivée'}.")
        self._actualiser_toute_interface_depuis_modele()

    def _basculer_mode_automatique(self):
        try:
            etat_actuel = self.etat.get_mode_automatique()
            nouvel_etat = not etat_actuel
            self.etat.set_mode_automatique(nouvel_etat)
            if not self.etat.get_etat_urgence(): # Ne met à jour le statut que si pas en urgence
                self.status_label.setText(f"Mode Automatique {'activé' if nouvel_etat else 'désactivé'}.")
        except Exception as e:
            self.status_label.setText(f"Erreur mode auto: {e}")
            # Remplacer par logging.error() dans une version finale
            print(f"ERREUR UI: Erreur dans _basculer_mode_automatique: {e}") 
        self._actualiser_toute_interface_depuis_modele()

    # MODIFICATION : Renommage de votre méthode _activer_arret_urgence pour refléter la bascule
    def _basculer_etat_urgence(self): 
        """Bascule l'état d'urgence (active ou désactive)."""
        etat_urgence_actuel = self.etat.get_etat_urgence()
        self.etat.set_etat_urgence(not etat_urgence_actuel) # Inverse l'état d'urgence dans le modèle
        
        # Le message de statut est principalement géré par _actualiser_toute_interface_depuis_modele.
        # On peut ajouter un message spécifique si on vient de désactiver l'urgence.
        if not self.etat.get_etat_urgence() and etat_urgence_actuel: # Si on vient de désactiver l'urgence
             self.status_label.setText("Arrêt d'urgence désactivé. Système prêt.")

        self._actualiser_toute_interface_depuis_modele()

    # --- Méthode pour mise à jour externe des capteurs ---
    def mettre_a_jour_donnees_capteurs(self, temp, hum, co2):
        """Met à jour le modèle avec les nouvelles données des capteurs et rafraîchit l'affichage."""
        self.etat.set_current_temp(str(temp))
        self.etat.set_current_humidity(str(hum))
        self.etat.set_current_co2(str(co2))
        self._actualiser_affichage_conditions() # Rafraîchit seulement les labels des capteurs








