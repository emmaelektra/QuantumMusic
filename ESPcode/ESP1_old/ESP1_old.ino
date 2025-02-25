#include <WiFi.h>
#include <ArduinoJson.h>
#include <FastLED.h>

#define SSID "BosonSamplerWiFi"
#define PASSWORD "QuantumTech2025"
#define LAPTOP_IP "192.168.4.2"

IPAddress staticIP(192,168,4,3);
IPAddress gateway(192,168,4,1);
IPAddress subnet(255,255,255,0);

#define LED_PIN1 5
#define LED_PIN2 26
#define LED_PIN3 18
#define LED_PIN4 25
#define POT_PIN 34

#define NUM_LEDS1 200  
#define NUM_LEDS2 200  
#define NUM_LEDS3 200  
#define NUM_LEDS4 200  

CRGB leds1[NUM_LEDS1];
CRGB leds2[NUM_LEDS2];
CRGB leds3[NUM_LEDS3];
CRGB leds4[NUM_LEDS4];

WiFiClient client;
unsigned long lastPotChange = 0;
unsigned long lastReceiveCheck = 0;
uint8_t brightness3 = 0;
uint8_t brightness4 = 0;

static int lastPotValue = -1;

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

void requestBrightness() {
    if (WiFi.status() == WL_CONNECTED) {
        WiFiClient clientReceive;
        if (clientReceive.connect(LAPTOP_IP, 80)) {
            clientReceive.println("{\"esp_id\": 1, \"request\": \"brightness\"}");

            unsigned long startTime = millis();
            while (!clientReceive.available() && millis() - startTime < 10) {}

            if (clientReceive.available()) {
                String response = clientReceive.readStringUntil('\n');
                StaticJsonDocument<200> doc;
                DeserializationError error = deserializeJson(doc, response);

                if (!error) {
                    brightness3 = doc["strip_3_bright"];
                    brightness4 = doc["strip_4_bright"];
                    Serial.print("[ESP1] Received brightness - Strip3: ");
                    Serial.print(brightness3);
                    Serial.print(", Strip4: ");
                    Serial.println(brightness4);
                }
            }
            clientReceive.stop();
        }
    }
}

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

    FastLED.addLeds<WS2812B, LED_PIN3, GRB>(leds3, NUM_LEDS3);
    FastLED.addLeds<WS2812B, LED_PIN4, GRB>(leds4, NUM_LEDS4);
}

void loop() {
    unsigned long currentMillis = millis();

    Serial.println("[ESP1] Loop Running...");

    int potValue = analogRead(POT_PIN);

    if (abs(potValue - lastPotValue) > 100) {  
        Serial.print("[ESP1] Potentiometer Value: ");
        Serial.println(potValue);
        lastPotChange = currentMillis;
        lastPotValue = potValue;

        Serial.println("[ESP1] Sending Pot Value to Laptop...");
        sendDataToLaptop(potValue);
    }

    if (currentMillis - lastReceiveCheck > 100) {
        lastReceiveCheck = currentMillis;
        Serial.println("[ESP1] Requesting Brightness...");
        requestBrightness();
    }

    Serial.println("[ESP1] Updating LEDs...");
    updateLEDs();

    //delay(50);  
}
