

import java.net.http.HttpClient;   //Pour faire des requêtes HTTP (comme requests en Python).
import java.net.http.HttpRequest;   
import java.net.http.HttpResponse; 

import java.net.URI;     //L’adresse du serveur Python (Raspberry Pi).

import com.google.gson.JsonObject;  
import com.google.gson.JsonParser;  // Pour parser le JSON reçu de l’API (comme json en Python)


 //Gère la communication avec l'API REST du Raspberry Pi.
public class Controller {
    private static final String API_URL = "http://10.0.0.216:5000";  // URL du Raspberry Pi

    
      //Récupère les données du capteur depuis l'API.
    public static Capteur getDonneesCapteur() throws Exception {
        try {
            HttpClient client = HttpClient.newHttpClient();
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(API_URL + "/status"))
                    .build();
            
             //Envoie la requête et récupère la réponse sous forme de texte (le JSON).
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
            String json = response.body(); //Extrait le corps de la réponse (le JSON brut).
            if (response.statusCode() != 200) { //Vérifie si la requête a réussi
                throw new Exception("Erreur API : " + response.statusCode());
            }
            
            //Transformer le JSON brut en données utilisables pour créer un objet Capteur
            JsonObject jsonObject = JsonParser.parseString(json).getAsJsonObject();
            // Vérifie que les champs temperature, hum, co2 existent
            if (!jsonObject.has("temperature") || !jsonObject.has("humidite") || !jsonObject.has("co2")) {
                throw new RuntimeException("JSON invalide : champs manquants");
            }
    
            // Récupérer les états supplémentaires
            // Pour les booléens (ex. : humidificateurActif) : Vérifie si le champ existe (has()) et récupère sa valeur (getAsBoolean())
            boolean humidificateurActif = jsonObject.has("humidificateur_actif") && jsonObject.get("humidificateur_actif").getAsBoolean();
            boolean ventilationActif = jsonObject.has("ventilation_actif") && jsonObject.get("ventilation_actif").getAsBoolean();
            boolean ledsActif = jsonObject.has("leds_actif") && jsonObject.get("leds_actif").getAsBoolean();
            String timestamp = jsonObject.has("transition") && !jsonObject.get("transition").isJsonNull() 
                ? jsonObject.get("transition").getAsJsonObject().get("timestamp").getAsString() : "N/A";
    
            return new Capteur(
                jsonObject.get("temperature").getAsDouble(), //Objectif : Retourner un objet Capteur avec toutes les données extraites.
                jsonObject.get("humidite").getAsDouble(),
                jsonObject.get("co2").getAsInt(),
                humidificateurActif,
                ventilationActif,
                ledsActif,
                timestamp
            );
        } catch (Exception e) {   //try/catch : Gère les erreurs (ex. : JSON mal formé, connexion échouée).
            throw new Exception("Erreur lors du parsing JSON : " + e.getMessage()); 
        }
    }

    /**
     * Envoie une commande à un appareil.
     * @param endpoint Chemin API (ex: "/control_ventilation")
     * @param activer true pour ON, false pour OFF
     */
    
    //Envoyer une commande à l’API (ex. : allumer la ventilation).
    public static void controlerAppareil(String endpoint, boolean activer) throws Exception {
        HttpClient client = HttpClient.newHttpClient();
        HttpRequest request = HttpRequest.newBuilder() //Construit une requête POST
                .uri(URI.create(API_URL + endpoint))   //uri(URI.create(API_URL + endpoint)) : Endpoint comme /control_ventilation
                .header("Content-Type", "application/x-www-form-urlencoded")  //header("Content-Type", ...) : Indique que les données sont au format "formulaire"
                .POST(HttpRequest.BodyPublishers.ofString("running=" + activer)) //POST(...) : Envoie running=true ou running=false dans le corps de la requête.
                .build();

        client.send(request, HttpResponse.BodyHandlers.ofString());  //Exécute la requête. La réponse n’est pas vérifiée ici (juste envoyée).
    }
}
