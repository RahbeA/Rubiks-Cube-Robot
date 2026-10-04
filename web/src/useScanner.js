import { useCallback, useEffect, useRef, useState } from "react";
import { CAPTURE_FRAMES, COLOR_TO_FACE, EMPTY_LAYOUT } from "./constants.js";

function currentStep(ui) {
  return ui.layout.steps?.[ui.stepIndex] || null;
}

function scanHint(ui) {
  if (ui.phase !== "scan") return "";
  if (ui.manual) return "Fit the face in the square, with the center color in the middle.";
  if (ui.locked) return "Outline locked. Keep the face there and it will capture.";
  if (ui.handsOn) return "Hand seen. Looking for the cube face in front of it.";
  if (ui.trackerReady) return "Show a cube face anywhere in the frame.";
  return "Show a cube face. Hand tracking is still loading, and the face can still be read.";
}

function agreedStickers(left, right) {
  if (!left || !right || left.length !== right.length) return 0;
  let same = 0;
  for (let i = 0; i < left.length; i += 1) if (left[i] === right[i]) same += 1;
  return same;
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  return { ok: response.ok, data };
}

export function useScanner() {
  const [ui, setUi] = useState({
    layout: EMPTY_LAYOUT,
    phase: "prepare",
    stepIndex: 0,
    liveStickers: [],
    selected: null,
    netPick: null,
    manual: false,
    handsOn: false,
    trackerReady: false,
    locked: false,
    stableCount: 0,
    hint: "",
    cameraStatus: "Setting up the camera…",
  });

  const uiRef = useRef(ui);
  const videoRef = useRef(null);
  const overlayRef = useRef(null);
  const cropRef = useRef(document.createElement("canvas"));
  const liveLabsRef = useRef([]);
  const editedRef = useRef(false);
  const savingRef = useRef(false);
  const analyzingRef = useRef(false);
  const captureAfterRef = useRef(0);
  const stableKeyRef = useRef("");
  const missCountRef = useRef(0);
  const quadRef = useRef([]);
  const focusRef = useRef(null);
  const handPointsRef = useRef([]);
  const handLandmarkerRef = useRef(null);
  const flashTimerRef = useRef(0);

  const patch = useCallback((partial) => {
    const next = { ...uiRef.current, ...partial };
    uiRef.current = next;
    setUi(next);
    return next;
  }, []);

  const clearedReading = useCallback(() => {
    liveLabsRef.current = [];
    editedRef.current = false;
    quadRef.current = [];
    stableKeyRef.current = "";
    missCountRef.current = 0;
    return { liveStickers: [], selected: null, locked: false, stableCount: 0 };
  }, []);

  const commitCurrent = useCallback(async () => {
    const state = uiRef.current;
    const step = currentStep(state);
    if (!step || savingRef.current || state.liveStickers.length !== 9) return;
    if (state.liveStickers[4]?.color !== step.color) return;
    savingRef.current = true;
    try {
      const { ok, data } = await postJson("/api/commit", {
        face: step.face,
        stickers: state.liveStickers.map((sticker) => sticker.color),
        labs: liveLabsRef.current,
      });
      if (!ok) {
        patch({ hint: data.error || "That face could not be saved." });
        return;
      }
      patch({
        layout: data,
        phase: "verify",
        stepIndex: state.stepIndex,
        selected: null,
        netPick: null,
        hint: "",
        ...clearedReading(),
      });
      captureAfterRef.current = performance.now() + 900;
    } finally {
      savingRef.current = false;
    }
  }, [clearedReading, patch]);

  const applyReading = useCallback((data) => {
    const state = uiRef.current;
    const step = currentStep(state);
    if (!step || state.phase !== "scan") return;
    const found = Boolean(data.locked) && data.stickers?.length === 9;
    if (!found) {
      missCountRef.current += 1;
      if (missCountRef.current < 3) return;
      quadRef.current = [];
      if (!editedRef.current) liveLabsRef.current = [];
      patch({
        locked: false,
        stableCount: 0,
        ...(editedRef.current ? {} : { liveStickers: [] }),
      });
      return;
    }
    missCountRef.current = 0;
    quadRef.current = !state.manual && data.quad?.length === 4 ? data.quad : [];
    let stickers = state.liveStickers;
    if (!editedRef.current) {
      stickers = data.stickers;
      liveLabsRef.current = data.stickers.map((sticker) => sticker.lab);
    }
    const center = stickers[4]?.color;
    const cooling = performance.now() < captureAfterRef.current;
    let stableCount = 0;
    let hint;
    if (cooling || center !== step.color) {
      stableKeyRef.current = "";
      hint = cooling ? "Get the face in place, then hold still." : `That center looks ${center}. ${step.nudge}`;
    } else {
      const key = stickers.map((sticker) => sticker.color).join("");
      const sameFace = key === stableKeyRef.current || agreedStickers(key, stableKeyRef.current) >= 7;
      stableCount = sameFace ? state.stableCount + 1 : 1;
      stableKeyRef.current = key;
      hint = stableCount >= CAPTURE_FRAMES
        ? "In focus. Capturing this face."
        : "Good focus. Hold still — it saves without a click.";
    }
    patch({ locked: true, liveStickers: stickers, stableCount, hint });
    if (!editedRef.current && !cooling && stableCount >= CAPTURE_FRAMES && center === step.color) {
      commitCurrent();
    }
  }, [commitCurrent, patch]);

  useEffect(() => {
    const video = videoRef.current;
    const overlay = overlayRef.current;
    let stopped = false;
    let analyzeTimer = 0;
    let frame = 0;
    let lastHandTime = 0;
    let lastHandRun = 0;

    function coverMap() {
      const ew = overlay.clientWidth;
      const eh = overlay.clientHeight;
      const vw = video.videoWidth || ew;
      const vh = video.videoHeight || eh;
      const scale = Math.max(ew / vw, eh / vh);
      return { scale, ox: (ew - vw * scale) / 2, oy: (eh - vh * scale) / 2, vw, vh };
    }
    function videoNormToCanvas(nx, ny) {
      const { scale, ox, oy, vw, vh } = coverMap();
      return [ox + nx * vw * scale, oy + ny * vh * scale];
    }
    function canvasToVideoNorm(x, y) {
      const { scale, ox, oy, vw, vh } = coverMap();
      return [(x - ox) / (vw * scale), (y - oy) / (vh * scale)];
    }
    function manualRoi() {
      const side = Math.min(overlay.clientWidth, overlay.clientHeight) * 0.68;
      const x = (overlay.clientWidth - side) / 2;
      const y = (overlay.clientHeight - side) / 2;
      const a = canvasToVideoNorm(x, y);
      const b = canvasToVideoNorm(x + side, y + side);
      const nx = Math.max(0, Math.min(a[0], b[0]));
      const ny = Math.max(0, Math.min(a[1], b[1]));
      return { x: nx, y: ny, w: Math.min(1 - nx, Math.abs(b[0] - a[0])), h: Math.min(1 - ny, Math.abs(b[1] - a[1])) };
    }
    function grabFrame() {
      if (!video.videoWidth) return null;
      const crop = cropRef.current;
      const ctx = crop.getContext("2d");
      if (uiRef.current.manual) {
        const box = manualRoi();
        const sx = box.x * video.videoWidth;
        const sy = box.y * video.videoHeight;
        const sw = Math.max(2, box.w * video.videoWidth);
        const sh = Math.max(2, box.h * video.videoHeight);
        crop.width = 420;
        crop.height = Math.max(2, Math.round(420 * sh / sw));
        ctx.drawImage(video, sx, sy, sw, sh, 0, 0, crop.width, crop.height);
      } else {
        const scale = Math.min(1, 640 / video.videoWidth);
        crop.width = Math.max(2, Math.round(video.videoWidth * scale));
        crop.height = Math.max(2, Math.round(video.videoHeight * scale));
        ctx.drawImage(video, 0, 0, crop.width, crop.height);
      }
      return crop.toDataURL("image/jpeg", 0.72);
    }
    function drawOverlay() {
      const dpr = window.devicePixelRatio || 1;
      overlay.width = overlay.clientWidth * dpr;
      overlay.height = overlay.clientHeight * dpr;
      const ctx = overlay.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, overlay.clientWidth, overlay.clientHeight);
      const state = uiRef.current;
      if (state.phase !== "scan") return;
      if (state.manual) {
        const side = Math.min(overlay.clientWidth, overlay.clientHeight) * 0.68;
        const x = (overlay.clientWidth - side) / 2;
        const y = (overlay.clientHeight - side) / 2;
        ctx.strokeStyle = "rgba(244,245,247,.9)";
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, side, side);
        ctx.beginPath();
        for (let i = 1; i < 3; i += 1) {
          ctx.moveTo(x + side * i / 3, y);
          ctx.lineTo(x + side * i / 3, y + side);
          ctx.moveTo(x, y + side * i / 3);
          ctx.lineTo(x + side, y + side * i / 3);
        }
        ctx.strokeStyle = "rgba(244,245,247,.35)";
        ctx.stroke();
        return;
      }
      handPointsRef.current.forEach((hand) => {
        hand.forEach((point) => {
          const [x, y] = videoNormToCanvas(point.x, point.y);
          ctx.beginPath();
          ctx.arc(x, y, 3, 0, Math.PI * 2);
          ctx.fillStyle = "rgba(158,193,255,.9)";
          ctx.fill();
        });
      });
      const quad = quadRef.current;
      if (!quad.length) {
        const side = Math.min(overlay.clientWidth, overlay.clientHeight) * 0.42;
        const x = (overlay.clientWidth - side) / 2;
        const y = (overlay.clientHeight - side) / 2;
        ctx.strokeStyle = "rgba(244,245,247,.28)";
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, side, side);
        return;
      }
      if (quad.length === 4) {
        const points = quad.map(([x, y]) => videoNormToCanvas(x, y));
        ctx.beginPath();
        points.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
        ctx.closePath();
        ctx.strokeStyle = state.locked ? "#7dffa8" : "rgba(255,255,255,.7)";
        ctx.lineWidth = 3;
        ctx.stroke();
        ctx.setLineDash([5, 6]);
        for (let i = 1; i < 3; i += 1) {
          const a = points[0].map((v, k) => v + (points[3][k] - v) * i / 3);
          const b = points[1].map((v, k) => v + (points[2][k] - v) * i / 3);
          ctx.beginPath();
          ctx.moveTo(a[0], a[1]);
          ctx.lineTo(b[0], b[1]);
          ctx.stroke();
          const c = points[0].map((v, k) => v + (points[1][k] - v) * i / 3);
          const d = points[3].map((v, k) => v + (points[2][k] - v) * i / 3);
          ctx.beginPath();
          ctx.moveTo(c[0], c[1]);
          ctx.lineTo(d[0], d[1]);
          ctx.stroke();
        }
        ctx.setLineDash([]);
      }
    }
    async function analyze() {
      if (uiRef.current.phase !== "scan" || analyzingRef.current || savingRef.current) return;
      const image = grabFrame();
      if (!image) return;
      analyzingRef.current = true;
      try {
        const { ok, data } = await postJson("/api/analyze", {
          image,
          manual: uiRef.current.manual,
          focus: focusRef.current,
        });
        if (stopped) return;
        if (!ok) {
          patch({ hint: "The scanner could not read that frame." });
          return;
        }
        applyReading(data);
      } catch {
        if (!stopped) patch({ hint: "The scanner could not read that frame." });
      } finally {
        analyzingRef.current = false;
      }
    }
    function loop(now) {
      const landmarker = handLandmarkerRef.current;
      if (landmarker && video.readyState >= 2 && !uiRef.current.manual && now - lastHandRun > 80) {
        lastHandRun = now;
        const timestamp = Math.max(lastHandTime + 1, Math.round(now));
        try {
          const result = landmarker.detectForVideo(video, timestamp);
          lastHandTime = timestamp;
          const hands = result?.landmarks || [];
          handPointsRef.current = hands;
          const handsOn = hands.length > 0;
          if (handsOn) {
            let sx = 0;
            let sy = 0;
            let n = 0;
            hands.forEach((hand) => hand.forEach((point) => {
              sx += point.x;
              sy += point.y;
              n += 1;
            }));
            focusRef.current = { x: sx / n, y: sy / n };
          } else {
            focusRef.current = null;
          }
          if (handsOn !== uiRef.current.handsOn) patch({ handsOn });
        } catch {
          if (uiRef.current.handsOn) patch({ handsOn: false });
        }
      } else if (uiRef.current.manual) {
        handPointsRef.current = [];
        focusRef.current = null;
        if (uiRef.current.handsOn) patch({ handsOn: false });
      }
      drawOverlay();
      frame = requestAnimationFrame(loop);
    }
    async function openCamera() {
      const attempts = [
        { video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false },
        { video: { facingMode: { ideal: "user" }, width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false },
        { video: true, audio: false },
      ];
      let lastError = null;
      for (const constraints of attempts) {
        try {
          return await navigator.mediaDevices.getUserMedia(constraints);
        } catch (error) {
          lastError = error;
        }
      }
      throw lastError;
    }
    async function startCamera() {
      try {
        video.srcObject = await openCamera();
        await video.play();
        if (stopped) return;
        if (uiRef.current.phase === "prepare") patch({ cameraStatus: "Ready when you are" });
        analyzeTimer = window.setInterval(analyze, 220);
        frame = requestAnimationFrame(loop);
      } catch {
        if (!stopped) patch({ cameraStatus: "Camera blocked — allow access, then refresh." });
      }
    }
    async function startHands() {
      try {
        const visionLib = await import("https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/vision_bundle.mjs");
        const vision = await visionLib.FilesetResolver.forVisionTasks("https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/wasm");
        const landmarker = await visionLib.HandLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
            delegate: "CPU",
          },
          runningMode: "VIDEO",
          numHands: 2,
        });
        if (stopped) return;
        handLandmarkerRef.current = landmarker;
        patch({ trackerReady: true, hint: scanHint({ ...uiRef.current, trackerReady: true }) });
      } catch {
        if (!stopped) patch({ trackerReady: false });
      }
    }

    fetch("/api/layout")
      .then((response) => response.json())
      .then((layout) => {
        if (!stopped) patch({ layout });
      })
      .catch(() => {});
    startCamera();
    startHands();

    return () => {
      stopped = true;
      window.clearInterval(analyzeTimer);
      window.clearTimeout(flashTimerRef.current);
      cancelAnimationFrame(frame);
      const stream = video.srcObject;
      if (stream) stream.getTracks().forEach((track) => track.stop());
    };
  }, [applyReading, patch]);

  const begin = useCallback(async () => {
    const { ok, data } = await postJson("/api/reset", {});
    if (!ok) {
      patch({ hint: "The scanner is not running. Start python app.py, then try Next again." });
      return;
    }
    videoRef.current?.play?.();
    const cleared = clearedReading();
    const next = { ...uiRef.current, layout: data, phase: "scan", stepIndex: 0, ...cleared };
    patch({ layout: data, phase: "scan", stepIndex: 0, netPick: null, ...cleared, hint: scanHint(next) });
  }, [clearedReading, patch]);

  const continueFace = useCallback(() => {
    const state = uiRef.current;
    const last = (state.layout.steps?.length || 6) - 1;
    const cleared = clearedReading();
    if (state.stepIndex >= last) {
      patch({ phase: "done", selected: null, netPick: null, hint: "", ...cleared });
      return;
    }
    videoRef.current?.play?.();
    const stepIndex = state.stepIndex + 1;
    const next = { ...state, phase: "scan", stepIndex, ...cleared };
    patch({ phase: "scan", stepIndex, selected: null, netPick: null, ...cleared, hint: scanHint(next) });
  }, [clearedReading, patch]);

  const selectStep = useCallback((index) => {
    const next = { ...uiRef.current, phase: "scan", stepIndex: index, ...clearedReading() };
    patch({ ...clearedReading(), phase: "scan", stepIndex: index, hint: scanHint(next) });
  }, [clearedReading, patch]);

  const correct = useCallback(async (color) => {
    const state = uiRef.current;
    if (state.phase === "verify" && state.selected != null) {
      const step = currentStep(state);
      if (!step) return;
      const { ok, data } = await postJson("/api/correct", {
        face: step.face,
        index: state.selected,
        color,
      });
      if (!ok) return;
      patch({ layout: data, phase: "verify" });
      return;
    }
    if (state.netPick && state.layout.faces[state.netPick.face]) {
      const { ok, data } = await postJson("/api/correct", {
        face: state.netPick.face,
        index: state.netPick.index,
        color,
      });
      if (!ok) return;
      patch({
        layout: data,
        phase: state.phase,
        hint: data.report?.complete ? "" : state.hint,
      });
      return;
    }
    if (state.selected == null || !state.liveStickers[state.selected]) return;
    const liveStickers = state.liveStickers.map((sticker, index) => (
      index === state.selected ? { ...sticker, color, face: COLOR_TO_FACE[color] } : sticker
    ));
    editedRef.current = true;
    patch({ liveStickers, stableCount: 0 });
  }, [patch]);

  const pickNet = useCallback((face, index) => {
    if (!uiRef.current.layout.faces[face]) return;
    patch({ netPick: { face, index }, selected: null, hint: "Pick a color for that sticker." });
  }, [patch]);

  const pickLive = useCallback((index) => {
    patch({ selected: index, netPick: null });
  }, [patch]);

  const redo = useCallback(async () => {
    const step = currentStep(uiRef.current);
    if (!step) return;
    const { ok, data } = await postJson("/api/clear", { face: step.face });
    if (!ok) return;
    videoRef.current?.play?.();
    captureAfterRef.current = performance.now() + 1800;
    const cleared = clearedReading();
    patch({
      layout: data,
      phase: "scan",
      selected: null,
      netPick: null,
      ...cleared,
      hint: "Get the face in place, then hold still.",
    });
  }, [clearedReading, patch]);

  const restart = useCallback(async () => {
    const { ok, data } = await postJson("/api/reset", {});
    if (!ok) return;
    patch({
      layout: data,
      phase: "prepare",
      stepIndex: 0,
      netPick: null,
      ...clearedReading(),
      hint: "",
    });
  }, [clearedReading, patch]);

  const toggleManual = useCallback(() => {
    const manual = !uiRef.current.manual;
    const next = { ...uiRef.current, manual, phase: uiRef.current.phase, ...clearedReading() };
    patch({ manual, ...clearedReading(), hint: scanHint(next) });
  }, [clearedReading, patch]);

  return {
    ...ui,
    videoRef,
    overlayRef,
    begin,
    continueFace,
    selectStep,
    correct,
    pickNet,
    pickLive,
    redo,
    restart,
    toggleManual,
    save: commitCurrent,
  };
}
