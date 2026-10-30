import { CircleCheck, CircleX, FlaskConical } from 'lucide-react-native';
import { useState } from 'react';
import { Text, View } from 'react-native';

import { Banner, BigNumber, Button, Card, Label, StackScreen, T } from '@/components/ui';
import { api, type TestLab as Lab } from '@/lib/api';
import { colors, font } from '@/lib/theme';

export default function TestLab() {
  const [lab, setLab] = useState<Lab | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setRunning(true);
    setError(null);
    try {
      setLab(await api.testlab());
    } catch (e) {
      setError((e as Error).message);
    }
    setRunning(false);
  }

  return (
    <StackScreen title="Safety Test Lab" subtitle="Deterministic checks" footer={<Button title={lab ? 'Run again' : 'Run the safety cases'} icon={FlaskConical} onPress={run} loading={running} />}>
      <Card style={{ gap: 6 }}>
        <Label>Cases passed</Label>
        <BigNumber value={lab ? `${lab.passed}/${lab.total}` : '—'} size={64} />
        <T style={{ fontSize: 14, color: colors.muted }}>
          Preset regimens built from real Indian brands, run through the same duplicate and allergy checks as every prescription. No AI involved.
        </T>
      </Card>
      {error ? <Banner text={error} /> : null}
      {lab?.results.map((r) => (
        <Card key={r.case} style={{ gap: 8 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
            {r.passed ? <CircleCheck size={22} color={colors.greenInk} /> : <CircleX size={22} color={colors.roseInk} />}
            <Text style={{ flex: 1, fontFamily: font.semibold, fontSize: 16, color: colors.ink }}>{r.case}</Text>
          </View>
          <T style={{ fontSize: 14 }}><Text style={{ fontFamily: font.semibold }}>Expected: </Text>{r.expected}</T>
          <T style={{ fontSize: 14, color: colors.muted }}><Text style={{ fontFamily: font.semibold }}>Got: </Text>{r.got}</T>
        </Card>
      ))}
    </StackScreen>
  );
}
