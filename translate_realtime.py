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
stop_flag = threading.Event()

def audio_callback(indata, frames, time, status):
    q.put(bytes(indata))

# ---- LISTENING LOGIC ----
def recognize_and_translate():
    start_btn.config(state=tk.DISABLED)
    stop_btn.config(state=tk.NORMAL)
    stop_flag.clear()
    gui_log("\n🎙 Listening... Speak Chinese now.\n")
    threading.Thread(target=listen_loop, daemon=True).start()

def stop_listening():
    stop_flag.set()
    start_btn.config(state=tk.NORMAL)
    stop_btn.config(state=tk.DISABLED)
    gui_log("\n🛑 Stopped listening.\n")

def listen_loop():
    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=audio_callback):
        partial_text = ""
        while not stop_flag.is_set():
            data = q.get()
            if rec.AcceptWaveform(data):
                # Full result
                result = json.loads(rec.Result())
                text = result.get("text", "").strip()
                if text:
                    gui_log(f"\n🈶 Chinese: {text}\n")
                    translate_text(text)
                    gui_log("\n---\nListening again...\n")
            else:
                # Partial (live text)
                partial = json.loads(rec.PartialResult()).get("partial", "").strip()
                if partial and partial != partial_text:
                    partial_text = partial
                    update_partial(partial_text)

# ---- TRANSLATION LOGIC ----
def translate_text(text):
    threading.Thread(target=_translate_task, args=(text,), daemon=True).start()

def _translate_task(text):
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
    if "Listening" in message:
        root.title("🎧 Listening… Chinese → Multi-language Translator")
    elif "Stopped" in message:
        root.title("⏹ Stopped — Realtime Translator")
    root.update_idletasks()

def update_partial(partial_text):
    partial_label.config(text=f"🗣️ Live Chinese: {partial_text}")

# ---- TKINTER UI ----
root = tk.Tk()
root.title("Realtime Chinese → Multi-language Translator (LibreTranslate)")
root.geometry("800x650")

frame = tk.Frame(root, bg="#f4f4f4")
frame.pack(fill="both", expand=True, padx=10, pady=10)

partial_label = tk.Label(frame, text="🗣️ Live Chinese: ", font=("Arial", 13), bg="#f4f4f4", anchor="w")
partial_label.pack(fill="x", pady=(0, 5))

text_area = ScrolledText(frame, wrap=tk.WORD, font=("Consolas", 11), height=25)
text_area.pack(fill="both", expand=True, padx=10, pady=(0, 10))

btn_frame = tk.Frame(frame, bg="#f4f4f4")
btn_frame.pack(pady=5)

start_btn = tk.Button(btn_frame, text="🎧 Start Listening", font=("Arial", 14, "bold"),
                      bg="#4CAF50", fg="white", relief="raised",
                      command=recognize_and_translate)
start_btn.pack(side=tk.LEFT, padx=10)

stop_btn = tk.Button(btn_frame, text="⏹ Stop Listening", font=("Arial", 14, "bold"),
                     bg="#f44336", fg="white", relief="raised",
                     state=tk.DISABLED, command=stop_listening)
stop_btn.pack(side=tk.LEFT, padx=10)

gui_log("✅ Ready.\nClick '🎧 Start Listening' and start speaking Chinese...\n")

root.mainloop()
