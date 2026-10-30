import {
  RecordingPresets,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  useAudioRecorder,
  useAudioRecorderState,
} from 'expo-audio';
import { router, useIsFocused } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { Heart, MapPin, MessageCircle, Phone, RefreshCw, ScanLine, Square } from 'lucide-react-native';
import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Linking, Platform, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { WaveLine } from '@/components/charts';
import { GreenBackdrop, PulseButton, TopBar } from '@/components/chrome';
import { Button } from '@/components/ui';
import { api, type RedFlag, type TriageResult } from '@/lib/api';
import { friendlyTriageError } from '@/lib/format';
import { useApp } from '@/lib/store';
import { colors, font, TAB_CLEARANCE, urgencyInfo } from '@/lib/theme';

const MAPS_URL = 'https://www.google.com/maps/search/?api=1&query=hospitals+near+me';
const MAX_RECORD_MS = 60000;
const SOURCE: Record<string, string> = {
  rules: 'warning-sign rules (code)',
  gemma: 'Gemma 4',
  both: 'warning-sign rules and Gemma 4',
  default: 'a safe default (AI unavailable)',
};

type Phase = 'idle' | 'recording' | 'transcribing' | 'checking';

export default function Symptoms() {
  const { symptom, setSymptom, symptomView, setDraftContext } = useApp();
  const [phase, setPhase] = useState<Phase>('idle');
  const [text, setText] = useState('');
  const [flags, setFlags] = useState<RedFlag[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [heard, setHeard] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [levels, setLevels] = useState<number[]>(() => idleWave(0));
  const [asking, setAsking] = useState(false);
  const cancelled = useRef(false);
  const focused = useIsFocused();

  const recorder = useAudioRecorder({ ...RecordingPresets.HIGH_QUALITY, isMeteringEnabled: true });
  const rec = useAudioRecorderState(recorder, 120);

  useEffect(() => () => {
    cancelled.current = true;
  }, []);

  // Live voice line while recording; a slow idle wave otherwise.
  const stopRef = useRef<() => void>(() => {});
  useEffect(() => {
    if (phase === 'recording') {
      const id = setInterval(() => {
        const st = recorder.getStatus();
        const level = Math.max(0.04, Math.min(1, ((st.metering ?? -60) + 55) / 50));
        setLevels((l) => [...l.slice(-40), 0.5 + (l.length % 2 ? level : -level) * 0.45]);
        if (st.durationMillis > MAX_RECORD_MS) stopRef.current();
      }, 120);
      return () => clearInterval(id);
    }
    let t = 0;
    const id = setInterval(() => setLevels(idleWave((t += 0.25))), 120);
    return () => clearInterval(id);
  }, [phase, recorder]);

  async function startRecording() {
    setError(null);
    try {
      const perm = await requestRecordingPermissionsAsync();
      if (!perm.granted) {
        setError('Microphone permission is off. You can type your symptoms instead.');
        return;
      }
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
      await recorder.prepareToRecordAsync();
      recorder.record();
      setLevels([]);
      setPhase('recording');
    } catch (e) {
      setError(`Could not start recording: ${(e as Error).message}`);
    }
  }

  async function stopRecording() {
    if (phase !== 'recording') return;
    setPhase('transcribing');
    try {
      await recorder.stop();
      await setAudioModeAsync({ allowsRecording: false }).catch(() => {});
      const uri = recorder.uri;
      if (!uri) throw new Error('No recording was saved.');
      const web = Platform.OS === 'web';
      const res = await api.transcribe({ uri, name: web ? 'symptoms.webm' : 'symptoms.m4a', type: web ? 'audio/webm' : 'audio/m4a' });
      if (res.error) setError(res.error);
      if (res.text) {
        setText(res.text);
        setHeard(`Heard in ${res.language === 'hi' ? 'Hindi' : 'English'} in ${res.seconds.toFixed(1)} s. Check the text and fix anything we got wrong.`);
      }
    } catch (e) {
      setError((e as Error).message);
    }
    setPhase('idle');
  }

  useEffect(() => {
    stopRef.current = stopRecording;
  });

  async function check() {
    const t = text.trim();
    if (!t) {
      setError('Record or type your symptoms first.');
      return;
    }
    setError(null);
    setPhase('checking');
    setElapsed(0);
    const started = Date.now();
    try {
      const { job_id, red_flags } = await api.triage(t);
      setFlags(red_flags);
      for (;;) {
        await new Promise((r) => setTimeout(r, 1200));
        if (cancelled.current) return;
        setElapsed(Math.round((Date.now() - started) / 1000));
        const job = await api.job<TriageResult>(job_id);
        if (job.status === 'done' && job.result) {
          setSymptom({ caseId: job.result.case_id, text: job.result.text, triage: job.result.triage });
          break;
        }
        if (job.status === 'error') throw new Error(job.error ?? 'The symptom check failed.');
      }
    } catch (e) {
      setError((e as Error).message);
    }
    setPhase('idle');
  }

  async function askDoctor() {
    if (!symptom) return;
    setAsking(true);
    try {
      const { escalation_id } = await api.askDoctorSymptoms(symptom.caseId);
      router.push(`/chat/${escalation_id}`);
    } catch (e) {
      setError((e as Error).message);
    }
    setAsking(false);
  }

  function newCheck() {
    setSymptom(null);
    setText('');
    setFlags([]);
    setHeard(null);
    setError(null);
  }

  const busy = phase === 'transcribing' || phase === 'checking';
  const seconds = Math.floor(rec.durationMillis / 1000);
  const pill = phase === 'recording' ? `0:${String(seconds).padStart(2, '0')}` : phase === 'transcribing' ? 'Transcribing…' : phase === 'checking' ? `Checking · ${elapsed}s` : 'Tap to talk';

  return (
    <View style={{ flex: 1 }}>
      {focused ? <StatusBar style="light" /> : null}
      <GreenBackdrop />
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={{ paddingBottom: TAB_CLEARANCE }} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
          <TopBar glass />
          {symptom && phase === 'idle' ? (
            <Result
              data={symptom}
              hasChat={!!symptomView?.escalations.length}
              chatId={symptomView?.escalations[symptomView.escalations.length - 1]?.id}
              asking={asking}
              error={error}
              onAsk={askDoctor}
              onUseAsContext={() => {
                setDraftContext(`${symptom.text} ${symptom.triage.gemma.summary_for_context ?? ''}`.trim());
                router.push('/scan');
              }}
              onNew={newCheck}
            />
          ) : (
            <View style={{ paddingHorizontal: 20 }}>
              <View style={{ alignItems: 'center', marginTop: 18 }}>
                {phase === 'recording' ? (
                  <View style={{ flexDirection: 'row', alignItems: 'flex-end' }}>
                    <Text style={styles.huge}>{String(seconds).padStart(2, '0')}</Text>
                    <Text style={styles.hugeUnit}>sec</Text>
                  </View>
                ) : (
                  <Text style={[styles.huge, { fontSize: 40, lineHeight: 46, textAlign: 'center' }]}>How are you{'\n'}feeling today?</Text>
                )}
                <Text style={styles.lead}>
                  {phase === 'recording'
                    ? 'Listening… describe what you feel and for how long, then tap again to stop'
                    : 'Tap the heart and describe your symptoms in English or Hindi'}
                </Text>
              </View>

              <View style={{ alignItems: 'center', marginTop: 0 }}>
                <PulseButton
                  active={phase === 'recording'}
                  label={phase === 'recording' ? 'Stop recording' : 'Start recording'}
                  onPress={phase === 'recording' ? stopRecording : busy ? () => {} : startRecording}
                >
                  {phase === 'recording' ? (
                    <Square size={24} color={colors.heart} fill={colors.heart} />
                  ) : busy ? (
                    <ActivityIndicator color={colors.heart} />
                  ) : (
                    <Heart size={28} color={colors.heart} fill={colors.heart} />
                  )}
                </PulseButton>
                <View style={styles.timePill}>
                  <Text style={styles.timePillText}>{pill}</Text>
                </View>
              </View>
              <View style={{ marginHorizontal: -20 }}>
                <WaveLine values={levels} height={130} label={phase === 'recording' ? pill : undefined} />
              </View>

              {flags.length ? (
                <View style={[styles.glass, { borderColor: 'rgba(255,190,200,0.8)', backgroundColor: 'rgba(176,52,76,0.35)' }]}>
                  <Text style={styles.glassTitle}>Warning signs found</Text>
                  {flags.map((f) => <Text key={f.id} style={styles.glassBody}>• {f.message}</Text>)}
                </View>
              ) : null}

              <View style={[styles.glass, { marginTop: 14 }]}>
                <TextInput
                  value={text}
                  onChangeText={setText}
                  placeholder="Or type here, e.g. stomach pain and mild fever since yesterday"
                  placeholderTextColor="rgba(255,255,255,0.7)"
                  multiline
                  style={styles.input}
                  editable={!busy && phase !== 'recording'}
                />
              </View>
              {heard ? <Text style={styles.note}>{heard}</Text> : null}
              {error ? <Text style={[styles.note, { color: '#FFE3E8', fontFamily: font.semibold }]}>{error}</Text> : null}
              <Button
                title={phase === 'checking' ? `Gemma 4 is thinking… ${elapsed}s` : 'Check my symptoms'}
                tone="white"
                onPress={check}
                loading={phase === 'checking'}
                disabled={busy || phase === 'recording'}
                style={{ marginTop: 14 }}
              />
              <Text style={styles.footer}>
                Possible causes only, never a diagnosis. In an emergency call 108 (ambulance) or 112. Mental health support:
                Tele-MANAS 14416 (free, 24x7).
              </Text>
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

function idleWave(phase: number): number[] {
  return Array.from({ length: 24 }, (_, i) => 0.5 + 0.18 * Math.sin(i * 0.55 + phase) + 0.07 * Math.sin(i * 1.7 - phase));
}

function Result({ data, hasChat, chatId, asking, error, onAsk, onUseAsContext, onNew }: {
  data: { text: string; triage: TriageResult['triage'] };
  hasChat: boolean;
  chatId?: number;
  asking: boolean;
  error: string | null;
  onAsk: () => void;
  onUseAsContext: () => void;
  onNew: () => void;
}) {
  const t = data.triage;
  const info = urgencyInfo[t.urgency] ?? urgencyInfo.SEE_DOCTOR;
  const serious = t.urgency === 'URGENT' || t.urgency === 'EMERGENCY';
  const g = t.gemma;
  return (
    <View style={{ paddingHorizontal: 20 }}>
      <View style={{ alignItems: 'center', marginTop: 28 }}>
        <View style={[styles.urgencyChip, { backgroundColor: info.dot }]} />
        <Text style={[styles.huge, { fontSize: 58, lineHeight: 66, textAlign: 'center' }]}>{info.title}</Text>
        <Text style={[styles.lead, { fontFamily: font.medium, fontSize: 18 }]}>{info.action}</Text>
        <Text style={[styles.note, { textAlign: 'center' }]}>Urgency from {SOURCE[t.urgency_source] ?? t.urgency_source}</Text>
      </View>

      <View style={{ gap: 10, marginTop: 18 }}>
        {t.urgency === 'EMERGENCY' ? <Button title="Call 108 (ambulance)" icon={Phone} tone="white" onPress={() => Linking.openURL('tel:108')} /> : null}
        <Button title="Hospitals near me" icon={MapPin} tone={serious && t.urgency !== 'EMERGENCY' ? 'white' : 'glass'} onPress={() => Linking.openURL(MAPS_URL)} />
      </View>

      {t.red_flags.length ? (
        <Glass title="Warning signs">
          {t.red_flags.map((f) => <Text key={f.id} style={styles.glassBody}>• {f.message}</Text>)}
        </Glass>
      ) : null}

      <Glass title="You said">
        <Text style={[styles.glassBody, { fontStyle: 'italic' }]}>“{data.text}”</Text>
      </Glass>

      <Glass title="Possible causes">
        {g.possible_causes.length ? g.possible_causes.map((c, i) => (
          <View key={i} style={{ marginTop: i ? 10 : 2 }}>
            <Text style={[styles.glassBody, { fontFamily: font.semibold }]}>{c.name} <Text style={styles.small}>· possible, not a diagnosis</Text></Text>
            {c.why ? <Text style={styles.glassBody}>{c.why}</Text> : null}
          </View>
        )) : <Text style={styles.glassBody}>Not available. Please talk to a doctor.</Text>}
      </Glass>

      {g.self_care.length ? (
        <Glass title="What you can do now">
          {g.self_care.map((s, i) => <Text key={i} style={styles.glassBody}>• {s}</Text>)}
        </Glass>
      ) : null}

      {g.questions_for_doctor.length ? (
        <Glass title="Questions to ask your doctor">
          {g.questions_for_doctor.map((q, i) => <Text key={i} style={styles.glassBody}>• {q}</Text>)}
        </Glass>
      ) : null}

      {t.error ? <Text style={styles.note}>Note: {friendlyTriageError(t.error)}</Text> : null}
      {error ? <Text style={[styles.note, { color: '#FFE3E8', fontFamily: font.semibold }]}>{error}</Text> : null}

      <View style={{ gap: 10, marginTop: 16 }}>
        {hasChat && chatId ? (
          <Button title="Open doctor chat" icon={MessageCircle} tone="white" onPress={() => router.push(`/chat/${chatId}`)} />
        ) : (
          <Button title="Ask a doctor" icon={MessageCircle} tone="white" onPress={onAsk} loading={asking} />
        )}
        <Button title="Use as my prescription context" icon={ScanLine} tone="glass" onPress={onUseAsContext} />
        <Button title="New symptom check" icon={RefreshCw} tone="glass" onPress={onNew} />
      </View>
      <Text style={styles.footer}>
        AushNexa suggests possible causes only. It is not a diagnosis and not a substitute for a doctor. Warning-sign rules
        run in code first; Gemma 4 can raise the urgency, but code never lowers it.
      </Text>
    </View>
  );
}

function Glass({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={[styles.glass, { marginTop: 12 }]}>
      <Text style={styles.glassTitle}>{title}</Text>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  huge: { fontFamily: font.light, fontSize: 92, lineHeight: 100, color: colors.white, letterSpacing: -2 },
  hugeUnit: { fontFamily: font.regular, fontSize: 20, color: colors.white, marginLeft: 6, marginBottom: 18 },
  lead: { fontFamily: font.regular, fontSize: 17, lineHeight: 24, color: 'rgba(255,255,255,0.92)', textAlign: 'center', marginTop: 8, maxWidth: 320 },
  timePill: { marginTop: -6, paddingHorizontal: 16, height: 34, borderRadius: 17, borderWidth: 1, borderColor: 'rgba(255,255,255,0.6)', backgroundColor: 'rgba(255,255,255,0.14)', justifyContent: 'center' },
  timePillText: { fontFamily: font.medium, fontSize: 15, color: colors.white },
  glass: { backgroundColor: 'rgba(255,255,255,0.14)', borderRadius: 24, borderWidth: 1, borderColor: 'rgba(255,255,255,0.4)', padding: 16 },
  glassTitle: { fontFamily: font.semibold, fontSize: 13, letterSpacing: 0.6, textTransform: 'uppercase', color: 'rgba(255,255,255,0.8)', marginBottom: 6 },
  glassBody: { fontFamily: font.regular, fontSize: 15.5, lineHeight: 22, color: colors.white },
  small: { fontFamily: font.regular, fontSize: 13, color: 'rgba(255,255,255,0.75)' },
  input: { minHeight: 74, fontFamily: font.regular, fontSize: 16, lineHeight: 22, color: colors.white, textAlignVertical: 'top' },
  note: { fontFamily: font.regular, fontSize: 13.5, lineHeight: 19, color: 'rgba(255,255,255,0.85)', marginTop: 10 },
  footer: { fontFamily: font.regular, fontSize: 12.5, lineHeight: 18, color: 'rgba(255,255,255,0.75)', textAlign: 'center', marginTop: 18 },
  urgencyChip: { width: 14, height: 14, borderRadius: 7, borderWidth: 2, borderColor: colors.white, marginBottom: 8 },
});
