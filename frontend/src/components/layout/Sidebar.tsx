import { useMemo, useState } from "react";
import {
  ChevronRight,
  FolderPlus,
  LogOut,
  Moon,
  Plus,
  Settings,
  Sparkles,
  Sun,
  Trash2,
  X,
} from "lucide-react";

import { ChatListItem } from "@/components/layout/ChatListItem";
import { IconButton } from "@/components/ui/IconButton";
import { useTheme } from "@/hooks/useTheme";
import { cn, initialsOf, relativeDayGroup } from "@/lib/utils";
import type { ChatSummary, Project, User } from "@/types";

interface SidebarProps {
  user: User;
  chats: ChatSummary[];
  projects: Project[];
  activeChatId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onNewChat: (projectId?: string | null) => void;
  onSelectChat: (chatId: string) => void;
  onRenameChat: (chatId: string, title: string) => void;
  onDeleteChat: (chatId: string) => void;
  onCreateProject: () => void;
  onDeleteProject: (projectId: string) => void;
  onOpenSettings: () => void;
  onLogout: () => void;
}

export function Sidebar({
  user,
  chats,
  projects,
  activeChatId,
  isOpen,
  onClose,
  onNewChat,
  onSelectChat,
  onRenameChat,
  onDeleteChat,
  onCreateProject,
  onDeleteProject,
  onOpenSettings,
  onLogout,
}: SidebarProps) {
  const { theme, toggle } = useTheme();
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const chatsByProject = useMemo(() => {
    const grouped = new Map<string, ChatSummary[]>();
    for (const chat of chats) {
      if (!chat.project_id) continue;
      const bucket = grouped.get(chat.project_id) ?? [];
      bucket.push(chat);
      grouped.set(chat.project_id, bucket);
    }
    return grouped;
  }, [chats]);

  /** Unfiled chats, bucketed into the date headings people expect. */
  const recentGroups = useMemo(() => {
    const groups: { label: string; chats: ChatSummary[] }[] = [];
    for (const chat of chats) {
      if (chat.project_id) continue;
      const label = relativeDayGroup(chat.updated_at);
      const last = groups.at(-1);
      if (last && last.label === label) last.chats.push(chat);
      else groups.push({ label, chats: [chat] });
    }
    return groups;
  }, [chats]);

  return (
    <>
      {/* Scrim for the mobile drawer. */}
      <div
        onClick={onClose}
        className={cn(
          "fixed inset-0 z-30 bg-black/50 transition-opacity lg:hidden",
          isOpen ? "opacity-100" : "pointer-events-none opacity-0",
        )}
      />

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-line bg-surface",
          "transition-transform duration-200 lg:static lg:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <header className="flex items-center gap-2 px-3 py-3">
          <span className="flex size-8 items-center justify-center rounded-lg bg-accent text-accent-fg">
            <Sparkles className="size-4" />
          </span>
          <span className="flex-1 text-sm font-semibold text-fg">Buddy</span>
          <IconButton label="New chat" onClick={() => onNewChat(null)}>
            <Plus className="size-[18px]" />
          </IconButton>
          <IconButton label="Close sidebar" className="lg:hidden" onClick={onClose}>
            <X className="size-[18px]" />
          </IconButton>
        </header>

        <div className="flex-1 space-y-4 overflow-y-auto px-3 pb-3">
          <section>
            <div className="flex items-center justify-between px-1 pb-1">
              <h2 className="text-[11px] font-semibold uppercase tracking-wider text-fg-subtle">
                Projects
              </h2>
              <IconButton label="New project" size="sm" onClick={onCreateProject}>
                <FolderPlus className="size-3.5" />
              </IconButton>
            </div>

            {projects.length === 0 ? (
              <p className="px-1 py-1 text-xs text-fg-subtle">
                Group related chats into a project.
              </p>
            ) : (
              <ul className="space-y-0.5">
                {projects.map((project) => {
                  const projectChats = chatsByProject.get(project.id) ?? [];
                  const isExpanded = expanded[project.id] ?? false;

                  return (
                    <li key={project.id}>
                      <div className="group flex items-center rounded-lg transition-colors hover:bg-surface-hover">
                        <button
                          type="button"
                          onClick={() =>
                            setExpanded((current) => ({
                              ...current,
                              [project.id]: !isExpanded,
                            }))
                          }
                          aria-expanded={isExpanded}
                          className="flex min-w-0 flex-1 items-center gap-1.5 px-1.5 py-2 text-left"
                        >
                          <ChevronRight
                            className={cn(
                              "size-3.5 shrink-0 text-fg-subtle transition-transform",
                              isExpanded && "rotate-90",
                            )}
                          />
                          <span className="truncate text-sm text-fg-muted group-hover:text-fg">
                            {project.name}
                          </span>
                          <span className="ml-auto pl-1 text-[11px] text-fg-subtle">
                            {projectChats.length || ""}
                          </span>
                        </button>

                        <div className="flex items-center gap-0.5 pr-1 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
                          <button
                            type="button"
                            onClick={() => {
                              setExpanded((current) => ({ ...current, [project.id]: true }));
                              onNewChat(project.id);
                            }}
                            aria-label={`New chat in ${project.name}`}
                            className="rounded p-1 text-fg-subtle transition-colors hover:text-fg"
                          >
                            <Plus className="size-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => onDeleteProject(project.id)}
                            aria-label={`Delete ${project.name}`}
                            className="rounded p-1 text-fg-subtle transition-colors hover:text-danger"
                          >
                            <Trash2 className="size-3.5" />
                          </button>
                        </div>
                      </div>

                      {isExpanded && (
                        <ul className="mt-0.5 space-y-0.5 border-l border-line pl-2 ml-3">
                          {projectChats.length === 0 ? (
                            <li className="px-2 py-1.5 text-xs text-fg-subtle">
                              No chats yet.
                            </li>
                          ) : (
                            projectChats.map((chat) => (
                              <li key={chat.id}>
                                <ChatListItem
                                  chat={chat}
                                  isActive={chat.id === activeChatId}
                                  onSelect={() => onSelectChat(chat.id)}
                                  onRename={(title) => onRenameChat(chat.id, title)}
                                  onDelete={() => onDeleteChat(chat.id)}
                                />
                              </li>
                            ))
                          )}
                        </ul>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          {recentGroups.map((group) => (
            <section key={group.label}>
              <h2 className="px-1 pb-1 text-[11px] font-semibold uppercase tracking-wider text-fg-subtle">
                {group.label}
              </h2>
              <ul className="space-y-0.5">
                {group.chats.map((chat) => (
                  <li key={chat.id}>
                    <ChatListItem
                      chat={chat}
                      isActive={chat.id === activeChatId}
                      onSelect={() => onSelectChat(chat.id)}
                      onRename={(title) => onRenameChat(chat.id, title)}
                      onDelete={() => onDeleteChat(chat.id)}
                    />
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>

        <footer className="border-t border-line p-2">
          <div className="flex items-center gap-2 rounded-xl px-1 py-1">
            <button
              type="button"
              onClick={onOpenSettings}
              className="flex min-w-0 flex-1 items-center gap-2.5 rounded-lg p-1.5 text-left transition-colors hover:bg-surface-hover"
            >
              <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-semibold text-accent-fg">
                {initialsOf(user.display_name || user.username)}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-fg">
                  {user.display_name || user.username}
                </span>
                <span className="block truncate text-[11px] text-fg-subtle">
                  View settings
                </span>
              </span>
              <Settings className="size-4 shrink-0 text-fg-subtle" />
            </button>
          </div>

          <div className="mt-1 flex items-center gap-1 px-1">
            <IconButton
              label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
              size="sm"
              onClick={toggle}
            >
              {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
            </IconButton>
            <IconButton label="Sign out" size="sm" onClick={onLogout}>
              <LogOut className="size-4" />
            </IconButton>
          </div>
        </footer>
      </aside>
    </>
  );
}
