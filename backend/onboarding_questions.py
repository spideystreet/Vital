"""Vocal onboarding question bank — ~15 high-signal questions from the Alan Precision questionnaire.

Each entry is pure data. Adding or removing a question is a one-line change —
no logic here, no side effects. The onboarding module iterates this list in order.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

FieldType = Literal["integer", "string", "enum", "boolean", "scale_1_10"]


@dataclass(frozen=True)
class OnboardingQuestion:
    id: str
    section: Literal["Baselines", "Context"]
    text_fr: str
    text_en: str
    field: str
    type: FieldType
    extraction_hint: str
    enum_values: tuple[str, ...] = ()


QUESTIONS: tuple[OnboardingQuestion, ...] = (
    OnboardingQuestion(
        id="age",
        section="Baselines",
        text_fr="Quel age as-tu ?",
        text_en="How old are you?",
        field="age",
        type="integer",
        extraction_hint="Extract an integer age in years. If the user says '32 ans' return 32.",
    ),
    OnboardingQuestion(
        id="sex",
        section="Baselines",
        text_fr="Quel est ton sexe ?",
        text_en="What is your sex?",
        field="sex",
        type="enum",
        enum_values=("male", "female", "other"),
        extraction_hint="Return one of male, female, other.",
    ),
    OnboardingQuestion(
        id="weight_kg",
        section="Baselines",
        text_fr="Quel est ton poids en kilos ?",
        text_en="What is your weight in kilograms?",
        field="weight_kg",
        type="integer",
        extraction_hint="Integer kilograms. Ignore units the user says.",
    ),
    OnboardingQuestion(
        id="height_cm",
        section="Baselines",
        text_fr="Quelle est ta taille en centimetres ?",
        text_en="What is your height in centimeters?",
        field="height_cm",
        type="integer",
        extraction_hint="Integer centimeters. If user says '1m80' return 180.",
    ),
    OnboardingQuestion(
        id="job",
        section="Baselines",
        text_fr="Quel est ton metier ?",
        text_en="What is your job?",
        field="job",
        type="string",
        extraction_hint="One short phrase describing the occupation.",
    ),
    OnboardingQuestion(
        id="weekly_endurance_hours",
        section="Baselines",
        text_fr="Combien d'heures de sport d'endurance fais-tu par semaine ?",
        text_en="How many hours of endurance training per week?",
        field="weekly_endurance_hours",
        type="integer",
        extraction_hint="Integer hours per week. 0 if none.",
    ),
    OnboardingQuestion(
        id="avg_sleep_hours",
        section="Baselines",
        text_fr="Combien d'heures dors-tu en moyenne par nuit ?",
        text_en="On average, how many hours do you sleep per night?",
        field="avg_sleep_hours",
        type="integer",
        extraction_hint="Integer hours. Round half-hours to nearest integer.",
    ),
    OnboardingQuestion(
        id="sitting_hours_per_day",
        section="Context",
        text_fr="Combien d'heures passes-tu assis par jour ?",
        text_en="How many hours per day do you spend sitting?",
        field="sitting_hours_per_day",
        type="integer",
        extraction_hint="Integer hours sitting per day.",
    ),
    OnboardingQuestion(
        id="smoker",
        section="Context",
        text_fr="Est-ce que tu fumes ?",
        text_en="Do you smoke?",
        field="smoker",
        type="boolean",
        extraction_hint="True if the user currently smokes, False otherwise.",
    ),
    OnboardingQuestion(
        id="alcohol_frequency",
        section="Context",
        text_fr="A quelle frequence bois-tu de l'alcool ?",
        text_en="How often do you drink alcohol?",
        field="alcohol_frequency",
        type="enum",
        enum_values=("never", "rarely", "weekly", "several_per_week", "daily"),
        extraction_hint="Map the answer to one of the enum values.",
    ),
    OnboardingQuestion(
        id="sleep_satisfaction",
        section="Context",
        text_fr="Sur une echelle de 1 a 10, a quel point es-tu satisfait de ton sommeil ?",
        text_en="On a scale of 1 to 10, how satisfied are you with your sleep?",
        field="sleep_satisfaction",
        type="scale_1_10",
        extraction_hint="Integer 1-10. Clamp to that range.",
    ),
    OnboardingQuestion(
        id="dominant_emotion_30d",
        section="Context",
        text_fr="Quelle emotion as-tu le plus ressentie ces 30 derniers jours ?",
        text_en="What emotion have you felt most strongly in the past 30 days?",
        field="dominant_emotion_30d",
        type="string",
        extraction_hint="One word or short phrase describing the emotion.",
    ),
    OnboardingQuestion(
        id="work_mental_impact",
        section="Context",
        text_fr=(
            "Sur une echelle de 1 a 10, a quel point ton travail"
            " impacte-t-il ton bien-etre mental en ce moment ?"
        ),
        text_en="On a scale of 1 to 10, how much is your work impacting your mental well-being?",
        field="work_mental_impact",
        type="scale_1_10",
        extraction_hint="Integer 1-10. 1 = no impact, 10 = severe impact.",
    ),
    OnboardingQuestion(
        id="family_cvd",
        section="Context",
        text_fr="Y a-t-il des antecedents de maladies cardiovasculaires dans ta famille proche ?",
        text_en="Is there a family history of cardiovascular disease in your close relatives?",
        field="family_cvd",
        type="boolean",
        extraction_hint="True if yes, False if no.",
    ),
    OnboardingQuestion(
        id="current_medications",
        section="Context",
        text_fr="Prends-tu des medicaments actuellement ? Si oui, lesquels ?",
        text_en="Are you currently taking any medications? If yes, which ones?",
        field="current_medications",
        type="string",
        extraction_hint="List the medications as a comma-separated string, or 'none'.",
    ),
)
