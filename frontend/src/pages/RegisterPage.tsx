import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { AuthLayout } from "@/pages/AuthLayout";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { useAuth } from "@/hooks/useAuth";
import { ApiError } from "@/lib/api";

const MIN_PASSWORD_LENGTH = 8;

export function RegisterPage() {
  const { register, isSubmitting } = useAuth();
  const [displayName, setDisplayName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);

    // Checked here too so the user gets the message without a round trip.
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }

    try {
      await register({ username, password, displayName });
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Could not create your account. Try again.",
      );
    }
  };

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Start chatting in a few seconds."
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-accent hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <Field
          label="Display name"
          name="displayName"
          autoComplete="name"
          autoFocus
          placeholder="How should Buddy address you?"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
        />
        <Field
          label="Username"
          name="username"
          autoComplete="username"
          required
          minLength={3}
          maxLength={64}
          hint="Letters, numbers, dots, dashes and underscores."
          value={username}
          onChange={(event) => setUsername(event.target.value)}
        />
        <Field
          label="Password"
          name="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={MIN_PASSWORD_LENGTH}
          hint={`At least ${MIN_PASSWORD_LENGTH} characters.`}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />

        {error && (
          <p role="alert" className="text-xs text-danger">
            {error}
          </p>
        )}

        <Button type="submit" size="lg" className="w-full" isLoading={isSubmitting}>
          Create account
        </Button>
      </form>
    </AuthLayout>
  );
}
