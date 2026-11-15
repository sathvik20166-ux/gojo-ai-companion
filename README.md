# Gojo — Local Desktop Companion

A local Python desktop chat app with Gojo in the UI, typed chat, optional offline speech input, and spoken replies through the computer's installed voices. No cloud model, API, or Ollama is used. It is rule-based, so it only responds to implemented commands; it is not a general conversational AI.

## Run

Python 3.10+ and Tkinter are required:

```bash
python -m pip install -r requirements.txt
python app.py
```

Speech output uses `pyttsx3` and an installed system voice. Speech input uses SpeechRecognition with PocketSphinx locally; microphone support also depends on PyAudio and OS microphone permissions. If voice dependencies or the microphone are unavailable, typed chat still works. Tailwind website styling loads from its CDN when a generated page is viewed, so that styling needs internet access.

## Built-in commands

- `open Notepad`, `open Calculator`, `open Paint`, `open File Explorer`, `open Chrome`, `open Edge`, `open Unreal`
- `search for …` or `open https://…`
- `create a website for …` or `create 6 websites about …` (maximum six)
- `create an Unreal game project named StarQuest`
- `add study task Biology chapter 3`; `show study planner`
- `stop`; `I’m angry` / `go away`; `come back`

The UI includes chat and quick-action buttons. It shows a simple drawn character; it is not an exact anime illustration. The character can walk in the app panel and leave temporarily on angry/leave-me-alone phrases. Actions that launch apps, open web pages, or create files require approval.

Unreal generation creates only a `.uproject` descriptor and empty folders, not a finished game. To launch the editor, install Unreal and set `UE_EDITOR_PATH` if it is not found on PATH. Chat history and study tasks are stored locally in `gojo_local.sqlite3`.
