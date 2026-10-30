import { router } from 'expo-router';
import { BedDouble, CalendarDays, Check, Clock, Moon, ScanLine, Sun, Sunrise, Sunset, type LucideIcon } from 'lucide-react-native';
import { useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { ArcGauge } from '@/components/charts';
import { TopBar } from '@/components/chrome';
import { BigNumber, Button, Card, Empty, Label, T, Title } from '@/components/ui';
import { useApp } from '@/lib/store';
import { colors, font, TAB_CLEARANCE } from '@/lib/theme';

const SLOTS: { key: string; icon: LucideIcon; hint: string }[] = [
  { key: 'Morning', icon: Sunrise, hint: 'after breakfast' },
  { key: 'Afternoon', icon: Sun, hint: 'after lunch' },
  { key: 'Evening', icon: Sunset, hint: 'early evening' },
  { key: 'Night', icon: Moon, hint: 'after dinner' },
  { key: 'Bedtime', icon: BedDouble, hint: 'at bedtime' },
  { key: 'As needed', icon: Clock, hint: 'only when needed (SOS)' },
];
const DAY = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

const iso = (d: Date) => `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`;

export default function Schedule() {
  const { caseView, taken, toggleTaken } = useApp();
  const today = useMemo(() => new Date(), []);
  const week = useMemo(() => {
    const start = new Date(today);
    start.setDate(today.getDate() - today.getDay());
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      return d;
    });
  }, [today]);
  const [day, setDay] = useState(iso(today));

  const view = caseView?.kind === 'prescription' ? caseView : null;
  const sched = view?.case.schedule ?? [];
  const key = (medIndex: number, slot: string) => `${view?.id}|${day}|${medIndex}|${slot}`;
  const due = sched.flatMap((s) => s.slots.filter((x) => x !== 'As needed').map((slot) => key(s.index, slot)));
  const done = due.filter((k) => taken[k]).length;
  const unscheduled = sched.filter((s) => !s.slots.length);

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <ScrollView contentContainerStyle={{ paddingBottom: TAB_CLEARANCE }} showsVerticalScrollIndicator={false}>
        <TopBar />
        <View style={{ paddingHorizontal: 20, gap: 14 }}>
          <View style={{ marginTop: 14 }}>
            <Label>{today.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })}</Label>
            <Title>Dose Schedule</Title>
          </View>

          <View style={styles.week}>
            {week.map((d) => {
              const on = iso(d) === day;
              return (
                <Pressable key={iso(d)} onPress={() => setDay(iso(d))} style={[styles.day, on && styles.dayOn]} accessibilityRole="button" accessibilityState={{ selected: on }}>
                  <Text style={[styles.dayName, on && { color: 'rgba(255,255,255,0.85)' }]}>{DAY[d.getDay()]}</Text>
                  <Text style={[styles.dayNum, on && { color: colors.white }]}>{d.getDate()}</Text>
                  {iso(d) === iso(today) ? <View style={[styles.todayDot, on && { backgroundColor: colors.white }]} /> : null}
                </Pressable>
              );
            })}
          </View>

          {!view ? (
            <Empty
              icon={CalendarDays}
              title="No schedule yet"
              text="Check a prescription and AushNexa turns OD, BD, TDS and 1-0-1 into a simple daily plan."
              action={<Button title="Scan prescription" icon={ScanLine} onPress={() => router.push('/scan')} style={{ alignSelf: 'stretch', marginTop: 8 }} />}
            />
          ) : (
            <>
              <Card style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
                <View style={{ flex: 1 }}>
                  <Label style={{ fontSize: 14.5 }}>Doses taken</Label>
                  <BigNumber value={`${done}/${due.length}`} size={52} />
                  <T style={{ fontSize: 14, color: colors.muted }}>Tap a dose to tick it off. Saved on this phone only.</T>
                </View>
                <ArcGauge value={due.length ? done / due.length : 0} width={120} />
              </Card>

              {SLOTS.map((slot) => {
                const items = sched.filter((s) => s.slots.includes(slot.key));
                if (!items.length) return null;
                const Icon = slot.icon;
                return (
                  <Card key={slot.key} style={{ gap: 10 }}>
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
                      <View style={styles.slotIcon}>
                        <Icon size={20} color={colors.sageDeep} strokeWidth={1.8} />
                      </View>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.slotTitle}>{slot.key}</Text>
                        <Text style={styles.muted}>{slot.hint}</Text>
                      </View>
                    </View>
                    {items.map((s) => {
                      const k = key(s.index, slot.key);
                      const on = !!taken[k];
                      return (
                        <Pressable key={k} onPress={() => toggleTaken(k)} style={[styles.dose, on && styles.doseOn]} accessibilityRole="checkbox" accessibilityState={{ checked: on }}>
                          <View style={{ flex: 1 }}>
                            <Text style={[styles.doseName, on && { color: colors.muted, textDecorationLine: 'line-through' }]} numberOfLines={1}>{s.label ?? '?'}</Text>
                            <Text style={styles.muted}>{s.freq || 'frequency not written'}</Text>
                          </View>
                          <View style={[styles.check, on && styles.checkOn]}>{on ? <Check size={16} color={colors.white} strokeWidth={2.5} /> : null}</View>
                        </Pressable>
                      );
                    })}
                  </Card>
                );
              })}

              {unscheduled.length ? (
                <Card style={{ gap: 6 }}>
                  <Label>Ask your doctor how often to take</Label>
                  {unscheduled.map((s) => <T key={s.index}>• {s.label ?? '?'}{s.freq ? ` (${s.freq})` : ''}</T>)}
                </Card>
              ) : null}
            </>
          )}
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  week: { flexDirection: 'row', justifyContent: 'space-between', gap: 6 },
  day: { flex: 1, height: 74, borderRadius: 24, backgroundColor: colors.card, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: colors.cardEdge },
  dayOn: { backgroundColor: colors.sage, borderColor: colors.sage },
  dayName: { fontFamily: font.regular, fontSize: 13, color: colors.muted },
  dayNum: { fontFamily: font.semibold, fontSize: 19, color: colors.ink, marginTop: 2 },
  todayDot: { width: 5, height: 5, borderRadius: 3, backgroundColor: colors.sage, marginTop: 4 },
  slotIcon: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.sageMist, alignItems: 'center', justifyContent: 'center' },
  slotTitle: { fontFamily: font.semibold, fontSize: 17, color: colors.ink },
  muted: { fontFamily: font.regular, fontSize: 13.5, color: colors.muted },
  dose: { flexDirection: 'row', alignItems: 'center', gap: 12, backgroundColor: colors.white, borderRadius: 18, padding: 14 },
  doseOn: { backgroundColor: '#EEF3EA' },
  doseName: { fontFamily: font.medium, fontSize: 15.5, color: colors.ink },
  check: { width: 30, height: 30, borderRadius: 15, borderWidth: 1.5, borderColor: colors.faint, alignItems: 'center', justifyContent: 'center' },
  checkOn: { backgroundColor: colors.sage, borderColor: colors.sage },
});
