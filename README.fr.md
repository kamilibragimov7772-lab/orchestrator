# Orchestrator — une stack d'orchestration vérifiable pour Claude Code

**[English](README.en.md) · [Русский](README.md) · [简体中文](README.zh-CN.md) · [Español](README.es.md) · [Português](README.pt-BR.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Deutsch](README.de.md) · [Français](README.fr.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md) · [Türkçe](README.tr.md)**

Transforme une session Claude Code en orchestrateur : un brief devient un plan de vagues, chaque
vague exécute des sous-agents spécialisés, chaque vague se matérialise dans un fichier, et un
relecteur indépendant accepte ou refuse le résultat. 41 fiches d'agent, 10 contrats partagés,
10 slash commands, 4 skills optionnelles.

Licence MIT. Auteur : **[@kamil_ibrgmv](https://instagram.com/kamil_ibrgmv)**. Protocole **2.16.0**.

> **À lire d'abord — la langue.** Le protocole d'orchestration, les fiches d'agent et les
> critères d'acceptation sont rédigés **en russe**. L'outillage, les tests, l'installation et les
> commentaires du code sont en anglais. Si ce sont les agents que vous cherchez, vous lirez du
> Markdown russe. Si c'est la plomberie qui rend une stack d'agents digne de confiance, cette
> partie ne dépend pas de la langue — et c'est la raison d'être de ce dépôt.

---

## Pourquoi ce projet existe

Les collections de sous-agents pour Claude Code ne manquent pas. Ce qui manque, ce sont celles
qu'on peut **vérifier**. La plupart sont un dossier de fichiers Markdown : rien ne prouve que les
hooks se déclenchent, rien ne prouve que le scanner de secrets lit les bons octets, et rien ne
casse quand une vérification cesse silencieusement de vérifier.

Ce dépôt fait l'arbitrage inverse. La bibliothèque d'agents est ordinaire ;
**c'est la plomberie autour qui compte** :

| Ce que livrent la plupart | Ce que livre ce dépôt |
|---|---|
| Uniquement du Markdown d'agents | Des agents **plus** des guards, un installeur, un doctor, un portail d'acceptation, une synchro |
| Aucun test | **97 tests**, bibliothèque standard uniquement, aucun appel d'API, aucun réseau |
| « Ajoutez ceci à settings.json » | Installeur avec préflight de collisions ; **le doctor exécute réellement le guard** et exige qu'il bloque |
| On suppose que les hooks marchent | Smoke test à trois charges : bénin doit passer, secret doit bloquer, commande risquée doit bloquer |
| « C'est sûr, faites confiance au prompt » | Le texte d'un prompt n'est jamais traité comme une frontière d'accès — voir [SECURITY.md](SECURITY.md) |

Tout ce qu'un script peut vérifier est vérifié par un script, parce qu'une règle qui ne vit que
dans un prompt est une règle qui cesse discrètement d'être suivie.

---

## Démarrage rapide

Nécessite **Python 3.10+** et **Git**. Sans clé d'API, sans réseau, sans appel au modèle :

```sh
git clone https://github.com/kamilibragimov7772-lab/orchestrator
cd orchestrator
python tools/verify.py
```

Cela lance le linter de contrats d'agent, l'autotest du compteur de préparation, la suite de
tests complète et un scan de secrets. Rien n'est touché en dehors du checkout.

Installez dans les répertoires de votre choix — l'installeur **planifie d'abord et n'écrase jamais** :

```sh
python tools/install.py \
  --destination /absolute/path/stack \
  --vault /absolute/path/knowledge-base \
  --mode minimal
```

Relisez le plan, puis relancez avec `--apply`. Si un fichier cible existe et diffère,
l'installation s'arrête et conserve le vôtre. Confirmez ensuite le résultat :

```sh
python tools/doctor.py --root /absolute/path/stack --installed
```

`minimal` installe sept rôles pour la recherche et les livrables Markdown. `full` ajoute les
pipelines logiciel / site / média et leurs dépendances externes. Notes Windows et manière de
pointer Claude Code vers le nouveau répertoire : [INSTALL.md](INSTALL.md).

---

## Ce que contient le dépôt

| Couche | Rôle | Limite de vérification |
|---|---|---|
| `_orchestr_protocol.md`, `agents/`, `commands/` | Routage, contrats, definition of done | Le linter vérifie la structure ; la qualité de la réponse exige une acceptation humaine |
| `tools/verify.py`, `tests/` | Une commande reproductible, cas négatifs inclus | Sans API Claude, sans MCP externe |
| `tools/guard.py` | Détection en PreToolUse des identifiants et commandes destructrices | **Défense en profondeur heuristique** — conservez permissions et sandbox de l'hôte |
| `tools/install.py`, `tools/doctor.py` | Installation non destructive ; rapport de préparation | Le doctor ne teste ni l'authentification ni la qualité du modèle |
| `tools/acceptance-gate/` | Vérifications déterministes du run-log plus un worker relecteur optionnel | Le worker modèle est **désactivé par défaut** ; bout-en-bout non certifié |
| `tools/sync_stack.py` | Pont Git sur une allowlist exacte | Optionnel ; refuse de fusionner à votre place des branches divergentes |
| `tools/export_session.py` | Export de transcriptions en opt-in | **Désactivé** ; le caviardage repose sur des motifs, ce n'est pas une garantie de confidentialité |

### Le portail d'acceptation

L'idée qui a demandé le plus de temps pour être juste. Une fois une exécution close, un
**contexte séparé** — qui n'a jamais vu le raisonnement de l'orchestrateur — juge le livrable
face au brief. Un script déterministe passe d'abord, et le modèle ne juge que ce que le script
ne peut pas juger :

- `run_status` et `verdict` sont deux champs distincts. Une exécution qui n'est pas `done`
  renvoie *« non soumise à acceptation »*, pas une réussite factice.
- `SKIP` donne **« incomplet »**, jamais « accepté ». Un PDF est signalé comme *signature
  seulement — ouvrez-le dans une visionneuse* ; un `.docx` comme *la structure se parse,
  l'acceptation visuelle est à part*.
- Les codes de sortie sont distincts : `0` accepté · `1` refusé · `3` incomplet ·
  `4` non applicable · `2` erreur.

La justification, mesurée par l'auteur sur 259 exécutions : une règle entrée dans un validateur
tient entre 76 % et 100 % du temps ; la même règle sous forme de texte de prompt, entre 0 % et 39 %.

---

## Ce qu'il refuse délibérément de faire

La confiance, c'est surtout la liste de ce qu'un outil s'interdit de faire dans votre dos :

- **Aucun export, miroir, push Git, cron ou processus modèle automatique à l'installation.**
  Chacun est en opt-in et exige une configuration explicite.
- **Aucun miroir façon `robocopy /MIR`.** Il pouvait supprimer côté destination des fichiers
  absents de la source. Il a été retiré.
- **Aucun écrasement.** Les fichiers en conflit arrêtent l'installation ; vos settings et hooks
  sont fusionnés, pas remplacés.
- **Aucune réussite silencieuse.** Une dépendance manquante ou une vérification non exécutée
  renvoie `NOT CHECKED` ou `SKIP`. Jamais une réussite non méritée.
- **Aucune note revendiquée sans preuve.** Un « 9,5/10 » était visé et **n'est pas certifié** —
  les points ouverts sont listés dans [`audit_9_5/`](audit_9_5/) plutôt que noyés dans une moyenne.

---

## État de la vérification

La CI tourne sur Windows / Linux / macOS × Python 3.10 et 3.12, analyse chaque script PowerShell
et scanne **tout l'historique Git** avec Gitleaks. Voir
[`.github/workflows/ci.yml`](.github/workflows/ci.yml).

Limites assumées, parce qu'un badge vert n'est pas une preuve :

- Les tests couvrent le comportement de l'outillage, pas la qualité de ce que les agents écrivent.
- L'acceptation bout-en-bout avec un vrai modèle **n'est pas** couverte par la suite.
- Les guards sont des heuristiques. Ils complètent les permissions de l'hôte ; ils ne les remplacent pas.

---

## Documentation

| Fichier | Réponse apportée |
|---|---|
| [INSTALL.md](INSTALL.md) | Installation, branchement à Claude Code, spécificités Windows |
| [AGENTS.md](AGENTS.md) | Point d'entrée pour travailler sur ce code |
| [SECURITY.md](SECURITY.md) | Ce que les guards protègent ou non ; confidentialité de l'export |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Les vérifications qu'un changement doit passer |
| [CHANGELOG.md](CHANGELOG.md) | Changements de comportement |

## Fondement méthodologique

Base d'ingénierie : **NIST SSDF 1.1** (NIST, 2022) — reproduire un défaut, le corriger, ajouter
une régression qui rejette le cas cassé — avec la documentation officielle de l'hôte
([Claude Code hooks](https://code.claude.com/docs/en/hooks)). Vérifié le 2026-09-06. Le SSDF sert
à sélectionner les risques, non de certificat de conformité.

## Licence

[MIT](LICENSE). Auteur : **[@kamil_ibrgmv](https://instagram.com/kamil_ibrgmv)**.
