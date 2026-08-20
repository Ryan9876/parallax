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
  Platform,
} from 'react-native';
import { LivingSurface } from './components/LivingSurface';
import { LaserTypesetter } from './components/LaserTypesetter';
import { ParallaxLogo } from './components/ParallaxLogo';
import { initialResponseState, motionForPhase, responseReducer } from './state/responseState';
import { api } from './lib/api';

const DEMO_RESPONSE =
  'Parallax 2.0 keeps the conversation calm while the system underneath becomes more capable. The living surface carries the sense of active intelligence, and the optical head inscribes the response directly into place. Spec-first contracts and DSPy optimization stay behind the experience instead of becoming interface clutter.';

export default function App() {
  const { width } = useWindowDimensions();
  const compact = width < 760;
  const [mode, setMode] = React.useState<'reason' | 'code'>('reason');
  const [draft, setDraft] = React.useState('');
  const [lastUserMessage, setLastUserMessage] = React.useState(
    'Build Parallax 2.0 so the experience feels alive without losing the calm interface.',
  );
  const [state, dispatch] = React.useReducer(responseReducer, initialResponseState);
  const [conversationId, setConversationId] = React.useState<string | null>(null);
  const motion = motionForPhase(state.phase);

  React.useEffect(() => {
    if (Platform.OS !== 'web') return;
    const saved = globalThis.localStorage?.getItem('parallax:p2:draft');
    if (saved) setDraft(saved);
  }, []);

  React.useEffect(() => {
    if (Platform.OS !== 'web') return;
    globalThis.localStorage?.setItem('parallax:p2:draft', draft);
  }, [draft]);

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const conversations = await api.listConversations();
        const current = conversations[0] ?? (await api.createConversation(mode));
        if (cancelled) return;
        setConversationId(current.id);
        const lastUser = [...current.messages].reverse().find((message) => message.role === 'user');
        if (lastUser) setLastUserMessage(lastUser.content);
      } catch {
        // The visual shell remains fully usable before the local API is started.
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const respond = React.useCallback(() => {
    if (state.phase !== 'IDLE' && state.phase !== 'COMPLETE' && state.phase !== 'ERROR') return;
    if (draft.trim()) {
      const content = draft.trim();
      setLastUserMessage(content);
      setDraft('');
      if (conversationId) void api.appendMessage(conversationId, 'user', content).catch(() => undefined);
    }
    if (state.phase !== 'IDLE') dispatch({ type: 'RESET' });
    requestAnimationFrame(() => dispatch({ type: 'START_THINKING' }));
    setTimeout(() => dispatch({ type: 'START_RESPONDING' }), 650);
  }, [conversationId, draft, state.phase]);

  const finishPrint = React.useCallback(() => {
    if (state.phase !== 'RESPONDING') return;
    dispatch({ type: 'START_VERIFYING' });
    if (conversationId) void api.appendMessage(conversationId, 'assistant', DEMO_RESPONSE).catch(() => undefined);
    setTimeout(() => dispatch({ type: 'COMPLETE' }), 500);
  }, [conversationId, state.phase]);

  return (
    <View style={styles.root}>
      <LivingSurface energy={motion.surfaceEnergy} />
      <SafeAreaView style={styles.safe}>
        <View style={styles.shell}>
          {!compact && (
            <View style={styles.rail}>
              <View style={styles.brandRow}>
                <ParallaxLogo size={42} />
                <View>
                  <Text style={styles.brand}>Parallax</Text>
                  <Text style={styles.brandSub}>2.0</Text>
                </View>
              </View>
              <Text style={styles.railLabel}>Recent</Text>
              <TouchableOpacity style={styles.railItemActive}>
                <Text style={styles.railItemText}>Designing Parallax 2.0</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.railItem}>
                <Text style={styles.railMuted}>New conversation</Text>
              </TouchableOpacity>
              <View style={styles.railBottom}>
                <Text style={styles.railStatus}>SPEC P2-V0.1.0</Text>
                <Text style={styles.railMuted}>Persistent context foundation</Text>
              </View>
            </View>
          )}

          <View style={styles.main}>
            <View style={styles.topbar}>
              <View style={styles.topbarTitleRow}>
                {compact && <ParallaxLogo size={36} />}
                <View>
                  <Text style={styles.topTitle}>Parallax</Text>
                  <Text style={styles.topSub}>{state.phase.toLowerCase()}</Text>
                </View>
              </View>
              <View style={styles.modeSwitch}>
                {(['reason', 'code'] as const).map((item) => (
                  <TouchableOpacity
                    key={item}
                    accessibilityRole="button"
                    accessibilityState={{ selected: mode === item }}
                    onPress={() => setMode(item)}
                    style={[styles.modeButton, mode === item && styles.modeButtonActive]}
                  >
                    <Text style={[styles.modeText, mode === item && styles.modeTextActive]}>{item}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>

            <ScrollView contentContainerStyle={styles.thread}>
              <View style={styles.userBlock}>
                <Text style={styles.meta}>You</Text>
                <View style={styles.userBubble}>
                  <Text style={styles.userText}>{lastUserMessage}</Text>
                </View>
              </View>

              <View style={styles.assistantBlock}>
                <View style={styles.assistantHead}>
                  <ParallaxLogo size={34} />
                  <View>
                    <Text style={styles.assistantName}>Parallax 2.0</Text>
                    <Text style={styles.meta}>{mode === 'reason' ? 'Reason' : 'Code'} · {state.phase}</Text>
                  </View>
                </View>
                <View style={styles.responseGlass}>
                  <LaserTypesetter
                    text={DEMO_RESPONSE}
                    active={state.phase === 'RESPONDING'}
                    onComplete={finishPrint}
                  />
                  <View style={styles.statusRow}>
                    <View style={[styles.statusDot, motion.laserActive && styles.statusDotActive]} />
                    <Text style={styles.statusText}>
                      {state.phase === 'RESPONDING' ? 'Optical renderer active' : state.phase.toLowerCase()}
                    </Text>
                  </View>
                </View>
              </View>
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
                  onSubmitEditing={respond}
                />
                <TouchableOpacity accessibilityRole="button" onPress={respond} style={styles.send}>
                  <Text style={styles.sendText}>↑</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F3EE' },
  safe: { flex: 1 },
  shell: { flex: 1, flexDirection: 'row' },
  rail: {
    width: 220,
    borderRightWidth: StyleSheet.hairlineWidth,
    borderRightColor: 'rgba(32,40,43,0.12)',
    backgroundColor: 'rgba(242,241,236,0.68)',
    padding: 18,
  },
  brandRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 32 },
  brand: { fontSize: 15, fontWeight: '700', color: '#20282B' },
  brandSub: { fontSize: 11, color: '#9A7F71', marginTop: 1 },
  railLabel: { fontSize: 10, textTransform: 'uppercase', letterSpacing: 1.4, color: '#8A9091', marginBottom: 8 },
  railItemActive: { padding: 11, borderRadius: 13, backgroundColor: 'rgba(255,255,255,0.54)' },
  railItem: { padding: 11 },
  railItemText: { fontSize: 12, color: '#20282B' },
  railMuted: { fontSize: 11, color: '#8A9091' },
  railBottom: { marginTop: 'auto', gap: 4 },
  railStatus: { fontSize: 9, color: '#147D9F', letterSpacing: 0.8 },
  main: { flex: 1, minWidth: 0 },
  topbar: {
    minHeight: 64,
    paddingHorizontal: 18,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(32,40,43,0.10)',
    backgroundColor: 'rgba(248,247,243,0.40)',
  },
  topbarTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 9 },
  topTitle: { fontSize: 16, fontWeight: '650', color: '#20282B' },
  topSub: { fontSize: 10, color: '#9A7F71', marginTop: 2 },
  modeSwitch: { flexDirection: 'row', borderRadius: 13, padding: 3, backgroundColor: 'rgba(255,255,255,0.38)' },
  modeButton: { paddingHorizontal: 10, paddingVertical: 7, borderRadius: 10 },
  modeButtonActive: { backgroundColor: '#20282B' },
  modeText: { fontSize: 10, textTransform: 'uppercase', color: '#7F898B' },
  modeTextActive: { color: '#F4F3EE' },
  thread: { width: '100%', maxWidth: 780, alignSelf: 'center', paddingHorizontal: 18, paddingTop: 42, paddingBottom: 150 },
  userBlock: { alignItems: 'flex-end', marginBottom: 44 },
  meta: { fontSize: 10, color: '#8A9091', marginBottom: 7 },
  userBubble: { maxWidth: 560, borderRadius: 20, borderBottomRightRadius: 6, padding: 16, backgroundColor: 'rgba(255,255,255,0.55)' },
  userText: { fontSize: 15, lineHeight: 23, color: '#20282B' },
  assistantBlock: { width: '100%' },
  assistantHead: { flexDirection: 'row', alignItems: 'center', gap: 9, marginBottom: 12 },
  assistantName: { fontSize: 12, fontWeight: '700', color: '#405055' },
  responseGlass: { borderRadius: 22, padding: 20, backgroundColor: 'rgba(250,250,247,0.58)', borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(255,255,255,0.80)' },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 14 },
  statusDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: 'rgba(20,125,159,0.26)' },
  statusDotActive: { backgroundColor: '#54D8FF' },
  statusText: { fontSize: 10, color: '#678B98' },
  composerWrap: { position: 'absolute', left: 0, right: 0, bottom: 0, padding: 16 },
  composer: { maxWidth: 740, width: '100%', alignSelf: 'center', flexDirection: 'row', gap: 8, padding: 8, borderRadius: 22, backgroundColor: 'rgba(248,247,243,0.78)', borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(255,255,255,0.86)' },
  input: { flex: 1, minWidth: 0, paddingHorizontal: 12, color: '#20282B', fontSize: 14 },
  send: { width: 42, height: 42, borderRadius: 21, alignItems: 'center', justifyContent: 'center', backgroundColor: '#147D9F' },
  sendText: { color: '#FFFFFF', fontSize: 19 },
});
