import { router, useLocalSearchParams } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { Check, ScanLine } from 'lucide-react-native';
import { useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { GreenBackdrop, PulseButton } from '@/components/chrome';
import { Button } from '@/components/ui';
import { api, type Job } from '@/lib/api';
import { useApp } from '@/lib/store';
import { colors, font } from '@/lib/theme';

export default function Analyzing() {
  const { job: jobId } = useLocalSearchParams<{ job: string }>();
  const { openCase } = useApp();
  const insets = useSafeAreaInsets();
  const [job, setJob] = useState<Job<{ case_id: number }> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    let alive = true;
    const started = Date.now();
    const tick = setInterval(() => setSeconds(Math.floor((Date.now() - started) / 1000)), 500);
    (async () => {
      let misses = 0;
      while (alive) {
        try {
          const j = await api.job<{ case_id: number }>(jobId);
          if (!alive) return;
          setJob(j);
          misses = 0;
          if (j.status === 'done' && j.result) {
            await openCase(j.result.case_id);
            if (alive) router.dismissTo('/report');
            return;
          }
          if (j.status === 'error') {
            setError(j.error ?? 'The check failed.');
            return;
          }
        } catch (e) {
          if (++misses >= 5) {
            setError((e as Error).message);
            return;
          }
        }
        await new Promise((r) => setTimeout(r, 1000));
      }
    })();
    return () => {
      alive = false;
      clearInterval(tick);
    };
  }, [jobId, openCase]);

  const steps = job?.steps ?? [];
  const running = !error && job?.status !== 'done';
  const photo = steps.some((s) => s.label.startsWith('Gemma 4 reading'));

  return (
    <View style={{ flex: 1 }}>
      <StatusBar style="light" />
      <GreenBackdrop />
      <ScrollView contentContainerStyle={{ paddingTop: insets.top + 40, paddingHorizontal: 20, paddingBottom: insets.bottom + 30, alignItems: 'center' }}>
        <View style={{ flexDirection: 'row', alignItems: 'flex-end' }}>
          <Text style={styles.huge}>{seconds}</Text>
          <Text style={styles.unit}>sec</Text>
        </View>
        <Text style={styles.lead}>{error ? 'Something went wrong' : steps.length ? steps[steps.length - 1].label : 'Starting…'}</Text>

        <PulseButton active={running} onPress={() => {}} label="Analysis in progress">
          {running ? <ScanLine size={28} color={colors.sageDeep} /> : <Check size={30} color={colors.sageDeep} />}
        </PulseButton>

        <View style={styles.glass}>
          {steps.map((s, i) => {
            const current = running && i === steps.length - 1;
            return (
              <View key={i} style={styles.step}>
                <View style={[styles.stepIcon, current && { backgroundColor: 'transparent' }]}>
                  {current ? <ActivityIndicator color={colors.white} size="small" /> : <Check size={14} color={colors.sageDeep} strokeWidth={3} />}
                </View>
                <Text style={[styles.stepText, current && { fontFamily: font.semibold }]}>{s.label}</Text>
                <Text style={styles.stepTime}>{s.at.toFixed(0)}s</Text>
              </View>
            );
          })}
          {!steps.length ? <Text style={styles.stepText}>Sending your prescription…</Text> : null}
        </View>

        {error ? (
          <View style={{ width: '100%', gap: 10, marginTop: 16 }}>
            <Text style={[styles.note, { color: '#FFE3E8', fontFamily: font.semibold }]}>{error}</Text>
            <Button title="Back to the form" tone="white" onPress={() => (router.canGoBack() ? router.back() : router.replace('/scan'))} />
          </View>
        ) : (
          <Text style={styles.note}>
            {photo
              ? 'Gemma 4 is reading the photo. Through the Gemini API this can take 40–200 seconds; answers are cached, so a repeat is instant.'
              : 'Gemma reads, code decides, and a doctor confirms anything unclear.'}
          </Text>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  huge: { fontFamily: font.light, fontSize: 96, lineHeight: 104, color: colors.white, letterSpacing: -3 },
  unit: { fontFamily: font.regular, fontSize: 20, color: colors.white, marginLeft: 6, marginBottom: 18 },
  lead: { fontFamily: font.regular, fontSize: 18, lineHeight: 25, color: colors.white, textAlign: 'center', marginTop: 4, maxWidth: 320 },
  glass: { width: '100%', backgroundColor: 'rgba(255,255,255,0.14)', borderRadius: 24, borderWidth: 1, borderColor: 'rgba(255,255,255,0.4)', padding: 16, gap: 12 },
  step: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  stepIcon: { width: 24, height: 24, borderRadius: 12, backgroundColor: colors.white, alignItems: 'center', justifyContent: 'center' },
  stepText: { flex: 1, fontFamily: font.regular, fontSize: 15.5, color: colors.white },
  stepTime: { fontFamily: font.medium, fontSize: 13, color: 'rgba(255,255,255,0.75)' },
  note: { fontFamily: font.regular, fontSize: 13.5, lineHeight: 19, color: 'rgba(255,255,255,0.85)', textAlign: 'center', marginTop: 16 },
});
