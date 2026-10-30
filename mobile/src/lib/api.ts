import Constants from 'expo-constants';
import { Platform } from 'react-native';

// ---------------------------------------------------------------- types (mirror backend/api.py)

export type Band = 'HIGH' | 'MEDIUM' | 'LOW';
export type Severity = 'HIGH' | 'REVIEW' | 'INFO';
export type Urgency = 'SELF_CARE' | 'SEE_DOCTOR' | 'URGENT' | 'EMERGENCY';
export type MedStatus = 'auto' | 'needs_confirmation' | 'confirmed_by_doctor' | 'picked_by_patient';

export type Salt = { salt: string; strength: string };
export type Candidate = {
  name: string;
  base_name?: string;
  salts: Salt[];
  salt_key?: string;
  price: number | null;
  pack: string | null;
  desc?: string;
  score?: number;
};
export type Read = {
  raw_text: string;
  brand_or_drug: string;
  form: string | null;
  strength: string | null;
  dose_and_frequency: string | null;
  duration: string | null;
  unsure: boolean;
};
export type Confidence = {
  value: number;
  band: Band;
  breakdown: Record<string, number>;
  reasons: string[];
  lasa_rival: Candidate | null;
  written_similarity?: number;
};
export type Fit = { fits: 'yes' | 'no' | 'unclear' | null; reason: string };
export type Med = {
  index: number;
  read: Read;
  candidates: Candidate[];
  fits: Record<string, Fit>;
  selected: Candidate | null;
  status: MedStatus;
  confidence: Confidence | null;
  resolution?: { name?: string; free_text?: string; by: string };
};
export type Resolved = {
  index: number;
  label: string | null;
  salts: Salt[];
  freq: string;
  price: number | null;
  pack: string | null;
  status: MedStatus;
};
export type SafetyAlert = { severity: Severity; type: string; title: string; detail: string; meds: number[] };
export type StripResult = {
  status: 'MATCH' | 'MISMATCH' | 'NOT_PRESCRIBED' | 'ERROR';
  detail: string;
  med_index: number | null;
};
export type Generic = { generic_name: string; price: number; pack: string; units: number };
export type JanAushadhi = {
  index: number;
  brand: string | null;
  brand_price: number | null;
  brand_pack: string | null;
  generic: Generic | null;
};
export type ScheduleItem = { index: number; label: string | null; freq: string; slots: string[] };
export type TraceStep = {
  step: string;
  model: string;
  backend: string;
  seconds: number;
  cache_hit: boolean;
  error: string | null;
};
export type Case = {
  context: string;
  allergies: string[];
  input_mode: 'typed' | 'photo';
  meds: Med[];
  errors: string[];
  _trace: TraceStep[];
  strip_resolved: { label: string | null; strength: string | null } | null;
  hindi_summary: string;
  resolved: Resolved[];
  alerts: SafetyAlert[];
  strip: StripResult | null;
  jan_aushadhi: JanAushadhi[];
  savings: number;
  schedule: ScheduleItem[];
  elapsed?: number;
  rechecked?: boolean;
};
export type Message = { id: number; escalation_id: number; sender: 'patient' | 'doctor' | 'system'; text: string; ts: number };
export type EscalationSummary = {
  id: number;
  kind: 'medicine' | 'symptom';
  case_id: number | null;
  med_index: number;
  raw_text: string;
  status: 'open' | 'resolved';
  resolution: { name?: string; free_text?: string; answered?: boolean } | null;
  created_at: number;
  message_count: number;
  last_message: Message | null;
};
export type CaseView = {
  id: number;
  created_at: number;
  kind: 'prescription' | 'symptom_check';
  image_url: string | null;
  case: Case;
  escalations: EscalationSummary[];
};
export type JobStep = { label: string; at: number };
export type Job<T> = {
  id: string;
  kind: string;
  status: 'running' | 'done' | 'error';
  steps: JobStep[];
  elapsed: number;
  result: T | null;
  error: string | null;
};
export type RedFlag = { id: string; level: Urgency; message: string; matched: string[] };
export type Triage = {
  red_flags: RedFlag[];
  urgency: Urgency;
  urgency_source: 'rules' | 'gemma' | 'both' | 'default';
  gemma: {
    possible_causes: { name: string; why: string }[];
    self_care: string[];
    urgency: Urgency | null;
    questions_for_doctor: string[];
    summary_for_context: string;
  };
  error?: string;
  _trace: TraceStep[];
};
export type TriageResult = { case_id: number; text: string; triage: Triage };
export type EscalationDetail = EscalationSummary & {
  messages: Message[];
  context: string;
  allergies: string;
  candidates: Candidate[];
  image_url: string | null;
  med: Med | null;
  triage: Pick<Triage, 'urgency' | 'urgency_source' | 'red_flags' | 'gemma'> | null;
};
export type Settings = {
  backend: 'gemini' | 'ollama';
  model: string;
  fallback_to_local: boolean;
  gemini_key_set: boolean;
  options: { id: 'gemini' | 'ollama'; label: string; model: string }[];
};
export type Demo = { context: string; allergies: string; typed_rx: string; prescription_url: string; strip_url: string };
export type TestLab = { results: { case: string; expected: string; got: string; passed: boolean }[]; passed: number; total: number };
export type Transcript = { text: string; language: string | null; seconds: number; error: string | null };

// ---------------------------------------------------------------- base URL

/** Where the API is, with no setup:
 *  - website build: the backend serves the page, so the API is on the same origin (also behind a tunnel);
 *  - web in development: the Expo dev server serves the page and the backend runs beside it on port 8000;
 *  - Expo Go: port 8000 on the dev server's LAN address, so a phone on the same Wi-Fi finds it. */
export function defaultApiUrl(): string {
  const fromEnv = process.env.EXPO_PUBLIC_API_URL;
  if (fromEnv) return fromEnv.replace(/\/$/, '');
  if (Platform.OS === 'web' && typeof window !== 'undefined') {
    return __DEV__ ? `${window.location.protocol}//${window.location.hostname}:8000` : window.location.origin;
  }
  const hostUri = Constants.expoConfig?.hostUri;
  if (hostUri) return `http://${hostUri.split(':')[0]}:8000`;
  return Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://localhost:8000';
}

let base = defaultApiUrl();

export function setApiBase(url: string) {
  base = url.replace(/\/$/, '');
}

export function apiUrl(path: string): string {
  return path.startsWith('http') ? path : `${base}${path}`;
}

// ---------------------------------------------------------------- requests

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit, timeoutMs = 30000): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(apiUrl(path), { ...init, signal: ctrl.signal });
  } catch {
    throw new ApiError(0, `Can't reach the AushNexa server at ${base}. Check that it is running and that the address in Settings is right.`);
  } finally {
    clearTimeout(timer);
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = body?.detail;
    const msg = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail[0]?.msg : `Request failed (${res.status})`;
    throw new ApiError(res.status, msg || `Request failed (${res.status})`);
  }
  return body as T;
}

const json = (method: string, data?: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: data === undefined ? undefined : JSON.stringify(data),
});

/** A picked file: a local URI on iOS/Android, a blob: or data: URI on the web. */
export type LocalFile = { uri: string; name: string; type: string };

async function appendFile(form: FormData, field: string, file: LocalFile) {
  if (Platform.OS === 'web') {
    const blob = await (await fetch(file.uri)).blob();
    form.append(field, blob, file.name);
  } else {
    // React Native's FormData uploads a { uri, name, type } object straight from disk.
    form.append(field, file as unknown as Blob);
  }
}

export const api = {
  health: () => request<{ ok: boolean; backend: string; model: string }>('/api/health', undefined, 6000),
  settings: () => request<Settings>('/api/settings'),
  setBackend: (backend: Settings['backend']) => request<Settings>('/api/settings', json('PUT', { backend })),
  demo: () => request<Demo>('/api/demo'),
  testlab: () => request<TestLab>('/api/testlab', undefined, 60000),

  async analyze(input: {
    context: string;
    allergies: string;
    rxText?: string;
    rxImage?: LocalFile | null;
    stripImage?: LocalFile | null;
    useDemoImages?: boolean;
  }) {
    const form = new FormData();
    form.append('context', input.context);
    form.append('allergies', input.allergies);
    form.append('rx_text', input.rxText ?? '');
    form.append('use_demo_images', input.useDemoImages ? 'true' : 'false');
    if (input.rxImage) await appendFile(form, 'rx_image', input.rxImage);
    if (input.stripImage) await appendFile(form, 'strip_image', input.stripImage);
    return request<{ job_id: string }>('/api/analyze', { method: 'POST', body: form }, 90000);
  },
  job: <T>(id: string) => request<Job<T>>(`/api/jobs/${id}`),
  caseView: (id: number) => request<CaseView>(`/api/cases/${id}`),
  pick: (caseId: number, medIndex: number, name: string) =>
    request<CaseView>(`/api/cases/${caseId}/meds/${medIndex}/pick`, json('POST', { name })),
  askDoctor: (caseId: number, medIndex: number) =>
    request<{ escalation_id: number; case: CaseView }>(`/api/cases/${caseId}/meds/${medIndex}/ask-doctor`, json('POST')),

  triage: (text: string) => request<{ job_id: string; red_flags: RedFlag[] }>('/api/triage', json('POST', { text })),
  async transcribe(file: LocalFile) {
    const form = new FormData();
    await appendFile(form, 'audio', file);
    return request<Transcript>('/api/transcribe', { method: 'POST', body: form }, 180000);
  },
  askDoctorSymptoms: (caseId: number) => request<{ escalation_id: number }>(`/api/cases/${caseId}/ask-doctor`, json('POST')),

  escalations: (status: 'open' | 'resolved' | 'all' = 'open') =>
    request<EscalationSummary[]>(`/api/escalations?status=${status}`),
  escalation: (id: number) => request<EscalationDetail>(`/api/escalations/${id}`),
  sendMessage: (id: number, sender: 'patient' | 'doctor', text: string) =>
    request<{ messages: Message[] }>(`/api/escalations/${id}/messages`, json('POST', { sender, text })),
  resolve: (id: number, resolution: { name?: string; free_text?: string }) =>
    request<EscalationSummary>(`/api/escalations/${id}/resolve`, json('POST', resolution)),
};
