import { useState, type ReactNode } from 'react';
import { View, type LayoutChangeEvent } from 'react-native';
import Svg, { Circle, G, Line, Path, Rect, Text as SvgText } from 'react-native-svg';

import { colors, font } from '@/lib/theme';

/** Renders children(width) once the container has been measured. */
function Measured({ height, children }: { height: number; children: (w: number) => ReactNode }) {
  const [w, setW] = useState(0);
  const onLayout = (e: LayoutChangeEvent) => setW(Math.round(e.nativeEvent.layout.width));
  return (
    <View style={{ height, width: '100%' }} onLayout={onLayout}>
      {w > 0 ? children(w) : null}
    </View>
  );
}

function smoothPath(pts: [number, number][]): string {
  if (pts.length < 2) return '';
  const f = (n: number) => n.toFixed(1);
  let d = `M ${f(pts[0][0])} ${f(pts[0][1])}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] ?? pts[i];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[i + 2] ?? p2;
    const c1x = p1[0] + (p2[0] - p0[0]) / 6;
    const c1y = p1[1] + (p2[1] - p0[1]) / 6;
    const c2x = p2[0] - (p3[0] - p1[0]) / 6;
    const c2y = p2[1] - (p3[1] - p1[1]) / 6;
    d += ` C ${f(c1x)} ${f(c1y)} ${f(c2x)} ${f(c2y)} ${f(p2[0])} ${f(p2[1])}`;
  }
  return d;
}

const clamp01 = (v: number) => Math.max(0, Math.min(1, v));

// ---------------------------------------------------------------- step chart (Report)

export type StepPoint = { label: string; value: number; color: string };

/** One step per medicine: hatched column up to its score, capped with its band colour. */
export function StepChart({ points, height = 220 }: { points: StepPoint[]; height?: number }) {
  return (
    <Measured height={height}>
      {(w) => {
        const axisW = 34;
        const top = 10;
        const bottom = 30;
        const plotH = height - top - bottom;
        const plotW = w - axisW - 4;
        const y = (v: number) => top + plotH * (1 - Math.max(0, Math.min(100, v)) / 100);
        const n = Math.max(points.length, 1);
        const sw = plotW / n;
        const maxChars = Math.max(3, Math.floor(sw / 7.5));
        return (
          <Svg width={w} height={height}>
            {[100, 75, 50, 25, 0].map((t) => (
              <G key={t}>
                <SvgText x={0} y={y(t) + 4} fontSize={12.5} fill={colors.muted} fontFamily={font.regular}>{t}</SvgText>
                {t > 0 ? (
                  <Line x1={axisW} x2={w} y1={y(t)} y2={y(t)} stroke={t === 100 ? colors.faint : colors.line} strokeDasharray="3 4" strokeWidth={1} />
                ) : null}
              </G>
            ))}
            {points.map((p, i) => {
              const x0 = axisW + i * sw;
              const x1 = x0 + sw;
              const vy = y(p.value);
              const hatch = [];
              for (let x = x0 + 4; x < x1 - 2; x += 4) {
                hatch.push(<Line key={x} x1={x} x2={x} y1={vy + 4} y2={y(0)} stroke={colors.hatch} strokeWidth={1} />);
              }
              const next = points[i + 1];
              const label = p.label.length > maxChars ? `${p.label.slice(0, maxChars - 1)}…` : p.label;
              return (
                <G key={i}>
                  {hatch}
                  <Line x1={x0 + 2} x2={x1 - 2} y1={vy} y2={vy} stroke={p.color} strokeWidth={3} strokeLinecap="round" />
                  {next ? <Line x1={x1} x2={x1} y1={vy} y2={y(next.value)} stroke={colors.faint} strokeDasharray="2 3" strokeWidth={1} /> : null}
                  <SvgText x={(x0 + x1) / 2} y={height - 8} fontSize={12.5} fill={colors.muted} textAnchor="middle" fontFamily={font.regular}>
                    {label}
                  </SvgText>
                </G>
              );
            })}
          </Svg>
        );
      }}
    </Measured>
  );
}

// ---------------------------------------------------------------- arc gauge (Activity progress)

export function ArcGauge({ value, width = 150, stroke = 14, color = colors.sageLight, track = colors.faint }: {
  value: number;
  width?: number;
  stroke?: number;
  color?: string;
  track?: string;
}) {
  const r = (width - stroke) / 2;
  const cx = width / 2;
  const cy = r + stroke / 2;
  const d = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;
  const len = Math.PI * r;
  const v = clamp01(value);
  return (
    <Svg width={width} height={cy + stroke / 2}>
      <Path d={d} stroke={track} strokeWidth={2} strokeDasharray="1 6" strokeLinecap="round" fill="none" />
      {v > 0 ? (
        <Path d={d} stroke={color} strokeWidth={stroke} strokeLinecap="round" fill="none" strokeDasharray={`${len * v} ${len}`} />
      ) : null}
    </Svg>
  );
}

// ---------------------------------------------------------------- mini bars (Blood pressure)

export function MiniBars({ values, height = 56, color = '#9AA096' }: { values: number[]; height?: number; color?: string }) {
  const bars = values.length ? values : [0];
  return (
    <Measured height={height}>
      {(w) => {
        const slot = w / (bars.length * 2);
        return (
          <Svg width={w} height={height}>
            {bars.map((v, i) => {
              const h = Math.max(6, clamp01(v) * height);
              const x = slot * (i * 2 + 0.5);
              return (
                <G key={i}>
                  <Rect x={x} y={height - h} width={4} height={h} rx={2} fill={v > 0.66 ? colors.inkSoft : color} />
                  <Circle cx={x + slot + 2} cy={height - 3} r={2} fill={colors.faint} />
                </G>
              );
            })}
          </Svg>
        );
      }}
    </Measured>
  );
}

// ---------------------------------------------------------------- waveform (Resting heart)

export function Waveform({ values, height = 52, color = '#9AA096' }: { values: number[]; height?: number; color?: string }) {
  return (
    <Measured height={height}>
      {(w) => {
        const count = Math.floor(w / 7);
        const src = values.length ? values : [0.3];
        return (
          <Svg width={w} height={height}>
            {Array.from({ length: count }, (_, i) => {
              const v = src[i % src.length] * (0.55 + 0.45 * Math.abs(Math.sin(i * 1.7)));
              const h = Math.max(4, clamp01(v) * height);
              return <Rect key={i} x={i * 7} y={(height - h) / 2} width={3} height={h} rx={1.5} fill={i % 3 === 0 ? colors.inkSoft : color} />;
            })}
          </Svg>
        );
      }}
    </Measured>
  );
}

// ---------------------------------------------------------------- sparkline (Sleep quality)

export function SparkLine({ values, height = 52, markIndex }: { values: number[]; height?: number; markIndex?: number }) {
  return (
    <Measured height={height}>
      {(w) => {
        const src = values.length > 1 ? values : [0.5, values[0] ?? 0.5];
        const pts: [number, number][] = src.map((v, i) => [4 + (i * (w - 8)) / (src.length - 1), 6 + (1 - clamp01(v)) * (height - 12)]);
        const m = pts[Math.min(markIndex ?? pts.length - 1, pts.length - 1)];
        return (
          <Svg width={w} height={height}>
            <Path d={smoothPath(pts)} stroke={colors.inkSoft} strokeWidth={1.4} fill="none" />
            <Circle cx={m[0]} cy={m[1]} r={9} fill="none" stroke={colors.faint} strokeWidth={1} />
            <Circle cx={m[0]} cy={m[1]} r={4} fill={colors.white} stroke={colors.inkSoft} strokeWidth={1.4} />
          </Svg>
        );
      }}
    </Measured>
  );
}

// ---------------------------------------------------------------- concentric arcs (Lab results)

export function ConcentricArcs({ rings, width = 260, thickness = 16, gap = 5 }: {
  rings: { value: number; color: string }[];
  width?: number;
  thickness?: number;
  gap?: number;
}) {
  const outer = (width - thickness) / 2;
  const cy = outer + thickness / 2;
  return (
    <Svg width={width} height={cy + 2}>
      {rings.map((ring, i) => {
        const r = outer - i * (thickness + gap);
        if (r <= thickness) return null;
        const cx = width / 2;
        const d = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;
        const len = Math.PI * r;
        return (
          <G key={i}>
            <Path d={d} stroke={colors.line} strokeWidth={thickness} fill="none" opacity={0.6} />
            <Path d={d} stroke={ring.color} strokeWidth={thickness} fill="none" strokeDasharray={`${len * clamp01(ring.value)} ${len}`} />
          </G>
        );
      })}
    </Svg>
  );
}

// ---------------------------------------------------------------- live wave line (Symptom check)

/** White line across the green screen, with a centre marker like the design's heart-rate trace. */
export function WaveLine({ values, height = 190, label }: { values: number[]; height?: number; label?: string }) {
  return (
    <Measured height={height}>
      {(w) => {
        const src = values.length > 1 ? values : [0.5, 0.5];
        const pts: [number, number][] = src.map((v, i) => [(i * w) / (src.length - 1), 24 + (1 - clamp01(v)) * (height - 60)]);
        const mid = pts[Math.floor(pts.length / 2)];
        return (
          <Svg width={w} height={height}>
            {Array.from({ length: 9 }, (_, i) => (
              <Line key={i} x1={w - 10} x2={w} y1={20 + i * ((height - 40) / 8)} y2={20 + i * ((height - 40) / 8)} stroke="rgba(255,255,255,0.45)" strokeWidth={1} />
            ))}
            <Line x1={w / 2} x2={w / 2} y1={0} y2={height} stroke="rgba(255,255,255,0.55)" strokeWidth={1} strokeDasharray={label ? undefined : '3 4'} />
            <Path d={smoothPath(pts)} stroke="rgba(255,255,255,0.9)" strokeWidth={1.6} fill="none" />
            <Circle cx={w / 2} cy={mid[1]} r={11} fill="rgba(255,255,255,0.25)" />
            <Circle cx={w / 2} cy={mid[1]} r={6} fill={colors.white} />
          </Svg>
        );
      }}
    </Measured>
  );
}
