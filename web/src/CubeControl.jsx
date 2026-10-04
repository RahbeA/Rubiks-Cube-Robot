import { useCallback, useEffect, useRef, useState } from "react";
import {
  connectServerSerial,
  disconnectServerSerial,
  fetchControlState,
  fetchSerialStatus,
  postVoice,
  scrambleCube,
  solveCubeControl,
} from "./cubeControlApi.js";

const SpeechRecognition =
  typeof window !== "undefined"
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : null;

function formatAlgorithm(moves) {
  if (!moves?.length) return "";
  return Array.isArray(moves) ? moves.join(" ") : moves;
}

function isResetPhrase(text) {
  return /^(reset|clear|solved|solve down)\b/i.test(text.trim());
}

export default function CubeControl({ onBack }) {
  const [state, setState] = useState(null);
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [interimText, setInterimText] = useState("");
  const [typedCommand, setTypedCommand] = useState("");
  const [micLevel, setMicLevel] = useState(0);
  const [speechHint, setSpeechHint] = useState("");
  const [log, setLog] = useState([]);
  const [error, setError] = useState("");
  const [algorithm, setAlgorithm] = useState("");
  const [serialMode, setSerialMode] = useState("server");
  const [serverConnecting, setServerConnecting] = useState(false);
  const [serverPorts, setServerPorts] = useState([]);
  const [serverPort, setServerPort] = useState("");
  const [baudRate, setBaudRate] = useState(115200);
  const [oneMovePerLine, setOneMovePerLine] = useState(false);
  const [serverConnected, setServerConnected] = useState(false);
  const [browserConnected, setBrowserConnected] = useState(false);
  const recognitionRef = useRef(null);
  const listeningRef = useRef(false);
  const runVoiceRef = useRef(null);
  const lastVoiceAtRef = useRef({ key: "", at: 0 });
  const interimCommandTimerRef = useRef(null);
  const micStreamRef = useRef(null);
  const micAudioRef = useRef(null);
  const micLevelFrameRef = useRef(null);
  const serialPortRef = useRef(null);
  const serialWriterRef = useRef(null);

  const pushLog = useCallback((message) => {
    setLog((entries) => [message, ...entries].slice(0, 40));
  }, []);

  const refreshState = useCallback(async () => {
    const payload = await fetchControlState();
    setState(payload);
    if (payload.algorithm) setAlgorithm(payload.algorithm);
  }, []);

  const sendToBrowserSerial = useCallback(
    async (line) => {
      if (!serialWriterRef.current) return;
      const trimmed = line.trim();
      if (!trimmed) return;
      if (oneMovePerLine) {
        const moves = trimmed.split(/\s+/).filter(Boolean);
        for (const move of moves) {
          await serialWriterRef.current.write(new TextEncoder().encode(`${move}\n`));
          pushLog(`Serial → ${move}`);
          await new Promise((resolve) => setTimeout(resolve, 50));
        }
        return;
      }
      await serialWriterRef.current.write(new TextEncoder().encode(`${trimmed}\n`));
      pushLog(`Serial → ${trimmed}`);
    },
    [oneMovePerLine, pushLog],
  );

  const afterAlgorithm = useCallback(
    async (data) => {
      setState(data);
      const line = data.algorithm || formatAlgorithm(data.moves);
      if (line) setAlgorithm(line);
      if (line && serialMode === "browser" && serialWriterRef.current) {
        await sendToBrowserSerial(line);
      }
      if (data.parsed?.type === "moves") {
        pushLog(`Moves: ${formatAlgorithm(data.parsed.moves)}`);
      } else if (data.parsed?.command) {
        pushLog(`Command: ${data.parsed.command}`);
      }
    },
    [pushLog, sendToBrowserSerial, serialMode],
  );

  function ensureSerialReady() {
    if (serialMode === "server" && !serverConnected) {
      throw new Error("Connect Server USB first (pick /dev/cu.usbmodem…, not tty).");
    }
    if (serialMode === "browser" && !browserConnected) {
      throw new Error("Connect Browser USB first (Connect Arduino button — no port dropdown).");
    }
  }

  const runVoice = useCallback(
    async (text, alternatives = []) => {
      const primary = text.trim();
      if (!primary) return;
      setTranscript(primary);
      setInterimText("");
      pushLog(`Heard: ${primary}`);
      if (!isResetPhrase(primary)) {
        ensureSerialReady();
      }
      const data = await postVoice(primary, {
        alternatives,
        useServerSerial: serialMode === "server" && serverConnected,
      });
      if (data.parsed?.heard && data.parsed.heard !== primary) {
        pushLog(`Matched: ${data.parsed.heard}`);
      }
      await afterAlgorithm(data);
      setError("");
    },
    [afterAlgorithm, pushLog, serialMode, serverConnected, browserConnected],
  );

  runVoiceRef.current = runVoice;
  listeningRef.current = listening;

  const stopMicMonitor = useCallback(() => {
    if (micLevelFrameRef.current) {
      cancelAnimationFrame(micLevelFrameRef.current);
      micLevelFrameRef.current = null;
    }
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((track) => track.stop());
      micStreamRef.current = null;
    }
    if (micAudioRef.current) {
      micAudioRef.current.context.close().catch(() => {});
      micAudioRef.current = null;
    }
    setMicLevel(0);
  }, []);

  const startMicMonitor = useCallback(async () => {
    stopMicMonitor();
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error("This browser does not expose microphone access.");
    }
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true },
    });
    micStreamRef.current = stream;
    const context = new AudioContext();
    const source = context.createMediaStreamSource(stream);
    const analyser = context.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);
    micAudioRef.current = { context, analyser };

    const sample = () => {
      if (!micAudioRef.current) return;
      const bins = new Uint8Array(micAudioRef.current.analyser.frequencyBinCount);
      micAudioRef.current.analyser.getByteFrequencyData(bins);
      const avg = bins.reduce((sum, value) => sum + value, 0) / bins.length;
      setMicLevel(Math.round(avg));
      micLevelFrameRef.current = requestAnimationFrame(sample);
    };
    sample();
  }, [stopMicMonitor]);

  const dispatchVoice = useCallback((text, alternatives = []) => {
    const primary = text.trim();
    if (!primary) return;
    const key = primary.toLowerCase();
    const now = Date.now();
    if (lastVoiceAtRef.current.key === key && now - lastVoiceAtRef.current.at < 1200) {
      return;
    }
    lastVoiceAtRef.current = { key, at: now };
    runVoiceRef.current?.(primary, alternatives).catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    refreshState().catch((err) => setError(err.message));
    fetchSerialStatus()
      .then((status) => {
        setServerPorts(status.available_ports || []);
        setServerConnected(Boolean(status.connected));
        if (status.port) {
          setServerPort(status.port);
        } else if (status.recommended_port) {
          setServerPort(status.recommended_port);
        }
      })
      .catch(() => {});
  }, [refreshState]);

  useEffect(() => {
    if (!SpeechRecognition) return undefined;

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 5;

    recognition.onstart = () => {
      pushLog("Mic active — say Scramble, Solve, or a move.");
      setSpeechHint("");
    };

    recognition.onspeechstart = () => {
      pushLog("Speech detected…");
    };

    recognition.onresult = (event) => {
      let interim = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        if (result.isFinal) {
          const transcripts = [];
          for (let alt = 0; alt < result.length; alt += 1) {
            const piece = result[alt].transcript.trim();
            if (piece && !transcripts.includes(piece)) transcripts.push(piece);
          }
          if (transcripts.length) {
            const [primary, ...alternatives] = transcripts;
            dispatchVoice(primary, alternatives);
          }
        } else {
          interim += result[0].transcript;
        }
      }
      setInterimText(interim.trim());

      const interimLower = interim.trim().toLowerCase();
      if (/^(scramble|solve|reset|clear)\b/.test(interimLower)) {
        window.clearTimeout(interimCommandTimerRef.current);
        interimCommandTimerRef.current = window.setTimeout(() => {
          dispatchVoice(interim.trim());
        }, 450);
      }
    };

    recognition.onerror = (event) => {
      const code = event.error || "";
      if (code === "aborted") return;
      if (code === "no-speech") {
        pushLog("No speech heard — speak louder or use Type command below.");
        return;
      }
      if (code === "network") {
        setSpeechHint(
          "Speech-to-text needs internet (Chrome uses Google). Use Type command below if offline.",
        );
      }
      setError(code || "Speech recognition error.");
      if (code === "not-allowed" || code === "service-not-allowed") {
        setListening(false);
      }
    };

    recognition.onend = () => {
      if (!listeningRef.current) return;
      window.setTimeout(() => {
        if (!listeningRef.current) return;
        try {
          recognition.start();
        } catch (error) {
          if (error?.name !== "InvalidStateError") {
            setError(error?.message || "Could not restart microphone.");
            setListening(false);
          }
        }
      }, 250);
    };

    recognitionRef.current = recognition;
    return () => {
      window.clearTimeout(interimCommandTimerRef.current);
      recognition.onstart = null;
      recognition.onspeechstart = null;
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.onend = null;
      try {
        recognition.stop();
      } catch {
        /* ignore */
      }
      recognitionRef.current = null;
    };
  }, [dispatchVoice, pushLog]);

  useEffect(() => {
    const recognition = recognitionRef.current;
    if (!recognition) return undefined;

    if (listening) {
      try {
        recognition.start();
      } catch (error) {
        if (error?.name !== "InvalidStateError") {
          setError(error?.message || "Could not start microphone.");
          setListening(false);
        }
      }
    } else {
      try {
        recognition.stop();
      } catch {
        /* ignore */
      }
      setInterimText("");
      stopMicMonitor();
    }
    return undefined;
  }, [listening, stopMicMonitor]);

  useEffect(() => {
    if (!listening) return undefined;
    const timer = window.setInterval(() => {
      if (micLevel >= 8 && !transcript && !interimText) {
        setSpeechHint(
          "Mic picks up sound but speech-to-text is silent. Use Google Chrome (not embedded preview), allow mic, stay online — or type Scramble below.",
        );
      }
    }, 5000);
    return () => window.clearInterval(timer);
  }, [listening, micLevel, transcript, interimText]);

  useEffect(() => () => stopMicMonitor(), [stopMicMonitor]);

  async function toggleListening() {
    if (listening) {
      setListening(false);
      stopMicMonitor();
      return;
    }
    setError("");
    setSpeechHint("");
    try {
      await startMicMonitor();
      setListening(true);
    } catch (err) {
      setError(err.message || "Microphone permission denied.");
    }
  }

  async function handleTypedCommand(event) {
    event.preventDefault();
    const text = typedCommand.trim();
    if (!text) return;
    try {
      await runVoice(text);
      setTypedCommand("");
    } catch (err) {
      setError(err.message);
    }
  }

  async function connectBrowserSerial() {
    if (!navigator.serial) {
      setError("Web Serial is not available in this browser. Use Chrome or connect via the server.");
      return;
    }
    const port = await navigator.serial.requestPort();
    await port.open({ baudRate: baudRate });
    serialPortRef.current = port;
    serialWriterRef.current = port.writable.getWriter();
    setBrowserConnected(true);
    pushLog(`Browser serial connected (${baudRate} baud).`);
  }

  async function disconnectBrowserSerial() {
    if (serialWriterRef.current) {
      await serialWriterRef.current.close();
      serialWriterRef.current = null;
    }
    if (serialPortRef.current) {
      await serialPortRef.current.close();
      serialPortRef.current = null;
    }
    setBrowserConnected(false);
  }

  async function handleScramble() {
    try {
      ensureSerialReady();
      const data = await scrambleCube({
        useServerSerial: serialMode === "server" && serverConnected,
      });
      await afterAlgorithm(data);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleSolve() {
    try {
      ensureSerialReady();
      const data = await solveCubeControl({
        useServerSerial: serialMode === "server" && serverConnected,
      });
      await afterAlgorithm(data);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleServerConnect() {
    const port = serverPort || serverPorts.find((p) => p.includes("usbmodem")) || serverPorts[0];
    if (!port) {
      setError("No USB serial port found. Plug in the Arduino and refresh.");
      return;
    }
    setServerConnecting(true);
    setError("");
    try {
      const status = await connectServerSerial(port, baudRate);
      setServerConnected(Boolean(status.connected));
      setServerPort(status.port || port);
      pushLog(`Server serial connected on ${status.port || port}.`);
    } catch (err) {
      setServerConnected(false);
      setError(err.message);
    } finally {
      setServerConnecting(false);
    }
  }

  return (
    <section className="slide slide-control">
      <header className="control-header">
        <button type="button" className="ghost" onClick={onBack}>
          ← Scanner
        </button>
        <div>
          <p className="kicker">Cube Control</p>
          <h1>Voice, scramble, solve, serial</h1>
        </div>
      </header>

      <p className="lead">
        Say moves like <strong>R</strong>, <strong>R prime</strong>, or <strong>R 2</strong>. Say{" "}
        <strong>Scramble</strong> or <strong>Solve</strong>. The algorithm string is sent to Arduino
        serial (one line, space-separated moves).
      </p>

      <div className="control-grid">
        <div className="control-panel">
          <h2>Voice</h2>
          {!SpeechRecognition && (
            <p className="hint">Speech recognition needs Google Chrome on desktop (not all in-app browsers).</p>
          )}
          <button
            type="button"
            className={listening ? "primary danger" : "primary"}
            disabled={!SpeechRecognition}
            onClick={() => toggleListening().catch((err) => setError(err.message))}
          >
            {listening ? "Stop listening" : "Start listening"}
          </button>
          {listening && (
            <div className="mic-meter" aria-label="Microphone level">
              <div className="mic-meter-fill" style={{ width: `${Math.min(100, micLevel * 2)}%` }} />
            </div>
          )}
          {listening && micLevel < 3 && (
            <p className="hint">Mic level is flat — check System Settings → Privacy → Microphone for Chrome.</p>
          )}
          {speechHint && <p className="hint error">{speechHint}</p>}
          {listening && !interimText && !transcript && (
            <p className="hint">Listening… say <strong>Scramble</strong> (pause briefly).</p>
          )}
          <form className="voice-type-form" onSubmit={handleTypedCommand}>
            <input
              type="text"
              value={typedCommand}
              placeholder="Type Scramble, Solve, R prime…"
              onChange={(event) => setTypedCommand(event.target.value)}
              autoComplete="off"
            />
            <button type="submit">Send</button>
          </form>
          <p className="hint">If voice never shows “Heard: …”, use Send — same as speaking.</p>
          {interimText && listening && (
            <p className="transcript interim">…{interimText}</p>
          )}
          {transcript && <p className="transcript">Heard: {transcript}</p>}
          <div className="control-actions">
            <button type="button" onClick={handleScramble}>
              Scramble
            </button>
            <button type="button" onClick={handleSolve}>
              Solve
            </button>
          </div>
        </div>

        <div className="control-panel">
          <h2>Arduino serial</h2>
          <p className="hint">
            <strong>Close Arduino Serial Monitor</strong> before connecting here. Use{" "}
            <strong>Server USB</strong> with <code>python app.py</code> (port dropdown). Browser USB
            has no dropdown — use <strong>Connect Arduino</strong> and pick the device in Chrome.
          </p>
          <label className="serial-mode">
            <input
              type="radio"
              name="serialMode"
              checked={serialMode === "server"}
              onChange={() => setSerialMode("server")}
            />
            Server USB (recommended — port dropdown)
          </label>
          <label className="serial-mode">
            <input
              type="radio"
              name="serialMode"
              checked={serialMode === "browser"}
              onChange={() => setSerialMode("browser")}
            />
            Browser USB (Web Serial — Chrome popup)
          </label>

          {serialMode === "browser" && (
            <div className="serial-row">
              {!browserConnected ? (
                <button type="button" onClick={connectBrowserSerial}>
                  Connect Arduino
                </button>
              ) : (
                <button type="button" onClick={disconnectBrowserSerial}>
                  Disconnect
                </button>
              )}
              <span>{browserConnected ? "Connected" : "Not connected"}</span>
            </div>
          )}

          <label className="serial-mode">
            Baud rate{" "}
            <select value={baudRate} onChange={(event) => setBaudRate(Number(event.target.value))}>
              <option value={115200}>115200 (Arduino IDE default)</option>
              <option value={9600}>9600</option>
            </select>
          </label>
          <label className="serial-mode">
            <input
              type="checkbox"
              checked={oneMovePerLine}
              onChange={(event) => setOneMovePerLine(event.target.checked)}
            />
            One move per line (debug only — disables RUBI X opposite-face pairing)
          </label>
          <p className="hint">
            RUBI X expects one serial line per sequence, e.g.{" "}
            <code>D2 B2 F' U D' L</code>. Your parser handles R, R', and R2.
          </p>

          {serialMode === "server" && (
            <div className="serial-row">
              <select value={serverPort} onChange={(event) => setServerPort(event.target.value)}>
                <option value="">Select port…</option>
                {serverPorts.map((port) => (
                  <option key={port} value={port}>
                    {port}
                  </option>
                ))}
              </select>
              {!serverConnected ? (
                <button type="button" disabled={serverConnecting} onClick={handleServerConnect}>
                  {serverConnecting ? "Connecting…" : "Connect"}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() =>
                    disconnectServerSerial()
                      .then(() => setServerConnected(false))
                      .catch((err) => setError(err.message))
                  }
                >
                  Disconnect
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="control-panel algorithm-panel">
        <h2>Algorithm string</h2>
        <pre className="algorithm-line">{algorithm || "(none yet)"}</pre>
        <p className="hint">
          Virtual cube: {state?.solved ? "solved" : "scrambled"} · {state?.history?.length || 0} moves
          tracked
        </p>
      </div>

      {error && <p className="hint error">{error}</p>}

      <ul className="control-log">
        {log.map((entry, index) => (
          <li key={`${entry}-${index}`}>{entry}</li>
        ))}
      </ul>
    </section>
  );
}
