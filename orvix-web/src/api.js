import axios from 'axios';

export const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');
export const api = axios.create({ baseURL: API_BASE, timeout: 120000 });

export const unwrap = (response) => response.data?.data ?? response.data;
export const listKnowledgeBases = async () => unwrap(await api.get('/knowledge_base/list_knowledge_bases')) || [];
export const listFiles = async (knowledge_base_name) => unwrap(await api.get('/knowledge_base/list_files', { params: { knowledge_base_name } })) || [];
export const listTools = async () => unwrap(await api.get('/tools')) || {};
export const uploadDocuments = (path, files, fields) => {
  const form = new FormData();
  Object.entries(fields).forEach(([key, value]) => form.append(key, typeof value === 'object' ? JSON.stringify(value) : String(value)));
  [...files].forEach(file => form.append('files', file));
  return api.post(path, form);
};

// The OpenAI-compatible routes stream SSE. fetch is used only here because Axios
// does not expose a browser ReadableStream; all regular API calls use Axios.
export async function streamCompletion(path, body, onChunk) {
  const response = await fetch(`${API_BASE}${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  if (!response.ok || !response.body) throw new Error((await response.text()) || `Request failed (${response.status})`);
  const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split(/\r?\n/); buffer = lines.pop();
    for (const line of lines) {
      if (!line.startsWith('data:')) continue;
      const payload = line.slice(5).trim(); if (!payload || payload === '[DONE]') continue;
      try { onChunk(JSON.parse(payload)); } catch { /* wait for next complete SSE event */ }
    }
  }
}
