import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Menu, PanelLeftOpen, Plus, Shield } from "lucide-react";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { ProjectDialog } from "@/components/ProjectDialog";
import { SettingsDialog } from "@/components/SettingsDialog";
import { Composer } from "@/components/chat/Composer";
import { EmptyState } from "@/components/chat/EmptyState";
import {
  MessageTimeline,
  type DisplayMessage,
} from "@/components/chat/MessageTimeline";
import { Sidebar } from "@/components/layout/Sidebar";
import { IconButton } from "@/components/ui/IconButton";
import { useAuth } from "@/hooks/useAuth";
import { useAutoScroll } from "@/hooks/useAutoScroll";
import {
  chatKeys,
  useChat,
  useChats,
  useCreateChat,
  useCreateProject,
  useDeleteChat,
  useDeleteProject,
  useProjects,
  useRewindChat,
  useUpdateChat,
  useUploadAttachment,
} from "@/hooks/useChatData";
import { useMessageStream } from "@/hooks/useMessageStream";
import { ApiError } from "@/lib/api";
import type { Attachment, EphemeralTurn } from "@/types";

type PendingDeletion =
  | { kind: "chat"; id: string; label: string }
  | { kind: "project"; id: string; label: string };

export function ChatPage() {
  const { chatId: routeChatId = null } = useParams<{ chatId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, logout } = useAuth();

  const [input, setInput] = useState("");
  const [webSearch, setWebSearch] = useState(false);
  const [temporary, setTemporary] = useState(false);
  const [temporaryTurns, setTemporaryTurns] = useState<EphemeralTurn[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [uploadingNames, setUploadingNames] = useState<string[]>([]);
  const [optimisticUser, setOptimisticUser] = useState<{
    content: string;
    attachments: Attachment[];
  } | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isProjectDialogOpen, setIsProjectDialogOpen] = useState(false);
  const [pendingDeletion, setPendingDeletion] = useState<PendingDeletion | null>(null);
  // Set when starting a chat from a project's "+" so the chat row is only
  // created once the first message is actually sent.
  const [pendingProjectId, setPendingProjectId] = useState<string | null>(null);

  const chats = useChats();
  const projects = useProjects();
  const chatDetail = useChat(temporary ? null : routeChatId);
  const createChat = useCreateChat();
  const updateChat = useUpdateChat();
  const deleteChat = useDeleteChat();
  const deleteProject = useDeleteProject();
  const createProject = useCreateProject();
  const rewindChat = useRewindChat();
  const uploadAttachment = useUploadAttachment();
  const stream = useMessageStream();

  const messages = useMemo<DisplayMessage[]>(() => {
    if (temporary) {
      return temporaryTurns.map((turn, index) => ({
        id: `temp-${index}`,
        role: turn.role,
        content: turn.content,
        attachments: [],
        sources: null,
        editable: turn.role === "user",
      }));
    }

    const persisted: DisplayMessage[] = (chatDetail.data?.messages ?? []).map((message) => ({
      id: message.id,
      role: message.role,
      content: message.content,
      attachments: message.attachments,
      sources: message.sources,
      editable: message.role === "user",
    }));

    // Shown until the refetch that follows a completed stream lands.
    if (optimisticUser) {
      persisted.push({
        id: "optimistic-user",
        role: "user",
        content: optimisticUser.content,
        attachments: optimisticUser.attachments,
        sources: null,
        editable: false,
      });
    }
    return persisted;
  }, [temporary, temporaryTurns, chatDetail.data, optimisticUser]);

  const { containerRef, handleScroll } = useAutoScroll(
    `${messages.length}:${stream.text.length}`,
  );

  // A chat can vanish from under us (deleted in another tab); fall back to the
  // new-chat view instead of rendering an error.
  useEffect(() => {
    if (chatDetail.error instanceof ApiError && chatDetail.error.status === 404) {
      navigate("/", { replace: true });
    }
  }, [chatDetail.error, navigate]);

  const resetComposer = useCallback(() => {
    setInput("");
    setAttachments([]);
    setSendError(null);
  }, []);

  const startNewChat = useCallback(
    (projectId: string | null = null) => {
      setPendingProjectId(projectId);
      setTemporary(false);
      setTemporaryTurns([]);
      setOptimisticUser(null);
      stream.reset();
      resetComposer();
      setIsSidebarOpen(false);
      navigate("/");
    },
    [navigate, resetComposer, stream],
  );

  const selectChat = useCallback(
    (chatId: string) => {
      setTemporary(false);
      setTemporaryTurns([]);
      setOptimisticUser(null);
      setPendingProjectId(null);
      stream.reset();
      resetComposer();
      setIsSidebarOpen(false);
      navigate(`/c/${chatId}`);
    },
    [navigate, resetComposer, stream],
  );

  const addFiles = async (files: File[]) => {
    setSendError(null);
    setUploadingNames((current) => [...current, ...files.map((file) => file.name)]);

    for (const file of files) {
      try {
        const uploaded = await uploadAttachment.mutateAsync(file);
        setAttachments((current) => [...current, uploaded]);
      } catch (error) {
        setSendError(
          error instanceof ApiError
            ? `${file.name}: ${error.message}`
            : `${file.name} could not be uploaded.`,
        );
      } finally {
        setUploadingNames((current) => current.filter((name) => name !== file.name));
      }
    }
  };

  const send = async () => {
    const content = input.trim();
    const outgoing = attachments;
    if (!content && outgoing.length === 0) return;
    if (stream.isStreaming) return;

    setInput("");
    setAttachments([]);
    setSendError(null);

    if (temporary) {
      const turns: EphemeralTurn[] = [
        ...temporaryTurns,
        { role: "user", content },
      ];
      setTemporaryTurns(turns);

      const result = await stream.start(
        "/api/ephemeral-chat/messages",
        { messages: turns, web_search: webSearch },
        {
          onDone: (text) =>
            setTemporaryTurns((current) => [
              ...current,
              { role: "assistant", content: text },
            ]),
        },
      );
      if (result.error) setSendError(result.error);
      stream.reset();
      return;
    }

    let targetChatId = routeChatId;
    if (!targetChatId) {
      try {
        const created = await createChat.mutateAsync({ projectId: pendingProjectId });
        targetChatId = created.id;
        setPendingProjectId(null);
        navigate(`/c/${created.id}`, { replace: true });
      } catch (error) {
        setSendError(
          error instanceof ApiError ? error.message : "Could not start a new chat.",
        );
        return;
      }
    }

    setOptimisticUser({ content, attachments: outgoing });

    const result = await stream.start(`/api/chats/${targetChatId}/messages`, {
      content,
      attachment_ids: outgoing.map((attachment) => attachment.id),
      web_search: webSearch,
    });

    // Refetch before clearing local state so the transcript never blinks empty.
    await queryClient.invalidateQueries({ queryKey: chatKeys.detail(targetChatId) });
    void queryClient.invalidateQueries({ queryKey: chatKeys.list });
    setOptimisticUser(null);
    stream.reset();
    if (result.error) setSendError(result.error);
  };

  const editMessage = async (message: DisplayMessage) => {
    setInput(message.content);
    setSendError(null);

    if (temporary) {
      const index = Number(message.id.replace("temp-", ""));
      setTemporaryTurns((current) => current.slice(0, index));
      return;
    }
    if (!routeChatId) return;

    // Drops this turn and everything after it, so resending continues from here.
    await rewindChat.mutateAsync({ chatId: routeChatId, messageId: message.id });
  };

  const confirmDeletion = async () => {
    if (!pendingDeletion) return;

    if (pendingDeletion.kind === "chat") {
      await deleteChat.mutateAsync(pendingDeletion.id);
      if (routeChatId === pendingDeletion.id) navigate("/", { replace: true });
    } else {
      await deleteProject.mutateAsync(pendingDeletion.id);
    }
    setPendingDeletion(null);
  };

  const activeTitle = temporary
    ? "Temporary chat"
    : (chatDetail.data?.title ?? "New chat");
  const showEmptyState = messages.length === 0 && !stream.isStreaming;

  return (
    <div className="flex h-full overflow-hidden bg-canvas">
      <Sidebar
        user={user!}
        chats={chats.data ?? []}
        projects={projects.data ?? []}
        activeChatId={routeChatId}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        onNewChat={startNewChat}
        onSelectChat={selectChat}
        onRenameChat={(chatId, title) => updateChat.mutate({ chatId, title })}
        onDeleteChat={(chatId) =>
          setPendingDeletion({
            kind: "chat",
            id: chatId,
            label: chats.data?.find((chat) => chat.id === chatId)?.title ?? "this chat",
          })
        }
        onCreateProject={() => setIsProjectDialogOpen(true)}
        onDeleteProject={(projectId) =>
          setPendingDeletion({
            kind: "project",
            id: projectId,
            label:
              projects.data?.find((project) => project.id === projectId)?.name ??
              "this project",
          })
        }
        onOpenSettings={() => setIsSettingsOpen(true)}
        onLogout={logout}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-2 border-b border-line px-3">
          <IconButton
            label="Open sidebar"
            className="lg:hidden"
            onClick={() => setIsSidebarOpen(true)}
          >
            <Menu className="size-[18px]" />
          </IconButton>

          <span className="hidden lg:inline-flex">
            <IconButton label="New chat" onClick={() => startNewChat(null)}>
              <PanelLeftOpen className="size-[18px]" />
            </IconButton>
          </span>

          <h1 className="min-w-0 flex-1 truncate text-sm font-medium text-fg">
            {activeTitle}
          </h1>

          {temporary && (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-accent/30 bg-accent-soft px-2.5 py-1 text-[11px] font-medium text-accent">
              <Shield className="size-3" />
              Not saved
            </span>
          )}

          <IconButton label="New chat" onClick={() => startNewChat(null)}>
            <Plus className="size-[18px]" />
          </IconButton>
        </header>

        <div
          ref={containerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto"
        >
          {showEmptyState ? (
            <EmptyState
              greeting={`How can I help, ${user?.display_name || user?.username}?`}
              temporary={temporary}
              onTemporaryChange={(value) => {
                setTemporary(value);
                setTemporaryTurns([]);
                stream.reset();
                if (value) navigate("/");
              }}
              onPickSuggestion={setInput}
            />
          ) : (
            <MessageTimeline
              messages={messages}
              streamingText={stream.text}
              streamingSources={stream.sources}
              isStreaming={stream.isStreaming}
              statusLabel={webSearch ? "Searching the web..." : null}
              error={sendError ?? stream.error}
              onEdit={editMessage}
            />
          )}
        </div>

        <Composer
          value={input}
          onChange={setInput}
          onSubmit={send}
          attachments={attachments}
          uploadingNames={uploadingNames}
          onAddFiles={addFiles}
          onRemoveAttachment={(id) =>
            setAttachments((current) => current.filter((item) => item.id !== id))
          }
          webSearch={webSearch}
          onToggleWebSearch={() => setWebSearch((value) => !value)}
          isStreaming={stream.isStreaming}
          onStop={stream.stop}
          temporary={temporary}
        />
      </main>

      {user && (
        <SettingsDialog
          open={isSettingsOpen}
          user={user}
          onClose={() => setIsSettingsOpen(false)}
        />
      )}

      <ProjectDialog
        open={isProjectDialogOpen}
        isPending={createProject.isPending}
        error={
          createProject.error instanceof ApiError ? createProject.error.message : null
        }
        onSubmit={async (values) => {
          await createProject.mutateAsync(values);
          setIsProjectDialogOpen(false);
        }}
        onClose={() => setIsProjectDialogOpen(false)}
      />

      <ConfirmDialog
        open={pendingDeletion !== null}
        title={
          pendingDeletion?.kind === "project" ? "Delete project?" : "Delete chat?"
        }
        description={
          pendingDeletion?.kind === "project"
            ? `"${pendingDeletion.label}" will be removed. Its chats are kept and moved back to your recent chats.`
            : `"${pendingDeletion?.label}" and its messages will be permanently deleted.`
        }
        isPending={deleteChat.isPending || deleteProject.isPending}
        onConfirm={confirmDeletion}
        onCancel={() => setPendingDeletion(null)}
      />
    </div>
  );
}
