export const HEX = {
  white: "#f4f6f8",
  yellow: "#f0c43a",
  red: "#e24b4b",
  orange: "#f08a32",
  blue: "#3c7dff",
  green: "#2faf62",
};

export const COLOR_TO_FACE = {
  blue: "U",
  red: "R",
  white: "F",
  green: "D",
  orange: "L",
  yellow: "B",
};

export const FACE_TO_COLOR = {
  U: "blue",
  R: "red",
  F: "white",
  D: "green",
  L: "orange",
  B: "yellow",
};

export const NET = [
  [null, "U", null, null],
  ["L", "F", "R", "B"],
  [null, "D", null, null],
];

export const CAPTURE_FRAMES = 4;

export const PREVIEW = {
  iso: [4.8, 4.1, 5.6],
  U: [0.5, 6.5, 1.1],
  D: [0.5, -6.5, 1.1],
  F: [0.7, 1.5, 6.5],
  B: [-0.7, 1.5, -6.5],
  R: [6.5, 1.5, 0.7],
  L: [-6.5, 1.5, -0.7],
};

export const EMPTY_LAYOUT = {
  faces: {},
  steps: [],
  report: { issues: [] },
  state: null,
};
