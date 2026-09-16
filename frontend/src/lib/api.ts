export const UNAUTHORIZED_EVENT = "buddy:unauthorized";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Non-JSON error body (a proxy error page, for example).
  }
  return `Request failed with status ${response.status}.`;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    // The session lives in an httpOnly cookie, so every call must carry it.
    credentials: "include",
    ...init,
  });

  if (!response.ok) {
    if (response.status === 401) {
      // Lets the auth provider drop stale state from anywhere in the app when
      // a session expires mid-session, instead of leaving a broken shell.
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    }
    throw new ApiError(response.status, await readErrorMessage(response));
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function jsonRequest<T>(method: string, path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => jsonRequest<T>("POST", path, body),
  patch: <T>(path: string, body?: unknown) => jsonRequest<T>("PATCH", path, body),
  put: <T>(path: string, body?: unknown) => jsonRequest<T>("PUT", path, body),
  delete: <T>(path: string) => jsonRequest<T>("DELETE", path),

  upload: <T>(path: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    // No Content-Type header: the browser must set the multipart boundary.
    return request<T>(path, { method: "POST", body: form });
  },
};

export const attachmentUrl = (id: string) => `/api/attachments/${id}/content`;
