import React from 'react';
import { AccessibilityInfo, StyleSheet, View, useWindowDimensions } from 'react-native';
import { Canvas, Fill, Shader, Skia, useClock } from '@shopify/react-native-skia';
import { useDerivedValue } from 'react-native-reanimated';
import { palette } from '../theme';

const effect = Skia.RuntimeEffect.Make(`
uniform float2 resolution;
uniform float time;
uniform float energy;

float hash(float2 p) {
  p = fract(p * float2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}

float noise(float2 p) {
  float2 i = floor(p);
  float2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(hash(i), hash(i + float2(1.0, 0.0)), f.x),
    mix(hash(i + float2(0.0, 1.0)), hash(i + float2(1.0, 1.0)), f.x),
    f.y
  );
}

float fbm(float2 p) {
  float v = 0.0;
  float a = 0.5;
  for (int i = 0; i < 4; i++) {
    v += a * noise(p);
    p = float2(0.82 * p.x + 0.57 * p.y, -0.57 * p.x + 0.82 * p.y) * 2.01 + 5.73;
    a *= 0.5;
  }
  return v;
}

float lineMask(float value, float spacing, float width) {
  float d = abs(fract(value / spacing + 0.5) - 0.5) * spacing;
  return 1.0 - smoothstep(width, width * 1.8, d);
}

half4 main(float2 pos) {
  float2 uv = pos / resolution;
  float2 q = uv - 0.5;
  float aspect = resolution.x / max(resolution.y, 1.0);
  q.x *= aspect;
  float t = time * 0.018;

  float n1 = fbm(q * 1.18 + float2(t * 0.16, -t * 0.07));
  float n2 = fbm(q * 1.72 + float2(-t * 0.05, t * 0.11));
  float field = mix(n1, n2, 0.30);

  float3 abyss = float3(0.031, 0.043, 0.071);
  float3 panel = float3(0.043, 0.063, 0.098);
  float3 indigo = float3(0.545, 0.612, 1.000);
  float3 violet = float3(0.820, 0.545, 1.000);
  float3 cyan = float3(0.490, 0.906, 1.000);
  float3 lightInk = float3(0.925, 0.914, 1.000);

  float3 col = mix(abyss, panel, 0.22 + field * 0.12);

  // Sparse topographic structure keeps the workplane spatial without turning into a HUD.
  float contourSource = field + 0.10 * sin(q.x * 1.45 - q.y * 1.05 + t);
  float contour = lineMask(contourSource, 0.128, 0.0017);
  col = mix(col, violet, contour * (0.018 + energy * 0.010));

  // Drafting grid stays near the threshold of perception.
  float gx = lineMask(uv.x, 0.070, 0.00032);
  float gy = lineMask(uv.y, 0.070, 0.00032);
  float grid = max(gx, gy);
  col = mix(col, indigo, grid * 0.010);

  // One slow focus region carries active optical energy.
  float2 focus = float2(
    0.12 * sin(t * 0.47),
    0.08 * cos(t * 0.39)
  );
  float r = length(q - focus);
  float halo = exp(-r * r * 8.6);
  float ring = 1.0 - smoothstep(0.004, 0.014, abs(r - (0.31 + 0.010 * sin(t))));
  col = mix(col, indigo, halo * (0.018 + energy * 0.024));
  col = mix(col, cyan, ring * (0.010 + energy * 0.018));

  // A restrained violet calibration trace prevents the field becoming generic blue SaaS.
  float diagonal = 1.0 - smoothstep(0.0025, 0.010, abs((q.x * 0.66 + q.y) - 0.60));
  col = mix(col, violet, diagonal * 0.014);

  // Dark center bias keeps conversation copy dominant.
  float center = exp(-dot(q, q) * 1.6);
  col = mix(col, abyss, center * 0.14);

  // Tiny lift under higher response energy, never enough to compete with text.
  col = mix(col, lightInk, energy * halo * 0.0025);

  return half4(col, 1.0);
}
`);

export function LivingSurface({ energy }: { energy: number }) {
  const { width, height } = useWindowDimensions();
  const clock = useClock();
  const [reduceMotion, setReduceMotion] = React.useState(false);

  React.useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion);
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduceMotion);
    return () => sub.remove();
  }, []);

  const uniforms = useDerivedValue(() => ({
    resolution: [width, height],
    time: reduceMotion ? 0 : clock.value / 1000,
    energy: reduceMotion ? 0 : energy,
  }));

  if (!effect) {
    return <View pointerEvents="none" style={[StyleSheet.absoluteFill, styles.fallback]} />;
  }

  return (
    <Canvas pointerEvents="none" style={StyleSheet.absoluteFill}>
      <Fill>
        <Shader source={effect} uniforms={uniforms} />
      </Fill>
    </Canvas>
  );
}

const styles = StyleSheet.create({
  fallback: {
    backgroundColor: palette.void,
  },
});
