import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';
import { ArrowDownRight, ArrowUpRight, CalendarDays, HeartPulse, ScanLine, Sparkles } from 'lucide-react-native';
import { useState, type ReactNode } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { ArcGauge, MiniBars, SparkLine, Waveform } from '@/components/charts';
import { TopBar } from '@/components/chrome';
import { Banner, BigNumber, Button, Card, IconButton, Label, T, Title } from '@/components/ui';
import { caseSummary, effectiveScore, insightsFor, rupees, timeAgo, type Insight } from '@/lib/format';
import { useApp } from '@/lib/store';
import { colors, font, TAB_CLEARANCE, urgencyInfo } from '@/lib/theme';

export default function Overview() {
  const { caseView, caseError, symptom, inbox } = useApp();
  const c = caseView?.kind === 'prescription' ? caseView.case : null;
  const sum = c ? caseSummary(c) : null;
  const openChats = inbox.filter((e) => e.status === 'open').length;

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <ScrollView contentContainerStyle={{ paddingBottom: TAB_CLEARANCE }} showsVerticalScrollIndicator={false}>
        <TopBar />
        <View style={{ paddingHorizontal: 20, gap: 14 }}>
          <View style={{ marginTop: 14, marginBottom: 6 }}>
            <Label>Your medicine safety</Label>
            <Title>Overview Panel</Title>
          </View>

          <InsightCard insights={insightsFor(c ? caseView : null)} />
          {caseError ? <Banner text={caseError} tone="warn" /> : null}

          {c && sum ? (
            <>
              <View style={styles.row}>
                <StatCard
                  label="Read confidence"
                  value={sum.total ? sum.avg.toFixed(0) : '—'}
                  unit="%"
                  up
                  strong={`${sum.high} of ${sum.total}`}
                  rest="confirmed"
                  onPress={() => router.navigate('/report')}
                >
                  <View style={{ alignItems: 'center' }}>
                    <ArcGauge value={sum.avg / 100} width={128} />
                  </View>
                </StatCard>
                <StatCard
                  label="Safety alerts"
                  value={String(c.alerts.length)}
                  unit={c.alerts.length === 1 ? 'alert' : 'alerts'}
                  up={sum.highAlerts === 0}
                  strong={`${sum.highAlerts} high`}
                  rest={`· ${sum.reviewAlerts} review`}
                  onPress={() => router.navigate('/report')}
                >
                  <MiniBars values={c.meds.map((m) => c.alerts.filter((a) => a.meds.includes(m.index)).length / 2)} />
                </StatCard>
              </View>
              <View style={styles.row}>
                <StatCard
                  label="Generic savings"
                  value={rupees(c.savings).replace('₹', '₹ ')}
                  unit="/mo"
                  size={36}
                  up
                  strong="Jan Aushadhi"
                  rest=""
                  onPress={() => router.navigate('/report')}
                >
                  <Waveform values={savingsShape(c.jan_aushadhi.map((j) => (j.generic && j.brand_price ? 1 : 0.25)))} />
                </StatCard>
                <StatCard
                  label="Doctor review"
                  value={String(sum.needsReview)}
                  unit="to confirm"
                  up={sum.needsReview === 0}
                  strong={`${openChats} ${openChats === 1 ? 'chat' : 'chats'}`}
                  rest="open"
                  onPress={() => router.push('/inbox')}
                >
                  <SparkLine
                    values={c.meds.map((m) => effectiveScore(m) / 100)}
                    markIndex={c.meds.reduce((lo, m, i, all) => (effectiveScore(m) < effectiveScore(all[lo]) ? i : lo), 0)}
                  />
                </StatCard>
              </View>
              <Card onPress={() => router.navigate('/report')} style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
                <View style={{ flex: 1 }}>
                  <Label style={{ fontSize: 14 }}>Last check · {timeAgo(caseView!.created_at)}</Label>
                  <Text style={styles.cardTitle} numberOfLines={1}>
                    {c.meds.length} medicines · {c.input_mode === 'photo' ? 'read from a photo' : 'typed'}
                  </Text>
                </View>
                <IconButton icon={ArrowUpRight} label="Open report" onPress={() => router.navigate('/report')} size={44} />
              </Card>
            </>
          ) : (
            <Card style={{ gap: 12 }}>
              <Label>Get started</Label>
              <Text style={[styles.cardTitle, { fontSize: 24 }]}>Check a prescription</Text>
              <T>
                Take a photo of a handwritten prescription or type the medicines. Gemma 4 reads it, our code checks every
                brand against 242k Indian medicines, and a doctor confirms anything unclear.
              </T>
              <Button title="Scan prescription" icon={ScanLine} onPress={() => router.push('/scan')} />
              <Button title="Try the demo case" tone="secondary" onPress={() => router.push({ pathname: '/scan', params: { demo: '1' } })} />
            </Card>
          )}

          <Card onPress={() => router.navigate('/symptoms')} style={{ flexDirection: 'row', alignItems: 'center', gap: 16 }}>
            <View style={{ flex: 1, gap: 4 }}>
              <Label style={{ fontSize: 14 }}>Symptom check</Label>
              {symptom ? (
                <>
                  <Text style={styles.cardTitle}>{urgencyInfo[symptom.triage.urgency].title}</Text>
                  <T numberOfLines={2} style={{ fontSize: 14, color: colors.muted }}>“{symptom.text}”</T>
                </>
              ) : (
                <T style={{ fontSize: 15 }}>Not feeling well? Speak or type how you feel, in English or Hindi.</T>
              )}
            </View>
            <View style={styles.heartDisc}>
              <HeartPulse size={26} color={colors.white} strokeWidth={1.8} />
            </View>
          </Card>
        </View>
      </ScrollView>
    </View>
  );
}

function savingsShape(v: number[]): number[] {
  return v.length ? v.flatMap((x) => [x, x * 0.5, x * 0.8]) : [0.3];
}

function StatCard({ label, value, unit, up, strong, rest, children, onPress, size = 46 }: {
  label: string;
  value: string;
  unit?: string;
  up: boolean;
  strong: string;
  rest: string;
  children: ReactNode;
  onPress?: () => void;
  size?: number;
}) {
  const Arrow = up ? ArrowUpRight : ArrowDownRight;
  return (
    <Card onPress={onPress} style={{ flex: 1, minHeight: 236, padding: 18 }}>
      <Label style={{ fontSize: 14.5 }}>{label}</Label>
      <View style={{ marginTop: 10 }}>
        <BigNumber value={value} unit={unit} size={size} />
      </View>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 3, marginTop: 4, flexWrap: 'wrap' }}>
        <Arrow size={15} color={colors.ink} strokeWidth={2} />
        <Text style={{ fontFamily: font.semibold, fontSize: 13.5, color: colors.ink }}>{strong}</Text>
        <Text style={{ fontFamily: font.regular, fontSize: 13.5, color: colors.muted }}>{rest}</Text>
      </View>
      <View style={{ marginTop: 'auto', paddingTop: 14 }}>{children}</View>
    </Card>
  );
}

const TONE_ICON: Record<Insight['tone'], string> = { alert: '#F6C1CB', review: '#F8D9B9', good: '#D9E8CF', info: '#E7EEE2' };

function InsightCard({ insights }: { insights: Insight[] }) {
  const [w, setW] = useState(0);
  const [page, setPage] = useState(0);
  return (
    <View style={{ marginTop: 4 }}>
      <View style={styles.insightGhost} />
      <LinearGradient colors={['#93A989', '#6D8565']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.insight}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 22, paddingTop: 20 }}>
          <Sparkles size={17} color={colors.white} strokeWidth={1.8} />
          <Text style={{ fontFamily: font.medium, fontSize: 15, color: colors.white, flex: 1 }}>Safety insights</Text>
          <Pressable onPress={() => router.navigate('/report')} hitSlop={10} accessibilityLabel="Open report">
            <ArrowUpRight size={20} color={colors.white} strokeWidth={1.8} />
          </Pressable>
        </View>
        <View style={{ flex: 1 }} onLayout={(e) => setW(e.nativeEvent.layout.width)}>
          {w > 0 ? (
            <ScrollView
              horizontal
              pagingEnabled
              showsHorizontalScrollIndicator={false}
              onMomentumScrollEnd={(e) => setPage(Math.round(e.nativeEvent.contentOffset.x / w))}
              onScroll={(e) => setPage(Math.round(e.nativeEvent.contentOffset.x / w))}
              scrollEventThrottle={32}
            >
              {insights.map((ins, i) => (
                <Pressable
                  key={i}
                  style={{ width: w, paddingHorizontal: 22, paddingTop: 14, flexDirection: 'row', gap: 10 }}
                  onPress={() => (ins.medIndex !== undefined ? router.push(`/medicine/${ins.medIndex}`) : undefined)}
                >
                  <View style={[styles.toneDot, { backgroundColor: TONE_ICON[ins.tone] }]} />
                  <Text style={styles.insightText} numberOfLines={5}>{ins.text}</Text>
                </Pressable>
              ))}
            </ScrollView>
          ) : null}
        </View>
        <View style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 22, paddingBottom: 18, gap: 10 }}>
          <View style={{ flexDirection: 'row', gap: 5, flex: 1 }}>
            {insights.map((_, i) => (
              <View key={i} style={{ height: 4, borderRadius: 2, width: i === page ? 22 : 6, backgroundColor: i === page ? colors.white : 'rgba(255,255,255,0.45)' }} />
            ))}
          </View>
          <IconButton icon={ScanLine} label="Scan a prescription" onPress={() => router.push('/scan')} size={52} />
          <IconButton icon={CalendarDays} label="Dose schedule" onPress={() => router.navigate('/schedule')} size={52} />
        </View>
      </LinearGradient>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 12 },
  cardTitle: { fontFamily: font.medium, fontSize: 19, color: colors.ink, marginTop: 2 },
  heartDisc: { width: 58, height: 58, borderRadius: 29, backgroundColor: colors.sage, alignItems: 'center', justifyContent: 'center' },
  insight: { height: 276, borderRadius: 30, overflow: 'hidden', borderWidth: 1, borderColor: 'rgba(255,255,255,0.35)' },
  insightGhost: { position: 'absolute', top: 14, bottom: 14, right: -8, left: 40, borderRadius: 30, backgroundColor: '#B9C7B1' },
  insightText: { flex: 1, fontFamily: font.light, fontSize: 20.5, lineHeight: 28, color: colors.white },
  toneDot: { width: 10, height: 10, borderRadius: 5, marginTop: 10 },
});
