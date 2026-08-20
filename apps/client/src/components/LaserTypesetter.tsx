import React from 'react';
import { AccessibilityInfo, LayoutChangeEvent, StyleSheet, Text, View } from 'react-native';
import { Canvas, Circle, Line, vec } from '@shopify/react-native-skia';

const CHAR_MS = 24;
const HOT_TAIL = 4;

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
  const canvasHeight = Math.max(34, height + 8);
  const center = canvasHeight / 2;
  return (
    <Canvas style={{ width: 122, height: canvasHeight }} pointerEvents="none">
      <Line p1={vec(0, center)} p2={vec(112, center)} color="rgba(84,216,255,0.34)" strokeWidth={1} />
      <Line p1={vec(112, 3)} p2={vec(112, canvasHeight - 3)} color="#D8F9FF" strokeWidth={2} />
      <Circle cx={112} cy={center} r={5} color="#D8F9FF" />
      <Circle cx={112} cy={center} r={10} color="rgba(84,216,255,0.18)" />
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

function lineForIndex(lines: MeasuredLine[], index: number): MeasuredLine | null {
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
  onComplete,
}: {
  text: string;
  active: boolean;
  onComplete?: () => void;
}) {
  const [reduceMotion, setReduceMotion] = React.useState(false);
  const [visibleCount, setVisibleCount] = React.useState(active ? 0 : text.length);
  const [measuredLines, setMeasuredLines] = React.useState<MeasuredLine[]>([]);
  const [containerWidth, setContainerWidth] = React.useState(0);
  const [head, setHead] = React.useState<HeadPosition>({ x: 0, y: 0, lineHeight: 30 });
  const [beamVisible, setBeamVisible] = React.useState(false);
  const [cooled, setCooled] = React.useState(!active);
  const completionRef = React.useRef(onComplete);
  const runRef = React.useRef(0);

  React.useEffect(() => {
    completionRef.current = onComplete;
  }, [onComplete]);

  React.useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion);
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduceMotion);
    return () => sub.remove();
  }, []);

  const onLayout = React.useCallback((event: LayoutChangeEvent) => {
    setContainerWidth(event.nativeEvent.layout.width);
  }, []);

  const onTextLayout = React.useCallback((event: { nativeEvent: { lines: Array<{ text: string; x: number; y: number; width: number; height: number }> } }) => {
    const next = indexMeasuredLines(text, event.nativeEvent.lines);
    const signature = (lines: MeasuredLine[]) => lines.map((line) => `${line.text}|${line.x}|${line.y}|${line.width}|${line.height}`).join('~');
    setMeasuredLines((current) => (signature(current) === signature(next) ? current : next));
  }, [text]);

  React.useEffect(() => {
    const run = ++runRef.current;

    if (!active || reduceMotion) {
      setVisibleCount(text.length);
      setBeamVisible(false);
      setCooled(true);
      if (active && reduceMotion) queueMicrotask(() => completionRef.current?.());
      return;
    }

    setVisibleCount(0);
    setBeamVisible(true);
    setCooled(false);
    setHead({ x: 0, y: 0, lineHeight: 30 });

    let index = 0;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const step = () => {
      if (run !== runRef.current) return;
      index = Math.min(text.length, index + 1);
      setVisibleCount(index);

      const measured = lineForIndex(measuredLines, Math.max(0, index - 1));
      if (measured) {
        const span = Math.max(1, measured.end - measured.start);
        const within = Math.max(0, Math.min(span, index - measured.start));
        setHead({
          x: measured.x + measured.width * (within / span),
          y: measured.y,
          lineHeight: measured.height,
        });
      } else if (containerWidth > 0) {
        // Graceful web fallback if a renderer does not expose onTextLayout geometry.
        const approximateLineLength = Math.max(24, Math.floor(containerWidth / 8.7));
        const approximateLine = Math.floor(index / approximateLineLength);
        const within = index % approximateLineLength;
        setHead({
          x: Math.min(containerWidth, (within / approximateLineLength) * containerWidth),
          y: approximateLine * 29,
          lineHeight: 29,
        });
      }

      if (index >= text.length) {
        setBeamVisible(false);
        timer = setTimeout(() => {
          if (run !== runRef.current) return;
          setCooled(true);
          completionRef.current?.();
        }, 170);
        return;
      }

      const current = text[index - 1] ?? '';
      const delay = /[.!?]/.test(current) ? CHAR_MS * 5 : /[,;:]/.test(current) ? CHAR_MS * 2.4 : /\s/.test(current) ? CHAR_MS * 0.45 : CHAR_MS;
      timer = setTimeout(step, delay);
    };

    timer = setTimeout(step, 90);
    return () => {
      runRef.current += 1;
      if (timer) clearTimeout(timer);
    };
  }, [active, containerWidth, measuredLines, reduceMotion, text]);

  const coolEnd = cooled ? visibleCount : Math.max(0, visibleCount - HOT_TAIL);
  const coolText = text.slice(0, coolEnd);
  const hotText = text.slice(coolEnd, visibleCount);
  const beamHeight = Math.max(34, head.lineHeight + 8);

  return (
    <View onLayout={onLayout} style={styles.container}>
      <View accessible={false} importantForAccessibility="no-hide-descendants" pointerEvents="none">
        <Text onTextLayout={onTextLayout} style={[styles.text, styles.measure]}>{text}</Text>
      </View>

      <View style={styles.visibleText}>
        <Text selectable accessibilityLiveRegion="polite" style={styles.text}>
          {coolText}
          <Text style={!cooled && hotText ? styles.hotText : undefined}>{hotText}</Text>
        </Text>
      </View>

      {beamVisible && (
        <View
          pointerEvents="none"
          style={[
            styles.beam,
            {
              height: beamHeight,
              transform: [
                { translateX: head.x - 112 },
                { translateY: head.y - 4 },
              ],
            },
          ]}
        >
          <OpticalHead height={head.lineHeight} />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    minHeight: 32,
    position: 'relative',
    overflow: 'hidden',
  },
  measure: {
    opacity: 0,
  },
  visibleText: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
  },
  text: {
    color: '#20282B',
    fontSize: 18,
    lineHeight: 29,
    letterSpacing: -0.1,
  },
  hotText: {
    color: '#36BEEA',
    textShadowColor: 'rgba(84,216,255,0.62)',
    textShadowRadius: 5,
  },
  beam: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: 122,
  },
});
