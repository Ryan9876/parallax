import React from 'react';
import { AccessibilityInfo, StyleSheet, Text, View } from 'react-native';
import { palette } from '../theme';

export function LaserTypesetter({
  text,
  active,
  streamComplete = true,
  onComplete,
}: {
  text: string;
  active: boolean;
  streamComplete?: boolean;
  onComplete?: () => void;
}) {
  const [reduceMotion, setReduceMotion] = React.useState(false);
  const completionRef = React.useRef(onComplete);
  const completionSentRef = React.useRef(false);

  React.useEffect(() => { completionRef.current = onComplete; }, [onComplete]);
  React.useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion);
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduceMotion);
    return () => sub.remove();
  }, []);

  React.useEffect(() => {
    if (!active) {
      completionSentRef.current = false;
      return;
    }
    if (!streamComplete || completionSentRef.current) return;
    const finish = () => {
      if (completionSentRef.current) return;
      completionSentRef.current = true;
      completionRef.current?.();
    };
    if (reduceMotion) {
      queueMicrotask(finish);
      return;
    }
    const timer = setTimeout(finish, 160);
    return () => clearTimeout(timer);
  }, [active, reduceMotion, streamComplete, text]);

  return (
    <View style={styles.container}>
      <Text selectable accessibilityLiveRegion="polite" style={styles.text}>{text}</Text>
      {active && !streamComplete ? (
        <View accessibilityLabel="Live response trace" testID="live-response-trace" style={styles.traceRow}>
          <View style={styles.traceDot} />
          <View style={styles.traceLine} />
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { minHeight: 32 },
  text: { color: palette.charcoal950, fontSize: 17, lineHeight: 28, letterSpacing: -0.12 },
  traceRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 10, width: 58 },
  traceDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: palette.teal600 },
  traceLine: { width: 34, height: 2, borderRadius: 2, backgroundColor: palette.teal100 },
});
