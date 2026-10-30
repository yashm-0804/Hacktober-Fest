import type { Band, Case, CaseView, EscalationSummary, Med, Salt } from './api';

export function saltsText(salts: Salt[] | null | undefined): string {
  const parts = (salts ?? []).map((s) => `${s.salt} ${s.strength ?? ''}`.trim()).filter(Boolean);
  return parts.length ? parts.join(' + ') : 'salts unknown';
}

export function rupees(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return '—';
  return `₹${n.toLocaleString('en-IN', { maximumFractionDigits: digits, minimumFractionDigits: digits })}`;
}

export function timeAgo(ts: number): string {
  const s = Math.max(0, Date.now() / 1000 - ts);
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return `${Math.floor(s / 86400)} d ago`;
}

export function clock(ts: number): string {
  const d = new Date(ts * 1000);
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
}

export function shortName(name: string | null | undefined, max = 7): string {
  const first = (name ?? '?').replace(/\s+(tablet|capsule|syrup|suspension)s?\b.*$/i, '').trim();
  return first.length > max ? `${first.slice(0, max - 1)}…` : first;
}

export const isHumanConfirmed = (m: Med) => m.status === 'confirmed_by_doctor' || m.status === 'picked_by_patient';

/** A human decision outranks the code's band. */
export function displayBand(m: Med): Band {
  return isHumanConfirmed(m) ? 'HIGH' : (m.confidence?.band ?? 'LOW');
}

/** Code confidence (0-100); a doctor's or patient's confirmation counts as 100. */
export function effectiveScore(m: Med): number {
  if (isHumanConfirmed(m)) return 100;
  return Math.round((m.confidence?.value ?? 0) * 1000) / 10;
}

export function statusLabel(m: Med, esc?: EscalationSummary): string {
  if (m.status === 'confirmed_by_doctor') return 'Confirmed by doctor';
  if (m.status === 'picked_by_patient') return 'Picked by you';
  if (esc?.status === 'open') return 'Waiting for doctor';
  return { HIGH: 'Auto-matched', MEDIUM: 'Please confirm', LOW: 'Ask a doctor' }[m.confidence?.band ?? 'LOW'];
}

export function escalationFor(view: CaseView | null, medIndex: number): EscalationSummary | undefined {
  const list = (view?.escalations ?? []).filter((e) => e.med_index === medIndex);
  return list.find((e) => e.status === 'open') ?? list[list.length - 1];
}

export function caseSummary(c: Case) {
  const meds = c.meds;
  const scores = meds.map(effectiveScore);
  const avg = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
  const bands = meds.map(displayBand);
  return {
    avg,
    total: meds.length,
    high: bands.filter((b) => b === 'HIGH').length,
    medium: bands.filter((b) => b === 'MEDIUM').length,
    low: bands.filter((b) => b === 'LOW').length,
    needsReview: meds.filter((m) => !isHumanConfirmed(m) && m.confidence?.band !== 'HIGH').length,
    highAlerts: c.alerts.filter((a) => a.severity === 'HIGH').length,
    reviewAlerts: c.alerts.filter((a) => a.severity !== 'HIGH').length,
  };
}

export type Insight = { text: string; tone: 'alert' | 'review' | 'good' | 'info'; medIndex?: number };

/** Plain-language highlights for the Overview card, most important first. */
export function insightsFor(view: CaseView | null): Insight[] {
  if (!view) {
    return [
      { text: 'Scan a prescription. Gemma 4 reads it, then our code checks every medicine for hidden duplicates and allergies.', tone: 'info' },
      { text: 'Not sure what you have? Describe how you feel and get possible causes and how urgent it is.', tone: 'info' },
    ];
  }
  const c = view.case;
  const out: Insight[] = [];
  for (const a of c.alerts) out.push({ text: `${a.title}. ${firstSentence(a.detail)}`, tone: a.severity === 'HIGH' ? 'alert' : 'review' });
  if (c.strip && c.strip.status !== 'MATCH') out.push({ text: `Strip check: ${firstSentence(c.strip.detail)}`, tone: 'alert' });
  for (const m of c.meds) {
    if (isHumanConfirmed(m) || m.confidence?.band === 'HIGH') continue;
    const name = m.read.brand_or_drug || m.read.raw_text;
    out.push({
      text: m.confidence?.band === 'LOW'
        ? `We couldn't read "${name}" confidently. Ask a doctor before you take it.`
        : `"${name}" has a look-alike. Confirm which medicine it is.`,
      tone: 'review',
      medIndex: m.index,
    });
  }
  if (c.savings > 0) out.push({ text: `Jan Aushadhi generics could save you about ${rupees(c.savings)} a month.`, tone: 'good' });
  if (!c.alerts.length && c.meds.length) out.push({ text: 'No alerts from our checks. No alert does not mean safe, so review it with your pharmacist.', tone: 'good' });
  if (!c.meds.length) out.push({ text: 'No medicines could be read. Try a clearer photo, or type the medicines.', tone: 'review' });
  return out;
}

function firstSentence(s: string): string {
  const m = s.match(/^.*?[.!?](\s|$)/);
  return (m ? m[0] : s).trim();
}

/** "Strip read failed: Gemma (gemini/…) failed: RuntimeError: GEMINI_API_KEY is not set" -> one plain sentence. */
export function friendlyErrors(errors: string[]): string {
  const steps = [...new Set(errors.map((e) => e.split(':')[0].replace(/ failed$/i, '').toLowerCase()))];
  const all = errors.join(' ');
  return `Some Gemma 4 steps did not run (${steps.join(', ')}) because ${gemmaReason(all)}. The code safety checks still ran; details are under "How Gemma 4 and code decided".`;
}

export function gemmaReason(error: string): string {
  if (error.includes('GEMINI_API_KEY')) return 'the server has no Gemini API key';
  if (/Ollama not reachable/i.test(error)) return 'local Ollama is not running';
  return 'Gemma 4 did not answer in time';
}

/** Triage error -> one plain sentence about what still ran. */
export function friendlyTriageError(error: string): string {
  return `Gemma 4 could not assess the symptoms (${gemmaReason(error)}), so only the warning-sign rules ran.`;
}
