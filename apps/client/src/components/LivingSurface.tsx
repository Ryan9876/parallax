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

float blob(float2 p, float2 c, float2 scale, float feather) {
  float2 d = (p - c) / scale;
  float r2 = dot(d, d);
  return exp(-r2 * feather);
}

half4 main(float2 pos) {
  float2 uv = pos / resolution;
  float2 q = uv - 0.5;
  float aspect = resolution.x / max(resolution.y, 1.0);
  q.x *= aspect;

  // Deliberately slow: a full perceived drift takes tens of seconds.
  float t = time * 0.027;
  float3 abyss = float3(0.020, 0.025, 0.045);
  float3 deep = float3(0.035, 0.041, 0.078);
  float3 indigo = float3(0.265, 0.315, 0.680);
  float3 violet = float3(0.455, 0.245, 0.705);
  float3 lavender = float3(0.650, 0.440, 0.890);
  float3 cyan = float3(0.220, 0.610, 0.730);

  float grainField = fbm(q * 1.05 + float2(t * 0.03, -t * 0.02));
  float3 col = mix(abyss, deep, 0.20 + grainField * 0.11);

  // Organic lava-lamp masses. Each path has a different period so the composition never visibly snaps.
  float2 c1 = float2(-0.46 + 0.15 * sin(t * 0.71), -0.28 + 0.19 * cos(t * 0.43));
  float2 c2 = float2( 0.48 + 0.13 * cos(t * 0.52),  0.24 + 0.17 * sin(t * 0.39));
  float2 c3 = float2( 0.06 + 0.20 * sin(t * 0.31), -0.52 + 0.08 * cos(t * 0.57));
  float2 c4 = float2(-0.58 + 0.08 * cos(t * 0.36),  0.50 + 0.13 * sin(t * 0.47));
  float2 c5 = float2( 0.34 + 0.11 * sin(t * 0.27),  0.57 + 0.09 * cos(t * 0.34));

  float warp = fbm(q * 1.55 + float2(-t * 0.045, t * 0.052));
  float wobble = (warp - 0.5) * 0.07;
  float2 wq = q + float2(wobble, -wobble * 0.72);

  float b1 = blob(wq, c1, float2(0.42, 0.30), 2.0);
  float b2 = blob(wq, c2, float2(0.40, 0.34), 2.1);
  float b3 = blob(wq, c3, float2(0.31, 0.24), 2.0);
  float b4 = blob(wq, c4, float2(0.33, 0.29), 2.2);
  float b5 = blob(wq, c5, float2(0.34, 0.26), 2.0);

  float idleLift = 0.82 + energy * 0.16;
  col = mix(col, violet, b1 * 0.18 * idleLift);
  col = mix(col, indigo, b2 * 0.16 * idleLift);
  col = mix(col, lavender, b3 * 0.085 * idleLift);
  col = mix(col, violet, b4 * 0.11 * idleLift);
  col = mix(col, indigo, b5 * 0.10 * idleLift);

  // A restrained cyan optical bloom appears only as a small secondary accent.
  float2 focus = float2(0.22 + 0.08 * sin(t * 0.29), -0.05 + 0.07 * cos(t * 0.33));
  float focusBloom = blob(wq, focus, float2(0.22, 0.18), 2.5);
  col = mix(col, cyan, focusBloom * (0.025 + energy * 0.045));

  // Extremely faint liquid edge separation gives the masses dimensionality without turning into outlines.
  float field = b1 + b2 + 0.72 * b3 + 0.82 * b4 + 0.78 * b5;
  float edge = smoothstep(0.50, 0.62, field) - smoothstep(0.67, 0.79, field);
  col = mix(col, lavender, edge * 0.022);

  // Keep the narrative reading zone darker than the moving perimeter material.
  float centerMask = exp(-dot(q / float2(0.68, 0.82), q / float2(0.68, 0.82)) * 1.72);
  col = mix(col, abyss, centerMask * 0.24);

  // Fine low-amplitude material grain prevents a flat digital gradient.
  float grain = hash(pos * 0.31 + time * 0.035) - 0.5;
  col += grain * 0.006;

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
    energy: reduceMotion ? 0.18 : energy,
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
