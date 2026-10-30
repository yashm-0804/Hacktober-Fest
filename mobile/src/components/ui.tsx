import { router, useFocusEffect } from 'expo-router';
import { ChevronLeft, type LucideIcon } from 'lucide-react-native';
import { useCallback, useEffect, useRef, type ReactNode } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  type StyleProp,
  type TextProps,
  type TextStyle,
  type ViewStyle,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { colors, font, radius } from '@/lib/theme';

// ---------------------------------------------------------------- text

type TProps = TextProps & { style?: StyleProp<TextStyle> };

export const T = ({ style, ...p }: TProps) => <Text {...p} style={[s.body, style]} />;
export const Label = ({ style, ...p }: TProps) => <Text {...p} style={[s.label, style]} />;
export const Title = ({ style, ...p }: TProps) => <Text {...p} style={[s.title, style]} />;

/** The thin oversized numerals from the design ("90.2 %"). */
export function BigNumber({ value, unit, size = 64, color = colors.ink, unitColor = colors.muted }: {
  value: string;
  unit?: string;
  size?: number;
  color?: string;
  unitColor?: string;
}) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'flex-end' }}>
      <Text style={{ fontFamily: font.light, fontSize: size, color, letterSpacing: -size * 0.04, lineHeight: size * 1.08 }}>
        {value}
      </Text>
      {unit ? (
        <Text style={{ fontFamily: font.regular, fontSize: Math.max(13, size * 0.22), color: unitColor, marginLeft: 6, marginBottom: size * 0.14 }}>
          {unit}
        </Text>
      ) : null}
    </View>
  );
}

// ---------------------------------------------------------------- surfaces

export function Card({ children, style, onPress }: { children: ReactNode; style?: StyleProp<ViewStyle>; onPress?: () => void }) {
  if (onPress) {
    return (
      <Pressable onPress={onPress} style={({ pressed }) => [s.card, pressed && { opacity: 0.85 }, style]}>
        {children}
      </Pressable>
    );
  }
  return <View style={[s.card, style]}>{children}</View>;
}

export function CardHeader({ label, icon, onIcon, right }: { label: string; icon?: LucideIcon; onIcon?: () => void; right?: ReactNode }) {
  return (
    <View style={s.cardHeader}>
      <Label style={{ flex: 1 }}>{label}</Label>
      {right}
      {icon ? <IconButton icon={icon} onPress={onIcon} size={44} /> : null}
    </View>
  );
}

export function IconButton({ icon: Icon, onPress, size = 48, tone = 'light', active = false, label, badge }: {
  icon: LucideIcon;
  onPress?: () => void;
  size?: number;
  tone?: 'light' | 'glass' | 'sage';
  active?: boolean;
  label?: string;
  badge?: boolean;
}) {
  const bg = tone === 'glass' ? (active ? colors.white : 'rgba(255,255,255,0.16)') : tone === 'sage' || active ? colors.sage : colors.white;
  const fg = tone === 'glass' ? (active ? colors.sageDeep : colors.white) : tone === 'sage' || active ? colors.white : colors.ink;
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={label}
      hitSlop={6}
      style={({ pressed }) => [
        { width: size, height: size, borderRadius: size / 2, backgroundColor: bg, alignItems: 'center', justifyContent: 'center' },
        tone === 'glass' && !active && { borderWidth: 1, borderColor: 'rgba(255,255,255,0.45)' },
        tone === 'light' && !active && s.softShadow,
        pressed && { transform: [{ scale: 0.94 }] },
      ]}
    >
      <Icon size={size * 0.4} color={fg} strokeWidth={1.8} />
      {badge ? <View style={s.badge} /> : null}
    </Pressable>
  );
}

type ButtonTone = 'primary' | 'secondary' | 'danger' | 'glass' | 'white';

export function Button({ title, onPress, tone = 'primary', icon: Icon, loading, disabled, style, small }: {
  title: string;
  onPress?: () => void;
  tone?: ButtonTone;
  icon?: LucideIcon;
  loading?: boolean;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
  small?: boolean;
}) {
  const palette: Record<ButtonTone, { bg: string; fg: string; border?: string }> = {
    primary: { bg: colors.sage, fg: colors.white },
    secondary: { bg: colors.white, fg: colors.ink, border: colors.line },
    danger: { bg: colors.roseInk, fg: colors.white },
    glass: { bg: 'rgba(255,255,255,0.18)', fg: colors.white, border: 'rgba(255,255,255,0.5)' },
    white: { bg: colors.white, fg: colors.sageDeep },
  };
  const p = palette[tone];
  const off = disabled || loading;
  return (
    <Pressable
      onPress={off ? undefined : onPress}
      accessibilityRole="button"
      accessibilityState={{ disabled: !!off }}
      style={({ pressed }) => [
        s.button,
        small && { height: 42, paddingHorizontal: 16 },
        { backgroundColor: p.bg, borderColor: p.border ?? p.bg, opacity: off ? 0.55 : 1 },
        pressed && !off && { transform: [{ scale: 0.98 }] },
        style,
      ]}
    >
      {loading ? <ActivityIndicator color={p.fg} /> : Icon ? <Icon size={small ? 16 : 19} color={p.fg} strokeWidth={2} /> : null}
      <Text style={{ fontFamily: font.semibold, fontSize: small ? 14 : 16, color: p.fg }}>{title}</Text>
    </Pressable>
  );
}

export function Chip({ label, dot, ink, soft, style }: { label: string; dot?: string; ink: string; soft: string; style?: StyleProp<ViewStyle> }) {
  return (
    <View style={[s.chip, { backgroundColor: soft }, style]}>
      {dot ? <View style={[s.dot, { backgroundColor: dot }]} /> : null}
      <Text style={{ fontFamily: font.semibold, fontSize: 12.5, color: ink }}>{label}</Text>
    </View>
  );
}

export function LegendDot({ color, label, light }: { color: string; label: string; light?: boolean }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
      <View style={[s.dot, { backgroundColor: color }]} />
      <Text style={{ fontFamily: font.medium, fontSize: 14, color: light ? colors.white : colors.inkSoft }}>{label}</Text>
    </View>
  );
}

export function Segmented<K extends string>({ options, value, onChange }: {
  options: { key: K; label: string }[];
  value: K;
  onChange: (k: K) => void;
}) {
  return (
    <View style={s.segmented}>
      {options.map((o) => {
        const on = o.key === value;
        return (
          <Pressable key={o.key} onPress={() => onChange(o.key)} style={[s.segment, on && s.segmentOn]} accessibilityRole="tab" accessibilityState={{ selected: on }}>
            <Text style={{ fontFamily: on ? font.semibold : font.medium, fontSize: 14.5, color: on ? colors.ink : colors.muted }}>{o.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export function Banner({ text, tone = 'error' }: { text: string; tone?: 'error' | 'warn' | 'info' }) {
  const t = { error: { bg: '#FBE1E6', fg: colors.roseInk }, warn: { bg: '#FBEBDC', fg: colors.peachInk }, info: { bg: colors.sageMist, fg: colors.sageDeep } }[tone];
  return (
    <View style={{ backgroundColor: t.bg, borderRadius: 18, padding: 14 }}>
      <Text style={{ fontFamily: font.medium, fontSize: 14, color: t.fg, lineHeight: 20 }}>{text}</Text>
    </View>
  );
}

export function Bullets({ items, color = colors.inkSoft, dot = colors.sage }: { items: string[]; color?: string; dot?: string }) {
  return (
    <View style={{ gap: 8 }}>
      {items.map((it, i) => (
        <View key={i} style={{ flexDirection: 'row', gap: 10 }}>
          <View style={[s.dot, { backgroundColor: dot, marginTop: 7 }]} />
          <Text style={{ flex: 1, fontFamily: font.regular, fontSize: 15, lineHeight: 21, color }}>{it}</Text>
        </View>
      ))}
    </View>
  );
}

// ---------------------------------------------------------------- screens

/** Stack screen header: round back button and a title. */
export function Header({ title, subtitle, right, onBack }: { title: string; subtitle?: string; right?: ReactNode; onBack?: () => void }) {
  return (
    <View style={s.header}>
      <IconButton icon={ChevronLeft} label="Back" onPress={onBack ?? (() => (router.canGoBack() ? router.back() : router.replace('/')))} />
      <View style={{ flex: 1 }}>
        {subtitle ? <Label style={{ fontSize: 13 }}>{subtitle}</Label> : null}
        <Text style={{ fontFamily: font.medium, fontSize: 22, color: colors.ink }} numberOfLines={1}>{title}</Text>
      </View>
      {right}
    </View>
  );
}

export function StackScreen({ title, subtitle, right, children, footer, scroll = true }: {
  title: string;
  subtitle?: string;
  right?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  scroll?: boolean;
}) {
  const insets = useSafeAreaInsets();
  return (
    <View style={{ flex: 1, backgroundColor: colors.bg, paddingTop: insets.top + 8 }}>
      <Header title={title} subtitle={subtitle} right={right} />
      {scroll ? (
        <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: (footer ? 24 : 40) + insets.bottom, gap: 14 }} keyboardShouldPersistTaps="handled">
          {children}
        </ScrollView>
      ) : (
        <View style={{ flex: 1 }}>{children}</View>
      )}
      {footer ? <View style={[s.footer, { paddingBottom: 12 + insets.bottom }]}>{footer}</View> : null}
    </View>
  );
}

export function Empty({ icon: Icon, title, text, action }: { icon: LucideIcon; title: string; text: string; action?: ReactNode }) {
  return (
    <Card style={{ alignItems: 'center', paddingVertical: 32, gap: 10 }}>
      <View style={{ width: 64, height: 64, borderRadius: 32, backgroundColor: colors.sageMist, alignItems: 'center', justifyContent: 'center' }}>
        <Icon size={28} color={colors.sageDark} strokeWidth={1.6} />
      </View>
      <Text style={{ fontFamily: font.semibold, fontSize: 18, color: colors.ink, textAlign: 'center' }}>{title}</Text>
      <T style={{ textAlign: 'center', color: colors.muted }}>{text}</T>
      {action}
    </Card>
  );
}

// ---------------------------------------------------------------- hooks

/** Run fn now and every `ms` while the screen is focused. */
export function usePoll(fn: () => unknown, ms: number, enabled = true) {
  const ref = useRef(fn);
  useEffect(() => {
    ref.current = fn;
  });
  useFocusEffect(
    useCallback(() => {
      if (!enabled) return;
      ref.current();
      const t = setInterval(() => ref.current(), ms);
      return () => clearInterval(t);
    }, [ms, enabled]),
  );
}

export const s = StyleSheet.create({
  body: { fontFamily: font.regular, fontSize: 15.5, color: colors.inkSoft, lineHeight: 22 },
  label: { fontFamily: font.regular, fontSize: 15, color: colors.muted },
  title: { fontFamily: font.regular, fontSize: 36, color: colors.ink, letterSpacing: -0.8 },
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.card,
    padding: 20,
    borderWidth: 1,
    borderColor: colors.cardEdge,
    shadowColor: '#3D4A38',
    shadowOpacity: 0.06,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 6 },
    elevation: 1,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 6 },
  softShadow: { shadowColor: '#3D4A38', shadowOpacity: 0.08, shadowRadius: 10, shadowOffset: { width: 0, height: 3 }, elevation: 2 },
  badge: { position: 'absolute', top: 10, right: 11, width: 9, height: 9, borderRadius: 5, backgroundColor: colors.heart, borderWidth: 1.5, borderColor: colors.white },
  button: { height: 54, borderRadius: radius.pill, paddingHorizontal: 22, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, borderWidth: 1 },
  chip: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 10, height: 28, borderRadius: radius.pill, alignSelf: 'flex-start' },
  dot: { width: 8, height: 8, borderRadius: 4 },
  segmented: { flexDirection: 'row', backgroundColor: '#E2E5DE', borderRadius: radius.pill, padding: 4 },
  segment: { flex: 1, height: 40, borderRadius: radius.pill, alignItems: 'center', justifyContent: 'center' },
  segmentOn: { backgroundColor: colors.white, shadowColor: '#3D4A38', shadowOpacity: 0.08, shadowRadius: 6, shadowOffset: { width: 0, height: 2 }, elevation: 1 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 14, paddingHorizontal: 20, paddingBottom: 6 },
  footer: { paddingHorizontal: 20, paddingTop: 12, backgroundColor: colors.bg, borderTopWidth: 1, borderTopColor: colors.line },
});
