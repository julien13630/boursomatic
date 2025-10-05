````markdown
# Boursomatic

Plateforme MVP d\'aide à la compréhension des recommandations boursières pour débutants : ingestion de données marchés (US & Euronext), génération de signaux (BUY / HOLD / SELL) via un modèle ML tabulaire (LightGBM) + justification condensée, interface web simple (Next.js + Chakra UI), et backtest pédagogique (phase ultérieure).

> Objectif MVP P0 : Aller de l\'ingestion daily historique + features + entraînement modèle + inférence batch jusqu\'à une UI listant les recommandations filtrables, avec authentification de base et observabilité minimale.

---
## 1. Vision & Valeur
- **Public cible** : Débutants/intermédiaires souhaitant comprendre des signaux simples plutôt que du trading haute fréquence.
- **Valeur** : Synthèse lisible (profil risque, horizon, expected return, stop/take), justification courte, transparence des métriques de modèle.
- **Limites** : Pas un outil de conseil financier personnalisé. Modèle initial purement quantitatif / explicatif simplifié.

---
## 2. Roadmap Phasée (Synthèse)
| Phase | Contenu principal | Statut | Objectif prioritaire |
|-------|------------------|--------|----------------------|
| 0 | Initialisation, DB, Infra GCP, CI/CD | En cours | Base propre & déploiement continu |
| 1 | Ingestion marché (daily + intraday) | En cours | Données fiables multi-sources |
| 2 | Features + Modèle LightGBM + Validation | En cours | Signaux exploitables reproductibles |
| 3 | Auth & Sécurité (sessions, rate limit, consentement) | À faire | Cadre utilisateur sûr |
| 4 | Frontend UI (listes, détail, historique) | À faire | Expérience utilisateur basique |
| 5 | Backtest pédagogique (simulation, métriques) | P1 | Crédibilité & rétention |
| 6 | Observabilité & Alertes | À faire | Fiabilité opérationnelle |
| 7 | Finalisation (doc, runbooks) | P1/P2 | Maintenabilité |

Les issues P0 couvrent Phases 0,1,2,3,4,6. La Phase 5 (Backtest) est P1.

---
## 3. Organisation des Issues
Chaque sous-issue suit un format standard pour faciliter l\'automation par agent :
```
Parent: #<numéro epic>
Order: Phase X.Y

Context: <contexte succinct>
Task: <formulation actionnable>
Steps:
- ...
Acceptance Criteria:
- ...
- Checklist:
  - [ ] ...
Technical Hints: ...
Dependencies: ...
Deliverables: ...
LLM Notes: (contraintes rédaction / ton / limites)
```

### 3.1. Principes de Nomination
- Titre : `[P0][Phase 2.2] Entraînement LightGBM classifier + regressor`
- Préfixes de labels (non encore appliqués à toutes les issues) :
  - `priority-P0`, `priority-P1`...
  - `domain-<foundation|ingestion|ml|auth|ui|backtest|observability>`
  - `phase-<n>`

### 3.2. Épics (exemples)
| Epic | Rôle |
|------|------|
| #2 Ingestion & stockage | Sources marché, stockage, cohérence |
| #3 IA/ML | Features, entraînement, validation, inférence |
| #4 Authentification & Sécurité | Accès & protection |
| #5 Frontend UI/UX | Expérience utilisateur |
| #6 Backtest pédagogique | Simulation & metrics ex-post |
| #7 Observabilité & Qualité | Logs, metrics, alertes |

---
## 4. Stack Technique
| Couche | Technologies |
|--------|--------------|
| Backend API | FastAPI, Python 3.12 |
| Modèle ML | LightGBM, pandas, numpy |
| DB | PostgreSQL (Cloud SQL), SQLAlchemy/Alembic |
| Cache / Rate Limit | Redis (Memorystore) |
| Frontend | Next.js 14, React Query, Chakra UI |
| Infra | GCP (Cloud Run, Cloud SQL, Secret Manager, Memorystore), Terraform (cible) |
| CI/CD | GitHub Actions (lint, tests, build, deploy) |
| Observabilité | Logs JSON + trace_id, prometheus_client (metrics), alertes email |

---
## 5. Modèle de Données (MVP simplifié)
```
users(id, email, password_hash, is_admin, is_deleted, created_at)
instruments(id, symbol, exchange, sector, market_cap_bucket, pe_bucket)
price_bars(id, instrument_id, ts, o, h, l, c, v, interval)
features(id, instrument_id, ts, ret_1d, ret_5d, ret_20d, rsi_14, momentum_5d, vol_20d, atr_14, volume_zscore, ...)
model_versions(id, version, trained_at, params_hash, metrics_json)
recommendations(id, instrument_id, profile, label, confidence, expected_return_pct, horizon_days, stop_loss, take_profit, justification, features_snapshot, model_version, generated_at)
```
Principes :
- Clés UUID (côté appli) ou int séquentiel (option). P0 : UUID OK.
- `interval` pour distinguer daily vs intraday.
- `features_snapshot` dans `recommendations` pour audit.

---
## 6. Pipeline Données & ML (Flux P0)
1. Ingestion daily historique (8 ans) → `price_bars`
2. Ingestion intraday (rolling J-30 15m) → enrichissement optionnel
3. Génération features → `features`
4. Split temporel (train / val / test) → entraînement LightGBM (classification + régression expected_return)
5. Walk-forward (Phase 2.3) → metrics (Precision BUY, Sharpe, Max Drawdown)
6. Inférence batch (Phase 2.4) → `recommendations`
7. Exposition API → Frontend (liste + détail)

---
## 7. Conventions Code
- Python : ruff/black, type hints (mypy optionnel plus tard)
- Dossiers: `backend/app`, `frontend/`, `scripts/`
- Nommage tables : snake_case
- Logs : JSON structurés (trace_id, level, msg, path, status, duration_ms)
- Tests : `pytest` (cible P0 core ingestion + features + train + auth)

---
## 8. Sécurité (P0)
- Auth email/password (Argon2id via passlib)
- JWT en cookie httpOnly + SameSite=Lax
- Rate limiting + brute force lock (Redis)
- Headers sécurité (CSP de base, HSTS, X-Frame-Options, etc.)
- Consentement risques obligatoire (stocké user_setting/colonne dedicated)

---
## 9. Observabilité (P0)
- Middleware trace_id + logs JSON
- Endpoint /metrics (usage interne) : jobs_ingestion_total, jobs_inference_total, recommendations_total, http_500_total
- Alertes email : échec ingestion/inférence, rafale d\'erreurs 500

---
## 10. Roadmap Post-P0 (extraits P1/P2)
- Backtest (simulation naïve, paramètres, metrics, benchmark SPY/CAC, export CSV)
- Drift monitoring simple (baisse Precision BUY)
- Justifications améliorées (LLM templating + guardrails)
- Admin modèle (promotion version)
- Onboarding / glossary / pédagogie

---
## 11. Contribution & Branching (Suggestion)
| Type | Préfixe | Exemple |
|------|---------|---------|
| Feature | `feat/phase-2-2-train-model` | Ajout train model |
| Fix | `fix/phase-1-2-fallback` | Correction fallback Stooq |
| Chore | `chore/ci-add-badge` | Ajustements CI |

PR Checklist (recommandé) :
- [ ] Lint OK
- [ ] Tests passent
- [ ] Mise à jour doc si applicable
- [ ] Pas de secrets commit

---
## 12. Variables d\'Environnement (échantillon)
```
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/boursomatic
SECRET_KEY=changeme
LLM_API_KEY=changeme
REDIS_URL=redis://localhost:6379/0
```

---
## 13. Limitations Connues
- Pas de couverture tests complète (prioriser ingestion + ML core + auth)
- Justification modèle simple (pas encore d\'explicabilité avancée SHAP)
- Gestion intraday minimaliste (15m, J-30)

---
## 14. Comment Lire une Sous-Issue
Chercher :
- `Acceptance Criteria` → définition de DONE
- `Checklist` → vérifications opérationnelles
- `Dependencies` → ordre d\'exécution
- `LLM Notes` → contraintes pour génération assistée

---
## 15. Licence
MIT (à ajouter si pas encore en place).

---
## 16. Avertissement
Ce projet ne fournit pas de conseil financier. Usage éducatif uniquement.

---
## 17. Prochaines Actions Immédiates (au moment de cette révision)
1. Appliquer labels manquants (priority-P0, domain-*, phase-*) aux issues existantes.
2. Implémenter ingestion daily + seed historique (#25 dépend #26 + #27).
3. Enchaîner features (#23) → entraînement (#22) → validation (#21) → inférence (#20).
4. Lancer travail Auth (#19 → #18 → #17 → #16).
5. UI pages (#15 → #14 → #13 → #12).
6. Observabilité (#11 → #10 → #9).

---
*(README enrichi pour fournir le contexte global aux agents / contributeurs.)*