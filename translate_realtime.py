import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import requests
import json
import sounddevice as sd
import queue
from vosk import Model, KaldiRecognizer
import threading

# ---- CONFIG ----
VOSK_MODEL_PATH = "vosk-model-cn-0.22"  # Path to your Vosk Chinese model
LIBRE_URL = "http://localhost:5000/translate"

TARGET_LANGS = {
    "en": "English",
    "tl": "Tagalog",
    "id": "Indonesian",
    "th": "Thai",
    "vi": "Vietnamese"  
}

# ---- INIT AUDIO + VOSK ----
model = Model(VOSK_MODEL_PATH)
rec = KaldiRecognizer(model, 16000)
q = queue.Queue()

def audio_callback(indata, frames, time, status):
    q.put(bytes(indata))

def recognize_and_translate():
    start_btn.config(state=tk.DISABLED)
    gui_log("\n🎙 Listening... Speak Chinese now.\n")
    threading.Thread(target=listen_loop, daemon=True).start()

def listen_loop():
    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=audio_callback):
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "").strip()
                if text:
                    gui_log(f"\n🈶 Chinese: {text}\n")
                    translate_text(text)
                    gui_log("\n---\nListening again...\n")

def translate_text(text):
    for lang_code, lang_name in TARGET_LANGS.items():
        payload = {
            "q": text,
            "source": "zh",
            "target": lang_code,
            "format": "text"
        }
        try:
            response = requests.post(LIBRE_URL, data=payload, timeout=10)
            if response.ok:
                translated = response.json().get("translatedText", "")
                gui_log(f"{lang_name}: {translated}\n")
            else:
                gui_log(f"{lang_name}: ❌ Error ({response.status_code})\n")
        except Exception as e:
            gui_log(f"{lang_name}: ⚠️ {e}\n")

# ---- GUI ----
def gui_log(message):
    text_area.insert(tk.END, message)
    text_area.see(tk.END)
    root.update_idletasks()

root = tk.Tk()
root.title("Realtime Chinese → Multi-language Translator (LibreTranslate)")
root.geometry("800x600")

frame = tk.Frame(root, bg="#f4f4f4")
frame.pack(fill="both", expand=True, padx=10, pady=10)

text_area = ScrolledText(frame, wrap=tk.WORD, font=("Consolas", 11), height=25)
text_area.pack(fill="both", expand=True, padx=10, pady=(0, 10))

start_btn = tk.Button(frame, text="🎧 Start Listening", font=("Arial", 14, "bold"),
                      bg="#4CAF50", fg="white", relief="raised", command=recognize_and_translate)
start_btn.pack(pady=5)

gui_log("✅ Ready.\nClick '🎧 Start Listening' and start speaking Chinese...\n")

root.mainloop()
