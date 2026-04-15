#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm;

// -------- SERVO LIMITS --------
#define SERVO_MIN     110
#define SERVO_CENTER  310
#define SERVO_MAX     510

// -------- CHANNELS --------
int leftUpper  = 0;
int leftLower  = 1;
int rightUpper = 2;
int rightLower = 3;

int eyeH = 4;
int eyeV = 5;

int mouth = 6;   // ✅ Mouth servo channel

// -------- EYELID POSITIONS --------
int upperOpen  = 260;
int upperClose = 360;

int lowerOpen  = 360;
int lowerClose = 260;

// -------- MOUTH POSITIONS --------
int mouthClose = 150;
int mouthOpen  = 400;

bool isBlinking = false;
bool speaking = false;

// -------- EYELID CONTROL --------
void openEyes() {
  pwm.setPWM(leftUpper,  0, upperOpen);
  pwm.setPWM(rightUpper, 0, upperOpen);
  pwm.setPWM(leftLower,  0, lowerOpen);
  pwm.setPWM(rightLower, 0, lowerOpen);
}

void closeEyes() {
  pwm.setPWM(leftUpper,  0, upperClose);
  pwm.setPWM(rightUpper, 0, upperClose);
  pwm.setPWM(leftLower,  0, lowerClose);
  pwm.setPWM(rightLower, 0, lowerClose);
}

void blinkEyes() {
  if (isBlinking) return;
  isBlinking = true;

  closeEyes();
  delay(220);
  openEyes();
  delay(180);

  isBlinking = false;
}

// -------- MOUTH CONTROL --------
void mouthTalk() {
  speaking = true;
}

void mouthStop() {
  pwm.setPWM(mouth, 0, mouthClose);
  speaking = false;
}

void setup() {
  Serial.begin(9600);

  pwm.begin();
  pwm.setPWMFreq(50);
  delay(300);

  pwm.setPWM(eyeH, 0, SERVO_CENTER);
  pwm.setPWM(eyeV, 0, SERVO_CENTER);
  pwm.setPWM(mouth, 0, mouthClose);

  openEyes();
}

void loop() {

  // ---- Mouth animation while speaking ----
  if (speaking) {
    pwm.setPWM(mouth, 0, mouthClose);
    delay(120);
    pwm.setPWM(mouth, 0, mouthOpen);
    delay(120);
  }

  if (!Serial.available()) return;

  String data = Serial.readStringUntil('\n');
  data.trim();

  if (data == "BLINK") {
    blinkEyes();
    return;
  }

  if (data == "OPEN") {
    openEyes();
    return;
  }

  if (data == "CLOSE") {
    closeEyes();
    return;
  }

  if (data == "SPEAK") {
    mouthTalk();
    return;
  }

  if (data == "STOP") {
    mouthStop();
    return;
  }

  int comma = data.indexOf(',');
  if (comma > 0 && !isBlinking) {
    int pulseH = data.substring(0, comma).toInt();
    int pulseV = data.substring(comma + 1).toInt();

    pulseH = constrain(pulseH, SERVO_MIN, SERVO_MAX);
    pulseV = constrain(pulseV, 250, 450);

    pwm.setPWM(eyeH, 0, pulseH);
    pwm.setPWM(eyeV, 0, pulseV);
  }
}

