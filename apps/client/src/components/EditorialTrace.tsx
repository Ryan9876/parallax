import React from 'react';
import { AccessibilityInfo, LayoutChangeEvent, StyleSheet, View } from 'react-native';
import { Canvas, Circle, Path, Skia } from '@shopify/react-native-skia';
import { palette } from '../theme';

export function EditorialTrace({
  active = false,
  tone = 'violet',
}: {
  active?: boolean;
  tone?: 'violet' | 'sage' | 'peach';
}) {
  const [size, setSize] = React.useState({ width: 0, height: 0 });
  const [reduceMotion, setReduceMotion] = React.useState(false);

  React.useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion);
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduceMotion);
    return () => sub.remove();
  }, []);

  const onLayout = React.useCallback((event: LayoutChangeEvent) => {
    const { width, height } = event.nativeEvent.layout;
    setSize((current) => current.width === width && current.height === height ? current : { width, height });
  }, []);

  const path = React.useMemo(() => {
    if (!size.width || !size.height) return null;
    const w = size.width;
    const h = size.height;
    const p = Skia.Path.Make();
    p.moveTo(10, Math.min(h - 8, 28));
    p.quadTo(4, h * 0.48, 12, h - 10);
    p.quadTo(w * 0.22, h - 4, w * 0.46, h - 8);
    p.moveTo(w * 0.67, 8);
    p.quadTo(w * 0.86, 4, w - 12, 14);
    p.quadTo(w - 5, h * 0.24, w - 10, Math.min(h - 12, h * 0.44));
    return p;
  }, [size]);

  const toneColor = tone === 'sage'
    ? palette.sage
    : tone === 'peach'
      ? palette.peach
      : palette.violet;
  const opacity = active && !reduceMotion ? 0.72 : 0.34;

  return (
    <View
      accessible={false}
      importantForAccessibility="no-hide-descendants"
      pointerEvents="none"
      onLayout={onLayout}
      style={StyleSheet.absoluteFill}
    >
      {path && (
        <Canvas style={StyleSheet.absoluteFill}>
          <Path
            path={path}
            color={toneColor}
            style="stroke"
            strokeWidth={1.25}
            opacity={opacity}
          />
          <Circle
            cx={Math.max(14, size.width - 11)}
            cy={Math.min(size.height - 12, size.height * 0.44)}
            r={active ? 2.6 : 1.8}
            color={active ? palette.cyan : toneColor}
            opacity={active ? 0.9 : 0.45}
          />
        </Canvas>
      )}
    </View>
  );
}
