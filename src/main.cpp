#include <Arduino.h>
#include <BluetoothSerial.h>
#include <Preferences.h>
#include "HX711.h"

// HX711.DT	- pin #A1 D33
// HX711.SCK	- pin #A0 D32
#define DT_PIN 33
#define SCK_PIN 32
// GAIN 128,64,32
#define GAIN 64

HX711 scale(DT_PIN, SCK_PIN, GAIN);
BluetoothSerial SerialBT;
Preferences preference;

#define LED_BLINK 0
#define LED_ON 1
#define LED_OFF 2
uint8_t ledState = 0;

#define SCALEMODE_UNIT 0
#define SCALEMODE_VALUE 1
uint8_t scaleMode = 0;
bool useBluetooth = false;

void ATCommandTask(void *pvParameters)
{
  Serial.println("ATCommand Task");
  for(;;) {
    int state = -1;
    bool isReboot = false;
    int8_t b;
    while ((b = Serial.read()) != -1) {
      if (b == 'A') state = 0;
      else if (state == 0 && b =='T') {
        String command = Serial.readStringUntil('\r');
        if (command.startsWith("ID")) {
          preference.begin("HX711");
          if (command.startsWith("ID=")) {
            preference.putString("ID", command.substring(command.indexOf('=')+1));
            isReboot = true;
            //Serial.printf("%s\r\n", command.substring(command.indexOf('=')+1).c_str());
          } else {
          Serial.printf("%s\r\n", preference.getString("ID", "").c_str());
          }
          preference.end();
        } else if (command.startsWith("MODE=")) {
          String mode = command.substring(command.indexOf('=')+1);
          if (mode == "0") {
            scaleMode = SCALEMODE_UNIT;
          } else if (mode == "1") {
            scaleMode = SCALEMODE_VALUE;
          }
        } else if (command.startsWith("TARE")) {
          scale.tare(10);
        } else if (command.startsWith("CAL")) {
          scale.set_scale();
          scale.tare();
          scaleMode = SCALEMODE_UNIT;
          Serial.printf("Start Calibration\r\n");
        } else if (command.startsWith("SCALE=")) {
          String numStr = command.substring(command.indexOf('=')+1);
          scale.set_scale(numStr.toFloat());
          scaleMode = SCALEMODE_UNIT;
        }
        if (isReboot) ESP.restart();
      } else {
        state = -1;
      }
    }
    vTaskDelay(100 / portTICK_PERIOD_MS);
  }
  vTaskDelete(NULL);
}

void SerialTask(void *pvParameters) {
  for(;;) {
    if (!useBluetooth) {
      if (scaleMode == SCALEMODE_VALUE) {
        Serial.println(scale.get_value(10));
      } else {
        Serial.println(scale.get_units(10));
      }
      vTaskDelay(100 / portTICK_PERIOD_MS);
    } else {
      vTaskDelay(3000 / portTICK_PERIOD_MS);
    }
  }
  vTaskDelete(NULL);
}

void BluetoothServerTask(void *pvParameters)
{
  for (;;) {
    if (SerialBT.hasClient()) {
      useBluetooth = true;
      ledState = LED_ON;
      SerialBT.printf("%.2lf %.2lf\n", scale.get_value(10), scale.get_units(10));
    } else {
      useBluetooth = false;
      if (ledState != LED_BLINK) ledState = LED_BLINK;
    }
    vTaskDelay(100 / portTICK_PERIOD_MS);
  }
  vTaskDelete(NULL);
}

extern "C" void app_main() {
  // power on LED PID
  initArduino();
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  
  // Debugging serial
  Serial.begin(9600);
  // Random name in form CA-NIBP-<4char>
  // https://www.random.org/cgi-bin/randbyte?nbytes=2&format=h
  preference.begin("HX711", true);
  String name = preference.getString("ID", "");
  preference.end();
  if (name.length() == 0)
    SerialBT.begin("WEIGH-0000");
  else
    SerialBT.begin("WEIGH-" + name);
  Serial.print("START\n");
  // AT Command (Serial) task
  xTaskCreatePinnedToCore(ATCommandTask, "ATCommand", 2048, NULL, 1, NULL, 1);
  // Serial task
  xTaskCreatePinnedToCore(SerialTask, "Serial", 1024, NULL, 0, NULL, 0);
  // Bluetooth Serial task
  xTaskCreatePinnedToCore(BluetoothServerTask, "Bluetooth", 2048, NULL, 0, NULL, 1);
  
  // LED status task
  bool ledLow = true;
  while(1) {
    if (ledState == LED_ON) {
      digitalWrite(LED_BUILTIN, HIGH);
    } else if (ledState == LED_OFF) {
      digitalWrite(LED_BUILTIN, LOW);
    } else {
      digitalWrite(LED_BUILTIN, (ledLow) ? HIGH : LOW);
      ledLow = !ledLow;
    }
    delay(500);
  }
}