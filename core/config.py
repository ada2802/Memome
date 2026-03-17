import os
from pathlib import Path

# Load .env if present
_env = Path(".env")
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


class Config:
    # ── Whisper ─────────────────────────────────────────────────────────────
    # Options (fastest → most accurate, all run on CPU):
    #   tiny   ~40MB   ~32x real-time   lowest quality
    #   base   ~75MB   ~16x real-time   good for testing
    #   small  ~244MB  ~6x  real-time   solid quality
    #   distil-large-v3  ~756MB  ~3-4x real-time  best quality
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "large-v3-turbo")

    # Device for Whisper inference. Options:
    #   "cpu"   — always safe, no GPU required
    #   "cuda"  — NVIDIA GPU, 10-50x faster (requires torch+CUDA)
    #   "auto"  — use CUDA if available, fall back to CPU silently
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")

    # Beam size for Whisper decoding.
    #   1  = greedy (fastest, slightly less accurate)
    #   5  = default beam search (balanced)
    # Lower this on slow CPUs (e.g. beam_size=1 saves ~30% per chunk).
    WHISPER_BEAM_SIZE: int = int(os.getenv("WHISPER_BEAM_SIZE", "5"))

    # ── Ollama ───────────────────────────────────────────────────────────────
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    # Use qwen2.5:3b for lower RAM (~2GB) or qwen2.5:7b for better quality (~5GB)
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "45"))

    # ── Translation ─────────────────────────────────────────────────────────
    # When True, skip the Ollama translation call if the detected source
    # language already matches the user-chosen target language.
    # This saves ~1-3s per chunk for bilingual sessions.
    SKIP_SAME_LANG: bool = os.getenv("SKIP_SAME_LANG", "1") not in ("0", "false", "no")

    # ── Audio ────────────────────────────────────────────────────────────────
    SAMPLE_RATE: int = 16000
    # sounddevice blocksize: 12800 samples = 800ms at 16kHz
    BLOCK_SIZE: int = 12800

    # Flush speech buffer after this many seconds of silence.
    # 0.5s works well for fast speakers (news, lectures).
    # Raise to 1.0–1.5s for slower conversational speech.
    SILENCE_FLUSH_SEC: float = float(os.getenv("SILENCE_FLUSH_SEC", "0.5"))

    # Hard cap: flush regardless after this many seconds of continuous speech.
    # CRITICAL for fast/unbroken speakers — without this a news anchor speaking
    # for 53s non-stop produces only 1–2 giant chunks.
    # 8s gives ~6–8 chunks/minute which is comfortable to read and translate.
    # Raise to 12–15s if you prefer longer, more contextual chunks.
    MAX_SPEECH_SEC: float = float(os.getenv("MAX_SPEECH_SEC", "8.0"))

    # Energy threshold for simple VAD (0.0 – 1.0); lower = more sensitive.
    # 0.008 catches broadcast audio and normal microphone levels.
    # Lower to 0.005 for distant or quiet microphones.
    VAD_THRESHOLD: float = float(os.getenv("VAD_THRESHOLD", "0.008"))

    # ── Sessions ─────────────────────────────────────────────────────────────
    # Maximum sessions returned by /api/sessions
    SESSIONS_LIST_LIMIT: int = int(os.getenv("SESSIONS_LIST_LIMIT", "100"))

    # How long (seconds) to keep an ended session in memory before GC removes it.
    # In-memory sessions are needed for WS reconnects during draining.
    # After this TTL, the session is removed from the sessions dict (DB is unaffected).
    SESSION_GC_SEC: int = int(os.getenv("SESSION_GC_SEC", "300"))

    # ── App ──────────────────────────────────────────────────────────────────
    DB_PATH: Path = Path(os.getenv("DB_PATH", "data/meetings.db"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8765"))
