import axios from "axios";
import type { AuthResponse, ChatMessage, ChatResponse, DocumentItem, InsightResponse } from "@/types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api";

export const api = axios.create({
  baseURL: API_URL
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("insuramind_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (typeof window === "undefined" || error.response?.status !== 401 || original?._retry) {
      return Promise.reject(error);
    }
    const refreshToken = localStorage.getItem("insuramind_refresh_token");
    if (!refreshToken) {
      return Promise.reject(error);
    }
    original._retry = true;
    try {
      const { data } = await axios.post<AuthResponse>(`${API_URL}/auth/refresh`, { refreshToken });
      saveAuth(data);
      original.headers.Authorization = `Bearer ${data.accessToken}`;
      return api(original);
    } catch (refreshError) {
      logout();
      return Promise.reject(refreshError);
    }
  }
);

export async function signup(payload: { fullName: string; email: string; password: string }) {
  const { data } = await api.post<AuthResponse>("/auth/signup", payload);
  saveAuth(data);
  return data;
}

export async function login(payload: { email: string; password: string }) {
  const { data } = await api.post<AuthResponse>("/auth/login", payload);
  saveAuth(data);
  return data;
}

export function saveAuth(auth: AuthResponse) {
  localStorage.setItem("insuramind_token", auth.accessToken);
  localStorage.setItem("insuramind_refresh_token", auth.refreshToken);
  localStorage.setItem("insuramind_user", JSON.stringify(auth));
}

export function logout() {
  localStorage.removeItem("insuramind_token");
  localStorage.removeItem("insuramind_refresh_token");
  localStorage.removeItem("insuramind_user");
  window.location.href = "/login";
}

export function currentUser(): AuthResponse | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("insuramind_user");
  return raw ? JSON.parse(raw) : null;
}

export async function listDocuments() {
  const { data } = await api.get<DocumentItem[]>("/documents");
  return data;
}

export async function uploadDocument(file: File) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<DocumentItem>("/documents", form);
  return data;
}

export async function getDocument(id: string) {
  const { data } = await api.get<DocumentItem>(`/documents/${id}`);
  return data;
}

export async function getFileUrl(id: string) {
  const { data } = await api.get<{ url: string; expiresInSeconds: number }>(`/documents/${id}/file-url`);
  return data;
}

export async function getDocumentPreviewBlob(id: string) {
  const { data } = await api.get<Blob>(`/documents/${id}/preview`, { responseType: "blob" });
  return data;
}

export async function getInsights(id: string) {
  const { data } = await api.get<InsightResponse>(`/documents/${id}/insights`);
  return data;
}

export async function getMessages(id: string) {
  const { data } = await api.get<ChatMessage[]>(`/chat/documents/${id}/messages`);
  return data;
}

export async function askDocument(id: string, question: string) {
  const { data } = await api.post<ChatResponse>(`/chat/documents/${id}/query`, { question });
  return data;
}
