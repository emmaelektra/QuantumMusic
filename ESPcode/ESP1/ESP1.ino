#include <WiFi.h>
#include <ArduinoJson.h>
#include <FastLED.h>

#define SSID "BosonSamplerWiFi"
#define PASSWORD "QuantumTech2025"
#define LAPTOP_IP "192.168.4.2"  // Laptop's static IP

// Static IP Configuration for ESP1
IPAddress staticIP(192,168,4,3);
IPAddress gateway(192,168,4,1);
IPAddress subnet(255,255,255,0);

#define LED_PIN1 5
#define LED_PIN2 26
#define LED_PIN3 18
#define LED_PIN4 25
#define POT_PIN 34

#define NUM_LEDS1 20  
#define NUM_LEDS2 20  
#define NUM_LEDS3 20  
#define NUM_LEDS4 20  

CRGB leds1[NUM_LEDS3];
CRGB leds2[NUM_LEDS4];
CRGB leds3[NUM_LEDS3];
CRGB leds4[NUM_LEDS4];

WiFiClient client;
WiFiServer server(80);  // ESP acts as a TCP server
uint8_t brightness1 = 0;
uint8_t brightness2 = 0;
uint8_t brightness3 = 0;
uint8_t brightness4 = 0;
bool entanglement = false;
unsigned long lastPotChange = 0;
static int lastPotValue = -1;

// Receive brightness updates
void getDataFromLaptop() {
    WiFiClient clientReceive = server.available();
    if (clientReceive) {
        if (clientReceive.connected()) {
            String response = clientReceive.readStringUntil('\n');
            StaticJsonDocument<200> doc;
            DeserializationError error = deserializeJson(doc, response);

            if (!error) {
                brightness1 = doc["strip_1_bright"];
                brightness2 = doc["strip_2_bright"];
                brightness3 = doc["strip_3_bright"];
                brightness4 = doc["strip_4_bright"];
                entanglement = doc["Entanglement"];
                Serial.print("[ESP1] Received Brightness - Strip1: ");
                Serial.print(brightness1);
                Serial.print(", Strip2: ");
                Serial.println(brightness2);
                Serial.print(", Strip3: ");
                Serial.println(brightness3);
                Serial.print(", Strip4: ");
                Serial.println(brightness4);
                // Update leds
                updateLEDs();
            }
        }
        clientReceive.stop();
    }
}

// Send potentiometer data to the laptop
void sendDataToLaptop(int potValue) {
    if (WiFi.status() == WL_CONNECTED) {
        WiFiClient laptop;
        if (laptop.connect(LAPTOP_IP, 80)) {  
            StaticJsonDocument<200> doc;
            doc["esp_id"] = 1;
            doc["pot_value"] = potValue;
            String jsonString;
            serializeJson(doc, jsonString);
            laptop.println(jsonString);
            laptop.stop();
        }
    }
}

// Update LED brightness
void updateLEDs() {
    for (int i = 0; i < NUM_LEDS1; i++) {
        leds1[i] = CRGB::Red;
        leds1[i].nscale8(brightness1);
    }
    for (int i = 0; i < NUM_LEDS2; i++) {
        leds2[i] = CRGB::Red;
        leds2[i].nscale8(brightness2);
    }
    for (int i = 0; i < NUM_LEDS3; i++) {
        leds3[i] = CRGB::Red;
        leds3[i].nscale8(brightness3);
    }
    for (int i = 0; i < NUM_LEDS4; i++) {
        leds4[i] = CRGB::Red;
        leds4[i].nscale8(brightness4);
    }
    FastLED.show();
}

void setup() {
    Serial.begin(115200);
    
    // Set static IP and connect to Wi-Fi
    WiFi.config(staticIP, gateway, subnet);
    WiFi.begin(SSID, PASSWORD);

    int timeout = 0;
    while (WiFi.status() != WL_CONNECTED && timeout < 20) {  
        delay(100);
        timeout++;
        Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n[ESP1] Connected to Wi-Fi.");
    } else {
        Serial.println("\n[ESP1] Failed to connect to Wi-Fi.");
    }

    server.begin();  // Start the server to listen for brightness updates

    FastLED.addLeds<WS2812B, LED_PIN1, GRB>(leds1, NUM_LEDS1);
    FastLED.addLeds<WS2812B, LED_PIN2, GRB>(leds2, NUM_LEDS2);
    FastLED.addLeds<WS2812B, LED_PIN3, GRB>(leds3, NUM_LEDS3);
    FastLED.addLeds<WS2812B, LED_PIN4, GRB>(leds4, NUM_LEDS4);
}

void loop() {
    Serial.println("[ESP1] Loop Running...");
    
    // Listen for brightness updates from laptop
    getDataFromLaptop();

    // Send potentiometer data only when it changes significantly
    int potValue = analogRead(POT_PIN);
    if (abs(potValue - lastPotValue) > 60) {  
        Serial.print("[ESP1] Potentiometer Value: ");
        Serial.println(potValue);
        lastPotChange = millis();
        lastPotValue = potValue;
        sendDataToLaptop(potValue);
    }

    delay(50);  // Small delay to prevent serial spam
}
