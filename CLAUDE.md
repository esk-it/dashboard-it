# ITManager Dashboard — Projet de gestion IT

## Description
Application desktop de gestion IT pour un ensemble scolaire (3 sites : NDK, NDE, SU). Construite avec **Svelte 5 + FastAPI + SQLite + Tauri v2** (desktop Windows). Le backend Python est compilé en exe via PyInstaller et lancé comme sidecar Tauri.

## Architecture technique
- **Frontend** : Svelte 5, Vite, composants dans `src/lib/`
- **Backend** : FastAPI (Python), routers dans `backend/routers/`, services dans `backend/services/`
- **Base de données** : SQLite (`dashboard.db`), schema dans `backend/database.py`
- **Desktop** : Tauri v2 (`src-tauri/`), config dans `tauri.conf.json`
- **CI/CD** : GitHub Actions (`.github/workflows/release.yml`), build + sign + release auto sur tag `v*`
- **Données persistantes** : `%APPDATA%/ITManager-Dashboard/` via `ITMANAGER_DATA_DIR`

## Modules (13)
| Module | Page | Router backend | Description |
|--------|------|----------------|-------------|
| Accueil | `HomePage.svelte` | `dashboard.py` | Dashboard avec widgets configurables (taille/ordre), météo, KPIs |
| Actualités | `NewsPage.svelte` | `news.py` | Flux RSS avec mode lecture intégré |
| Planning | `PlanningPage.svelte` | `planning.py` | Calendrier mois/semaine/jour avec événements |
| Tâches | `TasksPage.svelte` | `tasks.py` | Liste/Kanban/Stats, templates, récurrence |
| Documents | `DocumentsPage.svelte` | `documents.py` | GED avec tags, liens entre docs |
| Prestataires | `SuppliersPage.svelte` | `suppliers.py` | Fiche détaillée, domaines, logos |
| Parc | `ParcPage.svelte` | `parc.py` | Inventaire avec arbre sites/bâtiments/salles, audit intelligent |
| Sécurité | `SecurityPage.svelte` | `security.py` | WithSecure : appareils, couverture, profils |
| Procédures | `WikiPage.svelte` | `wiki.py` | Wiki Markdown avec système de références (PROC-SI-NGINX-INST) |
| Changelog | `ChangelogPage.svelte` | `changelog.py` | Timeline visuelle avec groupement par mois |
| Monitoring | `MonitoringPage.svelte` | `monitoring.py` | Zabbix (pas encore développé) |
| Lanceur | `LauncherPage.svelte` | `launcher.py` | Liens rapides avec logos, favoris sur Dashboard |
| Outils | `ToolsPage.svelte` | `tools.py` | Ping, DNS, TCP, Traceroute, QR Code, IP Calc, WoL, WHOIS, Scanner ports |

## Intégrations externes
- **GLPI** : `backend/services/glpi.py` — sync inventaire via API REST
- **WithSecure** : `backend/services/withsecure.py` — appareils via OAuth2
- **Zabbix** : `backend/services/zabbix.py` — monitoring (config prête, module pas développé)
- **Open-Meteo** : météo gratuite sans clé API, géocodage ville configurable

## Composants clés
- `Sidebar.svelte` — Navigation avec logo établissement, badge tâches en retard, barre active
- `SplashScreen.svelte` — Animation de démarrage avec logo
- `SearchPalette.svelte` — Recherche globale (Ctrl+K)
- `QuickCreate.svelte` — Création rapide (Ctrl+N)
- `EmptyState.svelte` — Empty states animés réutilisables
- `GlassBackground.svelte` — Fond animé glass morphism
- Widgets Dashboard dans `src/lib/components/cards/` (PriorityCard, SysMonCard, GaugeChart, SparklineChart, DonutChart, ActivityCard, WeatherCard, LauncherFavCard, QuickLinksCard)

## Système de mise à jour
- `tauri-plugin-updater` v2 avec dialogue natif Windows
- Signature des bundles via `TAURI_SIGNING_PRIVATE_KEY` (GitHub secret)
- `latest.json` avec signature + URL du zip NSIS (méthode Store, pas Deflate)
- Notes de version extraites du message de commit
- Backup pré-MAJ automatique de la BDD
- Kill du backend.exe avant installation NSIS

## Paramètres (`SettingsPage.svelte`)
- Panneau 0 : Général (username, ville météo, refresh)
- Panneau 1 : Apparence (thème dark/light, accent, icônes modules, compact)
- Panneau 2 : Intégrations (WithSecure, GLPI config)
- Panneau 3 : Données (backup manuel/auto, export, reset)
- Panneau 4 : Mise à jour manuelle

## Conventions
- Les versions suivent semver : `v4.0.x` actuellement
- Commit messages en anglais avec `Co-Authored-By: Claude Opus 4.6`
- Tags Git déclenchent le build CI
- Fichiers de config/cache dans `ITMANAGER_DATA_DIR/data/` (AppData)
- Emojis : utiliser des littéraux en Python, `{'\u{XXXX}'}` en Svelte
- Svelte 5 : `{@const}` doit être le premier enfant d'un block `{#each}`, `{#if}`, etc.

## Commandes utiles
```bash
# Dev frontend
npm run dev

# Dev backend
python -m backend.main

# Build Tauri
npx tauri build

# Générer icônes app depuis logo
npx tauri icon src/assets/logo-square.png

# Lancer le backend manuellement
python run_backend.py
```

## Points d'attention
- Le backend sidecar met 3-5 secondes à démarrer → le frontend a des retries
- Les fichiers dans le dossier d'installation sont écrasés à chaque MAJ NSIS
- Toutes les configs persistantes doivent utiliser `ITMANAGER_DATA_DIR`
- `window.open()` ne fonctionne pas dans Tauri → utiliser `@tauri-apps/plugin-shell` `open()`
- Les endpoints FastAPI avec paramètre path (`/{id}`) doivent être APRÈS les routes fixes (`/references/tree`)
