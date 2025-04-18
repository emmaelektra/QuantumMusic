#include <WiFi.h>
#include <ArduinoJson.h>
#include <FastLED.h>
#include <ArduinoOTA.h>

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
#define PHASE_POT_PIN_1 32 // Phase shift potentiometer for Strip 1
#define PHASE_POT_PIN_2 35 // Phase shift potentiometer for Strip 2

#define NUM_LEDS1 200  
#define NUM_LEDS2 100  
#define NUM_LEDS3 400  
#define NUM_LEDS4 200  

CRGB leds1[NUM_LEDS1];  
CRGB leds2[NUM_LEDS2];  
CRGB leds3[NUM_LEDS3];  
CRGB leds4[NUM_LEDS4];

uint8_t brightness1 = 0;
uint8_t brightness2 = 0;
uint8_t brightness3 = 0;
uint8_t brightness4 = 0;
uint8_t phaseShift1 = 0;
uint8_t phaseShift2 = 0;
bool entanglement = false;
static int lastPotValue = -1;

// Global variable to track last update
unsigned long lastUpdateTimeOTA = 0;
unsigned long lastUpdateTimePOT = 10;
unsigned long lastUpdateTimeLED = 0;  

WiFiClient laptopClient;

void updateLEDs() {
  for (int i = 0; i < NUM_LEDS1; i++) {
    int phasShiftbrightness1 = brightness1*(sin8((i + phaseShift1) * 15))/255;
    leds2[i] = CRGB::Red;
    leds2[i].nscale8(phasShiftbrightness1);
  }
  for (int i = 0; i < NUM_LEDS2; i++) {
    int phasShiftbrightness2 = brightness2*(sin8((i + phaseShift2) * 15))/255;
    leds2[i] = CRGB::Red;
    leds2[i].nscale8(phasShiftbrightness2);
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

bool connectToLaptop() {
  if (laptopClient.connected()) {
    return true;
  }
  Serial.print("[ESP4] Connecting to laptop...");
  if (laptopClient.connect(LAPTOP_IP, 80)) {
    Serial.println("Connected.");
    return true;
  } else {
    Serial.println("Connection failed.");
    return false;
  }
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
    Serial.println("\n[ESP4] Connected to Wi-Fi.");
  } else {
    Serial.println("\n[ESP4] Failed to connect to Wi-Fi.");
  }

  ArduinoOTA.begin(); // begin the OTA for Over The Air ESP updates

  // Initialize FastLED strips
  FastLED.addLeds<WS2812B, LED_PIN1, GRB>(leds1, NUM_LEDS1);
  FastLED.addLeds<WS2812B, LED_PIN2, GRB>(leds2, NUM_LEDS2);
  FastLED.addLeds<WS2812B, LED_PIN3, GRB>(leds3, NUM_LEDS3);
  FastLED.addLeds<WS2812B, LED_PIN4, GRB>(leds4, NUM_LEDS4);
}

void loop() {
  //unsigned long currentMillis = millis();
  if (millis() - lastUpdateTimeOTA >= 20) {
    lastUpdateTimeOTA = millis();
    ArduinoOTA.handle(); // handle OTA updates in the loop
  }
  // Maintain persistent connection to the laptop.
  if (!connectToLaptop()) {
    delay(1000);
    return;
  }
  
  // In your loop function:
  if (millis() - lastUpdateTimePOT >= 50) {
    lastUpdateTimePOT = millis();
    int potValue = analogRead(POT_PIN);
    int phaseValue1 = analogRead(PHASE_POT_PIN_1);
    int phaseValue2 = analogRead(PHASE_POT_PIN_2);
    //Serial.print("[ESP1] Potentiometer value: ");
    //Serial.println(potValue);

    StaticJsonDocument<200> doc;
    doc["esp_id"] = 4;
    doc["pot_value"] = potValue;
    doc["phase_value1"] = phaseValue1;
    doc["phase_value2"] = phaseValue2;
    
    String jsonString;
    serializeJson(doc, jsonString);
    jsonString += "\n";  // Terminate the message with newline
    
    laptopClient.print(jsonString);
    //laptopClient.flush();
    //Serial.print("[ESP1] Sent pot update: ");
    //Serial.println(jsonString);
  }
  
  // Always check for incoming brightness data.
  if (millis() - lastUpdateTimeLED >= 20) {
    lastUpdateTimeLED = millis();
    if (laptopClient.available()) {
      String response = laptopClient.readStringUntil('\n');
      StaticJsonDocument<200> respDoc;
      DeserializationError error = deserializeJson(respDoc, response);
      if (!error) {
        brightness1 = respDoc["strip_1_bright"];
        brightness2 = respDoc["strip_2_bright"];
        brightness3 = respDoc["strip_3_bright"];
        brightness4 = respDoc["strip_4_bright"];
        phaseShift1 = respDoc["strip_1_phaseshift"];
        phaseShift2 = respDoc["strip_2_phaseshift"];
        entanglement = respDoc["Entanglement"];
        //Serial.print("[ESP1] Updated brightness - Strip1: ");
        //Serial.print(brightness1);
        //Serial.print(", Strip2: ");
        //Serial.println(brightness2);
        //Serial.print("[ESP1] Updated brightness - Strip3: ");
        //Serial.print(brightness3);
        //Serial.print(", Strip4: ");
        //Serial.println(brightness4);
        updateLEDs();
      }
    }
  }
}
