// ==================================================
// RUBI X — 6-MOTOR CUBE MOVE CONTROLLER
// Adjacent opposite-face moves run simultaneously.
// ==================================================

// ==================================================
// PIN MAP
// ==================================================
const int DOWN_STEP_PIN = 2;
const int DOWN_DIR_PIN  = 3;
const int DOWN_EN_PIN   = 4;

const int FRONT_STEP_PIN = 5;
const int FRONT_DIR_PIN  = 6;
const int FRONT_EN_PIN   = 7;

const int BACK_STEP_PIN = 8;
const int BACK_DIR_PIN  = 9;
const int BACK_EN_PIN   = 10;

const int RIGHT_STEP_PIN = 11;
const int RIGHT_DIR_PIN  = 12;
const int RIGHT_EN_PIN   = 13;

// Left: A0, A1, A2
const int LEFT_STEP_PIN = A0;
const int LEFT_DIR_PIN  = A1;
const int LEFT_EN_PIN   = A2;

// Up: 22, 23, 24
const int UP_STEP_PIN = 22;
const int UP_DIR_PIN  = 23;
const int UP_EN_PIN   = 24;

// ==================================================
// MOVEMENT SETTINGS
// ==================================================
const int QUARTER_TURN_STEPS = 400;

// Smaller number = faster. Values are microseconds in delayMicroseconds().
const int NORMAL_TURN_DELAY = 120;
const int DOUBLE_TURN_DELAY = 90;

// Microseconds between step edges while two opposite motors move together.
const int SIMULTANEOUS_TURN_DELAY = 150;

// Change only if that face's direction is backwards.
const bool DOWN_DIRECTION_REVERSED  = true;
const bool FRONT_DIRECTION_REVERSED = true;
const bool BACK_DIRECTION_REVERSED  = true;
const bool RIGHT_DIRECTION_REVERSED = true;
const bool LEFT_DIRECTION_REVERSED  = true;
const bool UP_DIRECTION_REVERSED    = true;

// ==================================================
// MOTOR DATA TYPES
// ==================================================
struct Motor {
  int stepPin;
  int dirPin;
  int enablePin;
  bool directionReversed;
};

struct Move {
  char face;
  bool clockwise;
  int quarterTurns;
};

const Motor DOWN_MOTOR = {
  DOWN_STEP_PIN, DOWN_DIR_PIN, DOWN_EN_PIN,
  DOWN_DIRECTION_REVERSED
};

const Motor FRONT_MOTOR = {
  FRONT_STEP_PIN, FRONT_DIR_PIN, FRONT_EN_PIN,
  FRONT_DIRECTION_REVERSED
};

const Motor BACK_MOTOR = {
  BACK_STEP_PIN, BACK_DIR_PIN, BACK_EN_PIN,
  BACK_DIRECTION_REVERSED
};

const Motor RIGHT_MOTOR = {
  RIGHT_STEP_PIN, RIGHT_DIR_PIN, RIGHT_EN_PIN,
  RIGHT_DIRECTION_REVERSED
};

const Motor LEFT_MOTOR = {
  LEFT_STEP_PIN, LEFT_DIR_PIN, LEFT_EN_PIN,
  LEFT_DIRECTION_REVERSED
};

const Motor UP_MOTOR = {
  UP_STEP_PIN, UP_DIR_PIN, UP_EN_PIN,
  UP_DIRECTION_REVERSED
};

// ==================================================
// MOTOR HELPERS
// ==================================================
const Motor& motorForFace(char face) {
  if (face == 'D') return DOWN_MOTOR;
  if (face == 'F') return FRONT_MOTOR;
  if (face == 'B') return BACK_MOTOR;
  if (face == 'R') return RIGHT_MOTOR;
  if (face == 'L') return LEFT_MOTOR;
  return UP_MOTOR;
}

void disableAllMotors() {
  // TMC2209 EN is active LOW.
  digitalWrite(DOWN_EN_PIN, HIGH);
  digitalWrite(FRONT_EN_PIN, HIGH);
  digitalWrite(BACK_EN_PIN, HIGH);
  digitalWrite(RIGHT_EN_PIN, HIGH);
  digitalWrite(LEFT_EN_PIN, HIGH);
  digitalWrite(UP_EN_PIN, HIGH);
}

bool areOppositeFaces(char first, char second) {
  return
    (first == 'U' && second == 'D') ||
    (first == 'D' && second == 'U') ||
    (first == 'F' && second == 'B') ||
    (first == 'B' && second == 'F') ||
    (first == 'R' && second == 'L') ||
    (first == 'L' && second == 'R');
}

void enableMotorForMove(const Motor& motor, const Move& move) {
  bool physicalDirection =
    move.clockwise != motor.directionReversed;
  digitalWrite(motor.dirPin, physicalDirection ? HIGH : LOW);
  digitalWrite(motor.enablePin, LOW);
}

// ==================================================
// MOVE EXECUTION
// ==================================================
bool executeMoves(const Move& first, const Move* second) {
  const Motor& firstMotor = motorForFace(first.face);
  long firstSteps =
    (long)QUARTER_TURN_STEPS * first.quarterTurns;
  long secondSteps = 0;
  const Motor* secondMotor = NULL;

  if (second != NULL) {
    secondMotor = &motorForFace(second->face);
    secondSteps =
      (long)QUARTER_TURN_STEPS * second->quarterTurns;
  }

  long maximumSteps = firstSteps;
  if (secondSteps > maximumSteps) {
    maximumSteps = secondSteps;
  }

  // One move uses its normal/double-turn speed.
  int stepDelay = NORMAL_TURN_DELAY;
  if (second == NULL && first.quarterTurns == 2) {
    stepDelay = DOUBLE_TURN_DELAY;
  }

  // Two opposite moves use one shared safe timing value.
  if (second != NULL) {
    stepDelay = SIMULTANEOUS_TURN_DELAY;
  }

  disableAllMotors();
  delayMicroseconds(200);
  enableMotorForMove(firstMotor, first);
  if (second != NULL) {
    enableMotorForMove(*secondMotor, *second);
  }
  delayMicroseconds(200);

  for (long step = 0; step < maximumSteps; step++) {
    // Raise both STEP pins together.
    if (step < firstSteps) {
      digitalWrite(firstMotor.stepPin, HIGH);
    }
    if (second != NULL && step < secondSteps) {
      digitalWrite(secondMotor->stepPin, HIGH);
    }
    delayMicroseconds(stepDelay);

    // Lower both STEP pins together.
    if (step < firstSteps) {
      digitalWrite(firstMotor.stepPin, LOW);
    }
    if (second != NULL && step < secondSteps) {
      digitalWrite(secondMotor->stepPin, LOW);
    }
    delayMicroseconds(stepDelay);
  }

  disableAllMotors();
  return true;
}

// ==================================================
// ALGORITHM PARSER
// ==================================================
void skipSeparators(String sequence, int& index) {
  while (index < sequence.length()) {
    char character = sequence.charAt(index);
    if (
      character == ' ' ||
      character == ',' ||
      character == '\t'
    ) {
      index++;
    }
    else {
      return;
    }
  }
}

bool isValidFace(char face) {
  return
    face == 'U' ||
    face == 'D' ||
    face == 'F' ||
    face == 'B' ||
    face == 'R' ||
    face == 'L';
}

bool parseMove(String sequence, int& index, Move& move) {
  skipSeparators(sequence, index);
  if (index >= sequence.length()) {
    return false;
  }

  char face = sequence.charAt(index);
  if (!isValidFace(face)) {
    Serial.print("ERROR: invalid face: ");
    Serial.println(face);
    return false;
  }

  move.face = face;
  move.clockwise = true;
  move.quarterTurns = 1;
  index++;

  if (index < sequence.length()) {
    char suffix = sequence.charAt(index);
    if (suffix == '\'') {
      move.clockwise = false;
      index++;
    }
    else if (suffix == '2') {
      move.quarterTurns = 2;
      index++;
    }
  }

  return true;
}

void printMove(const Move& move) {
  Serial.print(move.face);
  if (move.quarterTurns == 2) {
    Serial.print("2");
  }
  else if (!move.clockwise) {
    Serial.print("'");
  }
}

bool executeSequence(String sequence) {
  sequence.trim();
  int index = 0;

  while (true) {
    skipSeparators(sequence, index);
    if (index >= sequence.length()) {
      return true;
    }

    Move first;
    if (!parseMove(sequence, index, first)) {
      disableAllMotors();
      return false;
    }

    // Look ahead without consuming the next move yet.
    int lookAheadIndex = index;
    Move second;
    bool hasSecondMove =
      parseMove(sequence, lookAheadIndex, second);

    // Run only adjacent opposite-face moves together.
    if (
      hasSecondMove &&
      areOppositeFaces(first.face, second.face)
    ) {
      Serial.print("Simultaneous: ");
      printMove(first);
      Serial.print(" + ");
      printMove(second);
      Serial.println();
      executeMoves(first, &second);
      // Consume the second move because it just ran.
      index = lookAheadIndex;
    }
    else {
      Serial.print("Executing: ");
      printMove(first);
      Serial.println();
      executeMoves(first, NULL);
    }
  }
}

// ==================================================
// SETUP + SERIAL LOOP
// ==================================================
void configureMotorPins(const Motor& motor) {
  pinMode(motor.enablePin, OUTPUT);
  digitalWrite(motor.enablePin, HIGH); // Start disabled.
  pinMode(motor.stepPin, OUTPUT);
  pinMode(motor.dirPin, OUTPUT);
  digitalWrite(motor.stepPin, LOW);
  digitalWrite(motor.dirPin, LOW);
}

void setup() {
  Serial.begin(115200);
  configureMotorPins(DOWN_MOTOR);
  configureMotorPins(FRONT_MOTOR);
  configureMotorPins(BACK_MOTOR);
  configureMotorPins(RIGHT_MOTOR);
  configureMotorPins(LEFT_MOTOR);
  configureMotorPins(UP_MOTOR);
  disableAllMotors();

  Serial.println("READY");
  Serial.println("Opposite adjacent moves run together.");
}

void loop() {
  if (Serial.available() > 0) {
    String sequence = Serial.readStringUntil('\n');
    sequence.trim();
    if (sequence.length() == 0) {
      return;
    }

    Serial.print("Sequence received: ");
    Serial.println(sequence);

    // Timer starts immediately before Rubi X executes move one.
    unsigned long startTime = micros();
    bool success = executeSequence(sequence);
    // Timer stops after the final driver is disabled.
    unsigned long elapsedMicroseconds = micros() - startTime;

    if (success) {
      float elapsedSeconds =
        elapsedMicroseconds / 1000000.0;
      Serial.println("DONE");
      Serial.print("Robot execution time: ");
      Serial.print(elapsedSeconds, 3);
      Serial.println(" seconds");
    }
    else {
      Serial.println("SEQUENCE FAILED");
    }
  }
}
