CREATE TABLE sensor_data (
    timestamp TIMESTAMP,
    temperature FLOAT,
    humidity FLOAT,
    co2 FLOAT,
    humidifier_active BOOLEAN,
    ventilation_active BOOLEAN,
    leds_active BOOLEAN,
    humidifier_on_duration FLOAT,
    humidifier_off_duration FLOAT,
    ventilation_on_duration FLOAT,
    ventilation_off_duration FLOAT
);

SELECT * FROM sensor_data;
DELETE FROM sensor_data;