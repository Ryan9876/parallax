import '@expo/metro-runtime';
import './src/web/installMobileViewportGuard';
import './src/web/installLiveEdgeGuard';
import React from 'react';
import { registerRootComponent } from 'expo';
import { LoadSkiaWeb } from '@shopify/react-native-skia/lib/module/web';
import WebAuthRoot from './src/WebAuthRoot';
import { ProjectCompatibilityGate } from './src/components/ProjectCompatibilityGate';

type ParallaxGlobal = typeof globalThis & { __PARALLAX_REDUCED_GRAPHICS__?: boolean };

function register(AppComponent: React.ComponentType) {
  function ProjectAwareApp() {
    return (
      <ProjectCompatibilityGate>
        <AppComponent />
      </ProjectCompatibilityGate>
    );
  }

  function Root() {
    return <WebAuthRoot AppComponent={ProjectAwareApp} />;
  }
  registerRootComponent(Root);
}

async function boot() {
  try {
    await LoadSkiaWeb({ locateFile: (file: string) => `/${file}` });
    (globalThis as ParallaxGlobal).__PARALLAX_REDUCED_GRAPHICS__ = false;
    const { default: App } = await import('./src/App');
    register(App);
  } catch (error) {
    console.error('Skia failed to initialize; registering functional static fallback.', error);
    (globalThis as ParallaxGlobal).__PARALLAX_REDUCED_GRAPHICS__ = true;
    const { default: FallbackApp } = await import('./src/FallbackApp');
    register(FallbackApp);
  }
}

void boot();
