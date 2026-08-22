import React from 'react';
import { AccessibilityInfo, LayoutChangeEvent, StyleSheet, Text, View } from 'react-native';
import { Canvas, Circle, Line, vec } from '@shopify/react-native-skia';
import { palette } from '../theme';

const HOT_TAIL = 8;
const COOL_DELAY_MS = 240;

type MeasuredLine = {
  text: string;
  x: number;
  y: number;
  width: number;
  height: number;
  start: number;
  end: number;
};

type HeadPosition = {
  x: number;
  y: number;
  lineHeight: number;
};

function OpticalHead({ height }: { height: number }) {
  const canvasHeight = Math.max(30, height + 6);
  const center = canvasHeight / 2;
  return (
    <Canvas style={{ width: 48, height: canvasHeight }} pointerEvents="none">
      <Line p1={vec(8, center + 1.4)} p2={vec(34, center + 1.4)} color="rgba(139,156,255,0.34)" strokeWidth={4.2} />
      <Line p1={vec(15, center)} p2={vec(38, center)} color="rgba(209,139,255,0.68)" strokeWidth={1.7} />
      <Line p1={vec(29, center - 1)} p2={vec(40, center - 1)} color="rgba(244,242,255,0.92)" strokeWidth={0.9} />
      <Circle cx={40} cy={center} r={8.0} color="rgba(209,139,255,0.11)" />
      <Circle cx={40} cy={center} r={4.4} color="rgba(125,231,255,0.28)" />
      <Circle cx={40} cy={center} r={2.5} color={palette.cyan} opacity={0.98} />
      <Circle cx={40} cy={center} r={0.9} color={palette.text} opacity={0.98} />
    </Canvas>
  );
}

function indexMeasuredLines(text: string, rawLines: readonly { text: string; x: number; y: number; width: number; height: number }[]): MeasuredLine[] {
  let cursor = 0;
  return rawLines.map((line) => {
    let start = text.indexOf(line.text, cursor);
    if (start < 0) start = cursor;
    const end = Math.min(text.length, start + line.text.length);
    cursor = end;
    while (cursor < text.length && /\s/.test(text[cursor] ?? '')) cursor += 1;
    return { ...line, start, end };
  });
}

function lineForIndex(lines: readonly MeasuredLine[], index: number): MeasuredLine | null {
  if (!lines.length) return null;
  const exact = lines.find((line, lineIndex) => {
    const next = lines[lineIndex + 1];
    return index >= line.start && (!next || index < next.start);
  });
  return exact ?? lines[lines.length - 1] ?? null;
}

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
  const [head, setHead] = React.useState<HeadPosition>({ x: 0, y: 0, lineHeight: 30 });
  const [beamVisible, setBeamVisible] = React.useState(false);
  const [cooled, setCooled] = React.useState(!active);

  const measuredLinesRef = React.useRef<MeasuredLine[]>([]);
  const containerWidthRef = React.useRef(0);
  const completionRef = React.useRef(onComplete);
  const completionSentRef = React.useRef(false);
  const coolTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  React.useEffect(() => { completionRef.current = onComplete; }, [onComplete]);

  React.useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion);
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduceMotion);
    return () => sub.remove();
  }, []);

  const onLayout = React.useCallback((event: LayoutChangeEvent) => {
    containerWidthRef.current = event.nativeEvent.layout.width;
  }, []);

  const updateHead = React.useCallback((index: number) => {
    if (index <= 0) return;
    const measured = lineForIndex(measuredLinesRef.current, index - 1);
    if (measured) {
      const span = Math.max(1, measured.end - measured.start);
      const within = Math.max(0, Math.min(span, index - measured.start));
      setHead({
        x: measured.x + measured.width * (within / span),
        y: measured.y,
        lineHeight: measured.height,
      });
      return;
    }

    const containerWidth = containerWidthRef.current;
    if (containerWidth <= 0) return;
    const approximateLineLength = Math.max(24, Math.floor(containerWidth / 8.7));
    const approximateLine = Math.floor((index - 1) / approximateLineLength);
    const within = index % approximateLineLength;
    setHead({
      x: Math.min(containerWidth, (within / approximateLineLength) * containerWidth),
      y: Math.max(0, approximateLine) * 29,
      lineHeight: 29,
    });
  }, []);

  const onTextLayout = React.useCallback((event: { nativeEvent: { lines: Array<{ text: string; x: number; y: number; width: number; height: number }> } }) => {
    measuredLinesRef.current = indexMeasuredLines(text, event.nativeEvent.lines);
    if (active && text.length > 0 && !reduceMotion) updateHead(text.length);
  }, [active, reduceMotion, text, updateHead]);

  React.useEffect(() => {
    if (coolTimerRef.current) {
      clearTimeout(coolTimerRef.current);
      coolTimerRef.current = null;
    }

    if (!active) {
      setBeamVisible(false);
      setCooled(true);
      completionSentRef.current = false;
      return;
    }

    if (reduceMotion) {
      setBeamVisible(false);
      setCooled(true);
      if (streamComplete && !completionSentRef.current) {
        completionSentRef.current = true;
        queueMicrotask(() => completionRef.current?.());
      }
      return;
    }

    if (text.length > 0) {
      setBeamVisible(!streamComplete);
      setCooled(false);
      requestAnimationFrame(() => updateHead(text.length));
    }

    if (streamComplete) {
      setBeamVisible(text.length > 0);
      coolTimerRef.current = setTimeout(() => {
        setBeamVisible(false);
        setCooled(true);
        if (!completionSentRef.current) {
          completionSentRef.current = true;
          completionRef.current?.();
        }
      }, COOL_DELAY_MS);
    }

    return () => {
      if (coolTimerRef.current) {
        clearTimeout(coolTimerRef.current);
        coolTimerRef.current = null;
      }
    };
  }, [active, reduceMotion, streamComplete, text, updateHead]);

  React.useEffect(() => () => {
    if (coolTimerRef.current) clearTimeout(coolTimerRef.current);
  }, []);

  const coolEnd = cooled ? text.length : Math.max(0, text.length - HOT_TAIL);
  const coolText = text.slice(0, coolEnd);
  const hotText = text.slice(coolEnd);
  const beamHeight = Math.max(30, head.lineHeight + 6);

  return (
    <View onLayout={onLayout} style={styles.container}>
      <View accessible={false} importantForAccessibility="no-hide-descendants" pointerEvents="none">
        <Text onTextLayout={onTextLayout} style={[styles.text, styles.measure]}>{text || ' '}</Text>
      </View>
      <View style={styles.visibleText}>
        <Text selectable accessibilityLiveRegion="polite" style={styles.text}>
          {coolText}
          <Text style={!cooled && hotText ? styles.hotText : undefined}>{hotText}</Text>
        </Text>
      </View>
      {beamVisible && text.length > 0 ? (
        <View
          accessibilityLabel="Optical engraving head"
          testID="optical-engraving-head"
          pointerEvents="none"
          style={[
            styles.beam,
            {
              height: beamHeight,
              transform: [{ translateX: head.x - 40 }, { translateY: head.y - 3 }],
            },
          ]}
        >
          <OpticalHead height={head.lineHeight} />
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { minHeight: 32, position: 'relative', overflow: 'hidden' },
  measure: { opacity: 0 },
  visibleText: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0 },
  text: { color: palette.text, fontSize: 18, lineHeight: 29, letterSpacing: -0.1 },
  hotText: {
    color: '#F1E5FF',
    textShadowColor: 'rgba(194,126,255,0.92)',
    textShadowRadius: 6,
  },
  beam: { position: 'absolute', top: 0, left: 0, width: 48 },
});
