import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import { TrailsProvider } from "./data/TrailsProvider";
import { AppStateProvider } from "./state/AppState";
import "./styles/global.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <TrailsProvider>
        <AppStateProvider>
          <App />
        </AppStateProvider>
      </TrailsProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
