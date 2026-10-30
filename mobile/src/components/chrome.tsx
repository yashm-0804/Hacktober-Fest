import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';
import { Bell, CalendarDays, ChartColumn, HeartPulse, House, Settings, User, type LucideIcon } from 'lucide-react-native';
import { useEffect, useState } from 'react';
import { Animated, Easing, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Svg, { Defs, Ellipse, G, Rect, RadialGradient, Stop } from 'react-native-svg';
import type { BottomTabBarProps } from 'expo-router/tabs';

import { IconButton } from './ui';
import { useApp } from '@/lib/store';
import { colors, font } from '@/lib/theme';

// ---------------------------------------------------------------- logo

/** Sage disc with a tilted capsule: "aushadhi" is Hindi for medicine. */
export function Logo({ size = 52, glass = false }: { size?: number; glass?: boolean }) {
  const mark = (
    <Svg width={size * 0.56} height={size * 0.56} viewBox="0 0 32 32">
      <G transform="rotate(-40 16 16)">
        <Rect x={4} y={11} width={24} height={10} rx={5} fill="none" stroke={colors.white} strokeWidth={2} />
        <Rect x={4} y={11} width={12} height={10} rx={5} fill={colors.white} />
        <Rect x={10} y={11} width={6} height={10} fill={colors.white} />
      </G>
    </Svg>
  );
  if (glass) {
    return (
      <View style={[styles.logo, { width: size, height: size, borderRadius: size / 2, backgroundColor: 'rgba(255,255,255,0.16)', borderWidth: 1, borderColor: 'rgba(255,255,255,0.5)' }]}>
        {mark}
      </View>
    );
  }
  return (
    <LinearGradient colors={['#A9BF9F', '#6F8B65']} start={{ x: 0.2, y: 0 }} end={{ x: 0.8, y: 1 }} style={[styles.logo, { width: size, height: size, borderRadius: size / 2 }]}>
      {mark}
    </LinearGradient>
  );
}

export function Avatar({ size = 52, onPress }: { size?: number; onPress?: () => void }) {
  const { profile } = useApp();
  const initials = profile.name.trim().split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase()).join('');
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel="Your profile" style={[styles.avatar, { width: size, height: size, borderRadius: size / 2 }]}>
      <LinearGradient colors={['#E9EEE5', '#C9D6C1']} style={[StyleSheet.absoluteFill, { borderRadius: size / 2 }]} />
      <View>
        {initials ? (
          <Text style={{ fontFamily: font.semibold, fontSize: size * 0.34, color: colors.sageDeep }}>{initials}</Text>
        ) : (
          <User size={size * 0.42} color={colors.sageDeep} strokeWidth={1.7} />
        )}
      </View>
    </Pressable>
  );
}

export function TopBar({ glass = false }: { glass?: boolean }) {
  const insets = useSafeAreaInsets();
  const { unread } = useApp();
  return (
    <View style={[styles.topBar, { paddingTop: insets.top + 10 }]}>
      <Pressable onPress={() => router.navigate('/')} accessibilityRole="button" accessibilityLabel="AushNexa home">
        <Logo glass={glass} />
      </Pressable>
      <View style={{ flexDirection: 'row', gap: 10, alignItems: 'center' }}>
        <IconButton icon={Bell} tone={glass ? 'glass' : 'light'} label="Doctor chats" badge={unread > 0} onPress={() => router.push('/inbox')} />
        <Avatar onPress={() => router.push('/profile')} />
      </View>
    </View>
  );
}

// ---------------------------------------------------------------- floating tab bar

const TAB_ICONS: Record<string, { icon: LucideIcon; label: string }> = {
  index: { icon: House, label: 'Overview' },
  report: { icon: ChartColumn, label: 'Report' },
  symptoms: { icon: HeartPulse, label: 'Symptom check' },
  schedule: { icon: CalendarDays, label: 'Dose schedule' },
  settings: { icon: Settings, label: 'Settings' },
};

export function TabBar({ state, navigateToTab, insets }: BottomTabBarProps) {
  const glass = state.routes[state.index]?.name === 'symptoms';
  const inner = (
    <View style={styles.tabRow}>
      {state.routes.map((route, i) => {
        const meta = TAB_ICONS[route.name];
        if (!meta) return null;
        return (
          <IconButton
            key={route.key}
            icon={meta.icon}
            label={meta.label}
            size={54}
            tone={glass ? 'glass' : 'light'}
            active={i === state.index}
            onPress={() => navigateToTab(route.key)}
          />
        );
      })}
    </View>
  );
  return (
    <View pointerEvents="box-none" style={[styles.tabWrap, { bottom: Math.max(insets.bottom, 12) + 6 }]}>
      <View style={[styles.tabPill, glass ? styles.tabPillGlass : styles.tabPillLight]}>
        {Platform.OS !== 'android' ? <BlurView intensity={glass ? 20 : 30} tint={glass ? 'light' : 'extraLight'} style={StyleSheet.absoluteFill} /> : null}
        {inner}
      </View>
    </View>
  );
}

// ---------------------------------------------------------------- green backdrop (Symptom check)

/** Soft sage gradient with out-of-focus foliage, drawn with radial gradients so it looks the same on every platform. */
export function GreenBackdrop() {
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      <LinearGradient colors={['#9DB592', '#83A078', '#6E8C64']} start={{ x: 0, y: 0 }} end={{ x: 0.6, y: 1 }} style={StyleSheet.absoluteFill} />
      <Svg width="100%" height="100%" viewBox="0 0 400 860" preserveAspectRatio="xMidYMid slice" style={StyleSheet.absoluteFill}>
        <Defs>
          <RadialGradient id="leaf" cx="50%" cy="50%" r="50%">
            <Stop offset="0" stopColor="#3F5A37" stopOpacity="0.55" />
            <Stop offset="1" stopColor="#3F5A37" stopOpacity="0" />
          </RadialGradient>
          <RadialGradient id="light" cx="50%" cy="50%" r="50%">
            <Stop offset="0" stopColor="#E6F0DF" stopOpacity="0.5" />
            <Stop offset="1" stopColor="#E6F0DF" stopOpacity="0" />
          </RadialGradient>
        </Defs>
        <Ellipse cx="300" cy="300" rx="190" ry="70" fill="url(#leaf)" transform="rotate(-38 300 300)" />
        <Ellipse cx="350" cy="140" rx="120" ry="44" fill="url(#leaf)" transform="rotate(-62 350 140)" />
        <Ellipse cx="250" cy="460" rx="150" ry="48" fill="url(#leaf)" transform="rotate(-20 250 460)" />
        <Ellipse cx="90" cy="200" rx="170" ry="140" fill="url(#light)" />
        <Ellipse cx="60" cy="700" rx="200" ry="120" fill="url(#light)" />
      </Svg>
    </View>
  );
}

// ---------------------------------------------------------------- pulsing button (Symptom check)

export function PulseButton({ children, active, onPress, label, size = 76 }: {
  children: React.ReactNode;
  active: boolean;
  onPress: () => void;
  label: string;
  size?: number;
}) {
  const [a] = useState(() => new Animated.Value(0));
  const [b] = useState(() => new Animated.Value(0));
  useEffect(() => {
    const dur = active ? 1100 : 2400;
    const loop = (v: Animated.Value, delay: number) =>
      Animated.loop(Animated.sequence([
        Animated.delay(delay),
        Animated.timing(v, { toValue: 1, duration: dur, easing: Easing.out(Easing.quad), useNativeDriver: true }),
        Animated.timing(v, { toValue: 0, duration: 0, useNativeDriver: true }),
      ]));
    const la = loop(a, 0);
    const lb = loop(b, dur / 2);
    la.start();
    lb.start();
    return () => {
      la.stop();
      lb.stop();
    };
  }, [active, a, b]);
  const ring = (v: Animated.Value) => ({
    position: 'absolute' as const,
    width: size,
    height: size,
    borderRadius: size / 2,
    borderWidth: 1.5,
    borderColor: 'rgba(255,255,255,0.7)',
    opacity: v.interpolate({ inputRange: [0, 1], outputRange: [0.8, 0] }),
    transform: [{ scale: v.interpolate({ inputRange: [0, 1], outputRange: [1, active ? 2.1 : 1.7] }) }],
  });
  return (
    <View style={{ width: size * 2.1, height: size * 2.1, alignItems: 'center', justifyContent: 'center' }}>
      <View style={{ position: 'absolute', width: size * 1.55, height: size * 1.55, borderRadius: size, backgroundColor: 'rgba(255,255,255,0.12)', borderWidth: 1, borderColor: 'rgba(255,255,255,0.3)' }} />
      <Animated.View style={ring(a)} />
      <Animated.View style={ring(b)} />
      <Pressable
        onPress={onPress}
        accessibilityRole="button"
        accessibilityLabel={label}
        style={({ pressed }) => [{
          width: size,
          height: size,
          borderRadius: size / 2,
          backgroundColor: 'rgba(255,255,255,0.88)',
          alignItems: 'center',
          justifyContent: 'center',
          shadowColor: '#2E4228',
          shadowOpacity: 0.25,
          shadowRadius: 16,
          shadowOffset: { width: 0, height: 6 },
          elevation: 6,
        }, pressed && { transform: [{ scale: 0.95 }] }]}
      >
        {children}
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  logo: { alignItems: 'center', justifyContent: 'center' },
  avatar: { alignItems: 'center', justifyContent: 'center', overflow: 'hidden', borderWidth: 2, borderColor: colors.white },
  topBar: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20, paddingBottom: 8 },
  tabWrap: { position: 'absolute', left: 0, right: 0, alignItems: 'center' },
  tabPill: { borderRadius: 999, overflow: 'hidden', padding: 7 },
  tabPillLight: { backgroundColor: 'rgba(236,238,233,0.78)', borderWidth: 1, borderColor: 'rgba(255,255,255,0.9)', shadowColor: '#2E3A2A', shadowOpacity: 0.12, shadowRadius: 20, shadowOffset: { width: 0, height: 8 }, elevation: 8 },
  tabPillGlass: { backgroundColor: 'rgba(255,255,255,0.1)', borderWidth: 1, borderColor: 'rgba(255,255,255,0.35)' },
  tabRow: { flexDirection: 'row', gap: 9 },
});
