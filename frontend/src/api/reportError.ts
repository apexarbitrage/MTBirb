/*
 * Best-effort client-error reporting. POSTs a small report to the backend sink
 * (POST /api/client-errors), which logs it and forwards to Sentry when configured, so a
 * white-screen crash in the field isn't invisible. Fire-and-forget, throttled, and never throws -
 * reporting must not itself break the app.
 */

let sent = 0;
const MAX_REPORTS = 10; // cap so an error loop can't spam the sink

interface ErrorInfo {
  kind?: string;
  stack?: string;
  url?: string;
}

export function reportClientError(message: string, info: ErrorInfo = {}): void {
  if (sent >= MAX_REPORTS) return;
  sent += 1;
  try {
    const body = JSON.stringify({
      message: String(message).slice(0, 2000),
      kind: info.kind,
      stack: info.stack?.slice(0, 8000),
      url: info.url ?? window.location.href,
      userAgent: navigator.userAgent?.slice(0, 500),
    });
    // keepalive lets it still send during an unload/crash; the response is ignored.
    void fetch("/api/client-errors", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true,
    }).catch(() => {});
  } catch {
    /* reporting is best-effort; never surface an error from here */
  }
}
