import { useEffect, useState } from "react";

function formatMoves(moves) {
  if (!moves?.length) return "Already solved";
  return moves.join(" ");
}

export default function SolveOverlay({ searching, solution, error, onClose }) {
  const ready = !searching && solution && !error;
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!searching) {
      setElapsed(0);
      return undefined;
    }
    const started = Date.now();
    const tick = () => setElapsed(Math.floor((Date.now() - started) / 1000));
    tick();
    const id = setInterval(tick, 500);
    return () => clearInterval(id);
  }, [searching]);

  return (
    <div className="solve-overlay" role="dialog" aria-modal="true" aria-labelledby="solve-title">
      <div className="solve-card">
        {searching && (
          <>
            <div className="face-loader" aria-hidden="true">
              {Array.from({ length: 9 }, (_, index) => (
                <span
                  key={index}
                  className="face-loader-cell"
                  style={{ "--i": index }}
                />
              ))}
            </div>
            <p className="kicker">Solving</p>
            <h2 id="solve-title">Mapping your cube…</h2>
            <p className="solve-lead">
              Solving the scanned cube ({elapsed}s). Kociemba runs when it is installed.
              Otherwise the experimental two-phase solver runs, and that search can take much longer.
              This timer is computer time, not robot motion time.
            </p>
          </>
        )}

        {ready && (
          <>
            <p className="kicker">Solution ready</p>
            <h2 id="solve-title">Your solve is ready.</h2>
            <p className="solve-meta">{solution.length} moves</p>
            <pre className="solve-moves">{formatMoves(solution)}</pre>
            <div className="robot-callout">
              <strong>Move list only</strong>
              <span>This screen does not send the solution to the Arduino. Cube Control does that.</span>
            </div>
            <button type="button" className="primary" onClick={onClose}>Back to layout</button>
          </>
        )}

        {error && !searching && (
          <>
            <p className="kicker">Solver</p>
            <h2 id="solve-title">Could not solve</h2>
            <p className="solve-lead">{error}</p>
            <button type="button" onClick={onClose}>Back to layout</button>
          </>
        )}
      </div>
    </div>
  );
}
