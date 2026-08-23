import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { VoiceStateProvider } from "./state/VoiceStateContext";
import "./styles/globals.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <VoiceStateProvider>
      <App />
    </VoiceStateProvider>
  </React.StrictMode>
);
