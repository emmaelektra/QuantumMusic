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

const int udpPort = 1234;  // Port to listen on
char incomingPacket[255];       // Buffer for incoming data

// Id of ESP
#define ESP_ID 4

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
float phaseShift1 = 0;
float phaseShift2 = 0;
float entanglement1 = 0;
float entanglement2  = 0;
int pulse1 = 0;
uint8_t pulse2 = 0;
uint8_t strobe1 = 0;
uint8_t strobe2 = 0;

// Initialise poti values
int potValue = -1;
int psValue1 = -1;
int psValue2 = -1;

static int lastPotValue = -1;

// Global variable to track last update
unsigned long lastUpdateTimeOTA = 0;
unsigned long lastUpdateTimePOT = 10;
unsigned long lastUpdateTimeLED = 0;  

//Entanglement parameters
int thisfade = 1;

// Pulse parameters
uint8_t pulse_boost = 255;

// Strobe parameters
bool strobeActive = false;
unsigned long strobeStartMs = 0;
const unsigned long strobeTimeMs = 2000; // 2 s
bool strobeConsumed = false;

#include <math.h>
#ifndef M_PI
  #define M_PI 3.14159265358979323846
#endif

#define MAX_GLOW_LEDS 40


WiFiClient laptopClient;
WiFiUDP udp;

void updateLEDs() {
  // clear our one‐shot as soon as the Python code drops strobe1 back to 0
  if (!strobe1) {
    strobeConsumed = false;
  }

  unsigned long now = millis();

  // ——— 1) Detect strobe start (rising edge) ———
  if (strobe1 && !strobeActive && !strobeConsumed) {
  // only trigger once
  strobeActive   = true;
  strobeStartMs  = now;
  strobeConsumed = true;
  }

  // ——— 2) Strip 1: moving phaser ———
  for (int i = 0; i < NUM_LEDS1; i++) {
    // sin8 returns 0–255; scale brightness1 by it
    int v = (brightness1 * sin8((i + phaseShift1) * 15)) / 255;
    leds1[i] = CRGB::White;
    leds1[i].nscale8(v);
  }

  // ——— 3) Strip 2: moving phaser ———
  for (int i = 0; i < NUM_LEDS2; i++) {
    int v = (brightness2 * sin8((i + phaseShift2) * 15)) / 255;
    leds2[i] = CRGB::White;
    leds2[i].nscale8(v);
  }

  // ——— 4) Entanglement/twinkle on strip 3 & 4 ———
  int sparkleBoost = map(entanglement1, 0, 20, 0, 255);

  // strip 3 base fade
  fadeToBlackBy(leds3, NUM_LEDS3, thisfade);
  static CRGB twinkle3[NUM_LEDS3];
  fill_solid(twinkle3, NUM_LEDS3, CRGB::Black);
  int maxS3    = map(entanglement1, 1, 20, NUM_LEDS3/1.5, NUM_LEDS3/30);
  int chance3  = map(entanglement1, 1, 20, 1, 20);
  for (int k = 0; k < maxS3; k++) {
    if (random8() < chance3) {
      int p = random16(NUM_LEDS3);
      twinkle3[p] = CRGB::White;
      twinkle3[p].nscale8(sparkleBoost);
    }
  }
  for (int i = 0; i < NUM_LEDS3; i++) {
    CRGB base = CRGB::White; base.nscale8(brightness3);
    leds3[i] = base;
    leds3[i] += twinkle3[i];
  }

  // strip 4 base fade
  fadeToBlackBy(leds4, NUM_LEDS4, thisfade);
  static CRGB twinkle4[NUM_LEDS4];
  fill_solid(twinkle4, NUM_LEDS4, CRGB::Black);
  int maxS4    = map(entanglement1, 1, 20, NUM_LEDS4/1.5, NUM_LEDS4/30);
  int chance4  = map(entanglement1, 1, 20, 1, 20);
  for (int k = 0; k < maxS4; k++) {
    if (random8() < chance4) {
      int p = random16(NUM_LEDS4);
      twinkle4[p] = CRGB::White;
      twinkle4[p].nscale8(sparkleBoost);
    }
  }
  for (int i = 0; i < NUM_LEDS4; i++) {
    CRGB base = CRGB::White; base.nscale8(brightness4);
    leds4[i] = base;
    leds4[i] += twinkle4[i];
  }

  // ——— 5) Photon pulse across all strips ———
  if (pulse1 > 400 && pulse1 < 1000) {
    int cp = pulse1 - 400;
    // strip1
    if (cp < 200 && brightness1 != 0) {
      int idx = 200 - cp;
      leds1[idx] = CRGB::White; leds1[idx].nscale8(pulse_boost);
    }
    // strip2
    if (cp >= 100 && cp < 200 && brightness2 != 0) {
      int idx = 200 - cp;
      leds2[idx] = CRGB::White; leds2[idx].nscale8(pulse_boost);
    }
    // strip3
    if (cp >= 200 && cp < 600 && brightness3 != 0) {
      int idx = cp - 200;
      leds3[idx] = CRGB::White; leds3[idx].nscale8(pulse_boost);
    }
    // strip4
    if (cp >= 200 && cp < 400 && brightness4 != 0) {
      int idx = cp - 200;
      leds4[idx] = CRGB::White; leds4[idx].nscale8(pulse_boost);
    }
  }

   if (pulse1 == -1){
    leds3[399] = CRGB::White; leds3[300].nscale8(brightness3);
  }

  if (strobeActive) {
    unsigned long dt = now - strobeStartMs;
    if (dt < strobeTimeMs) {
      // overall amplitude: 0→1→0 over strobeTimeMs
      float phase = float(dt) / float(strobeTimeMs);
      float amp   = sinf(phase * M_PI);      // 0→1→0

      const int glowLen = 30;                // number of LEDs lighting up
      for (int off = 0; off < glowLen; off++) {
        int idx = NUM_LEDS3 - 1 - off;        // tip inward
        if (idx < 0) break;

        // shape: base (off=0) bright, tip (off=glowLen-1) dark
        float falloff = 1.0f - float(off) / float(glowLen - 1);
        float intensity = amp * falloff;      // modulate by amp

        uint8_t b = uint8_t(intensity * 255);
        CRGB glow = CRGB::White; glow.nscale8(b);
        leds3[idx] += glow;
      }
    } else {
      strobeActive = false;  // end of strobe window
    }
  }

  // ——— 4) Push to LEDs ———
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

  // Start UDP
  udp.begin(udpPort);
}

void loop() {

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
    psValue1 = analogRead(PHASE_POT_PIN_1);
    psValue2 = analogRead(PHASE_POT_PIN_2);
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
