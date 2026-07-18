"use client";

import { useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { LoginForm } from "@/components/LoginForm";

type User = {
  username: string;
};

export const AuthenticatedApp = () => {
  const [user, setUser] = useState<User | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [logoutError, setLogoutError] = useState<string | null>(null);

  useEffect(() => {
    const checkSession = async () => {
      try {
        const response = await fetch("/api/auth/me");
        if (response.ok) {
          setUser((await response.json()) as User);
        }
      } catch {
        setUser(null);
      } finally {
        setIsCheckingSession(false);
      }
    };

    void checkSession();
  }, []);

  const handleLogin = async (username: string, password: string) => {
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        return response.status === 401
          ? "Invalid username or password."
          : "Unable to sign in. Please try again.";
      }

      setUser((await response.json()) as User);
      return null;
    } catch {
      return "Unable to sign in. Please try again.";
    }
  };

  const handleLogout = async () => {
    setLogoutError(null);
    try {
      const response = await fetch("/api/auth/logout", { method: "POST" });
      if (!response.ok) {
        setLogoutError("Unable to sign out. Please try again.");
        return;
      }
      setUser(null);
    } catch {
      setLogoutError("Unable to sign out. Please try again.");
    }
  };

  if (isCheckingSession) {
    return (
      <main className="flex min-h-screen items-center justify-center px-6">
        <p className="text-sm font-semibold text-[var(--gray-text)]" role="status">
          Checking your session…
        </p>
      </main>
    );
  }

  if (!user) {
    return <LoginForm onLogin={handleLogin} />;
  }

  return (
    <KanbanBoard
      username={user.username}
      logoutError={logoutError}
      onLogout={handleLogout}
    />
  );
};
