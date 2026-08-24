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

export function RunPipeline({ items }: { items: PipelineItem[] }) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row} accessibilityLabel="Governed engineering pipeline">
      {items.map((item, index) => (
        <React.Fragment key={item.stage}>
          <View style={styles.item} accessibilityLabel={`${item.stage} ${item.status.toLowerCase().replace('_', ' ')}`}>
            <View style={[styles.node, tone(item.status)]}><Text style={styles.nodeText}>{index + 1}</Text></View>
            <View>
              <Text style={styles.stage}>{item.stage}</Text>
              <Text style={styles.status}>{item.status.replace('_', ' ')}</Text>
            </View>
          </View>
          {index < items.length - 1 ? <View style={styles.connector} /> : null}
        </React.Fragment>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  row: { minHeight: 68, alignItems: 'center', paddingHorizontal: 4, paddingVertical: 8 },
  item: { flexDirection: 'row', alignItems: 'center', gap: 8, minWidth: 112 },
  node: { width: 28, height: 28, borderRadius: 14, alignItems: 'center', justifyContent: 'center', borderWidth: 1 },
  nodeText: { color: palette.charcoal800, fontSize: 10, fontWeight: '800' },
  pending: { backgroundColor: palette.cream100, borderColor: palette.border },
  complete: { backgroundColor: palette.olive200, borderColor: palette.olive500 },
  active: { backgroundColor: palette.teal100, borderColor: palette.teal600 },
  failed: { backgroundColor: palette.rust100, borderColor: palette.rust600 },
  review: { backgroundColor: palette.olive200, borderColor: palette.olive700 },
  stage: { color: palette.charcoal950, fontSize: 9, fontWeight: '800', letterSpacing: 0.45 },
  status: { color: palette.charcoal450, fontSize: 8, marginTop: 2 },
  connector: { width: 20, height: 1, marginHorizontal: 4, backgroundColor: palette.border },
});
