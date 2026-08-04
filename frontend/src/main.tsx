import React from "react";
import ReactDOM from "react-dom/client";
import { Toaster } from "react-hot-toast";

import { App } from "./App";
import "./styles/index.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
    <Toaster position="top-right" />
  </React.StrictMode>,
);

