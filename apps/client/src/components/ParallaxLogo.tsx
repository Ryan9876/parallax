import React from 'react';
import { AccessibilityInfo, StyleSheet, View } from 'react-native';
import { Canvas, Circle, Oval, useClock, vec } from '@shopify/react-native-skia';
import { useDerivedValue } from 'react-native-reanimated';

export function ParallaxLogo({ size = 44 }: { size?: number }) {
  const [reduceMotion, setReduceMotion] = React.useState(false);
  const clock = useClock();

  React.useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion);
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduceMotion);
    return () => sub.remove();
  }, []);

  const offset = useDerivedValue(() => {
    if (reduceMotion) return 0;
    return Math.sin((clock.value / 1000) * (Math.PI * 2 / 8)) * size * 0.035;
  }, [reduceMotion, size]);

  const leftTransform = useDerivedValue(() => [{ translateX: offset.value }, { rotate: -0.55 }]);
  const rightTransform = useDerivedValue(() => [{ translateX: -offset.value }, { rotate: 0.55 }]);
  const glintOpacity = useDerivedValue(() => {
    if (reduceMotion) return 0.28;
    const alignment = 1 - Math.min(1, Math.abs(offset.value) / (size * 0.035));
    return 0.18 + alignment * 0.55;
  });

  return (
    <View accessibilityLabel="Parallax" style={{ width: size, height: size }}>
      <Canvas style={StyleSheet.absoluteFill}>
        <Oval
          x={size * 0.17}
          y={size * 0.34}
          width={size * 0.66}
          height={size * 0.32}
          color="#147D9F"
          style="stroke"
          strokeWidth={1.5}
          transform={leftTransform}
          origin={vec(size / 2, size / 2)}
        />
        <Oval
          x={size * 0.17}
          y={size * 0.34}
          width={size * 0.66}
          height={size * 0.32}
          color="#8AA7AE"
          style="stroke"
          strokeWidth={1.2}
          transform={rightTransform}
          origin={vec(size / 2, size / 2)}
        />
        <Circle cx={size / 2} cy={size / 2} r={size * 0.055} color="#D8F9FF" opacity={glintOpacity} />
        <Circle cx={size / 2} cy={size / 2} r={size * 0.018} color="#147D9F" />
      </Canvas>
    </View>
  );
}
