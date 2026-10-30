import { useLocalSearchParams } from 'expo-router';
import { useRef, useState } from 'react';
import { Text, View } from 'react-native';

import { ChatThread } from '@/components/ChatThread';
import { Banner, Chip, StackScreen, T, usePoll } from '@/components/ui';
import { api, type EscalationDetail } from '@/lib/api';
import { saltsText } from '@/lib/format';
import { useApp } from '@/lib/store';
import { colors, font } from '@/lib/theme';

export default function PatientChat() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const eid = Number(id);
  const { refreshCase, refreshSymptom, markSeen } = useApp();
  const [detail, setDetail] = useState<EscalationDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wasOpen = useRef<boolean | null>(null);

  usePoll(async () => {
    try {
      const d = await api.escalation(eid);
      setDetail(d);
      setError(null);
      markSeen();
      // The doctor just confirmed: pull the re-checked case so the report updates.
      if (wasOpen.current && d.status === 'resolved') {
        refreshCase();
        refreshSymptom();
      }
      wasOpen.current = d.status === 'open';
    } catch (e) {
      setError((e as Error).message);
    }
  }, 3000);

  const title = detail?.kind === 'symptom' ? 'Symptom check' : detail ? `“${detail.raw_text}”` : 'Doctor chat';
  const resolvedName = detail?.resolution?.name ?? detail?.resolution?.free_text;

  return (
    <StackScreen
      title={title}
      subtitle="Ask a doctor"
      scroll={false}
      right={detail ? (
        detail.status === 'open'
          ? <Chip label="Waiting" dot={colors.peach} ink={colors.peachInk} soft="#FBEBDC" />
          : <Chip label="Answered" dot={colors.green} ink={colors.greenInk} soft="#E3EEDC" />
      ) : null}
    >
      {detail ? (
        <ChatThread
          me="patient"
          open={detail.status === 'open'}
          messages={detail.messages}
          onSend={async (text) => {
            try {
              const r = await api.sendMessage(eid, 'patient', text);
              setDetail({ ...detail, messages: r.messages });
            } catch (e) {
              setError((e as Error).message);
            }
          }}
          header={
            <View style={{ gap: 10 }}>
              {error ? <Banner text={error} /> : null}
              {detail.kind === 'medicine' && detail.candidates.length ? (
                <View style={{ backgroundColor: colors.card, borderRadius: 20, padding: 14, gap: 6 }}>
                  <Text style={{ fontFamily: font.semibold, fontSize: 14, color: colors.ink }}>Possible medicines we found</Text>
                  {detail.candidates.map((c) => (
                    <T key={c.name} style={{ fontSize: 14 }}>• {c.name} · {saltsText(c.salts)}</T>
                  ))}
                </View>
              ) : null}
              {detail.status === 'resolved' && resolvedName ? (
                <Banner tone="info" text={`The doctor confirmed ${resolvedName}. Your report has been re-checked.`} />
              ) : null}
              <T style={{ fontSize: 13, color: colors.muted, textAlign: 'center' }}>
                In this demo a teammate answers from the Doctor Console. In production this is a licensed doctor or pharmacist.
              </T>
            </View>
          }
        />
      ) : (
        <View style={{ padding: 20 }}>{error ? <Banner text={error} /> : <T>Loading…</T>}</View>
      )}
    </StackScreen>
  );
}
