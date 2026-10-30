import { useLocalSearchParams } from 'expo-router';
import { CheckCheck, ImageOff } from 'lucide-react-native';
import { useState } from 'react';
import { Image, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { ChatThread } from '@/components/ChatThread';
import { Banner, Bullets, Button, Card, CardHeader, Chip, Label, Segmented, StackScreen, T, usePoll } from '@/components/ui';
import { api, apiUrl, type EscalationDetail } from '@/lib/api';
import { saltsText } from '@/lib/format';
import { bandTone, colors, font, urgencyInfo } from '@/lib/theme';

export default function DoctorEscalation() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const eid = Number(id);
  const [d, setD] = useState<EscalationDetail | null>(null);
  const [tab, setTab] = useState<'case' | 'chat'>('case');
  const [other, setOther] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setD(await api.escalation(eid));
    } catch (e) {
      setError((e as Error).message);
    }
  };
  usePoll(load, 3000);

  async function confirm(resolution: { name?: string; free_text?: string }, key: string) {
    setBusy(key);
    setError(null);
    try {
      await api.resolve(eid, resolution);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
    setBusy(null);
  }

  const open = d?.status === 'open';
  const chatCount = d?.messages.filter((m) => m.sender !== 'system').length ?? 0;

  return (
    <StackScreen
      title={d ? (d.kind === 'symptom' ? 'Symptom check' : `Line ${d.med_index + 1}`) : 'Escalation'}
      subtitle={`Doctor Console · #${eid}`}
      scroll={false}
      right={d ? (open ? <Chip label="Open" dot={colors.peach} ink={colors.peachInk} soft="#FBEBDC" /> : <Chip label="Resolved" dot={colors.green} ink={colors.greenInk} soft="#E3EEDC" />) : null}
    >
      <View style={{ paddingHorizontal: 20, paddingTop: 10 }}>
        <Segmented options={[{ key: 'case', label: 'Case' }, { key: 'chat', label: `Chat${chatCount ? ` · ${chatCount}` : ''}` }]} value={tab} onChange={setTab} />
      </View>
      {!d ? (
        <View style={{ padding: 20 }}>{error ? <Banner text={error} /> : <T>Loading…</T>}</View>
      ) : tab === 'chat' ? (
        <ChatThread
          me="doctor"
          open={open}
          messages={d.messages}
          onSend={async (text) => {
            const r = await api.sendMessage(eid, 'doctor', text);
            setD({ ...d, messages: r.messages });
          }}
        />
      ) : (
        <ScrollView contentContainerStyle={{ padding: 20, gap: 14, paddingBottom: 40 }} keyboardShouldPersistTaps="handled">
          {error ? <Banner text={error} /> : null}
          {!open ? <Banner tone="info" text={`Resolved: ${d.resolution?.name ?? d.resolution?.free_text ?? 'answered'}. The patient's app updates within a few seconds.`} /> : null}

          {d.kind === 'symptom' ? (
            <>
              <Card style={{ gap: 8 }}>
                <CardHeader label="Patient says" />
                <Text style={styles.quote}>“{d.raw_text}”</Text>
                {d.triage ? (
                  <Text style={styles.strong}>
                    AushNexa urgency: {urgencyInfo[d.triage.urgency]?.title ?? d.triage.urgency} (from {d.triage.urgency_source})
                  </Text>
                ) : null}
              </Card>
              {d.triage?.red_flags.length ? (
                <Card style={{ gap: 8 }}>
                  <CardHeader label="Warning signs (code rules)" />
                  <Bullets items={d.triage.red_flags.map((f) => `${f.level}: ${f.message}`)} dot={colors.rose} />
                </Card>
              ) : null}
              {d.triage?.gemma.possible_causes.length ? (
                <Card style={{ gap: 8 }}>
                  <CardHeader label="Possible causes (Gemma 4, not a diagnosis)" />
                  <Bullets items={d.triage.gemma.possible_causes.map((c) => (c.why ? `${c.name}: ${c.why}` : c.name))} />
                </Card>
              ) : null}
              {open ? <Button title="Mark as answered" icon={CheckCheck} onPress={() => confirm({}, 'answered')} loading={busy === 'answered'} /> : null}
            </>
          ) : (
            <>
              <Card style={{ gap: 10 }}>
                <CardHeader label="Prescription photo" />
                {d.image_url ? (
                  <Image source={{ uri: apiUrl(d.image_url) }} style={styles.photo} resizeMode="contain" accessibilityLabel="Patient's prescription photo" />
                ) : (
                  <View style={[styles.photo, { alignItems: 'center', justifyContent: 'center', height: 90 }]}>
                    <ImageOff size={22} color={colors.muted} />
                    <T style={{ fontSize: 13.5, color: colors.muted }}>No photo: the prescription was typed.</T>
                  </View>
                )}
              </Card>
              <Card style={{ gap: 8 }}>
                <Label>Line {d.med_index + 1} as read</Label>
                <Text style={styles.quote}>“{d.raw_text}”</Text>
                <Label style={{ marginTop: 6 }}>Patient context</Label>
                <T>{d.context || 'Not given'}</T>
                <Label style={{ marginTop: 6 }}>Allergies</Label>
                <T>{d.allergies || 'None reported'}</T>
              </Card>
              {d.med?.confidence ? (
                <Card style={{ gap: 10 }}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                    <Label style={{ flex: 1 }}>AushNexa confidence</Label>
                    <Chip
                      label={`${bandTone[d.med.confidence.band].label} · ${(d.med.confidence.value * 100).toFixed(0)}%`}
                      dot={bandTone[d.med.confidence.band].dot}
                      ink={bandTone[d.med.confidence.band].ink}
                      soft={bandTone[d.med.confidence.band].soft}
                    />
                  </View>
                  <Bullets items={d.med.confidence.reasons} />
                </Card>
              ) : null}
              <Card style={{ gap: 10 }}>
                <CardHeader label="Confirm the medicine" />
                {d.candidates.map((c) => {
                  const fit = d.med?.fits?.[c.name];
                  return (
                    <View key={c.name} style={styles.cand}>
                      <Text style={styles.strong}>{c.name}</Text>
                      <T style={{ fontSize: 13.5, color: colors.muted }}>{saltsText(c.salts)}</T>
                      <T style={{ fontSize: 13.5 }}>
                        Match {c.score?.toFixed(0) ?? '?'}/100 · Gemma fit: {fit?.fits ?? 'n/a'}{fit?.reason ? ` (${fit.reason})` : ''}
                      </T>
                      {open ? <Button title={`Confirm ${c.name}`} small tone="secondary" onPress={() => confirm({ name: c.name }, c.name)} loading={busy === c.name} style={{ marginTop: 6 }} /> : null}
                    </View>
                  );
                })}
                {open ? (
                  <>
                    <Label style={{ marginTop: 6 }}>Or type the correct medicine</Label>
                    <TextInput value={other} onChangeText={setOther} placeholder="e.g. Calcimax" placeholderTextColor={colors.faint} style={styles.input} />
                    <Button
                      title="Confirm typed medicine"
                      onPress={() => (other.trim() ? confirm({ free_text: other.trim() }, 'other') : setError('Type a medicine name first.'))}
                      loading={busy === 'other'}
                    />
                  </>
                ) : null}
              </Card>
            </>
          )}
        </ScrollView>
      )}
    </StackScreen>
  );
}

const styles = StyleSheet.create({
  photo: { width: '100%', height: 320, borderRadius: 18, backgroundColor: '#E4E7E1' },
  quote: { fontFamily: font.medium, fontSize: 18, color: colors.ink, fontStyle: 'italic' },
  strong: { fontFamily: font.semibold, fontSize: 15.5, color: colors.ink },
  cand: { backgroundColor: colors.white, borderRadius: 18, padding: 14, gap: 3 },
  input: { height: 52, borderRadius: 18, backgroundColor: colors.white, paddingHorizontal: 16, fontFamily: font.regular, fontSize: 15.5, color: colors.ink, borderWidth: 1, borderColor: colors.line },
});
