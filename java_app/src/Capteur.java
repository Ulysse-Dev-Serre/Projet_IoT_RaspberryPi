/*: Cette classe représente les données reçues de tes capteurs via l’API Python 
    (température, humidité, CO2, états des appareils, timestamp). */


public class Capteur {
    private double temperature;
    private double humidite;
    private int co2;
    private boolean humidificateurActif;
    private boolean ventilationActif;
    private boolean ledsActif;
    private String timestamp;

    public Capteur(double temperature, double humidite, int co2, boolean humidificateurActif, 
                   boolean ventilationActif, boolean ledsActif, String timestamp) {
        this.temperature = temperature;
        this.humidite = humidite;
        this.co2 = co2;
        this.humidificateurActif = humidificateurActif;
        this.ventilationActif = ventilationActif;
        this.ledsActif = ledsActif;
        this.timestamp = timestamp;
    }

    // Getters
    public double getTemperature() { return temperature; }
    public double getHumidite() { return humidite; }
    public int getCo2() { return co2; }
    public boolean isHumidificateurActif() { return humidificateurActif; }
    public boolean isVentilationActif() { return ventilationActif; }
    public boolean isLedsActif() { return ledsActif; }
    public String getTimestamp() { return timestamp; }
}


 
