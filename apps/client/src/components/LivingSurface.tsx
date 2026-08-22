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

  // The v0.12 field was visually too slow in production because nested time multipliers
  // pushed major color cycles into multi-minute territory. v0.13 keeps the same broad
  // composition but moves the large wells on roughly 70–120 second cycles so motion is
  // perceptible during normal use without becoming an animation showcase.
  float t = time * 0.110;
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

  float hazeA = fbm(q * 0.86 + float2(t * 0.055, -t * 0.038));
  float hazeB = fbm(q * 1.18 + float2(-t * 0.046, t * 0.052) + 8.1);
  float2 flow = float2(
    sin(q.y * 2.2 + t * 0.58) + (hazeA - 0.5) * 1.2,
    cos(q.x * 2.0 - t * 0.49) + (hazeB - 0.5) * 1.1
  ) * 0.060;
  float2 p = q + flow;

  float3 col = mix(abyss, midnight, 0.34 + hazeA * 0.17);

  float chromaWave = 0.5 + 0.5 * sin(q.x * 1.35 - q.y * 1.05 + t * 0.31 + hazeB * 0.75);
  float3 atmospheric = mix(cobalt, violet, chromaWave);
  col = mix(col, atmospheric, 0.082 + hazeB * 0.062);

  // Large, heavily feathered color wells overlap like light moving through liquid glass.
  // Differing periods prevent a visible synchronized loop.
  float2 cBlue = float2(-0.40 + 0.18 * sin(t * 0.76), -0.27 + 0.21 * cos(t * 0.59));
  float2 cIndigo = float2(0.43 + 0.16 * cos(t * 0.64), 0.26 + 0.20 * sin(t * 0.53));
  float2 cViolet = float2(-0.06 + 0.23 * sin(t * 0.48), 0.47 + 0.14 * cos(t * 0.61));
  float2 cMagenta = float2(0.28 + 0.15 * cos(t * 0.43), -0.42 + 0.17 * sin(t * 0.51));
  float2 cLavender = float2(-0.52 + 0.12 * sin(t * 0.39), 0.38 + 0.17 * cos(t * 0.46));
  float2 cWarm = float2(0.53 + 0.11 * cos(t * 0.34), -0.10 + 0.24 * sin(t * 0.41));
  float2 cPeach = float2(-0.36 + 0.11 * sin(t * 0.31), 0.58 + 0.10 * cos(t * 0.37));

  float blueField = softWell(p, cBlue, float2(0.76, 0.62));
  float indigoField = softWell(p, cIndigo, float2(0.72, 0.66));
  float violetField = softWell(p, cViolet, float2(0.78, 0.62));
  float magentaField = softWell(p, cMagenta, float2(0.70, 0.58));
  float lavenderField = softWell(p, cLavender, float2(0.62, 0.57));
  float warmField = softWell(p, cWarm, float2(0.50, 0.45));
  float peachField = softWell(p, cPeach, float2(0.54, 0.48));

  float lift = 0.94 + energy * 0.22;
  col = mix(col, cobalt, blueField * 0.48 * lift);
  col = mix(col, indigo, indigoField * 0.41 * lift);
  col = mix(col, violet, violetField * 0.37 * lift);
  col = mix(col, magenta, magentaField * 0.23 * lift);
  col = mix(col, lavender, lavenderField * 0.17 * lift);

  // Warmth remains a sparse counterpoint, never the dominant field.
  float warmGate = smoothstep(0.34, 0.72, warmField) * (0.092 + energy * 0.021);
  float peachGate = smoothstep(0.40, 0.76, peachField) * 0.062;
  col = mix(col, amber, warmGate);
  col = mix(col, peach, peachGate);

  // Cyan remains an optical whisper near the reading region.
  float2 focus = float2(0.10 + 0.14 * sin(t * 0.42), 0.02 + 0.12 * cos(t * 0.47));
  float focusBloom = softWell(p, focus, float2(0.34, 0.29));
  col = mix(col, cyan, focusBloom * (0.026 + energy * 0.043));

  float diffusion = fbm(p * 0.72 + float2(t * 0.035, t * 0.029) + 17.0);
  col = mix(col, col * (0.92 + diffusion * 0.14), 0.42);

  // Protect the central conversation reading zone while allowing peripheral chroma to move.
  float2 centerScale = float2(0.72, 0.84);
  float2 centerQ = q / centerScale;
  float centerMask = exp(-dot(centerQ, centerQ) * 1.58);
  col = mix(col, abyss, centerMask * (0.17 - energy * 0.020));

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
