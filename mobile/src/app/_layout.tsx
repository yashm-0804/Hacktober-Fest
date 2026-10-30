import {
  Urbanist_200ExtraLight,
  Urbanist_300Light,
  Urbanist_400Regular,
  Urbanist_500Medium,
  Urbanist_600SemiBold,
  Urbanist_700Bold,
  useFonts,
} from '@expo-google-fonts/urbanist';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AppProvider, useApp } from '@/lib/store';
import { colors } from '@/lib/theme';

SplashScreen.preventAutoHideAsync().catch(() => {});

function Root() {
  const { ready } = useApp();
  const [fontsLoaded, fontError] = useFonts({
    Urbanist_200ExtraLight,
    Urbanist_300Light,
    Urbanist_400Regular,
    Urbanist_500Medium,
    Urbanist_600SemiBold,
    Urbanist_700Bold,
  });
  const done = ready && (fontsLoaded || !!fontError);
  useEffect(() => {
    if (done) SplashScreen.hideAsync().catch(() => {});
  }, [done]);
  if (!done) return null;
  return (
    <>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.bg } }}>
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="scan" options={{ presentation: 'modal' }} />
        <Stack.Screen name="analyzing/[job]" options={{ gestureEnabled: false }} />
      </Stack>
    </>
  );
}

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <AppProvider>
        <Root />
      </AppProvider>
    </SafeAreaProvider>
  );
}
