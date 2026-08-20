import React from 'react';
import {
  Platform,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from 'react-native';
import { LivingSurface } from './components/LivingSurface';
import { LaserTypesetter } from './components/LaserTypesetter';
import { ParallaxLogo } from './components/ParallaxLogo';
import { initialResponseState, motionForPhase, responseReducer } from './state/responseState';
import { api, AuthenticationRequiredError, type ConversationDto, type MessageDto, type ResponseStreamEvent } from './lib/api';
import { EngineeringRunStatus } from './components/EngineeringRunStatus';
import { useEngineeringRun } from './hooks/useEngineeringRun';

const FALLBACK_MESSAGES: MessageDto[] = [
  {
    id: 'fallback-user',
    role: 'user',
    content: 'Build Parallax 2.0 so the experience feels alive without losing the calm interface.',
    status: 'complete',
    created_at: new Date(0).toISOString(),
  },
  {
    id: 'fallback-assistant',
    role: 'assistant',
    content:
      'Parallax 2.0 keeps the conversation calm while the system underneath becomes more capable. The living surface carries the sense of active intelligence, and the optical head inscribes the response directly into place. Spec-first contracts and DSPy optimization stay behind the experience instead of becoming interface clutter.',
    status: 'complete',
    created_at: new Date(0).toISOString(),
  },
];

export default function App() {
  const { width } = useWindowDimensions();
  const compact = width < 760;
  const [mode, setMode] = React.useState<'reason' | 'code'>('reason');
  const [draft, setDraft] = React.useState('');
  const [state, dispatch] = React.useReducer(responseReducer, initialResponseState);
  const [conversationId, setConversationId] = React.useState<string | null>(null);
  const [conversations, setConversations] = React.useState<ConversationDto[]>([]);
  const [messages, setMessages] = React.useState<MessageDto[]>(FALLBACK_MESSAGES);
  const [apiOnline, setApiOnline] = React.useState(false);
  const [activePrintId, setActivePrintId] = React.useState<string | null>(null);
  const [streamFinished, setStreamFinished] = React.useState(true);
  const [accessToken, setAccessToken] = React.useState(() =>
    Platform.OS === 'web' ? globalThis.sessionStorage?.getItem('parallax:p2:access') ?? '' : '',
  );
  const [accessDraft, setAccessDraft] = React.useState(accessToken);
  const [accessError, setAccessError] = React.useState('');
  const pendingRefreshRef = React.useRef<string | null>(null);
  const motion = motionForPhase(state.phase);
  const activeConversation = conversations.find((item) => item.id === conversationId);
  const engineering = useEngineeringRun(conversationId, mode === 'code');

  React.useEffect(() => { api.setAccessToken(accessToken); }, [accessToken]);

  React.useEffect(() => {
    if (Platform.OS !== 'web') return;
    const saved = globalThis.localStorage?.getItem('parallax:p2:draft');
    if (saved) setDraft(saved);
  }, []);

  React.useEffect(() => {
    if (Platform.OS !== 'web') return;
    globalThis.localStorage?.setItem('parallax:p2:draft', draft);
  }, [draft]);

  const updateConversationSummary = React.useCallback((conversation: ConversationDto) => {
    setConversations((current) => {
      const without = current.filter((item) => item.id !== conversation.id);
      return [conversation, ...without];
    });
  }, []);

  const applyConversation = React.useCallback((conversation: ConversationDto) => {
    setConversationId(conversation.id);
    setMode(conversation.mode);
    setMessages(conversation.messages);
    setActivePrintId(null);
    setStreamFinished(true);
    pendingRefreshRef.current = null;
    updateConversationSummary(conversation);
  }, [updateConversationSummary]);

  React.useEffect(() => {
    if (!accessToken) return;
    let cancelled = false;
    (async () => {
      try {
        const existing = await api.listConversations();
        const current = existing[0] ?? (await api.createConversation('reason'));
        if (cancelled) return;
        setApiOnline(true);
        setConversations(existing.length ? existing : [current]);
        applyConversation(current);
      } catch (error) {
        if (cancelled) return;
        if (error instanceof AuthenticationRequiredError) {
          api.setAccessToken('');
          setAccessToken('');
          globalThis.sessionStorage?.removeItem('parallax:p2:access');
          setAccessError('That access credential was not accepted.');
        }
        setApiOnline(false);
        setConversationId(null);
        setMessages(FALLBACK_MESSAGES);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [accessToken, applyConversation]);

  const unlock = React.useCallback(() => {
    const candidate = accessDraft.trim();
    if (!candidate) {
      setAccessError('Enter the private production access credential.');
      return;
    }
    api.setAccessToken(candidate);
    globalThis.sessionStorage?.setItem('parallax:p2:access', candidate);
    setAccessError('');
    setAccessToken(candidate);
  }, [accessDraft]);

  const openConversation = React.useCallback(
    async (conversation: ConversationDto) => {
      if (state.phase === 'THINKING' || state.phase === 'RESPONDING' || state.phase === 'VERIFYING') return;
      try {
        const fresh = await api.getConversation(conversation.id);
        if (state.phase !== 'IDLE') dispatch({ type: 'RESET' });
        applyConversation(fresh);
        setApiOnline(true);
      } catch {
        setApiOnline(false);
      }
    },
    [applyConversation, state.phase],
  );

  const startConversation = React.useCallback(
    async (nextMode: 'reason' | 'code' = mode) => {
      if (state.phase === 'THINKING' || state.phase === 'RESPONDING' || state.phase === 'VERIFYING') return;
      try {
        const created = await api.createConversation(nextMode);
        if (state.phase !== 'IDLE') dispatch({ type: 'RESET' });
        applyConversation(created);
        setMode(nextMode);
        setApiOnline(true);
      } catch {
        setApiOnline(false);
      }
    },
    [applyConversation, mode, state.phase],
  );

  const changeMode = React.useCallback(
    async (nextMode: 'reason' | 'code') => {
      if (nextMode === mode) return;
      // Foundation behavior: a mode switch starts a new durable conversation so
      // the persisted server-side mode and visible mode can never diverge.
      await startConversation(nextMode);
    },
    [mode, startConversation],
  );

  const respond = React.useCallback(async () => {
    if (
      state.phase !== 'IDLE'
      && state.phase !== 'COMPLETE'
      && state.phase !== 'SPEC_AMENDMENT'
      && state.phase !== 'ERROR'
    ) return;
    const content = draft.trim();
    if (!content) return;

    let id = conversationId;
    try {
      if (!id) {
        const created = await api.createConversation(mode);
        id = created.id;
        applyConversation(created);
      }

      const now = Date.now();
      const optimisticUser: MessageDto = {
        id: `local-user-${now}`,
        role: 'user',
        content,
        status: 'pending',
        created_at: new Date().toISOString(),
      };
      const assistantId = `local-assistant-${now}`;
      let assistantStarted = false;
      let scopeAmendment = false;

      setMessages((current) => [...current.filter((message) => !message.id.startsWith('fallback-')), optimisticUser]);
      setDraft('');
      setApiOnline(true);
      setStreamFinished(false);
      pendingRefreshRef.current = id;
      dispatch({ type: 'START_THINKING' });

      const startAssistant = () => {
        if (assistantStarted) return;
        assistantStarted = true;
        setMessages((current) => {
          const completedUser = current.map((message) =>
            message.id === optimisticUser.id ? { ...message, status: 'complete' } : message,
          );
          if (completedUser.some((message) => message.id === assistantId)) return completedUser;
          return [
            ...completedUser,
            {
              id: assistantId,
              role: 'assistant',
              content: '',
              status: 'streaming',
              created_at: new Date().toISOString(),
            },
          ];
        });
        setActivePrintId(assistantId);
        dispatch({ type: 'START_RESPONDING' });
      };

      const requireAmendment = () => {
        if (scopeAmendment) return;
        scopeAmendment = true;
        setStreamFinished(true);
        setActivePrintId(null);
        dispatch({ type: 'REQUIRE_AMENDMENT' });
      };

      const onEvent = (event: ResponseStreamEvent) => {
        if (event.event === 'state') {
          if (event.data.phase === 'SPEC_AMENDMENT') {
            requireAmendment();
            return;
          }
          if (event.data.phase === 'RESPONDING') startAssistant();
          return;
        }

        if (event.event === 'amendment') {
          requireAmendment();
          return;
        }

        if (event.event === 'chunk' && typeof event.data.text === 'string') {
          startAssistant();
          const delta = event.data.text;
          setMessages((current) => current.map((message) =>
            message.id === assistantId ? { ...message, content: message.content + delta } : message,
          ));
        }
      };

      const result = await api.streamResponse(id, content, onEvent);
      if (result.phase === 'SPEC_AMENDMENT' || scopeAmendment) {
        requireAmendment();
        const fresh = await api.getConversation(id);
        applyConversation(fresh);
        return;
      }
      if (!result.text.trim()) throw new Error('Parallax returned an empty response');

      startAssistant();
      setMessages((current) => current.map((message) =>
        message.id === assistantId ? { ...message, content: result.text, status: 'streaming' } : message,
      ));
      setStreamFinished(true);

      // Refresh only the sidebar/title metadata now. Replacing active messages
      // before the optical renderer catches up would remount the typesetter.
      void api.getConversation(id).then(updateConversationSummary).catch(() => undefined);
    } catch (error) {
      setStreamFinished(true);
      setActivePrintId(null);
      setApiOnline(false);
      setMessages((current) => current.map((message) =>
        message.status === 'streaming' ? { ...message, status: 'error' } : message,
      ));
      dispatch({ type: 'FAIL', error: error instanceof Error ? error.message : 'Response failed' });
    }
  }, [applyConversation, conversationId, draft, mode, state.phase, updateConversationSummary]);

  const finishPrint = React.useCallback(
    (messageId: string) => {
      if (state.phase !== 'RESPONDING' || activePrintId !== messageId || !streamFinished) return;
      setMessages((current) => current.map((message) =>
        message.id === messageId ? { ...message, status: 'complete' } : message,
      ));
      setActivePrintId(null);
      dispatch({ type: 'START_VERIFYING' });

      const refreshId = pendingRefreshRef.current;
      setTimeout(() => {
        dispatch({ type: 'COMPLETE' });
        if (!refreshId) return;
        void api.getConversation(refreshId).then((fresh) => {
          setConversationId(fresh.id);
          setMode(fresh.mode);
          setMessages(fresh.messages);
          updateConversationSummary(fresh);
          pendingRefreshRef.current = null;
        }).catch(() => undefined);
      }, 420);
    },
    [activePrintId, state.phase, streamFinished, updateConversationSummary],
  );

  if (!accessToken) {
    return (
      <View style={styles.accessRoot}>
        <View style={styles.accessPanel}>
          <ParallaxLogo size={52} />
          <Text style={styles.accessTitle}>Parallax 2.0</Text>
          <Text style={styles.accessCopy}>Private production access</Text>
          <TextInput
            accessibilityLabel="Private access credential"
            secureTextEntry
            value={accessDraft}
            onChangeText={setAccessDraft}
            onSubmitEditing={unlock}
            placeholder="Access credential"
            placeholderTextColor="#8A9496"
            style={styles.accessInput}
          />
          {accessError ? <Text style={styles.errorText}>{accessError}</Text> : null}
          <TouchableOpacity accessibilityRole="button" onPress={unlock} style={styles.accessButton}>
            <Text style={styles.accessButtonText}>Continue</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

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
              <View style={styles.railHeading}>
                <Text style={styles.railLabel}>Recent</Text>
                <TouchableOpacity onPress={() => void startConversation(mode)} accessibilityRole="button">
                  <Text style={styles.newChat}>＋ New</Text>
                </TouchableOpacity>
              </View>
              <ScrollView style={styles.recentList}>
                {conversations.slice(0, 12).map((conversation) => (
                  <TouchableOpacity
                    key={conversation.id}
                    onPress={() => void openConversation(conversation)}
                    style={conversation.id === conversationId ? styles.railItemActive : styles.railItem}
                  >
                    <Text numberOfLines={2} style={styles.railItemText}>{conversation.title}</Text>
                    <Text style={styles.railMuted}>{conversation.mode}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
              <View style={styles.railBottom}>
                <Text style={styles.railStatus}>SPEC {activeConversation?.spec_id ?? 'P2-V0.3.0'}</Text>
                <Text style={styles.railMuted}>{apiOnline ? 'Persistent context online' : 'Visual fallback · API offline'}</Text>
              </View>
            </View>
          )}

          <View style={styles.main}>
            <View style={styles.topbar}>
              <View style={styles.topbarTitleRow}>
                {compact && <ParallaxLogo size={36} />}
                <View>
                  <Text style={styles.topTitle}>Parallax</Text>
                  <Text style={styles.topSub}>Parallax 2.0 · {state.phase.toLowerCase()}</Text>
                </View>
              </View>
              <View style={styles.modeSwitch}>
                {(['reason', 'code'] as const).map((item) => (
                  <TouchableOpacity
                    key={item}
                    accessibilityRole="button"
                    accessibilityState={{ selected: mode === item }}
                    onPress={() => void changeMode(item)}
                    style={[styles.modeButton, mode === item && styles.modeButtonActive]}
                  >
                    <Text style={[styles.modeText, mode === item && styles.modeTextActive]}>{item}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>

            {mode === 'code' && engineering.run && (
              <EngineeringRunStatus
                run={engineering.run}
                busy={engineering.busy}
                onPause={() => void engineering.pause()}
                onResume={() => void engineering.resume()}
                onCancel={() => void engineering.cancel()}
              />
            )}

            <ScrollView contentContainerStyle={styles.thread} keyboardShouldPersistTaps="handled">
              {messages.length === 0 ? (
                <View style={styles.emptyState}>
                  <ParallaxLogo size={44} />
                  <Text style={styles.emptyTitle}>Start with the outcome.</Text>
                  <Text style={styles.emptyCopy}>Describe what you are trying to accomplish. Parallax will keep the conversation, specification, evidence, and execution state together as the work evolves.</Text>
                </View>
              ) : messages.map((message) => (
                message.role === 'user' ? (
                  <View key={message.id} style={styles.userBlock}>
                    <Text style={styles.meta}>You</Text>
                    <View style={styles.userBubble}>
                      <Text selectable style={styles.userText}>{message.content}</Text>
                    </View>
                  </View>
                ) : message.role === 'assistant' ? (
                  <View key={message.id} style={styles.assistantBlock}>
                    <View style={styles.assistantHead}>
                      <ParallaxLogo size={34} />
                      <View>
                        <Text style={styles.assistantName}>Parallax 2.0</Text>
                        <Text style={styles.meta}>{mode === 'reason' ? 'Reason' : 'Code'} · {message.id === activePrintId ? 'RESPONDING' : 'COMPLETE'}</Text>
                      </View>
                    </View>
                    <View style={styles.responseGlass}>
                      {message.id === activePrintId ? (
                        <LaserTypesetter
                          text={message.content}
                          active
                          streamComplete={streamFinished}
                          onComplete={() => finishPrint(message.id)}
                        />
                      ) : (
                        <Text selectable accessibilityLiveRegion="polite" style={styles.assistantText}>{message.content}</Text>
                      )}
                      {message.id === activePrintId && (
                        <View style={styles.statusRow}>
                          <View style={[styles.statusDot, motion.laserActive && styles.statusDotActive]} />
                          <Text style={styles.statusText}>{streamFinished ? 'Finishing optical inscription' : 'Optical renderer active'}</Text>
                        </View>
                      )}
                    </View>
                  </View>
                ) : null
              ))}

              {state.phase === 'THINKING' && (
                <View style={styles.thinkingRow}>
                  <ParallaxLogo size={26} />
                  <Text style={styles.thinkingText}>Parallax is resolving the active objective…</Text>
                </View>
              )}
              {state.phase === 'VERIFYING' && <Text style={styles.phaseHint}>Verifying response…</Text>}
              {state.phase === 'SPEC_AMENDMENT' && (
                <View style={styles.amendmentNotice} accessibilityLiveRegion="polite">
                  <Text style={styles.amendmentTitle}>Specification amendment required</Text>
                  <Text style={styles.amendmentText}>
                    The conversation is preserved. Parallax has stopped substantive work against the prior approved objective until the scope is clarified or amended.
                  </Text>
                </View>
              )}
              {state.phase === 'ERROR' && <Text style={styles.errorText}>{state.error ?? 'Response failed. Your conversation is preserved.'}</Text>}
            </ScrollView>

            <View style={styles.composerWrap}>
              <View style={styles.composer}>
                {compact && (
                  <TouchableOpacity onPress={() => void startConversation(mode)} style={styles.newMobile} accessibilityLabel="New conversation">
                    <Text style={styles.newMobileText}>＋</Text>
                  </TouchableOpacity>
                )}
                <TextInput
                  accessibilityLabel="Message Parallax"
                  value={draft}
                  onChangeText={setDraft}
                  placeholder="Message Parallax…"
                  placeholderTextColor="#8A9496"
                  style={styles.input}
                  onSubmitEditing={() => void respond()}
                  multiline
                />
                <TouchableOpacity accessibilityRole="button" accessibilityLabel="Send message" onPress={() => void respond()} style={styles.send}>
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
  accessRoot: { flex: 1, backgroundColor: '#F4F3EE', alignItems: 'center', justifyContent: 'center', padding: 24 },
  accessPanel: { width: '100%', maxWidth: 390, alignItems: 'center', borderRadius: 24, padding: 28, backgroundColor: 'rgba(250,250,247,0.72)' },
  accessTitle: { color: '#20282B', fontSize: 24, fontWeight: '700', marginTop: 14 },
  accessCopy: { color: '#738083', fontSize: 13, marginTop: 5, marginBottom: 22 },
  accessInput: { width: '100%', minHeight: 48, borderRadius: 14, paddingHorizontal: 14, color: '#20282B', backgroundColor: 'rgba(255,255,255,0.7)', borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(32,40,43,0.16)' },
  accessButton: { width: '100%', minHeight: 46, borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: '#147D9F', marginTop: 8 },
  accessButtonText: { color: '#FFFFFF', fontSize: 13, fontWeight: '700' },
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
  brandRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 30 },
  brand: { fontSize: 15, fontWeight: '700', color: '#20282B' },
  brandSub: { fontSize: 11, color: '#9A7F71', marginTop: 1 },
  railHeading: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 7 },
  railLabel: { fontSize: 10, textTransform: 'uppercase', letterSpacing: 1.4, color: '#8A9091' },
  newChat: { fontSize: 10, color: '#147D9F', fontWeight: '700' },
  recentList: { flex: 1 },
  railItemActive: { padding: 11, borderRadius: 13, backgroundColor: 'rgba(255,255,255,0.54)', marginBottom: 4 },
  railItem: { padding: 11, marginBottom: 4 },
  railItemText: { fontSize: 12, lineHeight: 16, color: '#20282B' },
  railMuted: { fontSize: 10, color: '#8A9091', marginTop: 3, textTransform: 'capitalize' },
  railBottom: { gap: 4, paddingTop: 12 },
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
  topTitle: { fontSize: 16, fontWeight: '600', color: '#20282B' },
  topSub: { fontSize: 10, color: '#9A7F71', marginTop: 2 },
  modeSwitch: { flexDirection: 'row', borderRadius: 13, padding: 3, backgroundColor: 'rgba(255,255,255,0.38)' },
  modeButton: { paddingHorizontal: 10, paddingVertical: 7, borderRadius: 10 },
  modeButtonActive: { backgroundColor: '#20282B' },
  modeText: { fontSize: 10, textTransform: 'uppercase', color: '#7F898B' },
  modeTextActive: { color: '#F4F3EE' },
  thread: { width: '100%', maxWidth: 780, alignSelf: 'center', paddingHorizontal: 18, paddingTop: 42, paddingBottom: 150 },
  emptyState: { maxWidth: 560, alignSelf: 'center', alignItems: 'center', paddingTop: 88, paddingHorizontal: 24 },
  emptyTitle: { color: '#20282B', fontSize: 22, fontWeight: '600', marginTop: 14 },
  emptyCopy: { color: '#738083', fontSize: 13, lineHeight: 21, textAlign: 'center', marginTop: 9 },
  userBlock: { alignItems: 'flex-end', marginBottom: 34 },
  meta: { fontSize: 10, color: '#8A9091', marginBottom: 7 },
  userBubble: { maxWidth: 560, borderRadius: 20, borderBottomRightRadius: 6, padding: 16, backgroundColor: 'rgba(255,255,255,0.55)' },
  userText: { fontSize: 15, lineHeight: 23, color: '#20282B' },
  assistantBlock: { width: '100%', marginBottom: 34 },
  assistantHead: { flexDirection: 'row', alignItems: 'center', gap: 9, marginBottom: 12 },
  assistantName: { fontSize: 12, fontWeight: '700', color: '#405055' },
  responseGlass: { borderRadius: 22, padding: 20, backgroundColor: 'rgba(250,250,247,0.58)', borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(255,255,255,0.80)' },
  assistantText: { color: '#20282B', fontSize: 18, lineHeight: 29, letterSpacing: -0.1 },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 14 },
  statusDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: 'rgba(20,125,159,0.26)' },
  statusDotActive: { backgroundColor: '#54D8FF' },
  statusText: { fontSize: 10, color: '#678B98' },
  thinkingRow: { flexDirection: 'row', alignItems: 'center', gap: 9, marginTop: -10, marginBottom: 30 },
  thinkingText: { color: '#688086', fontSize: 11 },
  phaseHint: { color: '#688086', fontSize: 11, marginBottom: 24 },
  amendmentNotice: {
    borderRadius: 16,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(20,125,159,0.22)',
    backgroundColor: 'rgba(222,197,182,0.24)',
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: 24,
  },
  amendmentTitle: { color: '#405055', fontSize: 11, fontWeight: '700', marginBottom: 4 },
  amendmentText: { color: '#6F7472', fontSize: 11, lineHeight: 17 },
  errorText: { color: '#9A5A52', fontSize: 11, lineHeight: 17, marginBottom: 24 },
  composerWrap: { position: 'absolute', left: 0, right: 0, bottom: 0, padding: 16 },
  composer: { maxWidth: 740, width: '100%', alignSelf: 'center', flexDirection: 'row', alignItems: 'flex-end', gap: 8, padding: 8, borderRadius: 22, backgroundColor: 'rgba(248,247,243,0.78)', borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(255,255,255,0.86)' },
  newMobile: { width: 42, height: 42, borderRadius: 21, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(255,255,255,0.52)' },
  newMobileText: { color: '#647174', fontSize: 19 },
  input: { flex: 1, minWidth: 0, minHeight: 42, maxHeight: 110, paddingHorizontal: 12, paddingVertical: 10, color: '#20282B', fontSize: 14 },
  send: { width: 42, height: 42, borderRadius: 21, alignItems: 'center', justifyContent: 'center', backgroundColor: '#147D9F' },
  sendText: { color: '#FFFFFF', fontSize: 19 },
});
