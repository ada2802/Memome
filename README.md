# MemoMe — Private Voice Transcription

Local, private voice transcription + real-time translation into any of 17 languages.  
No cloud. No Kafka. No Redis. No Docker. One Python process.

```
Microphone → WAV file (streaming, O(1) RAM)
           → Whisper (CPU/GPU) → Source text
                               → Ollama (qwen3.5 / qwen2.5) → Translated text
                                                             → Browser (WebSocket)
```

---

## Requirements

| Component | Version | Notes |
|-----------|---------|-------|
| Python    | 3.10+   |       |
| Ollama    | any     | Runs as background service |

### RAM budget on a 32 GB machine (recommended setup)

| Component              | RAM      |
|------------------------|----------|
| Whisper `large-v3-turbo` | ~1.6 GB |
| Ollama `qwen3.5:9b`    | ~6.6 GB  |
| FastAPI server         | ~150 MB  |
| Windows 11 OS          | ~4–5 GB  |
| **Total**              | **~14 GB** |
| **Free**               | **~18 GB** |

### RAM budget — minimum (8 GB machine)

| Component           | RAM      |
|---------------------|----------|
| Whisper `base`      | ~500 MB  |
| Ollama `qwen2.5:3b` | ~2 GB    |
| FastAPI server      | ~150 MB  |
| **Total**           | **~3 GB** |

---

## Quick Start

### 1. Install Ollama

Download from https://ollama.com — it runs as a background service automatically after install.

```bash
# Recommended (best translation quality, ~6.6 GB download):
ollama pull qwen3.5:9b

# Alternative — lighter but still good:
ollama pull qwen3.5:4b      # ~2.9 GB
ollama pull qwen2.5:7b      # ~4.7 GB  (original default)
ollama pull qwen2.5:3b      # ~2 GB    (low RAM machines)
```

### 2. Install Python dependencies

```bash
cd memome_v2
pip install -r requirements.txt
```

On Ubuntu you may also need:
```bash
sudo apt install portaudio19-dev    # for sounddevice
```

On macOS:
```bash
brew install portaudio
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env to set your models and preferences (see Configuration section below)
```

### 4. Run

```bash
uvicorn server:app --host 0.0.0.0 --port 8765
```

Open http://localhost:8765

---

## Usage

### Recording

1. Wait for the status badge to show **Ready** (Whisper loads in the background — takes 10–30s)
2. Fill in meeting **Title**, **Project**, and **Participants** (all optional)
3. Choose your **Translate to** language from the dropdown
4. Click **Start Recording**
5. Transcripts appear in 3–8 seconds per chunk depending on model and CPU speed
6. Click **Stop Recording** — remaining audio drains, then an AI summary auto-generates

### Sessions page

- All past sessions are listed with search, filter by status, sort, and project chips
- Click any session to open the full detail panel:
  - Edit title, project, participants and save
  - Play the audio recording in the browser
  - Read or regenerate the AI summary and action items
  - Browse the **full transcript** with source and translation side-by-side (paginated, Load more)
  - Export as `.txt` or `.json`

### Monitor page

- Pipeline stats per session: total tokens, audio duration, Whisper latency, Ollama latency
- Per-chunk breakdown table showing exact ms for each processing step
- Both Sessions and Monitor auto-open the most recent session on navigation

### Sidebar

- All three pages have a collapsible sidebar — click the **‹ ›** tab at the sidebar edge
- Collapse state is saved per-page in localStorage

### Day / Night mode

- Click the **🌙 Dark / ☀️ Light** toggle in the top-right corner
- Preference is saved in localStorage

### Export

- **Copy** button copies all current session text to clipboard
- **Export ↓** in the Sessions panel downloads a `.txt` file with summary + full transcript
- **{ }** button downloads `.json` with full metadata and all chunks
- Raw data is also in `data/meetings.db` (SQLite) and `data/audio/*.wav`

---

## Configuration

All settings can be set in `.env` (copy from `.env.example`). Every setting has a sensible default and the server reads `.env` on startup.



**Key design decisions:**

- `asyncio.Queue` is the only message bus — no Kafka, no Redis, zero configuration
- WAV files are written **incrementally** per callback chunk — O(1) RAM regardless of recording length (handles 3–4 hour sessions safely)
- SQLite uses **WAL mode** and a thread-local connection pool for concurrent read/write
- Whisper runs in a `ThreadPoolExecutor` — the asyncio event loop stays responsive during CPU-intensive inference
- Long translation texts are split at sentence boundaries and translated in **parallel** with `asyncio.gather`
- The `session.chunks` list is capped at 500 entries in RAM; full history always available in SQLite

---

## Long Recording Support (3–4 hours)

MemoMe is specifically designed to handle multi-hour recordings without memory issues:
Expected RAM usage for a 4-hour Bloomberg session: flat ~14 GB throughout.

---

## Whisper Model Guide

All models run through `faster-whisper` (CTranslate2 backend) — up to 4× faster than the original OpenAI Whisper with identical accuracy.

| Model | Size | CPU speed | Best for |
|---|---|---|---|
| `tiny` | ~40 MB | ~32× RT | Quick tests |
| `base` | ~75 MB | ~16× RT | Getting started |
| `small` | ~244 MB | ~6× RT | Better accents |
| `distil-large-v3` | ~756 MB | ~3× RT | English-heavy content |
| `large-v3-turbo` | ~1.6 GB | ~8× RT | **Best multilingual, recommended** |

**Note on `large-v3-turbo`:** Turbo was fine-tuned on transcription data only — it does not support Whisper's built-in *translation* mode. This does not affect MemoMe, which uses Whisper only for transcription and routes all translation through Ollama.

---

## Ollama Model Guide

| Model | RAM | Pull command | Notes |
|---|---|---|---|
| `qwen3.5:9b` | ~6.6 GB | `ollama pull qwen3.5:9b` | **Recommended** — best quality, 201 languages |
| `qwen3.5:4b` | ~2.9 GB | `ollama pull qwen3.5:4b` | Good balance for 8 GB machines |
| `qwen3:8b` | ~5.5 GB | `ollama pull qwen3:8b` | Strong reasoning |
| `qwen2.5:7b` | ~5 GB | `ollama pull qwen2.5:7b` | Original default, reliable |
| `qwen2.5:3b` | ~2 GB | `ollama pull qwen2.5:3b` | Minimum RAM option |

**Qwen3/3.5 users:** The prompts already include `/no_think` to disable thinking mode on both the translation and summary calls, preventing unnecessary 2–5s delays.

---

## GPU Acceleration (Optional)

Set `WHISPER_DEVICE=cuda` in `.env` for 10–50× faster transcription on NVIDIA GPUs.

Requirements:
- NVIDIA GPU with CUDA 12 + cuDNN 9
- `pip install torch` (uncomment the line in `requirements.txt`)

```bash
# In .env:
WHISPER_DEVICE=cuda
WHISPER_MODEL=large-v3-turbo   # GPU makes the large model very fast
```

`WHISPER_DEVICE=auto` will use CUDA if available and fall back to CPU silently.

---


