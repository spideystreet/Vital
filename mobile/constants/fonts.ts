import { Platform } from 'react-native';

/**
 * Native iOS: SF Pro Rounded (system).
 * Web: Open Runde (bundled WOFF2 in public/fonts, loaded via web/open-runde.css).
 * Android: Roboto (system); bundle Open Runde with expo-font if you want parity.
 */
export const fontSans = Platform.select({
  ios: 'SF Pro Rounded',
  android: 'Roboto',
  web: '"Open Runde", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
}) as string;
