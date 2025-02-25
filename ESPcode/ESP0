#include <ESP8266WiFi.h>

#define SSID "BosonSamplerWiFi"
#define PASSWORD "QuantumTech2025"

void setup() {
    Serial.begin(115200);
    WiFi.softAP(SSID, PASSWORD, 1, 0, 8);  // Max 8 clients
    Serial.print("ESP8266 Wi-Fi Started! IP Address: ");
    Serial.println(WiFi.softAPIP());
}

void loop() {
    // Do nothing, just keep the Wi-Fi running
}
