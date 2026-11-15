"""Gojo local desktop companion.

A rule-based Python assistant with no external AI model/API. It supports:
- typed chat and optional voice input
- local text-to-speech if installed
- quick action buttons
- approval before opening apps, URLs, or saving files
- study task storage
- Tailwind website generation (max 6)
- Unreal project scaffold
- animated chibi mascot that walks and leaves the screen when upset
"""
import html
import os
import platform
import re
import shutil
import sqlite3
import subprocess
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus
import tkinter as tk
from tkinter import filedialog, ttk

try:
    import pyttsx3
except ImportError:  # pragma: no cover
    pyttsx3 = None

try:
    import speech_recognition as sr
except ImportError:  # pragma: no cover
    sr = None

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "gojo_local.sqlite3"
BG = "#0b1020"


def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("CREATE TABLE IF NOT EXISTS chat (id INTEGER PRIMARY KEY, role TEXT, text TEXT, at TEXT)")
        con.execute("CREATE TABLE IF NOT EXISTS study (id INTEGER PRIMARY KEY, subject TEXT NOT NULL, done INTEGER DEFAULT 0)")


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "gojo-project"


class GojoApp:
    def __init__(self, root):
        self.root = root
        root.title("Gojo — Local Companion")
        root.geometry("1040x720")
        root.minsize(720, 520)
        root.configure(bg=BG)
        self.pending = None
        self.tts_active = False
        self.voice_queue = []
        self.tts = self._start_tts()
        self._ui()
        self._history()
        self._pet_loop()
        self.say("Gojo", "Hey! I’m your local Gojo companion. I can chat, talk, create study tasks, build templates, and run safe actions only after approval.")

    def _start_tts(self):
        if not pyttsx3:
            return False
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 175)
            self.voice_engine = engine
            self.tts_active = True
            return True
        except Exception:
            self.tts_active = False
            return False

    def _ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", padding=7)

        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True, padx=18, pady=14)

        left = tk.Frame(outer, bg=BG)
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(outer, bg="#11172a", width=260)
        right.pack(side="right", fill="y", padx=(14, 0))
        right.pack_propagate(False)

        tk.Label(left, text="✦ GOJO", bg=BG, fg="#e7dcff", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        self.status = tk.StringVar(value="Local rule-based companion • no cloud AI")
        tk.Label(left, textvariable=self.status, bg=BG, fg="#aaa7c1", font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 8))

        self.chat = tk.Text(left, wrap="word", state="disabled", bg="#12182a", fg="#f3f2fa", insertbackground="white", relief="flat", font=("Segoe UI", 10), padx=12, pady=12)
        self.chat.pack(fill="both", expand=True)
        self.chat.tag_config("Gojo", foreground="#c9b5ff", font=("Segoe UI", 10, "bold"))
        self.chat.tag_config("You", foreground="#85e4ef", font=("Segoe UI", 10, "bold"))
        self.chat.tag_config("body", foreground="#f0eff7")

        self.approvals = ttk.Frame(left)
        self.ok_btn = ttk.Button(self.approvals, text="Approve", command=self.approve)
        self.no_btn = ttk.Button(self.approvals, text="Cancel", command=self.cancel)

        row = ttk.Frame(left)
        row.pack(fill="x", pady=(8, 0))
        self.entry = ttk.Entry(row)
        self.entry.pack(side="left", fill="x", expand=True, ipady=9, padx=(0, 7))
        self.entry.bind("<Return>", lambda _e: self.send())

        ttk.Button(row, text="Send", command=self.send).pack(side="left", padx=(0, 5))
        ttk.Button(row, text="🎙 Speak", command=self.listen).pack(side="left", padx=(0, 5))
        ttk.Button(row, text="Stop", command=self.stop).pack(side="left")

        tk.Label(right, text="YOUR COMPANION", bg="#11172a", fg="#aaa0d2", font=("Segoe UI", 9, "bold")).pack(pady=(13, 6))
        self.pet_canvas = tk.Canvas(right, width=235, height=330, bg="#151b30", highlightthickness=0)
        self.pet_canvas.pack(padx=10, pady=5)

        tk.Label(right, text="Quick actions", bg="#11172a", fg="#eee9ff", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(8, 4))
        actions = [
            ("Study planner", self.show_study),
            ("Create a website", lambda: self.quick("create a website for my project")),
            ("Unreal project", lambda: self.quick("create an Unreal game project named GojoGame")),
            ("Open an app", lambda: self.quick("open Notepad")),
        ]
        for label, callback in actions:
            ttk.Button(right, text=label, command=callback).pack(fill="x", padx=12, pady=3)

        self.pet_x = 42
        self.pet_direction = 1
        self.pet_mood = "happy"
        self.pet_hidden = False
        self.pet_step = 0
        self.draw_pet()

    def _history(self):
        with sqlite3.connect(DB_PATH) as con:
            rows = con.execute("SELECT role, text FROM chat ORDER BY id DESC LIMIT 50").fetchall()
        for role, text in reversed(rows):
            self.write(("You" if role == "user" else "Gojo"), text, persist=False, speak=False)

    def write(self, who, text, persist=True, speak=True):
        self.chat.configure(state="normal")
        self.chat.insert("end", who + "  ", who)
        self.chat.insert("end", text + "\n\n", "body")
        self.chat.configure(state="disabled")
        self.chat.see("end")
        if persist:
            with sqlite3.connect(DB_PATH) as con:
                con.execute("INSERT INTO chat(role, text, at) VALUES (?, ?, ?)", ("user" if who == "You" else "assistant", text, datetime.now().isoformat(timespec="seconds")))
        if speak and who == "Gojo" and self.tts_active and hasattr(self, "voice_engine"):
            try:
                self.voice_engine.say(text)
                threading.Thread(target=self.voice_engine.runAndWait, daemon=True).start()
            except Exception:
                pass

    def say(self, who, text):
        self.write(who, text, persist=True, speak=True)

    def quick(self, command):
        self.entry.delete(0, "end")
        self.entry.insert(0, command)
        self.send()

    def send(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")

        if text.lower().strip(".! ") in {"stop", "stop it", "cancel", "pause"}:
            self.stop()
            return

        self.say("You", text)
        if self.pending:
            self.say("Gojo", "Please approve or cancel the pending action first.")
            return

        low = text.lower()
        if any(p in low for p in ("i'm pissed", "im pissed", "i am pissed", "i'm angry", "im angry", "i am angry", "go away", "leave me alone", "mad at you")):
            self.pet_leave()
            self.say("Gojo", "Okay, I’ll give you space. Say ‘come back’ when you want me.")
            return
        if "come back" in low or "return gojo" in low:
            self.pet_return()
            self.say("Gojo", "I’m back. Ready for the next step.")
            return

        self.handle(text)

    def handle(self, text):
        low = text.lower().strip()

        app_match = re.fullmatch(r"(?:please\s+)?(?:open|launch|start)\s+(notepad|calculator|calc|paint|file explorer|explorer|chrome|edge|unreal(?: engine)?)", low)
        if app_match:
            app = app_match.group(1)
            self.ask(f"open {app}", lambda: self.open_app(app))
            return

        search_match = re.match(r"(?:search for|look up|google)\s+(.+)", text, re.I)
        if search_match:
            query = search_match.group(1).strip()
            self.ask(f"search the web for ‘{query}’", lambda: self.open_search(query))
            return

        url_match = re.match(r"open\s+(https?://\S+)", text, re.I)
        if url_match:
            url = url_match.group(1)
            self.ask(f"open {url}", lambda: self.open_url(url))
            return

        website_match = re.match(r"(?:create|make|build)\s+(?:(\d+)\s+)?(?:tailwind\s+)?websites?(?:\s+(?:for|about))?\s*(.*)", text, re.I)
        if website_match:
            count = min(6, max(1, int(website_match.group(1) or 1)))
            topic = website_match.group(2).strip() or "My project"
            self.ask(f"create {count} Tailwind website(s) about ‘{topic}’", lambda: self.create_sites(topic, count))
            return

        unreal_match = re.search(r"\b(unreal|ue5|ue 5)\b", low) and re.search(r"\b(create|make|new|start|project|game)\b", low)
        if unreal_match:
            named = re.search(r"(?:named|called)\s+([\w -]+)", text, re.I)
            name = named.group(1).strip() if named else "GojoGame"
            self.ask(f"create an Unreal project scaffold named {name}", lambda: self.create_unreal(name))
            return

        if re.match(r"(?:add|plan|schedule)\s+(?:study\s+)?(?:task\s+)?", low):
            subject = re.sub(r"^(?:add|plan|schedule)\s+(?:study\s+)?(?:task\s+)?", "", text, flags=re.I).strip()
            if subject:
                self.ask(f"save ‘{subject}’ in your study planner", lambda: self.add_study(subject))
            else:
                self.show_study()
            return

        if any(s in low for s in ("show study", "study planner", "my study plan", "list study")):
            self.show_study()
            return

        if low in {"hi", "hello", "hey", "hey gojo"}:
            self.say("Gojo", "Hey! What are we doing today?")
            return

        if "help" in low or "what can you do" in low:
            self.say("Gojo", "I can talk, open safe apps, save study tasks, create up to six Tailwind websites, and scaffold an Unreal project. I’m a local rule-based companion, not a full AI model.")
            return

        if "study" in low or "homework" in low:
            self.say("Gojo", "Try: ‘add study task Biology chapter 3’ or ‘show study planner’.")
            return

        self.say("Gojo", "I’m local and rule-based, so I only understand the built-in commands. Try ‘help’ for the list.")

    def ask(self, description, callback):
        self.pending = callback
        self.status.set("Waiting for approval — nothing has happened yet")
        self.say("Gojo", f"I can {description}. Approve or cancel?")
        self.approvals.pack(fill="x", pady=(7, 0))
        self.ok_btn.pack(side="left", padx=(0, 7))
        self.no_btn.pack(side="left")

    def clear_approval(self):
        self.pending = None
        self.ok_btn.pack_forget(); self.no_btn.pack_forget(); self.approvals.pack_forget()

    def approve(self):
        action = self.pending
        self.clear_approval()
        if not action:
            return
        try:
            action()
        except Exception as exc:
            self.status.set("Action failed")
            self.say("Gojo", f"Could not complete that: {exc}")

    def cancel(self):
        self.clear_approval()
        self.status.set("Cancelled — nothing done")
        self.say("Gojo", "Cancelled. Nothing was done.")

    def stop(self):
        self.clear_approval()
        self.status.set("Stopped")
        self.say("Gojo", "Stopped. I’m listening.")

    def open_app(self, app):
        app = {"calc": "calculator", "explorer": "file explorer", "unreal engine": "unreal"}.get(app, app)

        if app == "unreal":
            exe = os.environ.get("UE_EDITOR_PATH") or shutil.which("UnrealEditor") or shutil.which("UnrealEditor.exe")
            if not exe or not Path(exe).exists():
                self.say("Gojo", "Unreal Editor wasn’t found. Set UE_EDITOR_PATH to the executable path if it’s installed.")
                return
            subprocess.Popen([exe])
            self.status.set("Unreal Editor launched")
            self.say("Gojo", "Opened Unreal Editor.")
            return

        system = platform.system()
        if system == "Windows":
            mapping = {"notepad": "notepad.exe", "calculator": "calc.exe", "paint": "mspaint.exe", "file explorer": "explorer.exe", "chrome": "chrome.exe", "edge": "msedge.exe"}
            exe = mapping.get(app)
            if not exe:
                self.say("Gojo", f"I don’t allow that app: {app}")
                return
            path = shutil.which(exe)
            if not path:
                self.say("Gojo", f"I couldn’t find {app} on this machine.")
                return
            subprocess.Popen([path])
            self.status.set(f"Opened {app}")
            self.say("Gojo", f"Opened {app}.")
            return

        if system == "Darwin":
            mapping = {"notepad": "TextEdit", "calculator": "Calculator", "paint": "Preview", "file explorer": "Finder", "chrome": "Google Chrome", "edge": "Microsoft Edge"}
            name = mapping.get(app)
            if not name:
                self.say("Gojo", f"I don’t allow that app: {app}")
                return
            subprocess.Popen(["open", "-a", name])
            self.status.set(f"Opened {app}")
            self.say("Gojo", f"Opened {app}.")
            return

        mapping = {"notepad": "gedit", "calculator": "gnome-calculator", "paint": "pinta", "file explorer": "xdg-open", "chrome": "google-chrome", "edge": "microsoft-edge"}
        exe = mapping.get(app)
        if not exe:
            self.say("Gojo", f"I don’t allow that app: {app}")
            return
        path = shutil.which(exe)
        if not path:
            self.say("Gojo", f"I couldn’t find {app} on this machine.")
            return
        if app == "file explorer":
            subprocess.Popen([path, str(Path.home())])
        else:
            subprocess.Popen([path])
        self.status.set(f"Opened {app}")
        self.say("Gojo", f"Opened {app}.")

    def open_url(self, url):
        webbrowser.open(url)
        self.status.set("Website opened")
        self.say("Gojo", "Opened the website in your browser.")

    def open_search(self, query):
        webbrowser.open("https://www.google.com/search?q=" + quote_plus(query))
        self.status.set("Search opened")
        self.say("Gojo", "Opened your search in the browser.")

    def add_study(self, subject):
        with sqlite3.connect(DB_PATH) as con:
            con.execute("INSERT INTO study(subject) VALUES(?)", (subject,))
        self.status.set("Study task saved")
        self.say("Gojo", f"Added study task: {subject}.")

    def show_study(self):
        with sqlite3.connect(DB_PATH) as con:
            tasks = con.execute("SELECT subject FROM study WHERE done = 0 ORDER BY id").fetchall()
        if not tasks:
            self.say("Gojo", "Your study planner is empty. Try: ‘add study task Biology chapter 3’.")
            return
        text = "\n".join(f"• {item[0]}" for item in tasks)
        self.say("Gojo", "Study planner:\n" + text)

    def create_sites(self, topic, count):
        save_dir = filedialog.askdirectory(title="Choose folder to save website files")
        if not save_dir:
            self.say("Gojo", "Cancelled. No website files were created.")
            return

        created = []
        palette = [
            "from-cyan-400 to-violet-500",
            "from-fuchsia-400 to-indigo-500",
            "from-emerald-300 to-cyan-500",
            "from-amber-300 to-rose-500",
            "from-blue-400 to-teal-300",
            "from-purple-400 to-pink-400",
        ]

        root_dir = Path(save_dir)
        for i in range(count):
            title = topic if count == 1 else f"{topic} — concept {i + 1}"
            folder = root_dir / (slugify(topic) if count == 1 else f"{slugify(topic)}-{i + 1}")
            folder.mkdir(parents=True, exist_ok=True)
            safe_title = html.escape(title)
            body = f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{safe_title}</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="min-h-screen bg-slate-950 text-white">
  <nav class="mx-auto flex max-w-6xl justify-between p-6">
    <span class="font-bold">{safe_title}</span>
    <a href="#about" class="text-slate-300">About</a>
  </nav>
  <main class="mx-auto max-w-6xl px-6 py-24">
    <p class="uppercase tracking-[.3em] text-cyan-300">Your idea starts here</p>
    <h1 class="mt-5 bg-gradient-to-r {palette[i]} bg-clip-text text-5xl font-black text-transparent sm:text-7xl">Make something memorable.</h1>
    <p class="mt-6 max-w-2xl text-lg leading-8 text-slate-300">This is a Tailwind starter page for {safe_title}. Replace the sample copy with your real content.</p>
    <a href="#about" class="mt-8 inline-block rounded-xl bg-white px-6 py-3 font-semibold text-slate-950">Explore</a>
    <section id="about" class="mt-20 grid gap-5 md:grid-cols-3">
      <article class="rounded-2xl border border-slate-800 bg-slate-900 p-6"><h2 class="text-xl font-bold">Discover</h2><p class="mt-3 text-slate-400">Add a feature or idea.</p></article>
      <article class="rounded-2xl border border-slate-800 bg-slate-900 p-6"><h2 class="text-xl font-bold">Create</h2><p class="mt-3 text-slate-400">Customize your layout.</p></article>
      <article class="rounded-2xl border border-slate-800 bg-slate-900 p-6"><h2 class="text-xl font-bold">Share</h2><p class="mt-3 text-slate-400">Ship it when ready.</p></article>
    </section>
  </main>
</body>
</html>
'''
            path = folder / "index.html"
            path.write_text(body, encoding="utf-8")
            created.append(str(path))

        self.status.set(f"Created {len(created)} website(s)")
        self.say("Gojo", "Created local website files:\n" + "\n".join(created))

    def create_unreal(self, name):
        folder = filedialog.askdirectory(title="Choose a parent folder for the Unreal project")
        if not folder:
            self.say("Gojo", "Cancelled; no Unreal project was created.")
            return

        proj_name = re.sub(r"\W", "", name) or "GojoGame"
        proj_dir = Path(folder) / proj_name
        (proj_dir / "Content").mkdir(parents=True, exist_ok=True)
        (proj_dir / "Config").mkdir(parents=True, exist_ok=True)

        descriptor = {
            "FileVersion": 3,
            "EngineAssociation": "",
            "Category": "Games",
            "Description": "Starter project scaffold created by Gojo",
            "Modules": [{"Name": proj_name, "Type": "Runtime", "LoadingPhase": "Default"}],
        }
        (proj_dir / f"{proj_name}.uproject").write_text(__import__("json").dumps(descriptor, indent=2), encoding="utf-8")
        (proj_dir / "README.txt").write_text("Starter scaffold only. Open the .uproject in Unreal Editor to continue. This is not a finished game.\n", encoding="utf-8")

        self.status.set("Unreal scaffold created")
        self.say("Gojo", f"Created an Unreal project scaffold at {proj_dir}. Open the .uproject in Unreal Editor to continue.")

    def listen(self):
        if sr is None:
            self.say("Gojo", "Speech input is not installed. Install SpeechRecognition + PocketSphinx from requirements.txt to enable local voice input.")
            return
        self.status.set("Listening…")

        def worker():
            try:
                recognizer = sr.Recognizer()
                with sr.Microphone() as source:
                    audio = recognizer.listen(source, timeout=6, phrase_time_limit=10)
                text = recognizer.recognize_sphinx(audio)
                self.root.after(0, lambda: self._heard(text))
            except Exception as exc:
                self.root.after(0, lambda: self.status.set(f"Voice input failed: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    def _heard(self, text):
        self.entry.delete(0, "end")
        self.entry.insert(0, text)
        self.send()

    def draw_pet(self):
        c = self.pet_canvas
        c.delete("pet")
        if self.pet_hidden:
            return

        x = self.pet_x
        y = 180
        angry = self.pet_mood == "angry"
        step = self.pet_step % 8
        front = step if step < 4 else 8 - step
        back = 4 - front if front < 4 else front - 4
        arm_l = 12 + front
        arm_r = 12 + back
        leg_l = 8 + front
        leg_r = 8 + back

        c.create_oval(x - 52, y + 116, x + 52, y + 125, fill="#090d18", outline="", tags="pet")

        # body
        c.create_line(x, y + 20, x, y + 82, fill="#f3e7de", width=7, tags="pet")
        c.create_line(x - 8, y + 80, x - 14, y + 110 + leg_l, fill="#f3f4ff", width=5, tags="pet")
        c.create_line(x + 8, y + 80, x + 22, y + 110 + leg_r, fill="#f3f4ff", width=5, tags="pet")
        c.create_line(x - 7, y + 30, x - 24, y + 44 + arm_l, fill="#f3d6c5", width=5, tags="pet")
        c.create_line(x + 7, y + 30, x + 22, y + 44 + arm_r, fill="#f3d6c5", width=5, tags="pet")

        # head + hair
        c.create_oval(x - 36, y, x + 36, y + 52, fill="#f6e9df", outline="#faf0eb", width=2, tags="pet")
        hair = [
            (x - 34, y + 10),
            (x - 24, y - 18),
            (x - 10, y - 2),
            (x, y - 24),
            (x + 10, y - 2),
            (x + 24, y - 18),
            (x + 34, y + 10),
        ]
        c.create_polygon(*sum((pt for pt in hair), ()), fill="#f7fbff", outline="#edf3ff", tags="pet")

        # blindfold
        c.create_rectangle(x - 30, y + 15, x + 30, y + 24, fill="#121212", outline="#000000", width=2, tags="pet")
        c.create_line(x - 10, y + 19, x + 10, y + 19, fill="#2c2c2c", width=2, tags="pet")

        # face expression
        if angry:
            c.create_arc(x - 12, y + 22, x + 12, y + 34, start=210, extent=120, style="arc", outline="#7d2d3a", width=2, tags="pet")
            c.create_line(x - 18, y + 34, x + 18, y + 34, fill="#8c4658", width=2, tags="pet")
            c.create_oval(x - 18, y + 18, x - 10, y + 25, fill="#f4dfe2", outline="#f4dfe2", tags="pet")
            c.create_oval(x + 10, y + 18, x + 18, y + 25, fill="#f4dfe2", outline="#f4dfe2", tags="pet")
            c.create_oval(x - 30, y + 32, x + 30, y + 42, fill="#ff8e95", outline="#ff8e95", tags="pet")
        else:
            c.create_arc(x - 14, y + 22, x + 14, y + 34, start=200, extent=140, style="arc", outline="#7a4954", width=2, tags="pet")

        # outer aura rings when angry
        if angry:
            c.create_oval(x - 52, y - 18, x + 52, y + 62, outline="#ff9ca5", width=2, tags="pet")
            c.create_oval(x - 60, y - 24, x + 60, y + 68, outline="#ff6f7d", width=1, tags="pet")

        # label
        c.create_text(x, 290, text="GOJO  •  " + ("angry" if angry else "calm"), fill="#d6c9f6", font=("Segoe UI", 9, "bold"), tags="pet")

    def _pet_loop(self):
        self.pet_step += 1
        if not self.pet_hidden:
            self.pet_x += self.pet_direction * 3
            if self.pet_x > 200 or self.pet_x < 26:
                self.pet_direction *= -1
            self.draw_pet()
        self.root.after(140, self._pet_loop)

    def pet_leave(self):
        self.pet_mood = "angry"
        self.pet_direction = 1
        self.draw_pet()
        self.status.set("Gojo is giving you space")

        def step_out():
            if self.pet_x < 250:
                self.pet_x += 12
                self.draw_pet()
                self.root.after(35, step_out)
            else:
                self.pet_hidden = True
                self.draw_pet()
                self.root.after(5000, self.pet_return)

        step_out()

    def pet_return(self):
        self.pet_hidden = False
        self.pet_mood = "happy"
        self.pet_x = 32
        self.pet_direction = 1
        self.draw_pet()
        self.status.set("Gojo returned")


if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    GojoApp(root)
    root.mainloop()
