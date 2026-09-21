const trimTrailingSlashes = (value: string): string => value.replace(/\/+$/, '');

// This is a local-development default for the Android emulator only.
// Physical devices and other runtimes must set EXPO_PUBLIC_API_BASE_URL.
const localAndroidApiUrl = 'http://10.0.2.2:8000/api/v1';

export const API_BASE_URL = trimTrailingSlashes(
  process.env.EXPO_PUBLIC_API_BASE_URL?.trim() || localAndroidApiUrl,
);

// This is safe to show in development diagnostics: credentials and query
// strings are removed if someone accidentally places them in the URL.
export const API_BASE_URL_FOR_DISPLAY = API_BASE_URL
  .replace(/\/\/[^\/@\s]+@/, '//[credentials omitted]@')
  .replace(/[?#].*$/, '');

export const API_TIMEOUT_MS = 10_000;
