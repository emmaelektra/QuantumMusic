#include <WiFi.h>
#include <ArduinoJson.h>
#include <FastLED.h>

#define SSID "BosonSamplerWiFi"
#define PASSWORD "QuantumTech2025"
#define LAPTOP_IP "192.168.4.2"  // Laptop's static IP

// **Static IP Configuration for ESP3**
IPAddress staticIP(192,168,4,5);  
IPAddress gateway(192,168,4,1);
IPAddress subnet(255,255,255,0);

// **ESP3 LED Configuration**
#define LED_PIN2 26  // Phase-shifting strip
#define LED_PIN3 18
#define LED_PIN4 25

#define POT_PIN 34        // Main potentiometer
#define PHASE_POT_PIN 35  // Phase shift potentiometer

#define NUM_LEDS2 100  
#define NUM_LEDS3 100  
#define NUM_LEDS4 200  

CRGB leds2[NUM_LEDS2];  
CRGB leds3[NUM_LEDS3];  
CRGB leds4[NUM_LEDS4];

WiFiClient client;
unsigned long lastPotChange = 0;
unsigned long lastReceiveCheck = 0;
uint8_t brightness3 = 0;
uint8_t brightness4 = 0;
uint8_t phaseEffect2[NUM_LEDS2]; // Store phase shift effect

static int lastPotValue = -1;
static int lastPhaseValue = -1;
bool isFading = false;  // Track if fading message has been sent

// **Send potentiometer data to laptop**
void sendDataToLaptop(int potValue, int phaseValue) {
    if (WiFi.status() == WL_CONNECTED) {
        WiFiClient laptop;
        if (laptop.connect(LAPTOP_IP, 80)) {  
            StaticJsonDocument<256> doc;
            doc["esp_id"] = 3;
            doc["pot_value"] = potValue;
            doc["phase_value1"] = phaseValue;
            String jsonString;
            serializeJson(doc, jsonString);
            laptop.println(jsonString);
            laptop.stop();
            Serial.println("[ESP3] Sent Pot & Phase Values to Laptop.");
        } else {
            Serial.println("[ESP3] Failed to connect to Laptop.");
        }
    }
}

// **Request brightness & phase shift updates**
void requestBrightness() {
    if (WiFi.status() == WL_CONNECTED) {
        WiFiClient clientReceive;
        if (clientReceive.connect(LAPTOP_IP, 80)) {
            clientReceive.println("{\"esp_id\": 3, \"request\": \"brightness\"}");

            unsigned long startTime = millis();
            while (!clientReceive.available() && millis() - startTime < 10) {
                // Wait max 10ms for data
            }

            if (clientReceive.available()) {
                String response = clientReceive.readStringUntil('\n');
                StaticJsonDocument<256> doc;
                DeserializationError error = deserializeJson(doc, response);

                if (!error) {
                    brightness3 = doc["brightness3"];
                    brightness4 = doc["brightness4"];

                    JsonArray phaseArray = doc["phaseEffect2"];
                    for (int i = 0; i < NUM_LEDS2; i++) {
                        phaseEffect2[i] = phaseArray[i];
                    }
                    Serial.print("[ESP3] Received Brightness: ");
                    Serial.print(brightness3);
                    Serial.print(", ");
                    Serial.println(brightness4);
                } else {
                    Serial.println("[ESP3] Failed to parse brightness data.");
                }
            } else {
                Serial.println("[ESP3] No brightness data received.");
            }
            clientReceive.stop();
        } else {
            Serial.println("[ESP3] Failed to connect to laptop for brightness request.");
        }
    }
}

// **Update LED brightness**
void updateLEDs() {
    for (int i = 0; i < NUM_LEDS3; i++) {
        leds3[i] = CRGB::Red;
        leds3[i].nscale8(brightness3);
    }
    for (int i = 0; i < NUM_LEDS4; i++) {
        leds4[i] = CRGB::Red;
        leds4[i].nscale8(brightness4);
    }

    // **Apply Phase Shift Effect to Strip 2**
    for (int i = 0; i < NUM_LEDS2; i++) {
        leds2[i] = (phaseEffect2[i]) ? CRGB::Red : CRGB::Black;
    }

    FastLED.show();
}

void setup() {
    Serial.begin(115200);

    // **Set Static IP and Connect to Wi-Fi**
    WiFi.config(staticIP, gateway, subnet);
    WiFi.begin(SSID, PASSWORD);

    int timeout = 0;
    while (WiFi.status() != WL_CONNECTED && timeout < 20) {  
        delay(100);  // Faster retries
        timeout++;
        Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n[ESP3] Connected to Wi-Fi. IP: " + WiFi.localIP().toString());
    } else {
        Serial.println("\n[ESP3] Failed to connect to Wi-Fi.");
    }

    FastLED.addLeds<WS2812B, LED_PIN2, GRB>(leds2, NUM_LEDS2);
    FastLED.addLeds<WS2812B, LED_PIN3, GRB>(leds3, NUM_LEDS3);
    FastLED.addLeds<WS2812B, LED_PIN4, GRB>(leds4, NUM_LEDS4);
}

void loop() {
    unsigned long currentMillis = millis();

    Serial.println("[ESP3] Loop Running...");

    // **ESP3's Potentiometer Data**
    int potValue = analogRead(POT_PIN);
    int phasePotValue = analogRead(PHASE_POT_PIN);
    Serial.print("[ESP3] Potentiometer Value: ");
    Serial.print(potValue);
    Serial.print(" | Phase Pot Value: ");
    Serial.println(phasePotValue);

    if (abs(potValue - lastPotValue) > 60 || abs(phasePotValue - lastPhaseValue) > 60) {  
        lastPotChange = currentMillis;
        lastPotValue = potValue;
        lastPhaseValue = phasePotValue;
        isFading = false;

        Serial.println("[ESP3] Sending Pot & Phase Values to Laptop...");
        sendDataToLaptop(potValue, phasePotValue);
    }

    // **Request Brightness & Phase Data Every 100ms**
    if (currentMillis - lastReceiveCheck > 100) {
        lastReceiveCheck = currentMillis;
        Serial.println("[ESP3] Requesting Brightness...");
        requestBrightness();
    }

    // **Update LED Brightness**
    Serial.println("[ESP3] Updating LEDs...");
    updateLEDs();

    // **Fade Out LEDs After 10 Seconds**
    if (currentMillis - lastPotChange > 10000 && !isFading) {
        Serial.println("[ESP3] Fading Out LEDs...");
        for (int i = 0; i < NUM_LEDS3; i++) leds3[i].fadeToBlackBy(5);
        for (int i = 0; i < NUM_LEDS4; i++) leds4[i].fadeToBlackBy(5);
        for (int i = 0; i < NUM_LEDS2; i++) leds2[i].fadeToBlackBy(5);
        FastLED.show();
        isFading = true;
    }

    delay(50);  // Small delay to prevent serial spam
}
