import { Pressable, StyleSheet, Text } from 'react-native';
import { fontSans } from '../constants/fonts';

type State = 'idle' | 'recording' | 'transcribing';

interface Props {
  state: State;
  onPress: () => void;
}

const LABELS: Record<State, string> = {
  idle: '🎙 Parler',
  recording: '⏹ Arrêter',
  transcribing: '⏳ Transcription...',
};

export function VoiceButton({ state, onPress }: Props) {
  return (
    <Pressable
      style={[styles.btn, state === 'recording' && styles.btnRed]}
      onPress={onPress}
      disabled={state === 'transcribing'}
    >
      <Text style={styles.label}>{LABELS[state]}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  btn: {
    backgroundColor: '#6366f1',
    borderRadius: 14,
    paddingVertical: 18,
    alignItems: 'center',
    width: '100%',
  },
  btnRed: { backgroundColor: '#ef4444' },
  label: { fontFamily: fontSans, color: '#fff', fontWeight: '700', fontSize: 16 },
});
