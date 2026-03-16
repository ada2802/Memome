# MemoMe.spec
# PyInstaller build configuration for MemoMe
#
# Usage:
#   Windows:  pyinstaller MemoMe.spec --clean
#   macOS:    pyinstaller MemoMe.spec --clean
#
# Output:
#   dist/MemoMe/          ← directory bundle (Windows → zip → Inno Setup)
#   dist/MemoMe.app/      ← macOS app bundle (→ create-dmg)

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

# ── Collect data files from packages that need them ─────────────────────────
datas = []

# faster-whisper ships mel filter banks and tokenizer files as package data
datas += collect_data_files("faster_whisper")

# tiktoken (used by whisper) ships BPE vocabulary files
datas += collect_data_files("tiktoken", include_py_files=False)
datas += collect_data_files("tiktoken_ext", include_py_files=False)

# httpx ships its own CA bundle
datas += collect_data_files("httpx")

# certifi CA bundle (needed for HTTPS)
datas += collect_data_files("certifi")

# anyio (uvicorn dependency)
datas += collect_data_files("anyio")

# Your app's own files
datas += [
    ("static", "static"),           # index.html
    ("core",   "core"),             # config.py, vad.py, __init__.py
    ("server.py", "."),             # FastAPI app (imported by launcher)
]

# ── Hidden imports ───────────────────────────────────────────────────────────
# PyInstaller can't detect these because they're loaded dynamically
hiddenimports = [
    # faster-whisper / CTranslate2
    "faster_whisper",
    "faster_whisper.transcribe",
    "faster_whisper.audio",
    "faster_whisper.feature_extractor",
    "faster_whisper.tokenizer",
    "faster_whisper.vad",
    "ctranslate2",

    # uvicorn internals
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",

    # FastAPI / Starlette
    "fastapi",
    "starlette",
    "starlette.routing",
    "starlette.staticfiles",
    "starlette.websockets",
    "starlette.middleware",
    "starlette.middleware.cors",
    "anyio",
    "anyio._backends._asyncio",

    # httpx
    "httpx",
    "httpcore",

    # audio
    "sounddevice",

    # numpy
    "numpy",
    "numpy.core",
    "numpy.lib",

    # pystray + Pillow (tray icon)
    "pystray",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",

    # Windows: pystray needs win32 API
    "win32api",
    "win32con",
    "win32gui",

    # email / http stdlib used by httpx
    "email",
    "email.mime",
    "email.mime.multipart",

    # multiprocessing freeze support
    "multiprocessing",
    "multiprocessing.freeze_support",

    # tiktoken (BPE tokenizer for Whisper)
    "tiktoken",
    "tiktoken.core",
    "tiktoken_ext",
    "tiktoken_ext.openai_public",

    # your core module
    "core",
    "core.config",
    "core.vad",
]

# ── Binary dependencies ──────────────────────────────────────────────────────
binaries = []
binaries += collect_dynamic_libs("ctranslate2")
binaries += collect_dynamic_libs("sounddevice")

# ── Analysis ─────────────────────────────────────────────────────────────────
a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy unused packages to keep size down
        "torch",
        "torchvision",
        "tensorflow",
        "matplotlib",
        "scipy",
        "pandas",
        "jupyter",
        "notebook",
        "IPython",
        "pytest",
        "black",
        "mypy",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── EXE (the actual executable inside the bundle) ────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MemoMe",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,           # compress binaries (optional, saves ~20%)
    console=False,      # no console window on Windows
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Windows: set icon and version info
    icon="assets/icon.ico" if os.path.exists("assets/icon.ico") else None,
    version="version_info.txt" if os.path.exists("version_info.txt") else None,
)

# ── COLLECT (assemble the dist/ folder) ──────────────────────────────────────
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MemoMe",
)

# ── macOS: wrap in a .app bundle ─────────────────────────────────────────────
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="MemoMe.app",
        icon="assets/icon.icns" if os.path.exists("assets/icon.icns") else None,
        bundle_identifier="com.memome.app",
        info_plist={
            "CFBundleName":              "MemoMe",
            "CFBundleDisplayName":       "MemoMe",
            "CFBundleVersion":           "3.0.0",
            "CFBundleShortVersionString":"3.0",
            "NSMicrophoneUsageDescription":
                "MemoMe needs microphone access to transcribe speech in real time.",
            "LSUIElement":       True,   # hide from Dock (tray-only app)
            "NSHighResolutionCapable": True,
        },
    )
