import axios, { AxiosInstance } from "axios";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

function getCookie(name: string): string | null {
  // Guard against SSR — document is not available server-side
  if (typeof document === "undefined") return null;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(";").shift() || null;
  return null;
}

export function getClient(): AxiosInstance {
  const client = axios.create({
    baseURL: BACKEND_URL,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    withCredentials: true,
  });

  client.interceptors.request.use((config) => {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) {
      config.headers["X-CSRFToken"] = csrfToken;
    }
    return config;
  });

  client.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 403) {
        console.error("CSRF validation failed:", error);
      }
      return Promise.reject(error);
    }
  );

  return client;
}

// In-flight request deduplication — concurrent GET calls to the same URL
// share one HTTP request instead of firing N parallel requests.
const inflight = new Map<string, Promise<unknown>>();

export async function get<T>(url: string): Promise<T> {
  if (inflight.has(url)) {
    return inflight.get(url) as Promise<T>;
  }
  const promise = getClient()
    .get<T>(url)
    .then((res) => res.data)
    .finally(() => inflight.delete(url));
  inflight.set(url, promise as Promise<unknown>);
  return promise;
}

export async function post<T>(url: string, data: unknown): Promise<T> {
  try {
    const client = getClient();
    const response = await client.post<T>(url, data);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.error || "Failed to submit data");
    }
    throw error;
  }
}

export async function fetchCsrfToken(): Promise<void> {
  try {
    await get("/api/csrf-token/");
  } catch (error) {
    console.error("Error fetching CSRF token:", error);
  }
}
