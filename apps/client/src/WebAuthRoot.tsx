import React from 'react';
import {
  ActivityIndicator,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from 'react-native';
import {
  api,
  AuthenticationRequiredError,
  AuthorizationDeniedError,
  type AccessUserDto,
} from './lib/api';
import {
  beginGoogleSignIn,
  clearOAuthCallbackUrl,
  clearTransientGoogleSession,
  exchangeGoogleCallback,
  isHostedHttpsWeb,
  isOAuthCallback,
} from './lib/googleAuth';
import { palette } from './theme';

type GateState = 'checking' | 'login' | 'callback' | 'denied' | 'error' | 'ready';

function StaticOpticalMark({ size = 54 }: { size?: number }) {
  return (
    <View style={[styles.markOuter, { width: size, height: size, borderRadius: size / 2 }]}>
      <View style={[styles.markInner, { width: size * 0.67, height: size * 0.67, borderRadius: size * 0.34 }]}>
        <View style={[styles.markAperture, { width: size * 0.19, height: size * 0.44, borderRadius: size * 0.1 }]} />
        <View style={[styles.markCore, { width: size * 0.1, height: size * 0.1, borderRadius: size * 0.05 }]} />
      </View>
    </View>
  );
}

function AccessGate({
  state,
  message,
  busy,
  onGoogle,
}: {
  state: GateState;
  message: string;
  busy: boolean;
  onGoogle(): void;
}) {
  const denied = state === 'denied';
  const error = state === 'error';
  const checking = state === 'checking' || state === 'callback';

  return (
    <SafeAreaView style={styles.gateRoot}>
      <View style={styles.ambientOne} />
      <View style={styles.ambientTwo} />
      <View style={styles.gatePanel}>
        <StaticOpticalMark />
        <Text style={styles.gateKicker}>PARALLAX · PRIVATE WORKSPACE</Text>
        <Text style={styles.gateTitle}>Parallax 2.0</Text>
        <Text style={styles.gateCopy}>
          {denied
            ? 'Your Google account is valid, but it is not currently authorized for this workspace.'
            : error
              ? message || 'Parallax could not complete Google sign-in.'
              : checking
                ? state === 'callback' ? 'Completing secure Google sign-in…' : 'Checking your private session…'
                : 'Use an authorized Google account to enter the workspace.'}
        </Text>

        {checking ? (
          <ActivityIndicator color={palette.cyan} size="small" style={styles.spinner} />
        ) : (
          <TouchableOpacity
            accessibilityRole="button"
            accessibilityLabel={denied ? 'Try another Google account' : 'Continue with Google'}
            disabled={busy}
            onPress={onGoogle}
            style={styles.googleButton}
          >
            <View style={styles.googleGlyph}><Text style={styles.googleGlyphText}>G</Text></View>
            <Text style={styles.googleButtonText}>{busy ? 'REDIRECTING…' : denied ? 'TRY ANOTHER GOOGLE ACCOUNT' : 'CONTINUE WITH GOOGLE'}</Text>
          </TouchableOpacity>
        )}

        {denied ? <Text style={styles.gateHint}>An owner can authorize your Google email from Parallax Access.</Text> : null}
        {error ? <Text style={styles.gateHint}>No Google password or production credential is stored by Parallax.</Text> : null}
      </View>
    </SafeAreaView>
  );
}

function AccessControl({ profile, onSignedOut }: { profile: AccessUserDto; onSignedOut(): void }) {
  const { width } = useWindowDimensions();
  const compact = width < 760;
  const panelWidth = Math.min(390, Math.max(280, width - 24));
  const [open, setOpen] = React.useState(false);
  const [users, setUsers] = React.useState<AccessUserDto[]>([]);
  const [email, setEmail] = React.useState('');
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState('');

  const refresh = React.useCallback(async () => {
    if (profile.role !== 'owner') return;
    try {
      setUsers(await api.listAccessUsers());
      setError('');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Access list unavailable');
    }
  }, [profile.role]);

  React.useEffect(() => {
    if (open && profile.role === 'owner') void refresh();
  }, [open, profile.role, refresh]);

  async function addMember() {
    const candidate = email.trim();
    if (!candidate) return;
    setBusy(true);
    try {
      await api.addAccessUser(candidate);
      setEmail('');
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to authorize that account');
    } finally {
      setBusy(false);
    }
  }

  async function updateStatus(user: AccessUserDto) {
    if (user.role === 'owner') return;
    setBusy(true);
    try {
      await api.updateAccessUserStatus(user.id, user.status === 'active' ? 'revoked' : 'active');
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to update access');
    } finally {
      setBusy(false);
    }
  }

  async function signOut() {
    setBusy(true);
    try {
      await api.endSession();
    } finally {
      onSignedOut();
    }
  }

  const label = profile.display_name || profile.email || (profile.auth_method === 'bearer' ? 'Break-glass' : 'Google user');
  const compactInitial = label.trim().slice(0, 1).toUpperCase() || 'P';

  return (
    <View pointerEvents="box-none" style={[styles.accountLayer, compact && styles.accountLayerCompact]}>
      <TouchableOpacity
        accessibilityRole="button"
        accessibilityLabel="Parallax access menu"
        onPress={() => setOpen((value) => !value)}
        style={[styles.accountPill, compact && styles.accountPillCompact]}
      >
        <View style={[styles.accountDot, profile.role === 'owner' ? styles.ownerDot : styles.memberDot, compact && styles.accountDotCompact]} />
        {compact ? (
          <Text style={styles.accountInitial}>{compactInitial}</Text>
        ) : (
          <>
            <Text numberOfLines={1} style={styles.accountLabel}>{label}</Text>
            <Text style={styles.accountRole}>{profile.role.toUpperCase()}</Text>
          </>
        )}
      </TouchableOpacity>

      {open ? (
        <View accessibilityLabel="Parallax access panel" style={[styles.accessPanel, { width: panelWidth }, compact && styles.accessPanelCompact]}>
          <View style={styles.accessPanelHeader}>
            <View>
              <Text style={styles.accessKicker}>PARALLAX ACCESS</Text>
              <Text style={styles.accessTitle}>{profile.role === 'owner' ? 'Authorized people' : 'Your access'}</Text>
            </View>
            <TouchableOpacity accessibilityLabel="Close access panel" onPress={() => setOpen(false)}><Text style={styles.close}>×</Text></TouchableOpacity>
          </View>

          <Text style={styles.profileLine}>{profile.email ?? 'Server break-glass session'}</Text>

          {profile.role === 'owner' ? (
            <>
              <View style={[styles.addRow, compact && styles.addRowCompact]}>
                <TextInput
                  accessibilityLabel="Google email to authorize"
                  autoCapitalize="none"
                  autoCorrect={false}
                  keyboardType="email-address"
                  placeholder="Google email"
                  placeholderTextColor={palette.muted}
                  value={email}
                  onChangeText={setEmail}
                  onSubmitEditing={() => void addMember()}
                  style={styles.emailInput}
                />
                <TouchableOpacity accessibilityRole="button" accessibilityLabel="Authorize Google email" disabled={busy} onPress={() => void addMember()} style={styles.addButton}>
                  <Text style={styles.addButtonText}>AUTHORIZE</Text>
                </TouchableOpacity>
              </View>

              <ScrollView style={styles.userList}>
                {users.map((user) => (
                  <View key={user.id} style={styles.userRow}>
                    <View style={styles.userCopy}>
                      <Text numberOfLines={1} style={styles.userName}>{user.display_name || user.email || 'Authorized user'}</Text>
                      <Text numberOfLines={1} style={styles.userMeta}>{user.email} · {user.role} · {user.bound ? 'Google linked' : 'awaiting first sign-in'}</Text>
                    </View>
                    {user.role === 'owner' ? (
                      <Text style={styles.ownerBadge}>OWNER</Text>
                    ) : (
                      <TouchableOpacity disabled={busy} onPress={() => void updateStatus(user)} style={user.status === 'active' ? styles.revokeButton : styles.reactivateButton}>
                        <Text style={user.status === 'active' ? styles.revokeText : styles.reactivateText}>{user.status === 'active' ? 'REVOKE' : 'REACTIVATE'}</Text>
                      </TouchableOpacity>
                    )}
                  </View>
                ))}
              </ScrollView>
            </>
          ) : (
            <Text style={styles.memberCopy}>Your Google account is authorized as a Parallax member. Access changes are managed by the workspace owner.</Text>
          )}

          {error ? <Text style={styles.accessError}>{error}</Text> : null}
          <TouchableOpacity accessibilityRole="button" accessibilityLabel="Sign out of Parallax" disabled={busy} onPress={() => void signOut()} style={styles.signOutButton}>
            <Text style={styles.signOutText}>SIGN OUT</Text>
          </TouchableOpacity>
        </View>
      ) : null}
    </View>
  );
}

export default function WebAuthRoot({ AppComponent }: { AppComponent: React.ComponentType }) {
  const hosted = isHostedHttpsWeb();
  const [state, setState] = React.useState<GateState>(hosted ? 'checking' : 'ready');
  const [profile, setProfile] = React.useState<AccessUserDto | null>(null);
  const [message, setMessage] = React.useState('');
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    if (!hosted) return;
    let cancelled = false;

    async function resolve() {
      const callback = isOAuthCallback();
      try {
        await api.getSession();
        const current = await api.currentAccessUser();
        if (cancelled) return;
        setProfile(current);
        if (callback) clearOAuthCallbackUrl();
        setState('ready');
        return;
      } catch (cause) {
        if (!(cause instanceof AuthenticationRequiredError)) throw cause;
      }

      if (!callback) {
        if (!cancelled) setState('login');
        return;
      }

      if (!cancelled) setState('callback');
      let googleToken = '';
      try {
        googleToken = await exchangeGoogleCallback();
        await api.establishGoogleSession(googleToken);
        await clearTransientGoogleSession();
        googleToken = '';
        const current = await api.currentAccessUser();
        if (cancelled) return;
        clearOAuthCallbackUrl();
        setProfile(current);
        setState('ready');
      } catch (cause) {
        await clearTransientGoogleSession();
        googleToken = '';
        clearOAuthCallbackUrl();
        if (cancelled) return;
        if (cause instanceof AuthorizationDeniedError) {
          setMessage(cause.message);
          setState('denied');
        } else {
          setMessage(cause instanceof Error ? cause.message : 'Google sign-in failed');
          setState('error');
        }
      }
    }

    void resolve().catch((cause) => {
      if (cancelled) return;
      setMessage(cause instanceof Error ? cause.message : 'Parallax access check failed');
      setState('error');
    });
    return () => { cancelled = true; };
  }, [hosted]);

  async function signIn() {
    setBusy(true);
    setMessage('');
    try {
      await beginGoogleSignIn();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : 'Google sign-in could not be started');
      setState('error');
      setBusy(false);
    }
  }

  function signedOut() {
    setProfile(null);
    setState('login');
    if (typeof globalThis.location !== 'undefined') globalThis.location.assign('/');
  }

  if (state !== 'ready') {
    return <AccessGate state={state} message={message} busy={busy} onGoogle={() => void signIn()} />;
  }

  return (
    <View style={styles.appRoot}>
      <AppComponent />
      {hosted && profile ? <AccessControl profile={profile} onSignedOut={signedOut} /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  appRoot: { flex: 1 },
  gateRoot: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.void, padding: 24, overflow: 'hidden' },
  ambientOne: { position: 'absolute', width: 560, height: 560, borderRadius: 280, backgroundColor: 'rgba(196,74,27,0.08)', left: -190, top: -210 },
  ambientTwo: { position: 'absolute', width: 480, height: 480, borderRadius: 240, backgroundColor: 'rgba(0,132,135,0.05)', right: -180, bottom: -210 },
  gatePanel: { width: '100%', maxWidth: 560, alignItems: 'center', paddingHorizontal: 48, paddingVertical: 50, borderRadius: 30, backgroundColor: 'rgba(245,238,223,0.96)', borderWidth: 1, borderColor: palette.borderStrong },
  markOuter: { alignItems: 'center', justifyContent: 'center', borderWidth: 1.4, borderColor: 'rgba(125,231,255,0.42)' },
  markInner: { alignItems: 'center', justifyContent: 'center', borderWidth: 1.4, borderColor: palette.indigo },
  markAperture: { position: 'absolute', borderWidth: 2.2, borderColor: palette.violet, transform: [{ rotate: '45deg' }] },
  markCore: { backgroundColor: palette.cyan },
  gateKicker: { color: palette.peach, fontSize: 9, fontWeight: '800', letterSpacing: 1.5, marginTop: 24 },
  gateTitle: { color: palette.text, fontSize: 38, lineHeight: 44, fontWeight: '600', letterSpacing: -1.3, marginTop: 8 },
  gateCopy: { color: palette.textSecondary, fontSize: 15, lineHeight: 23, textAlign: 'center', maxWidth: 420, marginTop: 12 },
  spinner: { marginTop: 30 },
  googleButton: { width: '100%', minHeight: 56, marginTop: 30, paddingHorizontal: 18, borderRadius: 17, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 12, backgroundColor: palette.cream, borderWidth: 1, borderColor: 'rgba(255,255,255,0.18)' },
  googleGlyph: { width: 26, height: 26, borderRadius: 13, alignItems: 'center', justifyContent: 'center', backgroundColor: '#FFFFFF' },
  googleGlyphText: { color: '#4285F4', fontSize: 15, fontWeight: '800' },
  googleButtonText: { color: '#171521', fontSize: 11, fontWeight: '800', letterSpacing: 0.8 },
  gateHint: { color: palette.muted, fontSize: 10, lineHeight: 16, textAlign: 'center', marginTop: 16 },
  accountLayer: { position: 'absolute', top: 70, right: 18, zIndex: 50, alignItems: 'flex-end' },
  accountLayerCompact: { top: 9, left: 16, right: undefined },
  accountPill: { maxWidth: 300, height: 34, flexDirection: 'row', alignItems: 'center', gap: 7, paddingHorizontal: 10, borderRadius: 17, backgroundColor: 'rgba(245,238,223,0.98)', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.borderStrong },
  accountPillCompact: { width: 44, height: 44, borderRadius: 22, paddingHorizontal: 0, justifyContent: 'center', gap: 0 },
  accountDot: { width: 7, height: 7, borderRadius: 4 },
  accountDotCompact: { position: 'absolute', top: 7, right: 7, width: 6, height: 6, borderRadius: 3 },
  ownerDot: { backgroundColor: palette.sage },
  memberDot: { backgroundColor: palette.indigo },
  accountInitial: { color: palette.textSoft, fontSize: 13, fontWeight: '700' },
  accountLabel: { maxWidth: 150, color: palette.textSoft, fontSize: 10 },
  accountRole: { color: palette.muted, fontSize: 7, fontWeight: '800', letterSpacing: 0.7 },
  accessPanel: { width: 390, maxHeight: 590, marginTop: 9, padding: 19, borderRadius: 22, backgroundColor: 'rgba(251,247,238,0.99)', borderWidth: 1, borderColor: palette.borderStrong },
  accessPanelCompact: { position: 'absolute', top: 53, right: -136, maxHeight: 560, marginTop: 0, padding: 16, borderRadius: 20 },
  accessPanelHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  accessKicker: { color: palette.peach, fontSize: 8, fontWeight: '800', letterSpacing: 1.2 },
  accessTitle: { color: palette.cream, fontSize: 22, fontWeight: '600', letterSpacing: -0.5, marginTop: 4 },
  close: { color: palette.textSecondary, fontSize: 24, lineHeight: 26 },
  profileLine: { color: palette.textSecondary, fontSize: 10, marginTop: 8, marginBottom: 16 },
  addRow: { flexDirection: 'row', gap: 8, marginBottom: 14 },
  addRowCompact: { flexWrap: 'wrap' },
  emailInput: { flex: 1, minWidth: 180, minHeight: 42, borderRadius: 13, paddingHorizontal: 12, color: palette.text, backgroundColor: palette.glassStrong, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  addButton: { minHeight: 42, paddingHorizontal: 11, alignItems: 'center', justifyContent: 'center', borderRadius: 13, backgroundColor: palette.violetDeep },
  addButtonText: { color: palette.text, fontSize: 8, fontWeight: '800', letterSpacing: 0.7 },
  userList: { maxHeight: 330 },
  userRow: { minHeight: 58, flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 9, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: palette.border },
  userCopy: { flex: 1, minWidth: 0 },
  userName: { color: palette.text, fontSize: 11, fontWeight: '600' },
  userMeta: { color: palette.muted, fontSize: 8, marginTop: 4 },
  ownerBadge: { color: palette.sage, fontSize: 8, fontWeight: '800', letterSpacing: 0.8 },
  revokeButton: { paddingHorizontal: 8, paddingVertical: 7, borderRadius: 10, backgroundColor: 'rgba(255,154,171,0.08)' },
  revokeText: { color: palette.danger, fontSize: 7, fontWeight: '800', letterSpacing: 0.6 },
  reactivateButton: { paddingHorizontal: 8, paddingVertical: 7, borderRadius: 10, backgroundColor: palette.sageWash },
  reactivateText: { color: palette.sage, fontSize: 7, fontWeight: '800', letterSpacing: 0.6 },
  memberCopy: { color: palette.textSecondary, fontSize: 11, lineHeight: 18, marginBottom: 14 },
  accessError: { color: palette.danger, fontSize: 9, lineHeight: 14, marginTop: 10 },
  signOutButton: { marginTop: 14, minHeight: 38, alignItems: 'center', justifyContent: 'center', borderRadius: 12, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.borderStrong },
  signOutText: { color: palette.textSecondary, fontSize: 8, fontWeight: '800', letterSpacing: 0.8 },
});
