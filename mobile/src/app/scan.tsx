import * as ImagePicker from 'expo-image-picker';
import { router, useLocalSearchParams } from 'expo-router';
import { Camera, Images, Sparkles, X } from 'lucide-react-native';
import { useEffect, useState } from 'react';
import { Image, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { Banner, Button, Card, CardHeader, Segmented, StackScreen, T } from '@/components/ui';
import { api, apiUrl, type LocalFile, type Settings } from '@/lib/api';
import { useApp } from '@/lib/store';
import { colors, font } from '@/lib/theme';

type Photo = { file: LocalFile | null; preview: string } | null;

async function pickImage(source: 'camera' | 'library'): Promise<{ file: LocalFile; preview: string } | null> {
  if (source === 'camera' && Platform.OS !== 'web') {
    const perm = await ImagePicker.requestCameraPermissionsAsync();
    if (!perm.granted) throw new Error('Camera permission is off. Choose a photo from your gallery instead.');
  }
  const opts: ImagePicker.ImagePickerOptions = { mediaTypes: ['images'], quality: 0.85 };
  const res = source === 'camera' ? await ImagePicker.launchCameraAsync(opts) : await ImagePicker.launchImageLibraryAsync(opts);
  const a = res.canceled ? null : res.assets?.[0];
  if (!a) return null;
  const type = a.mimeType ?? 'image/jpeg';
  return { file: { uri: a.uri, name: a.fileName ?? `photo.${type.split('/')[1] ?? 'jpg'}`, type }, preview: a.uri };
}

export default function Scan() {
  const params = useLocalSearchParams<{ demo?: string }>();
  const { profile, draftContext, setDraftContext } = useApp();
  const [context, setContext] = useState(draftContext ?? profile.conditions);
  const [allergies, setAllergies] = useState(profile.allergies);
  const [mode, setMode] = useState<'photo' | 'typed'>('photo');
  const [typed, setTyped] = useState('');
  const [rx, setRx] = useState<Photo>(null);
  const [strip, setStrip] = useState<Photo>(null);
  const [demo, setDemo] = useState<{ typed: string } | null>(null);
  const [server, setServer] = useState<Settings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (draftContext) setDraftContext(null);
    api.settings().then(setServer).catch(() => {});
    if (params.demo) loadDemo();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const noModel = server?.backend === 'gemini' && !server.gemini_key_set && !server.fallback_to_local;

  async function loadDemo() {
    setError(null);
    try {
      const d = await api.demo();
      setContext(d.context);
      setAllergies(d.allergies);
      setRx({ file: null, preview: apiUrl(d.prescription_url) });
      setStrip({ file: null, preview: apiUrl(d.strip_url) });
      setDemo({ typed: d.typed_rx });
      setTyped(d.typed_rx);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function choose(target: 'rx' | 'strip', source: 'camera' | 'library') {
    setError(null);
    try {
      const picked = await pickImage(source);
      if (picked) (target === 'rx' ? setRx : setStrip)(picked);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function analyze() {
    setError(null);
    if (mode === 'typed' && !typed.trim()) return setError('Type at least one medicine, one per line.');
    if (mode === 'photo' && !rx) return setError('Add a photo of the prescription, or switch to "Type it".');
    setSending(true);
    try {
      const usesDemoPhoto = (mode === 'photo' && rx && !rx.file) || (strip && !strip.file);
      const { job_id } = await api.analyze({
        context,
        allergies,
        rxText: mode === 'typed' ? typed : '',
        rxImage: mode === 'photo' ? rx?.file : null,
        stripImage: strip?.file,
        useDemoImages: !!usesDemoPhoto,
      });
      router.replace(`/analyzing/${job_id}`);
    } catch (e) {
      setError((e as Error).message);
      setSending(false);
    }
  }

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <StackScreen
        title="New check"
        subtitle="Prescription safety"
        footer={<Button title={sending ? 'Sending…' : 'Analyze prescription'} onPress={analyze} loading={sending} />}
      >
        {!demo ? (
          <Pressable onPress={loadDemo} style={styles.demo} accessibilityRole="button">
            <Sparkles size={18} color={colors.sageDeep} />
            <Text style={styles.demoText}>Load the demo case (synthetic prescription)</Text>
          </Pressable>
        ) : null}

        <Card style={{ gap: 10 }}>
          <CardHeader label="1 · About the patient" />
          <TextInput
            value={context}
            onChangeText={setContext}
            placeholder="Symptoms or conditions, e.g. fever and body ache for 3 days; vitamin D deficiency"
            placeholderTextColor={colors.faint}
            multiline
            style={[styles.input, { minHeight: 92 }]}
          />
          <TextInput
            value={allergies}
            onChangeText={setAllergies}
            placeholder="Allergies, comma-separated, e.g. penicillin, sulfa"
            placeholderTextColor={colors.faint}
            style={styles.input}
          />
          <T style={styles.hint}>Gemma 4 uses this to judge whether each medicine fits. Allergy checks are done by code.</T>
        </Card>

        <Card style={{ gap: 12 }}>
          <CardHeader label="2 · Prescription" />
          <Segmented options={[{ key: 'photo', label: 'Photo' }, { key: 'typed', label: 'Type it' }]} value={mode} onChange={setMode} />
          {mode === 'photo' ? (
            <>
              <PhotoField photo={rx} onClear={() => setRx(null)} onPick={(src) => choose('rx', src)} height={260} caption={rx && !rx.file ? 'Synthetic demo prescription' : undefined} />
              {noModel ? (
                <Banner tone="warn" text="The server has no Gemini API key and no local fallback, so photos can't be read. Use 'Type it', or add GEMINI_API_KEY to backend/.env." />
              ) : (
                <T style={styles.hint}>Handwriting is fine. Gemma 4 can take 40–200 s to read a photo through the Gemini API.</T>
              )}
            </>
          ) : (
            <>
              <TextInput
                value={typed}
                onChangeText={setTyped}
                placeholder={'One medicine per line\nDolo 650 TDS x 5 days\nCombiflam SOS'}
                placeholderTextColor={colors.faint}
                multiline
                autoCapitalize="words"
                style={[styles.input, styles.mono, { minHeight: 140 }]}
              />
              <T style={styles.hint}>Typed medicines skip the photo read and finish in seconds. OD, BD, TDS, SOS, HS and 1-0-1 are understood.</T>
            </>
          )}
        </Card>

        <Card style={{ gap: 12 }}>
          <CardHeader label="3 · Medicine strip (optional)" />
          <T style={styles.hint}>A photo of the strip or box the pharmacy gave you. We check it matches the prescription.</T>
          <PhotoField photo={strip} onClear={() => setStrip(null)} onPick={(src) => choose('strip', src)} height={170} caption={strip && !strip.file ? 'Synthetic demo strip' : undefined} />
        </Card>

        {error ? <Banner text={error} /> : null}
      </StackScreen>
    </KeyboardAvoidingView>
  );
}

function PhotoField({ photo, onPick, onClear, height, caption }: {
  photo: Photo;
  onPick: (source: 'camera' | 'library') => void;
  onClear: () => void;
  height: number;
  caption?: string;
}) {
  if (photo) {
    return (
      <View>
        <Image source={{ uri: photo.preview }} style={{ width: '100%', height, borderRadius: 20, backgroundColor: colors.line }} resizeMode="cover" accessibilityLabel={caption ?? 'Chosen photo'} />
        <Pressable onPress={onClear} style={styles.clear} accessibilityRole="button" accessibilityLabel="Remove photo" hitSlop={8}>
          <X size={18} color={colors.ink} />
        </Pressable>
        {caption ? <Text style={styles.caption}>{caption}</Text> : null}
      </View>
    );
  }
  return (
    <View style={[styles.drop, { height: Math.min(height, 150) }]}>
      <Button title="Camera" icon={Camera} tone="secondary" small onPress={() => onPick('camera')} style={{ flex: 1 }} />
      <Button title="Gallery" icon={Images} tone="secondary" small onPress={() => onPick('library')} style={{ flex: 1 }} />
    </View>
  );
}

const styles = StyleSheet.create({
  input: { borderRadius: 18, backgroundColor: colors.white, paddingHorizontal: 16, paddingVertical: 14, fontFamily: font.regular, fontSize: 15.5, color: colors.ink, borderWidth: 1, borderColor: colors.line, textAlignVertical: 'top' },
  mono: { fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }), fontSize: 15 },
  hint: { fontSize: 13.5, color: colors.muted, lineHeight: 19 },
  demo: { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: colors.sageMist, borderRadius: 20, padding: 16 },
  demoText: { fontFamily: font.semibold, fontSize: 15, color: colors.sageDeep, flex: 1 },
  drop: { flexDirection: 'row', gap: 10, alignItems: 'center', justifyContent: 'center', borderRadius: 20, borderWidth: 1.5, borderStyle: 'dashed', borderColor: colors.faint, paddingHorizontal: 16 },
  clear: { position: 'absolute', top: 10, right: 10, width: 36, height: 36, borderRadius: 18, backgroundColor: 'rgba(255,255,255,0.92)', alignItems: 'center', justifyContent: 'center' },
  caption: { position: 'absolute', left: 10, bottom: 10, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12, overflow: 'hidden', backgroundColor: 'rgba(255,255,255,0.92)', fontFamily: font.medium, fontSize: 12.5, color: colors.inkSoft },
});
