#include <WiFi.h>
#include <ArduinoJson.h>
#include <FastLED.h>
#include <ArduinoOTA.h>

#define SSID "GalaxyS10agn43"
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

// Global variable to track last update
unsigned long lastUpdateTimeOTA = 0;
unsigned long lastUpdateTimePOT = 10;
unsigned long lastUpdateTimeLED = 0;  

// Phase shift parameters
constexpr int PHASER_LEN1 = 40;  // how many LEDs at the front get the full phaser  
constexpr int PHASER_LEN2 = 40;
constexpr int FADE_LEN1   = 5;  // over how many LEDs to cross-fade  
constexpr int FADE_LEN2   = 5;  // over how many LEDs to cross-fade  

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

void drawPulse(int currentpixel) {
  static int brightness1_pulse = brightness1;
  static int brightness2_pulse = brightness2;
  static int brightness3_pulse = brightness3;
  static int brightness4_pulse = brightness4;
  for (int offset = -SPREAD; offset <= SPREAD; offset++){
    int pixel = currentpixel + offset;
    if (currentpixel == 200){
        brightness1_pulse = brightness1;
      }
    if (currentpixel == 400){
        brightness2_pulse = brightness2;
    }
    int pix = pixel - 400;
    if (pixel > 400 && pixel < 1000) {
      if (currentpixel == 600){
        brightness3_pulse = brightness3;
        brightness4_pulse = brightness4;
      }
      // strip1
      if (pix < 200) {
        int idx = 200 - pix;
        uint8_t extra1 = uint8_t(map(brightness1_pulse, 0, max_brightness, 0, 255) * envelopeLUT[offset + SPREAD]);
        CRGB bump1 = CRGB::White;
        bump1.nscale8(extra1);
        leds1[idx] += bump1;
      }
      // strip2
      if (pix >= 100 && pix < 200) {
        int idx = 199 - pix;
        uint8_t extra2 = uint8_t(map(brightness2_pulse, 0, max_brightness, 0, 255) * envelopeLUT[offset + SPREAD]);
    
        CRGB bump2 = CRGB::White;
        bump2.nscale8(extra2);
        leds2[idx] += bump2;  
      }
      // strip3
      if (pix >= 200 && pix < 600) {
        int idx = pix - 200;
        uint8_t extra3 = uint8_t(map(brightness3_pulse, 0, max_brightness, 0, 255) * envelopeLUT[offset + SPREAD]);
        CRGB bump3 = CRGB::White;
        bump3.nscale8(extra3);
        leds3[idx] += bump3;
      }
      // strip4
      if (pix >= 200 && pix < 400) {
        int idx = pix - 200;
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

  // ——— Strip 1: phaser at the end, fading into glow ———
  for (int i = 0; i < NUM_LEDS1; i++) {
    // flat glow value
    uint8_t glow    = brightness1;
    // will hold our final brightness for this LED
    uint8_t finalV;

    if (i < NUM_LEDS1 - (PHASER_LEN1 + FADE_LEN1)) {
      // 1) Far from the end → solid glow
      finalV = glow;

    } else if (i < NUM_LEDS1 - PHASER_LEN1) {
      // 2) Fade region
      //   t: 0.0 at start of fade, → 1.0 at beginning of phaser
      float t = float(i - (NUM_LEDS1 - (PHASER_LEN1 + FADE_LEN1))) / FADE_LEN1;

      // compute phaser at this relative position
      int relPos = i - (NUM_LEDS1 - (PHASER_LEN1 + FADE_LEN1));
      int ph = (brightness1 * sin8((relPos + phaseShift1 * 3) * 18)) / 255;

      // cross-fade: glow*(t) + ph*(1 - t)
      finalV = uint8_t(glow * t + ph * (1.0 - t));

    } else {
      // 3) Full phaser region: last PHASER_LEN LEDs
      int relPos = i - (NUM_LEDS1 - PHASER_LEN1);
      finalV = (brightness1 * sin8((relPos + phaseShift1 * 3) * 18)) / 255;
    }

    leds1[i] = CRGB::White;
    leds1[i].nscale8(finalV);
  }

  // ——— Strip 2: exactly the same, but using brightness2 and phaseShift2 ———
  for (int i = 0; i < NUM_LEDS2; i++) {
    uint8_t glow = brightness2, finalV;

    if (i < NUM_LEDS2 - (PHASER_LEN2 + FADE_LEN2)) {
      finalV = glow;
    }
    else if (i < NUM_LEDS2 - PHASER_LEN2) {
      float t = float(i - (NUM_LEDS2 - (PHASER_LEN2 + FADE_LEN2))) / FADE_LEN2;
      int relPos = i - (NUM_LEDS2 - (PHASER_LEN2 + FADE_LEN2));
      int ph = (brightness2 * sin8((relPos + phaseShift2 * 3) * 18)) / 255;
      finalV = uint8_t(glow * t + ph * (1.0 - t));
    }
    else {
      int relPos = i - (NUM_LEDS2 - PHASER_LEN2);
      finalV = (brightness2 * sin8((relPos + phaseShift2 * 3) * 18)) / 255;
    }

    leds2[i] = CRGB::White;
    leds2[i].nscale8(finalV);
  }
  for (int i = 0; i < NUM_LEDS3; i++) {
    CRGB base = CRGB::White; base.nscale8(brightness3);
    leds3[i] = base;
  }
  for (int i = 0; i < NUM_LEDS4; i++) {
    CRGB base = CRGB::White; base.nscale8(brightness4);
    leds4[i] = base;
  }
  //Pulse
  if (pulse1 != -1){
    drawPulse(pulse1);
  }
  if (pulse2 != -1){
    drawPulse(pulse2);
  }
  if (pulse3 != -1){
    drawPulse(pulse3);
  }
  if (entanglement1 == 1){
    if (pulse1 != -1 && pulse1 >= 600){
      drawPulse(pulse1+entanglement_offset);
    }
    if (pulse2 != -1 && pulse2 >= 600){
      drawPulse(pulse2+entanglement_offset);
    }
    if (pulse3 != -1 && pulse3 >= 600){
      drawPulse(pulse3+entanglement_offset);
    }
  }
  if (entanglement1 == 2){
    if (pulse1 != -1 && 600 > pulse1 && pulse1 >= 500){
      drawPulse(pulse1+entanglement_offset);
    }
    if (pulse2 != -1 && 600 > pulse2 && pulse2 >= 500){
      drawPulse(pulse2+entanglement_offset);
    }
    if (pulse3 != -1 && 600 > pulse3 && pulse3 >= 500){
      drawPulse(pulse3+entanglement_offset);
    }
  }
  if (entanglement1 == 3){
    if (pulse1 != -1){
      drawPulse(pulse1+entanglement_offset);
    }
    if (pulse2 != -1){
      drawPulse(pulse2+entanglement_offset);
    }
    if (pulse3 != -1){
      drawPulse(pulse3+entanglement_offset);
    }
  }

  if (strobeActive) {
    unsigned long dt = now - strobeStartMs;
    if (dt < strobeTimeMs) {
      // overall amplitude: 0→1→0 over strobeTimeMs
      float phase = float(dt) / float(strobeTimeMs);
      float amp   = sinf(phase * M_PI);      // 0→1→0

      const int glowLen = 70;                // number of LEDs lighting up
      for (int off = 0; off < glowLen; off++) {
        int idx = NUM_LEDS3 - 1 - off;        // tip inward
        if (idx < 0) break;

        // shape: base (off=0) bright, tip (off=glowLen-1) dark
        float t      = float(off) / float(glowLen - 1);  
        float gamma  = 1.0f;         // <1 → shallower drop, >1 → sharper drop
        float falloff = powf(1.0f - t, gamma);
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
