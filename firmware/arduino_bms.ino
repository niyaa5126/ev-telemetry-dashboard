// Arduino / ESP32 Real-Time BMS Telemetry Transmitter
// Reads analog inputs and prints serialized CSV lines over UART/USB

const int PIN_VOLTAGE = A0;      // Analog voltage divider
const int PIN_TEMP    = A1;      // NTC Thermistor analog pin
const int PIN_CURRENT = A2;      // Current sensor (ACS712 / Hall-effect)

void setup() {
  Serial.begin(115200);
}

void loop() {
  // Read analog pins (0 - 1023)
  int rawV = analogRead(PIN_VOLTAGE);
  int rawT = analogRead(PIN_TEMP);
  int rawI = analogRead(PIN_CURRENT);

  // Convert to physical units
  float voltage = (rawV / 1023.0) * 55.0;            // Scaled for ~52V pack
  float temperature = (rawT / 1023.0) * 80.0;        // Scaled for degrees C
  float current = ((rawI / 1023.0) * 5.0 - 2.5) * 10.0; // Scaled current (Amperes)
  float soc = 95.0;

  // Print CSV telemetry line: voltage,current,temperature,soc
  Serial.print(voltage, 2);
  Serial.print(",");
  Serial.print(current, 2);
  Serial.print(",");
  Serial.print(temperature, 1);
  Serial.print(",");
  Serial.println(soc, 2);

  delay(500); // 2 Hz telemetry update rate
}
