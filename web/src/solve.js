const SOLVE_TIMEOUT_MS = 120_000;

export async function solveCube(state, faces) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), SOLVE_TIMEOUT_MS);
  try {
    const response = await fetch("/api/solve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ state, faces: faces || undefined }),
      signal: controller.signal,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || "The solver could not finish.");
    }
    return data;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error(
        "The server did not respond in time. Make sure python app.py is running, then fix any wrong sticker colors on the layout and try again.",
      );
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}
