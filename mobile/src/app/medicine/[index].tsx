import { router, useLocalSearchParams } from 'expo-router';
import { CircleCheck, MessageCircle, Pill } from 'lucide-react-native';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { ArcGauge } from '@/components/charts';
import { Banner, Bullets, Button, Card, CardHeader, Chip, Empty, Label, StackScreen, T } from '@/components/ui';
import { api, type Fit } from '@/lib/api';
import { displayBand, effectiveScore, escalationFor, isHumanConfirmed, rupees, saltsText, statusLabel } from '@/lib/format';
import { useApp } from '@/lib/store';
import { bandTone, colors, font } from '@/lib/theme';

const FIT_TONE: Record<string, { label: string; ink: string; soft: string; dot: string }> = {
  yes: { label: 'Fits patient', ink: colors.greenInk, soft: '#E3EEDC', dot: colors.green },
  no: { label: "Doesn't fit", ink: colors.roseInk, soft: '#FBE1E6', dot: colors.rose },
  unclear: { label: 'Unclear fit', ink: colors.inkSoft, soft: '#E8EBE5', dot: colors.faint },
};
const BREAKDOWN: Record<string, string> = {
  match: 'Name match',
  gap_penalty: 'Look-alike nearby',
  unsure_penalty: 'Reader unsure',
  strength_penalty: 'Strength mismatch',
  fit_adjust: 'Fit with condition',
};

export default function Medicine() {
  const { index } = useLocalSearchParams<{ index: string }>();
  const i = Number(index);
  const { caseView, setCaseView } = useApp();
  const med = caseView?.case.meds[i];
  const [choice, setChoice] = useState<string | null>(null);
  const [busy, setBusy] = useState<'pick' | 'ask' | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!caseView || !med) {
    return (
      <StackScreen title="Medicine">
        <Empty icon={Pill} title="Not found" text="This medicine is not in your current check." />
      </StackScreen>
    );
  }

  const resolved = caseView.case.resolved[i];
  const band = displayBand(med);
  const tone = bandTone[band];
  const conf = med.confidence;
  const esc = escalationFor(caseView, i);
  const human = isHumanConfirmed(med);
  const canPick = !human && med.confidence?.band === 'MEDIUM' && med.candidates.length > 0 && esc?.status !== 'open';
  const current = (med.selected ?? med.candidates[0])?.name;
  const selected = choice ?? current;

  async function pick() {
    if (!selected || !caseView) return;
    setBusy('pick');
    setError(null);
    try {
      setCaseView(await api.pick(caseView.id, i, selected));
      setChoice(null);
    } catch (e) {
      setError((e as Error).message);
    }
    setBusy(null);
  }

  async function ask() {
    if (!caseView) return;
    setBusy('ask');
    setError(null);
    try {
      const res = await api.askDoctor(caseView.id, i);
      setCaseView(res.case);
      router.push(`/chat/${res.escalation_id}`);
    } catch (e) {
      setError((e as Error).message);
    }
    setBusy(null);
  }

  const details = [
    med.read.strength && `Strength ${med.read.strength}`,
    med.read.dose_and_frequency && med.read.dose_and_frequency,
    med.read.duration && `for ${med.read.duration}`,
    med.read.form,
  ].filter(Boolean) as string[];

  return (
    <StackScreen title={resolved?.label ?? med.read.brand_or_drug} subtitle={`Medicine ${i + 1} of ${caseView.case.meds.length}`}>
      <Card style={{ gap: 12 }}>
        <View style={{ flexDirection: 'row', gap: 12 }}>
          <View style={{ flex: 1, gap: 6 }}>
            <Label style={{ fontSize: 14 }}>As written</Label>
            <Text style={styles.raw}>“{med.read.raw_text}”</Text>
            <Label style={{ fontSize: 14, marginTop: 6 }}>Matched to</Label>
            <Text style={styles.match}>{resolved?.label ?? 'No match'}</Text>
            <T style={{ fontSize: 14, color: colors.muted }}>{saltsText(resolved?.salts)}</T>
          </View>
          <View style={{ alignItems: 'center', width: 110 }}>
            <ArcGauge value={effectiveScore(med) / 100} width={104} stroke={11} color={tone.dot} />
            <Text style={styles.score}>{effectiveScore(med).toFixed(0)}%</Text>
          </View>
        </View>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
          <Chip label={statusLabel(med, esc)} dot={tone.dot} ink={tone.ink} soft={tone.soft} />
          {med.read.unsure ? <Chip label="Reader unsure" dot={colors.peach} ink={colors.peachInk} soft="#FBEBDC" /> : null}
          {details.map((d) => <Chip key={d} label={d} ink={colors.inkSoft} soft="#E8EBE5" />)}
        </View>
      </Card>

      {esc?.status === 'resolved' && med.status === 'confirmed_by_doctor' ? (
        <Banner tone="info" text={`A doctor confirmed this medicine as ${esc.resolution?.name ?? esc.resolution?.free_text}. Only the code checks re-ran.`} />
      ) : !human && conf?.band === 'LOW' ? (
        <Banner text="We could not read this medicine confidently. A doctor should confirm it before you take it." />
      ) : null}

      {conf ? (
        <Card style={{ gap: 12 }}>
          <CardHeader label="Why this confidence" />
          <Bullets items={conf.reasons} />
          <View style={{ gap: 6, marginTop: 4 }}>
            {Object.entries(conf.breakdown).filter(([, v]) => v !== 0).map(([k, v]) => (
              <View key={k} style={styles.breakRow}>
                <Text style={styles.breakLabel}>{BREAKDOWN[k] ?? k}</Text>
                <Text style={[styles.breakValue, { color: v < 0 ? colors.roseInk : colors.greenInk }]}>{v > 0 && k !== 'match' ? '+' : ''}{v.toFixed(2)}</Text>
              </View>
            ))}
          </View>
          {conf.lasa_rival ? (
            <Banner tone="warn" text={`Look-alike: ${conf.lasa_rival.name} (${saltsText(conf.lasa_rival.salts)}) is a different medicine with a similar name.`} />
          ) : null}
        </Card>
      ) : null}

      <Card style={{ gap: 10 }}>
        <CardHeader label={canPick ? 'Pick the right medicine' : 'Top candidates'} />
        {med.candidates.length ? med.candidates.map((c) => {
          const fit: Fit | undefined = med.fits?.[c.name];
          const ft = FIT_TONE[fit?.fits ?? 'unclear'];
          const on = c.name === selected;
          return (
            <Pressable
              key={c.name}
              disabled={!canPick}
              onPress={() => setChoice(c.name)}
              style={[styles.cand, on && canPick && styles.candOn]}
              accessibilityRole={canPick ? 'radio' : undefined}
              accessibilityState={canPick ? { checked: on } : undefined}
            >
              <View style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 10 }}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.candName}>{c.name}</Text>
                  <T style={{ fontSize: 13.5, color: colors.muted }}>{saltsText(c.salts)}</T>
                </View>
                {canPick ? <View style={[styles.radio, on && styles.radioOn]} /> : c.name === current ? <CircleCheck size={20} color={colors.sage} /> : null}
              </View>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                <Chip label={ft.label} dot={ft.dot} ink={ft.ink} soft={ft.soft} />
                {c.score !== undefined ? <Chip label={`Match ${c.score.toFixed(0)}/100`} ink={colors.inkSoft} soft="#E8EBE5" /> : null}
                {c.price ? <Chip label={`${rupees(c.price)} · ${c.pack ?? ''}`} ink={colors.inkSoft} soft="#E8EBE5" /> : null}
              </View>
              {fit?.reason ? <T style={{ fontSize: 13.5, marginTop: 6 }}>Gemma 4: {fit.reason}</T> : null}
            </Pressable>
          );
        }) : <T style={{ color: colors.muted }}>No matching brand was found in the dataset.</T>}
        {canPick ? <Button title="Use this medicine" onPress={pick} loading={busy === 'pick'} disabled={!selected} /> : null}
      </Card>

      {error ? <Banner text={error} /> : null}

      {esc ? (
        <Button
          title={esc.status === 'open' ? 'Open doctor chat · waiting' : 'View doctor chat'}
          icon={MessageCircle}
          tone={esc.status === 'open' ? 'primary' : 'secondary'}
          onPress={() => router.push(`/chat/${esc.id}`)}
        />
      ) : med.status !== 'confirmed_by_doctor' ? (
        <Button title="Ask a doctor" icon={MessageCircle} tone={conf?.band === 'LOW' ? 'primary' : 'secondary'} onPress={ask} loading={busy === 'ask'} />
      ) : null}
    </StackScreen>
  );
}

const styles = StyleSheet.create({
  raw: { fontFamily: font.medium, fontSize: 17, color: colors.inkSoft, fontStyle: 'italic' },
  match: { fontFamily: font.light, fontSize: 28, lineHeight: 32, color: colors.ink, letterSpacing: -0.5 },
  score: { fontFamily: font.light, fontSize: 26, color: colors.ink, marginTop: -6 },
  breakRow: { flexDirection: 'row', justifyContent: 'space-between' },
  breakLabel: { fontFamily: font.regular, fontSize: 14, color: colors.muted },
  breakValue: { fontFamily: font.semibold, fontSize: 14 },
  cand: { backgroundColor: colors.white, borderRadius: 20, padding: 14, borderWidth: 1.5, borderColor: 'transparent' },
  candOn: { borderColor: colors.sage },
  candName: { fontFamily: font.semibold, fontSize: 16, color: colors.ink },
  radio: { width: 22, height: 22, borderRadius: 11, borderWidth: 2, borderColor: colors.faint },
  radioOn: { borderColor: colors.sage, borderWidth: 7 },
});
