import React from "react";
import ReactDOM from "react-dom/client";
import * as Sentry from "@sentry/react";
import { QueryClientProvider } from "@tanstack/react-query";

import App from "./App";
import { ErrorBoundary } from "./components/ui/ErrorBoundary";
import { queryClient } from "./queryClient";
import { initAnalytics } from "./analytics";
import "./styles.css";

const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN;
if (SENTRY_DSN) {
  Sentry.init({ dsn: SENTRY_DSN, environment: import.meta.env.MODE });
}

initAnalytics();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
