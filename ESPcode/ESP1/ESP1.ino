#include <WiFi.h>
#include <ArduinoJson.h>
#include <FastLED.h>
#include <ArduinoOTA.h>

#define SSID "BosonSamplerWiFi"
#define PASSWORD "QuantumTech2025"
#define LAPTOP_IP "192.168.4.2"  // Laptop's static IP

// Static IP Configuration for ESP1
IPAddress staticIP(192, 168, 4, 3);
IPAddress gateway(192, 168, 4, 1);
IPAddress subnet(255, 255, 255, 0);

#define LED_PIN1 5
#define LED_PIN2 26
#define LED_PIN3 18
#define LED_PIN4 25
#define POT_PIN 34

#define NUM_LEDS1 200  
#define NUM_LEDS2 200 
#define NUM_LEDS3 200  
#define NUM_LEDS4 200  

// variables for entanglement effect
#define TWINKLE_SPEED 4
#define TWINKLE_DENSITY 5
#define COOL_LIKE_INCANDESCENT 1

// FairyLight colour palette
#define HALFFAIRY ((CRGB::FairyLight & 0xFEFEFE) / 2)
#define QUARTERFAIRY ((CRGB::FairyLight & 0xFCFCFC) / 4)
const TProgmemRGBPalette16 FairyLight_p FL_PROGMEM =
{  CRGB::FairyLight, CRGB::FairyLight, CRGB::FairyLight, CRGB::FairyLight, 
   HALFFAIRY,        HALFFAIRY,        CRGB::FairyLight, CRGB::FairyLight, 
   QUARTERFAIRY,     QUARTERFAIRY,     CRGB::FairyLight, CRGB::FairyLight, 
   CRGB::FairyLight, CRGB::FairyLight, CRGB::FairyLight, CRGB::FairyLight };

CRGBPalette16 gCurrentPalette = FairyLight_p; // colour palette for entanglement effect
CRGB gBackgroundColor = CRGB::Black; // background colour for entanglement
CRGB leds1[NUM_LEDS1];
CRGB leds2[NUM_LEDS2];
CRGB leds3[NUM_LEDS3];
CRGB leds4[NUM_LEDS4];

uint8_t brightness1 = 0;
uint8_t brightness2 = 0;
uint8_t brightness3 = 0;
uint8_t brightness4 = 0;
bool entanglement = false;
static int lastPotValue = -1;

unsigned long lastUpdateTime = 0;  // Global variable to track last update

WiFiClient laptopClient;

void updateLEDs() {
  for (int i = 0; i < NUM_LEDS1; i++) {
    leds1[i] = CRGB::Green;
    leds1[i].nscale8(brightness1);
  }
  for (int i = 0; i < NUM_LEDS2; i++) {
    leds2[i] = CRGB::Red;
    leds2[i].nscale8(brightness2);
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
}

void loop() {
  ArduinoOTA.handle(); // handle OTA updates in the loop
  // Maintain persistent connection to the laptop.
  if (!connectToLaptop()) {
    delay(1000);
    return;
  }
  
  // In your loop function:
  unsigned long currentMillis = millis();
  if (currentMillis - lastUpdateTime >= 20) {
    lastUpdateTime = currentMillis;
    int potValue = analogRead(POT_PIN);
    //Serial.print("[ESP1] Potentiometer value: ");
    //Serial.println(potValue);

    StaticJsonDocument<200> doc;
    doc["esp_id"] = 1;
    doc["pot_value"] = potValue;
    
    String jsonString;
    serializeJson(doc, jsonString);
    jsonString += "\n";  // Terminate the message with newline
    
    laptopClient.print(jsonString);
    //Serial.print("[ESP1] Sent pot update: ");
    //Serial.println(jsonString);
  }
  
  // Always check for incoming brightness data.
  if (laptopClient.available()) {
    String response = laptopClient.readStringUntil('\n');
    StaticJsonDocument<200> respDoc;
    DeserializationError error = deserializeJson(respDoc, response);
    if (!error) {
      brightness1 = respDoc["strip_1_bright"];
      brightness2 = respDoc["strip_2_bright"];
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
    } else {
      //Serial.println("[ESP1] Failed to parse brightness JSON");
    }
  }
  
  delay(10);
}

void drawTwinkles(CRGBSet& L)
{
  uint16_t PRNG16 = 11337;
  uint32_t clock32 = millis();

  CRGB bg = gBackgroundColor;
  uint8_t backgroundBrightness = bg.getAverageLight();
  
  for (CRGB& pixel : L) {
    PRNG16 = (uint16_t)(PRNG16 * 2053) + 1384; // next 'random' number
    uint16_t myclockoffset16 = PRNG16; // use that number as clock offset
    PRNG16 = (uint16_t)(PRNG16 * 2053) + 1384; // next 'random' number
    uint8_t myspeedmultiplierQ5_3 =  ((((PRNG16 & 0xFF) >> 4) + (PRNG16 & 0x0F)) & 0x0F) + 0x08;
    uint32_t myclock30 = (uint32_t)((clock32 * myspeedmultiplierQ5_3) >> 3) + myclockoffset16;
    uint8_t myunique8 = PRNG16 >> 8;

    CRGB c = computeOneTwinkle(myclock30, myunique8);

    uint8_t cbright = c.getAverageLight();
    int16_t deltabright = cbright - backgroundBrightness;
    if (deltabright >= 32 || (!bg)) {
      pixel = c;
    } else if (deltabright > 0) {
      pixel = blend(bg, c, deltabright * 8);
    } else {
      pixel = bg;
    }
  }
}

CRGB computeOneTwinkle(uint32_t ms, uint8_t salt)
{
  uint16_t ticks = ms >> (8 - TWINKLE_SPEED);
  uint8_t fastcycle8 = ticks;
  uint16_t slowcycle16 = (ticks >> 8) + salt;
  slowcycle16 += sin8(slowcycle16);
  slowcycle16 = (slowcycle16 * 2053) + 1384;
  uint8_t slowcycle8 = (slowcycle16 & 0xFF) + (slowcycle16 >> 8);
  
  uint8_t bright = 0;
  if (((slowcycle8 & 0x0E) / 2) < TWINKLE_DENSITY) {
    bright = attackDecayWave8(fastcycle8);
  }

  uint8_t hue = slowcycle8 - salt;
  CRGB c;
  if (bright > 0) {
    c = ColorFromPalette(gCurrentPalette, hue, bright, NOBLEND);
    if (COOL_LIKE_INCANDESCENT == 1) {
      coolLikeIncandescent(c, fastcycle8);
    }
  } else {
    c = CRGB::Black;
  }
  return c;
}

uint8_t attackDecayWave8(uint8_t i)
{
  if (i < 86) {
    return i * 3;
  } else {
    i -= 86;
    return 255 - (i + (i / 2));
  }
}

void coolLikeIncandescent(CRGB& c, uint8_t phase)
{
  if (phase < 128) return;

  uint8_t cooling = (phase - 128) >> 4;
  c.g = qsub8(c.g, cooling);
  c.b = qsub8(c.b, cooling * 2);
}