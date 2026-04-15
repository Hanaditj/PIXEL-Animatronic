# PIXEL — AI-Powered Animatronic Humanoid Eye System

> Real-time face tracking, offline speech recognition, local LLM inference, and servo-driven animatronic eyes — built from scratch using Python, Arduino, and a custom 3D-printed mechanical system.

---

## Demo



---<img width="523" height="474" alt="image" src="https://github.com/user-attachments/assets/1ec81d7f-2fd2-4446-835e-722260fa3306" />


## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     HOST COMPUTER                        │
│                                                          │
│  ┌──────────────┐   ┌──────────────┐  ┌──────────────┐  │
│  │  Vision      │   │  Voice       │  │  AI Engine   │  │
│  │  Pipeline    │   │  Pipeline    │  │  (Ollama     │  │
│  │  (MediaPipe) │   │  (Vosk STT)  │  │   llama3)    │  │
│  └──────┬───────┘   └──────┬───────┘  └──────┬───────┘  │
│         │                  │                  │          │
│         └──────────────────┴──────────────────┘          │
│                            │                             │
│                   Serial Protocol (9600 baud)            │
└────────────────────────────┼────────────────────────────┘
                             │ USB / UART
┌────────────────────────────▼────────────────────────────┐
│                    ARDUINO UNO                           │
│                                                          │
│          PCA9685 PWM Driver (I2C, 0x40)                  │
│                                                          │
│   CH0: Left Upper Eyelid    CH4: Eye Horizontal Pan      │
│   CH1: Left Lower Eyelid    CH5: Eye Vertical Tilt       │
│   CH2: Right Upper Eyelid   CH6: Mouth Servo             │
│   CH3: Right Lower Eyelid                                │
└─────────────────────────────────────────────────────────┘
```

---

## Features

| Feature | Implementation |
|---|---|
| Real-time face tracking | MediaPipe FaceMesh, landmark [1] (nose tip) |
| Servo smoothing | Exponential moving average (α=0.25H, α=0.15V) + dead zone |
| Wake word detection | Offline Vosk (vosk-model-en-in-0.5) |
| Natural language response | Local Ollama llama3 inference |
| Text-to-speech | Microsoft Edge TTS (en-IN-PrabhatNeural) |
| Eyelid control | 4-servo synchronized open/close/blink |
| Mouth animation | PWM-driven sync with speech output |
| Thread safety | `threading.Lock()` on serial writes |
| Concurrent execution | Vision, voice, blink on separate daemon threads |

---

## Hardware

| Component | Specification |
|---|---|
| Microcontroller | Arduino Uno |
| PWM Driver | Adafruit PCA9685 (16-channel, I2C) |
| Servos | 7× SG90 / MG90S micro servos |
| Camera | USB Webcam (1080p) |
| Microphone | USB Microphone |
| Structure | Custom 3D-printed animatronic eye mechanism |

**Wiring:**
```
Arduino → PCA9685 via I2C (SDA → A4, SCL → A5)
PCA9685 CH0–3 → Eyelid servos
PCA9685 CH4   → Horizontal eye pan servo
PCA9685 CH5   → Vertical eye tilt servo
PCA9685 CH6   → Mouth servo
```

---

## Serial Communication Protocol

Python sends commands over UART (9600 baud) to Arduino:

| Command | Action |
|---|---|
| `OPEN` | Open both eyes |
| `CLOSE` | Close both eyes (sleep state) |
| `BLINK` | Single blink animation (220ms close / 180ms open) |
| `SPEAK` | Start mouth animation loop |
| `STOP` | Stop mouth, close it |
| `{H},{V}` | Set eye pan/tilt pulse values (e.g. `310,350`) |

---

## Software Setup

### Requirements

```bash
pip install opencv-python mediapipe pyserial sounddevice edge-tts playsound vosk requests
```

### Ollama (Local LLM)
```bash
# Install Ollama: https://ollama.com
ollama pull llama3
ollama serve
```

### Vosk Model
Download [vosk-model-en-in-0.5](https://alphacephei.com/vosk/models) and place in project root.

### Arduino
1. Install `Adafruit PWM Servo Driver Library` via Arduino Library Manager
2. Flash `arduino/PIXEL_firmware.ino` to Arduino Uno
3. Note the COM port and update `COM_PORT` in `face_tracking.py`

### Run
```bash
python vision/face_tracking.py
```
Say **"wake up"** to activate PIXEL.

---

## Repository Structure

```
PIXEL-Animatronic/
├── arduino/
│   └── PIXEL_firmware.ino      # Arduino servo + mouth control firmware
├── vision/
│   └── face_tracking.py        # Main Python: vision + voice + AI pipeline
├── assets/
│   └── silence.wav             # BT speaker wake-up audio (required)
└── README.md
```

---

## Key Technical Decisions

**Why exponential smoothing on servos?**
Raw pixel-to-servo mapping causes jitter from MediaPipe's per-frame landmark variance. EMA with α=0.25 (horizontal) and α=0.15 (vertical) trades response speed for stability. Vertical uses lower α because eye tilt looks more unnatural when jittery.

**Why offline Vosk instead of cloud STT?**
Latency. Cloud APIs add 300–800ms round trip. Vosk runs on-device at ~50ms, critical for a responsive conversational system.

**Why local Ollama instead of OpenAI API?**
Privacy + zero latency variance. The robot runs fully air-gapped after setup.

---

## Author

**Hanadi Thaisir Jaradath**
B.Tech — Robotics, AI & ML | Srinivas University, Mangalore
[LinkedIn](https://linkedin.com/in/hanadi-thaisir-jaradath) | hanaditj31@gmail.com

---

## License

MIT License — free to use, modify, and build upon.
