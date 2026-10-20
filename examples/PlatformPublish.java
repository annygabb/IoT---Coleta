import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.Instant;
import java.util.UUID;

public class PlatformPublish {
    public static void main(String[] args) throws Exception {
        String body = "{\"versao\":\"1.0\",\"id_mensagem\":\"" + UUID.randomUUID()
            + "\",\"tipo\":\"telemetria\",\"dispositivo\":\"sensor-BIN-01\",\"timestamp\":\""
            + Instant.now().toString().replaceAll("(\\.\\d{6})\\d+Z$", "$1Z")
            + "\",\"medidas\":[{\"grandeza\":\"nivel_enchimento\",\"valor\":65,\"unidade\":\"%\"}]}";
        HttpRequest request = HttpRequest.newBuilder(URI.create("http://127.0.0.1:8000/api/v1/ingestao"))
            .timeout(Duration.ofSeconds(5)).header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(body)).build();
        HttpResponse<String> response = HttpClient.newHttpClient().send(request, HttpResponse.BodyHandlers.ofString());
        System.out.println(response.statusCode() + " " + response.body());
        if(response.statusCode()!=202)throw new IllegalStateException("Ingestão recusada");
    }
}
