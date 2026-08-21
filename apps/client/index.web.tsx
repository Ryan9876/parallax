import '@expo/metro-runtime';
import { registerRootComponent } from 'expo';
import { LoadSkiaWeb } from '@shopify/react-native-skia/lib/module/web';

type ParallaxGlobal = typeof globalThis & { __PARALLAX_REDUCED_GRAPHICS__?: boolean };

async function boot() {
  try {
    await LoadSkiaWeb({ locateFile: (file: string) => `/${file}` });
    (globalThis as ParallaxGlobal).__PARALLAX_REDUCED_GRAPHICS__ = false;
    const { default: App } = await import('./src/App');
    registerRootComponent(App);
  } catch (error) {
    console.error('Skia failed to initialize; registering functional static fallback.', error);
    (globalThis as ParallaxGlobal).__PARALLAX_REDUCED_GRAPHICS__ = true;
    const { default: FallbackApp } = await import('./src/FallbackApp');
    registerRootComponent(FallbackApp);
  }
}

void boot();
