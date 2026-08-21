import React from 'react';
import { AccessibilityInfo, StyleSheet, View } from 'react-native';
import { Canvas, Circle, Line, Path, Skia, useClock, vec } from '@shopify/react-native-skia';
import { useDerivedValue } from 'react-native-reanimated';

export function ParallaxLogo({ size = 44 }: { size?: number }) {
  const [reduceMotion, setReduceMotion] = React.useState(false);
  const clock = useClock();

  React.useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion);
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduceMotion);
    return () => sub.remove();
  }, []);

  const phase = useDerivedValue(() => {
    if (reduceMotion) return 0;
    return Math.sin((clock.value / 1000) * (Math.PI * 2 / 9));
  }, [reduceMotion]);

  const scanOpacity = useDerivedValue(() => 0.18 + Math.abs(phase.value) * 0.24);
  const dotCx = useDerivedValue(() => size / 2 + phase.value * size * 0.045, [size]);

  const aperture = React.useMemo(() => {
    const p = Skia.Path.Make();
    const c = size / 2;
    const r = size * 0.23;
    p.moveTo(c, c - r);
    p.lineTo(c + r * 0.86, c - r * 0.5);
    p.lineTo(c + r * 0.86, c + r * 0.5);
    p.lineTo(c, c + r);
    p.lineTo(c - r * 0.86, c + r * 0.5);
    p.lineTo(c - r * 0.86, c - r * 0.5);
    p.close();
    return p;
  }, [size]);

  return (
    <View accessibilityLabel="Parallax" style={{ width: size, height: size }}>
      <Canvas style={StyleSheet.absoluteFill}>
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={size * 0.32}
          color="rgba(20,125,159,0.18)"
          style="stroke"
          strokeWidth={1}
        />
        <Path
          path={aperture}
          color="#147D9F"
          style="stroke"
          strokeWidth={1.35}
        />
        <Line
          p1={vec(size * 0.18, size / 2)}
          p2={vec(size * 0.82, size / 2)}
          color="#9A7F71"
          strokeWidth={0.8}
          opacity={scanOpacity}
        />
        <Line
          p1={vec(size / 2, size * 0.18)}
          p2={vec(size / 2, size * 0.82)}
          color="#9A7F71"
          strokeWidth={0.8}
          opacity={0.16}
        />
        <Circle cx={dotCx} cy={size / 2} r={size * 0.04} color="#D8F9FF" />
        <Circle cx={size / 2} cy={size / 2} r={size * 0.018} color="#20282B" />
      </Canvas>
    </View>
  );
}
