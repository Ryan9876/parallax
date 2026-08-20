import React from 'react';
import { AccessibilityInfo, LayoutChangeEvent, StyleSheet, Text, View } from 'react-native';
import { Canvas, Circle, Line, vec } from '@shopify/react-native-skia';

const CHAR_MS = 14;
const HOT_TAIL = 5;
const START_DELAY_MS = 70;
const COOL_DELAY_MS = 160;

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

function lineForIndex(lines: readonly MeasuredLine[], index: number): MeasuredLine | null {
  if (!lines.length) return null;
  const exact = lines.find((line, lineIndex) => {
    const next = lines[lineIndex + 1];
    return index >= line.start && (!next || index < next.start);
  });
  return exact ?? lines[lines.length - 1] ?? null;
}

function characterDelay(character: string): number {
  if (/[.!?]/.test(character)) return CHAR_MS * 4.2;
  if (/[,;:]/.test(character)) return CHAR_MS * 2.1;
  if (/\s/.test(character)) return CHAR_MS * 0.42;
  return CHAR_MS;
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
  const [visibleCount, setVisibleCount] = React.useState(active ? 0 : text.length);
  const [head, setHead] = React.useState<HeadPosition>({ x: 0, y: 0, lineHeight: 30 });
  const [beamVisible, setBeamVisible] = React.useState(false);
  const [cooled, setCooled] = React.useState(!active);

  const textRef = React.useRef(text);
  const streamCompleteRef = React.useRef(streamComplete);
  const measuredLinesRef = React.useRef<MeasuredLine[]>([]);
  const containerWidthRef = React.useRef(0);
  const completionRef = React.useRef(onComplete);
  const runRef = React.useRef(0);
  const completionSentRef = React.useRef(false);

  React.useEffect(() => {
    textRef.current = text;
  }, [text]);

  React.useEffect(() => {
    streamCompleteRef.current = streamComplete;
  }, [streamComplete]);

  React.useEffect(() => {
    completionRef.current = onComplete;
  }, [onComplete]);

  React.useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion);
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduceMotion);
    return () => sub.remove();
  }, []);

  const onLayout = React.useCallback((event: LayoutChangeEvent) => {
    containerWidthRef.current = event.nativeEvent.layout.width;
  }, []);

  const onTextLayout = React.useCallback((event: { nativeEvent: { lines: Array<{ text: string; x: number; y: number; width: number; height: number }> } }) => {
    measuredLinesRef.current = indexMeasuredLines(text, event.nativeEvent.lines);
  }, [text]);

  const updateHead = React.useCallback((index: number) => {
    if (index <= 0) return;
    const targetText = textRef.current;
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
    const finalLine = Math.max(0, Math.ceil(targetText.length / approximateLineLength) - 1);
    setHead({
      x: Math.min(containerWidth, (within / approximateLineLength) * containerWidth),
      y: Math.min(approximateLine, finalLine) * 29,
      lineHeight: 29,
    });
  }, []);

  React.useEffect(() => {
    if (!active || !reduceMotion) return;
    setVisibleCount(text.length);
    setBeamVisible(false);
    setCooled(true);
    if (streamComplete && !completionSentRef.current) {
      completionSentRef.current = true;
      queueMicrotask(() => completionRef.current?.());
    }
  }, [active, reduceMotion, streamComplete, text]);

  React.useEffect(() => {
    const run = ++runRef.current;
    completionSentRef.current = false;

    if (!active) {
      setVisibleCount(textRef.current.length);
      setBeamVisible(false);
      setCooled(true);
      return;
    }

    if (reduceMotion) return;

    let displayed = 0;
    let budget = -START_DELAY_MS;
    let lastFrame: number | null = null;
    let frame: number | null = null;
    let coolStartedAt: number | null = null;

    setVisibleCount(0);
    setBeamVisible(false);
    setCooled(false);
    setHead({ x: 0, y: 0, lineHeight: 30 });

    const tick = (now: number) => {
      if (run !== runRef.current) return;
      if (lastFrame === null) lastFrame = now;
      budget += Math.min(100, Math.max(0, now - lastFrame));
      lastFrame = now;

      const target = textRef.current;
      let next = displayed;
      while (next < target.length) {
        const delay = characterDelay(target[next] ?? '');
        if (budget < delay) break;
        budget -= delay;
        next += 1;
      }

      if (next !== displayed) {
        displayed = next;
        setVisibleCount(displayed);
        updateHead(displayed);
      }

      const caughtUp = displayed >= target.length;
      const finished = caughtUp && streamCompleteRef.current;

      if (finished) {
        setBeamVisible(false);
        if (coolStartedAt === null) coolStartedAt = now;
        if (now - coolStartedAt >= COOL_DELAY_MS) {
          setCooled(true);
          if (!completionSentRef.current) {
            completionSentRef.current = true;
            completionRef.current?.();
          }
          return;
        }
      } else {
        coolStartedAt = null;
        setBeamVisible(target.length > 0);
      }

      frame = requestAnimationFrame(tick);
    };

    frame = requestAnimationFrame(tick);
    return () => {
      runRef.current += 1;
      if (frame !== null) cancelAnimationFrame(frame);
    };
  }, [active, reduceMotion, updateHead]);

  React.useEffect(() => {
    if (!active) setVisibleCount(text.length);
  }, [active, text]);

  const boundedVisibleCount = Math.min(visibleCount, text.length);
  const coolEnd = cooled ? boundedVisibleCount : Math.max(0, boundedVisibleCount - HOT_TAIL);
  const coolText = text.slice(0, coolEnd);
  const hotText = text.slice(coolEnd, boundedVisibleCount);
  const beamHeight = Math.max(34, head.lineHeight + 8);

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
