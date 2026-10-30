import Constants from 'expo-constants';
import { router, useFocusEffect } from 'expo-router';
import { ChevronRight, FlaskConical, Server, Stethoscope, Trash2, User, type LucideIcon } from 'lucide-react-native';
import { useCallback, useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { TopBar } from '@/components/chrome';
import { Banner, Button, Card, CardHeader, Label, Segmented, T, Title } from '@/components/ui';
import { api, defaultApiUrl, type Settings as ServerSettings } from '@/lib/api';
import { useApp } from '@/lib/store';
import { colors, font, TAB_CLEARANCE } from '@/lib/theme';

export default function Settings() {
  const { apiUrl, setApiUrl, resetAll } = useApp();
  const [url, setUrl] = useState(apiUrl);
  const [status, setStatus] = useState<{ ok: boolean; text: string } | null>(null);
  const [testing, setTesting] = useState(false);
  const [server, setServer] = useState<ServerSettings | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);

  const loadServer = useCallback(() => {
    api.settings().then(setServer).catch(() => setServer(null));
  }, []);
  useFocusEffect(loadServer);

  async function saveAndTest() {
    const clean = url.trim().replace(/\/$/, '') || defaultApiUrl();
    setUrl(clean);
    setApiUrl(clean);
    setTesting(true);
    try {
      const h = await api.health();
      setStatus({ ok: true, text: `Connected · ${h.backend} / ${h.model}` });
      loadServer();
    } catch (e) {
      setStatus({ ok: false, text: (e as Error).message });
    }
    setTesting(false);
  }

  async function chooseBackend(b: ServerSettings['backend']) {
    try {
      setServer(await api.setBackend(b));
    } catch (e) {
      setStatus({ ok: false, text: (e as Error).message });
    }
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={{ paddingBottom: TAB_CLEARANCE }} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
          <TopBar />
          <View style={{ paddingHorizontal: 20, gap: 14 }}>
            <View style={{ marginTop: 14 }}>
              <Label>AushNexa</Label>
              <Title>Settings</Title>
            </View>

            <Card style={{ gap: 12 }}>
              <CardHeader label="AushNexa server" right={<Server size={18} color={colors.muted} />} />
              <TextInput
                value={url}
                onChangeText={setUrl}
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="url"
                placeholder="http://192.168.1.10:8000"
                placeholderTextColor={colors.faint}
                style={styles.input}
              />
              <Button title="Save and test" onPress={saveAndTest} loading={testing} small />
              {status ? <Banner tone={status.ok ? 'info' : 'error'} text={status.text} /> : null}
              <T style={styles.hint}>
                Run the backend on your computer, then use its Wi-Fi address with port 8000. In Expo Go this is filled in automatically.
              </T>
            </Card>

            <Card style={{ gap: 12 }}>
              <CardHeader label="Gemma 4 model" />
              {server ? (
                <>
                  <Segmented options={server.options.map((o) => ({ key: o.id, label: o.label }))} value={server.backend} onChange={chooseBackend} />
                  <Text style={styles.model}>{server.model}</Text>
                  <T style={styles.hint}>
                    {server.backend === 'gemini'
                      ? `Gemma 4 through the Gemini API. API key on the server: ${server.gemini_key_set ? 'set' : 'not set'}.`
                      : 'Gemma 4 open weights on your own computer with Ollama, so photos never leave it.'}
                    {server.fallback_to_local && server.backend === 'gemini' ? ' Falls back to local Ollama if the API fails.' : ''}
                  </T>
                </>
              ) : (
                <T style={styles.hint}>Connect to the server to choose between the Gemini API and local Ollama.</T>
              )}
            </Card>

            <Card style={{ paddingVertical: 6 }}>
              <Row icon={User} title="Your profile" text="Name, conditions and allergies used in every check" onPress={() => router.push('/profile')} />
              <Row icon={Stethoscope} title="Doctor Console" text="Answer patients' questions and confirm medicines" onPress={() => router.push('/doctor')} divider />
              <Row icon={FlaskConical} title="Safety Test Lab" text="Run the preset safety cases on real brand data" onPress={() => router.push('/testlab')} divider />
            </Card>

            <Card style={{ gap: 8 }}>
              <CardHeader label="About" />
              <Text style={styles.motto}>Gemma reads → code decides → a doctor confirms.</Text>
              <T style={styles.hint}>
                AushNexa supports medication review only. The absence of an alert does not mean a prescription is safe. It is
                not a substitute for a doctor or pharmacist, and it has no regulatory approval.
              </T>
              <T style={styles.hint}>
                Brand data: junioralive/Indian-Medicine-Dataset (MIT), 241,987 brands. Jan Aushadhi prices are indicative.
                Speech-to-text: Whisper, running on the server.
              </T>
              <T style={[styles.hint, { color: colors.faint }]}>Version {Constants.expoConfig?.version ?? '1.0.0'}</T>
            </Card>

            <Button
              title={confirmReset ? 'Tap again to clear everything' : 'Clear data on this phone'}
              icon={Trash2}
              tone={confirmReset ? 'danger' : 'secondary'}
              onPress={() => {
                if (!confirmReset) {
                  setConfirmReset(true);
                  return;
                }
                resetAll();
                setConfirmReset(false);
              }}
            />
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

function Row({ icon: Icon, title, text, onPress, divider }: { icon: LucideIcon; title: string; text: string; onPress: () => void; divider?: boolean }) {
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [styles.row, divider && styles.divider, pressed && { opacity: 0.7 }]} accessibilityRole="button">
      <View style={styles.rowIcon}>
        <Icon size={20} color={colors.sageDeep} strokeWidth={1.8} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.rowTitle}>{title}</Text>
        <Text style={styles.rowText}>{text}</Text>
      </View>
      <ChevronRight size={20} color={colors.faint} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  input: { height: 52, borderRadius: 18, backgroundColor: colors.white, paddingHorizontal: 16, fontFamily: font.medium, fontSize: 15.5, color: colors.ink, borderWidth: 1, borderColor: colors.line },
  hint: { fontSize: 14, color: colors.muted, lineHeight: 20 },
  model: { fontFamily: font.semibold, fontSize: 15, color: colors.ink },
  motto: { fontFamily: font.medium, fontSize: 18, color: colors.sageDeep },
  row: { flexDirection: 'row', alignItems: 'center', gap: 14, paddingVertical: 14 },
  divider: { borderTopWidth: 1, borderTopColor: colors.line },
  rowIcon: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.sageMist, alignItems: 'center', justifyContent: 'center' },
  rowTitle: { fontFamily: font.semibold, fontSize: 16, color: colors.ink },
  rowText: { fontFamily: font.regular, fontSize: 13.5, color: colors.muted, marginTop: 2 },
});
