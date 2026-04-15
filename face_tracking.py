# ================= IMPORTS =================
import cv2
import serial
import time
import mediapipe as mp
import threading
import sounddevice as sd
import json
import os
import uuid
import asyncio
import edge_tts
import playsound
import random
from vosk import Model, KaldiRecognizer
from datetime import datetime
import requests

# ================= SETTINGS =================
COM_PORT = "COM10"
CAMERA_ID = 1
USB_MIC_ID = 1

SERIAL_BAUD = 9600
SERIAL_DELAY = 0.03

WAKE_WORDS = ["wake up", "wake"]
NO_FACE_SLEEP_TIME = 1.2
SILENCE_TIMEOUT = 0.15

# ================= STATES =================
awake = False
speaking = False
eyes_closed = True
last_face_time = time.time()

speech_buffer = ""
last_speech_time = 0

# ================= SERIAL =================
arduino = serial.Serial(COM_PORT, SERIAL_BAUD, timeout=1, write_timeout=1)
time.sleep(2)

serial_lock = threading.Lock()

def safe_write(cmd):
    try:
        with serial_lock:
            arduino.write((cmd + "\n").encode())
            time.sleep(SERIAL_DELAY)
    except:
        pass

safe_write("CLOSE")

# ================= CAMERA =================
cap = cv2.VideoCapture(CAMERA_ID, cv2.CAP_DSHOW)

# ================= FACE =================
mp_face = mp.solutions.face_mesh
face_mesh = mp_face.FaceMesh(max_num_faces=1)

# ================= VOICE =================
vosk_model = Model("vosk-model-en-in-0.5")
rec = KaldiRecognizer(vosk_model, 16000)

# ================= SERVO =================
SERVO_CENTER = 310
SERVO_MAX = 510
V_CENTER = 350
V_RANGE = 80

smoothH = SERVO_CENTER
smoothV = V_CENTER

alphaH = 0.25
alphaV = 0.15
dead_zone = 30

last_track_send = 0
TRACK_INTERVAL = 0.05

# ================= AI (FAST OLLAMA) =================
def ask_ai(prompt):
    try:
        payload = {
            "model": "llama3",
            "prompt": (
                "You are PIXEL, a modern Indian humanoid robot.\n"
                "Do NOT use words like comrade, sir, madam, or political language.\n"
                "Speak neutral, friendly, and technical.\n"

                "Reply  SHORT like a human.\n"
                "Maximum ONE sentence.\n"
                "No explanations.\n\n"
                f"Human: {prompt}\nRobot:"
            ),
            "options": {
                "temperature": 0.2,
                "top_p": 0.8,
                "num_predict": 12,
                "stop": ["\n", "Human:", "Robot:"]

            },
            "stream": False
        }

        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=25
        )

        data = response.json()
        reply = data.get("response", "").strip()

        if "." in reply:1
        reply = reply.split(".")[0] + "."

        return reply or "Yes?"

    except Exception as e:
        print("OLLAMA ERROR:", e)
        return "I am not ready."

# ================= LOCAL COMMANDS =================
def handle_local_commands(text):
    now = datetime.now()
    text = text.strip().lower()

    # 🎂 Date of Birth (check first!)
    dob_keywords = [
        "date of birth",
        "your birthday",
        "when did you born"
        "when were you born",
        "when are you born",
        "your birth date",
        "when is your birthday",
        "what is your date of birth"
    ]
    if any(k in text for k in dob_keywords):
        return "My date of birth is 11 December 2025."

    # 👨‍🔧 Creator / Builder
    creator_keywords = [
        "who built you",
        "who created you",
        "who made you",
        "who developed you",
        "who found you",
        "your creator",
        "your builder",
        "your inventor"
    ]
    if any(k in text for k in creator_keywords):
        return "I was built by Team Alpha."

    # 🎓 Guide
    guide_keywords = [
        "your guide",
        "project guide",
        "who guided you",
        "who is your mentor",
        "who trained you"
    ]
    if any(k in text for k in guide_keywords):
        return ("My project guide is Vishwas sir at Srinivas University, "
                "mentoring me in robotics and AI projects for advanced learning.")

    # 🏫 University
    university_keywords = [
        "my university",
        "your university",
        "where do you study"
    ]
    if any(k in text for k in university_keywords):
        return ("I am based at Srinivas University in Mangalore, "
                "where I explore robotics, AI, and innovative technologies.")

    # ⏰ Time & Date
    if any(k in text for k in ["time", "current time", "what time"]):
        return now.strftime("It is %I:%M %p.")

    if any(k in text for k in ["date", "today's date", "what date"]):
        return now.strftime("Today is %d %B %Y.")

    # 🤖 Identity
    if any(k in text for k in ["your name", "who are you", "what are you"]):
        return "My name is PIXEL."

    return None


# ================= TTS =================
def speak(text):
    global speaking

    if speaking:
        return

    speaking = True
    print("🤖 PIXEL:", text)

    # Bluetooth wake-up silence
    playsound.playsound("silence.wav")

    filename = f"tts_{uuid.uuid4().hex}.mp3"

    async def run():
        tts = edge_tts.Communicate(text, "en-IN-PrabhatNeural")
        await tts.save(filename)

    asyncio.run(run())

    safe_write("SPEAK")
    playsound.playsound(filename)
    safe_write("STOP")

    os.remove(filename)
    speaking = False

# ================= BLINK THREAD =================
def blink_loop():
    while True:
        if awake and not speaking:
            safe_write("BLINK")
        time.sleep(random.uniform(3, 4))

threading.Thread(target=blink_loop, daemon=True).start()

# ================= VOICE LOOP =================
def voice_loop():
    global awake, eyes_closed, speech_buffer, last_speech_time

    stream = sd.RawInputStream(
        samplerate=16000,
        blocksize=2048,
        dtype="int16",
        channels=1,
        device=USB_MIC_ID
    )
    stream.start()

    while True:
        data, _ = stream.read(2048)

        if rec.AcceptWaveform(bytes(data)):
            result = json.loads(rec.Result())
            text = result.get("text", "").lower()

            if text:
                speech_buffer += " " + text
                last_speech_time = time.time()

        if speech_buffer and time.time() - last_speech_time > SILENCE_TIMEOUT:
            final_text = speech_buffer.strip()
            speech_buffer = ""

            print("🗣️ Heard:", final_text)

            if not awake:
                if any(w in final_text for w in WAKE_WORDS):
                    awake = True
                    eyes_closed = False
                    safe_write("OPEN")
                    speak("Yes?")
                continue

            local = handle_local_commands(final_text)
            if local:
                speak(local)
            else:
                if not speaking:
                    speak(ask_ai(final_text))

threading.Thread(target=voice_loop, daemon=True).start()

# ================= MAIN LOOP =================
while True:
    ret, frame = cap.read()
    if not ret:
        continue

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = face_mesh.process(rgb)

    face_detected = awake and result.multi_face_landmarks

    if face_detected:
        last_face_time = time.time()

        now = time.time()
        if now - last_track_send < TRACK_INTERVAL:
            cv2.imshow("PIXEL", frame)
            cv2.waitKey(1)
            continue

        last_track_send = now

        nose = result.multi_face_landmarks[0].landmark[1]
        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2
        fx, fy = int(nose.x * w), int(nose.y * h)

        dx, dy = fx - cx, fy - cy
        if abs(dx) < dead_zone: dx = 0
        if abs(dy) < dead_zone: dy = 0

        nx, ny = -dx / cx, -dy / cy
        smoothH += int(alphaH * ((SERVO_CENTER + nx * (SERVO_MAX - SERVO_CENTER)) - smoothH))
        smoothV += int(alphaV * ((V_CENTER + ny * V_RANGE) - smoothV))

        safe_write(f"{smoothH},{smoothV}")

    if awake and not face_detected and time.time() - last_face_time > NO_FACE_SLEEP_TIME:
        awake = False
        eyes_closed = True
        safe_write("CLOSE")

    cv2.imshow("Animatronic Robot PIXEL", frame)
    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()
arduino.close()
