#!/bin/bash
# ============================================================
#  MemoMe — macOS build script
#  Run from the memome_v2 project root on a Mac.
#
#  Output: installer/MemoMe-v3.0-mac.dmg
# ============================================================
set -e

VERSION="3.0"
APP_NAME="MemoMe"
DMG_NAME="${APP_NAME}-v${VERSION}-mac.dmg"

echo ""
echo "============================================================"
echo "  MemoMe macOS Build"
echo "============================================================"
echo ""

# ── Prerequisites ────────────────────────────────────────────
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found."; exit 1; }
command -v pip3    >/dev/null 2>&1 || { echo "ERROR: pip3 not found."; exit 1; }

if ! python3 -m pyinstaller --version >/dev/null 2>&1; then
    echo "Installing PyInstaller..."
    pip3 install pyinstaller
fi

if ! python3 -c "import pystray" 2>/dev/null; then
    echo "Installing pystray + Pillow..."
    pip3 install pystray pillow
fi

# ── Assets ───────────────────────────────────────────────────
mkdir -p assets
if [ ! -f "assets/icon.icns" ]; then
    echo "NOTE: No assets/icon.icns found."
    echo "      A branded icon makes the DMG look professional."
    echo "      To create one: make a 1024x1024 PNG → use iconutil or Image2icon."
    echo ""
fi

# ── Clean ────────────────────────────────────────────────────
echo "Cleaning previous build..."
rm -rf "dist/${APP_NAME}" "dist/${APP_NAME}.app" build/

# ── PyInstaller ───────────────────────────────────────────────
echo ""
echo "Running PyInstaller (3-8 minutes)..."
echo ""
python3 -m PyInstaller MemoMe.spec --clean --noconfirm

echo ""
echo "PyInstaller done. App bundle at: dist/${APP_NAME}.app"

# ── Code signing (optional but recommended) ───────────────────
#
# To sign, set CODESIGN_ID to your Apple Developer ID:
#   export CODESIGN_ID="Developer ID Application: Your Name (XXXXXXXXXX)"
#
if [ -n "${CODESIGN_ID}" ]; then
    echo ""
    echo "Signing app bundle with: ${CODESIGN_ID}"
    codesign --force --deep --sign "${CODESIGN_ID}" \
             --options runtime \
             --entitlements entitlements.plist \
             "dist/${APP_NAME}.app"
    echo "Signing done."
else
    echo ""
    echo "NOTE: CODESIGN_ID not set — skipping code signing."
    echo "      Users will see 'unidentified developer' on first launch."
    echo "      They can right-click → Open to bypass Gatekeeper once."
    echo "      To sign: export CODESIGN_ID='Developer ID Application: ...'"
fi

# ── Create DMG ───────────────────────────────────────────────
echo ""
mkdir -p installer

if command -v create-dmg >/dev/null 2>&1; then
    echo "Building DMG with create-dmg..."
    create-dmg \
        --volname "${APP_NAME}" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 100 \
        --icon "${APP_NAME}.app" 175 190 \
        --hide-extension "${APP_NAME}.app" \
        --app-drop-link 425 190 \
        --background "assets/dmg_background.png" \
        "installer/${DMG_NAME}" \
        "dist/${APP_NAME}.app" \
    || {
        # create-dmg fails if no background image — fall back to simple DMG
        echo "create-dmg with background failed, trying without background..."
        create-dmg \
            --volname "${APP_NAME}" \
            --window-size 500 300 \
            --icon-size 100 \
            --icon "${APP_NAME}.app" 140 150 \
            --app-drop-link 360 150 \
            "installer/${DMG_NAME}" \
            "dist/${APP_NAME}.app"
    }
else
    echo "create-dmg not found — building plain DMG with hdiutil..."
    echo "(Install create-dmg for a nicer installer: brew install create-dmg)"
    hdiutil create \
        -volname "${APP_NAME}" \
        -srcfolder "dist/${APP_NAME}.app" \
        -ov \
        -format UDZO \
        "installer/${DMG_NAME}"
fi

# ── Notarize (optional, requires Apple Developer account) ─────
#
# Notarization removes the Gatekeeper warning entirely.
# Requires: CODESIGN_ID set + Apple ID credentials in Keychain.
#
# Uncomment to enable:
# if [ -n "${CODESIGN_ID}" ] && [ -n "${APPLE_ID}" ]; then
#     echo "Notarizing DMG..."
#     xcrun notarytool submit "installer/${DMG_NAME}" \
#         --apple-id "${APPLE_ID}" \
#         --team-id "${TEAM_ID}" \
#         --password "${APP_PASSWORD}" \
#         --wait
#     xcrun stapler staple "installer/${DMG_NAME}"
#     echo "Notarization done."
# fi

echo ""
echo "============================================================"
echo "  BUILD COMPLETE"
echo "============================================================"
echo ""
echo "  DMG: installer/${DMG_NAME}"
ls -lh "installer/${DMG_NAME}" 2>/dev/null || true
echo ""
echo "  Upload to GitHub Releases as: ${DMG_NAME}"
echo ""
