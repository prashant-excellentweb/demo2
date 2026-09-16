import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Sparkles } from "lucide-react";

import { useAuth } from "@/hooks/useAuth";
import { ChatPage } from "@/pages/ChatPage";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";

function SplashScreen() {
  return (
    <div className="flex h-full items-center justify-center bg-canvas">
      <span className="flex size-12 animate-pulse items-center justify-center rounded-2xl bg-accent text-accent-fg">
        <Sparkles className="size-6" />
      </span>
    </div>
  );
}

/** Blocks protected routes until the session cookie has been resolved. */
function RequireAuth({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return <SplashScreen />;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RedirectIfSignedIn({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return <SplashScreen />;
  if (user) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <RedirectIfSignedIn>
            <LoginPage />
          </RedirectIfSignedIn>
        }
      />
      <Route
        path="/register"
        element={
          <RedirectIfSignedIn>
            <RegisterPage />
          </RedirectIfSignedIn>
        }
      />
      <Route
        path="/"
        element={
          <RequireAuth>
            <ChatPage />
          </RequireAuth>
        }
      />
      {/* Chat id in the URL keeps conversations linkable and the back button useful. */}
      <Route
        path="/c/:chatId"
        element={
          <RequireAuth>
            <ChatPage />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
