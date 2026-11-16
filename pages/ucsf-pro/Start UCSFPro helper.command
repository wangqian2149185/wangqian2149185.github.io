#!/bin/bash
# UCSFViewer Pro — double-click to start the NMRPipe helper (macOS).
# Keep this file next to ucsfpro_helper.py. It asks for the working folder (the one with fid/, ucsf/ …),
# remembers it for next time, loads your NMRPipe environment and starts the helper.
# Close this Terminal window (or press Ctrl+C) to stop the helper.

HERE="$(cd "$(dirname "$0")" && pwd)"
HELPER="$HERE/ucsfpro_helper.py"
LAST="$HOME/.ucsfpro_helper_last"
pause() { echo; read -r -n 1 -s -p "Press any key to close this window." ; echo; }

printf '\033]0;UCSFViewer Pro helper\007'
echo "UCSFViewer Pro — NMRPipe helper"
echo "--------------------------------"

if [ ! -f "$HELPER" ]; then
  echo "ucsfpro_helper.py was not found next to this file:"; echo "  $HERE"
  echo "Put both files in the same folder (the app can save ucsfpro_helper.py for you)."; pause; exit 1
fi

PY="$(command -v python3)"
if [ -z "$PY" ] || ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)' 2>/dev/null; then
  echo "python3 (3.7 or newer) is needed. On macOS: run  xcode-select --install  in Terminal, or install Python from python.org."
  pause; exit 1
fi

# working folder: argument > this file's own folder if it is a working folder > folder dialog (last choice preselected)
WD="$1"
if [ -z "$WD" ] && { [ -d "$HERE/fid" ] || [ -d "$HERE/ucsf" ]; }; then WD="$HERE"; fi
if [ -z "$WD" ]; then
  DEF=""; [ -f "$LAST" ] && DEF="$(cat "$LAST")"
  [ -d "$DEF" ] || DEF="$HOME"
  WD="$(osascript - "$DEF" <<'APPLESCRIPT' 2>/dev/null
on run argv
  set p to "UCSFViewer Pro: choose the working folder (it contains fid/, ucsf/, peaks/ …)"
  try
    set d to (POSIX file (item 1 of argv)) as alias
    return POSIX path of (choose folder with prompt p default location d)
  on error number n
    if n is -128 then return ""
    return POSIX path of (choose folder with prompt p)
  end try
end run
APPLESCRIPT
)"
fi
if [ -z "$WD" ]; then echo "No working folder chosen."; pause; exit 1; fi
WD="${WD%/}"
if [ ! -d "$WD" ]; then echo "Not a folder: $WD"; pause; exit 1; fi
printf '%s\n' "$WD" > "$LAST"

echo "Working folder: $WD"
echo
# The helper loads the NMRPipe environment itself if nmrPipe is not on PATH
# (~/.cshrc, ~/.tcshrc, login zsh/bash, or nmrInit*.com in ~/nmrpipe, /opt/nmrpipe …).
# If your NMRPipe lives elsewhere, set it here, e.g.:
export NMRPIPE_INIT="/Users/wangqian/nmr/com/nmrInit.mac_arm64.com"
"$PY" "$HELPER" "$WD"
code=$?
echo; echo "Helper stopped (exit $code)."
pause
