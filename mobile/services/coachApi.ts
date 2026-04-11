import { API_BASE_URL } from '../constants/config';

export type CoachEvent = { text: string };

/** Parse /api/coach/brief SSE — looks for event:brief, field raw_text */
async function fetchBriefSSE(patientId: string): Promise<string> {
  const res = await fetch(`${API_BASE_URL}/api/coach/brief`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ patient_id: patientId }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);

  const raw = await res.text();
  let result = '';
  let currentEvent = '';

  for (const line of raw.split('\n')) {
    if (line.startsWith('event: ')) {
      currentEvent = line.slice(7).trim();
    } else if (line.startsWith('data: ') && currentEvent === 'brief') {
      try {
        const parsed = JSON.parse(line.slice(6).trim());
        if (parsed.raw_text) result = parsed.raw_text;
      } catch {}
    } else if (line === '') {
      currentEvent = '';
    }
  }
  return result;
}

/** Parse /api/checkup/respond SSE — accumulates event:text chunks */
async function fetchRespondSSE(sessionId: string, transcript: string): Promise<string> {
  const res = await fetch(`${API_BASE_URL}/api/checkup/respond`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, transcript }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);

  const raw = await res.text();
  let result = '';
  let currentEvent = '';

  for (const line of raw.split('\n')) {
    if (line.startsWith('event: ')) {
      currentEvent = line.slice(7).trim();
    } else if (line.startsWith('data: ') && currentEvent === 'text') {
      try {
        const parsed = JSON.parse(line.slice(6).trim());
        if (parsed.chunk) result += parsed.chunk;
      } catch {}
    } else if (line === '') {
      currentEvent = '';
    }
  }
  return result.trim();
}

export const coachApi = {
  async *brief(patientId: string): AsyncGenerator<CoachEvent> {
    const text = await fetchBriefSSE(patientId);
    if (text) yield { text };
  },

  async startSession(patientId: string): Promise<string> {
    const res = await fetch(`${API_BASE_URL}/api/checkup/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ patient_id: patientId }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const { session_id } = await res.json();
    return session_id;
  },

  async *reply(sessionId: string, transcript: string): AsyncGenerator<CoachEvent> {
    const text = await fetchRespondSSE(sessionId, transcript);
    if (text) yield { text };
  },

  async dashboard(patientId: string) {
    const res = await fetch(`${API_BASE_URL}/api/dashboard/${patientId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },
};
