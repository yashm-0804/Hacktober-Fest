import { Tabs } from 'expo-router';

import { TabBar } from '@/components/chrome';
import { colors } from '@/lib/theme';

export default function TabsLayout() {
  return (
    <Tabs
      tabBar={(props) => <TabBar {...props} />}
      screenOptions={{ headerShown: false, sceneStyle: { backgroundColor: colors.bg } }}
    >
      <Tabs.Screen name="index" />
      <Tabs.Screen name="report" />
      <Tabs.Screen name="symptoms" />
      <Tabs.Screen name="schedule" />
      <Tabs.Screen name="settings" />
    </Tabs>
  );
}
