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
import { api, type ConversationDto, type MessageDto } from './lib/api';

function StaticMark({ size = 34 }: { size?: number }) {
  return (
    <View accessibilityLabel="Parallax" style={[styles.mark, { width: size, height: size, borderRadius: size / 2 }]}>
      <View style={[styles.markPlaneA, { width: size * 0.56, height: size * 0.28, borderRadius: size * 0.15 }]} />
      <View style={[styles.markPlaneB, { width: size * 0.56, height: size * 0.28, borderRadius: size * 0.15 }]} />
      <View style={[styles.markCenter, { width: size * 0.08, height: size * 0.08, borderRadius: size * 0.04 }]} />
    </View>
  );
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
        setStatus(current.status === 'SPEC_AMENDMENT'
          ? 'Reduced graphics mode · specification amendment required'
          : 'Reduced graphics mode · persistent context online');
      } catch {
        if (!cancelled) setStatus('Reduced graphics mode · API offline');
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
      setStatus('Reduced graphics mode · persistent context online');
    } catch {
      setStatus('Reduced graphics mode · API offline');
    }
  }

  async function openConversation(item: ConversationDto) {
    try {
      const fresh = await api.getConversation(item.id);
      setConversation(fresh);
      setMessages(fresh.messages);
      setMode(fresh.mode);
      setStatus(fresh.status === 'SPEC_AMENDMENT'
        ? 'Reduced graphics mode · specification amendment required'
        : 'Reduced graphics mode · persistent context online');
    } catch {
      setStatus('Reduced graphics mode · API offline');
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
      setStatus('Thinking…');
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
        ? 'Reduced graphics mode · specification amendment required'
        : 'Reduced graphics mode · complete');
    } catch (error) {
      setStatus(`Reduced graphics mode · ${error instanceof Error ? error.message : 'response failed'}`);
    }
  }

  return (
    <SafeAreaView style={styles.root}>
      <View style={styles.shell}>
        {!compact && (
          <View style={styles.rail}>
            <View style={styles.brandRow}>
              <StaticMark size={38} />
              <View><Text style={styles.brand}>Parallax</Text><Text style={styles.brandSub}>2.0</Text></View>
            </View>
            <View style={styles.railHeading}>
              <Text style={styles.railLabel}>Recent</Text>
              <TouchableOpacity onPress={() => void newConversation()}><Text style={styles.newChat}>＋ New</Text></TouchableOpacity>
            </View>
            <ScrollView>
              {recent.slice(0, 12).map((item) => (
                <TouchableOpacity key={item.id} onPress={() => void openConversation(item)} style={item.id === conversation?.id ? styles.railItemActive : styles.railItem}>
                  <Text numberOfLines={2} style={styles.railItemText}>{item.title}</Text>
                  <Text style={styles.railMuted}>{item.mode}</Text>
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
            <View style={styles.modeSwitch}>
              {(['reason', 'code'] as const).map((item) => (
                <TouchableOpacity key={item} onPress={() => void newConversation(item)} style={[styles.modeButton, mode === item && styles.modeActive]}>
                  <Text style={[styles.modeText, mode === item && styles.modeTextActive]}>{item}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          <ScrollView contentContainerStyle={styles.thread} keyboardShouldPersistTaps="handled">
            {messages.length === 0 && (
              <View style={styles.empty}>
                <StaticMark size={44} />
                <Text style={styles.emptyTitle}>Graphics reduced. Conversation preserved.</Text>
                <Text style={styles.emptyCopy}>Parallax can continue without Skia. Messages remain normal selectable text and durable server-side context remains available.</Text>
              </View>
            )}
            {messages.map((message) => message.role === 'user' ? (
              <View key={message.id} style={styles.userBubble}><Text selectable style={styles.userText}>{message.content}</Text></View>
            ) : message.role === 'assistant' ? (
              <View key={message.id} style={styles.assistantBlock}>
                <View style={styles.assistantHead}><StaticMark size={28} /><Text style={styles.assistantName}>Parallax 2.0</Text></View>
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
                placeholderTextColor="#8A9496"
                style={styles.input}
                multiline
                onSubmitEditing={() => void submit()}
              />
              <TouchableOpacity accessibilityLabel="Send message" onPress={() => void submit()} style={styles.send}><Text style={styles.sendText}>↑</Text></TouchableOpacity>
            </View>
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F3EE' },
  shell: { flex: 1, flexDirection: 'row' },
  mark: { position: 'relative', alignItems: 'center', justifyContent: 'center' },
  markPlaneA: { position: 'absolute', borderWidth: 1.4, borderColor: '#147D9F', transform: [{ rotate: '-28deg' }] },
  markPlaneB: { position: 'absolute', borderWidth: 1.2, borderColor: '#8AA7AE', transform: [{ rotate: '28deg' }] },
  markCenter: { backgroundColor: '#147D9F' },
  rail: { width: 220, padding: 18, borderRightWidth: StyleSheet.hairlineWidth, borderRightColor: 'rgba(32,40,43,0.12)', backgroundColor: '#F0EFEA' },
  brandRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 30 },
  brand: { fontSize: 15, fontWeight: '700', color: '#20282B' },
  brandSub: { fontSize: 11, color: '#9A7F71' },
  railHeading: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  railLabel: { fontSize: 10, color: '#8A9091', letterSpacing: 1.2, textTransform: 'uppercase' },
  newChat: { fontSize: 10, color: '#147D9F', fontWeight: '700' },
  railItem: { padding: 10, marginBottom: 3 },
  railItemActive: { padding: 10, marginBottom: 3, borderRadius: 12, backgroundColor: '#FAFAF7' },
  railItemText: { color: '#20282B', fontSize: 12 },
  railMuted: { color: '#8A9091', fontSize: 10, textTransform: 'capitalize', marginTop: 3 },
  main: { flex: 1, minWidth: 0 },
  topbar: { minHeight: 64, paddingHorizontal: 18, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: 'rgba(32,40,43,0.10)' },
  identity: { flexDirection: 'row', alignItems: 'center', gap: 9 },
  title: { color: '#20282B', fontSize: 16, fontWeight: '600' },
  status: { color: '#9A7F71', fontSize: 10, marginTop: 2 },
  modeSwitch: { flexDirection: 'row', padding: 3, borderRadius: 13, backgroundColor: '#ECECE7' },
  modeButton: { paddingHorizontal: 10, paddingVertical: 7, borderRadius: 10 },
  modeActive: { backgroundColor: '#20282B' },
  modeText: { fontSize: 10, color: '#7F898B', textTransform: 'uppercase' },
  modeTextActive: { color: '#F4F3EE' },
  thread: { width: '100%', maxWidth: 780, alignSelf: 'center', paddingHorizontal: 18, paddingTop: 42, paddingBottom: 150 },
  empty: { maxWidth: 560, alignSelf: 'center', alignItems: 'center', paddingTop: 90 },
  emptyTitle: { color: '#20282B', fontSize: 20, fontWeight: '600', marginTop: 14, textAlign: 'center' },
  emptyCopy: { color: '#738083', fontSize: 13, lineHeight: 21, marginTop: 8, textAlign: 'center' },
  userBubble: { alignSelf: 'flex-end', maxWidth: 560, padding: 16, marginBottom: 30, borderRadius: 20, borderBottomRightRadius: 6, backgroundColor: '#FAFAF7' },
  userText: { color: '#20282B', fontSize: 15, lineHeight: 23 },
  assistantBlock: { maxWidth: 700, padding: 20, marginBottom: 30, borderRadius: 22, backgroundColor: '#FAFAF7' },
  assistantHead: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 10 },
  assistantName: { color: '#405055', fontSize: 12, fontWeight: '700' },
  assistantText: { color: '#20282B', fontSize: 17, lineHeight: 27 },
  composerWrap: { position: 'absolute', left: 0, right: 0, bottom: 0, padding: 16 },
  composer: { maxWidth: 740, width: '100%', alignSelf: 'center', flexDirection: 'row', alignItems: 'flex-end', gap: 8, padding: 8, borderRadius: 22, borderWidth: StyleSheet.hairlineWidth, borderColor: '#DADCD7', backgroundColor: '#FAFAF7' },
  input: { flex: 1, minHeight: 42, maxHeight: 110, paddingHorizontal: 12, paddingVertical: 10, color: '#20282B', fontSize: 14 },
  send: { width: 42, height: 42, borderRadius: 21, alignItems: 'center', justifyContent: 'center', backgroundColor: '#147D9F' },
  sendText: { color: '#FFFFFF', fontSize: 19 },
});
