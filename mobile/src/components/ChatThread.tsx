import { Info, Send, Stethoscope, User } from 'lucide-react-native';
import { useEffect, useRef, useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, TextInput, View, type ScrollViewInstance } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { IconButton } from './ui';
import type { Message } from '@/lib/api';
import { clock } from '@/lib/format';
import { colors, font } from '@/lib/theme';

/** Patient and doctor chat. `me` decides which side is "mine". */
export function ChatThread({ messages, me, open, onSend, header }: {
  messages: Message[];
  me: 'patient' | 'doctor';
  open: boolean;
  onSend: (text: string) => Promise<void>;
  header?: React.ReactNode;
}) {
  const insets = useSafeAreaInsets();
  const scroll = useRef<ScrollViewInstance>(null);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => scroll.current?.scrollToEnd({ animated: true }), 60);
    return () => clearTimeout(t);
  }, [messages.length]);

  async function send() {
    const text = draft.trim();
    if (!text || sending) return;
    setSending(true);
    try {
      await onSend(text);
      setDraft('');
    } finally {
      setSending(false);
    }
  }

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={insets.top + 60}>
      <ScrollView ref={scroll} contentContainerStyle={{ padding: 20, gap: 12 }} keyboardShouldPersistTaps="handled">
        {header}
        {messages.map((m) => {
          if (m.sender === 'system') {
            return (
              <View key={m.id} style={styles.system}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <Info size={14} color={colors.muted} />
                  <Text style={styles.meta}>Sent by AushNexa · {clock(m.ts)}</Text>
                </View>
                <Text style={styles.systemText}>{m.text}</Text>
              </View>
            );
          }
          const mine = m.sender === me;
          const Avatar = m.sender === 'doctor' ? Stethoscope : User;
          return (
            <View key={m.id} style={[styles.row, mine && { justifyContent: 'flex-end' }]}>
              {!mine ? (
                <View style={styles.avatar}>
                  <Avatar size={16} color={colors.sageDeep} />
                </View>
              ) : null}
              <View style={[styles.bubble, mine ? styles.mine : styles.theirs]}>
                <Text style={[styles.text, mine && { color: colors.white }]}>{m.text}</Text>
                <Text style={[styles.meta, { marginTop: 4 }, mine && { color: 'rgba(255,255,255,0.75)' }]}>
                  {m.sender === 'doctor' ? 'Doctor' : 'Patient'} · {clock(m.ts)}
                </Text>
              </View>
            </View>
          );
        })}
      </ScrollView>
      {open ? (
        <View style={[styles.composer, { paddingBottom: 12 + insets.bottom }]}>
          <TextInput
            value={draft}
            onChangeText={setDraft}
            placeholder={me === 'doctor' ? 'Reply to the patient…' : 'Message the doctor…'}
            placeholderTextColor={colors.faint}
            style={styles.input}
            multiline
            onSubmitEditing={send}
          />
          <IconButton icon={Send} tone="sage" label="Send" onPress={send} size={50} />
        </View>
      ) : (
        <View style={[styles.closed, { paddingBottom: 14 + insets.bottom }]}>
          <Text style={styles.meta}>This chat is closed.</Text>
        </View>
      )}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'flex-end', gap: 8 },
  avatar: { width: 32, height: 32, borderRadius: 16, backgroundColor: colors.sageMist, alignItems: 'center', justifyContent: 'center' },
  bubble: { maxWidth: '80%', borderRadius: 22, paddingHorizontal: 16, paddingVertical: 11 },
  mine: { backgroundColor: colors.sage, borderBottomRightRadius: 6 },
  theirs: { backgroundColor: colors.white, borderBottomLeftRadius: 6 },
  text: { fontFamily: font.regular, fontSize: 15.5, lineHeight: 21, color: colors.ink },
  meta: { fontFamily: font.regular, fontSize: 11.5, color: colors.muted },
  system: { backgroundColor: '#E4E7E1', borderRadius: 18, padding: 14 },
  systemText: { fontFamily: font.regular, fontSize: 14, lineHeight: 20, color: colors.inkSoft },
  composer: { flexDirection: 'row', alignItems: 'flex-end', gap: 10, paddingHorizontal: 16, paddingTop: 12, borderTopWidth: 1, borderTopColor: colors.line, backgroundColor: colors.bg },
  input: { flex: 1, minHeight: 50, maxHeight: 120, borderRadius: 25, backgroundColor: colors.white, paddingHorizontal: 18, paddingTop: 14, paddingBottom: 12, fontFamily: font.regular, fontSize: 15.5, color: colors.ink, borderWidth: 1, borderColor: colors.line },
  closed: { alignItems: 'center', paddingTop: 14, borderTopWidth: 1, borderTopColor: colors.line },
});
