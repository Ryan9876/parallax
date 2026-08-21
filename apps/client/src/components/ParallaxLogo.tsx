import React from 'react';
import { AccessibilityInfo, StyleSheet, View } from 'react-native';
import { Canvas, Circle, Path, Skia } from '@shopify/react-native-skia';
import { useClock } from '@shopify/react-native-skia';
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
    return Math.sin((clock.value / 1000) * (Math.PI * 2 / 16));
  }, [reduceMotion]);

  const aperture = React.useMemo(() => {
    const p = Skia.Path.Make();
    const c = size / 2;
    const r = size * 0.28;
    p.moveTo(c, c - r);
    p.quadTo(c + r * 1.15, c, c, c + r * 1.15);
    p.quadTo(c - r * 1.15, c, c, c - r);
    p.close();
    return p;
  }, [size]);

  return (
    <View accessibilityLabel="Parallax optical mark" style={{ width: size, height: size }}>
      <Canvas style={StyleSheet.absoluteFill}>
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={size * 0.43}
          color="rgba(20,125,159,0.08)"
          style="stroke"
          strokeWidth={1}
        />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={size * 0.34}
          color="rgba(20,125,159,0.18)"
          style="stroke"
          strokeWidth={1}
        />
        <Path
          path={aperture}
          color="#147D9F"
          style="stroke"
          strokeWidth={2}
        />
        <Circle
          cx={size / 2 + phase.value * size * 0.08}
          cy={size / 2}
          r={size * 0.065}
          color="rgba(216,249,255,0.9)"
        />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={size * 0.026}
          color="#20282B"
        />
      </Canvas>
    </View>
  );
}
