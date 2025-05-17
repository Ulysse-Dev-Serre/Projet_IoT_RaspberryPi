# serre_logic.py: Contrôle logique de la serre connectée
# Gère les capteurs, appareils (humidificateur, ventilation, LEDs), enregistrement des données
# Optimisé avec buffer temporel, gestion d'erreurs, et tests facilités via commentaires

import time
from datetime import datetime
import psycopg2
from psycopg2 import pool
import logging


# Configuration de la journalisation pour enregistrer succès/erreurs
logging.basicConfig(filename='serre.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import pour la version réelle (Raspberry Pi)
from logic_hardware import hardware
# Import pour la version test (données aléatoires, PC)
#from logic_hardware import hardware_mock as hardware

class SerreController:
    def __init__(self, interval=60):
        # Initialisation des paramètres de la serre
        self.interval = interval  # Intervalle de mise à jour (60s par défaut)

        self.temperature = None  # Température actuelle (°C)
        self.humidite = None  # Humidité actuelle (%)
        self.co2 = None  # CO2 actuel (ppm)

        self.manual_humidificateur = False  # Mode manuel humidificateur
        self.manual_ventilation = False  # Mode manuel ventilation
        self.manual_leds = False  # Mode manuel LEDs

        self.running_leds = False  # État manuel LEDs
        self.dernier_etat_leds = False  # Dernier état LEDs
        self.HEURE_DEBUT_LEDS = 8  # Heure début LEDs (8h)
        self.HEURE_FIN_LEDS = 20  # Heure fin LEDs (20h)

        self.running_humidificateur = False  # État manuel humidificateur
        self.brumisateur_on_time = None  # Timestamp début humidificateur
        self.brumisateur_off_time = None  # Timestamp fin humidificateur
        self.dernier_etat_brumisateur = False  # Dernier état humidificateur

        self.last_session_done = False  # Session spéciale 21h30-21h35 faite ?

        self.SEUIL_ON = 75.0  # Seuil humidité ON (%)
        self.SEUIL_OFF = 84.9  # Seuil humidité OFF (%)

        self.running_ventilation = False  # État manuel ventilation
        self.ventilation_on_time = None  # Timestamp début ventilation
        self.ventilation_off_time = None  # Timestamp fin ventilation
        self.dernier_etat_ventilation = False  # Dernier état ventilation
        self.SEUIL_CO2_MAX = 2000.0  # Seuil CO2 max (ppm)

        self.transition_info = None  # Infos transitions appareils

        self.data_buffer = []  # Buffer pour stocker données avant insertion
        self.last_flush_time = time.time()  # Dernière insertion buffer
        self.flush_interval = 300  # Intervalle vidage buffer (5 min)





        # Connexion à la base de données (prod)
       # self.db_pool = psycopg2.pool.SimpleConnectionPool(
        #    1, 5,  # Réduit maxconn pour optimiser
        #    database="serre_connectee",
        #    user="ulysse",
        #    password="1234",
        #    host="localhost",
        #    port="5432"
        #)

        # Connexion à la base de test (commenter/décommenter pour basculer)
        self.db_pool = psycopg2.pool.SimpleConnectionPool(
        1, 5,
            database="serre_test",
            user="ulysse",
            password="1234",
            host="10.0.0.216",
            port="5432",
            client_encoding="UTF8"  # Forcer encodage UTF-8
            )
        
        import threading
        self.fast_read_thread = threading.Thread(target=self.fast_read_sensors, daemon=True)
        self.fast_read_thread.start()  # Démarre le thread de lecture rapide


#========================================================
    def read_sensors(self):
        # Lit les données des capteurs avec réessais
        retries = 3
        for attempt in range(retries):
            try:
                self.temperature, self.humidite, self.co2 = hardware.lire_capteur()
                # Vérifie si données valides (non None)
                if all(x is not None for x in (self.temperature, self.humidite, self.co2)):
                    logging.info(f"Sensors read: temp={self.temperature}, hum={self.humidite}, co2={self.co2}")
                    return True
                logging.warning(f"Échec lecture capteurs (tentative {attempt + 1}/{retries})")
                time.sleep(1)
            except Exception as e:
                logging.error(f"Erreur lecture capteurs (tentative {attempt + 1}/{retries}) : {e}")
                time.sleep(1)
        logging.critical("Échec définitif lecture capteurs")
        return False
    #----------------------------------------------------------------------
    # Lit les capteurs pour les données en temps réel
    def fast_read_sensors(self):
    
        while True:
            if self.read_sensors():
                logging.info(f"Fast read: temp={self.temperature}, hum={self.humidite}, co2={self.co2}")
                error_count = 0
            else:
                error_count +=1
                if error_count >= 3:
                    logging.warning("Erreur répétée dans la lecture des capteurs")
            time.sleep(15)  # Mise à jour toutes les 15 secondes
    

    #========================================================
        # Centralise calcul des durées allumage/extinction
        # Retourne dictionnaire avec durées arrondies à 1 décimale
    def _calculate_durations(self):
        return {
            "humidifier_on_duration": round(
                (time.time() - self.brumisateur_on_time) if self.brumisateur_on_time and self.dernier_etat_brumisateur else 0, 1
            ),
            "humidifier_off_duration": round(
                (time.time() - self.brumisateur_off_time) if self.brumisateur_off_time and not self.dernier_etat_brumisateur else 0, 1
            ),
            "ventilation_on_duration": round(
                (time.time() - self.ventilation_on_time) if self.ventilation_on_time and self.dernier_etat_ventilation else 0, 1
            ),
            "ventilation_off_duration": round(
                (time.time() - self.ventilation_off_time) if self.ventilation_off_time and not self.dernier_etat_ventilation else 0, 1
            )
        }
    
    #=======================================================
    def control_leds(self):
        # Contrôle LEDs (manuel ou auto basé sur plage horaire)
        now = datetime.now().replace(microsecond=0)  # Enlève millisecondes
        heure_actuelle = now.hour
        if self.manual_leds:
            leds_actif = self.running_leds  # Mode manuel
        else:
            # Mode auto : LEDs ON entre 8h et 20h
            leds_actif = self.HEURE_DEBUT_LEDS <= heure_actuelle < self.HEURE_FIN_LEDS
        # Active/désactive LEDs si changement d'état
        if leds_actif and not self.dernier_etat_leds:
            hardware.activer_leds()
        elif not leds_actif and self.dernier_etat_leds:
            hardware.desactiver_leds()
        self.dernier_etat_leds = leds_actif
        self._save_to_db(leds_actif)  # Enregistre état

#=======================================================
    def control_humidifier(self):
        # Contrôle humidificateur (manuel ou auto basé sur humidité/plage horaire)
        if self.humidite is None:
            return
        now = datetime.now().replace(microsecond=0)  # Enlève millisecondes
        heure_actuelle = now.hour
        minute_actuelle = now.minute
        hors_plage_horaire = 22 <= heure_actuelle or heure_actuelle < 8  # Nuit
        est_21h30 = heure_actuelle == 21 and 30 <= minute_actuelle < 35  # Session spéciale
        # Réinitialise session spéciale après 8h
        if heure_actuelle >= 8 and self.last_session_done:
            self.last_session_done = False
        if self.manual_humidificateur:
            humidificateur_actif = self.running_humidificateur  # Mode manuel
        else:
            # Mode auto
            if hors_plage_horaire:
                humidificateur_actif = False  # OFF la nuit
            elif est_21h30 and not self.last_session_done:
                humidificateur_actif = True  # ON à 21h30-21h35
            else:
                # Basé sur seuils humidité
                if self.humidite < self.SEUIL_ON:
                    humidificateur_actif = True
                elif self.humidite >= self.SEUIL_OFF:
                    humidificateur_actif = False
                    if heure_actuelle == 21 and minute_actuelle >= 30:
                        self.last_session_done = True
                else:
                    humidificateur_actif = self.dernier_etat_brumisateur  # Maintient état
        # Gestion transitions
        if humidificateur_actif and not self.dernier_etat_brumisateur:
            self.brumisateur_on_time = time.time()
            hardware.activer_humidificateur()
            if self.brumisateur_off_time:
                duree_eteint = self.brumisateur_on_time - self.brumisateur_off_time
                duree_eteint_min = duree_eteint / 60
                self.transition_info = {
                    "type": "humidificateur_actif",
                    "duree_eteint_min": duree_eteint_min,
                    "humidite": self.humidite,
                    "temperature": self.temperature,
                    "co2": self.co2,
                    "timestamp": now.strftime('%H:%M:%S')
                }
            self._save_to_db(humidificateur_actif, duree_eteint=duree_eteint if 'duree_eteint' in locals() else None)
        elif not humidificateur_actif and self.dernier_etat_brumisateur:
            self.brumisateur_off_time = time.time()
            hardware.desactiver_humidificateur()
            if self.brumisateur_on_time:
                duree_allume = self.brumisateur_off_time - self.brumisateur_on_time
                duree_allume_min = duree_allume / 60
                self.transition_info = {
                    "type": "humidificateur_desactiver",
                    "duree_allume_min": duree_allume_min,
                    "humidite": self.humidite,
                    "temperature": self.temperature,
                    "co2": self.co2,
                    "timestamp": now.strftime('%H:%M:%S')
                }
            self._save_to_db(humidificateur_actif, duree_allume=duree_allume if 'duree_allume' in locals() else None)
        else:
            self._save_to_db(humidificateur_actif)
        self.dernier_etat_brumisateur = humidificateur_actif

    #=======================================================
    def control_ventilation(self):
        # Contrôle ventilation (manuel ou auto basé sur CO2/plage horaire)
        if self.co2 is None:
            return
        now = datetime.now().replace(microsecond=0)  # Enlève millisecondes
        heure_actuelle = now.hour
        hors_plage_horaire = 22 <= heure_actuelle or heure_actuelle < 8
        if self.manual_ventilation:
            ventilation_actif = self.running_ventilation
        else:
            # Mode auto : ON si CO2 > seuil et pas la nuit
            ventilation_actif = not hors_plage_horaire and self.co2 > self.SEUIL_CO2_MAX
        # Gestion transitions
        if ventilation_actif and not self.dernier_etat_ventilation:
            self.ventilation_on_time = time.time()
            hardware.activer_ventilation()
            if self.ventilation_off_time:
                duree_eteint = self.ventilation_on_time - self.ventilation_off_time
                duree_eteint_min = duree_eteint / 60
                self.transition_info = {
                    "type": "ventilation_actif",
                    "duree_eteint_min": duree_eteint_min,
                    "humidite": self.humidite,
                    "temperature": self.temperature,
                    "co2": self.co2,
                    "timestamp": now.strftime('%H:%M:%S')
                }
            self._save_to_db(ventilation_actif, duree_eteint=duree_eteint if 'duree_eteint' in locals() else None)
        elif not ventilation_actif and self.dernier_etat_ventilation:
            self.ventilation_off_time = time.time()
            hardware.desactiver_ventilation()
            if self.ventilation_on_time:
                duree_allume = self.ventilation_off_time - self.ventilation_on_time
                duree_allume_min = duree_allume / 60
                self.transition_info = {
                    "type": "ventilation_desactiver",
                    "duree_allume_min": duree_allume_min,
                    "humidite": self.humidite,
                    "temperature": self.temperature,
                    "co2": self.co2,
                    "timestamp": now.strftime('%H:%M:%S')
                }
            self._save_to_db(ventilation_actif, duree_allume=duree_allume if 'duree_allume' in locals() else None)
        else:
            self._save_to_db(ventilation_actif)
        self.dernier_etat_ventilation = ventilation_actif

#=======================================================
    # Enregistre données dans la base de données
    def _save_to_db(self, etat_actif, duree_allume=None, duree_eteint=None):
        # Ajoute données au buffer pour enregistrement
        durations = self._calculate_durations()

        # Tronquer les millisecondes du timestamp
        timestamp = datetime.now().replace(microsecond=0)  # <===================


        self.data_buffer.append((
            timestamp,   # <===============
            round(self.temperature, 1) if self.temperature is not None else None,
            round(self.humidite, 1) if self.humidite is not None else None,
            round(self.co2, 1) if self.co2 is not None else None,
            self.dernier_etat_brumisateur,
            self.dernier_etat_ventilation,
            self.dernier_etat_leds,
            round(duree_allume, 1) if duree_allume is not None else None,
            round(duree_eteint, 1) if duree_eteint is not None else None,
            durations["ventilation_on_duration"],
            durations["ventilation_off_duration"]
        ))
        # Vérifie ou on en est rendu dans le buffer
        logging.info(f"Donnée ajoutée au buffer, taille actuelle : {len(self.data_buffer)}")
        # Vérifie si intervalle de vidage buffer atteint
        if len(self.data_buffer) >= 10:
            self._flush_buffer()


#=======================================================
    # Vide le buffer dans la base de données
    # j'utilise le buffer pour éviter de faire trop d'inserts dans la base de données
    def _flush_buffer(self):
        # Vide le buffer dans la base avec réessais
        if not self.data_buffer:
            return
        conn = None
        retries = 3
        for attempt in range(retries):
            try:
                conn = self.db_pool.getconn()
                cur = conn.cursor()
                cur.executemany(
                    """
                    INSERT INTO sensor_data (
                        timestamp, temperature, humidity, co2, 
                        humidifier_active, ventilation_active, leds_active,
                        humidifier_on_duration, humidifier_off_duration,
                        ventilation_on_duration, ventilation_off_duration
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    self.data_buffer
                )
                conn.commit()
                cur.close()
                logging.info(f"Inserted {len(self.data_buffer)} records into sensor_data")
                self.data_buffer.clear()
                self.last_flush_time = time.time()  # Met à jour temps dernière insertion
                break
            except Exception as e:
                logging.error(f"Échec enregistrement (tentative {attempt + 1}/{retries}) : {e}")
                if attempt < retries - 1:
                    time.sleep(1)
                else:
                    logging.critical("Échec définitif enregistrement données")
                    # TODO: Ajouter alerte (ex. email/push) pour échec critique
            finally:
                if conn:
                    self.db_pool.putconn(conn)

    #=======================================================
    # Méthode de mise à jour principale
    def update(self):
        # Met à jour capteurs et appareils, force vidage buffer
        if self.read_sensors():
            self.control_humidifier()
            self.control_ventilation()
            self.control_leds()
        else:  # Ajoute une donnée vide au buffer en cas d'échec
            self.data_buffer.append((
                datetime.now(),
                None, None, None, # Température, humidité, CO2
                self.dernier_etat_brumisateur,
                self.dernier_etat_ventilation,
                self.dernier_etat_leds,
                None, None, # Durées humidificateur
                0,0 # Durées ventilation
            ))
            logging.info(f"Donnée vide ajoutée au buffer après échec lecture, taille : {len(self.data_buffer)}")
            if len(self.data_buffer) >= 10:
                self._flush_buffer()

            

    def run(self):
        # Boucle principale de mise à jour
        while True:
            self.update()
            time.sleep(self.interval)

    def get_status(self):
        # Retourne état actuel pour affichage temps réel
        durations = self._calculate_durations()
        status = {
            "timestamp": datetime.now().replace(microsecond=0).strftime('%Y-%m-%d %H:%M:%S'),  # Ajout timestamp
            "temperature": self.temperature if self.temperature is not None else "N/A",
            "humidite": self.humidite if self.humidite is not None else "N/A",
            "co2": self.co2 if self.co2 is not None else "N/A",
            "humidificateur_actif": self.dernier_etat_brumisateur,
            "ventilation_actif": self.dernier_etat_ventilation,
            "leds_actif": self.dernier_etat_leds,
            "duree_allume_brumisateur": durations["humidifier_on_duration"],
            "duree_eteint_brumisateur": durations["humidifier_off_duration"],
            "duree_allume_ventilation": durations["ventilation_on_duration"],
            "duree_eteint_ventilation": durations["ventilation_off_duration"],
            "transition": self.transition_info
        }
        self.transition_info = None  # Réinitialise après usage
        return status
    
    
# Méthode pour contrôle manuel (facultatif, pour une future API)
"""
    def set_leds_manual(self, state: bool):
        #ctive ou désactive manuellement les LEDs.
        self.running_leds = state
        if state:
            hardware.activer_leds()
        else:
            hardware.desactiver_leds()
        self.dernier_etat_leds = state"""
    
    