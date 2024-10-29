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

export const post = async <T>(url: string, data: any): Promise<T> => {
  try {
    const response = await axios.post(url, data, {
      withCredentials: true, //for cookies
      headers: {
        "Content-Type": "application/json",
      },
    });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.error || "Failed to submit data");
    }
    throw error;
  }
};
