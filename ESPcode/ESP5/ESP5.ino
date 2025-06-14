#include <WiFi.h>
#include <ArduinoJson.h>
#include <FastLED.h>
#include <ArduinoOTA.h>

#define SSID "GalaxyS10agn43"
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
int pulse1 = 0;
int pulse2 = 0;
int pulse3 = 0;
int entanglement_offset = 15;
uint8_t max_brightness = 0;
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

// Pulse parameters
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

void drawPulse(int currentpixel){
  static int brightness3_pulse = brightness3;
  static int brightness4_pulse = brightness4;
  for (int offset = -SPREAD; offset <= SPREAD; offset++) {
    int pixel = currentpixel + offset;
    if (currentpixel >= 0 && currentpixel < 400) {
      if (pixel == 0){
        brightness3_pulse = brightness3;
        brightness4_pulse = brightness4;
      }
      if (pixel >= 0 && pixel < 200) {
        int idx = pixel;
        uint8_t extra3 = uint8_t(map(brightness3_pulse, 0, max_brightness, 0, 255) * envelopeLUT[offset + SPREAD]);
        CRGB bump3 = CRGB::White;
        bump3.nscale8(extra3);
        leds3[idx] += bump3;
      }
      if (pixel >= 0 && pixel < 400) {
        int idx = pixel;
        uint8_t extra4 = uint8_t(map(brightness4_pulse, 0, max_brightness, 0, 255) * envelopeLUT[offset + SPREAD]);
        CRGB bump4 = CRGB::White;
        bump4.nscale8(extra4);
        leds4[idx] += bump4;
      }
    }
  }
}
// Strobe parameters
bool strobeActive = false;
unsigned long strobeStartMs = 0;
const unsigned long strobeTimeMs = 2000; // 2 s
bool strobeConsumed = false;

WiFiClient laptopClient;
WiFiUDP udp;

void updateLEDs() {
    if (!strobe2) {
    strobeConsumed = false;
  }

  unsigned long now = millis();

  // ——— 1) Detect strobe start (rising edge) ———
  if (strobe2 && !strobeActive && !strobeConsumed) {
  // only trigger once
  strobeActive   = true;
  strobeStartMs  = now;
  strobeConsumed = true;
  }

  // BACKGROUND BRIGHTNESS //
  for (int i = 0; i < NUM_LEDS3; i++) {
    CRGB glowColor = CRGB::White;
    glowColor.nscale8(brightness3);
    leds3[i] = glowColor;  
  }
  for (int i = 0; i < NUM_LEDS4; i++) {
    CRGB glowColor = CRGB::White;
    glowColor.nscale8(brightness4);
    leds4[i] = glowColor;
  }

  //Pulse
  if (pulse1 != -1){
    drawPulse(pulse1-600);
  }
  if (pulse2 != -1){
    drawPulse(pulse2-600);
  }
  if (pulse3 != -1){
    drawPulse(pulse3-600);
  }
  if (entanglement1 == 1){
    if (pulse1 != -1){
      drawPulse(pulse1-600+entanglement_offset);
    }
    if (pulse2 != -1){
      drawPulse(pulse2-600+entanglement_offset);
    }
    if (pulse3 != -1){
      drawPulse(pulse3-600+entanglement_offset);
    }
  }

  // STROBE //
  if (strobeActive) {
    unsigned long dt = now - strobeStartMs;
    if (dt < strobeTimeMs) {
      // overall amplitude: 0→1→0 over strobeTimeMs
      float phase = float(dt) / float(strobeTimeMs);
      float amp   = sinf(phase * M_PI);      // 0→1→0

      const int glowLen = 70;                // number of LEDs lighting up
      for (int off = 0; off < glowLen; off++) {
        int idx = NUM_LEDS4 - 1 - off;        // tip inward
        if (idx < 0) break;

        // shape: base (off=0) bright, tip (off=glowLen-1) dark
        float t      = float(off) / float(glowLen - 1);  
        float gamma  = 1.0f;         // <1 → shallower drop, >1 → sharper drop
        float falloff = powf(1.0f - t, gamma);
        float intensity = amp * falloff;      // modulate by amp

        uint8_t b = uint8_t(intensity * 255);
        CRGB glow = CRGB::White; glow.nscale8(b);
        leds4[idx] += glow;
      }
    } else {
      strobeActive = false;  // end of strobe window
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
    float values[13];  // Adjust if you add more fields

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
        if (index >= 13) break;  // Safety check
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
    pulse1         = values[7];
    pulse2         = values[8];
    pulse3         = values[9];
    max_brightness = values[10];
    strobe1        = values[11];
    strobe2        = values[12];
    updateLEDs();
  }
}