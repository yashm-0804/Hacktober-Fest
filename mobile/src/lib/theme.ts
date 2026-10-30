import type { Band, Severity, Urgency } from './api';

/** Sage, stone and soft accent colours taken from the design reference. */
export const colors = {
  bg: '#ECEEE9',
  card: '#F7F8F5',
  cardEdge: 'rgba(255,255,255,0.95)',
  white: '#FFFFFF',
  ink: '#151714',
  inkSoft: '#3B3E39',
  muted: '#7D817A',
  faint: '#B6BAB2',
  line: '#DDE0D9',
  hatch: '#DADDD6',

  sage: '#7C9871',
  sageDark: '#5E7A55',
  sageDeep: '#465E40',
  sageLight: '#A8BC9E',
  sageMist: '#DCE5D6',

  green: '#86AE76',
  greenInk: '#456F37',
  peach: '#F2B27C',
  peachInk: '#99520F',
  rose: '#EC8597',
  roseInk: '#B0344C',
  sky: '#8FB0CF',
  skyInk: '#2F5B85',
  heart: '#E04A5F',
};

export const font = {
  thin: 'Urbanist_200ExtraLight',
  light: 'Urbanist_300Light',
  regular: 'Urbanist_400Regular',
  medium: 'Urbanist_500Medium',
  semibold: 'Urbanist_600SemiBold',
  bold: 'Urbanist_700Bold',
};

export const radius = { card: 28, pill: 999 };

/** Bottom padding so content clears the floating tab bar. */
export const TAB_CLEARANCE = 120;

type Tone = { dot: string; ink: string; soft: string; label: string };

/** Colour is always paired with a text label, never used alone. */
export const bandTone: Record<Band, Tone> = {
  HIGH: { dot: colors.green, ink: colors.greenInk, soft: '#E3EEDC', label: 'High confidence' },
  MEDIUM: { dot: colors.peach, ink: colors.peachInk, soft: '#FBEBDC', label: 'Please confirm' },
  LOW: { dot: colors.rose, ink: colors.roseInk, soft: '#FBE1E6', label: 'Ask a doctor' },
};

export const severityTone: Record<Severity, Tone> = {
  HIGH: { dot: colors.rose, ink: colors.roseInk, soft: '#FBE1E6', label: 'High' },
  REVIEW: { dot: colors.peach, ink: colors.peachInk, soft: '#FBEBDC', label: 'Review' },
  INFO: { dot: colors.sky, ink: colors.skyInk, soft: '#E2ECF5', label: 'Info' },
};

export const urgencyInfo: Record<Urgency, { title: string; action: string; dot: string }> = {
  EMERGENCY: { title: 'Emergency', action: 'Call 108 (ambulance) or 112 now', dot: colors.rose },
  URGENT: { title: 'Urgent', action: 'See a doctor today', dot: colors.peach },
  SEE_DOCTOR: { title: 'See a doctor', action: 'Book a visit in the next day or two', dot: '#F4D27C' },
  SELF_CARE: {
    title: 'Self-care',
    action: 'Home care is likely enough for now. See a doctor if it gets worse or lasts over 3 days',
    dot: colors.green,
  },
};
