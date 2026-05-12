/** API-клиент для backend */
import type { ContestInfo, RankingResponse } from '@/types';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000';

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export async function fetchContestInfo(): Promise<ContestInfo> {
  return apiFetch<ContestInfo>('/api/contest');
}

export async function fetchRanking(category: 'day' | 'night'): Promise<RankingResponse> {
  return apiFetch<RankingResponse>(`/api/ranking/${category}`);
}

export function buildWsUrl(): string {
  const tg = window.Telegram?.WebApp;
  const token = tg?.initData
    ? btoa(tg.initData).replace(/=/g, '').slice(0, 16)
    : 'demo';
  const wsBase = import.meta.env.VITE_WS_URL ?? 'ws://127.0.0.1:8000';
  return `${wsBase}?token=${encodeURIComponent(token)}`;
}

export function getTgUser() {
  return window.Telegram?.WebApp?.initDataUnsafe?.user;
}