import React from 'react';
import {
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from 'react-native';
import { EngineeringRunStatus } from './components/EngineeringRunStatus';
import { WorkSpecificationStatus } from './components/WorkSpecificationStatus';
import { useEngineeringRun } from './hooks/useEngineeringRun';
import { useWorkSpecification } from './hooks/useWorkSpecification';
import { api, type ConversationDto, type MessageDto } from './lib/api';
import { palette } from './theme';

function StaticMark({ size = 34 }: { size?: number }) {
  return (
    <View accessibilityLabel="Parallax" style={[styles.mark, { width: size, height: size, borderRadius: size / 2 }]}>
      <View style={[styles.markPlaneA, { width: size * 0.56, height: size * 0.28, borderRadius: size * 0.15 }]} />
      <View style={[styles.markPlaneB, { width: size * 0.56, height: size * 0.28, borderRadius: size * 0.15 }]} />
      <View style={[styles.markCenter, { width: size * 0.08, height: size * 0.08, borderRadius: size * 0.04 }]} />
    </View>
  );
}

function modeLabel(mode: ConversationDto['mode']): string {
  return mode === 'code' ? 'Build' : 'Ask';
}

function conversationStatus(status: ConversationDto['status']): string {
  return status === 'SPEC_AMENDMENT'
    ? 'Reduced graphics mode · request changed'
    : 'Reduced graphics mode · ready';
}

export default function FallbackApp() {
  const { width } = useWindowDimensions();
  const compact = width < 760;
  const [mode, setMode] = React.useState<'reason' | 'code'>('reason');
  const [draft, setDraft] = React.useState('');
  const [status, setStatus] = React.useState('Reduced graphics mode');
  const [conversation, setConversation] = React.useState<ConversationDto | null>(null);
  const [messages, setMessages] = React.useState<MessageDto[]>([]);
  const [recent, setRecent] = React.useState<ConversationDto[]>([]);
  const conversationId = conversation?.id ?? null;
  const workSpecification = useWorkSpecification(conversationId);
  const engineering = useEngineeringRun(conversationId, mode === 'code');
  const canDraftWorkSpecification = messages.some((message) => message.role === 'user');

  React.useEffect(() => {
    const saved = globalThis.localStorage?.getItem('parallax:p2:draft');
    if (saved) setDraft(saved);
    let cancelled = false;
    (async () => {
      try {
        const conversations = await api.listConversations();
        const current = conversations[0] ?? (await api.createConversation('reason'));
        if (cancelled) return;
        setRecent(conversations.length ? conversations : [current]);
        setConversation(current);
        setMode(current.mode);
        setMessages(current.messages);
        setStatus(conversationStatus(current.status));
      } catch {
        if (!cancelled) setStatus('Reduced graphics mode · unavailable');
      }
    })();
    return () => { cancelled = true; };
  }, []);

  React.useEffect(() => {
    globalThis.localStorage?.setItem('parallax:p2:draft', draft);
  }, [draft]);

  async function newConversation(nextMode = mode) {
    try {
      const created = await api.createConversation(nextMode);
      setConversation(created);
      setRecent((current) => [created, ...current.filter((item) => item.id !== created.id)]);
      setMessages([]);
      setMode(nextMode);
      setStatus('Reduced graphics mode · ready');
    } catch {
      setStatus('Reduced graphics mode · unavailable');
    }
  }

  async function openConversation(item: ConversationDto) {
    try {
      const fresh = await api.getConversation(item.id);
      setConversation(fresh);
      setMessages(fresh.messages);
      setMode(fresh.mode);
      setStatus(conversationStatus(fresh.status));
    } catch {
      setStatus('Reduced graphics mode · unavailable');
    }
  }

  async function submit() {
    const content = draft.trim();
    if (!content) return;
    try {
      let current = conversation;
      if (!current) {
        current = await api.createConversation(mode);
        setConversation(current);
      }
      const user: MessageDto = {
        id: `fallback-user-${Date.now()}`,
        role: 'user',
        content,
        status: 'pending',
        created_at: new Date().toISOString(),
      };
      setMessages((value) => [...value, user]);
      setDraft('');
      setStatus('Working through your request…');
      const result = await api.streamResponse(current.id, content);
      const assistant: MessageDto = {
        id: result.messageId ?? `fallback-assistant-${Date.now()}`,
        role: 'assistant',
        content: result.text,
        status: 'complete',
        created_at: new Date().toISOString(),
      };
      setMessages((value) => [...value.filter((item) => item.id !== user.id), { ...user, status: 'complete' }, assistant]);
      const fresh = await api.getConversation(current.id).catch(() => null);
      if (fresh) {
        setConversation(fresh);
        setRecent((value) => [fresh, ...value.filter((item) => item.id !== fresh.id)]);
      }
      setStatus(result.phase === 'SPEC_AMENDMENT'
        ? 'Reduced graphics mode · request changed'
        : 'Reduced graphics mode · ready');
    } catch {
      setStatus('Reduced graphics mode · something went wrong');
    }
  }

  return (
    <SafeAreaView style={styles.root}>
      <View style={styles.shell}>
        {!compact && (
          <View style={styles.rail}>
            <View style={styles.brandRow}>
              <StaticMark size={38} />
              <View><Text style={styles.brand}>Parallax</Text><Text style={styles.brandSub}>Reduced graphics</Text></View>
            </View>
            <View style={styles.railHeading}>
              <Text style={styles.railLabel}>Recent</Text>
              <TouchableOpacity accessibilityRole="button" accessibilityLabel="New conversation" onPress={() => void newConversation()} style={styles.newChatButton}><Text style={styles.newChat}>＋ New</Text></TouchableOpacity>
            </View>
            <ScrollView>
              {recent.slice(0, 12).map((item) => (
                <TouchableOpacity accessibilityRole="button" accessibilityLabel={`Open ${item.title}`} key={item.id} onPress={() => void openConversation(item)} style={item.id === conversation?.id ? styles.railItemActive : styles.railItem}>
                  <Text numberOfLines={2} style={styles.railItemText}>{item.title}</Text>
                  <Text style={styles.railMuted}>{modeLabel(item.mode)}</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
        )}

        <View style={styles.main}>
          <View style={styles.topbar}>
            <View style={styles.identity}>
              {compact && <StaticMark size={32} />}
              <View><Text style={styles.title}>Parallax</Text><Text style={styles.status}>{status}</Text></View>
            </View>
            <View accessibilityLabel="Choose what you want to do" style={styles.modeSwitch}>
              {(['reason', 'code'] as const).map((item) => {
                const label = modeLabel(item);
                return (
                  <TouchableOpacity accessibilityRole="button" accessibilityLabel={label} accessibilityState={{ selected: mode === item }} key={item} onPress={() => void newConversation(item)} style={[styles.modeButton, mode === item && styles.modeActive]}>
                    <Text style={[styles.modeText, mode === item && styles.modeTextActive]}>{label}</Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>

          <WorkSpecificationStatus
            specification={workSpecification.specification}
            busy={workSpecification.busy}
            error={workSpecification.error}
            canDraft={canDraftWorkSpecification}
            onDraft={() => void workSpecification.draft()}
            onApprove={() => void workSpecification.approve()}
          />

          {mode === 'code' && engineering.run && (
            <EngineeringRunStatus
              run={engineering.run}
              busy={engineering.busy}
              onPause={() => void engineering.pause()}
              onResume={() => void engineering.resume()}
              onCancel={() => void engineering.cancel()}
            />
          )}

          <ScrollView style={styles.threadScroll} contentContainerStyle={styles.thread} keyboardShouldPersistTaps="handled">
            {messages.length === 0 && (
              <View style={styles.empty}>
                <StaticMark size={44} />
                <Text style={styles.emptyTitle}>A simpler display is active.</Text>
                <Text style={styles.emptyCopy}>Parallax can keep working with fewer visual effects. Your conversation and saved work remain available.</Text>
              </View>
            )}
            {messages.map((message) => message.role === 'user' ? (
              <View key={message.id} style={styles.userBubble}><Text selectable style={styles.userText}>{message.content}</Text></View>
            ) : message.role === 'assistant' ? (
              <View key={message.id} style={styles.assistantBlock}>
                <View style={styles.assistantHead}><StaticMark size={28} /><Text style={styles.assistantName}>Parallax</Text></View>
                <Text selectable accessibilityLiveRegion="polite" style={styles.assistantText}>{message.content}</Text>
              </View>
            ) : null)}
          </ScrollView>

          <View style={styles.composerWrap}>
            <View style={styles.composer}>
              <TextInput
                accessibilityLabel="Message Parallax"
                value={draft}
                onChangeText={setDraft}
                placeholder="Message Parallax…"
                placeholderTextColor={palette.muted}
                style={styles.input}
                multiline
                onSubmitEditing={() => void submit()}
              />
              <TouchableOpacity accessibilityRole="button" accessibilityLabel="Send message" onPress={() => void submit()} style={styles.send}><Text style={styles.sendText}>↑</Text></TouchableOpacity>
            </View>
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: palette.void },
  shell: { flex: 1, flexDirection: 'row' },
  mark: { position: 'relative', alignItems: 'center', justifyContent: 'center' },
  markPlaneA: { position: 'absolute', borderWidth: 1.4, borderColor: palette.teal600, transform: [{ rotate: '-28deg' }] },
  markPlaneB: { position: 'absolute', borderWidth: 1.2, borderColor: palette.olive500, transform: [{ rotate: '28deg' }] },
  markCenter: { backgroundColor: palette.rust600 },
  rail: { width: 230, padding: 18, borderRightWidth: StyleSheet.hairlineWidth, borderRightColor: palette.border, backgroundColor: palette.forest950 },
  brandRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 26 },
  brand: { fontSize: 18, lineHeight: 22, fontWeight: '700', color: palette.ivory50 },
  brandSub: { fontSize: 12, lineHeight: 16, color: palette.olive200, marginTop: 2 },
  railHeading: { minHeight: 44, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 },
  railLabel: { fontSize: 12, lineHeight: 16, color: palette.muted, letterSpacing: 0.8, textTransform: 'uppercase', fontWeight: '800' },
  newChatButton: { minHeight: 44, paddingHorizontal: 8, alignItems: 'center', justifyContent: 'center' },
  newChat: { fontSize: 13, lineHeight: 18, color: palette.teal500, fontWeight: '700' },
  railItem: { minHeight: 48, justifyContent: 'center', paddingHorizontal: 10, paddingVertical: 8, marginBottom: 3 },
  railItemActive: { minHeight: 48, justifyContent: 'center', paddingHorizontal: 10, paddingVertical: 8, marginBottom: 3, borderRadius: 12, backgroundColor: 'rgba(196,74,27,0.22)', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.borderStrong },
  railItemText: { color: palette.cream100, fontSize: 14, lineHeight: 19 },
  railMuted: { color: palette.muted, fontSize: 12, lineHeight: 16, marginTop: 3 },
  main: { flex: 1, minWidth: 0, minHeight: 0, backgroundColor: palette.ivory50 },
  topbar: { minHeight: 72, paddingHorizontal: 18, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border, backgroundColor: 'rgba(251,247,238,0.92)' },
  identity: { flex: 1, minWidth: 0, flexDirection: 'row', alignItems: 'center', gap: 9 },
  title: { color: palette.text, fontSize: 18, lineHeight: 22, fontWeight: '600' },
  status: { color: palette.textSecondary, fontSize: 13, lineHeight: 18, marginTop: 2 },
  modeSwitch: { minHeight: 48, flexDirection: 'row', padding: 2, borderRadius: 14, backgroundColor: palette.glassSoft, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  modeButton: { minHeight: 44, minWidth: 60, paddingHorizontal: 11, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  modeActive: { backgroundColor: palette.rust600 },
  modeText: { fontSize: 14, lineHeight: 18, color: palette.textSecondary, fontWeight: '800' },
  modeTextActive: { color: palette.ivory50 },
  threadScroll: { flex: 1, minHeight: 0 },
  thread: { width: '100%', maxWidth: 780, alignSelf: 'center', paddingHorizontal: 18, paddingTop: 42, paddingBottom: 28 },
  empty: { maxWidth: 560, alignSelf: 'center', alignItems: 'center', paddingTop: 90 },
  emptyTitle: { color: palette.text, fontSize: 22, lineHeight: 28, fontWeight: '600', marginTop: 14, textAlign: 'center' },
  emptyCopy: { color: palette.textSecondary, fontSize: 16, lineHeight: 24, marginTop: 8, textAlign: 'center' },
  userBubble: { alignSelf: 'flex-end', maxWidth: 560, padding: 16, marginBottom: 30, borderRadius: 20, borderBottomRightRadius: 6, backgroundColor: palette.teal100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  userText: { color: palette.text, fontSize: 16, lineHeight: 24 },
  assistantBlock: { maxWidth: 700, padding: 20, marginBottom: 30, borderRadius: 22, backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  assistantHead: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 10 },
  assistantName: { color: palette.olive700, fontSize: 14, lineHeight: 18, fontWeight: '700' },
  assistantText: { color: palette.text, fontSize: 17, lineHeight: 27 },
  composerWrap: { flexShrink: 0, padding: 16 },
  composer: { maxWidth: 740, width: '100%', alignSelf: 'center', flexDirection: 'row', alignItems: 'flex-end', gap: 8, padding: 8, borderRadius: 22, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.borderStrong, backgroundColor: palette.glassStrong },
  input: { flex: 1, minHeight: 44, maxHeight: 110, paddingHorizontal: 12, paddingVertical: 10, color: palette.charcoal950, fontSize: 16 },
  send: { width: 46, height: 46, borderRadius: 23, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.teal600 },
  sendText: { color: palette.ivory50, fontSize: 19 },
});