import React from 'react';
import { AccessibilityInfo, LayoutChangeEvent, StyleSheet, Text, View } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';
import { Canvas, Circle, Line, vec } from '@shopify/react-native-skia';

const CHAR_MS = 22;

function OpticalHead() {
  return (
    <Canvas style={styles.beamCanvas} pointerEvents="none">
      <Line p1={vec(0, 20)} p2={vec(108, 20)} color="rgba(84,216,255,0.36)" strokeWidth={1} />
      <Line p1={vec(108, 4)} p2={vec(108, 36)} color="#D8F9FF" strokeWidth={2} />
      <Circle cx={108} cy={20} r={5} color="#D8F9FF" />
      <Circle cx={108} cy={20} r={9} color="rgba(84,216,255,0.18)" />
    </Canvas>
  );
}

export function LaserTypesetter({
  text,
  active,
  onComplete,
}: {
  text: string;
  active: boolean;
  onComplete?: () => void;
}) {
  const [reduceMotion, setReduceMotion] = React.useState(false);
  const [visible, setVisible] = React.useState(active ? '' : text);
  const [width, setWidth] = React.useState(0);
  const progress = useSharedValue(active ? 0 : 1);

  React.useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion);
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduceMotion);
    return () => sub.remove();
  }, []);

  React.useEffect(() => {
    if (!active || reduceMotion) {
      setVisible(text);
      progress.value = 1;
      if (active) onComplete?.();
      return;
    }

    let cancelled = false;
    let index = 0;
    setVisible('');
    progress.value = 0;
    progress.value = withTiming(1, { duration: Math.max(600, text.length * CHAR_MS) });

    const tick = () => {
      if (cancelled) return;
      index += 1;
      setVisible(text.slice(0, index));
      if (index >= text.length) {
        onComplete?.();
        return;
      }
      setTimeout(tick, CHAR_MS);
    };

    const timer = setTimeout(tick, CHAR_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [active, onComplete, progress, reduceMotion, text]);

  const beamStyle = useAnimatedStyle(() => ({
    opacity: active && !reduceMotion ? 1 : 0,
    transform: [{ translateX: Math.max(0, width - 108) * progress.value }],
  }));

  const onLayout = React.useCallback((event: LayoutChangeEvent) => {
    setWidth(event.nativeEvent.layout.width);
  }, []);

  return (
    <View onLayout={onLayout} style={styles.container}>
      <Text selectable accessibilityLiveRegion="polite" style={styles.text}>
        {visible}
      </Text>
      <Animated.View pointerEvents="none" style={[styles.beam, beamStyle]}>
        <OpticalHead />
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    minHeight: 118,
    position: 'relative',
    overflow: 'hidden',
  },
  text: {
    color: '#20282B',
    fontSize: 18,
    lineHeight: 29,
    letterSpacing: -0.1,
  },
  beam: {
    position: 'absolute',
    top: 1,
    left: -108,
    width: 116,
    height: 42,
  },
  beamCanvas: {
    width: 116,
    height: 42,
  },
});
