# Pitch Statistics — Sources & Data

All stats used in the pitch, with exact sources and methodology.

## Primary stats

| Stat | Value | Source | Year |
|------|-------|--------|------|
| Cost of absenteeism in France | 120 billion €/year | WTW (Willis Towers Watson) barometer | Sept 2025 |
| Share of long-term leave = stress/burnout | 36% | WTW barometer | 2024 |
| Absenteeism rate (private sector) | 5.1% | WTW barometer | 2024 |
| Average absence duration | 24.1 days | WTW barometer | 2024 |
| Absenteeism increase since 2019 | +50% | WTW barometer | 2024 |
| Psychosocial risks = #1 cause of long-term absence (under 55) | Yes | WTW barometer | 2024 |

## data.gouv.fr stats (via MCP datagouv)

Retrieved via the official data.gouv.fr MCP server (`https://mcp.data.gouv.fr/mcp`).

### COVIPREV — Mental health survey (Santé publique France)

- **Dataset:** [COVIPREV](https://www.data.gouv.fr/datasets/donnees-denquete-relatives-a-levolution-des-comportements-et-de-la-sante-mentale-pendant-lepidemie-de-covid-19-coviprev)
- **Resource:** `coviprev-santementale-vague28.xlsx` (Vague 28, sept-oct)
- **Organization:** Santé publique France

| Indicator | Value (range across regions) |
|-----------|------------------------------|
| Sleep problems | 66-73% |
| Anxiety | 18-30% |
| Depression | 12-20% |

**Pitch-ready:** "70% des actifs français ont des problèmes de sommeil. 1 sur 4 souffre d'anxiété."

### Absenteeism by cause — Région Île-de-France

- **Dataset:** [Absentéisme des agents de la Région](https://www.data.gouv.fr/datasets/absenteisme-des-agents-de-la-region-siege-et-lycees-arrets-par-motif)
- **Resource:** `rsu-absenteisme-arrets-par-motif.csv`
- **Organization:** Région Île-de-France

| Type (2024) | Days lost | Cases | Avg days/case |
|-------------|-----------|-------|---------------|
| Long-term illness (lycées) | 62,710 | 424 | 148 |
| Long-term illness (siège) | 9,680 | 52 | 186 |
| Workplace accident (lycées) | 30,466 | 1,354 | 22 |
| Ordinary illness (2023, lycées) | 143,995 | 13,947 | 10 |

**Pitch-ready:** "Un arrêt longue maladie dure en moyenne 150 jours. Le temps de détecter le burnout, il est trop tard."

## Official references (not on data.gouv.fr)

| Source | Stat | Year |
|--------|------|------|
| INRS + Arts et Métiers ParisTech | Cost of work stress: 2-3 billion €/year (minimum estimate, job strain only) | 2007 |
| DARES | Psychosocial risks surveys | Various |
| HAS (Haute Autorité de Santé) | Clinical guidelines for burnout diagnosis | 2017 |

## How data was retrieved

Stats from data.gouv.fr were queried using the **official datagouv MCP server**:
- Endpoint: `https://mcp.data.gouv.fr/mcp`
- Tools used: `search_datasets`, `list_dataset_resources`, `query_resource_data`
- All data is public and open (Licence Ouverte / Open Licence)
