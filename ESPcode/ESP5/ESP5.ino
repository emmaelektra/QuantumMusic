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

const int udpPort = 1234;  // Port to listen on
char incomingPacket[255];       // Buffer for incoming data

// Id of ESP
#define ESP_ID 5

#define LED_PIN3 18
#define LED_PIN4 25
#define POT_PIN 34

#define NUM_LEDS3 200  
#define NUM_LEDS4 400  

CRGB leds3[NUM_LEDS3];
CRGB leds4[NUM_LEDS4];

uint8_t brightness1 = 0;
uint8_t brightness2 = 0;
uint8_t brightness3 = 0;
uint8_t brightness4 = 0;
float phaseShift1 = 0;
float phaseShift2 = 0;
float entanglement1 = 0;
float entanglement2  = 0;
uint8_t pulse1 = 0;
uint8_t pulse2 = 0;
uint8_t strobe1 = 0;
uint8_t strobe2 = 0;

// Initialise poti values
int potValue = -1;
int psValue1 = -1;
int psValue2 = -1;

static int lastPotValue = -1;

// For WiFi reconnection
static unsigned long lastReconnectAttempt = 0;

// For watchdog restart
unsigned long lastGoodPacketTime;

// Global variable to track last update
unsigned long lastUpdateTimeOTA = 0;
unsigned long lastUpdateTimePOT = 0;
unsigned long lastUpdateTimeLED = 0;  

//Entanglement parameters
int thisfade = 1;

WiFiClient laptopClient;
WiFiUDP udp;

void updateLEDs() {
  // Entanglement on strips 3 and 4
  int sparkleBoost = map(entanglement1, 0, 15, 0, 255);
  fadeToBlackBy(leds3, NUM_LEDS3, thisfade);
  fadeToBlackBy(leds4, NUM_LEDS4, thisfade);

  // Blending amount: 0 = full glow, 1 = full twinkle
  float fadeAmount = constrain(entanglement1 / 20.0, 0.0, 1.0);  // normalized
  fadeAmount = pow(fadeAmount, 1.5);  // optional: softer entry

  // Twinkle pattern buffer
  CRGB twinkleBuffer3[NUM_LEDS3];
  CRGB twinkleBuffer4[NUM_LEDS4];
  fill_solid(twinkleBuffer3, NUM_LEDS3, CRGB::Black);
  fill_solid(twinkleBuffer4, NUM_LEDS4, CRGB::Black);

  // Twinkle logic based on entanglement
  int maxSparkles3 = map(entanglement1, 1, 15, NUM_LEDS3 / 1.5, NUM_LEDS3 / 30);
  int maxSparkles4 = map(entanglement1, 1, 15, NUM_LEDS4 / 1.5, NUM_LEDS4 / 30);
  int twinkleChance = map(entanglement1, 1, 15, 1, 20);

  for (int i = 0; i < maxSparkles3; i++) {
    if (random8() < twinkleChance) {
      int pos = random16(NUM_LEDS3);
      twinkleBuffer3[pos] = CRGB::White;
      twinkleBuffer3[pos].nscale8(sparkleBoost);  // full entanglement = full sparkle
    }
  }

  // Blend twinkleBuffer with steady white background
  for (int i = 0; i < NUM_LEDS3; i++) {
    CRGB glowColor = CRGB::White;
    glowColor.nscale8(brightness3);

    leds3[i] = blend(glowColor, twinkleBuffer3[i], fadeAmount * 255);
  }

    for (int i = 0; i < maxSparkles4; i++) {
    if (random8() < twinkleChance) {
      int pos = random16(NUM_LEDS4);
      twinkleBuffer4[pos] = CRGB::White;
      twinkleBuffer4[pos].nscale8(sparkleBoost);  // full entanglement = full sparkle
    }
  }

  for (int i = 0; i < NUM_LEDS4; i++) {
    CRGB glowColor = CRGB::White;
    glowColor.nscale8(brightness4);
    leds4[i] = blend(glowColor, twinkleBuffer4[i], fadeAmount * 255);
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
    Serial.println("\n[ESP5] Connected to Wi-Fi.");
  } else {
    Serial.println("\n[ESP5] Failed to connect to Wi-Fi.");
  }

  ArduinoOTA.begin(); // begin the OTA for Over The Air ESP updates

  // Initialize FastLED strips
  FastLED.addLeds<WS2812B, LED_PIN3, GRB>(leds3, NUM_LEDS3);
  FastLED.addLeds<WS2812B, LED_PIN4, GRB>(leds4, NUM_LEDS4);

  // Start UDP
  udp.begin(udpPort);
  lastGoodPacketTime = millis();

}

void loop() {
  // Reconnect WiFi if disconnected
  if (WiFi.status() != WL_CONNECTED && millis() - lastReconnectAttempt > 5000) {
    lastReconnectAttempt = millis();
    Serial.println("[ESP5] WiFi disconnected. Attempting reconnect...");
    WiFi.disconnect();
    WiFi.begin(SSID, PASSWORD);
  }

  // Watchdog: Restart if no good packets in 10 seconds
  if (millis() - lastGoodPacketTime > 10000) {
    Serial.println("[ESP5] No data received for 10 seconds. Restarting...");
    ESP.restart();
  }

  // Handle OTA
  if (millis() - lastUpdateTimeOTA >= 20) {
    lastUpdateTimeOTA = millis();
    ArduinoOTA.handle(); 
  }
  
  // Send data over UDP
  if (millis() - lastUpdateTimePOT >= 20) {
    lastUpdateTimePOT = millis();
    // Read POT Values
    potValue = analogRead(POT_PIN);
    // Helper: convert int to String or blank if missing
    auto intOrBlank = [](int v) {
      return (v == -1) ? "" : String(v);
    };

    // Build CSV string with blanks for -1
    String csvString = String(ESP_ID) + "," + intOrBlank(potValue) + "," + intOrBlank(psValue1) + "," + intOrBlank(psValue2) + "\n";

    // Send to laptop
    udp.beginPacket(LAPTOP_IP, udpPort);
    udp.print(csvString);
    udp.endPacket();
  }
  
  // Recieve data over UDP and update strip
  if (millis() - lastUpdateTimeLED >= 20) {
    lastUpdateTimeLED = millis();
    int packetSize = udp.parsePacket();
    if (packetSize) {
      int len = udp.read(incomingPacket, 255);
      if (len > 0) {
        incomingPacket[len] = '\0';  // Null-terminate the string
      }
    }
    if (packetSize > 0) {
      lastGoodPacketTime = millis();  // We got something from the server
    }


    // Convert packet to string
    String response = String(incomingPacket);

    // Split CSV into tokens
    int index = 0;
    float values[12];  // Adjust if you add more fields

    int lastComma = -1;
    for (int i = 0; i < response.length(); i++) {
      if (response[i] == ',' || i == response.length() - 1) {
        int end = (response[i] == ',') ? i : i + 1;
        String valueStr = response.substring(lastComma + 1, end);
        valueStr.trim();
        if (valueStr.length() > 0) {
          values[index] = valueStr.toFloat();  // Parses to 0.0 if invalid
        } else {
          values[index] = NAN;  // Use NAN to indicate missing value
        }
        lastComma = i;
        index++;
        if (index >= 12) break;  // Safety check
      }
    }

    // Now assign variables from csv
    brightness1    = values[0]/2;
    brightness2    = values[1]/2;
    brightness3    = values[2]/2;
    brightness4    = values[3]/2;
    phaseShift1    = values[4];
    phaseShift2    = values[5];
    entanglement1  = values[6];
    entanglement2  = values[7];
    pulse1         = values[8];
    pulse2         = values[9];
    strobe1        = values[10];
    strobe2        = values[11];

    // Update LEDS
    updateLEDs();
  }
}