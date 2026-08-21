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
  float t = time * 0.035;

  // Quiet mineral substrate. Motion is broad and slow so the surface reads
  // like an optical workplane instead of decorative fluid animation.
  float n1 = fbm(q * 1.35 + float2(t * 0.24, -t * 0.11));
  float n2 = fbm(q * 2.10 + float2(-t * 0.08, t * 0.18));
  float field = mix(n1, n2, 0.38);

  float3 paper = float3(0.965, 0.958, 0.931);
  float3 stone = float3(0.902, 0.910, 0.894);
  float3 cool = float3(0.707, 0.829, 0.827);
  float3 warm = float3(0.875, 0.796, 0.709);
  float3 ink = float3(0.132, 0.159, 0.165);

  float3 col = mix(paper, stone, 0.11 + field * 0.055);

  // Sparse topographic isolines. They are the signature background behavior:
  // precise enough to feel instrument-like, soft enough to disappear under copy.
  float contourSource = field + 0.13 * sin(q.x * 1.7 - q.y * 1.2 + t);
  float contour = lineMask(contourSource, 0.105, 0.0022);
  col = mix(col, ink, contour * (0.025 + energy * 0.012));

  // A very faint drafting grid adds scale without turning the surface into a dashboard.
  float gx = lineMask(uv.x, 0.055, 0.00045);
  float gy = lineMask(uv.y, 0.055, 0.00045);
  float grid = max(gx, gy);
  col = mix(col, ink, grid * 0.010);

  // One optical focus region, not a full-screen glow. The focus drifts slowly and
  // becomes slightly more apparent while intelligence is active.
  float2 focus = float2(
    0.16 * sin(t * 0.71),
    0.11 * cos(t * 0.53)
  );
  float r = length(q - focus);
  float halo = exp(-r * r * 7.8);
  float ring = 1.0 - smoothstep(0.006, 0.018, abs(r - (0.34 + 0.018 * sin(t))));
  col = mix(col, cool, halo * (0.025 + energy * 0.026));
  col = mix(col, cool, ring * (0.025 + energy * 0.030));

  // A secondary warm calibration trace keeps the palette from becoming generic blue SaaS.
  float diagonal = 1.0 - smoothstep(0.003, 0.012, abs((q.x * 0.72 + q.y) - 0.56));
  col = mix(col, warm, diagonal * 0.022);

  // Slight edge falloff keeps attention in the working area without visible vignette styling.
  float edge = smoothstep(0.94, 0.35, length(float2(q.x / max(aspect, 1.0), q.y)));
  col = mix(paper, col, 0.90 + edge * 0.10);

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
