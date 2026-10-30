# AushNexa mobile app

The patient and doctor app for AushNexa, built with **Expo SDK 58**, React Native 0.88 and Expo Router. It runs on iOS and Android (in Expo Go or as a native build) and on the web for quick previews. It talks to the FastAPI backend in [`../backend`](../backend).

## Run it

Start the backend first (see the [root README](../README.md#quick-start)), then:

```bash
npm install
```

```bash
npx expo start
```

- **Phone:** scan the QR code with Expo Go. The phone must be on the same Wi-Fi as the computer.
- **Web preview:** press `w`.
- **Android emulator / iOS simulator:** press `a` / `i`.

### Finding the backend

The app looks for the API in this order:

1. `EXPO_PUBLIC_API_URL`, if set (for example, `EXPO_PUBLIC_API_URL=http://192.168.1.10:8000 npx expo start`).
2. The Expo dev server's LAN address on port 8000. In Expo Go this works with no setup.
3. On the web, the page's own host on port 8000.

You can change the address any time in **Settings → AushNexa server**, then tap *Save and test*.

## Screens

The visual language follows the design reference: sage greens on warm stone, oversized thin numerals, soft 28 px cards, round icon buttons and a floating pill tab bar. The symptom check uses the immersive green layout with the pulsing heart.

| Route | Screen |
|---|---|
| `(tabs)/index` | **Overview Panel**: swipeable safety insights and four stat cards (read confidence arc, alerts, generic savings waveform, doctor review sparkline) |
| `(tabs)/report` | **Report**: read score with a per-medicine step chart, medicines, alerts, strip check, Jan Aushadhi generics (concentric arcs), Hindi summary, pipeline trace |
| `(tabs)/symptoms` | **Symptom check**: tap the heart to record (live voice line), or type; urgency, warning signs, possible causes, *Call 108*, *Hospitals near me*, *Ask a doctor* |
| `(tabs)/schedule` | **Dose schedule**: week strip plus Morning / Afternoon / Night / Bedtime / As-needed doses to tick off |
| `(tabs)/settings` | Server address, Gemma 4 backend (Gemini API or local Ollama), profile, Doctor Console, Test Lab |
| `scan` | **New check**: patient context, prescription photo or typed lines, optional strip photo, demo case |
| `analyzing/[job]` | Live progress of the analysis job, step by step |
| `medicine/[index]` | Why this confidence, candidates with Gemma 4's fit notes, pick one, ask a doctor |
| `chat/[id]` | Patient ↔ doctor chat (polls every 3 s) |
| `inbox` | The bell: your doctor chats, with an unread dot |
| `profile` | Name, conditions and allergies, pre-filled into each check |
| `doctor/index`, `doctor/[id]` | **Doctor Console**: the question queue, then the case (photo, read, context, confidence, candidates) and the chat, with one-tap confirmation |
| `testlab` | Runs the backend's preset safety cases |

## Code layout

```
src/app/          routes (Expo Router)
src/components/   ui.tsx (cards, buttons, chips), charts.tsx (SVG charts), chrome.tsx (logo, top bar,
                  tab bar, green backdrop, pulse button), ChatThread.tsx
src/lib/          api.ts (typed client), store.tsx (app state, persisted with AsyncStorage),
                  theme.ts (colours, fonts), format.ts (labels, insights, summaries)
```

State that should survive a restart (server address, profile, current case, last symptom check, ticked doses) is stored on the device with AsyncStorage. Everything else comes from the API.

## Checks

```bash
npm run typecheck
```

```bash
npm run lint
```

## Native builds

The app uses only modules that ship in Expo Go (expo-audio, expo-image-picker, expo-blur, expo-linear-gradient, react-native-svg), so no development build is needed while developing. For store builds, use EAS (`npx eas-cli@latest build`). Android blocks plain `http://` in release builds, so serve the API over HTTPS, or allow cleartext traffic with the `expo-build-properties` plugin for an internal test build.
