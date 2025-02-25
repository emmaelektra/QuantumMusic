#include <WiFi.h>
#include <ArduinoJson.h>
#include <FastLED.h>

#define SSID "BosonSamplerWiFi"
#define PASSWORD "QuantumTech2025"
#define LAPTOP_IP "192.168.4.2"  // Laptop's static IP

// Static IP Configuration for ESP2
IPAddress staticIP(192,168,4,4);
IPAddress gateway(192,168,4,1);
IPAddress subnet(255,255,255,0);

// ESP2 LED Configuration
#define LED_PIN4 5
#define LED_PIN3 26
#define LED_PIN2 18
#define LED_PIN1 33
#define POT_PIN 34  // ESP2's own potentiometer

#define NUM_LEDS1 200  
#define NUM_LEDS2 200  
#define NUM_LEDS3 100  
#define NUM_LEDS4 400  

CRGB leds1[NUM_LEDS1];
CRGB leds2[NUM_LEDS2];
CRGB leds3[NUM_LEDS3];
CRGB leds4[NUM_LEDS4];

WiFiClient client;
unsigned long lastPotChange = 0;
unsigned long lastReceiveCheck = 0;
uint8_t brightness3 = 0;
uint8_t brightness4 = 0;

// Store last potentiometer value
static int lastPotValue = -1;
bool isFading = false;

// Function to send potentiometer data to the laptop
void sendDataToLaptop(int potValue) {
    if (WiFi.status() == WL_CONNECTED) {
        WiFiClient laptop;
        if (laptop.connect(LAPTOP_IP, 80)) {  
            StaticJsonDocument<200> doc;
            doc["esp_id"] = 2;  // ESP2 Identifier
            doc["pot_value"] = potValue;
            String jsonString;
            serializeJson(doc, jsonString);
            laptop.println(jsonString);
            laptop.stop();
            Serial.println("[ESP2] Sent Potentiometer Value to Laptop.");
        } else {
            Serial.println("[ESP2] Failed to connect to Laptop.");
        }
    }
}

// Function to request brightness updates
void requestBrightness() {
    if (WiFi.status() == WL_CONNECTED) {
        WiFiClient clientReceive;
        if (clientReceive.connect(LAPTOP_IP, 80)) {
            clientReceive.println("{\"esp_id\": 2, \"request\": \"brightness\"}");

            unsigned long startTime = millis();
            while (!clientReceive.available() && millis() - startTime < 10) {
                // Wait max 10ms for data
            }

            if (clientReceive.available()) {
                String response = clientReceive.readStringUntil('\n');
                StaticJsonDocument<200> doc;
                DeserializationError error = deserializeJson(doc, response);

                if (!error) {
                    brightness3 = doc["brightness3"];
                    brightness4 = doc["brightness4"];
                    Serial.print("[ESP2] Received Brightness: ");
                    Serial.print(brightness3);
                    Serial.print(", ");
                    Serial.println(brightness4);
                } else {
                    Serial.println("[ESP2] Failed to parse brightness data.");
                }
            } else {
                Serial.println("[ESP2] No brightness data received.");
            }
            clientReceive.stop();
        } else {
            Serial.println("[ESP2] Failed to connect to laptop for brightness request.");
        }
    }
}

// Function to update LED brightness
void updateLEDs() {
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
        delay(100);  // Reduced delay for faster connection attempt
        timeout++;
        Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n[ESP2] Connected to Wi-Fi. IP: " + WiFi.localIP().toString());
    } else {
        Serial.println("\n[ESP2] Failed to connect to Wi-Fi.");
    }

    FastLED.addLeds<WS2812B, LED_PIN1, GRB>(leds1, NUM_LEDS1);
    FastLED.addLeds<WS2812B, LED_PIN2, GRB>(leds2, NUM_LEDS2);
    FastLED.addLeds<WS2812B, LED_PIN3, GRB>(leds3, NUM_LEDS3);
    FastLED.addLeds<WS2812B, LED_PIN4, GRB>(leds4, NUM_LEDS4);
}

void loop() {
    unsigned long currentMillis = millis();

    Serial.println("[ESP2] Loop Running...");

    // **ESP2's Potentiometer Data**
    int potValue = analogRead(POT_PIN);
    Serial.print("[ESP2] Potentiometer Value: ");
    Serial.println(potValue);

    if (abs(potValue - lastPotValue) > 60) {  
        lastPotChange = currentMillis;
        lastPotValue = potValue;
        isFading = false;

        Serial.println("[ESP2] Sending Pot Value to Laptop...");
        sendDataToLaptop(potValue);
    }

    // **Request Brightness Data Every 100ms**
    if (currentMillis - lastReceiveCheck > 100) {
        lastReceiveCheck = currentMillis;
        Serial.println("[ESP2] Requesting Brightness...");
        requestBrightness();
    }

    // **Update LED Brightness**
    Serial.println("[ESP2] Updating LEDs...");
    updateLEDs();

    // **Fade Out LEDs After 10 Seconds**
    if (currentMillis - lastPotChange > 10000 && !isFading) {
        Serial.println("[ESP2] Fading Out LEDs...");
        for (int i = 0; i < NUM_LEDS3; i++) leds3[i].fadeToBlackBy(5);
        for (int i = 0; i < NUM_LEDS4; i++) leds4[i].fadeToBlackBy(5);
        FastLED.show();
        isFading = true;
    }

    delay(50);  // Small delay to prevent serial spam
}
