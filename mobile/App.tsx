import React, { useState, useRef, useEffect } from 'react';
import { View, Text, Image, Pressable, StyleSheet, ScrollView, SafeAreaView, TextInput, KeyboardAvoidingView, Platform, ActivityIndicator } from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import Svg, { Circle } from 'react-native-svg';
import { Audio } from 'expo-av';
import * as DocumentPicker from 'expo-document-picker';
import { transcribeAudio } from './services/voxtral';
import { coachApi } from './services/coachApi';
import { API_BASE_URL } from './constants/config';
import { fontSans } from './constants/fonts';

const META_ICON_SIZE = 15;
const PATIENT_ID = 'patient-1';

// ─── Splash (OnboardingIntro) ─────────────────────────────────────────────────

function OnboardingIntro({ onDone, onSkip }: { onDone: () => void; onSkip: () => void }) {
  return (
    <SafeAreaView style={styles.splashScreen}>
      <View style={styles.splashSkipRow}>
        <Pressable onPress={onSkip} hitSlop={12} accessibilityRole="button" accessibilityLabel="Passer l'onboarding">
          <Text style={styles.skipLinkText}>Passer</Text>
        </Pressable>
      </View>

      <View style={styles.splashTop}>
        <Image
          source={Platform.OS === 'web' ? { uri: '/Vital_logo.svg' } : require('./assets/vital_logo.png')}
          style={styles.onboardingLogo}
          resizeMode="contain"
          accessibilityLabel="VITAL"
        />
        <Text style={styles.splashSub}>
          Voix · Biométrie · Burnout — détecté avant qu'il arrive.
        </Text>
      </View>

      <View style={styles.splashBottom}>
        <Pressable style={({ pressed }) => [styles.btn, pressed && { opacity: 0.85 }]} onPress={onDone}>
          <Text style={styles.btnText}>Commencer</Text>
        </Pressable>
        <Text style={styles.splashLegal}>Tes données restent sur ton appareil.</Text>
      </View>
    </SafeAreaView>
  );
}

// ─── Voice Intake ──────────────────────────────────────────────────────────────

type IntakeField = { key: string; label: string; icon: string; value: string | null };

const FIELD_META: Record<string, { label: string; icon: string }> = {
  age:        { label: 'Âge',    icon: '🎂' },
  sex:        { label: 'Sexe',   icon: '⚥'  },
  weight_kg:  { label: 'Poids',  icon: '⚖️' },
  height_cm:  { label: 'Taille', icon: '📏' },
  job:        { label: 'Métier', icon: '💼' },
};

function formatValue(key: string, value: string | number | null): string {
  if (value === null || value === undefined) return '—';
  if (key === 'weight_kg') return `${value} kg`;
  if (key === 'height_cm') return `${value} cm`;
  if (key === 'age') return `${value} ans`;
  if (key === 'sex') {
    const map: Record<string, string> = { male: 'Homme', female: 'Femme', other: 'Autre' };
    return map[String(value)] ?? String(value);
  }
  return String(value);
}

function normalizeForm(data: any): IntakeField[] {
  const formSource = data?.form ?? data ?? {};
  const flat: Record<string, any> = {};
  if (Array.isArray(formSource?.categories)) {
    for (const cat of formSource.categories) {
      for (const f of cat.fields ?? []) {
        flat[f.key] = f.value;
      }
    }
  }
  return Object.keys(FIELD_META).map((key) => ({
    key,
    ...FIELD_META[key],
    value: flat[key] != null ? formatValue(key, flat[key]) : null,
  }));
}

function VoiceIntake({ onDone, onSkip }: { onDone: (firstName: string) => void; onSkip: () => void }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [fields, setFields] = useState<IntakeField[]>(
    Object.keys(FIELD_META).map((key) => ({ key, ...FIELD_META[key], value: null }))
  );
  const [phase, setPhase] = useState<'init' | 'ready' | 'recording' | 'processing' | 'error'>('init');
  const [transcript, setTranscript] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const recordingRef = useRef<Audio.Recording | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/intake/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ patient_id: PATIENT_ID }),
        });
        const data = await res.json();
        setSessionId(data.session_id);
        if (data.form) setFields(normalizeForm(data));
        setPhase('ready');
      } catch (e: any) {
        setErrorMsg(e.message);
        setPhase('error');
      }
    })();
  }, []);

  async function onPressIn() {
    if (phase !== 'ready') return;
    try {
      await Audio.requestPermissionsAsync();
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const { recording } = await Audio.Recording.createAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
      recordingRef.current = recording;
      setPhase('recording');
    } catch (e: any) { setErrorMsg(e.message); setPhase('error'); }
  }

  async function onPressOut() {
    if (phase !== 'recording' || !recordingRef.current || !sessionId) return;
    setPhase('processing');
    try {
      const rec = recordingRef.current;
      recordingRef.current = null;
      await rec.stopAndUnloadAsync();
      const uri = rec.getURI()!;

      const form = new FormData();
      form.append('audio', { uri, name: 'intake.m4a', type: 'audio/m4a' } as any);

      const res = await fetch(`${API_BASE_URL}/api/intake/audio?session_id=${sessionId}`, {
        method: 'POST',
        body: form,
      });
      const data = await res.json();
      if (data.transcript) setTranscript(data.transcript);
      if (data.form) setFields(normalizeForm(data));
      setPhase('ready');
    } catch (e: any) { setErrorMsg(e.message); setPhase('error'); }
  }

  async function finalize() {
    if (!sessionId) return;
    setPhase('processing');
    try {
      await fetch(`${API_BASE_URL}/api/intake/finalize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      onDone('');
    } catch (e: any) { setErrorMsg(e.message); setPhase('error'); }
  }

  const filledCount = fields.filter((f) => f.value !== null).length;
  const canConfirm = fields.some((f) => f.value !== null);
  const isRecording = phase === 'recording';
  const isProcessing = phase === 'processing' || phase === 'init';

  return (
    <SafeAreaView style={styles.intakeScreen}>
      <View style={styles.intakeSkipRow}>
        <Pressable onPress={onSkip} hitSlop={12} accessibilityRole="button" accessibilityLabel="Passer l'enregistrement vocal">
          <Text style={styles.skipLinkText}>Passer</Text>
        </Pressable>
      </View>

      <ScrollView
        style={styles.intakeScroll}
        contentContainerStyle={styles.intakeScrollContent}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
      <Text style={styles.intakeTitle}>Parle-nous de toi</Text>
      <Text style={styles.intakeSub}>
        {phase === 'init' ? 'Connexion…' :
         isRecording ? '🎙 Parle, je t\'écoute…' :
         phase === 'processing' ? 'Analyse en cours…' :
         filledCount === 0 ? 'Maintiens le bouton et présente-toi' :
         `${filledCount}/${fields.length} informations recueillies`}
      </Text>

      <View style={styles.intakeGrid}>
        {fields.map((f) => (
          <View key={f.key} style={[styles.intakeField, f.value !== null && styles.intakeFieldFilled]}>
            <Text style={styles.intakeFieldIcon}>{f.icon}</Text>
            <Text style={styles.intakeFieldLabel}>{f.label}</Text>
            <Text style={[styles.intakeFieldValue, f.value === null && styles.intakeFieldEmpty]}>
              {f.value ?? '—'}
            </Text>
          </View>
        ))}
      </View>

      {transcript !== '' && (
        <Text style={styles.intakeTranscript}>« {transcript} »</Text>
      )}

      {!isProcessing && (
        <Pressable
          style={[styles.intakeMic, isRecording && styles.intakeMicActive]}
          onPressIn={onPressIn}
          onPressOut={onPressOut}
        >
          {isRecording
            ? <ActivityIndicator color="#fff" size="small" />
            : <Ionicons name="mic" size={36} color="#fff" />}
          <Text style={styles.intakeMicLabel}>
            {isRecording ? 'Relâche pour analyser' : 'Maintenir pour parler'}
          </Text>
        </Pressable>
      )}

      {isProcessing && <ActivityIndicator color="#111827" size="large" />}

      {phase === 'error' && (
        <Text style={styles.intakeError}>{errorMsg}</Text>
      )}

      {canConfirm && !isProcessing && (
        <Pressable style={styles.btn} onPress={finalize}>
          <Text style={styles.btnText}>Confirmer →</Text>
        </Pressable>
      )}
      </ScrollView>
    </SafeAreaView>
  );
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

const DASHBOARD_FIRST_NAME = 'Kylian';
const DASHBOARD_UV_INDEX = 4;

function formatDashboardHeaderDate(d: Date = new Date()): string {
  const day = d.getDate();
  const wd = d.toLocaleDateString('fr-FR', { weekday: 'short' })
    .replace(/\.$/, '')
    .trim();
  return `${day} ${wd}`;
}

function formatSheetSectionDate(d: Date = new Date()): string {
  return d.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
}

const METRICS = [
  { label: 'Sommeil', value: '5h12', unit: '', icon: '😴', alert: true,  raw: 5.2  },
  { label: 'HRV',     value: '42',   unit: 'ms', icon: '💓', alert: false, raw: 42   },
  { label: 'Pas',     value: '3 240',unit: '', icon: '👟', alert: false, raw: 3240 },
  { label: 'SpO2',    value: '97',   unit: '%', icon: '🫁', alert: false, raw: 97   },
  { label: 'Stress',  value: 'Élevé',unit: '', icon: '⚡', alert: true,  raw: 3    },
  { label: 'Mindful', value: '0',    unit: 'min', icon: '🧘', alert: false, raw: 0   },
];

type Segment = { text: string; hi?: boolean; icon?: React.ComponentProps<typeof Ionicons>['name'] };

function buildInsightSegments(metrics: typeof METRICS): Segment[] {
  const sleep   = metrics.find(m => m.label === 'Sommeil')!;
  const hrv     = metrics.find(m => m.label === 'HRV')!;
  const stress  = metrics.find(m => m.label === 'Stress')!;
  const mindful = metrics.find(m => m.label === 'Mindful')!;

  const segs: Segment[] = [];
  const hi  = (text: string, icon?: Segment['icon']): Segment => ({ text, hi: true, icon });
  const dim = (text: string): Segment => ({ text });

  segs.push(dim('Tu as dormi '));
  segs.push(hi(sleep.value, 'moon'));
  segs.push(dim(' cette nuit, soit bien en dessous des 7 h recommandées.'));

  if (hrv.raw < 50) {
    segs.push(dim(' Ton '));
    segs.push(hi('HRV'));
    segs.push(dim(' est basse à '));
    segs.push(hi(`${hrv.raw} ms`, 'heart'));
    segs.push(dim(', signe que ton corps récupère mal.'));
  }

  if (mindful.raw === 0) {
    segs.push(dim(' Tu n\'as pris aucun moment de '));
    segs.push(hi('pleine conscience'));
    segs.push(dim(' aujourd\'hui.'));
  }

  if (stress.raw >= 3) {
    segs.push(dim(' Ton niveau de '));
    segs.push(hi('stress'));
    segs.push(dim(' est-il '));
    segs.push(hi('élevé'));
    segs.push(dim(' ?'));
  }

  return segs;
}

type RingCardProps = {
  label: string;
  value: string;
  unit: string;
  progress: number;
  color: string;
  trackColor?: string;
  onPress?: () => void;
};

function RingCard({ label, value, unit, progress, color, trackColor = '#f0f0f5', onPress }: RingCardProps) {
  const size = 80;
  const stroke = 8;
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const dash = Math.min(Math.max(progress, 0), 1) * circ;

  return (
    <Pressable style={[styles.card, styles.ringCard]} onPress={onPress}>
      <View style={styles.ringWrap}>
        <Svg width={size} height={size}>
          <Circle cx={size / 2} cy={size / 2} r={r} stroke={trackColor} strokeWidth={stroke} fill="none" />
          <Circle
            cx={size / 2} cy={size / 2} r={r}
            stroke={color} strokeWidth={stroke} fill="none"
            strokeDasharray={`${circ}`}
            strokeDashoffset={circ - dash}
            strokeLinecap="round"
            rotation="-90"
            origin={`${size / 2}, ${size / 2}`}
          />
        </Svg>
        <View style={styles.ringCenter}>
          <Text style={[styles.ringValue, { color }]}>{value}</Text>
          {unit ? <Text style={styles.ringUnit}>{unit}</Text> : null}
        </View>
      </View>
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
      form.append('pdf', { uri: file.uri, name: file.name, type: 'application/pdf' } as any);

      const res = await fetch(`${API_BASE_URL}/api/blood-panel/upload`, { method: 'POST', body: form });
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
        <ActivityIndicator size="large" color="#111827" />
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

function Dashboard({ onMetricPress, userName }: { onMetricPress: (label: string, value: string, unit: string) => void; userName?: string }) {
  const [bloodTestStatus, setBloodTestStatus] = useState<BloodTestStatus>('idle');
  const [showUpload, setShowUpload] = useState(false);
  const segments = buildInsightSegments(METRICS);

  if (showUpload) {
    return (
      <UploadScreen
        onSuccess={() => { setBloodTestStatus('done'); setShowUpload(false); }}
        onCancel={() => setShowUpload(false)}
      />
    );
  }

  return (
    <SafeAreaView style={styles.dashSafe}>
      <View style={styles.dashHeader}>
        <View style={styles.insightCard}>
          <View style={styles.dashHeaderTopRow}>
            <Text style={styles.dashGreetingInCard}>Bonne Matinée, {DASHBOARD_FIRST_NAME}</Text>
            <View style={styles.dashHeaderMeta}>
              <View style={styles.dashMetaLine}>
                <Text style={styles.dashHeaderDate}>{formatDashboardHeaderDate()}</Text>
                <Ionicons name="calendar" size={META_ICON_SIZE} color="rgba(255, 255, 255, 0.95)" />
              </View>
              <View style={styles.dashMetaLine}>
                <Text style={styles.dashHeaderUv}>UV {DASHBOARD_UV_INDEX}</Text>
                <Ionicons name="sunny" size={META_ICON_SIZE + 1} color="rgba(255, 255, 255, 0.85)" />
              </View>
            </View>
          </View>
          <Text style={styles.dashInCard}>
            {segments.map((s, i) => (
              <React.Fragment key={i}>
                <Text style={s.hi ? styles.dashHiInCard : styles.dashDimInCard}>{s.text}</Text>
                {s.icon && <Ionicons name={s.icon} size={13} color="#fff" style={{ marginLeft: 2 }} />}
              </React.Fragment>
            ))}
          </Text>
        </View>
      </View>

      <View style={styles.dashSheet}>
        <View style={styles.sheetHandleWrap}>
          <View style={styles.sheetHandle} />
        </View>
        <ScrollView contentContainerStyle={styles.dashContent} showsVerticalScrollIndicator={false}>
          <Text style={styles.sectionDateTitle}>{formatSheetSectionDate()}</Text>

          <View style={[styles.ringRow, styles.ringRowTop]}>
            <RingCard label="Sommeil" value="5h12"  unit=""   progress={5.2 / 8}       color="#6366f1" trackColor="#ede9fe" onPress={() => onMetricPress('Sommeil', '5h12', '')} />
            <RingCard label="HRV"     value="42"     unit="ms" progress={42 / 80}        color="#ec4899" trackColor="#fce7f3" onPress={() => onMetricPress('HRV', '42', 'ms')} />
            <RingCard label="Pas"     value="3 240"  unit=""   progress={3240 / 10000}   color="#10b981" trackColor="#d1fae5" onPress={() => onMetricPress('Pas', '3 240', '')} />
          </View>
          <View style={styles.ringRow}>
            <RingCard label="SpO2"    value="97"    unit="%"   progress={97 / 100} color="#38bdf8" trackColor="#e0f2fe" onPress={() => onMetricPress('SpO2', '97', '%')} />
            <RingCard label="Stress"  value="Élevé" unit=""    progress={3 / 3}    color="#f87171" trackColor="#fee2e2" onPress={() => onMetricPress('Stress', 'Élevé', '')} />
            <RingCard label="Mindful" value="0"     unit="min" progress={0 / 30}   color="#a78bfa" trackColor="#ede9fe" onPress={() => onMetricPress('Mindful', '0', 'min')} />
          </View>

          {bloodTestStatus === 'idle' && (
            <Pressable style={styles.bloodTestBanner} onPress={() => setShowUpload(true)}>
              <MaterialCommunityIcons name="blood-bag" size={26} color="#dc2626" style={styles.bloodTestBannerIcon} />
              <View style={styles.bloodTestBannerTextCol}>
                <Text style={styles.bloodTestBannerTitle}>Déposez votre bilan sanguin</Text>
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
      </View>
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
  const [attachedContext, setAttachedContext] = useState<string | null>(null);
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
    <SafeAreaView style={styles.chatSafe}>
      <KeyboardAvoidingView style={styles.chatKeyboard} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
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
              <Text style={styles.bubbleText}>…</Text>
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
            placeholderTextColor="#9ca3af"
            onSubmitEditing={() => sendText(input)}
            returnKeyType="send"
          />
          <Pressable style={[styles.chatSend, recording && styles.chatSendRed]} onPress={recording ? toggleVoice : input.trim() ? () => sendText(input) : toggleVoice}>
            {recording ? (
              <Ionicons name="stop" size={22} color="#fff" />
            ) : input.trim() ? (
              <Ionicons name="arrow-up" size={22} color="#fff" />
            ) : (
              <Ionicons name="mic" size={22} color="#fff" />
            )}
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
        <Ionicons name="grid" size={24} color={active === 'dashboard' ? '#111827' : '#d1d5db'} />
        <Text style={[styles.tabLabel, active === 'dashboard' && styles.tabLabelActive]}>Dashboard</Text>
      </Pressable>
      <Pressable style={styles.tab} onPress={() => onChange('chat')}>
        <Ionicons name="mic" size={24} color={active === 'chat' ? '#111827' : '#d1d5db'} />
        <Text style={[styles.tabLabel, active === 'chat' && styles.tabLabelActive]}>Assistant</Text>
      </Pressable>
    </View>
  );
}

// ─── Root ─────────────────────────────────────────────────────────────────────

export default function App() {
  const [phase, setPhase] = useState<'intro' | 'intake' | 'main'>('intro');
  const [userName, setUserName] = useState('');
  const [tab, setTab] = useState<Tab>('dashboard');
  const [pendingContext, setPendingContext] = useState<string | null>(null);

  function skipOnboardingToMain() {
    setUserName('');
    setPhase('main');
  }

  if (phase === 'intro') {
    return (
      <OnboardingIntro
        onDone={() => setPhase('intake')}
        onSkip={skipOnboardingToMain}
      />
    );
  }
  if (phase === 'intake') {
    return (
      <VoiceIntake
        onDone={(name) => { setUserName(name); setPhase('main'); }}
        onSkip={skipOnboardingToMain}
      />
    );
  }

  function handleMetricPress(label: string, value: string, unit: string) {
    const msg = `Mon score ${label} est à ${value}${unit ? ' ' + unit : ''}. Qu'est-ce que ça indique pour ma santé ?`;
    setPendingContext(msg);
    setTab('chat');
  }

  return (
    <View style={{ flex: 1, backgroundColor: '#f5f6fa' }}>
      <View style={{ flex: 1, display: tab === 'dashboard' ? 'flex' : 'none' }}>
        <Dashboard onMetricPress={handleMetricPress} userName={userName} />
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
  // ── Splash / Onboarding ──
  splashScreen: { flex: 1, backgroundColor: '#fff', paddingHorizontal: 48, paddingTop: 16, paddingBottom: 48 },
  splashSkipRow: { width: '100%', flexDirection: 'row', justifyContent: 'flex-end', paddingBottom: 8 },
  skipLinkText: { fontFamily: fontSans, fontSize: 15, fontWeight: '600', color: '#6b7280' },
  splashTop: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 24, width: '100%' },
  onboardingLogo: { width: '88%', maxWidth: 300, aspectRatio: 390 / 101, alignSelf: 'center' },
  splashSub: { fontFamily: fontSans, fontSize: 15, color: '#6b7280', lineHeight: 24, textAlign: 'center' },
  splashBottom: { gap: 14, width: '100%', alignItems: 'center' },
  splashLegal: { fontFamily: fontSans, textAlign: 'center', fontSize: 12, color: '#9ca3af' },

  // ── Shared buttons ──
  btn: { backgroundColor: '#111827', borderRadius: 9999, paddingVertical: 18, alignItems: 'center', width: '100%' },
  btnText: { fontFamily: fontSans, color: '#fff', fontWeight: '700', fontSize: 16 },
  btnGhost: { flex: 1, backgroundColor: '#FAFAFA', borderRadius: 9999, paddingVertical: 18, alignItems: 'center' },
  btnGhostText: { fontFamily: fontSans, color: '#111827', fontWeight: '600', fontSize: 16 },
  row: { flexDirection: 'row', gap: 12, width: '100%', marginTop: 8 },

  // ── Voice Intake ──
  intakeScreen: { flex: 1, backgroundColor: '#fff', paddingHorizontal: 48, paddingTop: 8 },
  intakeSkipRow: { width: '100%', flexDirection: 'row', justifyContent: 'flex-end', paddingBottom: 8 },
  intakeScroll: { flex: 1, width: '100%' },
  intakeScrollContent: { alignItems: 'center', paddingBottom: 32, gap: 20, width: '100%' },
  intakeTitle: { fontFamily: fontSans, fontSize: 28, fontWeight: '800', color: '#111827', textAlign: 'center' },
  intakeSub: { fontFamily: fontSans, fontSize: 14, color: '#6b7280', textAlign: 'center' },
  intakeGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, justifyContent: 'center', width: '100%' },
  intakeField: { backgroundColor: '#f9fafb', borderRadius: 14, padding: 14, width: '46%', alignItems: 'center', gap: 4, borderWidth: 1, borderColor: '#e5e7eb' },
  intakeFieldFilled: { borderColor: '#111827', backgroundColor: '#f3f4f6' },
  intakeFieldIcon: { fontSize: 22 },
  intakeFieldLabel: { fontFamily: fontSans, fontSize: 11, color: '#9ca3af', fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5 },
  intakeFieldValue: { fontFamily: fontSans, fontSize: 16, fontWeight: '700', color: '#111827' },
  intakeFieldEmpty: { color: '#d1d5db' },
  intakeTranscript: { fontFamily: fontSans, fontSize: 13, color: '#6b7280', fontStyle: 'italic', textAlign: 'center', paddingHorizontal: 8 },
  intakeMic: { backgroundColor: '#111827', borderRadius: 60, width: 120, height: 120, alignItems: 'center', justifyContent: 'center', gap: 8 },
  intakeMicActive: { backgroundColor: '#ef4444', transform: [{ scale: 1.08 }] },
  intakeMicLabel: { fontFamily: fontSans, fontSize: 10, color: 'rgba(255,255,255,0.8)', fontWeight: '600', textAlign: 'center' },
  intakeError: { fontFamily: fontSans, color: '#ef4444', fontSize: 13, textAlign: 'center' },

  // ── Upload screen ──
  uploadScreen: { flex: 1, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center', padding: 32, gap: 16 },
  uploadEmoji: { fontSize: 64 },
  uploadTitle: { fontFamily: fontSans, fontSize: 26, fontWeight: '800', color: '#111827' },
  uploadMuted: { fontFamily: fontSans, fontSize: 14, color: '#6b7280', textAlign: 'center', lineHeight: 22 },
  uploadLoadingText: { fontFamily: fontSans, fontSize: 18, fontWeight: '700', color: '#111827', marginTop: 16 },
  uploadBtn: { backgroundColor: '#111827', borderRadius: 9999, paddingVertical: 16, paddingHorizontal: 32, width: '100%', alignItems: 'center', marginTop: 8 },
  uploadBtnText: { fontFamily: fontSans, color: '#fff', fontWeight: '700', fontSize: 16 },
  uploadCancelBtn: { paddingVertical: 12 },
  uploadCancelText: { fontFamily: fontSans, color: '#9ca3af', fontSize: 14 },
  uploadError: { backgroundColor: '#fef2f2', borderRadius: 10, padding: 12, width: '100%' },
  uploadErrorText: { fontFamily: fontSans, color: '#ef4444', fontSize: 13 },

  // ── Dashboard ──
  dashSafe: { flex: 1, backgroundColor: '#f5f6fa' },
  dashHeader: {
    paddingHorizontal: 24,
    paddingTop: 38,
    paddingBottom: 68,
    ...(Platform.OS === 'web'
      ? ({ backgroundImage: 'linear-gradient(180deg, #5178B6 0%, #DDEBF4 100%)' } as any)
      : { backgroundColor: '#8CB4DD' }),
  },
  dashHeaderTopRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 12, marginBottom: 16 },
  dashGreetingInCard: { flex: 1, fontFamily: fontSans, fontSize: 22, lineHeight: 28, fontWeight: '500', color: '#fff' },
  dashHeaderMeta: { alignItems: 'flex-end', gap: 4 },
  dashMetaLine: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  dashHeaderDate: { fontFamily: fontSans, fontSize: 13, fontWeight: '600', color: 'rgba(255,255,255,0.95)', textTransform: 'capitalize' },
  dashHeaderUv: { fontFamily: fontSans, fontSize: 13, fontWeight: '500', color: 'rgba(255,255,255,0.85)' },
  insightCard: { marginTop: 32, borderRadius: 16, overflow: 'hidden', paddingVertical: 16, paddingHorizontal: 16 },
  dashInCard: { fontFamily: fontSans, fontSize: 18, lineHeight: 30, fontWeight: '400' },
  dashHiInCard: { fontFamily: fontSans, fontSize: 18, lineHeight: 30, color: '#fff', fontWeight: '700' },
  dashDimInCard: { fontFamily: fontSans, fontSize: 18, lineHeight: 30, color: 'rgba(255,255,255,0.85)' },
  dashSheet: { flex: 1, backgroundColor: '#fff', borderTopLeftRadius: 28, borderTopRightRadius: 28, marginTop: -24 },
  sheetHandleWrap: { alignItems: 'center', paddingTop: 10, paddingBottom: 4 },
  sheetHandle: { width: 40, height: 5, borderRadius: 3, backgroundColor: '#e5e7eb' },
  dashContent: { paddingHorizontal: 24, paddingTop: 12, gap: 16, paddingBottom: 40 },
  sectionDateTitle: { fontFamily: fontSans, fontSize: 16, fontWeight: '700', color: '#9ca3af', letterSpacing: 0.4, marginBottom: 4, textTransform: 'capitalize' },

  // ── Cards / Rings ──
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  card: { backgroundColor: '#fff', borderRadius: 18, padding: 16, width: '47%', gap: 4, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.06, shadowRadius: 4 },
  cardIcon: { fontSize: 22, fontFamily: fontSans },
  cardValue: { fontFamily: fontSans, fontSize: 24, fontWeight: '800', color: '#111827' },
  cardUnit: { fontFamily: fontSans, fontSize: 14, fontWeight: '400', color: '#9ca3af' },
  cardLabel: { fontFamily: fontSans, fontSize: 12, color: '#6b7280' },
  cardHint: { fontFamily: fontSans, fontSize: 10, color: '#6366f1', marginTop: 4, fontWeight: '600' },
  ringRow: { flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: 4 },
  ringRowTop: { paddingTop: 16 },
  ringCard: { alignItems: 'center', flex: 1, backgroundColor: 'transparent', borderWidth: 0, shadowOpacity: 0, paddingVertical: 8 },
  ringWrap: { position: 'relative', alignItems: 'center', justifyContent: 'center', marginBottom: 8 },
  ringCenter: { position: 'absolute', alignItems: 'center', justifyContent: 'center' },
  ringValue: { fontFamily: fontSans, fontSize: 18, fontWeight: '800', lineHeight: 22 },
  ringUnit: { fontFamily: fontSans, fontSize: 10, fontWeight: '500', color: '#9ca3af', lineHeight: 12 },

  // ── Blood test banner ──
  bloodTestBanner: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#f9fafb', borderRadius: 16, padding: 16, marginTop: 8, gap: 12 },
  bloodTestBannerIcon: { marginTop: 2 },
  bloodTestBannerTextCol: { flex: 1, gap: 2 },
  bloodTestBannerTitle: { fontFamily: fontSans, color: '#111827', fontWeight: '700', fontSize: 15, marginBottom: 2 },
  bloodTestBannerSub: { fontFamily: fontSans, color: '#9ca3af', fontSize: 12 },
  bloodTestBannerArrow: { fontFamily: fontSans, color: '#111827', fontSize: 20, fontWeight: '700' },
  bloodTestDone: { backgroundColor: '#f0fdf4', borderRadius: 16, padding: 16, borderWidth: 1, borderColor: '#bbf7d0', alignItems: 'center', marginTop: 8 },
  bloodTestDoneText: { fontFamily: fontSans, color: '#16a34a', fontWeight: '700', fontSize: 15 },

  // ── Chat (light) ──
  chatSafe: { flex: 1, backgroundColor: '#f5f6fa' },
  chatKeyboard: { flex: 1, backgroundColor: '#f5f6fa' },
  chatScroll: { flex: 1, backgroundColor: '#f5f6fa' },
  chatContent: { padding: 16, gap: 12, paddingBottom: 8, flexGrow: 1 },
  bubble: { maxWidth: '80%', borderRadius: 16, padding: 14 },
  bubbleCoach: { backgroundColor: '#fff', alignSelf: 'flex-start', borderBottomLeftRadius: 4, borderWidth: 1, borderColor: '#e5e7eb', shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 3 },
  bubbleUser: { backgroundColor: '#6366f1', alignSelf: 'flex-end', borderBottomRightRadius: 4 },
  bubbleText: { fontFamily: fontSans, color: '#374151', fontSize: 15, lineHeight: 22 },
  bubbleTextUser: { color: '#fff' },
  contextChip: { flexDirection: 'row', alignItems: 'center', marginHorizontal: 12, marginBottom: 6, backgroundColor: '#eff6ff', borderRadius: 12, padding: 10, borderLeftWidth: 3, borderLeftColor: '#6366f1', gap: 8 },
  contextChipInner: { flex: 1 },
  contextChipLabel: { fontFamily: fontSans, fontSize: 10, color: '#6366f1', fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 2 },
  contextChipText: { fontFamily: fontSans, fontSize: 13, color: '#374151', lineHeight: 18 },
  contextChipClose: { fontFamily: fontSans, fontSize: 14, color: '#9ca3af', padding: 4 },
  chatBar: { flexDirection: 'row', padding: 12, gap: 8, borderTopWidth: 1, borderTopColor: '#e5e7eb', backgroundColor: '#fff' },
  chatInput: { flex: 1, backgroundColor: '#f3f4f6', borderRadius: 22, paddingHorizontal: 16, paddingVertical: 10, color: '#111827', fontSize: 15, fontFamily: fontSans },
  chatSend: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#111827', alignItems: 'center', justifyContent: 'center' },
  chatSendRed: { backgroundColor: '#ef4444' },

  // ── Tab bar ──
  tabBar: { flexDirection: 'row', backgroundColor: '#fff', paddingBottom: 28, paddingTop: 12 },
  tab: { flex: 1, alignItems: 'center', gap: 4 },
  tabLabel: { fontFamily: fontSans, fontSize: 11, color: '#d1d5db' },
  tabLabelActive: { color: '#111827' },
});
