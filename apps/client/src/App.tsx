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
import { EditorialNavigationRail, type EditorialShellView } from './components/EditorialNavigationRail';
import { EditorialProjectWorkspace } from './components/EditorialProjectWorkspace';
import { EditorialUtilityRail } from './components/EditorialUtilityRail';
import { EditorialWorkspaceHeader } from './components/EditorialWorkspaceHeader';
import {
  MobileAmendmentNotice,
  MobileBottomNavigation,
  MobileBuildWorkspace,
  MobileContextCard,
  MobileHeader,
  MobileProjectWorkspace,
  MobileSpecificationDetail,
  type MobileDestination,
} from './components/mobile/MobileExperience';
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

type MobileDetail = 'specification' | 'live-build' | null;

export default function App() {
  const { width } = useWindowDimensions();
  const compact = width < 760;
  const showUtilityRail = width >= 1240;
  const navigationWidth = width >= 1680 ? 284 : width >= 1360 ? 260 : 228;
  const utilityWidth = width >= 1600 ? 320 : 296;
  const [mode, setMode] = React.useState<'reason' | 'code'>('reason');
  const [workspaceView, setWorkspaceView] = React.useState<EditorialShellView>('conversation');
  const [mobileDestination, setMobileDestination] = React.useState<MobileDestination>('chat');
  const [mobileDetail, setMobileDetail] = React.useState<MobileDetail>(null);
  const [mobileActionBusy, setMobileActionBusy] = React.useState(false);
  const [mobileActionError, setMobileActionError] = React.useState('');
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
  const activeProjectId = activeConversation?.project_id ?? engineering.run?.project_id ?? null;
  const activeProjectBinding = activeConversation?.project_binding_status ?? engineering.run?.project_binding_status ?? null;
  const observabilityAvailable = mode === 'code' && Boolean(engineering.run);
  const amendmentActive = state.phase === 'SPEC_AMENDMENT' || activeConversation?.status === 'SPEC_AMENDMENT';
  const mobileBuildActive = Boolean(engineering.run && !['COMPLETE', 'CANCELLED'].includes(engineering.run.state));

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
    if (workspaceView === 'observability' && !observabilityAvailable) setWorkspaceView('conversation');
  }, [observabilityAvailable, workspaceView]);

  React.useEffect(() => {
    if (!compact) setMobileDetail(null);
  }, [compact]);

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
    setMobileDestination('chat');
    setMobileDetail(null);
    setMobileActionError('');
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

  const selectWorkspace = React.useCallback((view: EditorialShellView) => {
    if (view === 'observability' && !observabilityAvailable) return;
    setWorkspaceView(view);
  }, [observabilityAvailable]);

  const resumeApprovedScope = React.useCallback(async () => {
    if (!conversationId || mobileActionBusy) return;
    setMobileActionBusy(true);
    setMobileActionError('');
    try {
      const conversation = await api.resumeApprovedScope(conversationId);
      if (state.phase !== 'IDLE') dispatch({ type: 'RESET' });
      applyConversation(conversation);
      await workSpecification.refresh();
      setApiOnline(true);
    } catch (error) {
      if (error instanceof AuthenticationRequiredError) {
        lockAccess('Your private session expired. Unlock Parallax to continue.');
      } else {
        setMobileActionError(error instanceof Error ? error.message : 'The approved build could not be resumed.');
      }
    } finally {
      setMobileActionBusy(false);
    }
  }, [applyConversation, conversationId, lockAccess, mobileActionBusy, state.phase, workSpecification]);

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

  if (compact) {
    if (mobileDetail === 'specification' && workSpecification.specification) {
      return (
        <View style={styles.root}>
          <LivingSurface energy={motion.surfaceEnergy} />
          <SafeAreaView style={styles.safe}>
            <MobileSpecificationDetail
              specification={workSpecification.specification}
              busy={workSpecification.busy || mobileActionBusy}
              error={workSpecification.error || mobileActionError || null}
              amendment={amendmentActive}
              onBack={() => setMobileDetail(null)}
              onApprove={() => void workSpecification.approve()}
              onRefresh={() => void workSpecification.draft()}
              onResumeApprovedScope={() => void resumeApprovedScope()}
            />
          </SafeAreaView>
        </View>
      );
    }

    if (mobileDetail === 'live-build' && engineering.run) {
      return (
        <View style={styles.root}>
          <LivingSurface energy={motion.surfaceEnergy} />
          <SafeAreaView style={styles.safe}>
            <LiveBuildWorkspace run={engineering.run} onBack={() => setMobileDetail(null)} />
          </SafeAreaView>
        </View>
      );
    }

    return (
      <View style={styles.root}>
        <LivingSurface energy={motion.surfaceEnergy} />
        <SafeAreaView style={styles.safe}>
          <View style={styles.mobileShell} testID="mobile-guided-shell">
            <MobileHeader
              mode={mode}
              projectId={activeProjectId}
              conversationTitle={activeConversation?.title}
              onModeChange={(nextMode) => void changeMode(nextMode)}
              onNewConversation={() => void startConversation(mode)}
            />

            <View style={styles.mobileContent}>
              {mobileDestination === 'chat' ? (
                <>
                  <ScrollView
                    ref={threadRef}
                    style={styles.threadScroll}
                    contentContainerStyle={[styles.thread, styles.threadCompact]}
                    keyboardShouldPersistTaps="handled"
                    onScroll={handleThreadScroll}
                    onContentSizeChange={handleThreadContentSizeChange}
                    scrollEventThrottle={32}
                    testID="mobile-chat-scroll"
                  >
                    {amendmentActive ? (
                      <MobileAmendmentNotice
                        busy={mobileActionBusy}
                        canResumeApprovedScope={Boolean(workSpecification.approvedSpecification)}
                        onStartNewObjective={() => void startConversation(mode)}
                        onResumeApprovedScope={() => void resumeApprovedScope()}
                      />
                    ) : (
                      <MobileContextCard
                        specification={workSpecification.specification}
                        run={mode === 'code' ? engineering.run : null}
                        canDraft={canDraftWorkSpecification && mode === 'code'}
                        busy={workSpecification.busy}
                        error={workSpecification.error}
                        onCapture={() => void workSpecification.draft()}
                        onReviewSpecification={() => workSpecification.specification && setMobileDetail('specification')}
                        onOpenBuild={() => setMobileDestination('build')}
                      />
                    )}
                    {mobileActionError ? <Text style={styles.mobileActionError}>{mobileActionError}</Text> : null}

                    {messages.length === 0 ? (
                      <View style={[styles.emptyState, styles.emptyStateCompact]}>
                        <View style={styles.emptyLogoWell}><ParallaxLogo size={58} /></View>
                        <Text style={[styles.emptyTitle, styles.emptyTitleCompact]}>Start with the outcome.</Text>
                        <Text style={styles.emptyCopy}>Describe what you want to accomplish. Parallax will keep the conversation and protected build flow aligned.</Text>
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
                          <View>
                            <Text style={styles.assistantName}>Parallax</Text>
                            <Text style={styles.meta}>{mode === 'reason' ? 'ASK' : 'BUILD'} · {message.id === activePrintId ? 'LIVE' : 'COMPLETE'}</Text>
                          </View>
                        </View>
                        <View accessibilityLabel="Parallax response" testID="assistant-response" style={[styles.responseCard, styles.responseCardCompact]}>
                          {message.id === activePrintId ? (
                            <LaserTypesetter text={message.content} active streamComplete={streamFinished} onComplete={() => finishPrint(message.id)} />
                          ) : (
                            <Text selectable accessibilityLiveRegion="polite" style={[styles.assistantText, styles.assistantTextCompact]}>{message.content}</Text>
                          )}
                          {message.id === activePrintId ? (
                            <View style={styles.statusRow}><View style={[styles.statusDot, motion.laserActive && styles.statusDotActive]} /><Text style={styles.statusText}>{streamFinished ? 'Settling response' : 'Live response'}</Text></View>
                          ) : null}
                        </View>
                      </View>
                    ) : null)}

                    {state.phase === 'THINKING' ? <View style={styles.thinkingRow}><ParallaxLogo size={28} /><Text style={styles.thinkingText}>Resolving the active objective…</Text></View> : null}
                    {state.phase === 'VERIFYING' ? <Text style={styles.phaseHint}>Verifying response…</Text> : null}
                    {state.phase === 'ERROR' ? <Text style={styles.errorText}>{state.error ?? 'Response failed. Your conversation is preserved.'}</Text> : null}
                  </ScrollView>

                  <View style={[styles.composerWrap, styles.composerWrapCompact]}>
                    <View style={[styles.composer, styles.composerCompact]}>
                      <TextInput
                        accessibilityLabel="Message Parallax"
                        value={draft}
                        onChangeText={setDraft}
                        placeholder={canDraftWorkSpecification ? 'Continue this objective…' : 'Describe the outcome you want…'}
                        placeholderTextColor={palette.muted}
                        style={styles.input}
                        onSubmitEditing={() => void respond()}
                        multiline
                      />
                      <TouchableOpacity accessibilityRole="button" accessibilityLabel="Send message" onPress={() => void respond()} style={styles.send}><Text style={styles.sendText}>↑</Text></TouchableOpacity>
                    </View>
                  </View>
                </>
              ) : null}

              {mobileDestination === 'build' ? (
                <MobileBuildWorkspace
                  specification={workSpecification.specification}
                  run={mode === 'code' ? engineering.run : null}
                  canDraft={canDraftWorkSpecification && mode === 'code'}
                  busy={workSpecification.busy}
                  error={workSpecification.error}
                  onCaptureSpecification={() => void workSpecification.draft()}
                  onReviewSpecification={() => workSpecification.specification && setMobileDetail('specification')}
                  onOpenDetails={() => engineering.run && setMobileDetail('live-build')}
                />
              ) : null}

              {mobileDestination === 'project' ? (
                <MobileProjectWorkspace
                  activeConversation={activeConversation}
                  conversations={conversations}
                  onOpenConversation={(conversation) => void openConversation(conversation)}
                  onStartAsk={() => void startConversation('reason')}
                  onStartBuild={() => void startConversation('code')}
                />
              ) : null}
            </View>

            <MobileBottomNavigation
              active={mobileDestination}
              buildActive={mobileBuildActive}
              onSelect={(destination) => {
                setMobileActionError('');
                setMobileDetail(null);
                setMobileDestination(destination);
              }}
            />
          </View>
        </SafeAreaView>
      </View>
    );
  }

  const headerEyebrow = workspaceView === 'projects'
    ? 'Project workspace'
    : mode === 'code'
      ? 'Engineering workspace'
      : 'Reasoning workspace';
  const headerTitle = workspaceView === 'projects' ? 'Projects' : 'What shall we build today?';
  const headerSubtitle = workspaceView === 'projects'
    ? 'Keep canonical Project identity visible without turning shell navigation into a provider console.'
    : activeConversation?.title ?? 'Start with the outcome you want to create.';

  return (
    <View style={styles.root}>
      <LivingSurface energy={motion.surfaceEnergy} />
      <SafeAreaView style={styles.safe}>
        <View style={styles.shell}>
          <EditorialNavigationRail
            width={navigationWidth}
            activeView={workspaceView}
            conversations={conversations}
            conversationId={conversationId}
            observabilityAvailable={observabilityAvailable}
            apiOnline={apiOnline}
            activeSpecId={activeConversation?.spec_id ?? null}
            projectId={activeProjectId}
            projectBindingStatus={activeProjectBinding}
            onSelectView={selectWorkspace}
            onNewConversation={() => void startConversation(mode)}
            onOpenConversation={(conversation) => void openConversation(conversation)}
          />

          <View style={styles.main} testID="editorial-main-workplane">
            {workspaceView !== 'observability' ? (
              <EditorialWorkspaceHeader
                compact={false}
                mode={mode}
                eyebrow={headerEyebrow}
                title={headerTitle}
                subtitle={headerSubtitle}
                projectId={activeProjectId}
                projectBindingStatus={activeProjectBinding}
                onModeChange={(nextMode) => void changeMode(nextMode)}
                onNewConversation={() => void startConversation(mode)}
              />
            ) : null}

            {workspaceView === 'conversation' ? (
              <>
                <View style={styles.governedContext}>
                  <WorkSpecificationStatus
                    specification={workSpecification.specification}
                    busy={workSpecification.busy}
                    error={workSpecification.error}
                    canDraft={canDraftWorkSpecification}
                    onDraft={() => void workSpecification.draft()}
                    onApprove={() => void workSpecification.approve()}
                  />

                  {mode === 'code' && engineering.run ? (
                    <EngineeringRunStatus
                      run={engineering.run}
                      busy={engineering.busy}
                      onPause={() => void engineering.pause()}
                      onResume={() => void engineering.resume()}
                      onCancel={() => void engineering.cancel()}
                    />
                  ) : null}
                </View>

                <ScrollView
                  ref={threadRef}
                  style={styles.threadScroll}
                  contentContainerStyle={styles.thread}
                  keyboardShouldPersistTaps="handled"
                  onScroll={handleThreadScroll}
                  onContentSizeChange={handleThreadContentSizeChange}
                  scrollEventThrottle={32}
                >
                  {messages.length === 0 ? (
                    <View style={styles.emptyState}>
                      <View style={styles.emptyLogoWell}><ParallaxLogo size={62} /></View>
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
                        <ParallaxLogo size={36} />
                        <View><Text style={styles.assistantName}>Parallax</Text><Text style={styles.meta}>{mode === 'reason' ? 'REASON' : 'CODE'} · {message.id === activePrintId ? 'LIVE' : 'COMPLETE'}</Text></View>
                      </View>
                      <View accessibilityLabel="Parallax response" testID="assistant-response" style={styles.responseCard}>
                        {message.id === activePrintId ? (
                          <LaserTypesetter text={message.content} active streamComplete={streamFinished} onComplete={() => finishPrint(message.id)} />
                        ) : (
                          <Text selectable accessibilityLiveRegion="polite" style={styles.assistantText}>{message.content}</Text>
                        )}
                        {message.id === activePrintId ? (
                          <View style={styles.statusRow}><View style={[styles.statusDot, motion.laserActive && styles.statusDotActive]} /><Text style={styles.statusText}>{streamFinished ? 'Settling response' : 'Live response'}</Text></View>
                        ) : null}
                      </View>
                    </View>
                  ) : null)}

                  {state.phase === 'THINKING' ? <View style={styles.thinkingRow}><ParallaxLogo size={28} /><Text style={styles.thinkingText}>Resolving the active objective…</Text></View> : null}
                  {state.phase === 'VERIFYING' ? <Text style={styles.phaseHint}>Verifying response…</Text> : null}
                  {state.phase === 'SPEC_AMENDMENT' ? (
                    <View style={styles.amendmentNotice} accessibilityLiveRegion="polite">
                      <Text style={styles.amendmentTitle}>Specification amendment required</Text>
                      <Text style={styles.amendmentText}>The conversation is preserved. Parallax has stopped substantive work against the prior approved objective. Continue only within that approved objective, or start a new objective for materially different work.</Text>
                      <TouchableOpacity
                        accessibilityRole="button"
                        accessibilityLabel="Start new objective"
                        onPress={() => void startConversation(mode)}
                        style={styles.amendmentAction}
                      >
                        <Text style={styles.amendmentActionText}>Start new objective</Text>
                      </TouchableOpacity>
                    </View>
                  ) : null}
                  {state.phase === 'ERROR' ? <Text style={styles.errorText}>{state.error ?? 'Response failed. Your conversation is preserved.'}</Text> : null}
                </ScrollView>

                <View style={styles.composerWrap}>
                  <View style={styles.composer}>
                    <TextInput
                      accessibilityLabel="Message Parallax"
                      value={draft}
                      onChangeText={setDraft}
                      placeholder={canDraftWorkSpecification ? 'Continue this objective…' : 'Describe the outcome you want…'}
                      placeholderTextColor={palette.muted}
                      style={styles.input}
                      onSubmitEditing={() => void respond()}
                      multiline
                    />
                    <TouchableOpacity accessibilityRole="button" accessibilityLabel="Send message" onPress={() => void respond()} style={styles.send}><Text style={styles.sendText}>↑</Text></TouchableOpacity>
                  </View>
                </View>
              </>
            ) : null}

            {workspaceView === 'observability' && mode === 'code' && engineering.run ? (
              <LiveBuildWorkspace run={engineering.run} onBack={() => setWorkspaceView('conversation')} />
            ) : null}

            {workspaceView === 'projects' ? (
              <ScrollView style={styles.projectScroll} contentContainerStyle={styles.projectScrollContent}>
                <EditorialProjectWorkspace conversation={activeConversation} onStartCodeWork={() => void startConversation('code')} />
              </ScrollView>
            ) : null}
          </View>

          {showUtilityRail && workspaceView === 'conversation' ? (
            <EditorialUtilityRail
              width={utilityWidth}
              apiOnline={apiOnline}
              phase={state.phase}
              mode={mode}
              run={engineering.run}
              specification={workSpecification.specification}
              projectId={activeProjectId}
              projectBindingStatus={activeProjectBinding}
            />
          ) : null}
        </View>
      </SafeAreaView>
    </View>
  );
}

const serif = Platform.OS === 'web' ? 'Georgia, ui-serif, Charter, serif' : undefined;

const styles = StyleSheet.create({
  accessRoot: { flex: 1, backgroundColor: palette.ivory50, alignItems: 'center', justifyContent: 'center', padding: 24 },
  accessPanel: { width: '100%', maxWidth: 390, alignItems: 'center', borderRadius: 24, padding: 30, backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, shadowColor: '#564B38', shadowOpacity: 0.08, shadowRadius: 26, shadowOffset: { width: 0, height: 12 } },
  accessTitle: { color: palette.charcoal950, fontSize: 30, fontWeight: '600', marginTop: 14, letterSpacing: -0.9, fontFamily: serif },
  accessCopy: { color: palette.charcoal600, fontSize: 12, marginTop: 5, marginBottom: 22 },
  accessInput: { width: '100%', minHeight: 48, borderRadius: 14, paddingHorizontal: 14, color: palette.charcoal950, backgroundColor: '#FFFFFF', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, fontSize: 16 },
  accessButton: { width: '100%', minHeight: 46, borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.rust600, marginTop: 8 },
  accessButtonText: { color: palette.ivory50, fontSize: 12, fontWeight: '700' },
  root: { flex: 1, backgroundColor: palette.ivory50 },
  safe: { flex: 1 },
  shell: { flex: 1, flexDirection: 'row' },
  mobileShell: { flex: 1, minHeight: 0, backgroundColor: 'rgba(251,247,238,0.94)' },
  mobileContent: { flex: 1, minHeight: 0 },
  main: { flex: 1, minWidth: 0, minHeight: 0, backgroundColor: 'rgba(251,247,238,0.82)' },
  governedContext: { flexShrink: 0, width: '100%', maxWidth: 980, alignSelf: 'center', paddingHorizontal: 22, paddingTop: 10 },
  threadScroll: { flex: 1, minHeight: 0 },
  thread: { width: '100%', maxWidth: 940, alignSelf: 'center', paddingHorizontal: 30, paddingTop: 28, paddingBottom: 34 },
  threadCompact: { paddingHorizontal: 14, paddingTop: 16, paddingBottom: 24 },
  emptyState: { maxWidth: 620, alignSelf: 'center', alignItems: 'center', paddingTop: 62, paddingHorizontal: 24 },
  emptyStateCompact: { paddingTop: 30, paddingHorizontal: 8 },
  emptyLogoWell: { width: 76, height: 76, borderRadius: 24, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, shadowColor: '#5B4C36', shadowOpacity: 0.06, shadowRadius: 16, shadowOffset: { width: 0, height: 7 } },
  emptyTitle: { color: palette.charcoal950, fontSize: 31, lineHeight: 36, fontWeight: '500', marginTop: 18, letterSpacing: -0.9, fontFamily: serif },
  emptyTitleCompact: { fontSize: 26, lineHeight: 31 },
  emptyCopy: { color: palette.charcoal600, fontSize: 13, lineHeight: 21, textAlign: 'center', marginTop: 10 },
  orientationRow: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', gap: 8, marginTop: 20 },
  orientationChip: { minHeight: 34, justifyContent: 'center', borderRadius: 999, paddingHorizontal: 14, backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  orientationText: { color: palette.olive700, fontSize: 10, fontWeight: '700' },
  userBlock: { alignItems: 'flex-end', marginBottom: 30 },
  meta: { fontSize: 8, lineHeight: 11, color: palette.charcoal450, marginBottom: 7, letterSpacing: 0.75, fontWeight: '700' },
  userBubble: { maxWidth: 590, borderRadius: 20, paddingHorizontal: 18, paddingVertical: 14, backgroundColor: palette.teal100, borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(0,132,135,0.16)' },
  userText: { fontSize: 15, lineHeight: 23, color: palette.charcoal950 },
  assistantBlock: { width: '100%', maxWidth: 800, alignSelf: 'flex-start', marginBottom: 36 },
  assistantHead: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 11, paddingLeft: 2 },
  assistantName: { fontSize: 15, lineHeight: 19, fontWeight: '700', color: palette.charcoal950, fontFamily: serif },
  responseCard: { borderRadius: 22, paddingTop: 20, paddingBottom: 21, paddingHorizontal: 22, backgroundColor: 'rgba(245,238,223,0.90)', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, shadowColor: '#5A4D38', shadowOpacity: 0.06, shadowRadius: 18, shadowOffset: { width: 0, height: 8 } },
  responseCardCompact: { borderRadius: 19, paddingTop: 16, paddingBottom: 17, paddingHorizontal: 16 },
  assistantText: { color: palette.charcoal950, fontSize: 17, lineHeight: 28, letterSpacing: -0.12 },
  assistantTextCompact: { fontSize: 16, lineHeight: 25 },
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
  amendmentAction: { alignSelf: 'flex-start', minHeight: 40, marginTop: 12, paddingHorizontal: 14, borderRadius: 13, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.rust700 },
  amendmentActionText: { color: palette.ivory50, fontSize: 10, fontWeight: '800', letterSpacing: 0.2 },
  errorText: { color: palette.danger, fontSize: 11, lineHeight: 17, marginBottom: 24 },
  mobileActionError: { color: palette.danger, fontSize: 10, lineHeight: 15, marginBottom: 18, paddingHorizontal: 2 },
  composerWrap: { flexShrink: 0, paddingHorizontal: 22, paddingBottom: 18, paddingTop: 8, backgroundColor: 'rgba(251,247,238,0.88)' },
  composerWrapCompact: { paddingHorizontal: 10, paddingBottom: 8, paddingTop: 6, backgroundColor: 'rgba(251,247,238,0.98)' },
  composer: { maxWidth: 880, width: '100%', alignSelf: 'center', flexDirection: 'row', alignItems: 'flex-end', gap: 8, padding: 8, borderRadius: 22, backgroundColor: '#FFFDF8', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, shadowColor: '#564B38', shadowOpacity: 0.09, shadowRadius: 20, shadowOffset: { width: 0, height: 9 } },
  composerCompact: { borderRadius: 19, padding: 6 },
  input: { flex: 1, minWidth: 0, minHeight: 44, maxHeight: 110, paddingHorizontal: 11, paddingVertical: 10, color: palette.charcoal950, fontSize: 16, letterSpacing: -0.05 },
  send: { width: 44, height: 44, borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.teal600, shadowColor: '#145D5E', shadowOpacity: 0.12, shadowRadius: 8, shadowOffset: { width: 0, height: 4 } },
  sendText: { color: palette.ivory50, fontSize: 19 },
  projectScroll: { flex: 1, minHeight: 0 },
  projectScrollContent: { flexGrow: 1 },
});