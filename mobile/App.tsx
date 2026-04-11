import { useState, useRef, useEffect } from 'react';
import { View, Text, Pressable, StyleSheet, ScrollView, SafeAreaView, TextInput, KeyboardAvoidingView, Platform } from 'react-native';
import { Audio } from 'expo-av';
import { transcribeAudio } from './services/voxtral';
import { coachApi } from './services/coachApi';

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

function MetricCard({ label, value, unit, icon, alert }: typeof METRICS[0]) {
  return (
    <View style={[styles.card, alert && styles.cardAlert]}>
      <Text style={styles.cardIcon}>{icon}</Text>
      <Text style={styles.cardValue}>{value}<Text style={styles.cardUnit}>{unit ? ` ${unit}` : ''}</Text></Text>
      <Text style={styles.cardLabel}>{label}</Text>
    </View>
  );
}

function Dashboard() {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#0f0f0f' }}>
      <ScrollView contentContainerStyle={styles.dashContent}>
        <Text style={styles.greeting}>Bonjour Malik 👋</Text>
        <View style={styles.insightBox}>
          <Text style={styles.insightText}>😴 Vous avez mal dormi cette nuit. Votre HRV est en baisse et votre niveau de stress est élevé.</Text>
        </View>
        <Text style={styles.sectionTitle}>Aujourd'hui</Text>
        <View style={styles.grid}>
          {METRICS.map((m) => <MetricCard key={m.label} {...m} />)}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

// ─── Chat ─────────────────────────────────────────────────────────────────────

type Message = { role: 'coach' | 'user'; text: string };

function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const sessionRef = useRef<string | null>(null);
  const scrollRef = useRef<ScrollView>(null);

  useEffect(() => {
    coachApi.startSession(PATIENT_ID).then((sid) => { sessionRef.current = sid; }).catch(() => {});
    loadBrief();
  }, []);

  async function loadBrief() {
    setLoading(true);
    let full = '';
    let added = false;
    try {
      for await (const event of coachApi.brief(PATIENT_ID)) {
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
    }
  }

  async function sendText(text: string) {
    if (!text.trim()) return;
    const sid = sessionRef.current;
    if (!sid) {
      setMessages((prev) => [...prev, { role: 'coach', text: 'Session en cours de démarrage, réessaie dans un instant.' }]);
      return;
    }
    setMessages((prev) => [...prev, { role: 'user', text }]);
    setInput('');
    setLoading(true);
    let full = '';
    let added = false;
    try {
      for await (const event of coachApi.reply(sid, text)) {
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
          {messages.map((m, i) => (
            <View key={i} style={[styles.bubble, m.role === 'user' ? styles.bubbleUser : styles.bubbleCoach]}>
              <Text style={[styles.bubbleText, m.role === 'user' && styles.bubbleTextUser]}>{m.text}</Text>
            </View>
          ))}
          {loading && (
            <View style={styles.bubbleCoach}>
              <Text style={styles.bubbleText}>...</Text>
            </View>
          )}
        </ScrollView>

        <View style={styles.chatBar}>
          <TextInput
            style={styles.chatInput}
            value={input}
            onChangeText={setInput}
            placeholder="Répondre..."
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

  if (!onboarded) return <Onboarding onDone={() => setOnboarded(true)} />;

  return (
    <View style={{ flex: 1, backgroundColor: '#0f0f0f' }}>
      {tab === 'dashboard' ? <Dashboard /> : <Chat />}
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
