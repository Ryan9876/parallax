import React from 'react';
import {
  AccessibilityInfo,
  Animated,
  Easing,
  Image,
  Platform,
  StyleSheet,
  View,
} from 'react-native';
import { palette } from '../theme';
import { PARALLAX_KNOT_URI } from './ParallaxLogoAsset';

export function ParallaxLogo({ size = 44 }: { size?: number }) {
  const [reduceMotion, setReduceMotion] = React.useState(false);
  const spin = React.useRef(new Animated.Value(0)).current;
  const sweep = React.useRef(new Animated.Value(0)).current;

  React.useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion);
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduceMotion);
    return () => sub.remove();
  }, []);

  React.useEffect(() => {
    spin.stopAnimation();
    sweep.stopAnimation();
    spin.setValue(0);
    sweep.setValue(0);
    if (reduceMotion) return;

    const spinLoop = Animated.loop(
      Animated.timing(spin, {
        toValue: 1,
        duration: 36000,
        easing: Easing.linear,
        useNativeDriver: true,
      }),
    );
    const sweepLoop = Animated.loop(
      Animated.sequence([
        Animated.delay(900),
        Animated.timing(sweep, {
          toValue: 1,
          duration: 7600,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
        Animated.delay(1100),
        Animated.timing(sweep, {
          toValue: 0,
          duration: 7200,
          easing: Easing.inOut(Easing.sin),
          useNativeDriver: true,
        }),
      ]),
    );

    spinLoop.start();
    sweepLoop.start();
    return () => {
      spinLoop.stop();
      sweepLoop.stop();
    };
  }, [reduceMotion, spin, sweep]);

  const rotation = spin.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] });
  const sweepX = sweep.interpolate({ inputRange: [0, 1], outputRange: [-size * 1.05, size * 1.05] });
  const sweepY = sweep.interpolate({ inputRange: [0, 1], outputRange: [size * 0.16, -size * 0.12] });

  const webMask = Platform.OS === 'web'
    ? ({
        WebkitMaskImage: `url("${PARALLAX_KNOT_URI}")`,
        maskImage: `url("${PARALLAX_KNOT_URI}")`,
        WebkitMaskRepeat: 'no-repeat',
        maskRepeat: 'no-repeat',
        WebkitMaskPosition: 'center',
        maskPosition: 'center',
        WebkitMaskSize: 'contain',
        maskSize: 'contain',
      } as any)
    : null;

  return (
    <View
      accessibilityLabel="Parallax animated knot mark"
      testID="parallax-knot-logo"
      style={{ width: size, height: size }}
    >
      <Animated.View
        style={[
          styles.rotor,
          {
            width: size,
            height: size,
            transform: [{ rotate: reduceMotion ? '0deg' : rotation }],
          },
        ]}
      >
        <Image
          resizeMode="contain"
          source={{ uri: PARALLAX_KNOT_URI }}
          style={[
            styles.image,
            { width: size, height: size },
            Platform.OS === 'web' ? ({ filter: 'drop-shadow(0 5px 10px rgba(80,55,180,0.28))' } as any) : null,
          ]}
        />

        {!reduceMotion && Platform.OS === 'web' ? (
          <View pointerEvents="none" style={[styles.sweepMask, webMask]}>
            <Animated.View
              style={[
                styles.sweepBand,
                styles.sweepBandCyan,
                {
                  width: size * 0.34,
                  height: size * 1.65,
                  transform: [
                    { translateX: sweepX },
                    { translateY: sweepY },
                    { rotate: '18deg' },
                  ],
                },
              ]}
            />
            <Animated.View
              style={[
                styles.sweepBand,
                styles.sweepBandViolet,
                {
                  width: size * 0.22,
                  height: size * 1.65,
                  transform: [
                    { translateX: Animated.add(sweepX, size * 0.18) },
                    { translateY: sweepY },
                    { rotate: '18deg' },
                  ],
                },
              ]}
            />
          </View>
        ) : null}
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  rotor: {
    position: 'relative',
    alignItems: 'center',
    justifyContent: 'center',
  },
  image: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
  },
  sweepMask: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    overflow: 'hidden',
  },
  sweepBand: {
    position: 'absolute',
    left: '50%',
    top: '-30%',
    borderRadius: 999,
  },
  sweepBandCyan: {
    backgroundColor: 'rgba(125,231,255,0.42)',
    shadowColor: palette.cyan,
    shadowOpacity: 0.48,
    shadowRadius: 12,
  },
  sweepBandViolet: {
    backgroundColor: 'rgba(225,145,255,0.30)',
    shadowColor: palette.violet,
    shadowOpacity: 0.40,
    shadowRadius: 10,
  },
});