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

float blob(float2 p, float2 center, float sx, float sy, float wobble) {
  float2 d = p - center;
  d += float2(
    sin((p.y + center.x) * 5.0 + wobble) * 0.035,
    cos((p.x - center.y) * 4.2 - wobble * 0.7) * 0.030
  );
  d /= float2(sx, sy);
  return exp(-dot(d, d) * 1.55);
}

half4 main(float2 pos) {
  float2 uv = pos / resolution;
  float2 q = uv - 0.5;
  float aspect = resolution.x / max(resolution.y, 1.0);
  q.x *= aspect;

  // Slow non-synchronous motion: roughly 20–45+ second visual cycles.
  float t = time * 0.115;

  float3 abyss = float3(0.018, 0.023, 0.043);
  float3 midnight = float3(0.032, 0.038, 0.075);
  float3 indigo = float3(0.310, 0.300, 0.720);
  float3 violet = float3(0.515, 0.260, 0.830);
  float3 lavender = float3(0.720, 0.510, 1.000);
  float3 blue = float3(0.145, 0.255, 0.600);

  float paper = fbm(q * 1.15 + float2(t * 0.018, -t * 0.012));
  float3 col = mix(abyss, midnight, 0.30 + paper * 0.10);

  float2 c1 = float2(-0.47 + 0.16 * sin(t * 0.57), -0.24 + 0.19 * cos(t * 0.43));
  float2 c2 = float2( 0.45 + 0.18 * cos(t * 0.38),  0.22 + 0.18 * sin(t * 0.51));
  float2 c3 = float2(-0.12 + 0.23 * sin(t * 0.31 + 1.7), 0.50 + 0.13 * cos(t * 0.47));
  float2 c4 = float2( 0.17 + 0.20 * cos(t * 0.29 + 2.2), -0.51 + 0.14 * sin(t * 0.41));

  float b1 = blob(q, c1, 0.50, 0.38, t * 0.74);
  float b2 = blob(q, c2, 0.54, 0.42, -t * 0.61);
  float b3 = blob(q, c3, 0.46, 0.34, t * 0.53 + 1.2);
  float b4 = blob(q, c4, 0.42, 0.31, -t * 0.67 + 2.1);

  // Soft metaball fusion creates a lava-lamp feel without discrete particles.
  float fusionA = smoothstep(0.28, 0.86, b1 + b3 * 0.72);
  float fusionB = smoothstep(0.30, 0.88, b2 + b4 * 0.76);
  float overlap = smoothstep(0.38, 1.08, b1 + b2 + b3 + b4);

  col = mix(col, violet, fusionA * (0.105 + energy * 0.020));
  col = mix(col, indigo, fusionB * (0.095 + energy * 0.018));
  col = mix(col, lavender, overlap * (0.034 + energy * 0.012));

  // Deep blue undercurrent adds dimensional separation without introducing a new accent family.
  float undercurrent = blob(q, float2(-0.02 + 0.12 * cos(t * 0.23), 0.04 + 0.10 * sin(t * 0.27)), 0.76, 0.58, t * 0.21);
  col = mix(col, blue, undercurrent * 0.050);

  // Soft liquid seams around the merged forms. They are broader than contour lines and never read as a HUD.
  float liquidField = b1 + b2 + b3 + b4;
  float seamA = 1.0 - smoothstep(0.018, 0.060, abs(liquidField - 0.82));
  float seamB = 1.0 - smoothstep(0.016, 0.055, abs(liquidField - 1.08));
  col = mix(col, lavender, seamA * 0.026);
  col = mix(col, violet, seamB * 0.022);

  // Fine material grain stays almost subliminal.
  float grain = hash(pos * 0.31 + time * 0.021) - 0.5;
  col += grain * 0.006;

  // Dark reading bias keeps the conversation visually dominant even as blobs pass behind it.
  float center = exp(-dot(q, q) * 1.55);
  col = mix(col, abyss, center * 0.16);

  // Gentle vignette grounds the field at the device edges.
  float edge = smoothstep(0.35, 0.95, length(q * float2(0.84, 1.0)));
  col = mix(col, abyss, edge * 0.18);

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
