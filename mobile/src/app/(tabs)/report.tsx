import { router } from 'expo-router';
import { ArrowUpRight, ChevronDown, ChevronRight, ChevronUp, FileText, Languages, ScanLine } from 'lucide-react-native';
import { useState } from 'react';
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import { ConcentricArcs, StepChart } from '@/components/charts';
import { TopBar } from '@/components/chrome';
import { Banner, BigNumber, Button, Card, CardHeader, Chip, Empty, Label, LegendDot, T } from '@/components/ui';
import type { JanAushadhi, SafetyAlert, StripResult } from '@/lib/api';
import { caseSummary, displayBand, effectiveScore, escalationFor, friendlyErrors, rupees, saltsText, shortName, statusLabel, timeAgo } from '@/lib/format';
import { useApp } from '@/lib/store';
import { bandTone, colors, font, severityTone, TAB_CLEARANCE } from '@/lib/theme';

const RING_COLORS = [colors.sageLight, colors.peach, colors.rose, colors.sky];

export default function Report() {
  const { caseView, refreshCase } = useApp();
  const [refreshing, setRefreshing] = useState(false);
  const view = caseView?.kind === 'prescription' ? caseView : null;

  const onRefresh = async () => {
    setRefreshing(true);
    await refreshCase();
    setRefreshing(false);
  };

  if (!view) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.bg }}>
        <TopBar />
        <View style={{ padding: 20 }}>
          <Empty
            icon={FileText}
            title="No report yet"
            text="Scan or type a prescription to see the medicines, safety alerts, dose schedule and cheaper generics."
            action={<Button title="Scan prescription" icon={ScanLine} onPress={() => router.push('/scan')} style={{ alignSelf: 'stretch', marginTop: 8 }} />}
          />
        </View>
      </View>
    );
  }

  const c = view.case;
  const sum = caseSummary(c);
  const ja = c.jan_aushadhi.filter((j) => j.generic);

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
      <ScrollView
        contentContainerStyle={{ paddingBottom: TAB_CLEARANCE }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.sage} />}
        showsVerticalScrollIndicator={false}
      >
        <TopBar />
        <View style={{ paddingHorizontal: 20, gap: 14, marginTop: 8 }}>
          {c.errors.length ? <Banner tone="warn" text={friendlyErrors(c.errors)} /> : null}

          <Card>
            <CardHeader label="Prescription read score" icon={ScanLine} onIcon={() => router.push('/scan')} />
            <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 12, flexWrap: 'wrap' }}>
              <BigNumber value={sum.total ? sum.avg.toFixed(1) : '—'} unit="%" size={68} />
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4, marginBottom: 14 }}>
                <ArrowUpRight size={16} color={colors.ink} strokeWidth={2} />
                <Text style={styles.strong}>{sum.high} of {sum.total}</Text>
                <Text style={styles.muted}>confirmed</Text>
              </View>
            </View>
            <View style={styles.legend}>
              <LegendDot color={colors.green} label="High" />
              <LegendDot color={colors.peach} label="Confirm" />
              <LegendDot color={colors.rose} label="Ask a doctor" />
            </View>
            {c.meds.length ? (
              <View style={{ marginTop: 18 }}>
                <StepChart points={c.meds.map((m) => ({ label: shortName(c.resolved[m.index]?.label ?? m.read.brand_or_drug, 14), value: effectiveScore(m), color: bandTone[displayBand(m)].dot }))} />
              </View>
            ) : (
              <T style={{ marginTop: 12 }}>No medicines could be read. Try a clearer photo, or type the medicines.</T>
            )}
            <Text style={[styles.muted, { marginTop: 6, fontSize: 12.5 }]}>
              Checked {timeAgo(view.created_at)}{c.elapsed ? ` in ${c.elapsed.toFixed(1)} s` : ''}{c.rechecked ? ' · re-checked after a confirmation' : ''}
            </Text>
          </Card>

          {c.meds.length ? (
            <Card style={{ paddingHorizontal: 0, paddingBottom: 6 }}>
              <View style={{ paddingHorizontal: 20 }}>
                <CardHeader label="Medicines" />
              </View>
              {c.meds.map((m, i) => {
                const r = c.resolved[m.index];
                const band = displayBand(m);
                const tone = bandTone[band];
                const esc = escalationFor(view, m.index);
                return (
                  <Pressable key={m.index} onPress={() => router.push(`/medicine/${m.index}`)} style={({ pressed }) => [styles.medRow, i > 0 && styles.medDivider, pressed && { backgroundColor: '#F0F2EE' }]}>
                    <View style={[styles.indexBubble, { backgroundColor: tone.soft }]}>
                      <Text style={{ fontFamily: font.semibold, color: tone.ink }}>{m.index + 1}</Text>
                    </View>
                    <View style={{ flex: 1, gap: 3 }}>
                      <Text style={styles.medName} numberOfLines={1}>{r?.label ?? m.read.brand_or_drug}</Text>
                      <Text style={styles.muted} numberOfLines={1}>{saltsText(r?.salts)}</Text>
                      <Text style={styles.raw} numberOfLines={1}>Written: “{m.read.raw_text}”</Text>
                      <Chip label={statusLabel(m, esc)} dot={tone.dot} ink={tone.ink} soft={tone.soft} style={{ marginTop: 4 }} />
                    </View>
                    <ChevronRight size={18} color={colors.faint} />
                  </Pressable>
                );
              })}
            </Card>
          ) : null}

          <Card style={{ gap: 12 }}>
            <CardHeader label="Safety alerts" />
            {c.alerts.length ? c.alerts.map((a, i) => <AlertRow key={i} alert={a} />) : (
              <Banner tone="info" text="No alerts from our checks. No alert does not mean safe: please review with your doctor or pharmacist." />
            )}
          </Card>

          <StripCard strip={c.strip} label={c.strip_resolved?.label} strength={c.strip_resolved?.strength} readFailed={c.errors.some((e) => e.startsWith('Strip read failed'))} />

          <Card>
            <CardHeader label="Jan Aushadhi generics" />
            <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 10, flexWrap: 'wrap' }}>
              <BigNumber value={rupees(c.savings)} unit="/ month" size={58} />
              <Text style={[styles.muted, { marginBottom: 12 }]}>could be saved</Text>
            </View>
            {ja.length ? (
              <>
                <View style={[styles.legend, { marginTop: 4 }]}>
                  {ja.slice(0, 4).map((j, i) => <LegendDot key={j.index} color={RING_COLORS[i]} label={shortName(j.brand, 12)} />)}
                </View>
                <View style={{ alignItems: 'center', marginTop: 18 }}>
                  <ConcentricArcs rings={ja.slice(0, 4).map((j, i) => ({ value: savingFraction(j), color: RING_COLORS[i] }))} />
                  <Text style={[styles.muted, { fontSize: 12.5, marginTop: 6 }]}>Ring = share of the brand price you save per tablet</Text>
                </View>
              </>
            ) : null}
            <View style={{ marginTop: 14, gap: 10 }}>
              {c.jan_aushadhi.map((j) => (
                <View key={j.index} style={styles.genericRow}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.genericBrand} numberOfLines={1}>{j.brand ?? '?'}</Text>
                    <Text style={styles.muted} numberOfLines={1}>{j.generic ? `→ ${j.generic.generic_name}` : 'No Jan Aushadhi match in our list'}</Text>
                  </View>
                  <View style={{ alignItems: 'flex-end' }}>
                    <Text style={styles.strong}>{rupees(j.brand_price)}</Text>
                    {j.generic ? <Text style={[styles.muted, { color: colors.greenInk }]}>{rupees(j.generic.price)} generic</Text> : null}
                  </View>
                </View>
              ))}
            </View>
            <Text style={[styles.muted, { fontSize: 12.5, marginTop: 12 }]}>Indicative prices; verify at janaushadhi.gov.in.</Text>
          </Card>

          <Card style={{ gap: 8 }}>
            <CardHeader label="Hindi summary · हिंदी सारांश" right={<Languages size={18} color={colors.muted} />} />
            <Text style={{ fontFamily: font.regular, fontSize: 17, lineHeight: 27, color: colors.ink }}>{c.hindi_summary || 'Not available.'}</Text>
          </Card>

          <TraceCard steps={c._trace} rechecked={!!c.rechecked} />

          <Text style={[styles.muted, { textAlign: 'center', paddingHorizontal: 10, fontSize: 12.5 }]}>
            Supports medication review only. No alert does not mean safe. Not a substitute for a doctor or pharmacist.
          </Text>
        </View>
      </ScrollView>
    </View>
  );
}

function packCount(pack: string | null): number | null {
  if (!pack || /\d+\s*(ml|gm|g)\b/i.test(pack)) return null;
  const m = pack.match(/(\d+)/);
  return m && Number(m[1]) > 0 ? Number(m[1]) : null;
}

/** Fraction of the per-unit brand price saved by the generic (0 when unknown). */
function savingFraction(j: JanAushadhi): number {
  if (!j.generic || !j.brand_price) return 0;
  const brandUnit = j.brand_price / (packCount(j.brand_pack) ?? 1);
  const genericUnit = j.generic.price / (j.generic.units || 10);
  return brandUnit > 0 ? Math.max(0, 1 - genericUnit / brandUnit) : 0;
}

function AlertRow({ alert }: { alert: SafetyAlert }) {
  const tone = severityTone[alert.severity];
  return (
    <View style={[styles.alert, { borderLeftColor: tone.dot }]}>
      <View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>
        <Chip label={tone.label} dot={tone.dot} ink={tone.ink} soft={tone.soft} />
        <Chip label={alert.type.replace('_', ' ').toLowerCase()} ink={colors.inkSoft} soft="#E8EBE5" />
      </View>
      <Text style={[styles.medName, { marginTop: 8 }]}>{alert.title}</Text>
      <T style={{ marginTop: 4, fontSize: 14.5 }}>{alert.detail}</T>
    </View>
  );
}

const STRIP_TONE: Record<StripResult['status'], { label: string; dot: string; ink: string; soft: string }> = {
  MATCH: { label: 'Match', dot: colors.green, ink: colors.greenInk, soft: '#E3EEDC' },
  MISMATCH: { label: 'Mismatch', dot: colors.rose, ink: colors.roseInk, soft: '#FBE1E6' },
  NOT_PRESCRIBED: { label: 'Not prescribed', dot: colors.rose, ink: colors.roseInk, soft: '#FBE1E6' },
  ERROR: { label: 'Could not check', dot: colors.faint, ink: colors.inkSoft, soft: '#E8EBE5' },
};

function StripCard({ strip, label, strength, readFailed }: { strip: StripResult | null; label?: string | null; strength?: string | null; readFailed: boolean }) {
  return (
    <Card style={{ gap: 10 }}>
      <CardHeader label="Strip check" />
      {strip ? (
        <>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
            <Chip {...STRIP_TONE[strip.status]} />
            <Text style={styles.medName}>{label ?? '?'} {strength ?? ''}</Text>
          </View>
          <T style={{ fontSize: 14.5 }}>{strip.detail}</T>
        </>
      ) : readFailed ? (
        <T style={{ color: colors.muted, fontSize: 14.5 }}>
          The strip photo could not be read this time, so it was not compared. Check it against the prescription with your pharmacist.
        </T>
      ) : (
        <T style={{ color: colors.muted, fontSize: 14.5 }}>
          No strip photo added. Add a photo of the strip or box the pharmacy gave you to check it against the prescription.
        </T>
      )}
    </Card>
  );
}

function TraceCard({ steps, rechecked }: { steps: { step: string; model: string; backend: string; seconds: number; cache_hit: boolean; error: string | null }[]; rechecked: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <Card>
      <Pressable onPress={() => setOpen(!open)} style={{ flexDirection: 'row', alignItems: 'center' }} accessibilityRole="button">
        <Label style={{ flex: 1 }}>How Gemma 4 and code decided</Label>
        {open ? <ChevronUp size={20} color={colors.muted} /> : <ChevronDown size={20} color={colors.muted} />}
      </Pressable>
      {open ? (
        <View style={{ marginTop: 12, gap: 10 }}>
          {steps.map((t, i) => (
            <View key={i} style={styles.traceRow}>
              <View style={[styles.traceDot, { backgroundColor: t.error ? colors.rose : t.backend === 'python' || t.backend === 'code' ? colors.sky : colors.sage }]} />
              <View style={{ flex: 1 }}>
                <Text style={{ fontFamily: font.medium, fontSize: 14, color: colors.ink }}>{t.step}</Text>
                <Text style={[styles.muted, { fontSize: 12.5 }]}>
                  {t.model} · {t.seconds}s{t.cache_hit ? ' · cached' : ''}
                </Text>
                {t.error ? <Text style={{ fontFamily: font.regular, fontSize: 12.5, color: colors.roseInk }}>{t.error}</Text> : null}
              </View>
            </View>
          ))}
          {rechecked ? <T style={{ fontSize: 13, color: colors.muted }}>After a confirmation, only the code checks re-ran. No new Gemma call.</T> : null}
        </View>
      ) : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  strong: { fontFamily: font.semibold, fontSize: 14.5, color: colors.ink },
  muted: { fontFamily: font.regular, fontSize: 14, color: colors.muted },
  legend: { flexDirection: 'row', flexWrap: 'wrap', gap: 16, marginTop: 6 },
  medRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 14, paddingHorizontal: 20, paddingVertical: 14 },
  medDivider: { borderTopWidth: 1, borderTopColor: colors.line },
  indexBubble: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center', marginTop: 2 },
  medName: { fontFamily: font.semibold, fontSize: 16, color: colors.ink },
  raw: { fontFamily: font.regular, fontSize: 13, color: colors.faint, fontStyle: 'italic' },
  alert: { backgroundColor: colors.white, borderRadius: 18, padding: 14, borderLeftWidth: 5 },
  genericRow: { flexDirection: 'row', alignItems: 'center', gap: 12, backgroundColor: colors.white, borderRadius: 16, padding: 12 },
  genericBrand: { fontFamily: font.semibold, fontSize: 15, color: colors.ink },
  traceRow: { flexDirection: 'row', gap: 10 },
  traceDot: { width: 8, height: 8, borderRadius: 4, marginTop: 6 },
});
