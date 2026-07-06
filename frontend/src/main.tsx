import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { reportClientError } from "./api/reportError";
import { TrailsProvider } from "./data/TrailsProvider";
import { AppStateProvider } from "./state/AppState";
import { ProfileProvider } from "./state/ProfileContext";
import "./styles/global.css";

// Catch errors the React boundary can't see: async rejections and uncaught script errors.
window.addEventListener("unhandledrejection", (e) => {
  const reason = e.reason as { message?: string; stack?: string } | undefined;
  reportClientError(reason?.message ?? String(e.reason), { kind: "unhandledrejection", stack: reason?.stack });
});
window.addEventListener("error", (e) => {
  if (e.message) reportClientError(e.message, { kind: "window.error", stack: e.error?.stack });
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <ProfileProvider>
          <TrailsProvider>
            <AppStateProvider>
              <App />
            </AppStateProvider>
          </TrailsProvider>
        </ProfileProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>,
);
