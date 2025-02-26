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
#define DATA_PIN        18
//#define CLK_PIN       4
#define VOLTS          5
#define MAX_MA       4000

CRGBArray<NUM_LEDS> leds;

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
CRGB gBackgroundColor = CRGB::Black; 

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


CRGBPalette16 gCurrentPalette = FairyLight_p; // Fixed single palette

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

  delay(3000); // safety startup delay
  FastLED.setMaxPowerInVoltsAndMilliamps(VOLTS, MAX_MA);
  FastLED.addLeds<LED_TYPE, DATA_PIN, COLOR_ORDER>(leds, NUM_LEDS)
    .setCorrection(TypicalLEDStrip);
}

void loop() {
  ArduinoOTA.handle(); // handle OTA updates in the loop

  EVERY_N_MILLISECONDS(10) {
    nblendPaletteTowardPalette(gCurrentPalette, gCurrentPalette, 12);
  }

  drawTwinkles(leds);
  FastLED.show();
}

// This function loops over each pixel, calculates the 
// adjusted 'clock' that this pixel should use, and calls 
// "CalculateOneTwinkle" on each pixel. It then displays
// either the twinkle color of the background color, 
// whichever is brighter.
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
