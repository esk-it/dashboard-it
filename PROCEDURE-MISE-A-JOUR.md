# Procédure de mise à jour - ITManager Dashboard

## Travail quotidien

Tu continues à travailler normalement dans le dossier `Dashboard-Web`.
Rien ne change pour le développement.

## Quand tu veux publier une nouvelle version

### Étape 1 : Changer le numéro de version

Ouvre `src-tauri/tauri.conf.json` et incrémente la version :

```json
"version": "2.2.0"
```

Règle simple :
- Bug fix → `2.1.0` → `2.1.1`
- Nouvelle fonctionnalité → `2.1.0` → `2.2.0`
- Changement majeur → `2.1.0` → `3.0.0`

### Étape 2 : Pousser le code sur GitHub

```bash
git add .
git commit -m "v2.2.0 - description des changements"
git push origin master:main
```

### Étape 3 : Créer le tag (déclenche le build automatique)

```bash
git tag v2.2.0
git push origin v2.2.0
```

> Le numéro du tag doit correspondre à celui dans `tauri.conf.json`

### Étape 4 : Attendre

- Suivre le build sur : https://github.com/esk-it/dashboard-it/actions
- Ça prend environ 10-15 minutes
- Une fois terminé, la Release apparaît sur : https://github.com/esk-it/dashboard-it/releases

## Côté utilisateur

L'app vérifie automatiquement au démarrage s'il y a une mise à jour.
Si oui, elle la télécharge et l'installe en arrière-plan.

## En cas de problème

- Si le build échoue : vérifier les logs dans GitHub Actions
- Si la clé de signature est perdue : en regénérer une avec `npx @tauri-apps/cli signer generate` et mettre à jour le secret `TAURI_SIGNING_PRIVATE_KEY` dans GitHub + la pubkey dans `tauri.conf.json`
- Clé privée locale : `src-tauri/keys/updater.key` (ne jamais la partager)
