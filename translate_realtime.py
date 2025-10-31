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

# In-memory text storage (persists even when popup closed)
text_buffers = {lang: "" for lang in ["zh"] + list(TARGET_LANGS.keys())}

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
                    update_text("zh", text)
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
                update_text(lang_code, translated)
            else:
                update_text(lang_code, f"❌ Error ({response.status_code})")
        except Exception as e:
            update_text(lang_code, f"⚠️ {e}")

# ---- TEXT HANDLING ----
def update_text(lang_code, message):
    global text_buffers
    text_buffers[lang_code] += f"{message}\n\n"

    # If window for this language is open, update its display
    if lang_code in open_windows:
        win = open_windows[lang_code]["text"]
        win.insert(tk.END, f"{message}\n\n")
        win.see(tk.END)

# ---- SAVE TRANSCRIPT ----
def save_transcript():
    combined = []
    combined.append("🈶 Chinese Transcript:\n")
    combined.append(text_buffers["zh"].strip() + "\n\n")
    for code, name in TARGET_LANGS.items():
        combined.append(f"🌐 {name} Translation:\n")
        combined.append(text_buffers[code].strip() + "\n\n")

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

# ---- POPUP LOGIC ----
open_windows = {}

def toggle_window(lang_code, title):
    """Opens or closes a language window on button press."""
    if lang_code in open_windows:
        # Close it
        open_windows[lang_code]["window"].destroy()
        del open_windows[lang_code]
        log_message(f"❌ Closed {title} window.\n")
        return

    # Otherwise create it
    win = tk.Toplevel(root)
    win.title(title)
    win.geometry("400x400+100+100")
    win.configure(bg="#f4f4f4")

    label = tk.Label(win, text=title, font=("Arial", 14, "bold"), bg="#f4f4f4")
    label.pack(pady=5)

    text_area = ScrolledText(win, wrap=tk.WORD, font=("Consolas", 11))
    text_area.pack(fill="both", expand=True, padx=10, pady=10)

    # Load previous content if exists
    if lang_code in text_buffers:
        text_area.insert(tk.END, text_buffers[lang_code])
        text_area.see(tk.END)

    open_windows[lang_code] = {"window": win, "text": text_area}

    # Handle when user manually closes window (X button)
    def on_close():
        if lang_code in open_windows:
            del open_windows[lang_code]
        win.destroy()
        log_message(f"❌ Closed {title} window.\n")

    win.protocol("WM_DELETE_WINDOW", on_close)
    log_message(f"🪟 Opened {title} window.\n")

# ---- MAIN CONTROL WINDOW ----
root = tk.Tk()
root.title("🎧 Chinese → Multi-language Translator (Main Control)")
root.geometry("600x600")

control_frame = tk.Frame(root, bg="#f4f4f4")
control_frame.pack(fill="both", expand=True, padx=10, pady=10)

main_log = ScrolledText(control_frame, wrap=tk.WORD, font=("Consolas", 11), height=15)
main_log.pack(fill="both", expand=True, padx=10, pady=10)

btn_frame = tk.Frame(root, bg="#f4f4f4")
btn_frame.pack(pady=10)

start_btn = tk.Button(btn_frame, text="🎧 Start Listening", font=("Arial", 13, "bold"),
                      bg="#4CAF50", fg="white", relief="raised",
                      command=recognize_and_translate)
start_btn.pack(side=tk.LEFT, padx=10)

stop_btn = tk.Button(btn_frame, text="⏹ Stop", font=("Arial", 13, "bold"),
                     bg="#f44336", fg="white", relief="raised",
                     state=tk.DISABLED, command=stop_listening)
stop_btn.pack(side=tk.LEFT, padx=10)

save_btn = tk.Button(btn_frame, text="💾 Save Transcript", font=("Arial", 13, "bold"),
                     bg="#2196F3", fg="white", relief="raised",
                     command=save_transcript)
save_btn.pack(side=tk.LEFT, padx=10)

# ---- LANGUAGE WINDOW BUTTONS ----
lang_frame = tk.LabelFrame(root, text="🌐 Open / Close Language Windows", font=("Arial", 12, "bold"), bg="#f4f4f4")
lang_frame.pack(fill="x", padx=10, pady=10)

# Add Chinese first
tk.Button(lang_frame, text="🈶 Chinese", font=("Arial", 12),
          bg="#E0E0E0", relief="raised",
          command=lambda: toggle_window("zh", "Chinese (Recognized)")).pack(fill="x", padx=10, pady=3)

# Then all translations
for code, name in TARGET_LANGS.items():
    tk.Button(lang_frame, text=f"🌐 {name}", font=("Arial", 12),
              bg="#E0E0E0", relief="raised",
              command=lambda c=code, n=name: toggle_window(c, n)).pack(fill="x", padx=10, pady=3)

# ---- LOG MESSAGE HELPER ----
def log_message(msg):
    main_log.insert(tk.END, msg)
    main_log.see(tk.END)

log_message("✅ Ready.\nClick '🎧 Start Listening' and open language windows as needed.\n")

root.mainloop()
