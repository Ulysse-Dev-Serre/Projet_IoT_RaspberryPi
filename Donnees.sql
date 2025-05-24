-- La table de ma serre
CREATE TABLE sensor_data (
    timestamp TIMESTAMP,
    temperature FLOAT,
    humidity FLOAT,
    co2 FLOAT,
    humidifier_active BOOLEAN,
    ventilation_active BOOLEAN,
    leds_active BOOLEAN,
    humidifier_on_duration_seconds FLOAT,
    humidifier_off_duration_seconds FLOAT,
    ventilation_on_duration_seconds FLOAT,
    ventilation_off_duration_seconds FLOAT
);
-- visioner les donner et la table
SELECT * FROM sensor_data;

--Suprimer le contenue de la table 
DELETE FROM sensor_data;

-- Modifier la table pour supprimer la colonne id
ALTER TABLE sensor_data
DROP COLUMN id;