import React from 'react';
import { StyleSheet, View } from 'react-native';
import { palette } from '../theme';

export function ParallaxLogo({ size = 44 }: { size?: number }) {
  const ringWidth = Math.max(1.5, size * 0.045);
  const body = size * 0.34;
  return (
    <View
      accessibilityLabel="Parallax orbital planet mark"
      testID="parallax-orbital-logo"
      style={[styles.root, { width: size, height: size }]}
    >
      <View
        style={[
          styles.orbit,
          {
            width: size * 0.82,
            height: size * 0.34,
            borderRadius: size,
            borderWidth: ringWidth,
            borderColor: palette.teal600,
            transform: [{ rotate: '-24deg' }],
          },
        ]}
      />
      <View
        style={[
          styles.orbit,
          {
            width: size * 0.78,
            height: size * 0.31,
            borderRadius: size,
            borderWidth: ringWidth,
            borderColor: palette.olive500,
            transform: [{ rotate: '28deg' }],
          },
        ]}
      />
      <View
        style={[
          styles.planet,
          {
            width: body,
            height: body,
            borderRadius: body / 2,
          },
        ]}
      />
      <View
        style={[
          styles.highlight,
          {
            width: body * 0.26,
            height: body * 0.18,
            borderRadius: body,
            left: size * 0.5 - body * 0.2,
            top: size * 0.5 - body * 0.22,
          },
        ]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { position: 'relative', alignItems: 'center', justifyContent: 'center' },
  orbit: { position: 'absolute' },
  planet: {
    backgroundColor: palette.rust600,
    shadowColor: palette.rust700,
    shadowOpacity: 0.18,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
  },
  highlight: { position: 'absolute', backgroundColor: 'rgba(255,255,255,0.34)' },
});
