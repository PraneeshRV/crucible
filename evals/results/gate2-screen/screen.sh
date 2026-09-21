#!/usr/bin/env bash
# Gate 2 bare-arm difficulty screen.
# Runs one case with NO skill, NO instruction files, NO subagents, on glm-5.2.
# A case the bare arm passes has no headroom and should not cost a Gate 2 matrix cell.
set -euo pipefail

# Paths were parameterised after the fact, on 2026-09-21, when this repository was made
# public. The recorded runs used the author's absolute paths; behaviour is unchanged.
CRUC=${CRUC:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}
SCRATCH=${SCRATCH:-${TMPDIR:-/tmp}/gate2-screen}
ZAI_KEY_FILE=${ZAI_KEY_FILE:-$HOME/.config/zai.key}
CLEAN_HOME="$SCRATCH/clean-home"
case_id="$1"

mkdir -p "$CLEAN_HOME"
WS="$SCRATCH/ws-$case_id"
rm -rf "$WS"; mkdir -p "$WS"
WORK=$(python "$CRUC/evals/materialize.py" "$case_id" "$WS")
TURN2="$WS/$case_id/turn2.md"   # staged outside WORK on purpose; never copied in

CASE="$WORK"
OUT="$SCRATCH/$case_id-bare.md"
SID=$(python -c 'import uuid;print(uuid.uuid4())')

run() {
  HOME="$CLEAN_HOME" ZAI_KEY_FILE="$ZAI_KEY_FILE" \
    glm -p "$1" "${@:2}" --disallowedTools "Task,Agent,Skill"
}

{
  echo "# $case_id — bare arm (glm-5.2, clean HOME, no skills, no instruction files)"
  echo "session: $SID"
  echo
  echo "## turn 1 prompt"; echo; cat "$CASE/prompt.md"
  echo; echo "## turn 1 response"; echo
  ( cd "$CASE" && run "$(cat prompt.md)" --session-id "$SID" )
  if [ -f "$TURN2" ]; then
    echo; echo "## turn 2 prompt"; echo; cat "$TURN2"
    echo; echo "## turn 2 response"; echo
    ( cd "$CASE" && run "$(cat "$TURN2")" --resume "$SID" )
  fi
} > "$OUT" 2>&1

echo "done: $OUT ($(wc -l < "$OUT") lines)"
