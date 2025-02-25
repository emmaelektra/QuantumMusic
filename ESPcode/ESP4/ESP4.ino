#include <WiFi.h>
#include <ArduinoJson.h>
#include <FastLED.h>

#define SSID "BosonSamplerWiFi"
#define PASSWORD "QuantumTech2025"
#define LAPTOP_IP "192.168.4.2"  // Laptop's static IP

// **Static IP Configuration for ESP4**
IPAddress staticIP(192,168,4,6);  
IPAddress gateway(192,168,4,1);
IPAddress subnet(255,255,255,0);

// **ESP4 LED Configuration**
#define LED_PIN1 5   // Phase shift strip 1
#define LED_PIN2 26  // Phase shift strip 2
#define LED_PIN3 18  // Brightness-controlled strip 3
#define LED_PIN4 25  // Brightness-controlled strip 4

#define POT_PIN 34        // Main potentiometer
#define PHASE_POT1_PIN 35 // Phase shift potentiometer for Strip 1
#define PHASE_POT2_PIN 32 // Phase shift potentiometer for Strip 2

#define NUM_LEDS1 200  
#define NUM_LEDS2 100  
#define NUM_LEDS3 400  
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
uint8_t phaseEffect1[NUM_LEDS1];  // Store phase shift effect for Strip 1
uint8_t phaseEffect2[NUM_LEDS2];  // Store phase shift effect for Strip 2

static int lastPotValue = -1;
static int lastPhaseValue1 = -1;
static int lastPhaseValue2 = -1;
bool isFading = false;  // Track if fading message has been sent

// **Send potentiometer & phase shift data to laptop**
void sendDataToLaptop(int potValue, int phaseValue1, int phaseValue2) {
    if (WiFi.status() == WL_CONNECTED) {
        WiFiClient laptop;
        if (laptop.connect(LAPTOP_IP, 80)) {  
            StaticJsonDocument<256> doc;
            doc["esp_id"] = 4;
            doc["pot_value"] = potValue;
            doc["phase_value1"] = phaseValue1;
            doc["phase_value2"] = phaseValue2;
            String jsonString;
            serializeJson(doc, jsonString);
            laptop.println(jsonString);
            laptop.stop();
            Serial.println("[ESP4] Sent Pot & Phase Values to Laptop.");
        } else {
            Serial.println("[ESP4] Failed to connect to Laptop.");
        }
    }
}

// **Request brightness & phase shift updates**
void requestBrightnessAndPhase() {
    if (WiFi.status() == WL_CONNECTED) {
        WiFiClient clientReceive;
        if (clientReceive.connect(LAPTOP_IP, 80)) {
            clientReceive.println("{\"esp_id\": 4, \"request\": \"brightness_phase\"}");

            unsigned long startTime = millis();
            while (!clientReceive.available() && millis() - startTime < 10) {
                // Wait max 10ms for data
            }

            if (clientReceive.available()) {
                String response = clientReceive.readStringUntil('\n');
                StaticJsonDocument<512> doc;
                DeserializationError error = deserializeJson(doc, response);

                if (!error) {
                    brightness3 = doc["brightness3"];
                    brightness4 = doc["brightness4"];

                    JsonArray phaseArray1 = doc["phaseEffect1"];
                    for (int i = 0; i < NUM_LEDS1; i++) {
                        phaseEffect1[i] = phaseArray1[i];
                    }

                    JsonArray phaseArray2 = doc["phaseEffect2"];
                    for (int i = 0; i < NUM_LEDS2; i++) {
                        phaseEffect2[i] = phaseArray2[i];
                    }

                    Serial.print("[ESP4] Received Brightness: ");
                    Serial.print(brightness3);
                    Serial.print(", ");
                    Serial.println(brightness4);
                } else {
                    Serial.println("[ESP4] Failed to parse brightness & phase data.");
                }
            } else {
                Serial.println("[ESP4] No brightness data received.");
            }
            clientReceive.stop();
        } else {
            Serial.println("[ESP4] Failed to connect to laptop for brightness request.");
        }
    }
}

// **Update LED brightness and apply phase shift effects**
void updateLEDs() {
    for (int i = 0; i < NUM_LEDS3; i++) {
        leds3[i] = CRGB::Red;
        leds3[i].nscale8(brightness3);
    }
    for (int i = 0; i < NUM_LEDS4; i++) {
        leds4[i] = CRGB::Red;
        leds4[i].nscale8(brightness4);
    }

    // **Apply Phase Shift Effects**
    for (int i = 0; i < NUM_LEDS1; i++) {
        leds1[i] = (phaseEffect1[i]) ? CRGB::Red : CRGB::Black;
    }
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
        Serial.println("\n[ESP4] Connected to Wi-Fi. IP: " + WiFi.localIP().toString());
    } else {
        Serial.println("\n[ESP4] Failed to connect to Wi-Fi.");
    }

    FastLED.addLeds<WS2812B, LED_PIN1, GRB>(leds1, NUM_LEDS1);
    FastLED.addLeds<WS2812B, LED_PIN2, GRB>(leds2, NUM_LEDS2);
    FastLED.addLeds<WS2812B, LED_PIN3, GRB>(leds3, NUM_LEDS3);
    FastLED.addLeds<WS2812B, LED_PIN4, GRB>(leds4, NUM_LEDS4);
}

void loop() {
    unsigned long currentMillis = millis();

    Serial.println("[ESP4] Loop Running...");

    // **ESP4's Potentiometer & Phase Data**
    int potValue = analogRead(POT_PIN);
    int phasePot1Value = analogRead(PHASE_POT1_PIN);
    int phasePot2Value = analogRead(PHASE_POT2_PIN);
    Serial.print("[ESP4] Potentiometer: ");
    Serial.print(potValue);
    Serial.print(" | Phase1: ");
    Serial.print(phasePot1Value);
    Serial.print(" | Phase2: ");
    Serial.println(phasePot2Value);

    if (abs(potValue - lastPotValue) > 60 || abs(phasePot1Value - lastPhaseValue1) > 60 || abs(phasePot2Value - lastPhaseValue2) > 60) {  
        lastPotChange = currentMillis;
        lastPotValue = potValue;
        lastPhaseValue1 = phasePot1Value;
        lastPhaseValue2 = phasePot2Value;
        isFading = false;

        Serial.println("[ESP4] Sending Pot & Phase Values to Laptop...");
        sendDataToLaptop(potValue, phasePot1Value, phasePot2Value);
    }

    // **Request Brightness & Phase Data Every 100ms**
    if (currentMillis - lastReceiveCheck > 100) {
        lastReceiveCheck = currentMillis;
        Serial.println("[ESP4] Requesting Brightness & Phase...");
        requestBrightnessAndPhase();
    }

    // **Update LED Brightness**
    Serial.println("[ESP4] Updating LEDs...");
    updateLEDs();

    delay(50);  // Small delay to prevent serial spam
}
