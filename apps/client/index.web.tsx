import '@expo/metro-runtime';
import { registerRootComponent } from 'expo';
import { LoadSkiaWeb } from '@shopify/react-native-skia/lib/module/web';
import App from './src/App';

LoadSkiaWeb({ locateFile: (file: string) => `/${file}` })
  .then(() => registerRootComponent(App))
  .catch((error) => {
    console.error('Skia failed to initialize; registering static fallback.', error);
    registerRootComponent(App);
  });
