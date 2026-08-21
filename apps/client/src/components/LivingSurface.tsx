import React from 'react';
import { AccessibilityInfo, StyleSheet, View, useWindowDimensions } from 'react-native';
import { Canvas, Fill, Shader, Skia, useClock } from '@shopify/react-native-skia';
import { useDerivedValue } from 'react-native-reanimated';

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

  float3 paper = float3(0.972, 0.966, 0.944);
  float3 stone = float3(0.912, 0.916, 0.903);
  float3 cool = float3(0.735, 0.834, 0.827);
  float3 warm = float3(0.882, 0.814, 0.748);
  float3 ink = float3(0.132, 0.159, 0.165);

  float3 col = mix(paper, stone, 0.075 + field * 0.035);

  // Sparse topographic isolines: perceptible only after the interface settles.
  float contourSource = field + 0.10 * sin(q.x * 1.45 - q.y * 1.05 + t);
  float contour = lineMask(contourSource, 0.128, 0.0017);
  col = mix(col, ink, contour * (0.012 + energy * 0.006));

  // Drafting grid is intentionally near the threshold of perception.
  float gx = lineMask(uv.x, 0.070, 0.00032);
  float gy = lineMask(uv.y, 0.070, 0.00032);
  float grid = max(gx, gy);
  col = mix(col, ink, grid * 0.0045);

  // A single low-energy optical focus provides depth without becoming a glow effect.
  float2 focus = float2(
    0.12 * sin(t * 0.47),
    0.08 * cos(t * 0.39)
  );
  float r = length(q - focus);
  float halo = exp(-r * r * 8.6);
  float ring = 1.0 - smoothstep(0.004, 0.014, abs(r - (0.31 + 0.010 * sin(t))));
  col = mix(col, cool, halo * (0.010 + energy * 0.012));
  col = mix(col, cool, ring * (0.008 + energy * 0.012));

  // One warm calibration trace keeps the material system from becoming generic blue SaaS.
  float diagonal = 1.0 - smoothstep(0.0025, 0.010, abs((q.x * 0.66 + q.y) - 0.60));
  col = mix(col, warm, diagonal * 0.008);

  // Gentle center bias preserves contrast behind the conversation surface.
  float center = exp(-dot(q, q) * 1.6);
  col = mix(col, paper, center * 0.025);

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
    backgroundColor: '#F7F4EC',
  },
});
