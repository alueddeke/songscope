import axios, { AxiosInstance } from "axios";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

function getCookie(name: string): string | null {
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

  // Add request interceptor to include CSRF token
  client.interceptors.request.use((config) => {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) {
      config.headers["X-CSRFToken"] = csrfToken;
    }
    return config;
  });

  // Add response interceptor to handle errors
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

export async function get<T>(url: string): Promise<T> {
  const client = getClient();
  const response = await client.get<T>(url);
  return response.data;
}

<<<<<<< HEAD
export async function post<T>(url: string, data: any): Promise<T> {
  try {
    const client = getClient();
    const response = await client.post<T>(url, data);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      console.error("Axios error:", error.response?.data);
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
=======
export async function post<T>(url: string, body: any): Promise<T> {
  const client = getClient();
  const response = await client.post<T>(url, body);
  return response.data;
}
>>>>>>> development
