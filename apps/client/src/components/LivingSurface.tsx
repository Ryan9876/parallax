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
    p = float2(0.82 * p.x + 0.57 * p.y, -0.57 * p.x + 0.82 * p.y) * 1.93 + 5.73;
    a *= 0.5;
  }
  return v;
}

float softWell(float2 p, float2 c, float2 scale) {
  float2 d = (p - c) / scale;
  return exp(-dot(d, d));
}

half4 main(float2 pos) {
  float2 uv = pos / resolution;
  float2 q = uv - 0.5;
  float aspect = resolution.x / max(resolution.y, 1.0);
  q.x *= aspect;

  // Low-frequency advection: perceived composition changes over tens of seconds, not frames.
  float t = time * 0.030;
  float3 abyss = float3(0.014, 0.018, 0.036);
  float3 midnight = float3(0.024, 0.031, 0.068);
  float3 cobalt = float3(0.075, 0.115, 0.360);
  float3 indigo = float3(0.225, 0.190, 0.565);
  float3 violet = float3(0.400, 0.175, 0.610);
  float3 magenta = float3(0.600, 0.155, 0.430);
  float3 lavender = float3(0.585, 0.385, 0.805);
  float3 cyan = float3(0.155, 0.470, 0.650);
  float3 amber = float3(0.640, 0.350, 0.095);
  float3 peach = float3(0.650, 0.310, 0.220);

  float hazeA = fbm(q * 0.86 + float2(t * 0.040, -t * 0.026));
  float hazeB = fbm(q * 1.18 + float2(-t * 0.031, t * 0.037) + 8.1);
  float2 flow = float2(
    sin(q.y * 2.2 + t * 0.42) + (hazeA - 0.5) * 1.2,
    cos(q.x * 2.0 - t * 0.35) + (hazeB - 0.5) * 1.1
  ) * 0.055;
  float2 p = q + flow;

  float3 col = mix(abyss, midnight, 0.28 + hazeA * 0.16);

  // Large, heavily feathered color wells overlap to read as diffused light through liquid glass.
  // Their differing periods avoid a visible short loop while preserving a calm drift.
  float2 cBlue = float2(-0.40 + 0.17 * sin(t * 0.44), -0.27 + 0.20 * cos(t * 0.31));
  float2 cIndigo = float2(0.43 + 0.15 * cos(t * 0.37), 0.26 + 0.19 * sin(t * 0.29));
  float2 cViolet = float2(-0.06 + 0.22 * sin(t * 0.24), 0.47 + 0.13 * cos(t * 0.33));
  float2 cMagenta = float2(0.28 + 0.14 * cos(t * 0.23), -0.42 + 0.16 * sin(t * 0.27));
  float2 cLavender = float2(-0.52 + 0.11 * sin(t * 0.21), 0.38 + 0.16 * cos(t * 0.25));
  float2 cWarm = float2(0.53 + 0.10 * cos(t * 0.19), -0.10 + 0.23 * sin(t * 0.22));
  float2 cPeach = float2(-0.36 + 0.10 * sin(t * 0.17), 0.58 + 0.09 * cos(t * 0.20));

  float blueField = softWell(p, cBlue, float2(0.72, 0.58));
  float indigoField = softWell(p, cIndigo, float2(0.68, 0.62));
  float violetField = softWell(p, cViolet, float2(0.74, 0.57));
  float magentaField = softWell(p, cMagenta, float2(0.64, 0.54));
  float lavenderField = softWell(p, cLavender, float2(0.58, 0.53));
  float warmField = softWell(p, cWarm, float2(0.46, 0.41));
  float peachField = softWell(p, cPeach, float2(0.50, 0.44));

  float lift = 0.86 + energy * 0.18;
  col = mix(col, cobalt, blueField * 0.33 * lift);
  col = mix(col, indigo, indigoField * 0.29 * lift);
  col = mix(col, violet, violetField * 0.27 * lift);
  col = mix(col, magenta, magentaField * 0.14 * lift);
  col = mix(col, lavender, lavenderField * 0.12 * lift);

  // Warmth is intentionally sparse: a counterpoint to the violet field, never the dominant palette.
  float warmGate = smoothstep(0.34, 0.72, warmField) * (0.055 + energy * 0.018);
  float peachGate = smoothstep(0.40, 0.76, peachField) * 0.040;
  col = mix(col, amber, warmGate);
  col = mix(col, peach, peachGate);

  // Cyan is a cool optical whisper rather than a full-field wash.
  float2 focus = float2(0.10 + 0.13 * sin(t * 0.20), 0.02 + 0.11 * cos(t * 0.26));
  float focusBloom = softWell(p, focus, float2(0.32, 0.27));
  col = mix(col, cyan, focusBloom * (0.018 + energy * 0.035));

  // A second low-frequency haze blends neighboring chroma so no discrete blob edge reads to the eye.
  float diffusion = fbm(p * 0.72 + float2(t * 0.022, t * 0.017) + 17.0);
  col = mix(col, col * (0.93 + diffusion * 0.12), 0.42);

  // Protect the conversation reading zone while allowing the periphery to remain visibly alive.
  float2 centerScale = float2(0.72, 0.84);
  float2 centerQ = q / centerScale;
  float centerMask = exp(-dot(centerQ, centerQ) * 1.58);
  col = mix(col, abyss, centerMask * (0.20 - energy * 0.025));

  // Fine low-amplitude material grain prevents a flat digital gradient.
  float grain = hash(pos * 0.29 + time * 0.031) - 0.5;
  col += grain * 0.0045;

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
