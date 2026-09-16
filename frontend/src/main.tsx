import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { App } from "@/App";
import { AuthProvider } from "@/hooks/useAuth";
import { ApiError } from "@/lib/api";

import "highlight.js/styles/github-dark.css";
import "@/index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // A refetch mid-stream would briefly show the transcript without the
      // message currently being answered, so focus refetching stays off.
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        // Never retry an auth or "not found" failure; it will not change.
        if (error instanceof ApiError && error.status < 500) return false;
        return failureCount < 2;
      },
    },
  },
});

const container = document.getElementById("root");
if (!container) throw new Error("Root element #root was not found.");

createRoot(container).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
