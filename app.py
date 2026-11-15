"""Local Gojo AI starter: Tkinter UI + Ollama running on your own computer.

No cloud AI API or arbitrary shell-command execution. Install Ollama, pull a model,
then run this file with Python. Ollama's localhost endpoint is used only to talk to
the local model process.
"""
import json
import os
import re
import sqlite3
import threading
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import Tk, StringVar, END, WORD, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
from tkinter import ttk

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "gojo_memory.sqlite3"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
MODEL = os.environ.get("GOJO_MODEL", "qwen2.5:3b")
SYSTEM_PROMPT = (
    "You are Gojo AI, an original, upbeat and encouraging assistant. Be natural and concise. "
    "You can converse in English or Telugu when asked. You are running locally. "
    "Never claim to have performed an action unless the app confirms it. Never instruct the app "
    "to run shell commands. For outside-world actions, the application will ask the user first."
)


def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, role TEXT NOT NULL, content TEXT NOT NULL)")


def load_history(limit=24):
    with sqlite3.connect(DB_PATH) as db:
        rows = db.execute("SELECT role, content FROM messages ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]


def save_message(role, content):
    with sqlite3.connect(DB_PATH) as db:
        db.execute("INSERT INTO messages(role, content) VALUES (?, ?)", (role, content))


def local_model_reply(user_text):
    history = load_history()
    payload = {
        "model": MODEL,
        "stream": False,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *history, {"role": "user", "content": user_text}],
        "options": {"temperature": 0.7},
    }
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.loads(response.read().decode("utf-8"))
    return result["message"]["content"].strip()


class GojoApp:
    def __init__(self, root):
        self.root = root
        root.title("Gojo AI — Local Python Assistant")
        root.geometry("800x650")
        root.minsize(580, 420)
        root.configure(bg="#0b1020")
        self.busy = False
        self.pending = None
        self.status = StringVar(value=f"Local model: {MODEL}")
        self._ui()
        self.say("Gojo AI", f"Ready. I use the local model ‘{MODEL}’. Say ‘stop’ to interrupt a reply.")

    def _ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", padding=8)
        ttk.Label(self.root, text="✦  GOJO AI", background="#0b1020", foreground="#eee7ff",
                  font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=18, pady=(16, 2))
        ttk.Label(self.root, textvariable=self.status, background="#0b1020", foreground="#b9b4cf").pack(anchor="w", padx=20, pady=(0, 10))
        self.chat = ScrolledText(self.root, wrap=WORD, state="disabled", bg="#12182a", fg="#f5f4fb",
                                 insertbackground="white", relief="flat", font=("Segoe UI", 11), padx=14, pady=12)
        self.chat.pack(fill="both", expand=True, padx=18, pady=4)
        self.chat.tag_config("assistant", foreground="#cbbaff", font=("Segoe UI", 10, "bold"))
        self.chat.tag_config("user", foreground="#83e5ef", font=("Segoe UI", 10, "bold"))
        self.chat.tag_config("body", foreground="#f0eff7")
        self.approvals = ttk.Frame(self.root)
        self.approve_btn = ttk.Button(self.approvals, text="Approve", command=self.approve)
        self.cancel_btn = ttk.Button(self.approvals, text="Cancel", command=self.cancel)
        self.row = ttk.Frame(self.root)
        self.row.pack(fill="x", padx=18, pady=(8, 16))
        self.entry = ttk.Entry(self.row)
        self.entry.pack(side="left", fill="x", expand=True, ipady=9, padx=(0, 8))
        self.entry.bind("<Return>", lambda _event: self.send())
        ttk.Button(self.row, text="Send", command=self.send).pack(side="left", padx=(0, 7))
        ttk.Button(self.row, text="Stop", command=self.stop).pack(side="left")

    def say(self, who, text):
        self.chat.configure(state="normal")
        self.chat.insert(END, who + "\n", "user" if who == "You" else "assistant")
        self.chat.insert(END, text + "\n\n", "body")
        self.chat.configure(state="disabled")
        self.chat.see(END)

    def send(self):
        text = self.entry.get().strip()
        if not text or self.busy:
            return
        self.entry.delete(0, END)
        if text.lower() in {"stop", "stop it", "cancel", "pause"}:
            self.stop()
            return
        if self.pending:
            self.say("Gojo AI", "Please approve or cancel the pending action first.")
            return
        self.say("You", text)
        save_message("user", text)
        action = self.detect_action(text)
        if action:
            self.pending = action
            self.status.set("Waiting for your approval; nothing has happened yet.")
            self.say("Gojo AI", "I can " + action["description"] + ". Approve or cancel?")
            self.approvals.pack(fill="x", padx=18, pady=(2, 8))
            self.approve_btn.pack(side="left", padx=(0, 8))
            self.cancel_btn.pack(side="left")
            return
        self.busy = True
        self.status.set(f"Thinking locally with {MODEL}…")
        threading.Thread(target=self.ask_model, args=(text,), daemon=True).start()

    @staticmethod
    def detect_action(text):
        match = re.match(r"\s*(?:search for|look up|google)\s+(.+)", text, re.I)
        if match:
            query = match.group(1).strip()
            return {"type": "search", "value": query, "description": f"search the web for ‘{query}’"}
        match = re.match(r"\s*open\s+(https?://\S+)", text, re.I)
        if match:
            return {"type": "open", "value": match.group(1), "description": f"open {match.group(1)} in your browser"}
        match = re.match(r"\s*(?:create|make|build)\s+(?:a\s+)?website(?:\s+(?:for|about))?\s*(.*)", text, re.I)
        if match:
            topic = match.group(1).strip() or "My project"
            return {"type": "website", "value": topic, "description": f"create a starter website about ‘{topic}’"}
        return None

    def ask_model(self, text):
        try:
            answer = local_model_reply(text)
            save_message("assistant", answer)
            self.root.after(0, lambda: self.finish(answer, None))
        except urllib.error.URLError:
            self.root.after(0, lambda: self.finish(
                "I can’t reach Ollama on this computer. Start Ollama and make sure the model is installed. No cloud API was used.",
                "Ollama not reachable"))
        except Exception as exc:
            self.root.after(0, lambda error=str(exc): self.finish(f"Local model error: {error}", "Model error"))

    def finish(self, answer, error):
        self.busy = False
        self.status.set(error or f"Ready · local model {MODEL}")
        self.say("Gojo AI", answer)

    def approve(self):
        action = self.pending
        self.pending = None
        self.approvals.pack_forget()
        if not action:
            return
        try:
            if action["type"] == "search":
                from urllib.parse import quote_plus
                webbrowser.open("https://www.google.com/search?q=" + quote_plus(action["value"]))
                result = "Opened your approved search in the browser."
            elif action["type"] == "open":
                webbrowser.open(action["value"])
                result = "Opened the approved website in the browser."
            else:
                self.save_website(action["value"])
                return
            self.status.set("Action completed after approval.")
            self.say("Gojo AI", result)
            save_message("assistant", result)
        except Exception as exc:
            self.status.set("Action failed.")
            self.say("Gojo AI", f"Could not complete the action: {exc}")

    def save_website(self, topic):
        path = filedialog.asksaveasfilename(defaultextension=".html", initialfile="study-or-project.html",
                                            filetypes=[("HTML files", "*.html")])
        if not path:
            self.status.set("Cancelled; no file was created.")
            self.say("Gojo AI", "No problem. No website file was created.")
            return
        safe = (topic.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace('"', "&quot;").replace("'", "&#39;"))
        html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{safe}</title><script src="https://cdn.tailwindcss.com"></script></head><body class="min-h-screen bg-slate-950 text-white grid place-items-center p-8"><main class="max-w-3xl text-center"><p class="text-cyan-300">MADE WITH GOJO AI</p><h1 class="text-5xl font-bold mt-4">{safe}</h1><p class="text-slate-300 mt-5">Your idea starts here. Customize this page and make it yours.</p><section class="mt-12 rounded-2xl border border-slate-700 p-8">Add your content here.</section></main></body></html>'''
        Path(path).write_text(html, encoding="utf-8")
        self.status.set("Website saved to " + path)
        self.say("Gojo AI", "Starter website saved. You can open the HTML file in your browser.")

    def cancel(self):
        self.pending = None
        self.approvals.pack_forget()
        self.status.set("Cancelled; nothing was done.")
        self.say("Gojo AI", "Cancelled. Nothing was done.")

    def stop(self):
        self.busy = False
        self.cancel()
        self.status.set("Stopped. I’m listening.")


if __name__ == "__main__":
    init_db()
    window = Tk()
    GojoApp(window)
    window.mainloop()
