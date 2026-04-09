# Health Metrics Dictionary

All health metrics collected by V.I.T.A.L via Apple Watch / HealthKit.

## Vitals

| Metric | Unit | Description |
|--------|------|-------------|
| `heart_rate` | bpm | Instantaneous heart rate |
| `resting_hr` | bpm | Resting heart rate (calculated over the day) |
| `hrv` | ms | Heart rate variability — regularity between heartbeats. Higher = better recovery |
| `spo2` | % | Blood oxygen saturation |
| `respiratory_rate` | brpm | Breaths per minute (measured during sleep) |
| `wrist_temperature` | °C | Deviation from baseline wrist temperature (measured during sleep) |
| `vo2_max` | mL/kg/min | Maximum oxygen consumption — cardio fitness indicator |
| `walking_hr_avg` | bpm | Average heart rate while walking |

## Activity

| Metric | Unit | Description |
|--------|------|-------------|
| `steps` | count | Daily step count |
| `active_calories` | kcal | Calories burned during active movement |
| `resting_energy` | kcal | Basal metabolism calories (calculated from age, weight, HR) |
| `distance` | km | Walking + running distance |
| `workout` | min | Duration of recorded workout sessions |
| `stand_time` | min | Time spent standing during the day |
| `exercise_time` | min | Moderate+ physical activity time |

## Sleep

| Metric | Unit | Description |
|--------|------|-------------|
| `sleep` | hours | Total sleep duration |
| `sleep_deep` | hours | Deep sleep duration (physical recovery) |
| `sleep_rem` | hours | REM sleep duration (cognitive recovery) |

## Environment

| Metric | Unit | Description |
|--------|------|-------------|
| `audio_exposure` | dBASPL | Environmental noise level |

## Mindfulness

| Metric | Unit | Description |
|--------|------|-------------|
| `mindful_minutes` | min | Time spent in meditation/mindfulness sessions |
