#include <WiFi.h>
#include <ArduinoJson.h>
#include <FastLED.h>
#include <ArduinoOTA.h>

#define SSID "BosonSamplerWiFi"
#define PASSWORD "QuantumTech2025"
#define LAPTOP_IP "192.168.4.2"  // Laptop's static IP

// Static IP Configuration for ESP1
IPAddress staticIP(192, 168, 4, 7);
IPAddress gateway(192, 168, 4, 1);
IPAddress subnet(255, 255, 255, 0);

#define LED_PIN3 18
#define LED_PIN4 25
#define POT_PIN 34

#define NUM_LEDS3 200  
#define NUM_LEDS4 400  

CRGB leds3[NUM_LEDS3];
CRGB leds4[NUM_LEDS4];

uint8_t brightness3 = 0;
uint8_t brightness4 = 0;
bool entanglement = false;
static int lastPotValue = -1;

// Global variable to track last update
unsigned long lastUpdateTimeOTA = 0;
unsigned long lastUpdateTimePOT = 0;
unsigned long lastUpdateTimeLED = 0;  

WiFiClient laptopClient;

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

bool connectToLaptop() {
  if (laptopClient.connected()) {
    return true;
  }
  Serial.print("[ESP1] Connecting to laptop...");
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
    Serial.println("\n[ESP5] Connected to Wi-Fi.");
  } else {
    Serial.println("\n[ESP5] Failed to connect to Wi-Fi.");
  }

  ArduinoOTA.begin(); // begin the OTA for Over The Air ESP updates

  // Initialize FastLED strips
  FastLED.addLeds<WS2812B, LED_PIN3, GRB>(leds3, NUM_LEDS3);
  FastLED.addLeds<WS2812B, LED_PIN4, GRB>(leds4, NUM_LEDS4);
}

void loop() {
  unsigned long currentMillis = millis();
  if (currentMillis - lastUpdateTimeOTA >= 20) {
    lastUpdateTimeOTA = currentMillis;
    ArduinoOTA.handle(); // handle OTA updates in the loop
  }
  // Maintain persistent connection to the laptop.
  if (!connectToLaptop()) {
    delay(1000);
    return;
  }
  
  // In your loop function:
  
  if (currentMillis - lastUpdateTimePOT >= 25) {
    lastUpdateTimePOT = currentMillis;
    int potValue = analogRead(POT_PIN);
    //Serial.print("[ESP1] Potentiometer value: ");
    //Serial.println(potValue);

    StaticJsonDocument<200> doc;
    doc["esp_id"] = 5;
    doc["pot_value"] = potValue;
    
    String jsonString;
    serializeJson(doc, jsonString);
    jsonString += "\n";  // Terminate the message with newline
    
    laptopClient.print(jsonString);
    //Serial.print("[ESP1] Sent pot update: ");
    //Serial.println(jsonString);
  }
  
  // Always check for incoming brightness data.
  if (currentMillis - lastUpdateTimeLED >= 25) {
    lastUpdateTimeLED = currentMillis;
    if (laptopClient.available()) {
      String response = laptopClient.readStringUntil('\n');
      StaticJsonDocument<200> respDoc;
      DeserializationError error = deserializeJson(respDoc, response);
      if (!error) {
        brightness3 = respDoc["strip_3_bright"];
        brightness4 = respDoc["strip_4_bright"];
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