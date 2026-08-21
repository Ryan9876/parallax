import React from 'react';
import { AccessibilityInfo, StyleSheet, View } from 'react-native';
import { Canvas, Circle, Path, Skia } from '@shopify/react-native-skia';
import { useClock } from '@shopify/react-native-skia';
import { useDerivedValue } from 'react-native-reanimated';
import { palette } from '../theme';

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

  const editorialCut = React.useMemo(() => {
    const p = Skia.Path.Make();
    p.moveTo(size * 0.18, size * 0.68);
    p.quadTo(size * 0.33, size * 0.82, size * 0.48, size * 0.78);
    return p;
  }, [size]);

  return (
    <View accessibilityLabel="Parallax optical mark" style={{ width: size, height: size }}>
      <Canvas style={StyleSheet.absoluteFill}>
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={size * 0.44}
          color="rgba(125,231,255,0.30)"
          style="stroke"
          strokeWidth={1.2}
        />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={size * 0.35}
          color="rgba(139,156,255,0.52)"
          style="stroke"
          strokeWidth={1.1}
        />
        <Path
          path={aperture}
          color={palette.violet}
          style="stroke"
          strokeWidth={2.4}
        />
        <Path
          path={editorialCut}
          color={palette.peach}
          style="stroke"
          strokeWidth={1.2}
        />
        <Circle
          cx={size / 2 + phase.value * size * 0.08}
          cy={size / 2}
          r={size * 0.07}
          color={palette.cyan}
        />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={size * 0.03}
          color={palette.cream}
        />
      </Canvas>
    </View>
  );
}
