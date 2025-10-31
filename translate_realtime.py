import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import filedialog, messagebox
import requests
import json
import sounddevice as sd
import queue
from vosk import Model, KaldiRecognizer
import threading

# ---- CONFIG ----
VOSK_MODEL_PATH = "vosk-model-cn-0.22"
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
    log_message("🎙 Listening... Speak Chinese now.\n")
    threading.Thread(target=listen_loop, daemon=True).start()

def stop_listening():
    stop_flag.set()
    start_btn.config(state=tk.NORMAL)
    stop_btn.config(state=tk.DISABLED)
    log_message("🛑 Stopped listening.\n")

def listen_loop():
    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=audio_callback):
        while not stop_flag.is_set():
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "").strip()
                if text:
                    update_window("zh", text)
                    translate_text(text)

# ---- TRANSLATION LOGIC ----
def translate_text(text):
    threading.Thread(target=_translate_task, args=(text,), daemon=True).start()

def _translate_task(text):
    for lang_code in TARGET_LANGS.keys():
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
                update_window(lang_code, translated)
            else:
                update_window(lang_code, f"❌ Error ({response.status_code})")
        except Exception as e:
            update_window(lang_code, f"⚠️ {e}")

# ---- GUI LOGIC ----
def update_window(lang_code, message):
    text_widget = windows[lang_code]["text"]
    text_widget.insert(tk.END, f"{message}\n\n")
    text_widget.see(tk.END)

def log_message(msg):
    main_log.insert(tk.END, msg)
    main_log.see(tk.END)

# ---- SAVE TRANSCRIPT ----
def save_transcript():
    combined = []
    combined.append("🈶 Chinese Transcript:\n")
    combined.append(windows["zh"]["text"].get("1.0", tk.END).strip() + "\n\n")
    for code, name in TARGET_LANGS.items():
        combined.append(f"🌐 {name} Translation:\n")
        combined.append(windows[code]["text"].get("1.0", tk.END).strip() + "\n\n")

    content = "\n".join(combined).strip()
    if not content:
        messagebox.showinfo("No Content", "There's no text to save yet.")
        return

    file_path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text Files", "*.txt")],
        title="Save Transcript As"
    )

    if file_path:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        messagebox.showinfo("Saved", f"Transcript saved successfully:\n{file_path}")

# ---- WINDOW CREATION ----
def create_window(title, color, position):
    win = tk.Toplevel(root)
    win.title(title)
    win.geometry(f"400x400+{position[0]}+{position[1]}")
    win.configure(bg="#f4f4f4")

    label = tk.Label(win, text=title, font=("Arial", 14, "bold"), bg="#f4f4f4", fg=color)
    label.pack(pady=5)

    text = ScrolledText(win, wrap=tk.WORD, font=("Consolas", 11))
    text.pack(fill="both", expand=True, padx=10, pady=10)
    return {"window": win, "text": text}

# ---- MAIN CONTROL WINDOW ----
root = tk.Tk()
root.title("🎧 Chinese → Multi-language Translator (Main Control)")
root.geometry("500x400")

control_frame = tk.Frame(root, bg="#f4f4f4")
control_frame.pack(fill="both", expand=True, padx=10, pady=10)

main_log = ScrolledText(control_frame, wrap=tk.WORD, font=("Consolas", 11), height=10)
main_log.pack(fill="both", expand=True, padx=10, pady=10)

btn_frame = tk.Frame(root, bg="#f4f4f4")
btn_frame.pack(pady=10)

start_btn = tk.Button(btn_frame, text="🎧 Start Listening", font=("Arial", 14, "bold"),
                      bg="#4CAF50", fg="white", relief="raised",
                      command=recognize_and_translate)
start_btn.pack(side=tk.LEFT, padx=10)

stop_btn = tk.Button(btn_frame, text="⏹ Stop", font=("Arial", 14, "bold"),
                     bg="#f44336", fg="white", relief="raised",
                     state=tk.DISABLED, command=stop_listening)
stop_btn.pack(side=tk.LEFT, padx=10)

save_btn = tk.Button(btn_frame, text="💾 Save Transcript", font=("Arial", 14, "bold"),
                     bg="#2196F3", fg="white", relief="raised",
                     command=save_transcript)
save_btn.pack(side=tk.LEFT, padx=10)

# ---- CREATE TRANSLATION WINDOWS ----
windows = {}
colors = ["#333", "#007BFF", "#28A745", "#FFC107", "#9C27B0", "#FF5722"]
positions = [(50, 100), (500, 100), (950, 100), (50, 550), (500, 550), (950, 550)]

# Main (Chinese) window
windows["zh"] = create_window("🈶 Chinese (Recognized)", "#333", positions[0])

# Translation windows
for (code, name), pos, color in zip(TARGET_LANGS.items(), positions[1:], colors[1:]):
    windows[code] = create_window(f"{name}", color, pos)

log_message("✅ Ready.\nClick '🎧 Start Listening' and start speaking Chinese...\n")

root.mainloop()
