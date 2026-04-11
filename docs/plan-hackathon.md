> **⚠️ SUPERSEDED (2026-04-11).** This plan describes the pre-pivot reactive weekly-checkup product. The current implementation plan is `docs/superpowers/plans/2026-04-11-proactive-coach-pivot.md`. Team-facing handoff: `HANDOFF.md`. Kept as historical record only.

# Plan — Hackathon Alan x Mistral (11 avril 2026)

## Le problème

L'absentéisme coûte 120 milliards €/an aux entreprises françaises (WTW, 2025). 36% des arrêts longue durée sont liés au stress et au burnout. Alan assure ces entreprises mais n'a aucune donnée objective pour prévenir le burnout — leur bilan de santé repose sur un questionnaire déclaratif que les gens remplissent une fois et oublient.

## Données clés (wiki)

- **2.5M Français** touchés par le burnout (OpinionWay 2022)
- **18-24 ans** = plus forte détérioration santé mentale
- **Sommeil <7h** = **17x plus de burnout** (étude healthcare workers)
- **€2-3B/an** coût du stress au travail (INRS)
- **0 concurrent direct** sur "burnout au travail" (6 apps analysées)
- **HRV ↔ burnout** validé scientifiquement : méta-analyse Kim & Cheon, BMJ Open continuous HRV monitoring
- **26% d'engagement hebdo** sur Alan Play → cadence cible du rituel V.I.T.A.L

## Le produit

Bilan de santé vocal qui croise **tes réponses vocales** avec ce que ton corps mesure (montres connectées via Thryve), pour détecter le burnout avant l'arrêt maladie.

- **Avec Watch** → bilan ultra précis (données objectives + déclaratif vocal)
- **Sans Watch** → bilan quand même (app Santé iPhone + questions vocales du LLM)
- **Le moment clé** → "Tu dis que tu vas bien mais ton HRV dit le contraire"
- **L'action** → prise de rdv pro santé remboursé par Alan

**Pitch one-liner:** "Le premier bilan de santé qui écoute ce que tu ressens ET mesure ce que ton corps dit."

## Ce qui est prêt

- [x] brain.py — system prompt stress/burnout, 6 tools (summary, latest, trend, compare, correlation, book_consultation)
- [x] **brain.py — mode `weekly_checkup`** : rituel hebdo structuré 5 étapes sur 168h (build_system_message(weekly_checkup=True))
- [x] **nudge.py — daily nudge detector** : `vital-nudge` scanne 24h, déclenche uniquement si HRV ↓15%, sommeil <6h ou FC repos >80
- [x] **berries.py — Alan Play ledger** : 3 actions vérifiables côté serveur (weekly_checkup=50, daily_nudge_accepted=5, streak_4_weeks=100)
- [x] health_store.py — 20 métriques, PostgreSQL, toutes les queries
- [x] health_server.py — POST /health (réception données)
- [x] voxtral.py — STT + TTS streaming
- [x] Modèles Swift — HealthMetric (20 types), APIModels, UserProfile, Conversation
- [x] Build pipeline — xcodegen → xcodebuild → simctl (Mac Mini SSH)
- [x] Seed data — 4 scénarios de test (healthy, stressed, athlete, sleep_deprived)
- [x] Profil utilisateur — âge, sexe, taille, poids injecté dans le LLM
- [x] **Wiki de recherche public** — 9 pages concept/entité + 30+ sources (committed sur `dev`, visible sur GitHub)

## Ce qui reste avant le 11

- [ ] Endpoint `POST /ask` (audio → STT → LLM avec tools → TTS → stream audio)
- [ ] **Formaliser le score 0–100** pour le checkup hebdo (les seuils existent dans `nudge.py`, reste à les pondérer)
- [ ] **Slide pitch "Engagement model"** avec la matrice berries (50 / 5 / 100)
- [ ] **Slide pitch "Research-backed"** pointant vers le wiki public
- [ ] Slides backup tech (archi Voxtral→Mistral→Voxtral, RGPD/HDS) — pour le Q&A
- [ ] Répartition Q&A figée (voir tableau ci-dessous)
- [ ] **Répétition pitch en blanc** au moins 1× avant le jour J
- [ ] Attendre les challenges partners (Discord)
- [ ] Figer le runbook jour J une fois les challenges connus

> ✅ Résolu aujourd'hui : seuils stress score (`nudge.py`), stat 17x burnout (déjà dans `wiki/concepts/sleep.md`).

## Q&A — qui répond à quoi

Pendant le pitch, **un seul speaker** (Alexis). Pendant le Q&A, le jury pose des questions, on répond en relais selon le domaine :

| Domaine | Qui | Munition |
|---|---|---|
| Produit / vision / pitch | Alexis | Plan + slides |
| Démo / UX / iOS | Spidey | App Watch + iPhone |
| Archi tech / Mistral / Voxtral | Byron | `wiki/raw/articles/agent_architecture.md` |
| Burnout / HRV / RGPD / Alan | Zinedine *(à confirmer)* | Wiki concept pages |

## Jour J — Runbook (9h - 22h30)

### 9h-10h — Setup (tous)
- Installer le backend sur le Mac (PostgreSQL + FastAPI)
- Vérifier le WiFi / hotspot 5G backup
- Vérifier le signing Xcode + pairing iPhone/Watch
- Répartir les tâches

### 10h-13h — Build core (parallèle)
| Qui | Quoi |
|-----|------|
| **Spidey + Claude** | Web app (frontend + FastAPI backend) |
| **Byron** | Backend Python (POST /ask + intégrations) |
| **Zinedine** | Design app + maquette dashboard |
| **Alexis** | Structure du pitch + slides |

### 13h-14h — Lunch + premier point
- Tester le flow iPhone → Backend → réponse vocale
- Identifier les blockers

### 14h-17h — Build Watch + polish
| Qui | Quoi |
|-----|------|
| **Spidey + Claude** | App Watch (mic + WatchConnectivity + playback) |
| **Byron** | Tests end-to-end, fix bugs backend |
| **Zinedine** | Intégrer le design dans l'app |
| **Alexis** | Affiner le pitch, préparer la démo |

### 17h-19h — Intégration + debug
- Flow complet : Watch → iPhone → Backend → réponse vocale
- Tester le bilan vocal en conditions réelles
- Fallback : si Watch marche pas, démo sur iPhone

### 19h-20h — Freeze code + répétition pitch
- Plus de code, on répète
- Préparer le scénario de démo (quelles questions poser)
- Tester la démo 3 fois

### 20h-22h30 — Pitch + démo + délibération

## Scénario de démo

### Acte 1 — Question libre (45 sec)
1. Spidey lève le poignet, parle à la Watch : "Comment je vais cette semaine ?"
2. V.I.T.A.L répond vocalement avec les vraies données Watch
3. Spidey : "Je me sens épuisé depuis quelques jours"
4. V.I.T.A.L croise le déclaratif avec les données : "Ton HRV a chuté de 48 à 22ms **et ton sommeil moyen est à 4h30/night. Le sommeil <7h multiplie le burnout par 17.** Ton corps confirme ce que tu ressens."
5. V.I.T.A.L propose : "Tu veux que je te prenne un rdv psy ? C'est remboursé à 100% par Alan."
6. Spidey : "Oui"
7. V.I.T.A.L : "Rdv mardi à 14h avec le Dr Martin. **+50 berries Alan Play pour ton checkup de la semaine.**"

### Acte 2 — Le rituel hebdo (45 sec) — *si le timing le permet*
1. Spidey : "OK V.I.T.A.L, mon checkup hebdo"
2. V.I.T.A.L démarre le rituel structuré : résumé semaine en 1 phrase + 3 questions ciblées
3. Synthèse : score burnout 0–100 + une action concrète
4. **Punchline pitch** : "Ce rituel s'inspire des 26% d'engagement hebdomadaire d'Alan Play. C'est notre point d'entrée dans l'écosystème Alan."

### Acte 3 — Le smart nudge (10 sec, slide ou voix-off)
- "Et si jamais tu as un signal de stress entre deux checkups, V.I.T.A.L te ping — **uniquement si ton corps le justifie**. Pas de notification quotidienne. On récompense ce qu'on ne peut pas tricher : ton corps."

## Fallbacks

| Problème | Fallback |
|----------|----------|
| Watch marche pas | Démo sur iPhone (même flow) |
| WiFi instable | Hotspot iPhone 5G |
| Signing Xcode | Compte Apple Developer (Spidey) |
| Latence API trop haute | Réponses pré-cachées pour la démo |
| Pas le temps pour la Watch | iPhone only, le flow reste identique |

## Ce qu'on NE build PAS (slides only)

- Dashboard web entreprise → maquette dans les slides
- Complication Watch → nice-to-have si le temps le permet
- Landing page → template rapide si Zinedine a le temps
- Intégration réelle Alan → vision dans le pitch
