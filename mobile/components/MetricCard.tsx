import { StyleSheet, Text, View } from 'react-native';
import { fontSans } from '../constants/fonts';

interface Props {
  label: string;
  value: number | null;
  unit?: string;
}

export function MetricCard({ label, value, unit }: Props) {
  return (
    <View style={styles.card}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.value}>
        {value !== null ? `${value}${unit ? ` ${unit}` : ''}` : '—'}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#1a1a1a',
    borderRadius: 14,
    padding: 16,
    flex: 1,
    minWidth: '45%',
  },
  label: { fontFamily: fontSans, color: '#888', fontSize: 12, marginBottom: 6 },
  value: { fontFamily: fontSans, color: '#fff', fontSize: 24, fontWeight: '700' },
});
