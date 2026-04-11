import { useState, useRef, useEffect } from 'react';
import { View, Text, Pressable, StyleSheet, ScrollView, SafeAreaView, TextInput, KeyboardAvoidingView, Platform, ActivityIndicator } from 'react-native';
import { Audio } from 'expo-av';
import * as DocumentPicker from 'expo-document-picker';
import { transcribeAudio } from './services/voxtral';
import { coachApi } from './services/coachApi';
import { API_BASE_URL } from './constants/config';

const PATIENT_ID = 'patient-1';

// ─── Onboarding ───────────────────────────────────────────────────────────────

const STEPS = [
  { emoji: '👋', title: 'Bienvenue sur VITAL', desc: "Ton assistant santé vocal. On analyse ta voix et tes données biométriques pour détecter le burnout avant qu'il arrive." },
  { emoji: '🎙', title: 'Parle, on écoute', desc: '3 questions. 3 minutes. VITAL croise ta réponse vocale avec tes données de sommeil, rythme cardiaque et stress.' },
  { emoji: '📊', title: 'Tes données, ton bord', desc: 'Toutes tes métriques santé au même endroit. Tendances sur 7 jours, alertes biométriques, score de récupération.' },
  { emoji: '🔔', title: 'Des nudges, pas du bruit', desc: "VITAL t'envoie une notification uniquement quand tes signaux biométriques le justifient." },
];

function Onboarding({ onDone }: { onDone: () => void }) {
  const [step, setStep] = useState(0);
  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

  return (
    <View style={styles.screen}>
      <View style={styles.dots}>
        {STEPS.map((_, i) => (
          <View key={i} style={[styles.dot, i === step && styles.dotActive]} />
        ))}
      </View>
      <Text style={styles.emoji}>{current.emoji}</Text>
      <Text style={styles.h1}>{current.title}</Text>
      <Text style={styles.muted}>{current.desc}</Text>
      <View style={styles.row}>
        {step > 0 && (
          <Pressable style={styles.btnGhost} onPress={() => setStep(step - 1)}>
            <Text style={styles.btnGhostText}>Retour</Text>
          </Pressable>
        )}
        <Pressable style={[styles.btn, step === 0 && { flex: 1 }]} onPress={isLast ? onDone : () => setStep(step + 1)}>
          <Text style={styles.btnText}>{isLast ? "C'est parti →" : 'Suivant'}</Text>
        </Pressable>
      </View>
    </View>
  );
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

const METRICS = [
  { label: 'Sommeil', value: '5h12', unit: '', icon: '😴', alert: true },
  { label: 'HRV', value: '42', unit: 'ms', icon: '💓', alert: false },
  { label: 'Pas', value: '3 240', unit: '', icon: '👟', alert: false },
  { label: 'SpO2', value: '97', unit: '%', icon: '🫁', alert: false },
  { label: 'Stress', value: 'Élevé', unit: '', icon: '⚡', alert: true },
  { label: 'Mindful', value: '0', unit: 'min', icon: '🧘', alert: false },
];

function MetricCard({ label, value, unit, icon, alert, onPress }: typeof METRICS[0] & { onPress?: () => void }) {
  return (
    <Pressable
      style={({ pressed }) => [styles.card, alert && styles.cardAlert, pressed && { opacity: 0.7 }]}
      onPress={onPress}
    >
      <Text style={styles.cardIcon}>{icon}</Text>
      <Text style={styles.cardValue}>{value}<Text style={styles.cardUnit}>{unit ? ` ${unit}` : ''}</Text></Text>
      <Text style={styles.cardLabel}>{label}</Text>
      {onPress && <Text style={styles.cardHint}>Discuter →</Text>}
    </Pressable>
  );
}

type BloodTestStatus = 'idle' | 'uploading' | 'done';

function UploadScreen({ onSuccess, onCancel }: { onSuccess: () => void; onCancel: () => void }) {
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  async function pickAndUpload() {
    try {
      const result = await DocumentPicker.getDocumentAsync({ type: 'application/pdf', copyToCacheDirectory: true });
      if (result.canceled) return;
      const file = result.assets[0];
      setStatus('loading');

      const form = new FormData();
      form.append('file', { uri: file.uri, name: file.name, type: 'application/pdf' } as any);

      // TODO: replace with real endpoint when provided
      const res = await fetch(`${API_BASE_URL}/api/blood-test/upload`, {
        method: 'POST',
        body: form,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      onSuccess();
    } catch (e: any) {
      setErrorMsg(e.message ?? 'Erreur inconnue');
      setStatus('error');
    }
  }

  if (status === 'loading') {
    return (
      <SafeAreaView style={styles.uploadScreen}>
        <ActivityIndicator size="large" color="#6366f1" />
        <Text style={styles.uploadLoadingText}>Analyse en cours…</Text>
        <Text style={styles.uploadMuted}>Ton bilan est envoyé au backend</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.uploadScreen}>
      <Text style={styles.uploadEmoji}>🩸</Text>
      <Text style={styles.uploadTitle}>Bilan sanguin</Text>
      <Text style={styles.uploadMuted}>Importe ton PDF — VITAL l'analyse et le prend en compte dans tes données de santé.</Text>

      {status === 'error' && (
        <View style={styles.uploadError}>
          <Text style={styles.uploadErrorText}>Erreur : {errorMsg}</Text>
        </View>
      )}

      <Pressable style={styles.uploadBtn} onPress={pickAndUpload}>
        <Text style={styles.uploadBtnText}>📄 Choisir un PDF</Text>
      </Pressable>
      <Pressable style={styles.uploadCancelBtn} onPress={onCancel}>
        <Text style={styles.uploadCancelText}>Annuler</Text>
      </Pressable>
    </SafeAreaView>
  );
}

function Dashboard({ onMetricPress }: { onMetricPress: (label: string, value: string, unit: string) => void }) {
  const [bloodTestStatus, setBloodTestStatus] = useState<BloodTestStatus>('idle');
  const [showUpload, setShowUpload] = useState(false);

  if (showUpload) {
    return (
      <UploadScreen
        onSuccess={() => { setBloodTestStatus('done'); setShowUpload(false); }}
        onCancel={() => setShowUpload(false)}
      />
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#0f0f0f' }}>
      <ScrollView contentContainerStyle={styles.dashContent}>
        <Text style={styles.greeting}>Bonjour Malik 👋</Text>
        <View style={styles.insightBox}>
          <Text style={styles.insightText}>😴 Vous avez mal dormi cette nuit. Votre HRV est en baisse et votre niveau de stress est élevé.</Text>
        </View>
        <Text style={styles.sectionTitle}>Aujourd'hui · <Text style={{ color: '#555', fontWeight: '400' }}>Appuie sur un KPI pour en discuter</Text></Text>
        <View style={styles.grid}>
          {METRICS.map((m) => (
            <MetricCard key={m.label} {...m} onPress={() => onMetricPress(m.label, m.value, m.unit)} />
          ))}
        </View>

        {bloodTestStatus === 'idle' && (
          <Pressable style={styles.bloodTestBanner} onPress={() => setShowUpload(true)}>
            <View style={{ flex: 1 }}>
              <Text style={styles.bloodTestBannerTitle}>🩸 Déposez votre bilan sanguin</Text>
              <Text style={styles.bloodTestBannerSub}>Enrichissez votre suivi avec vos données biologiques</Text>
            </View>
            <Text style={styles.bloodTestBannerArrow}>→</Text>
          </Pressable>
        )}

        {bloodTestStatus === 'done' && (
          <View style={styles.bloodTestDone}>
            <Text style={styles.bloodTestDoneText}>✅ Bilan sanguin transmis</Text>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

// ─── Chat ─────────────────────────────────────────────────────────────────────

type Message = { role: 'coach' | 'user' | 'context'; text: string };

function Chat({ pendingContext, onContextConsumed }: { pendingContext: string | null; onContextConsumed: () => void }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const sessionRef = useRef<string | null>(null);
  const sendingRef = useRef(false);
  const scrollRef = useRef<ScrollView>(null);

  useEffect(() => {
    let cancelled = false;
    coachApi.startSession(PATIENT_ID)
      .then((sid) => { if (!cancelled) sessionRef.current = sid; })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  const [attachedContext, setAttachedContext] = useState<string | null>(null);

  useEffect(() => {
    if (!pendingContext) return;
    onContextConsumed();
    setAttachedContext(pendingContext);
    scrollRef.current?.scrollToEnd({ animated: true });
  }, [pendingContext]);

  async function sendText(text: string) {
    if (!text.trim() || sendingRef.current) return;
    const sid = sessionRef.current;
    if (!sid) {
      setMessages((prev) => [...prev, { role: 'coach', text: 'Session en cours de démarrage, réessaie dans un instant.' }]);
      return;
    }
    sendingRef.current = true;
    const context = attachedContext;
    setAttachedContext(null);
    const transcript = context ? `${context}\n\n${text}` : text;
    setMessages((prev) => [
      ...prev,
      ...(context ? [{ role: 'context' as const, text: context }] : []),
      { role: 'user', text },
    ]);
    setInput('');
    setLoading(true);
    let full = '';
    let added = false;
    try {
      for await (const event of coachApi.reply(sid, transcript)) {
        full += event.text;
        if (!added) {
          setMessages((prev) => [...prev, { role: 'coach', text: full }]);
          added = true;
        } else {
          setMessages((prev) => [...prev.slice(0, -1), { role: 'coach', text: full }]);
        }
        scrollRef.current?.scrollToEnd({ animated: true });
      }
    } catch (e: any) {
      setMessages((prev) => [...prev, { role: 'coach', text: `Erreur : ${e.message}` }]);
    } finally {
      setLoading(false);
      sendingRef.current = false;
    }
  }

  async function toggleVoice() {
    if (recording) {
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI()!;
      setRecording(null);
      setLoading(true);
      try {
        const text = await transcribeAudio(uri);
        await sendText(text);
      } catch (e: any) {
        setLoading(false);
      }
    } else {
      await Audio.requestPermissionsAsync();
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const { recording: rec } = await Audio.Recording.createAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
      setRecording(rec);
    }
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#0f0f0f' }}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView
          ref={scrollRef}
          style={styles.chatScroll}
          contentContainerStyle={styles.chatContent}
          onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
        >
          {messages.map((m, i) =>
            m.role === 'context' ? (
              <View key={i} style={styles.contextChip}>
                <View style={styles.contextChipInner}>
                  <Text style={styles.contextChipLabel}>📎 Contexte KPI</Text>
                  <Text style={styles.contextChipText}>{m.text}</Text>
                </View>
              </View>
            ) : (
              <View key={i} style={[styles.bubble, m.role === 'user' ? styles.bubbleUser : styles.bubbleCoach]}>
                <Text style={[styles.bubbleText, m.role === 'user' && styles.bubbleTextUser]}>{m.text}</Text>
              </View>
            )
          )}
          {loading && (
            <View style={styles.bubbleCoach}>
              <Text style={styles.bubbleText}>...</Text>
            </View>
          )}
        </ScrollView>

        {attachedContext && (
          <View style={styles.contextChip}>
            <View style={styles.contextChipInner}>
              <Text style={styles.contextChipLabel}>📎 Contexte KPI</Text>
              <Text style={styles.contextChipText} numberOfLines={2}>{attachedContext}</Text>
            </View>
            <Pressable onPress={() => setAttachedContext(null)} hitSlop={12}>
              <Text style={styles.contextChipClose}>✕</Text>
            </Pressable>
          </View>
        )}

        <View style={styles.chatBar}>
          <TextInput
            style={styles.chatInput}
            value={input}
            onChangeText={setInput}
            placeholder={attachedContext ? 'Ajoute ton message...' : 'Répondre...'}
            placeholderTextColor="#555"
            onSubmitEditing={() => sendText(input)}
            returnKeyType="send"
          />
          <Pressable style={[styles.chatSend, recording && styles.chatSendRed]} onPress={recording ? toggleVoice : input.trim() ? () => sendText(input) : toggleVoice}>
            <Text style={styles.chatSendIcon}>{recording ? '⏹' : input.trim() ? '↑' : '🎙'}</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// ─── Tab bar ──────────────────────────────────────────────────────────────────

type Tab = 'dashboard' | 'chat';

function TabBar({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  return (
    <View style={styles.tabBar}>
      <Pressable style={styles.tab} onPress={() => onChange('dashboard')}>
        <Text style={[styles.tabIcon, active === 'dashboard' && styles.tabActive]}>📊</Text>
        <Text style={[styles.tabLabel, active === 'dashboard' && styles.tabActive]}>Dashboard</Text>
      </Pressable>
      <Pressable style={styles.tab} onPress={() => onChange('chat')}>
        <Text style={[styles.tabIcon, active === 'chat' && styles.tabActive]}>🎙</Text>
        <Text style={[styles.tabLabel, active === 'chat' && styles.tabActive]}>Checkup</Text>
      </Pressable>
    </View>
  );
}

// ─── Root ─────────────────────────────────────────────────────────────────────

export default function App() {
  const [onboarded, setOnboarded] = useState(false);
  const [tab, setTab] = useState<Tab>('dashboard');
  const [pendingContext, setPendingContext] = useState<string | null>(null);

  if (!onboarded) return <Onboarding onDone={() => setOnboarded(true)} />;

  function handleMetricPress(label: string, value: string, unit: string) {
    const msg = `Mon score ${label} est à ${value}${unit ? ' ' + unit : ''}. Qu'est-ce que ça indique pour ma santé ?`;
    setPendingContext(msg);
    setTab('chat');
  }

  return (
    <View style={{ flex: 1, backgroundColor: '#0f0f0f' }}>
      <View style={{ flex: 1, display: tab === 'dashboard' ? 'flex' : 'none' }}>
        <Dashboard onMetricPress={handleMetricPress} />
      </View>
      <View style={{ flex: 1, display: tab === 'chat' ? 'flex' : 'none' }}>
        <Chat pendingContext={pendingContext} onContextConsumed={() => setPendingContext(null)} />
      </View>
      <TabBar active={tab} onChange={setTab} />
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#0f0f0f', alignItems: 'center', justifyContent: 'center', padding: 32, gap: 20 },

  // Onboarding
  dots: { flexDirection: 'row', gap: 8, marginBottom: 8 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#2a2a2a' },
  dotActive: { backgroundColor: '#6366f1', width: 24 },
  emoji: { fontSize: 64 },
  h1: { fontSize: 28, fontWeight: '800', color: '#fff', textAlign: 'center' },
  muted: { fontSize: 15, color: '#666', textAlign: 'center', lineHeight: 24 },
  row: { flexDirection: 'row', gap: 12, width: '100%', marginTop: 8 },
  btn: { flex: 1, backgroundColor: '#6366f1', borderRadius: 14, paddingVertical: 18, alignItems: 'center' },
  btnText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  btnGhost: { flex: 1, backgroundColor: '#1a1a1a', borderRadius: 14, paddingVertical: 18, alignItems: 'center' },
  btnGhostText: { color: '#555', fontWeight: '600', fontSize: 16 },

  // Dashboard
  dashContent: { padding: 24, gap: 16, paddingBottom: 40 },
  greeting: { fontSize: 26, fontWeight: '800', color: '#fff', marginTop: 12 },
  insightBox: { backgroundColor: '#1a1a2e', borderRadius: 16, padding: 18, borderLeftWidth: 3, borderLeftColor: '#6366f1' },
  insightText: { color: '#c7c7ff', fontSize: 15, lineHeight: 22 },
  sectionTitle: { fontSize: 13, fontWeight: '600', color: '#444', textTransform: 'uppercase', letterSpacing: 1 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  card: { backgroundColor: '#1a1a1a', borderRadius: 16, padding: 16, width: '47%', gap: 4 },
  cardAlert: { borderWidth: 1, borderColor: '#3f1f1f', backgroundColor: '#1f1212' },
  cardIcon: { fontSize: 22 },
  cardValue: { fontSize: 24, fontWeight: '800', color: '#fff' },
  cardUnit: { fontSize: 14, fontWeight: '400', color: '#555' },
  cardLabel: { fontSize: 12, color: '#555' },
  cardHint: { fontSize: 10, color: '#6366f1', marginTop: 4, fontWeight: '600' },

  bloodTestBanner: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1a1a2e', borderRadius: 16, padding: 16, borderWidth: 1, borderColor: '#2d2d5e', marginTop: 8 },
  bloodTestBannerTitle: { color: '#fff', fontWeight: '700', fontSize: 15, marginBottom: 2 },
  bloodTestBannerSub: { color: '#666', fontSize: 12 },
  bloodTestBannerArrow: { color: '#6366f1', fontSize: 20, fontWeight: '700' },
  bloodTestDone: { backgroundColor: '#0d2d1a', borderRadius: 16, padding: 16, borderWidth: 1, borderColor: '#1a5c35', alignItems: 'center', marginTop: 8 },
  bloodTestDoneText: { color: '#4ade80', fontWeight: '700', fontSize: 15 },

  uploadScreen: { flex: 1, backgroundColor: '#0f0f0f', alignItems: 'center', justifyContent: 'center', padding: 32, gap: 16 },
  uploadEmoji: { fontSize: 64 },
  uploadTitle: { fontSize: 26, fontWeight: '800', color: '#fff' },
  uploadMuted: { fontSize: 14, color: '#666', textAlign: 'center', lineHeight: 22 },
  uploadLoadingText: { fontSize: 18, fontWeight: '700', color: '#fff', marginTop: 16 },
  uploadBtn: { backgroundColor: '#6366f1', borderRadius: 14, paddingVertical: 16, paddingHorizontal: 32, width: '100%', alignItems: 'center', marginTop: 8 },
  uploadBtnText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  uploadCancelBtn: { paddingVertical: 12 },
  uploadCancelText: { color: '#555', fontSize: 14 },
  uploadError: { backgroundColor: '#2d1515', borderRadius: 10, padding: 12, width: '100%' },
  uploadErrorText: { color: '#f87171', fontSize: 13 },

  contextChip: { flexDirection: 'row', alignItems: 'center', marginHorizontal: 12, marginBottom: 6, backgroundColor: '#1a1a2e', borderRadius: 12, padding: 10, borderLeftWidth: 3, borderLeftColor: '#6366f1', gap: 8 },
  contextChipInner: { flex: 1 },
  contextChipLabel: { fontSize: 10, color: '#6366f1', fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 2 },
  contextChipText: { fontSize: 13, color: '#c7c7ff', lineHeight: 18 },
  contextChipClose: { fontSize: 14, color: '#555', padding: 4 },

  // Chat
  chatScroll: { flex: 1 },
  chatContent: { padding: 16, gap: 12, paddingBottom: 8 },
  bubble: { maxWidth: '80%', borderRadius: 16, padding: 14 },
  bubbleCoach: { backgroundColor: '#1a1a1a', alignSelf: 'flex-start', borderBottomLeftRadius: 4 },
  bubbleUser: { backgroundColor: '#6366f1', alignSelf: 'flex-end', borderBottomRightRadius: 4 },
  bubbleText: { color: '#e2e8f0', fontSize: 15, lineHeight: 22 },
  bubbleTextUser: { color: '#fff' },
  chatBar: { flexDirection: 'row', padding: 12, gap: 8, borderTopWidth: 1, borderTopColor: '#1e1e1e', backgroundColor: '#0f0f0f' },
  chatInput: { flex: 1, backgroundColor: '#1a1a1a', borderRadius: 22, paddingHorizontal: 16, paddingVertical: 10, color: '#fff', fontSize: 15 },
  chatSend: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#6366f1', alignItems: 'center', justifyContent: 'center' },
  chatSendRed: { backgroundColor: '#ef4444' },
  chatSendIcon: { color: '#fff', fontSize: 18 },

  // Tab bar
  tabBar: { flexDirection: 'row', backgroundColor: '#111', borderTopWidth: 1, borderTopColor: '#1e1e1e', paddingBottom: 28, paddingTop: 12 },
  tab: { flex: 1, alignItems: 'center', gap: 4 },
  tabIcon: { fontSize: 22, opacity: 0.3 },
  tabLabel: { fontSize: 11, color: '#444' },
  tabActive: { opacity: 1, color: '#6366f1' },
});
