import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import { ApiError, api } from "@/lib/api";
import type { DailyUsage, User } from "@/types";

interface SettingsDialogProps {
  open: boolean;
  user: User;
  onClose: () => void;
}

export function SettingsDialog({ open, user, onClose }: SettingsDialogProps) {
  const queryClient = useQueryClient();
  const [displayName, setDisplayName] = useState(user.display_name ?? "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setDisplayName(user.display_name ?? "");
      setCurrentPassword("");
      setNewPassword("");
      setStatus(null);
      setError(null);
    }
  }, [open, user.display_name]);

  const usage = useQuery({
    queryKey: ["usage", "daily"],
    queryFn: () => api.get<DailyUsage>("/api/users/me/usage"),
    enabled: open,
  });

  const save = useMutation({
    mutationFn: () =>
      api.patch<User>("/api/users/me", {
        display_name: displayName.trim() || null,
        current_password: currentPassword || null,
        new_password: newPassword || null,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["auth", "me"], updated);
      setCurrentPassword("");
      setNewPassword("");
      setError(null);
      setStatus("Profile updated.");
    },
    onError: (mutationError) => {
      setStatus(null);
      setError(
        mutationError instanceof ApiError
          ? mutationError.message
          : "Could not save your changes.",
      );
    },
  });

  const budget = usage.data?.daily_budget ?? 0;
  const used = usage.data?.tokens_used ?? 0;
  const percentUsed = budget > 0 ? Math.min(100, Math.round((used / budget) * 100)) : 0;

  return (
    <Modal
      open={open}
      title="Settings"
      description={`Signed in as ${user.username}`}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
          <Button isLoading={save.isPending} onClick={() => save.mutate()}>
            Save changes
          </Button>
        </>
      }
    >
      <Field
        label="Display name"
        value={displayName}
        maxLength={128}
        placeholder={user.username}
        onChange={(event) => setDisplayName(event.target.value)}
      />

      <div className="space-y-4 rounded-xl border border-line bg-surface/60 p-3.5">
        <p className="text-xs font-medium text-fg">Change password</p>
        <Field
          label="Current password"
          type="password"
          autoComplete="current-password"
          value={currentPassword}
          placeholder="Required to set a new password"
          onChange={(event) => setCurrentPassword(event.target.value)}
        />
        <Field
          label="New password"
          type="password"
          autoComplete="new-password"
          value={newPassword}
          hint="At least 8 characters. Leave both fields blank to keep your current password."
          onChange={(event) => setNewPassword(event.target.value)}
        />
      </div>

      {usage.data && budget > 0 && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-fg-muted">Today's usage</span>
            <span className="text-fg-subtle">
              {used.toLocaleString()} / {budget.toLocaleString()} tokens
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-line">
            <div
              className="h-full rounded-full bg-accent transition-[width]"
              style={{ width: `${percentUsed}%` }}
            />
          </div>
          <p className="text-[11px] text-fg-subtle">Resets at midnight UTC.</p>
        </div>
      )}

      {status && <p className="text-xs text-success">{status}</p>}
      {error && <p className="text-xs text-danger">{error}</p>}
    </Modal>
  );
}
