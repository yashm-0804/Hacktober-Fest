import { router } from 'expo-router';
import { HeartPulse, Inbox, Pill } from 'lucide-react-native';
import { useState } from 'react';
import { Text, View } from 'react-native';

import { Banner, Card, Chip, Empty, Segmented, StackScreen, T, usePoll } from '@/components/ui';
import { api, type EscalationSummary } from '@/lib/api';
import { timeAgo } from '@/lib/format';
import { colors, font } from '@/lib/theme';

export default function DoctorConsole() {
  const [tab, setTab] = useState<'open' | 'resolved'>('open');
  const [items, setItems] = useState<EscalationSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  usePoll(async () => {
    try {
      const list = await api.escalations(tab);
      setItems(tab === 'open' ? list : [...list].reverse());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, 3000);

  return (
    <StackScreen title="Doctor Console" subtitle="For the consulting doctor">
      <Banner tone="info" text="Demo: a teammate plays the doctor on a second phone or browser. In production this is a licensed doctor or pharmacist." />
      <Segmented options={[{ key: 'open', label: 'Open' }, { key: 'resolved', label: 'Resolved' }]} value={tab} onChange={(k) => { setTab(k); setItems(null); }} />
      {error ? <Banner text={error} /> : null}
      {items && !items.length ? (
        <Empty icon={Inbox} title={tab === 'open' ? 'No open questions' : 'Nothing resolved yet'} text="When a patient taps Ask a doctor, the question appears here within a few seconds." />
      ) : null}
      {items?.map((e) => {
        const Icon = e.kind === 'symptom' ? HeartPulse : Pill;
        return (
          <Card key={e.id} onPress={() => router.push(`/doctor/${e.id}`)} style={{ gap: 8 }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
              <View style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: colors.sageMist, alignItems: 'center', justifyContent: 'center' }}>
                <Icon size={18} color={colors.sageDeep} />
              </View>
              <Text style={{ flex: 1, fontFamily: font.semibold, fontSize: 16, color: colors.ink }}>
                #{e.id} · {e.kind === 'symptom' ? 'Symptom check' : `Prescription line ${e.med_index + 1}`}
              </Text>
              <Text style={{ fontFamily: font.regular, fontSize: 12.5, color: colors.muted }}>{timeAgo(e.created_at)}</Text>
            </View>
            <T numberOfLines={2} style={{ fontFamily: font.medium, color: colors.ink }}>“{e.raw_text}”</T>
            <View style={{ flexDirection: 'row', gap: 8 }}>
              <Chip label={`${e.message_count} messages`} ink={colors.inkSoft} soft="#E8EBE5" />
              {e.last_message?.sender === 'patient' && e.status === 'open' ? <Chip label="Patient replied" dot={colors.peach} ink={colors.peachInk} soft="#FBEBDC" /> : null}
            </View>
          </Card>
        );
      })}
    </StackScreen>
  );
}
