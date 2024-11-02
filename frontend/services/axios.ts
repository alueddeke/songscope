import axios, { AxiosInstance } from "axios";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export function getClient(): AxiosInstance {
  const client = axios.create({
    baseURL: BACKEND_URL,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    withCredentials: true,
  });

  return client;
}

export async function get<T>(url: string): Promise<T> {
  const client = getClient();
  const response = await client.get<T>(url);
  return response.data;
}

export async function post<T>(url: string, body: any): Promise<T> {
  const client = getClient();
  const response = await client.post<T>(url, body);
  return response.data;
}