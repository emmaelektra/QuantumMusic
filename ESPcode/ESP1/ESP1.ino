#include <WiFi.h>
#include <ArduinoJson.h>
#include <FastLED.h>
#include <ArduinoOTA.h>

#define SSID "BosonSamplerWiFi"
#define PASSWORD "QuantumTech2025"
#define LAPTOP_IP "192.168.4.2"  // Laptop's static IP

const int udpPort = 1234;  // Port to listen on
char incomingPacket[255];       // Buffer for incoming data

// Static IP Configuration for ESP1
IPAddress staticIP(192, 168, 4, 3);
IPAddress gateway(192, 168, 4, 1);
IPAddress subnet(255, 255, 255, 0);

// Id of ESP
#define ESP_ID 1

#define LED_PIN1 5
#define LED_PIN2 26
#define LED_PIN3 18
#define LED_PIN4 25
#define POT_PIN 34

#define NUM_LEDS1 200  
#define NUM_LEDS2 200 
#define NUM_LEDS3 200  
#define NUM_LEDS4 200  

static CRGB leds1[NUM_LEDS1];
static CRGB leds2[NUM_LEDS2];
static CRGB leds3[NUM_LEDS3];
static CRGB leds4[NUM_LEDS4];

uint8_t brightness1 = 0;
uint8_t brightness2 = 0;
uint8_t brightness3 = 0;
uint8_t brightness4 = 0;
float phaseShift1 = 0;
float phaseShift2 = 0;
float entanglement1 = 0;
float entanglement2  = 0;
int pulse1 = 0;
int max_brightness = 0;
uint8_t strobe1 = 0;
uint8_t strobe2 = 0;

int p1 = -1;
int p2 = -1;
int p3 = -1;

static int lastPotValue = -1;

// Global variable to track last update
unsigned long lastUpdateTimeOTA = 0;
unsigned long lastUpdateTimePOT = 0;
unsigned long lastUpdateTimeLED = 0;  
unsigned long lastUpdateRecieve = 0;

//Entanglement parameters
int thisfade = 1;

// Pulse parameters
constexpr int spread = 7;     // keep this (or use #define SPREAD 5)
float alpha = 0.3;  // decay rate of exponential

constexpr int SPREAD = 5;
constexpr int LUT_SIZE = 2*SPREAD + 1;
static float envelopeLUT[LUT_SIZE];

static bool initLUT = false;
void initEnvelopeLUT() {
  if (initLUT) return;
  initLUT = true;
  for (int o = -SPREAD; o <= SPREAD; o++) {
    envelopeLUT[o + SPREAD] = expf(-abs(o)*alpha);
  }
}

WiFiClient laptopClient;
WiFiUDP udp;

void updateLEDs() {
  for (int i = 0; i < NUM_LEDS1; i++) {
    leds1[i] = CRGB::White;
    leds1[i].nscale8(brightness1);
  }
  for (int i = 0; i < NUM_LEDS2; i++) {
    leds2[i] = CRGB::White;
    leds2[i].nscale8(brightness2);
  }
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

  /// Blend twinkleBuffer with steady white background
  for (int i = 0; i < NUM_LEDS3; i++) {
    CRGB glowColor = CRGB::White;
    glowColor.nscale8(brightness3);
    leds3[i] = glowColor;  
    leds3[i] += twinkleBuffer3[i];  
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
    leds4[i] = glowColor;
    leds4[i] += twinkleBuffer4[i];
  }
  
  int currentpixel = pulse1;
  for (int offset = -SPREAD; offset <= SPREAD; offset++) {
    int pixel = currentpixel + offset;
    uint8_t extra1 = uint8_t(map(brightness1, 0, max_brightness, 0, 255) * envelopeLUT[offset + SPREAD]);
    uint8_t extra2 = uint8_t(map(brightness2, 0, max_brightness, 0, 255) * envelopeLUT[offset + SPREAD]);
    if (pixel >= 0 && pixel < 200 && pulse1 != -1) {
      int idx = 200 - pixel;  // = 199 - pixel
      CRGB bump1 = CRGB::White;
      CRGB bump2 = CRGB::White;
      bump1.nscale8(extra1);
      bump2.nscale8(extra2);
      leds1[idx] += bump1;
      leds2[idx] += bump2;
    }
    if (pixel >= 200 && pixel < 400 && pulse1 != -1) {
      static int brightness3_pulse = brightness3;
      static int brightness4_pulse = brightness4;
      if (pixel == 200){
        brightness3_pulse = brightness3;
        brightness4_pulse = brightness4;
      }
      uint8_t extra3 = uint8_t(map(brightness3_pulse, 0, max_brightness, 0, 255) * envelopeLUT[offset + SPREAD]);
      uint8_t extra4 = uint8_t(map(brightness4_pulse, 0, max_brightness, 0, 255) * envelopeLUT[offset + SPREAD]);
      int idx2 = pixel - 200;
      CRGB bump3 = CRGB::White;
      CRGB bump4 = CRGB::White;
      bump3.nscale8(extra3);
      bump4.nscale8(extra4);
      leds3[idx2] += bump3;
      leds4[idx2] += bump4;
    }
  }
  FastLED.show();
}

void setup() {
  Serial.begin(115200);
  initEnvelopeLUT(); 
  
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

  if (millis() - lastUpdateTimeOTA >= 20) {
    lastUpdateTimeOTA = millis();
    ArduinoOTA.handle(); // handle OTA updates in the loop
  } 
  
  // Send data over udp
  if (millis() - lastUpdateTimePOT >= 20) {
    lastUpdateTimePOT = millis();
    int potValue = analogRead(POT_PIN);
    // Your values (some can be undefined or marked with a special value)
    p1 = potValue;  // Actual reading
    p2 = -1;                   // Placeholder for "missing"
    p3 = -1;                   // Placeholder for "missing"

    // Helper: convert int to String or blank if missing
    auto intOrBlank = [](int v) {
      return (v == -1) ? "" : String(v);
    };

    // Build CSV string with blanks for -1
    String csvString = String(ESP_ID) + "," + intOrBlank(p1) + "," + intOrBlank(p2) + "," + intOrBlank(p3) + "\n";

    // Send to laptop
    udp.beginPacket(LAPTOP_IP, udpPort);
    udp.print(csvString);
    udp.endPacket();
  }

  // Recieve data over UDP and update strip
  if (millis() - lastUpdateRecieve >= 10) {
    lastUpdateRecieve = millis();
    int packetSize = udp.parsePacket();
    if (packetSize) {
      int len = udp.read(incomingPacket, 255);
      if (len > 0) {
        incomingPacket[len] = '\0';  // Null-terminate the string
      }
    }

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

      // Now assign to your variables
    brightness1    = values[0];
    brightness2    = values[1];
    brightness3    = values[2];
    brightness4    = values[3];
    phaseShift1    = values[4];
    phaseShift2    = values[5];
    entanglement1  = values[6];
    entanglement2  = values[7];
    pulse1         = values[8];
    max_brightness = values[9];
    strobe1        = values[10];
    strobe2        = values[11];
    updateLEDs();
  }
}