import { router } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, TextInput } from 'react-native';

import { Avatar } from '@/components/chrome';
import { Button, Card, CardHeader, Label, StackScreen, T } from '@/components/ui';
import { useApp } from '@/lib/store';
import { colors, font } from '@/lib/theme';

export default function Profile() {
  const { profile, setProfile } = useApp();
  const [name, setName] = useState(profile.name);
  const [conditions, setConditions] = useState(profile.conditions);
  const [allergies, setAllergies] = useState(profile.allergies);

  return (
    <StackScreen
      title="Your profile"
      subtitle="Saved on this phone"
      footer={<Button title="Save" onPress={() => { setProfile({ name: name.trim(), conditions: conditions.trim(), allergies: allergies.trim() }); router.back(); }} />}
    >
      <Card style={{ alignItems: 'center', gap: 10 }}>
        <Avatar size={84} />
        <T style={{ textAlign: 'center', color: colors.muted, fontSize: 14 }}>
          Your conditions and allergies are filled into every new check, so you only type them once.
        </T>
      </Card>
      <Card style={{ gap: 10 }}>
        <CardHeader label="Name" />
        <TextInput value={name} onChangeText={setName} placeholder="e.g. Ramesh K." placeholderTextColor={colors.faint} style={styles.input} />
        <Label style={{ marginTop: 6 }}>Long-term conditions</Label>
        <TextInput value={conditions} onChangeText={setConditions} placeholder="e.g. type 2 diabetes, vitamin D deficiency" placeholderTextColor={colors.faint} multiline style={[styles.input, { minHeight: 80 }]} />
        <Label style={{ marginTop: 6 }}>Allergies</Label>
        <TextInput value={allergies} onChangeText={setAllergies} placeholder="e.g. penicillin, sulfa" placeholderTextColor={colors.faint} style={styles.input} />
      </Card>
    </StackScreen>
  );
}

const styles = StyleSheet.create({
  input: { borderRadius: 18, backgroundColor: colors.white, paddingHorizontal: 16, paddingVertical: 14, fontFamily: font.regular, fontSize: 15.5, color: colors.ink, borderWidth: 1, borderColor: colors.line, textAlignVertical: 'top' },
});
