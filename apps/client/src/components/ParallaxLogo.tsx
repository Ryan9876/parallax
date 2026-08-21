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
    return Math.sin((clock.value / 1000) * (Math.PI * 2 / 12));
  }, [reduceMotion]);

  const focus = useDerivedValue(() => 0.55 + phase.value * 0.08);

  const aperture = React.useMemo(() => {
    const p = Skia.Path.Make();
    const c = size / 2;
    const r = size * 0.27;
    p.moveTo(c, c - r);
    p.quadTo(c + r * 1.05, c - r * 0.15, c + r * 0.58, c + r * 0.92);
    p.quadTo(c, c + r * 1.1, c - r * 0.58, c + r * 0.92);
    p.quadTo(c - r * 1.05, c - r * 0.15, c, c - r);
    p.close();
    return p;
  }, [size]);

  return (
    <View accessibilityLabel="Parallax optical mark" style={{ width: size, height: size }}>
      <Canvas style={StyleSheet.absoluteFill}>
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={size * 0.38}
          color="rgba(20,125,159,0.10)"
          style="stroke"
          strokeWidth={1}
        />
        <Path
          path={aperture}
          color="#147D9F"
          style="stroke"
          strokeWidth={1.8}
        />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={size * 0.09}
          color="rgba(20,125,159,0.12)"
        />
        <Circle
          cx={size / 2 + phase.value * size * 0.06}
          cy={size / 2}
          r={size * 0.035}
          color="#D8F9FF"
          opacity={focus}
        />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={size * 0.022}
          color="#20282B"
        />
      </Canvas>
    </View>
  );
}
