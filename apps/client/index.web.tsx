import '@expo/metro-runtime';
import { registerRootComponent } from 'expo';
import { LoadSkiaWeb } from '@shopify/react-native-skia/lib/module/web';

async function boot() {
  try {
    await LoadSkiaWeb({ locateFile: (file: string) => `/${file}` });
    const { default: App } = await import('./src/App');
    registerRootComponent(App);
  } catch (error) {
    console.error('Skia failed to initialize; registering functional static fallback.', error);
    const { default: FallbackApp } = await import('./src/FallbackApp');
    registerRootComponent(FallbackApp);
  }
}

void boot();
