export async function fetchControlState() {
  const response = await fetch("/api/cube-control/state");
  if (!response.ok) throw new Error("Could not load cube control state.");
  return response.json();
}

export async function postVoice(text, { alternatives = [], useServerSerial = false } = {}) {
  const response = await fetch("/api/cube-control/voice", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      alternatives,
      send_serial: useServerSerial,
    }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const heard = data.parsed?.text || text;
    throw new Error(data.error || `Could not understand “${heard}”. Try “R”, “R prime”, Scramble, or Solve.`);
  }
  if (data.parsed?.type === "empty") {
    throw new Error("Heard nothing useful — pause after speaking.");
  }
  return data;
}

export async function scrambleCube({ useServerSerial = false, length = 20 } = {}) {
  const response = await fetch("/api/cube-control/scramble", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ length, send_serial: useServerSerial }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Scramble failed.");
  return data;
}

export async function solveCubeControl({ useServerSerial = false } = {}) {
  const response = await fetch("/api/cube-control/solve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ send_serial: useServerSerial }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Solve failed.");
  return data;
}

export async function fetchSerialStatus() {
  const response = await fetch("/api/cube-control/serial");
  if (!response.ok) throw new Error("Could not read serial status.");
  return response.json();
}

export async function connectServerSerial(port, baud = 115200) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 12_000);
  try {
    const response = await fetch("/api/cube-control/serial/connect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ port, baud }),
      signal: controller.signal,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "Serial connect failed.");
    return data;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error(
        "Connect timed out. Close Arduino Serial Monitor, restart python app.py, then try again.",
      );
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

export async function disconnectServerSerial() {
  const response = await fetch("/api/cube-control/serial/disconnect", { method: "POST" });
  if (!response.ok) throw new Error("Serial disconnect failed.");
  return response.json();
}
