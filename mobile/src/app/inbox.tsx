import { router, useFocusEffect } from 'expo-router';
import { HeartPulse, MessageCircle, Pill } from 'lucide-react-native';
import { useCallback } from 'react';
import { Text, View } from 'react-native';

import { Card, Chip, Empty, StackScreen, T } from '@/components/ui';
import { timeAgo } from '@/lib/format';
import { useApp } from '@/lib/store';
import { colors, font } from '@/lib/theme';

export default function Inbox() {
  const { inbox, lastSeen, markSeen, refreshCase, refreshSymptom } = useApp();
  // Read the unread state before marking everything seen.
  const seenAt = lastSeen;
  useFocusEffect(
    useCallback(() => {
      refreshCase();
      refreshSymptom();
      return () => markSeen();
    }, [refreshCase, refreshSymptom, markSeen]),
  );

  return (
    <StackScreen title="Doctor chats" subtitle="Your questions">
      {inbox.length ? inbox.map((e) => {
        const Icon = e.kind === 'symptom' ? HeartPulse : Pill;
        const fresh = e.last_message?.sender === 'doctor' && e.last_message.ts > seenAt;
        return (
          <Card key={e.id} onPress={() => router.push(`/chat/${e.id}`)} style={{ flexDirection: 'row', gap: 14, alignItems: 'center' }}>
            <View style={{ width: 46, height: 46, borderRadius: 23, backgroundColor: colors.sageMist, alignItems: 'center', justifyContent: 'center' }}>
              <Icon size={20} color={colors.sageDeep} />
            </View>
            <View style={{ flex: 1, gap: 3 }}>
              <Text style={{ fontFamily: font.semibold, fontSize: 16, color: colors.ink }} numberOfLines={1}>
                {e.kind === 'symptom' ? 'Symptom check' : `Line ${e.med_index + 1}: ${e.raw_text}`}
              </Text>
              <T numberOfLines={2} style={{ fontSize: 14, color: colors.muted }}>
                {e.last_message ? `${e.last_message.sender === 'doctor' ? 'Doctor: ' : e.last_message.sender === 'patient' ? 'You: ' : ''}${e.last_message.text}` : 'No messages yet'}
              </T>
              <Text style={{ fontFamily: font.regular, fontSize: 12, color: colors.faint }}>{timeAgo(e.last_message?.ts ?? e.created_at)}</Text>
            </View>
            <View style={{ alignItems: 'flex-end', gap: 6 }}>
              {e.status === 'open'
                ? <Chip label="Waiting" dot={colors.peach} ink={colors.peachInk} soft="#FBEBDC" />
                : <Chip label="Answered" dot={colors.green} ink={colors.greenInk} soft="#E3EEDC" />}
              {fresh ? <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: colors.heart }} /> : null}
            </View>
          </Card>
        );
      }) : (
        <Empty icon={MessageCircle} title="No doctor chats yet" text="When a medicine can't be read confidently, or after a symptom check, tap Ask a doctor. Replies show up here." />
      )}
    </StackScreen>
  );
}
