import AsyncStorage from '@react-native-async-storage/async-storage';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';

import { api, defaultApiUrl, setApiBase, type CaseView, type EscalationSummary, type Triage } from './api';

const STORAGE_KEY = 'aushnexa:v1';
const POLL_MS = 4000;

export type Profile = { name: string; conditions: string; allergies: string };
export type SymptomState = { caseId: number; text: string; triage: Triage } | null;

type Persisted = {
  apiUrl: string;
  profile: Profile;
  caseId: number | null;
  symptom: SymptomState;
  taken: Record<string, boolean>;
  lastSeen: number;
};

type AppState = Persisted & {
  ready: boolean;
  caseView: CaseView | null;
  caseError: string | null;
  symptomView: CaseView | null;
  /** Doctor chats for the current prescription and symptom check, newest activity first. */
  inbox: EscalationSummary[];
  unread: number;
  draftContext: string | null;
  setApiUrl: (url: string) => void;
  setProfile: (p: Profile) => void;
  openCase: (id: number) => Promise<void>;
  setCaseView: (v: CaseView) => void;
  refreshCase: () => Promise<void>;
  setSymptom: (s: SymptomState) => void;
  refreshSymptom: () => Promise<void>;
  setDraftContext: (s: string | null) => void;
  toggleTaken: (key: string) => void;
  markSeen: () => void;
  resetAll: () => void;
};

const initial: Persisted = {
  apiUrl: defaultApiUrl(),
  profile: { name: '', conditions: '', allergies: '' },
  caseId: null,
  symptom: null,
  taken: {},
  lastSeen: 0,
};

const Ctx = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [state, setState] = useState<Persisted>(initial);
  const [caseView, setCaseViewState] = useState<CaseView | null>(null);
  const [caseError, setCaseError] = useState<string | null>(null);
  const [symptomView, setSymptomView] = useState<CaseView | null>(null);
  const [draftContext, setDraftContext] = useState<string | null>(null);
  const stateRef = useRef(state);
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const update = useCallback((patch: Partial<Persisted> | ((s: Persisted) => Partial<Persisted>)) => {
    setState((s) => {
      const next = { ...s, ...(typeof patch === 'function' ? patch(s) : patch) };
      AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next)).catch(() => {});
      return next;
    });
  }, []);

  const loadCase = useCallback(async (id: number | null) => {
    if (id === null) return;
    try {
      setCaseViewState(await api.caseView(id));
      setCaseError(null);
    } catch (e) {
      setCaseError((e as Error).message);
    }
  }, []);

  const loadSymptom = useCallback(async (id: number | undefined) => {
    if (id === undefined) return;
    try {
      setSymptomView(await api.caseView(id));
    } catch {
      // the symptom result itself is stored locally; the chat list can wait for the next poll
    }
  }, []);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY)
      .then((raw) => {
        const saved = raw ? (JSON.parse(raw) as Partial<Persisted>) : {};
        const next = { ...initial, ...saved, profile: { ...initial.profile, ...saved.profile } };
        setApiBase(next.apiUrl);
        setState(next);
        loadCase(next.caseId);
        loadSymptom(next.symptom?.caseId);
      })
      .catch(() => {})
      .finally(() => setReady(true));
  }, [loadCase, loadSymptom]);

  // Keep doctor replies flowing in while any chat is open.
  const hasOpen = [caseView, symptomView].some((v) => v?.escalations.some((e) => e.status === 'open'));
  useEffect(() => {
    if (!hasOpen) return;
    const t = setInterval(() => {
      loadCase(stateRef.current.caseId);
      loadSymptom(stateRef.current.symptom?.caseId);
    }, POLL_MS);
    return () => clearInterval(t);
  }, [hasOpen, loadCase, loadSymptom]);

  const inbox = useMemo(() => {
    const all = [...(caseView?.escalations ?? []), ...(symptomView?.escalations ?? [])];
    const at = (e: EscalationSummary) => e.last_message?.ts ?? e.created_at;
    return all.sort((a, b) => at(b) - at(a));
  }, [caseView, symptomView]);
  const unread = inbox.filter((e) => e.last_message?.sender === 'doctor' && e.last_message.ts > state.lastSeen).length;

  // Stable identities, so screens can list these in effect dependencies without re-running every render.
  const actions = useMemo(
    () => ({
      setDraftContext,
      setApiUrl: (url: string) => {
        setApiBase(url);
        update({ apiUrl: url.replace(/\/$/, '') });
      },
      setProfile: (profile: Profile) => update({ profile }),
      openCase: async (id: number) => {
        update({ caseId: id });
        await loadCase(id);
      },
      setCaseView: (v: CaseView) => {
        setCaseViewState(v);
        update({ caseId: v.id });
      },
      refreshCase: () => loadCase(stateRef.current.caseId),
      setSymptom: (symptom: SymptomState) => {
        update({ symptom });
        setSymptomView(null);
        loadSymptom(symptom?.caseId);
      },
      refreshSymptom: () => loadSymptom(stateRef.current.symptom?.caseId),
      toggleTaken: (key: string) =>
        update((s) => {
          const taken = { ...s.taken };
          if (taken[key]) delete taken[key];
          else taken[key] = true;
          return { taken };
        }),
      markSeen: () => update({ lastSeen: Date.now() / 1000 }),
      resetAll: () => {
        update((s) => ({ ...initial, apiUrl: s.apiUrl }));
        setCaseViewState(null);
        setSymptomView(null);
      },
    }),
    [update, loadCase, loadSymptom],
  );

  const value: AppState = { ...state, ready, caseView, caseError, symptomView, inbox, unread, draftContext, ...actions };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp(): AppState {
  const v = useContext(Ctx);
  if (!v) throw new Error('useApp must be used inside <AppProvider>');
  return v;
}
