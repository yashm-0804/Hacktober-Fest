import type { ReactNode } from 'react';

/** On iOS and Android the app fills the screen. The browser version lives in WebFrame.web.tsx. */
export function WebFrame({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
