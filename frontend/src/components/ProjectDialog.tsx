import { useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";

interface ProjectDialogProps {
  open: boolean;
  isPending?: boolean;
  error?: string | null;
  onSubmit: (values: { name: string; description: string | null }) => void;
  onClose: () => void;
}

export function ProjectDialog({
  open,
  isPending = false,
  error,
  onSubmit,
  onClose,
}: ProjectDialogProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  useEffect(() => {
    if (open) {
      setName("");
      setDescription("");
    }
  }, [open]);

  const submit = () => {
    if (!name.trim()) return;
    onSubmit({ name: name.trim(), description: description.trim() || null });
  };

  return (
    <Modal
      open={open}
      title="New project"
      description="Projects keep related conversations together."
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button isLoading={isPending} disabled={!name.trim()} onClick={submit}>
            Create project
          </Button>
        </>
      }
    >
      <Field
        label="Name"
        value={name}
        maxLength={128}
        placeholder="Client work"
        onChange={(event) => setName(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") submit();
        }}
      />
      <Field
        label="Description (optional)"
        value={description}
        maxLength={2000}
        placeholder="What this project is about"
        onChange={(event) => setDescription(event.target.value)}
      />
      {error && <p className="text-xs text-danger">{error}</p>}
    </Modal>
  );
}
