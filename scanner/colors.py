"""Color classification in CIE Lab using CIEDE2000.

The distance formula follows Sharma, Wu, and Dalal (2005). Open-source
webcam solvers such as QBR showed that Lab + ΔE00 is far more stable
under room lighting than HSV ranges, which is why this scanner uses it.
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

FACE_ORDER = "URFDLB"

# Matches the existing visualizer: U blue, D green, F white, B yellow, R red, L orange.
FACE_TO_COLOR = {
    "U": "blue",
    "R": "red",
    "F": "white",
    "D": "green",
    "L": "orange",
    "B": "yellow",
}
COLOR_TO_FACE = {name: face for face, name in FACE_TO_COLOR.items()}
COLOR_NAMES = ["white", "yellow", "red", "orange", "blue", "green"]

# Typical sticker BGR under indoor light. Calibration replaces these.
DEFAULT_BGR = {
    "white": (236, 236, 236),
    "yellow": (40, 210, 245),
    "red": (45, 40, 190),
    "orange": (30, 110, 235),
    "blue": (190, 75, 35),
    "green": (70, 175, 45),
}

DISPLAY_HEX = {
    "white": "#f5f5f5",
    "yellow": "#f4c430",
    "red": "#e53935",
    "orange": "#ff8c32",
    "blue": "#1976d2",
    "green": "#2eaa59",
}


def bgr_to_lab(bgr: tuple[float, float, float] | np.ndarray) -> np.ndarray:
    pixel = np.array([[bgr]], dtype=np.uint8)
    lab_cv = cv2.cvtColor(pixel, cv2.COLOR_BGR2LAB)[0, 0].astype(np.float64)
    return np.array(
        [lab_cv[0] * 100.0 / 255.0, lab_cv[1] - 128.0, lab_cv[2] - 128.0],
        dtype=np.float64,
    )


def ciede2000(lab1: np.ndarray, lab2: np.ndarray) -> float:
    L1, a1, b1 = (float(x) for x in lab1)
    L2, a2, b2 = (float(x) for x in lab2)

    c1 = (a1 * a1 + b1 * b1) ** 0.5
    c2 = (a2 * a2 + b2 * b2) ** 0.5
    c_bar = (c1 + c2) / 2.0
    c_bar7 = c_bar**7
    g = 0.5 * (1.0 - (c_bar7 / (c_bar7 + 25.0**7)) ** 0.5)

    a1p = (1.0 + g) * a1
    a2p = (1.0 + g) * a2
    c1p = (a1p * a1p + b1 * b1) ** 0.5
    c2p = (a2p * a2p + b2 * b2) ** 0.5

    h1p = 0.0 if c1p == 0 else np.degrees(np.arctan2(b1, a1p)) % 360.0
    h2p = 0.0 if c2p == 0 else np.degrees(np.arctan2(b2, a2p)) % 360.0

    dLp = L2 - L1
    dCp = c2p - c1p

    if c1p * c2p == 0:
        dhp = 0.0
    elif abs(h2p - h1p) <= 180:
        dhp = h2p - h1p
    elif h2p - h1p > 180:
        dhp = h2p - h1p - 360.0
    else:
        dhp = h2p - h1p + 360.0
    dHp = 2.0 * (c1p * c2p) ** 0.5 * np.sin(np.radians(dhp) / 2.0)

    Lp_bar = (L1 + L2) / 2.0
    Cp_bar = (c1p + c2p) / 2.0

    if c1p * c2p == 0:
        hp_bar = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hp_bar = (h1p + h2p) / 2.0
    elif h1p + h2p < 360:
        hp_bar = (h1p + h2p + 360.0) / 2.0
    else:
        hp_bar = (h1p + h2p - 360.0) / 2.0

    t = (
        1.0
        - 0.17 * np.cos(np.radians(hp_bar - 30.0))
        + 0.24 * np.cos(np.radians(2.0 * hp_bar))
        + 0.32 * np.cos(np.radians(3.0 * hp_bar + 6.0))
        - 0.20 * np.cos(np.radians(4.0 * hp_bar - 63.0))
    )
    d_theta = 30.0 * np.exp(-(((hp_bar - 275.0) / 25.0) ** 2))
    rc = 2.0 * (Cp_bar**7 / (Cp_bar**7 + 25.0**7)) ** 0.5
    sl = 1.0 + (0.015 * (Lp_bar - 50.0) ** 2) / ((20.0 + (Lp_bar - 50.0) ** 2) ** 0.5)
    sc = 1.0 + 0.045 * Cp_bar
    sh = 1.0 + 0.015 * Cp_bar * t
    rt = -np.sin(np.radians(2.0 * d_theta)) * rc

    return float(
        (
            (dLp / sl) ** 2
            + (dCp / sc) ** 2
            + (dHp / sh) ** 2
            + rt * (dCp / sc) * (dHp / sh)
        )
        ** 0.5
    )


class ColorClassifier:
    def __init__(self, references: dict[str, np.ndarray] | None = None):
        self.references = references or {
            name: bgr_to_lab(bgr) for name, bgr in DEFAULT_BGR.items()
        }

    @classmethod
    def from_path(cls, path: Path) -> ColorClassifier:
        if not path.exists():
            return cls()
        payload = json.loads(path.read_text())
        refs = {name: np.array(values, dtype=np.float64) for name, values in payload.items()}
        return cls(refs)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({k: v.tolist() for k, v in self.references.items()}, indent=2))

    def classify_lab(self, lab: np.ndarray) -> tuple[str, float]:
        L, a, b = (float(x) for x in lab)
        chroma = (a * a + b * b) ** 0.5
        if L >= 58 and chroma <= 22:
            return "white", chroma
        best_name = "white"
        best_delta = float("inf")
        for name, reference in self.references.items():
            delta = ciede2000(lab, reference)
            if name == "white" and L < 48:
                delta += 8
            if name in {"red", "orange"} and chroma < 16:
                delta += 10
            if delta < best_delta:
                best_name = name
                best_delta = delta
        # A bright cube red is more saturated than a drifted red sample, so
        # nearest-neighbor pulls it onto orange. Hue keeps them apart:
        # red stays near pure red, orange sits closer to yellow.
        if chroma >= 40 and a > 20 and b > 10:
            hue = float(np.degrees(np.arctan2(b, a)))
            if hue <= 42:
                return "red", best_delta
            if hue >= 48:
                return "orange", best_delta
        return best_name, best_delta

    def learn(self, color_name: str, lab: np.ndarray, blend: float = 0.45) -> None:
        current = self.references[color_name]
        self.references[color_name] = (1.0 - blend) * current + blend * lab
