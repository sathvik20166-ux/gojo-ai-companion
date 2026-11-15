# Gojo — Local Python Assistant

A rule-based desktop assistant. It uses no AI model, API, Ollama, or cloud service. It can speak replies using optional system TTS, open a small allow-list of installed apps, keep study tasks locally, create Tailwind HTML starter sites (up to six per request), and create an Unreal project scaffold. Actions that launch apps, open web pages, or create files require an on-screen approval.

## Run

Python 3.10+ with Tkinter is required.

```bash
python -m pip install -r requirements.txt
python app.py
```

If `pyttsx3` is installed and the machine has a speech voice, Gojo reads assistant replies aloud. Otherwise the app still works silently. On Windows, `python -m tkinter` can check whether Tkinter is available.

## Commands

- `open Notepad`, `open Calculator`, `open Paint`, `open File Explorer`, `open Chrome`, `open Edge`, `open Unreal`
- `search for game ideas`
- `open https://example.com`
- `create a website for my study project`
- `create 6 websites about my game`
- `create an Unreal game project named StarQuest`
- `add study task Biology chapter 3`
- `show study planner`
- `stop`

The study tasks and chat history are stored in `gojo_local.sqlite3` next to the script. Tailwind CSS is loaded from its CDN, so the generated site's styling requires internet access when viewed. Six-site requests are capped at six.

## Unreal limitation

Gojo creates a basic `.uproject` descriptor plus empty `Content` and `Config` directories. This is a starter scaffold—not gameplay, a map, assets, or a guaranteed ready-to-play game. Open the descriptor in an installed Unreal Editor and complete project setup there. `open Unreal` launches an editor only if it can find `UnrealEditor` on PATH or `UE_EDITOR_PATH` is set to the executable path.

This assistant is deliberately rule-based, not a general conversational AI. It does not execute arbitrary commands, send WhatsApp messages, or place calls.
