import { LinearGradient } from 'expo-linear-gradient';
import { usePathname } from 'expo-router';
import { BatteryFull, Signal, Wifi } from 'lucide-react-native';
import type { ReactNode } from 'react';
import { StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { SafeAreaInsetsContext } from 'react-native-safe-area-context';

import { Logo } from './chrome';
import { colors, font } from '@/lib/theme';

/** Room for the drawn status bar and home indicator, like a real iPhone. */
const INSETS = { top: 50, bottom: 24, left: 0, right: 0 };
const PHONE_W = 390;
const BEZEL = 11;
const LIGHT_STATUS = ['/symptoms', '/analyzing'];
const embedded = typeof window !== 'undefined' && window.self !== window.top;

/**
 * Showcase layout for laptops and projectors: the app runs inside a phone frame, and on wide screens a second
 * phone shows the Doctor Console (the same app at /doctor, in an iframe) so the ask-a-doctor loop can be shown
 * side by side. On a phone-sized browser the app simply fills the screen.
 */
export function WebFrame({ children }: { children: ReactNode }) {
  const { width, height } = useWindowDimensions();
  const path = usePathname();
  const inset = <SafeAreaInsetsContext.Provider value={INSETS}>{children}</SafeAreaInsetsContext.Provider>;

  if (embedded) return inset; // the Doctor Console phone: the parent page draws its frame
  if (width < 600) return <>{children}</>;

  const phoneH = Math.max(560, Math.min(844, height - 190));
  return (
    <View style={styles.page}>
      <LinearGradient colors={['#E4EBDF', '#CBD8C3']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={StyleSheet.absoluteFill} />
      <View style={styles.header}>
        <Logo size={46} />
        <View>
          <Text style={styles.brand}>AushNexa</Text>
          <Text style={styles.tagline}>Prescription safety for Indian brand medicines · Gemma reads → code decides → a doctor confirms</Text>
        </View>
      </View>
      <View style={styles.phones}>
        <Phone height={phoneH} label="Patient app" light={LIGHT_STATUS.some((p) => path.startsWith(p))}>
          {inset}
        </Phone>
        {width >= 1000 ? (
          <Phone height={phoneH} label="Doctor Console · played by a teammate in the demo">
            <iframe src="/doctor" title="AushNexa Doctor Console" style={{ border: 0, width: '100%', height: '100%', display: 'block' }} />
          </Phone>
        ) : null}
      </View>
    </View>
  );
}

function Phone({ height, label, light = false, children }: { height: number; label: string; light?: boolean; children: ReactNode }) {
  const ink = light ? colors.white : colors.ink;
  return (
    <View style={{ alignItems: 'center', gap: 14 }}>
      <View style={styles.bezel}>
        <View style={[styles.screen, { height }]}>
          {children}
          <View pointerEvents="none" style={styles.statusBar}>
            <Text style={[styles.time, { color: ink }]}>9:41</Text>
            <View style={styles.island} />
            <View style={styles.statusIcons}>
              <Signal size={16} color={ink} strokeWidth={2.4} />
              <Wifi size={16} color={ink} strokeWidth={2.4} />
              <BatteryFull size={22} color={ink} strokeWidth={1.8} />
            </View>
          </View>
          <View pointerEvents="none" style={[styles.homeIndicator, { backgroundColor: ink }]} />
        </View>
      </View>
      <Text style={styles.label}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, alignItems: 'center', paddingTop: 24, overflow: 'hidden' },
  header: { flexDirection: 'row', alignItems: 'center', gap: 14, marginBottom: 22, paddingHorizontal: 24 },
  brand: { fontFamily: font.semibold, fontSize: 22, color: colors.ink },
  tagline: { fontFamily: font.regular, fontSize: 14.5, color: colors.inkSoft, marginTop: 2 },
  phones: { flexDirection: 'row', gap: 64, alignItems: 'flex-start', justifyContent: 'center' },
  bezel: {
    padding: BEZEL,
    borderRadius: 58,
    backgroundColor: '#1C1F1B',
    shadowColor: '#2E3A2A',
    shadowOpacity: 0.28,
    shadowRadius: 40,
    shadowOffset: { width: 0, height: 24 },
  },
  screen: { width: PHONE_W, borderRadius: 47, overflow: 'hidden', backgroundColor: colors.bg },
  statusBar: { position: 'absolute', top: 0, left: 0, right: 0, height: 50, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 32 },
  time: { fontFamily: font.semibold, fontSize: 16, width: 70 },
  island: { width: 122, height: 34, borderRadius: 17, backgroundColor: '#0B0C0B', marginTop: 4 },
  statusIcons: { flexDirection: 'row', alignItems: 'center', gap: 5, width: 70, justifyContent: 'flex-end' },
  homeIndicator: { position: 'absolute', bottom: 8, alignSelf: 'center', width: 134, height: 5, borderRadius: 3, opacity: 0.85 },
  label: { fontFamily: font.medium, fontSize: 15, color: colors.inkSoft },
});
