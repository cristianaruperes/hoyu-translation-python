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
text_buffers = {lang: "" for lang in ["zh"] + list(TARGET_LANGS.keys())}

def audio_callback(indata, frames, time, status):
    q.put(bytes(indata))

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

def translate_text(text):
    threading.Thread(target=_translate_task, args=(text,), daemon=True).start()

def _translate_task(text):
    for lang_code in TARGET_LANGS.keys():
        payload = {"q": text, "source": "zh", "target": lang_code, "format": "text"}
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
    text_buffers[lang_code] += f"{message}\n\n"
    if lang_code in open_windows:
        win = open_windows[lang_code]["text"]
        win.insert(tk.END, f"{message}\n\n")
        win.see(tk.END)

# ---- SAVE TRANSCRIPT ----
def save_transcript():
    combined = ["🈶 Chinese Transcript:\n", text_buffers["zh"].strip() + "\n\n"]
    for code, name in TARGET_LANGS.items():
        combined.append(f"🌐 {name} Translation:\n{text_buffers[code].strip()}\n\n")
    content = "\n".join(combined).strip()
    if not content:
        messagebox.showinfo("No Content", "There's no text to save yet.")
        return
    path = filedialog.asksaveasfilename(defaultextension=".txt",
                                        filetypes=[("Text Files", "*.txt")],
                                        title="Save Transcript As")
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        messagebox.showinfo("Saved", f"Transcript saved:\n{path}")

# ---- POPUP WINDOWS ----
open_windows = {}

def toggle_window(lang_code, title):
    if lang_code in open_windows:
        open_windows[lang_code]["window"].destroy()
        del open_windows[lang_code]
        log_message(f"❌ Closed {title} window.\n")
        return

    win = tk.Toplevel(root)
    win.title(title)
    win.geometry("600x400+200+200")
    win.configure(bg="#f4f4f4")

    label = tk.Label(win, text=title, font=("Arial", 16, "bold"), bg="#f4f4f4")
    label.pack(pady=5)

    text_area = ScrolledText(win, wrap=tk.WORD, font=("Arial", 18), bg="#ffffff")
    text_area.pack(fill="both", expand=True, padx=10, pady=10)

    # Restore text
    if lang_code in text_buffers:
        text_area.insert(tk.END, text_buffers[lang_code])
        text_area.see(tk.END)

    # Add presentation toggle
    pres_mode = tk.BooleanVar(value=False)
    def toggle_presentation():
        if not pres_mode.get():
            win.attributes('-fullscreen', True)
            text_area.config(font=("Arial", 36), bg="black", fg="white")
            label.config(bg="black", fg="white")
            pres_mode.set(True)
        else:
            win.attributes('-fullscreen', False)
            text_area.config(font=("Arial", 18), bg="white", fg="black")
            label.config(bg="#f4f4f4", fg="black")
            pres_mode.set(False)

    tk.Button(win, text="🖥 Presentation Mode", font=("Arial", 12),
              bg="#333", fg="white", command=toggle_presentation).pack(pady=5)

    open_windows[lang_code] = {"window": win, "text": text_area}
    win.protocol("WM_DELETE_WINDOW", lambda: close_window(lang_code, title))
    log_message(f"🪟 Opened {title} window.\n")

def close_window(lang_code, title):
    if lang_code in open_windows:
        open_windows[lang_code]["window"].destroy()
        del open_windows[lang_code]
        log_message(f"❌ Closed {title} window.\n")

# ---- MAIN WINDOW ----
root = tk.Tk()
root.title("🎧 Chinese → Multi-language Translator (Control Panel)")
root.geometry("650x650")

frame = tk.Frame(root, bg="#f4f4f4")
frame.pack(fill="both", expand=True, padx=10, pady=10)

main_log = ScrolledText(frame, wrap=tk.WORD, font=("Consolas", 11), height=15)
main_log.pack(fill="both", expand=True, padx=10, pady=10)

btn_frame = tk.Frame(root, bg="#f4f4f4")
btn_frame.pack(pady=10)

start_btn = tk.Button(btn_frame, text="🎧 Start Listening", font=("Arial", 13, "bold"),
                      bg="#4CAF50", fg="white", relief="raised", command=recognize_and_translate)
start_btn.pack(side=tk.LEFT, padx=10)

stop_btn = tk.Button(btn_frame, text="⏹ Stop", font=("Arial", 13, "bold"),
                     bg="#f44336", fg="white", relief="raised",
                     state=tk.DISABLED, command=stop_listening)
stop_btn.pack(side=tk.LEFT, padx=10)

save_btn = tk.Button(btn_frame, text="💾 Save Transcript", font=("Arial", 13, "bold"),
                     bg="#2196F3", fg="white", relief="raised",
                     command=save_transcript)
save_btn.pack(side=tk.LEFT, padx=10)

lang_frame = tk.LabelFrame(root, text="🌐 Open / Close Language Windows",
                           font=("Arial", 12, "bold"), bg="#f4f4f4")
lang_frame.pack(fill="x", padx=10, pady=10)

tk.Button(lang_frame, text="🈶 Chinese", font=("Arial", 12),
          bg="#E0E0E0", relief="raised",
          command=lambda: toggle_window("zh", "Chinese (Recognized)")).pack(fill="x", padx=10, pady=3)

for code, name in TARGET_LANGS.items():
    tk.Button(lang_frame, text=f"🌐 {name}", font=("Arial", 12),
              bg="#E0E0E0", relief="raised",
              command=lambda c=code, n=name: toggle_window(c, n)).pack(fill="x", padx=10, pady=3)

def log_message(msg):
    main_log.insert(tk.END, msg)
    main_log.see(tk.END)

log_message("✅ Ready.\nClick '🎧 Start Listening', then open translation windows.\nEach window has a Presentation Mode button for projector use.\n")

root.mainloop()
