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
import { EngineeringRunStatus } from './components/EngineeringRunStatus';
import { WorkSpecificationStatus } from './components/WorkSpecificationStatus';
import { EditorialUtilityRail } from './components/EditorialUtilityRail';
import { LiveBuildWorkspace } from './components/observability/LiveBuildWorkspace';
import { initialResponseState, motionForPhase, responseReducer } from './state/responseState';
import { api, AuthenticationRequiredError, type ConversationDto, type MessageDto, type ResponseStreamEvent } from './lib/api';
import { useEngineeringRun } from './hooks/useEngineeringRun';
import { useWorkSpecification } from './hooks/useWorkSpecification';
import { palette } from './theme';

const FALLBACK_MESSAGES: MessageDto[] = [
  {
    id: 'fallback-user',
    role: 'user',
    content: 'What can Parallax help me build?',
    status: 'complete',
    created_at: new Date(0).toISOString(),
  },
  {
    id: 'fallback-assistant',
    role: 'assistant',
    content: 'Parallax keeps the conversation, approved specification, engineering evidence, and protected execution path aligned while you build.',
    status: 'complete',
    created_at: new Date(0).toISOString(),
  },
];

const NAV_ITEMS = ['Conversations', 'Observability', 'Projects', 'Templates', 'Tools', 'Knowledge', 'Integrations', 'Settings'] as const;

export default function App() {
  const { width } = useWindowDimensions();
  const compact = width < 760;
  const showUtilityRail = width >= 1180;
  const [mode, setMode] = React.useState<'reason' | 'code'>('reason');
  const [workspaceView, setWorkspaceView] = React.useState<'conversation' | 'observability'>('conversation');
  const [draft, setDraft] = React.useState('');
  const [state, dispatch] = React.useReducer(responseReducer, initialResponseState);
  const [conversationId, setConversationId] = React.useState<string | null>(null);
  const [conversations, setConversations] = React.useState<ConversationDto[]>([]);
  const [messages, setMessages] = React.useState<MessageDto[]>(FALLBACK_MESSAGES);
  const [apiOnline, setApiOnline] = React.useState(false);
  const [activePrintId, setActivePrintId] = React.useState<string | null>(null);
  const [streamFinished, setStreamFinished] = React.useState(true);
  const [accessResolved, setAccessResolved] = React.useState(false);
  const [accessGranted, setAccessGranted] = React.useState(false);
  const [accessEnforced, setAccessEnforced] = React.useState(process.env.EXPO_PUBLIC_PARALLAX_REQUIRE_AUTH === 'true');
  const [accessDraft, setAccessDraft] = React.useState('');
  const [accessError, setAccessError] = React.useState('');
  const [accessBusy, setAccessBusy] = React.useState(false);
  const pendingRefreshRef = React.useRef<string | null>(null);
  const threadRef = React.useRef<ScrollView>(null);
  const liveEdgeRef = React.useRef(true);
  const motion = motionForPhase(state.phase);
  const activeConversation = conversations.find((item) => item.id === conversationId);
  const engineering = useEngineeringRun(conversationId, mode === 'code');
  const workSpecification = useWorkSpecification(conversationId);
  const canDraftWorkSpecification = messages.some((message) => message.role === 'user' && !message.id.startsWith('fallback-'));

  React.useEffect(() => {
    if (Platform.OS !== 'web') return;
    const saved = globalThis.localStorage?.getItem('parallax:p2:draft');
    if (saved) setDraft(saved);
  }, []);

  React.useEffect(() => {
    if (Platform.OS !== 'web') return;
    globalThis.localStorage?.setItem('parallax:p2:draft', draft);
  }, [draft]);

  const scrollToLiveEdge = React.useCallback((animated = true) => {
    requestAnimationFrame(() => threadRef.current?.scrollToEnd({ animated }));
  }, []);

  React.useEffect(() => {
    if (!activePrintId) return;
    liveEdgeRef.current = true;
    const timer = setTimeout(() => scrollToLiveEdge(true), 24);
    return () => clearTimeout(timer);
  }, [activePrintId, scrollToLiveEdge]);

  const handleThreadScroll = React.useCallback((event: any) => {
    const { contentOffset, contentSize, layoutMeasurement } = event.nativeEvent;
    liveEdgeRef.current = contentSize.height - (contentOffset.y + layoutMeasurement.height) < 120;
  }, []);

  const handleThreadContentSizeChange = React.useCallback(() => {
    if (activePrintId && liveEdgeRef.current) scrollToLiveEdge(false);
  }, [activePrintId, scrollToLiveEdge]);

  const updateConversationSummary = React.useCallback((conversation: ConversationDto) => {
    setConversations((current) => [conversation, ...current.filter((item) => item.id !== conversation.id)]);
  }, []);

  const applyConversation = React.useCallback((conversation: ConversationDto) => {
    setWorkspaceView('conversation');
    setConversationId(conversation.id);
    setMode(conversation.mode);
    setMessages(conversation.messages);
    setActivePrintId(null);
    setStreamFinished(true);
    pendingRefreshRef.current = null;
    liveEdgeRef.current = true;
    updateConversationSummary(conversation);
  }, [updateConversationSummary]);

  const loadWorkspace = React.useCallback(async () => {
    const existing = await api.listConversations();
    const current = existing[0] ?? (await api.createConversation('reason'));
    setApiOnline(true);
    setConversations(existing.length ? existing : [current]);
    applyConversation(current);
  }, [applyConversation]);

  const lockAccess = React.useCallback((message = '') => {
    api.setAccessToken('');
    setAccessGranted(false);
    setAccessEnforced(true);
    setApiOnline(false);
    setConversationId(null);
    setMessages(FALLBACK_MESSAGES);
    setAccessError(message);
  }, []);

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await api.getSession();
        if (cancelled) return;
        setAccessGranted(true);
        setAccessError('');
        await loadWorkspace();
      } catch (error) {
        if (cancelled) return;
        if (error instanceof AuthenticationRequiredError) lockAccess();
        else {
          setApiOnline(false);
          setConversationId(null);
          setMessages(FALLBACK_MESSAGES);
        }
      } finally {
        if (!cancelled) setAccessResolved(true);
      }
    })();
    return () => { cancelled = true; };
  }, [loadWorkspace, lockAccess]);

  const unlock = React.useCallback(async () => {
    const candidate = accessDraft.trim();
    if (!candidate) {
      setAccessError('Enter the private production access credential.');
      return;
    }
    setAccessBusy(true);
    setAccessError('');
    try {
      await api.establishSession(candidate);
      setAccessDraft('');
      setAccessGranted(true);
      setAccessEnforced(true);
      await loadWorkspace();
    } catch (error) {
      if (error instanceof AuthenticationRequiredError) lockAccess('That access credential was not accepted.');
      else {
        setApiOnline(false);
        setAccessError('Parallax could not establish a private session. Try again.');
      }
    } finally {
      setAccessBusy(false);
      setAccessResolved(true);
    }
  }, [accessDraft, loadWorkspace, lockAccess]);

  const openConversation = React.useCallback(async (conversation: ConversationDto) => {
    if (['THINKING', 'RESPONDING', 'VERIFYING'].includes(state.phase)) return;
    try {
      const fresh = await api.getConversation(conversation.id);
      if (state.phase !== 'IDLE') dispatch({ type: 'RESET' });
      applyConversation(fresh);
      setApiOnline(true);
    } catch (error) {
      if (error instanceof AuthenticationRequiredError) {
        lockAccess('Your private session expired. Unlock Parallax to continue.');
        return;
      }
      setApiOnline(false);
    }
  }, [applyConversation, lockAccess, state.phase]);

  const startConversation = React.useCallback(async (nextMode: 'reason' | 'code' = mode) => {
    if (['THINKING', 'RESPONDING', 'VERIFYING'].includes(state.phase)) return;
    try {
      const created = await api.createConversation(nextMode);
      if (state.phase !== 'IDLE') dispatch({ type: 'RESET' });
      applyConversation(created);
      setMode(nextMode);
      setApiOnline(true);
    } catch (error) {
      if (error instanceof AuthenticationRequiredError) {
        lockAccess('Your private session expired. Unlock Parallax to continue.');
        return;
      }
      setApiOnline(false);
    }
  }, [applyConversation, lockAccess, mode, state.phase]);

  const changeMode = React.useCallback(async (nextMode: 'reason' | 'code') => {
    if (nextMode !== mode) await startConversation(nextMode);
  }, [mode, startConversation]);

  const respond = React.useCallback(async () => {
    if (!['IDLE', 'COMPLETE', 'SPEC_AMENDMENT', 'ERROR'].includes(state.phase)) return;
    const content = draft.trim();
    if (!content) return;

    liveEdgeRef.current = true;
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
      setTimeout(() => scrollToLiveEdge(true), 20);

      const startAssistant = () => {
        if (assistantStarted) return;
        assistantStarted = true;
        setMessages((current) => {
          const completedUser = current.map((message) => message.id === optimisticUser.id ? { ...message, status: 'complete' as const } : message);
          if (completedUser.some((message) => message.id === assistantId)) return completedUser;
          return [...completedUser, {
            id: assistantId,
            role: 'assistant' as const,
            content: '',
            status: 'streaming' as const,
            created_at: new Date().toISOString(),
          }];
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
          if (event.data.phase === 'SPEC_AMENDMENT') requireAmendment();
          else if (event.data.phase === 'RESPONDING') startAssistant();
          return;
        }
        if (event.event === 'amendment') {
          requireAmendment();
          return;
        }
        if (event.event === 'chunk' && typeof event.data.text === 'string') {
          startAssistant();
          const delta = event.data.text;
          setMessages((current) => current.map((message) => message.id === assistantId ? { ...message, content: message.content + delta } : message));
        }
      };

      const result = await api.streamResponse(id, content, onEvent);
      if (result.phase === 'SPEC_AMENDMENT' || scopeAmendment) {
        requireAmendment();
        applyConversation(await api.getConversation(id));
        return;
      }
      if (!result.text.trim()) throw new Error('Parallax returned an empty response');

      startAssistant();
      setMessages((current) => current.map((message) => message.id === assistantId ? { ...message, content: result.text, status: 'streaming' } : message));
      setStreamFinished(true);
      void api.getConversation(id).then(updateConversationSummary).catch(() => undefined);
    } catch (error) {
      setStreamFinished(true);
      setActivePrintId(null);
      setApiOnline(false);
      setMessages((current) => current.map((message) => message.status === 'streaming' ? { ...message, status: 'error' } : message));
      if (error instanceof AuthenticationRequiredError) {
        if (state.phase !== 'IDLE') dispatch({ type: 'RESET' });
        lockAccess('Your private session expired. Unlock Parallax to continue.');
        return;
      }
      dispatch({ type: 'FAIL', error: error instanceof Error ? error.message : 'Response failed' });
    }
  }, [applyConversation, conversationId, draft, lockAccess, mode, scrollToLiveEdge, state.phase, updateConversationSummary]);

  const finishPrint = React.useCallback((messageId: string) => {
    if (state.phase !== 'RESPONDING' || activePrintId !== messageId || !streamFinished) return;
    setMessages((current) => current.map((message) => message.id === messageId ? { ...message, status: 'complete' } : message));
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
  }, [activePrintId, state.phase, streamFinished, updateConversationSummary]);

  if (!accessResolved) {
    return (
      <View style={styles.accessRoot}>
        <View style={styles.accessPanel}>
          <ParallaxLogo size={56} />
          <Text style={styles.accessTitle}>Parallax</Text>
          <Text style={styles.accessCopy}>Restoring private session…</Text>
        </View>
      </View>
    );
  }

  if (accessEnforced && !accessGranted) {
    return (
      <View style={styles.accessRoot}>
        <View style={styles.accessPanel}>
          <ParallaxLogo size={58} />
          <Text style={styles.accessTitle}>Parallax</Text>
          <Text style={styles.accessCopy}>Private production access</Text>
          <TextInput
            accessibilityLabel="Private access credential"
            secureTextEntry
            value={accessDraft}
            onChangeText={setAccessDraft}
            onSubmitEditing={() => void unlock()}
            placeholder="Access credential"
            placeholderTextColor={palette.muted}
            style={styles.accessInput}
          />
          {accessError ? <Text style={styles.errorText}>{accessError}</Text> : null}
          <TouchableOpacity accessibilityRole="button" accessibilityState={{ disabled: accessBusy }} disabled={accessBusy} onPress={() => void unlock()} style={styles.accessButton}>
            <Text style={styles.accessButtonText}>{accessBusy ? 'Verifying…' : 'Continue'}</Text>
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
            <View style={styles.rail} testID="editorial-navigation-rail">
              <View style={styles.brandRow}>
                <ParallaxLogo size={48} />
                <View style={styles.brandCopy}>
                  <Text style={styles.brand}>Parallax</Text>
                  <Text style={styles.brandSub}>Build with perspective.</Text>
                </View>
              </View>

              <View style={styles.navList}>
                {NAV_ITEMS.map((item) => {
                  const actionable = item === 'Conversations' || item === 'Observability';
                  const observabilityAvailable = mode === 'code' && Boolean(engineering.run);
                  const active = item === 'Conversations' ? workspaceView === 'conversation' : item === 'Observability' && workspaceView === 'observability';
                  return (
                    <TouchableOpacity
                      key={item}
                      accessibilityRole={actionable ? 'button' : undefined}
                      accessibilityState={{ disabled: !actionable || (item === 'Observability' && !observabilityAvailable), selected: active }}
                      disabled={!actionable || (item === 'Observability' && !observabilityAvailable)}
                      onPress={() => item === 'Observability' ? setWorkspaceView('observability') : item === 'Conversations' ? setWorkspaceView('conversation') : undefined}
                      style={[styles.navRow, active && styles.navRowActive, !actionable && styles.navRowDormant]}
                    >
                      <View style={[styles.navDot, active && styles.navDotActive]} />
                      <Text style={[styles.navText, active && styles.navTextActive, !actionable && styles.navTextDormant]}>{item}</Text>
                    </TouchableOpacity>
                  );
                })}
              </View>

              <View style={styles.railHeading}>
                <Text style={styles.railLabel}>Recent conversations</Text>
                <TouchableOpacity onPress={() => void startConversation(mode)} accessibilityRole="button" style={styles.newChatButton}>
                  <Text style={styles.newChat}>New +</Text>
                </TouchableOpacity>
              </View>
              <ScrollView style={styles.recentList} showsVerticalScrollIndicator={false}>
                {conversations.slice(0, 8).map((conversation) => (
                  <TouchableOpacity key={conversation.id} onPress={() => void openConversation(conversation)} style={conversation.id === conversationId ? styles.railItemActive : styles.railItem}>
                    <Text numberOfLines={2} style={styles.railItemText}>{conversation.title}</Text>
                    <Text style={styles.railMuted}>{conversation.mode}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
              <View style={styles.railBottom}>
                <View style={[styles.onlineDot, !apiOnline && styles.offlineDot]} />
                <View><Text style={styles.railStatus}>{apiOnline ? 'Workspace available' : 'Workspace unavailable'}</Text><Text style={styles.railMuted}>{activeConversation?.spec_id ?? 'No active specification'}</Text></View>
              </View>
            </View>
          )}

          <View style={styles.main}>
            <View style={[styles.topbar, workspaceView === 'observability' && styles.hidden]}>
              <View style={styles.topbarTitleRow}>
                {compact && <ParallaxLogo size={38} />}
                <View style={styles.headerCopy}>
                  <Text style={styles.eyebrow}>{mode === 'code' ? 'Engineering workspace' : 'Reasoning workspace'}</Text>
                  <Text style={styles.topTitle}>What shall we build today?</Text>
                  <Text style={styles.topSub}>{activeConversation?.title ?? 'Start with the outcome you want to create.'}</Text>
                </View>
              </View>
              <View style={styles.modeSwitch}>
                {(['reason', 'code'] as const).map((item) => (
                  <TouchableOpacity key={item} accessibilityRole="button" accessibilityState={{ selected: mode === item }} onPress={() => void changeMode(item)} style={[styles.modeButton, mode === item && styles.modeButtonActive]}>
                    <Text style={[styles.modeText, mode === item && styles.modeTextActive]}>{item}</Text>
                  </TouchableOpacity>
                ))}
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

            {workspaceView === 'conversation' && mode === 'code' && engineering.run && (
              <EngineeringRunStatus run={engineering.run} busy={engineering.busy} onPause={() => void engineering.pause()} onResume={() => void engineering.resume()} onCancel={() => void engineering.cancel()} />
            )}

            {compact && workspaceView === 'conversation' && mode === 'code' && engineering.run ? (
              <TouchableOpacity accessibilityRole="button" accessibilityLabel="Open Live Build observability" onPress={() => setWorkspaceView('observability')} style={styles.mobileLiveBuild}>
                <Text style={styles.mobileLiveBuildText}>Open Live Build · Observability</Text>
              </TouchableOpacity>
            ) : null}

            {workspaceView === 'observability' && mode === 'code' && engineering.run ? (
              <LiveBuildWorkspace run={engineering.run} onBack={() => setWorkspaceView('conversation')} />
            ) : null}

            <ScrollView
              ref={threadRef}
              style={[styles.threadScroll, workspaceView === 'observability' && styles.hidden]}
              contentContainerStyle={styles.thread}
              keyboardShouldPersistTaps="handled"
              onScroll={handleThreadScroll}
              onContentSizeChange={handleThreadContentSizeChange}
              scrollEventThrottle={32}
            >
              {messages.length === 0 ? (
                <View style={styles.emptyState}>
                  <ParallaxLogo size={56} />
                  <Text style={styles.emptyTitle}>Start with the outcome.</Text>
                  <Text style={styles.emptyCopy}>Describe what you want to accomplish. Parallax keeps the conversation, specification, evidence, and protected execution path aligned while the work evolves.</Text>
                  <View style={styles.orientationRow}>
                    {['Plan', 'Design', 'Build', 'Ship'].map((label) => <View key={label} style={styles.orientationChip}><Text style={styles.orientationText}>{label}</Text></View>)}
                  </View>
                </View>
              ) : messages.map((message) => message.role === 'user' ? (
                <View key={message.id} style={styles.userBlock}>
                  <Text style={styles.meta}>YOU</Text>
                  <View style={styles.userBubble}><Text selectable style={styles.userText}>{message.content}</Text></View>
                </View>
              ) : message.role === 'assistant' ? (
                <View key={message.id} style={styles.assistantBlock}>
                  <View style={styles.assistantHead}>
                    <ParallaxLogo size={34} />
                    <View><Text style={styles.assistantName}>Parallax</Text><Text style={styles.meta}>{mode === 'reason' ? 'REASON' : 'CODE'} · {message.id === activePrintId ? 'LIVE' : 'COMPLETE'}</Text></View>
                  </View>
                  <View accessibilityLabel="Parallax response" testID="assistant-response" style={styles.responseCard}>
                    {message.id === activePrintId ? (
                      <LaserTypesetter text={message.content} active streamComplete={streamFinished} onComplete={() => finishPrint(message.id)} />
                    ) : (
                      <Text selectable accessibilityLiveRegion="polite" style={styles.assistantText}>{message.content}</Text>
                    )}
                    {message.id === activePrintId && (
                      <View style={styles.statusRow}><View style={[styles.statusDot, motion.laserActive && styles.statusDotActive]} /><Text style={styles.statusText}>{streamFinished ? 'Settling response' : 'Live response'}</Text></View>
                    )}
                  </View>
                </View>
              ) : null)}

              {state.phase === 'THINKING' && <View style={styles.thinkingRow}><ParallaxLogo size={28} /><Text style={styles.thinkingText}>Resolving the active objective…</Text></View>}
              {state.phase === 'VERIFYING' && <Text style={styles.phaseHint}>Verifying response…</Text>}
              {state.phase === 'SPEC_AMENDMENT' && (
                <View style={styles.amendmentNotice} accessibilityLiveRegion="polite"><Text style={styles.amendmentTitle}>Specification amendment required</Text><Text style={styles.amendmentText}>The conversation is preserved. Parallax has stopped substantive work against the prior approved objective until the scope is clarified or amended.</Text></View>
              )}
              {state.phase === 'ERROR' && <Text style={styles.errorText}>{state.error ?? 'Response failed. Your conversation is preserved.'}</Text>}
            </ScrollView>

            <View style={[styles.composerWrap, workspaceView === 'observability' && styles.hidden]}>
              <View style={styles.composer}>
                {compact && <TouchableOpacity onPress={() => void startConversation(mode)} style={styles.newMobile} accessibilityLabel="New conversation"><Text style={styles.newMobileText}>＋</Text></TouchableOpacity>}
                <TextInput
                  accessibilityLabel="Message Parallax"
                  value={draft}
                  onChangeText={setDraft}
                  placeholder="Describe the next outcome…"
                  placeholderTextColor={palette.muted}
                  style={styles.input}
                  onSubmitEditing={() => void respond()}
                  multiline
                />
                <TouchableOpacity accessibilityRole="button" accessibilityLabel="Send message" onPress={() => void respond()} style={styles.send}><Text style={styles.sendText}>↑</Text></TouchableOpacity>
              </View>
            </View>
          </View>

          {showUtilityRail && workspaceView === 'conversation' && (
            <EditorialUtilityRail apiOnline={apiOnline} phase={state.phase} mode={mode} run={engineering.run} specification={workSpecification.specification} />
          )}
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  accessRoot: { flex: 1, backgroundColor: palette.ivory50, alignItems: 'center', justifyContent: 'center', padding: 24 },
  accessPanel: { width: '100%', maxWidth: 390, alignItems: 'center', borderRadius: 22, padding: 30, backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, shadowColor: '#564B38', shadowOpacity: 0.08, shadowRadius: 26, shadowOffset: { width: 0, height: 12 } },
  accessTitle: { color: palette.charcoal950, fontSize: 28, fontWeight: '600', marginTop: 14, letterSpacing: -0.8, fontFamily: Platform.OS === 'web' ? 'Georgia, ui-serif, serif' : undefined },
  accessCopy: { color: palette.charcoal600, fontSize: 12, marginTop: 5, marginBottom: 22 },
  accessInput: { width: '100%', minHeight: 48, borderRadius: 14, paddingHorizontal: 14, color: palette.charcoal950, backgroundColor: '#FFFFFF', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, fontSize: 16 },
  accessButton: { width: '100%', minHeight: 46, borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.rust600, marginTop: 8 },
  accessButtonText: { color: palette.ivory50, fontSize: 12, fontWeight: '700' },
  root: { flex: 1, backgroundColor: palette.ivory50 },
  safe: { flex: 1 },
  shell: { flex: 1, flexDirection: 'row' },
  rail: { width: 236, backgroundColor: 'rgba(28,42,24,0.98)', paddingHorizontal: 16, paddingTop: 20, paddingBottom: 16, overflow: 'hidden', shadowColor: '#172016', shadowOpacity: 0.12, shadowRadius: 16, shadowOffset: { width: 5, height: 0 } },
  brandRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 26, paddingHorizontal: 2 },
  brandCopy: { flex: 1, minWidth: 0 },
  brand: { fontSize: 22, lineHeight: 26, fontWeight: '600', color: palette.ivory50, letterSpacing: -0.5, fontFamily: Platform.OS === 'web' ? 'Georgia, ui-serif, serif' : undefined },
  brandSub: { fontSize: 9, color: palette.olive200, marginTop: 3, letterSpacing: 0.25 },
  navList: { gap: 4, marginBottom: 22 },
  navRow: { minHeight: 40, flexDirection: 'row', alignItems: 'center', gap: 10, borderRadius: 12, paddingHorizontal: 12 },
  navRowActive: { backgroundColor: palette.rust600 },
  navRowDormant: { opacity: 0.68 },
  navTextDormant: { color: '#AEB79A' },
  navDot: { width: 7, height: 7, borderRadius: 4, borderWidth: 1, borderColor: palette.olive500 },
  navDotActive: { backgroundColor: palette.ivory50, borderColor: palette.ivory50 },
  navText: { color: '#E2E5D4', fontSize: 12, fontWeight: '600' },
  navTextActive: { color: palette.ivory50 },
  railHeading: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 9, paddingHorizontal: 4 },
  railLabel: { fontSize: 8, textTransform: 'uppercase', letterSpacing: 1.1, color: '#AEB79A' },
  newChatButton: { minHeight: 30, paddingHorizontal: 9, borderRadius: 999, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(21,153,154,0.16)' },
  newChat: { fontSize: 8, color: '#BFE4DD', fontWeight: '800' },
  recentList: { flex: 1 },
  railItemActive: { paddingHorizontal: 12, paddingVertical: 10, borderRadius: 12, backgroundColor: 'rgba(196,74,27,0.28)', marginBottom: 4 },
  railItem: { paddingHorizontal: 12, paddingVertical: 9, marginBottom: 3, borderRadius: 11 },
  railItemText: { fontSize: 11, lineHeight: 15, color: '#F3EEE1' },
  railMuted: { fontSize: 8, color: '#AEB79A', marginTop: 4, textTransform: 'uppercase', letterSpacing: 0.5 },
  railBottom: { minHeight: 54, flexDirection: 'row', alignItems: 'center', gap: 9, paddingTop: 13, paddingHorizontal: 4, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: 'rgba(216,220,192,0.18)' },
  railStatus: { fontSize: 9, color: '#E2E5D4', fontWeight: '700' },
  onlineDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: palette.olive500 },
  offlineDot: { backgroundColor: '#A86714' },
  main: { flex: 1, minWidth: 0, minHeight: 0, backgroundColor: 'rgba(251,247,238,0.76)' },
  hidden: { display: 'none' },
  mobileLiveBuild: { minHeight: 44, marginHorizontal: 12, marginTop: 8, borderRadius: 13, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.teal100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.teal600 },
  mobileLiveBuildText: { color: palette.teal700, fontSize: 10, fontWeight: '800' },
  topbar: { minHeight: 112, paddingHorizontal: 28, paddingTop: 18, paddingBottom: 15, flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: 18, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  topbarTitleRow: { flex: 1, flexDirection: 'row', alignItems: 'flex-start', gap: 11 },
  headerCopy: { flex: 1, minWidth: 0 },
  eyebrow: { color: palette.olive700, fontSize: 9, fontWeight: '800', letterSpacing: 1.0, textTransform: 'uppercase', marginBottom: 4 },
  topTitle: { fontSize: 30, lineHeight: 35, fontWeight: '500', color: palette.charcoal950, letterSpacing: -1.0, fontFamily: Platform.OS === 'web' ? 'Georgia, ui-serif, serif' : undefined },
  topSub: { fontSize: 11, lineHeight: 16, color: palette.charcoal600, marginTop: 4, maxWidth: 620 },
  modeSwitch: { flexDirection: 'row', borderRadius: 14, padding: 3, backgroundColor: palette.cream200, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  modeButton: { minHeight: 38, paddingHorizontal: 13, paddingVertical: 7, borderRadius: 11, alignItems: 'center', justifyContent: 'center' },
  modeButtonActive: { backgroundColor: palette.rust600 },
  modeText: { fontSize: 9, textTransform: 'uppercase', color: palette.charcoal600, fontWeight: '700', letterSpacing: 0.6 },
  modeTextActive: { color: palette.ivory50 },
  threadScroll: { flex: 1, minHeight: 0 },
  thread: { width: '100%', maxWidth: 880, alignSelf: 'center', paddingHorizontal: 26, paddingTop: 30, paddingBottom: 30 },
  emptyState: { maxWidth: 600, alignSelf: 'center', alignItems: 'center', paddingTop: 76, paddingHorizontal: 24 },
  emptyTitle: { color: palette.charcoal950, fontSize: 28, fontWeight: '500', marginTop: 16, letterSpacing: -0.8, fontFamily: Platform.OS === 'web' ? 'Georgia, ui-serif, serif' : undefined },
  emptyCopy: { color: palette.charcoal600, fontSize: 13, lineHeight: 21, textAlign: 'center', marginTop: 10 },
  orientationRow: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', gap: 8, marginTop: 20 },
  orientationChip: { minHeight: 32, justifyContent: 'center', borderRadius: 999, paddingHorizontal: 13, backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  orientationText: { color: palette.olive700, fontSize: 10, fontWeight: '700' },
  userBlock: { alignItems: 'flex-end', marginBottom: 30 },
  meta: { fontSize: 8, color: palette.charcoal450, marginBottom: 7, letterSpacing: 0.75, fontWeight: '700' },
  userBubble: { maxWidth: 570, borderRadius: 20, paddingHorizontal: 18, paddingVertical: 14, backgroundColor: palette.teal100, borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(0,132,135,0.16)' },
  userText: { fontSize: 15, lineHeight: 23, color: palette.charcoal950 },
  assistantBlock: { width: '100%', maxWidth: 780, alignSelf: 'flex-start', marginBottom: 36 },
  assistantHead: { flexDirection: 'row', alignItems: 'center', gap: 9, marginBottom: 10, paddingLeft: 2 },
  assistantName: { fontSize: 14, fontWeight: '700', color: palette.charcoal950, fontFamily: Platform.OS === 'web' ? 'Georgia, ui-serif, serif' : undefined },
  responseCard: { borderRadius: 20, paddingTop: 19, paddingBottom: 20, paddingHorizontal: 20, backgroundColor: 'rgba(245,238,223,0.86)', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, shadowColor: '#5A4D38', shadowOpacity: 0.055, shadowRadius: 18, shadowOffset: { width: 0, height: 8 } },
  assistantText: { color: palette.charcoal950, fontSize: 17, lineHeight: 28, letterSpacing: -0.12 },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 14 },
  statusDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: palette.cream200 },
  statusDotActive: { backgroundColor: palette.teal600 },
  statusText: { fontSize: 9, color: palette.teal700, letterSpacing: 0.45, fontWeight: '700' },
  thinkingRow: { flexDirection: 'row', alignItems: 'center', gap: 9, marginTop: -4, marginBottom: 28 },
  thinkingText: { color: palette.charcoal600, fontSize: 11 },
  phaseHint: { color: palette.charcoal600, fontSize: 10, marginBottom: 24 },
  amendmentNotice: { borderRadius: 18, backgroundColor: palette.rust100, paddingHorizontal: 16, paddingVertical: 13, marginBottom: 24, borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(168,59,23,0.16)' },
  amendmentTitle: { color: palette.charcoal950, fontSize: 11, fontWeight: '800', marginBottom: 5 },
  amendmentText: { color: palette.charcoal600, fontSize: 11, lineHeight: 17 },
  errorText: { color: palette.danger, fontSize: 11, lineHeight: 17, marginBottom: 24 },
  composerWrap: { flexShrink: 0, paddingHorizontal: 18, paddingBottom: 16, paddingTop: 8, backgroundColor: 'rgba(251,247,238,0.84)' },
  composer: { maxWidth: 840, width: '100%', alignSelf: 'center', flexDirection: 'row', alignItems: 'flex-end', gap: 8, padding: 8, borderRadius: 22, backgroundColor: '#FFFDF8', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, shadowColor: '#564B38', shadowOpacity: 0.08, shadowRadius: 20, shadowOffset: { width: 0, height: 9 } },
  newMobile: { width: 44, height: 44, borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.cream200 },
  newMobileText: { color: palette.rust700, fontSize: 18 },
  input: { flex: 1, minWidth: 0, minHeight: 44, maxHeight: 110, paddingHorizontal: 11, paddingVertical: 10, color: palette.charcoal950, fontSize: 16, letterSpacing: -0.05 },
  send: { width: 44, height: 44, borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.teal600 },
  sendText: { color: palette.ivory50, fontSize: 19 },
});
