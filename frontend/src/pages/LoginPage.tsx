import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { AuthLayout } from "@/pages/AuthLayout";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { useAuth } from "@/hooks/useAuth";
import { ApiError } from "@/lib/api";

export function LoginPage() {
  const { login, isSubmitting } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await login({ username, password });
      // Navigation happens via the route guard once the session is cached.
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "Could not sign in. Try again.",
      );
    }
  };

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to continue your conversations."
      footer={
        <>
          New here?{" "}
          <Link to="/register" className="font-medium text-accent hover:underline">
            Create an account
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <Field
          label="Username"
          name="username"
          autoComplete="username"
          autoFocus
          required
          value={username}
          onChange={(event) => setUsername(event.target.value)}
        />
        <Field
          label="Password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />

        {error && (
          <p role="alert" className="text-xs text-danger">
            {error}
          </p>
        )}

        <Button type="submit" size="lg" className="w-full" isLoading={isSubmitting}>
          Sign in
        </Button>
      </form>
    </AuthLayout>
  );
}
