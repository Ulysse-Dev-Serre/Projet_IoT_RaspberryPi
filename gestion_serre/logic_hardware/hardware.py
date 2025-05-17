import lgpio
import time
import board
import busio
import adafruit_scd30

# Configuration des GPIO
LEDS = 27
VENTILATION = 22
FAN_HUMIDI = 26
BRUMISATEUR = 13

# Initialisation des broches GPIO et capteur
h = lgpio.gpiochip_open(0)
i2c = busio.I2C(board.SCL, board.SDA)
scd = adafruit_scd30.SCD30(i2c)

lgpio.gpio_claim_output(h, LEDS)
lgpio.gpio_claim_output(h, VENTILATION)
lgpio.gpio_claim_output(h, FAN_HUMIDI)
lgpio.gpio_claim_output(h, BRUMISATEUR)

# Initialisation des sorties (tout éteint par défaut)
lgpio.gpio_write(h, LEDS, 1)
lgpio.gpio_write(h, VENTILATION, 1)
lgpio.gpio_write(h, FAN_HUMIDI, 1)
lgpio.gpio_write(h, BRUMISATEUR, 1)

def lire_capteur():
    essais = 0
    while essais < 3:
        if scd.data_available:
            temperature = scd.temperature
            humidite = scd.relative_humidity
            co2 = scd.CO2
            if 0 <= humidite <= 100:
                return temperature, humidite, co2
        essais += 1
        time.sleep(2)
    return None, None, None

#-------------------------------------
def activer_leds():
    lgpio.gpio_write(h, LEDS, 0)

def desactiver_leds():
    lgpio.gpio_write(h, LEDS, 1)

#-----------------------------------------
def activer_humidificateur():
    lgpio.gpio_write(h, FAN_HUMIDI, 0)
    lgpio.gpio_write(h, BRUMISATEUR, 0)

def desactiver_humidificateur():
    lgpio.gpio_write(h, FAN_HUMIDI, 1)
    lgpio.gpio_write(h, BRUMISATEUR, 1)

#-------------------------------------------
def activer_ventilation():
    lgpio.gpio_write(h, VENTILATION, 0)
    

def desactiver_ventilation():
    lgpio.gpio_write(h, VENTILATION, 1)

#-----------------------------------------

def cleanup():
    desactiver_humidificateur()
    desactiver_ventilation()  # Ajoute ça
    desactiver_leds()
    lgpio.gpiochip_close(h)
    