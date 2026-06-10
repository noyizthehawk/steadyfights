import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";

// getElementById returns `HTMLElement | null`, so TS makes you prove it's there.
// The `!` is a non-null assertion: "I know #root exists, trust me."
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
