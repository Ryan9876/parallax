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
    p = float2(0.8 * p.x + 0.6 * p.y, -0.6 * p.x + 0.8 * p.y) * 2.03 + 7.13;
    a *= 0.5;
  }
  return v;
}

half4 main(float2 pos) {
  float2 uv = pos / resolution;
  float2 q = uv - 0.5;
  q.x *= resolution.x / max(resolution.y, 1.0);
  float t = time * 0.10;

  float2 warp = float2(
    fbm(q * 2.35 + float2(t * (0.20 + energy * 0.20), -t * 0.08)),
    fbm(q * 2.15 + float2(-t * 0.11, t * (0.20 + energy * 0.20)))
  );
  float2 w = q + (warp - 0.5) * (0.16 + energy * 0.08);

  float f1 = fbm(w * 2.0 + float2(t * 0.06, t * 0.025));
  float f2 = fbm(w * 3.1 - float2(t * 0.035, t * 0.05));
  float band1 = 0.5 + 0.5 * sin((w.x * 3.2 + w.y * 2.0 + f1 * 2.6 + t * 0.13) * 3.14159);
  float band2 = 0.5 + 0.5 * sin((-w.x * 2.4 + w.y * 3.1 + f2 * 2.0 - t * 0.10) * 3.14159);

  float3 mineral = float3(0.957, 0.953, 0.933);
  float3 smoke = float3(0.835, 0.850, 0.846);
  float3 teal = float3(0.54, 0.77, 0.79);
  float3 peach = float3(0.92, 0.78, 0.67);
  float3 moss = float3(0.75, 0.79, 0.64);

  float3 col = mix(mineral, smoke, 0.14 * f1);
  col = mix(col, teal, (0.10 + energy * 0.04) * smoothstep(0.62, 0.98, band1));
  col = mix(col, peach, 0.08 * smoothstep(0.66, 0.99, band2));
  col = mix(col, moss, 0.035 * smoothstep(0.76, 1.0, (band1 + band2) * 0.5));

  float caustic = pow(max(0.0, 1.0 - abs(0.5 - band1) * 2.0), 10.0);
  col += float3(0.84, 0.96, 1.0) * caustic * (0.05 + energy * 0.07);
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
    backgroundColor: '#F4F3EE',
  },
});
