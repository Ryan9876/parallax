import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import type { PipelineItem } from '../../lib/observabilityProjection';
import { palette } from '../../theme';

function tone(status: PipelineItem['status']) {
  if (status === 'COMPLETE') return styles.complete;
  if (status === 'ACTIVE' || status === 'RECOVERING') return styles.active;
  if (status === 'FAILED') return styles.failed;
  if (status === 'HUMAN_REQUIRED') return styles.review;
  return styles.pending;
}

function displayStage(stage: PipelineItem['stage']) {
  return stage === 'SPECIFY' ? 'SPEC' : stage;
}

export function RunPipeline({ items }: { items: PipelineItem[] }) {
  return (
    <View style={styles.wrap}>
      <View style={styles.headingRow}>
        <Text style={styles.heading}>GOVERNED RUN PIPELINE</Text>
        <Text style={styles.headingNote}>Persisted stage evidence only</Text>
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row} accessibilityLabel="Governed engineering pipeline">
        {items.map((item, index) => (
          <React.Fragment key={item.stage}>
            <View style={styles.item} accessibilityLabel={`${displayStage(item.stage)} ${item.status.toLowerCase().replaceAll('_', ' ')}`}>
              <View style={[styles.node, tone(item.status)]}><Text style={styles.nodeText}>{index + 1}</Text></View>
              <View style={styles.itemCopy}>
                <Text style={styles.stage}>{displayStage(item.stage)}</Text>
                <Text style={styles.status}>{item.status.replaceAll('_', ' ')}</Text>
                {item.sequence ? <Text style={styles.sequence}>evidence #{item.sequence}</Text> : <Text style={styles.sequence}>no stage event</Text>}
              </View>
            </View>
            {index < items.length - 1 ? <View style={styles.connector} /> : null}
          </React.Fragment>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 3 },
  headingRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12, paddingHorizontal: 4 },
  heading: { color: palette.rust600, fontSize: 8, fontWeight: '800', letterSpacing: 1.1 },
  headingNote: { color: palette.charcoal450, fontSize: 8 },
  row: { minHeight: 78, alignItems: 'center', paddingHorizontal: 4, paddingVertical: 7 },
  item: { flexDirection: 'row', alignItems: 'center', gap: 8, minWidth: 118 },
  itemCopy: { minWidth: 0 },
  node: { width: 30, height: 30, borderRadius: 15, alignItems: 'center', justifyContent: 'center', borderWidth: 1 },
  nodeText: { color: palette.charcoal800, fontSize: 10, fontWeight: '800' },
  pending: { backgroundColor: palette.cream100, borderColor: palette.border },
  complete: { backgroundColor: palette.olive200, borderColor: palette.olive500 },
  active: { backgroundColor: palette.teal100, borderColor: palette.teal600 },
  failed: { backgroundColor: palette.rust100, borderColor: palette.rust600 },
  review: { backgroundColor: palette.olive200, borderColor: palette.olive700 },
  stage: { color: palette.charcoal950, fontSize: 9, fontWeight: '800', letterSpacing: 0.45 },
  status: { color: palette.charcoal600, fontSize: 8, marginTop: 1 },
  sequence: { color: palette.charcoal450, fontSize: 7, marginTop: 1 },
  connector: { width: 18, height: 1, marginHorizontal: 4, backgroundColor: palette.border },
});
