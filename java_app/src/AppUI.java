import javafx.application.Application;
import javafx.scene.Scene;
import javafx.scene.control.*;
import javafx.scene.layout.VBox;
import javafx.stage.Stage;
import java.text.DecimalFormat;



public class AppUI extends Application {
    // Labels pour les affichages
    private Label tempLabel = new Label("Température: --°C");
    private Label humLabel = new Label("Humidité: --%");
    private Label co2Label = new Label("CO2: -- ppm");
    private Label humStatusLabel = new Label("Humidificateur: Désactivé");
    private Label ventStatusLabel = new Label("Ventilation: Désactivé");
    private Label ledsStatusLabel = new Label("LEDs: Désactivées");
    private Label lastUpdateLabel = new Label("Dernière mise à jour: N/A");

    // Boutons pour chaque appareil
    private Button btnHumidifier = new Button("Activer Humidificateur");
    private Button btnVentilation = new Button("Activer Ventilation");
    private Button btnLeds = new Button("Activer LEDs");
    private Button btnEmergencyStop = new Button("Arrêt d’urgence");
    private Button btnAutoMode = new Button("Retour au mode automatique");

    // Formatage des nombres
    private DecimalFormat oneDecimal = new DecimalFormat("#.#");
    

    @Override
    public void start(Stage stage) {
        // Layout
        VBox root = new VBox(10, tempLabel, humLabel, co2Label, humStatusLabel, ventStatusLabel, 
                            ledsStatusLabel, lastUpdateLabel, btnHumidifier, btnVentilation, 
                            btnLeds, btnEmergencyStop, btnAutoMode);

        // Style du de la page
        Scene scene = new Scene(root, 400, 500);
        scene.getStylesheets().add(getClass().getResource("/style/styles.css").toExternalForm());

        // Action des boutons avec toggle
        btnHumidifier.setOnAction(e -> toggleDevice("/control_humidifier", btnHumidifier, humStatusLabel, "Humidificateur"));
        btnVentilation.setOnAction(e -> toggleDevice("/control_ventilation", btnVentilation, ventStatusLabel, "Ventilation"));
        btnLeds.setOnAction(e -> toggleDevice("/control_leds", btnLeds, ledsStatusLabel, "LEDs"));

        // Bouton arrêt d’urgence
        btnEmergencyStop.setOnAction(e -> {
            try {
                Controller.controlerAppareil("/stop", false); // Pas de "running" ici, adapté au HTML
                showAlert(Alert.AlertType.INFORMATION, "Arrêt d’urgence activé");
            } catch (Exception ex) {
                showAlert(Alert.AlertType.ERROR, "Erreur : " + ex.getMessage());
            }
        });

        // Bouton mode automatique
        btnAutoMode.setOnAction(e -> {
            try {
                Controller.controlerAppareil("/auto_mode", false); // Pas de "running" ici
                showAlert(Alert.AlertType.INFORMATION, "Mode automatique activé");
            } catch (Exception ex) {
                showAlert(Alert.AlertType.ERROR, "Erreur : " + ex.getMessage());
            }
        });

        // Style des boutons
        btnEmergencyStop.setStyle("-fx-background-color: red; -fx-text-fill: white;");

        // Afficher la fenêtre
        stage.setTitle("Serre à Champignons");
        stage.setScene(scene);
        stage.show();

        // Rafraîchir les données toutes les 5 secondes
        new Thread(() -> {
            while (true) {
                try {
                    Capteur capteur = Controller.getDonneesCapteur();
                    javafx.application.Platform.runLater(() -> updateUI(capteur));
                    Thread.sleep(5000);
                } catch (Exception ex) {
                    javafx.application.Platform.runLater(() -> 
                        showAlert(Alert.AlertType.ERROR, "Erreur capteur : " + ex.getMessage()));
                }
            }
        }).start();
    }

    // Méthode pour gérer le toggle des appareils
    private void toggleDevice(String endpoint, Button button, Label statusLabel, String deviceName) {
        try {
            boolean activer = button.getText().startsWith("Activer");
            Controller.controlerAppareil(endpoint, activer);
            button.setText(activer ? "Désactiver " + deviceName : "Activer " + deviceName);
            statusLabel.setText(deviceName + ": " + (activer ? "Actif" : "Désactivé"));
        } catch (Exception ex) {
            showAlert(Alert.AlertType.ERROR, "Erreur : " + ex.getMessage());
        }
    }

    // Mise à jour de l’interface avec les données du capteur
    private void updateUI(Capteur capteur) {
        tempLabel.setText("Température: " + oneDecimal.format(capteur.getTemperature()) + "°C");
        humLabel.setText("Humidité: " + oneDecimal.format(capteur.getHumidite()) + "%");
        co2Label.setText("CO2: " + capteur.getCo2() + " ppm");
        // Les états des appareils ne sont pas dans Capteur pour l’instant, à adapter si backend change
    }

    // Afficher une alerte
    private void showAlert(Alert.AlertType type, String message) {
        Alert alert = new Alert(type, message);
        alert.showAndWait();
    }
}
