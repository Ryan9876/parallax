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

float band(float value, float width) {
  float s = abs(sin(value));
  return 1.0 - smoothstep(width, width * 2.6, s);
}

half4 main(float2 pos) {
  float2 uv = pos / resolution;
  float2 q = uv - 0.5;
  float aspect = resolution.x / max(resolution.y, 1.0);
  q.x *= aspect;

  float t = time * 0.09;
  float warpA = fbm(q * 1.18 + float2(t * 0.11, -t * 0.06));
  float warpB = fbm(q * 1.72 + float2(-t * 0.05, t * 0.08));
  float2 warped = q + float2(warpA - 0.5, warpB - 0.5) * 0.20;

  float3 mineral = float3(0.944, 0.949, 0.925);
  float3 warm = float3(0.974, 0.957, 0.918);
  float3 cool = float3(0.868, 0.922, 0.910);
  float3 white = float3(1.0, 0.998, 0.982);

  float field = fbm(warped * 1.05 + 1.7);
  float3 col = mix(mineral, warm, 0.34 + field * 0.20);
  col = mix(col, cool, smoothstep(0.44, 0.78, field) * 0.22);

  // Broad water-light contours. They are intentionally visible at rest, but remain
  // soft enough that the conversation surface still wins the hierarchy.
  float r1 = length(warped - float2(-0.28, -0.12));
  float r2 = length(warped - float2(0.36, 0.18));
  float r3 = length(warped - float2(0.02, 0.46));
  float c1 = band((r1 * 15.0) + warpA * 5.0 - t * 0.55, 0.095);
  float c2 = band((r2 * 13.0) - warpB * 4.0 + t * 0.38, 0.105);
  float c3 = band((r3 * 11.0) + (warpA - warpB) * 3.0 - t * 0.24, 0.11);
  float contour = max(c1 * 0.88, max(c2 * 0.72, c3 * 0.55));

  float contourStrength = 0.25 + energy * 0.16;
  col = mix(col, white, contour * contourStrength);

  // A broad translucent lift behind the working center keeps the surface luminous,
  // rather than reading as a flat beige canvas.
  float center = exp(-dot(q, q) * 1.55);
  col = mix(col, white, center * 0.055);

  // Quiet edge depth preserves the softly bowed material feeling of the prototype.
  float edge = smoothstep(0.90, 0.26, length(float2(q.x / max(aspect, 1.0), q.y)));
  col = mix(mineral, col, 0.90 + edge * 0.10);

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
    backgroundColor: '#EEF1EC',
  },
});
