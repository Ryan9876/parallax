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

float ribbon(float value, float center, float width) {
  return 1.0 - smoothstep(width, width * 2.2, abs(value - center));
}

half4 main(float2 pos) {
  float2 uv = pos / resolution;
  float2 q = uv - 0.5;
  float aspect = resolution.x / max(resolution.y, 1.0);
  q.x *= aspect;
  float t = time * 0.020;

  float3 abyss = float3(0.027, 0.035, 0.059);
  float3 deep = float3(0.043, 0.052, 0.090);
  float3 indigo = float3(0.545, 0.612, 1.000);
  float3 violet = float3(0.820, 0.545, 1.000);
  float3 cyan = float3(0.490, 0.906, 1.000);
  float3 peach = float3(0.875, 0.655, 0.561);

  float paper = fbm(q * 1.04 + float2(t * 0.09, -t * 0.04));
  float3 col = mix(abyss, deep, 0.18 + paper * 0.10);

  // Slow editorial ink fields: broad asymmetric stains, never a full-screen neon wash.
  float2 c1 = float2(-0.38 + 0.05 * sin(t * 0.7), -0.18 + 0.04 * cos(t * 0.5));
  float2 c2 = float2(0.44 + 0.04 * cos(t * 0.4), 0.24 + 0.05 * sin(t * 0.55));
  float2 c3 = float2(0.08 + 0.03 * sin(t * 0.33), -0.42);
  float ink1 = exp(-dot(q - c1, q - c1) * 4.0);
  float ink2 = exp(-dot(q - c2, q - c2) * 5.0);
  float ink3 = exp(-dot(q - c3, q - c3) * 7.0);
  float warp = fbm(q * 1.7 + float2(-t * 0.05, t * 0.08));
  col = mix(col, violet, ink1 * (0.045 + warp * 0.026));
  col = mix(col, indigo, ink2 * (0.040 + (1.0 - warp) * 0.024));
  col = mix(col, peach, ink3 * 0.010);

  // Hand-drawn contour ribbons: intentionally uneven, sparse, and open.
  float contourField = fbm(q * 1.32 + float2(t * 0.08, t * -0.03));
  float wobble = 0.018 * sin(q.x * 8.2 + q.y * 5.7 + t * 1.1);
  float r1 = ribbon(contourField + wobble, 0.44, 0.0045);
  float r2 = ribbon(contourField - wobble * 0.7, 0.59, 0.0038);
  float r3 = ribbon(contourField + wobble * 0.5, 0.72, 0.0032);
  col = mix(col, violet, (r1 + r3) * (0.018 + energy * 0.006));
  col = mix(col, indigo, r2 * (0.015 + energy * 0.008));

  // One optical focus region carries active response energy.
  float2 focus = float2(0.15 * sin(t * 0.41), 0.10 * cos(t * 0.36));
  float radius = length(q - focus);
  float halo = exp(-radius * radius * 8.2);
  float focusRing = 1.0 - smoothstep(0.004, 0.015, abs(radius - (0.29 + 0.012 * sin(t * 0.8))));
  col = mix(col, indigo, halo * (0.015 + energy * 0.022));
  col = mix(col, cyan, focusRing * (0.008 + energy * 0.020));

  // Procedural print grain keeps glass/material from feeling digitally sterile.
  float grain = hash(pos * 0.37 + time * 0.07) - 0.5;
  col += grain * 0.008;

  // Reading field stays darker than the perimeter so conversation always wins.
  float center = exp(-dot(q, q) * 1.8);
  col = mix(col, abyss, center * 0.18);

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
