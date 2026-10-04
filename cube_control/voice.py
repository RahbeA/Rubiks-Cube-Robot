"""Map spoken phrases to cube moves and commands."""

from __future__ import annotations

import re

from cube_control.moves import ALL_MOVES, FACE_MOVES

_MOVE_BY_TOKEN: dict[str, str] = {}
for move in ALL_MOVES:
    face = move[0].lower()
    if move.endswith("2"):
        _MOVE_BY_TOKEN[f"{face}2"] = move
        _MOVE_BY_TOKEN[f"{face} 2"] = move
        _MOVE_BY_TOKEN[f"{face} two"] = move
    elif move.endswith("'"):
        _MOVE_BY_TOKEN[f"{face} prime"] = move
        _MOVE_BY_TOKEN[f"{face}'"] = move
        _MOVE_BY_TOKEN[f"{face} inverted"] = move
    else:
        _MOVE_BY_TOKEN[face] = move

# Common mis-hearings
_ALIASES = {
    "are": "r",
    "our": "r",
    "you": "u",
    "why": "y",
    "bee": "b",
    "be": "b",
    "see": "c",
    "ef": "f",
    "eff": "f",
    "el": "l",
    "dee": "d",
}


def _normalize(text: str) -> str:
    lowered = text.lower().strip()
    lowered = lowered.replace("’", "'")
    lowered = re.sub(r"[^\w\s']", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def _replace_aliases(tokens: list[str]) -> list[str]:
    return [_ALIASES.get(token, token) for token in tokens]


def _match_command(normalized: str) -> str | None:
    if normalized in ("scramble", "scramble cube", "random scramble", "scrambled"):
        return "scramble"
    if normalized.startswith("scramble"):
        return "scramble"
    if normalized in ("solve", "solve cube", "solve it", "reverse", "undo scramble", "sol"):
        return "solve"
    if normalized.startswith("solve"):
        return "solve"
    if normalized in ("reset", "clear", "solved", "solve down"):
        return "reset"
    return None


def parse_voice_transcript(text: str) -> dict:
    """Return {type: command|moves, moves?, command?}."""
    normalized = _normalize(text)
    if not normalized:
        return {"type": "empty"}

    command = _match_command(normalized)
    if command:
        return {"type": "command", "command": command}

    tokens = _replace_aliases(normalized.split())
    moves: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        pair = f"{token} {tokens[index + 1]}" if index + 1 < len(tokens) else token
        triple = (
            f"{token} {tokens[index + 1]} {tokens[index + 2]}"
            if index + 2 < len(tokens)
            else ""
        )

        if triple in _MOVE_BY_TOKEN:
            moves.append(_MOVE_BY_TOKEN[triple])
            index += 3
            continue
        if pair in _MOVE_BY_TOKEN:
            moves.append(_MOVE_BY_TOKEN[pair])
            index += 2
            continue
        if token in _MOVE_BY_TOKEN:
            moves.append(_MOVE_BY_TOKEN[token])
            index += 1
            continue
        if len(token) == 1 and token.upper() in FACE_MOVES:
            moves.append(token.upper())
            index += 1
            continue
        if token == "prime" and moves:
            last = moves[-1]
            if not last.endswith("'") and not last.endswith("2"):
                moves[-1] = f"{last}'"
            index += 1
            continue
        if token in ("2", "two") and moves:
            last = moves[-1]
            if len(last) == 1:
                moves[-1] = f"{last}2"
            index += 1
            continue
        index += 1

    if moves:
        return {"type": "moves", "moves": moves}
    return {"type": "unknown", "text": normalized}


def parse_voice_best(text: str, alternatives: list[str] | None = None) -> dict:
    """Try the main transcript and speech alternatives; prefer first actionable parse."""
    candidates: list[str] = []
    for piece in [text, *(alternatives or [])]:
        cleaned = (piece or "").strip()
        if cleaned and cleaned not in candidates:
            candidates.append(cleaned)
    if not candidates:
        return {"type": "empty"}

    last_unknown: dict | None = None
    for candidate in candidates:
        parsed = parse_voice_transcript(candidate)
        if parsed["type"] not in ("empty", "unknown"):
            if candidate != text:
                parsed["heard"] = candidate
            return parsed
        if parsed["type"] == "unknown":
            last_unknown = parsed
    return last_unknown or {"type": "empty"}
