import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Attachment, ChatDetail, ChatSummary, Project } from "@/types";

export const chatKeys = {
  list: ["chats", "list"] as const,
  detail: (id: string) => ["chats", "detail", id] as const,
};

export const projectKeys = {
  list: ["projects", "list"] as const,
};

export function useChats() {
  return useQuery({
    queryKey: chatKeys.list,
    queryFn: () => api.get<ChatSummary[]>("/api/chats"),
  });
}

export function useChat(chatId: string | null) {
  return useQuery({
    queryKey: chatKeys.detail(chatId ?? "none"),
    queryFn: () => api.get<ChatDetail>(`/api/chats/${chatId}`),
    enabled: Boolean(chatId),
  });
}

export function useProjects() {
  return useQuery({
    queryKey: projectKeys.list,
    queryFn: () => api.get<Project[]>("/api/projects"),
  });
}

export function useCreateChat() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { projectId?: string | null } = {}) =>
      api.post<ChatDetail>("/api/chats", { project_id: input.projectId ?? null }),
    onSuccess: (chat) => {
      queryClient.setQueryData(chatKeys.detail(chat.id), chat);
      void queryClient.invalidateQueries({ queryKey: chatKeys.list });
    },
  });
}

export function useUpdateChat() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { chatId: string; title?: string; projectId?: string | null }) => {
      // Only keys present in the body are applied, so an omitted `projectId`
      // leaves the chat in its current folder.
      const body: Record<string, unknown> = {};
      if (input.title !== undefined) body.title = input.title;
      if (input.projectId !== undefined) body.project_id = input.projectId;
      return api.patch<ChatDetail>(`/api/chats/${input.chatId}`, body);
    },
    onSuccess: (chat) => {
      queryClient.setQueryData(chatKeys.detail(chat.id), chat);
      void queryClient.invalidateQueries({ queryKey: chatKeys.list });
    },
  });
}

export function useDeleteChat() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (chatId: string) => api.delete<void>(`/api/chats/${chatId}`),
    onSuccess: (_result, chatId) => {
      // Removed locally first so the sidebar responds instantly.
      queryClient.setQueryData<ChatSummary[]>(chatKeys.list, (current) =>
        current?.filter((chat) => chat.id !== chatId),
      );
      queryClient.removeQueries({ queryKey: chatKeys.detail(chatId) });
    },
  });
}

/** Deletes a message and everything after it, backing edit-and-resend. */
export function useRewindChat() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { chatId: string; messageId: string }) =>
      api.delete<void>(`/api/chats/${input.chatId}/messages/${input.messageId}`),
    onSuccess: (_result, input) => {
      void queryClient.invalidateQueries({ queryKey: chatKeys.detail(input.chatId) });
      void queryClient.invalidateQueries({ queryKey: chatKeys.list });
    },
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; description?: string | null }) =>
      api.post<Project>("/api/projects", {
        name: input.name,
        description: input.description ?? null,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: projectKeys.list }),
  });
}

export function useUpdateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { id: string; name: string; description?: string | null }) =>
      api.put<Project>(`/api/projects/${input.id}`, {
        name: input.name,
        description: input.description ?? null,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: projectKeys.list }),
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) => api.delete<void>(`/api/projects/${projectId}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.list });
      // Its chats are moved back to the unfiled list rather than deleted.
      void queryClient.invalidateQueries({ queryKey: chatKeys.list });
    },
  });
}

export function useUploadAttachment() {
  return useMutation({
    mutationFn: (file: File) => api.upload<Attachment>("/api/attachments", file),
  });
}
