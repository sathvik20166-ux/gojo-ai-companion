# Gojo — Local Desktop Companion

Python desktop companion with typed chat, optional offline speech recognition, local text-to-speech, a small animated chibi mascot, allow-listed app launching, study-task storage, Tailwind site generation, and an Unreal project scaffold. It uses no LLM, Ollama, cloud AI, or external chat API. Conversation is rule-based, not general-purpose AI.

## Run

Python 3.10+ and Tkinter are required:

```bash
python -m pip install -r requirements.txt
python app.py
```

Speech input uses SpeechRecognition + PocketSphinx locally. Microphone support depends on PyAudio and OS permissions; if its installation fails, typed chat still works. Spoken replies use local system voices through pyttsx3. Generated Tailwind sites load Tailwind from its CDN when viewed, so styling needs an internet connection.

## Commands and buttons

- `open Notepad`, `open Calculator`, `open Paint`, `open File Explorer`, `open Chrome`, `open Edge`, `open Unreal`
- `search for …` or `open https://…`
- `create a website for …` or `create 6 websites about …` (maximum six)
- `create an Unreal game project named StarQuest`
- `add study task Biology chapter 3`; `show study planner`
- `stop`; `I’m angry` / `go away`; `come back`

Click the mascot-side quick actions to open the study planner or start common tasks. App/browser/file actions ask for approval. Saying an angry/leave-me-alone phrase makes the mascot walk off its stage and return after five seconds; “come back” returns it sooner.

## Character and limits

The app draws a simple original chibi-style fan interpretation; it does not include official Gojo artwork or reproduce the exact anime design. It is not a language model and only responds to implemented commands/patterns. The Unreal action creates a `.uproject` descriptor and empty folders, not a playable game. `open Unreal` requires Unreal Editor to be installed; set `UE_EDITOR_PATH` if it is not on PATH. Chat/study data stays in `gojo_local.sqlite3` next to the app.
