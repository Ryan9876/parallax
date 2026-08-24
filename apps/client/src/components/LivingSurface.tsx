import React from 'react';
import { AccessibilityInfo, StyleSheet, View, useWindowDimensions } from 'react-native';
import { Canvas, Fill, Shader, Skia, useClock } from '@shopify/react-native-skia';
import { useDerivedValue } from 'react-native-reanimated';
import { palette } from '../theme';

const effect = Skia.RuntimeEffect.Make(`
uniform float2 resolution;
uniform float time;
uniform float energy;

float softWell(float2 p, float2 c, float2 scale) {
  float2 d = (p - c) / scale;
  return exp(-dot(d, d));
}

half4 main(float2 pos) {
  float2 uv = pos / resolution;
  float2 q = uv - 0.5;
  q.x *= resolution.x / max(resolution.y, 1.0);
  float t = time * 0.035;

  float3 ivory = float3(0.984, 0.969, 0.933);
  float3 cream = float3(0.961, 0.933, 0.875);
  float3 rust = float3(0.769, 0.290, 0.106);
  float3 teal = float3(0.000, 0.518, 0.529);
  float3 olive = float3(0.400, 0.459, 0.227);

  float3 col = mix(ivory, cream, smoothstep(-0.55, 0.75, uv.y) * 0.55);
  float rustField = softWell(q, float2(0.48 + 0.03 * sin(t), -0.38), float2(0.72, 0.42));
  float tealField = softWell(q, float2(-0.52, 0.28 + 0.025 * cos(t * 0.8)), float2(0.62, 0.48));
  float oliveField = softWell(q, float2(0.10, 0.62), float2(0.78, 0.42));

  col = mix(col, rust, rustField * (0.025 + energy * 0.010));
  col = mix(col, teal, tealField * (0.020 + energy * 0.008));
  col = mix(col, olive, oliveField * 0.020);

  float contour = sin((q.x * 1.6 + q.y * 2.1) * 10.0 + sin(q.x * 5.0) * 0.8);
  float contourMask = smoothstep(0.94, 0.985, contour) * 0.018;
  col = mix(col, olive, contourMask);

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
    energy: reduceMotion ? 0 : Math.min(energy, 0.7),
  }));

  if (!effect) return <View pointerEvents="none" style={[StyleSheet.absoluteFill, styles.fallback]} />;

  return (
    <Canvas pointerEvents="none" style={StyleSheet.absoluteFill}>
      <Fill><Shader source={effect} uniforms={uniforms} /></Fill>
    </Canvas>
  );
}

const styles = StyleSheet.create({ fallback: { backgroundColor: palette.ivory50 } });
