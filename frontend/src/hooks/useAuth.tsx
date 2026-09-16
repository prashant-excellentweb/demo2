import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  type ReactNode,
} from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, UNAUTHORIZED_EVENT, api } from "@/lib/api";
import type { User } from "@/types";

const ME_KEY = ["auth", "me"] as const;

interface Credentials {
  username: string;
  password: string;
  displayName?: string;
}

interface AuthValue {
  user: User | null;
  isLoading: boolean;
  login: (credentials: Credentials) => Promise<void>;
  register: (credentials: Credentials) => Promise<void>;
  logout: () => Promise<void>;
  isSubmitting: boolean;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();

  const { data: user, isPending } = useQuery({
    queryKey: ME_KEY,
    queryFn: async () => {
      try {
        return await api.get<User>("/api/auth/me");
      } catch (error) {
        // Not being signed in is an expected state, not a failure to surface.
        if (error instanceof ApiError && error.isUnauthorized) return null;
        throw error;
      }
    },
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    const handleExpiry = () => queryClient.setQueryData(ME_KEY, null);
    window.addEventListener(UNAUTHORIZED_EVENT, handleExpiry);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, handleExpiry);
  }, [queryClient]);

  const loginMutation = useMutation({
    mutationFn: ({ username, password }: Credentials) =>
      api.post<User>("/api/auth/login", { username, password }),
    onSuccess: (authenticated) => {
      queryClient.setQueryData(ME_KEY, authenticated);
    },
  });

  const registerMutation = useMutation({
    mutationFn: ({ username, password, displayName }: Credentials) =>
      api.post<User>("/api/auth/register", {
        username,
        password,
        display_name: displayName || null,
      }),
    onSuccess: (created) => {
      queryClient.setQueryData(ME_KEY, created);
    },
  });

  const logout = useCallback(async () => {
    await api.post<void>("/api/auth/logout");
    // Drop every cached response so the next account never sees this one's data.
    queryClient.clear();
    queryClient.setQueryData(ME_KEY, null);
  }, [queryClient]);

  const value = useMemo<AuthValue>(
    () => ({
      user: user ?? null,
      isLoading: isPending,
      login: async (credentials) => {
        await loginMutation.mutateAsync(credentials);
      },
      register: async (credentials) => {
        await registerMutation.mutateAsync(credentials);
      },
      logout,
      isSubmitting: loginMutation.isPending || registerMutation.isPending,
    }),
    [user, isPending, loginMutation, registerMutation, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>.");
  return context;
}
