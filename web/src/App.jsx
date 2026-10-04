import { useState } from "react";
import CubeControl from "./CubeControl.jsx";
import CubePreview from "./CubePreview.jsx";
import SolveOverlay from "./SolveOverlay.jsx";
import { CAPTURE_FRAMES, FACE_TO_COLOR, HEX, NET } from "./constants.js";
import { solveCube } from "./solve.js";
import { useScanner } from "./useScanner.js";

const COLOR_NAMES = Object.keys(HEX);

function titleCase(value) {
  return `${value[0].toUpperCase()}${value.slice(1)}`;
}

function formatCubeState(state) {
  if (!state) return "";
  return [
    `corner_permutation = [${state.corner_permutation.join(", ")}]`,
    `corner_orientation = [${state.corner_orientation.join(", ")}]`,
    `edge_permutation = [${state.edge_permutation.join(", ")}]`,
    `edge_orientation = [${state.edge_orientation.join(", ")}]`,
    state.valid ? (state.solved ? "valid · solved" : "valid") : "invalid",
  ].join("\n");
}

function FaceGrid({ colors, selected, onPick, large }) {
  return (
    <div className={large ? "face face-large" : "face"}>
      {Array.from({ length: 9 }, (_, index) => (
        <button
          key={index}
          type="button"
          className={selected === index ? "sticker selected" : "sticker"}
          style={{ background: colors?.[index] ? HEX[colors[index]] : undefined }}
          aria-label={`Sticker ${index + 1}`}
          onClick={onPick ? () => onPick(index) : undefined}
        />
      ))}
    </div>
  );
}

function Prepare({ scan }) {
  return (
    <section className="slide">
      <p className="kicker">Before you start</p>
      <h1>Get the cube ready.</h1>
      <p className="lead">
        You will show one face at a time. Hold it steady in front of the camera,
        check the colors, then move to the next face.
      </p>
      <ol className="prep-list">
        <li>Green center first, with white along the top.</li>
        <li>Then red, white, orange, and yellow, each with blue along the top.</li>
        <li>Blue last, with white along the bottom.</li>
      </ol>
      <button className="primary next" type="button" onClick={scan.begin}>Next</button>
      {(scan.hint || scan.cameraStatus.startsWith("Camera blocked")) && (
        <p className="hint">{scan.hint || scan.cameraStatus}</p>
      )}
    </section>
  );
}

function CameraHud({ scan }) {
  const step = scan.layout.steps?.[scan.stepIndex];
  const progress = Math.min(scan.stableCount / CAPTURE_FRAMES, 1);
  return (
    <>
      <div className="hud-top">
        <p className="kicker">Face {scan.stepIndex + 1} of 6</p>
        <h1>{step ? `Show ${step.color}` : "Show a face"}</h1>
        <p>{step?.hold}</p>
        <div className="bar" aria-hidden="true"><span style={{ width: `${progress * 100}%` }} /></div>
      </div>
      <div className="mini-face">
        <FaceGrid colors={scan.liveStickers.map((sticker) => sticker.color)} />
        <p>{scan.hint || "Hold the face steady."}</p>
      </div>
    </>
  );
}

function Verify({ scan }) {
  const step = scan.layout.steps?.[scan.stepIndex];
  const colors = step ? scan.layout.faces?.[step.face] : [];
  const last = scan.stepIndex >= (scan.layout.steps?.length || 6) - 1;
  return (
    <section className="slide">
      <p className="kicker">Face {scan.stepIndex + 1} of 6 · {step ? titleCase(step.color) : ""}</p>
      <h1>Does this look right?</h1>
      <p className="lead">Tap a square, then a color, if one is wrong.</p>
      <FaceGrid colors={colors} selected={scan.selected} onPick={scan.pickLive} large />
      <div className="palette">
        {COLOR_NAMES.map((name) => (
          <button
            key={name}
            type="button"
            className="chip"
            style={{ background: HEX[name] }}
            aria-label={name}
            onClick={() => scan.correct(name)}
          />
        ))}
      </div>
      <div className="actions">
        <button type="button" onClick={scan.redo}>Recapture</button>
        <button className="primary next" type="button" onClick={scan.continueFace}>
          {last ? "See the cube" : "Next"}
        </button>
      </div>
    </section>
  );
}

function Done({ scan }) {
  const [showPreview, setShowPreview] = useState(false);
  const [showDev, setShowDev] = useState(false);
  const [solving, setSolving] = useState(false);
  const [solution, setSolution] = useState(null);
  const [solveError, setSolveError] = useState("");
  const issues = scan.layout.report?.issues || [];
  const ok = Boolean(scan.layout.report?.valid_layout && scan.layout.state);
  const editing = scan.netPick;
  const editingFace = editing?.face;
  const editingName = editingFace ? FACE_TO_COLOR[editingFace] : "";

  async function handleSolve() {
    if (!scan.layout.state || solving) return;
    setSolving(true);
    setSolveError("");
    setSolution(null);
    try {
      const result = await solveCube(scan.layout.state, scan.layout.faces);
      setSolution(result.solution || []);
    } catch (error) {
      setSolveError(error.message || "The solver could not finish.");
    } finally {
      setSolving(false);
    }
  }

  function closeSolveOverlay() {
    setSolution(null);
    setSolveError("");
  }

  return (
    <>
      {(solving || solution || solveError) && (
        <SolveOverlay
          searching={solving}
          solution={solution}
          error={solveError}
          onClose={closeSolveOverlay}
        />
      )}
      <section className="slide slide-layout">
        <button
          type="button"
          className="dev-toggle"
          aria-label="Show CubeState"
          aria-pressed={showDev}
          onClick={() => setShowDev((open) => !open)}
        >
          &lt;&gt;
        </button>
        {showDev && scan.layout.state && (
          <pre className="dev-state">{formatCubeState(scan.layout.state)}</pre>
        )}
      <p className="kicker">Finished</p>
      <h1>{ok ? "Here is your cube." : "Here is the layout."}</h1>
      <p className="lead">Tap a square, then the color it should be.</p>
      {issues.length > 0 && (
        <ul className="issues">
          {issues.map((issue) => <li key={issue}>{issue}</li>)}
        </ul>
      )}
      <div className="net">
        {NET.flat().map((face, index) => (
          <div key={face || `gap-${index}`} className={face && face === editingFace ? "net-face editing" : face ? "net-face" : "net-gap"}>
            {face && (
              <>
                <FaceGrid
                  colors={scan.layout.faces?.[face]}
                  selected={editingFace === face ? editing.index : null}
                  onPick={(sticker) => scan.pickNet(face, sticker)}
                />
                <p className="face-label">{FACE_TO_COLOR[face]}</p>
              </>
            )}
          </div>
        ))}
      </div>
      {editingFace && (
        <div className="fix-panel">
          <p className="kicker">Editing the {editingName} face</p>
          <div className="color-choices">
            {COLOR_NAMES.map((name) => (
              <button key={name} type="button" className="color-choice" onClick={() => scan.correct(name)}>
                <i className="swatch" style={{ background: HEX[name] }} />
                {titleCase(name)}
              </button>
            ))}
          </div>
        </div>
      )}
      {showPreview && (
        <div className="preview-panel">
          <CubePreview faces={scan.layout.faces || {}} previewFace="iso" />
        </div>
      )}
      <div className="actions">
        <button type="button" onClick={() => setShowPreview((open) => !open)}>
          {showPreview ? "Hide 3D preview" : "3D preview"}
        </button>
        {ok && (
          <button className="primary" type="button" disabled={solving} onClick={handleSolve}>
            Solve
          </button>
        )}
        <button type="button" onClick={scan.restart}>Start over</button>
      </div>
    </section>
    </>
  );
}

export default function App() {
  const scan = useScanner();
  const [mode, setMode] = useState("scanner");

  return (
    <main className="screen">
      <nav className="app-nav">
        <button
          type="button"
          className={mode === "scanner" ? "nav-active" : ""}
          onClick={() => setMode("scanner")}
        >
          Scanner
        </button>
        <button
          type="button"
          className={mode === "control" ? "nav-active" : ""}
          onClick={() => setMode("control")}
        >
          Cube Control
        </button>
      </nav>
      {mode === "control" ? (
        <CubeControl onBack={() => setMode("scanner")} />
      ) : (
        <>
          <div className={scan.phase === "scan" ? "camera-layer" : "camera-layer idle"}>
            <video ref={scan.videoRef} autoPlay playsInline muted />
            <canvas ref={scan.overlayRef} />
            {scan.phase === "scan" && <CameraHud scan={scan} />}
          </div>
          {scan.phase === "prepare" && <Prepare scan={scan} />}
          {scan.phase === "verify" && <Verify scan={scan} />}
          {scan.phase === "done" && <Done scan={scan} />}
        </>
      )}
    </main>
  );
}
