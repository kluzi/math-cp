# Spécifications fonctionnelles — App Maths CP (Sofia)

2026-09-20 · document de travail, rédigé avant le développement du moteur et du Chapitre 1

Application web autonome (HTML, iPad/Safari), sœur de l'app *Maths CM2* développée pour Nola, adaptée pour **Sofia** (CP), basée sur le manuel *Tandem Maths CP* (Nathan, éd. 2025, "Mon fichier"), en suivant la progression de la classe.

> Projet distinct de l'app CM2 : dépôt Git dédié (`Maths CP`), moteur repensé pour le CP (types d'interaction tactiles plutôt que saisie clavier), mais on reprend telle quelle l'architecture qui a fait ses preuves côté progression, étoiles, récompenses et accès parent.

## 1. Vue d'ensemble et principes

- Appli web **autonome en un seul fichier HTML** (`index.html`), hors ligne, sans compte, sans dépendance externe chargée depuis internet (police, script) — seule exception assumée : la synthèse vocale utilise l'API navigateur `speechSynthesis`, embarquée dans Safari/iPadOS, qui ne nécessite pas de réseau à l'exécution
- Un seul profil utilisateur, prénom **Sofia** codé en dur (comme Nola pour l'app CM2)
- Contenu basé sur *Tandem Maths CP*, construit chapitre par chapitre à partir de photos des pages envoyées par le parent (dossier `Captures/`, fichiers nommés `<CODE_DOMAINE>-<NN>_<Nom_du_chapitre>.HEIC`)
- Objectif : entraînement quotidien très court (le CP décroche vite), ludique, très visuel, aligné sur la progression réelle de la classe
- Dépôt Git dédié (`Maths CP`), séparé de tout autre dépôt

## 2. Différences clés avec l'app CM2 (et pourquoi)

| Sujet | CM2 (Nola) | CP (Sofia) | Raison |
| --- | --- | --- | --- |
| Organisation du manuel | Périodes 1-5, chapitres numérotés en continu | 6 **domaines** colorés (Nombres entiers, Calcul, Résolution de problèmes, Grandeurs et mesures, Espace et géométrie, Organisation et gestion de données), chapitres numérotés **par domaine** | *Tandem Maths CP* n'a pas de découpage en périodes dans son sommaire ; c'est un sommaire par domaine |
| Structure d'un chapitre | 4 blocs (Leçon, Flash Maths, Calcul, Atelier problèmes) | **1 session unique** par chapitre = les exercices numérotés de la page + le "Bonus du jour" | Chaque chapitre CP correspond à une seule notion sur une double-page, pas à un regroupement de sous-blocs |
| Saisie | Clavier numérique, QCM, glisser d'étiquettes | **Manipulation tactile de collections d'objets** (toucher pour entourer/colorier/ajouter/barrer), pas de clavier | Sofia déchiffre encore peu et ne maîtrise pas la frappe ; le manuel CP est lui-même 100% manipulation visuelle |
| Chrono | Oui sur certains blocs (Flash Maths, Calcul) | **Non, aucun chrono en v1** | Ajouter une pression de temps à 6 ans sur des exercices de dénombrement serait contre-productif ; à reconsidérer plus tard si Sofia est à l'aise |
| Consignes | Texte lu par l'enfant | Texte court **+ bouton "écouter"** (voix de synthèse féminine, français) | Lecture encore fragile en début de CP |
| Déblocage | Chapitre suivant débloqué après 80% sur les 4 blocs | Chapitre suivant d'un domaine débloqué après 80% sur la session unique de ce chapitre ; **les 6 domaines sont ouverts en parallèle** (pas de verrou inter-domaine) | La classe avance sur plusieurs domaines la même semaine ; on ne connaît pas de découpage en périodes pour caler un verrouillage global |

Tout le reste (système d'étoiles, catalogue de récompenses éditable, code parent 4 chiffres, streak, objectif hebdomadaire, réinitialisation, stockage localStorage) est **repris à l'identique** du moteur CM2 : c'est un système validé, pas de raison de le repenser.

## 3. Structure de navigation

- **Accueil** : carte du jour personnalisée pour Sofia (créneaux horaires comme CM2) + streak + solde d'étoiles + jauge hebdomadaire + accès aux 6 domaines
- **Domaines** (couleur constante sur tous ses chapitres, reprise du sommaire du manuel) :
  - Nombres entiers — rose
  - Calcul — corail
  - Résolution de problèmes — vert
  - Grandeurs et mesures — bleu
  - Espace et géométrie — jaune
  - Organisation et gestion de données — bleu sarcelle/teal
- **Chapitres** : numérotés comme dans le sommaire du manuel, à l'intérieur de chaque domaine (ex. Nombres entiers : 1 à 30). Un chapitre n'est jouable qu'une fois le précédent du **même domaine** validé. Le contenu s'enrichit au fil des captures envoyées ; un chapitre sans contenu envoyé affiche "Contenu à venir"
- **Affichage du statut d'un chapitre** sur la page du domaine : verrouillé (cadenas) / débloqué non commencé / % de réussite / maîtrisé (trophée) — repris du CM2

## 4. Types d'exercices (moteur v1, d'après les Chapitres 1 à 3 du manuel)

Interaction commune : une **collection d'objets/nombres affichés en grille ou en vrac**, sur laquelle l'enfant tape pour sélectionner, ajouter ou éliminer — jamais de saisie clavier.

- **`tap_to_fill`** — compléter une collection jusqu'à un nombre cible : des cases vides à côté d'objets déjà présents, l'enfant tape sur les cases vides pour "ajouter" des objets jusqu'au compte demandé (remplace "Dessine les billes/jetons pour compléter")
- **`tap_select_quantity`** — toucher exactement N objets parmi un ensemble (remplace "Entoure le nombre d'objets demandé" / "Colorie le nombre d'objets demandé" — même mécanique, habillage visuel différent : contour ou remplissage de couleur selon la consigne d'origine)
- **`pair_sum`** — toucher deux nombres (ou deux représentations en points/dés) dont la somme fait le nombre cible, peut avoir plusieurs bonnes paires à trouver dans la même grille (remplace "Entoure toutes les façons de faire N avec deux nombres")
- **`compare_collections`** — toucher, parmi 2 (ou plus) collections affichées, celle qui est la plus grande ou la plus petite (remplace "Entoure la plus grande/petite collection")
- **`cross_out_to_equalize`** — toucher des objets en trop dans une collection pour qu'elle égale une autre collection donnée en référence (remplace "Barre les objets en trop")
- **`continue_pattern`** — compléter une suite qui se répète (couleurs/formes) en touchant la bonne couleur/forme pour chaque case vide (remplace "Colorie la suite")
- **`number_sequence_fill`** — compléter les nombres manquants sur une frise numérique, en touchant un petit clavier de 2-3 chiffres proposés (pas de saisie libre) (remplace "Écris" sur la frise)

Chaque exercice régénère des valeurs différentes à chaque lancement (objets, nombres, quantités), comme sur l'app CM2, pour éviter la mémorisation — en gardant la même structure et le même niveau de difficulté que la page du manuel.

Feedback immédiat après validation (icône + couleur), bonne réponse affichée en cas d'erreur, **bouton "écouter la consigne"** en haut de chaque exercice (icône haut-parleur, `speechSynthesis`, voix française féminine sélectionnée automatiquement parmi les voix disponibles).

## 5. Système de score, validation et récompenses

Repris à l'identique du moteur CM2 (voir `specifications-app-maths-cm2.md` §5) :
- Score par chapitre → étoiles de qualité (1-3), seuil de maîtrise 80%
- Monnaie virtuelle (étoiles) sur paliers de progression (chapitre maîtrisé, domaine entièrement maîtrisé)
- Catalogue de récompenses éditable par le parent (contenu propre à Sofia, à définir séparément de celui de Nola)
- Streak, objectif hebdomadaire (à confirmer : 40 min comme Nola, ou plus court vu l'âge — **à ajuster en marche selon l'usage réel**)
- Accès parent protégé par code à 4 chiffres (propre à cette app, indépendant du code de l'app CM2)

## 6. Charte graphique

- Couleur dominante par domaine (voir §3), constante sur tous les écrans d'un chapitre
- Icônes plates SVG dessinées sur mesure, pas d'emoji système (cohérent avec CM2)
- Gros boutons tactiles, zones de tap larges (doigts d'enfant de 6 ans, moins précis qu'à 10 ans)
- Pas de clavier à l'écran sauf le mini-clavier à choix limité de `number_sequence_fill`
- Typographie ronde/moderne (même famille que CM2)
- Mode paysage iPad : grille à 2 colonnes au-delà de 820px, comme CM2

## 7. Données et persistance

- localStorage uniquement, aucune synchronisation, aucune donnée envoyée à un serveur — identique à CM2
- Clé de stockage distincte de l'app CM2 (les deux apps peuvent tourner sur le même iPad sans se marcher dessus si besoin)

## 8. Workflow de contenu (photos du livre)

- Le parent envoie les captures dans `Captures/`, nommées `<CODE_DOMAINE>-<NN>_<Nom>.HEIC` (déjà en place pour Nombres entiers : `NE-01` à `NE-09`, avec des trous — NE-04 et NE-05 pas encore envoyés)
- Codes domaine à confirmer au fil de l'eau pour les 5 autres domaines (probable : CA = Calcul, RP = Résolution de problèmes, GM = Grandeurs et mesures, EG = Espace et géométrie, OG = Organisation et gestion de données)
- Les valeurs numériques et objets sont régénérés aléatoirement à chaque partie (voir §4), donc pas besoin de modifier les énoncés eux-mêmes comme sur l'app CM2 — la variation est déjà nativement gérée par le moteur
- Contenu enrichi progressivement, chapitre après chapitre

## 9. Points ouverts / hors périmètre v1

- Pas de multi-enfants dans cette app (Sofia uniquement, comme Nola dans la sienne)
- Chrono : absent en v1, à reconsidérer plus tard si besoin de dynamiser certains exercices
- Codes des 5 domaines restants (hors Nombres entiers) : à confirmer quand les premières captures arrivent
- Objectif hebdomadaire (minutes) : valeur de départ à ajuster selon l'usage réel de Sofia
- Contenu limité au Chapitre 1 "Construire des collections jusqu'à 10" pour le lancement ; les chapitres suivants seront ajoutés au fil des captures déjà reçues (NE-02, NE-03, NE-06 à NE-09) puis à venir
