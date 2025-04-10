/// @file    TwinkleFox.ino
/// @brief   Twinkling "holiday" lights that fade in and out.
/// @example TwinkleFox.ino

#include "FastLED.h"
#include <ArduinoOTA.h>
#include <WiFi.h>

#define SSID "BosonSamplerWiFi"
#define PASSWORD "QuantumTech2025"

// Static IP Configuration for ESP1
IPAddress staticIP(192, 168, 4, 3);
IPAddress gateway(192, 168, 4, 1);
IPAddress subnet(255, 255, 255, 0);

#define NUM_LEDS      200
#define LED_TYPE   WS2812
#define COLOR_ORDER   GRB
#define DATA_PIN        5

#define LED_PIN1 18
CRGBArray<NUM_LEDS> leds1;
CRGB leds[NUM_LEDS];

int lednumber = 200;

// Overall twinkle speed.
// 0 (VERY slow) to 8 (VERY fast).  
// 4, 5, and 6 are recommended, default is 4.
#define TWINKLE_SPEED 4

// Overall twinkle density.
// 0 (NONE lit) to 8 (ALL lit at once).  
// Default is 5.
#define TWINKLE_DENSITY 5

// Background color for 'unlit' pixels
// Can be set to CRGB::Black if desired.
CRGB BackgroundColor = CRGB::Black; 
CRGB lBackgroundColor = CRGB::Black; 

// If COOL_LIKE_INCANDESCENT is set to 1, colors will 
// fade out slightly 'reddened', similar to how
// incandescent bulbs change color as they get dimmed down.
#define COOL_LIKE_INCANDESCENT 1

#define HALFFAIRY ((CRGB::FairyLight & 0xFEFEFE) / 2)
#define QUARTERFAIRY ((CRGB::FairyLight & 0xFCFCFC) / 4)
const TProgmemRGBPalette16 FairyLight_p FL_PROGMEM =
{  CRGB::FairyLight, CRGB::FairyLight, CRGB::FairyLight, CRGB::FairyLight, 
   HALFFAIRY,        HALFFAIRY,        CRGB::FairyLight, CRGB::FairyLight, 
   QUARTERFAIRY,     QUARTERFAIRY,     CRGB::FairyLight, CRGB::FairyLight, 
   CRGB::FairyLight, CRGB::FairyLight, CRGB::FairyLight, CRGB::FairyLight };

const TProgmemRGBPalette16 WhitePalette FL_PROGMEM =
{  CRGB::White, CRGB::White, CRGB::White, CRGB::White, 
   CRGB::White,        CRGB::White,        CRGB::White, CRGB::White, 
   CRGB::White,     CRGB::White,     CRGB::White, CRGB::White, 
   CRGB::White, CRGB::White, CRGB::White, CRGB::White };


CRGBPalette16 gCurrentPalette = FairyLight_p; // Fixed single palette
CRGBPalette16 gNextPalette = WhitePalette; // Fixed single palette

// Function to interpolate between two colors and get the RGB value
CRGB interpolateColor(CRGB colorStart, CRGB colorEnd, float t) {
    // Clamp t between 0 and 1 to avoid going out of range
    t = constrain(t, 0.0, 1.0);

    // Calculate the interpolated color for each channel (Red, Green, Blue)
    uint8_t r = (uint8_t)(colorStart.r + t * (colorEnd.r - colorStart.r));
    uint8_t g = (uint8_t)(colorStart.g + t * (colorEnd.g - colorStart.g));
    uint8_t b = (uint8_t)(colorStart.b + t * (colorEnd.b - colorStart.b));

    // Return the resulting color as a CRGB object
    return CRGB(r, g, b);
}

void setup() {
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

  // Define start and end colors (you can replace them with any colors)
  CRGB colorStart = CRGB::White;  // Red color
  CRGB colorEnd = CRGB::Black;   // Blue color

  delay(3000); // safety startup delay
  FastLED.addLeds<WS2812, LED_PIN1, COLOR_ORDER>(leds1, NUM_LEDS).setCorrection(TypicalLEDStrip);
  FastLED.addLeds<WS2812, DATA_PIN, COLOR_ORDER>(leds, NUM_LEDS).setCorrection(TypicalLEDStrip);
  fill_solid(leds1, NUM_LEDS, lBackgroundColor);
  leds1.nscale8(77);
  FastLED.show();
}

void loop() {
  ArduinoOTA.handle(); // handle OTA updates in the loop

  static float t = 0.0;
  static unsigned long lastTime = 0;
  unsigned long currentTime = millis();
  CRGB lBackgroundColor = interpolateColor(CRGB::Black, CRGB::White, t);

  if (currentTime - lastTime >= 100){
    lastTime = currentTime;
    t += 0.01;
    if (t >= 1){
      t = 0;
    }
  }
  fill_solid(leds1, NUM_LEDS, lBackgroundColor);
  for (int i = 0; i < NUM_LEDS; i++) {
    int phasShiftbrightness2 = 77*(sin8((i + 3.141) * 15))/255;
    leds1[i].nscale8(phasShiftbrightness2);
  }
  drawTwinkles(leds, lednumber, lBackgroundColor);
  //leds.nscale8(10);
  FastLED.show();
}

// This function loops over each pixel, calculates the 
// adjusted 'clock' that this pixel should use, and calls 
// "CalculateOneTwinkle" on each pixel. It then displays
// either the twinkle color of the background color, 
// whichever is brighter.
void drawTwinkles(CRGB* leds, int lednum, CRGB BackgroundColor)
{
  uint16_t PRNG16 = 11337;
  uint32_t clock32 = millis();

  CRGB bg = BackgroundColor;
  uint8_t backgroundBrightness = bg.getAverageLight();
  
  for (int i = 0; i < lednum; i++) {
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
      leds[i] = c;
    } else if (deltabright > 0) {
      leds[i] = blend(bg, c, deltabright * 8);
    } else {
      leds[i] = bg;
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
    c = ColorFromPalette(gNextPalette, hue, bright, NOBLEND);
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
