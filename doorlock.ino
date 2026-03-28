#include <Adafruit_Keypad.h>
#include <LiquidCrystal_I2C.h>
#include <Servo.h>

const int PIN_BUZZER = 4;
const int PIN_SERVO  = 3;
const byte ROWS = 4, COLS = 4;
char keys[ROWS][COLS] = {{'1','2','3','A'},{'4','5','6','B'},{'7','8','9','C'},{'*','0','#','D'}};
byte rowPins[ROWS] = {5, 6, 7, 8};
byte colPins[COLS] = {9, 10, 11, 12};

Adafruit_Keypad keypad = Adafruit_Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);
LiquidCrystal_I2C lcd(0x27, 16, 2);
Servo door;

String inputBuf = "";
enum State { STATE_LOCKED, STATE_INPUT };
State currentState = STATE_LOCKED;

void setup() {
  Serial.begin(9600);
  keypad.begin();
  lcd.init();
  lcd.backlight();
  pinMode(PIN_BUZZER, OUTPUT);
  door.attach(PIN_SERVO);
  door.write(90); 
  showStatus();
}

void showStatus() {
  lcd.clear();
  if(currentState == STATE_LOCKED) { 
    lcd.print("Status: LOCKED");
    lcd.setCursor(0,1); 
    lcd.print("Press * to enter");
  } else { 
    lcd.print("Enter PIN:");
    lcd.setCursor(0,1); 
    for(int i=0; i<inputBuf.length(); i++) lcd.print('*');
  }
}

void loop() {
  keypad.tick();
  while(keypad.available()){
    keypadEvent e = keypad.read();
    if(e.bit.EVENT == KEY_JUST_PRESSED){
      char k = (char)e.bit.KEY;
      tone(PIN_BUZZER, 1000, 50);
      
      if(currentState == STATE_LOCKED && k == '*') { 
        currentState = STATE_INPUT;
        inputBuf = ""; 
        showStatus();
      }
      else if(currentState == STATE_INPUT){
        if(k >= '0' && k <= '9' && inputBuf.length() < 4) { 
          inputBuf += k;
          showStatus();
        }
        else if(k == '#' || k == 'A'){
          Serial.println("{\"event\":\"PIN_SUBMITTED\",\"pin\":\"" + inputBuf + "\"}");
          lcd.clear(); 
          lcd.print("Verifying...");
        }
      }
    }
  }

  if(Serial.available() > 0){
    String res = Serial.readStringUntil('\n');
    res.trim();
    
    if(res == "OPEN" || res.startsWith("OPEN:")){
      String name = res.startsWith("OPEN:") ? res.substring(5) : "Authorized";
      lcd.clear();
      lcd.print("Welcome,");
      lcd.setCursor(0,1); 
      lcd.print(name);

      // Smooth Opening (90 to 0 degrees)
      for (int pos = 90; pos >= 0; pos -= 1) {
        door.write(pos);
        delay(15); 
      }

      delay(7000); 

      // Smooth Closing (0 to 90 degrees)
      for (int pos = 0; pos <= 90; pos += 1) {
        door.write(pos);
        delay(15);
      }
      
      currentState = STATE_LOCKED;
      showStatus();
    } 
    else if(res == "DENY"){
      lcd.clear(); 
      lcd.print("ACCESS DENIED");
      delay(2000);
      currentState = STATE_LOCKED;
      showStatus();
    }
  }
}