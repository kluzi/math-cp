#!/usr/bin/env python3
"""Génère les voix ElevenLabs des énoncés de l'app (un MP3 par phrase, dans audio/).

Usage (depuis la racine du projet) :
  python3 tools/generer_voix.py voix                    # liste les voix de ton compte
  python3 tools/generer_voix.py essai --voice-id XXX    # une phrase test, jouée tout de suite
  python3 tools/generer_voix.py phrases                 # recense les phrases de l'app -> tools/phrases.json
  python3 tools/generer_voix.py estimer --voice-id XXX  # combien de phrases / crédits, sans rien appeler
  python3 tools/generer_voix.py generer --voice-id XXX  # génère les MP3 manquants (reprise possible)

La clé API se lit dans la variable d'environnement ELEVENLABS_API_KEY (jamais dans le code) :
  export ELEVENLABS_API_KEY=...
Seule la bibliothèque standard de Python est utilisée.
"""
import argparse, hashlib, html, json, os, re, shutil, subprocess, sys, tempfile, time
import urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'index.html')
PHRASES = os.path.join(ROOT, 'tools', 'phrases.json')
AUDIO_DIR = os.path.join(ROOT, 'audio')
MANIFEST = os.path.join(AUDIO_DIR, 'manifest.json')
API = 'https://api.elevenlabs.io/v1'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

DEFAULT_MODEL = 'eleven_multilingual_v2'
# Crédits ElevenLabs consommés par caractère selon le modèle
CREDITS_PER_CHAR = {'eleven_multilingual_v2': 1.0, 'eleven_flash_v2_5': 0.5, 'eleven_turbo_v2_5': 0.5, 'eleven_v3': 1.0}

# Passes de build() par chapitre pour recenser les variantes aléatoires d'énoncés
COLLECT_RUNS = 400


def speech_key(text):
    """Doit rester identique à speechKey() dans index.html."""
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]*>', ' ', str(text))).strip()


def speech_units(key):
    """Morceaux à enregistrer pour une phrase. Doit rester identique à speechUnits() dans index.html.
    Les énoncés « Colorie 2 carrés en bleu et 3 étoiles en rose. » combinent au hasard nombre, forme et
    couleur (plus de 1500 phrases) : on les découpe en morceaux réutilisables que l'app enchaîne."""
    m = re.match(r'^Colorie (.+)\.$', key)
    if not m:
        return [key]
    parts = re.split(r', | et ', m.group(1))
    if len(parts) < 2:
        return [key]
    return ['Colorie'] + [('et ' + p + '.') if i == len(parts) - 1 else (p + ',') for i, p in enumerate(parts)]


def all_units(phrases):
    return sorted({u for p in phrases for u in speech_units(p)})


def select_units(phrases, exclure):
    units = all_units(phrases)
    if exclure:
        rx = re.compile(exclure)
        units = [u for u in units if not rx.search(u)]
    return units


def clip_name(voice_id, model, text):
    return hashlib.sha1(f'{voice_id}|{model}|{text}'.encode('utf-8')).hexdigest()[:12] + '.mp3'


def die(msg):
    sys.exit(f'Erreur : {msg}')


# ---------------------------------------------------------------- phrases
COLLECTOR_JS = """
<script>
(function(){
  const seen = new Set(); const stats = {};
  const RUNS = %d;
  Object.keys(CHAPTERS).forEach(function(d){
    CHAPTERS[d].forEach(function(c){
      if(!c.ready || !c.build) return;
      const mine = new Set(); let half = [];
      for(let i=0;i<RUNS;i++){
        c.build().forEach(function(it){
          const t = it.speech || it.instruction;
          if(t) mine.add(speechKey(t));
        });
        if(i===RUNS/2-1) half = Array.from(mine);
      }
      mine.forEach(function(t){ seen.add(t); });
      stats[d+'-'+c.num] = {title:c.title, half:half, all:Array.from(mine)};
    });
  });
  const pre = document.createElement('pre'); pre.id = 'phrases-out';
  pre.textContent = JSON.stringify({phrases:Array.from(seen).sort(), stats:stats});
  document.body.innerHTML = ''; document.body.appendChild(pre);
})();
</script>
""" % COLLECT_RUNS


def cmd_phrases(args):
    if not os.path.exists(CHROME):
        die("Google Chrome introuvable. Ouvre index.html dans Chrome, puis exécute dans la console "
            "le contenu de COLLECTOR_JS (voir ce script) et enregistre le résultat dans tools/phrases.json.")
    src = open(INDEX, encoding='utf-8').read()
    # injecté juste avant le démarrage de l'app (setTimeout goHome) : tout le code de l'app est déjà défini
    marker = 'setTimeout(()=>{ goHome(); }, 900);'
    if marker not in src:
        die("repère de démarrage introuvable dans index.html (setTimeout goHome) : adapter tools/generer_voix.py")
    src = src.replace(marker, '</script>' + COLLECTOR_JS + '<script>', 1)
    tmp = tempfile.mkdtemp(prefix='collecte_')
    try:
        page = os.path.join(tmp, 'index.html')
        open(page, 'w', encoding='utf-8').write(src)
        out = subprocess.run(
            [CHROME, '--headless=new', '--disable-gpu', '--no-sandbox', '--virtual-time-budget=30000',
             f'--user-data-dir={os.path.join(tmp, "profil")}', '--dump-dom', 'file://' + page],
            capture_output=True, text=True, timeout=180)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    m = re.search(r'<pre id="phrases-out">(.*?)</pre>', out.stdout, re.S)
    if not m:
        die('la collecte n\'a rien renvoyé.\n' + out.stderr[-800:])
    data = json.loads(html.unescape(m.group(1)))
    json.dump(data, open(PHRASES, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    phrases = data['phrases']
    units = all_units(phrases)
    print(f"{len(phrases)} phrases uniques -> {len(units)} clips à enregistrer, {sum(len(u) for u in units)} caractères")
    for k, st in data['stats'].items():
        u_all, u_half = set(all_units(st['all'])), set(all_units(st['half']))
        late = len(u_all - u_half)
        print(f"  {k:6} {len(st['all']):5} phrases, {len(u_all):4} clips"
              + (f"  ({late} clips apparus dans la 2e moitié des passes : relancer `phrases` ou augmenter COLLECT_RUNS)" if late else ''))
    # les chapitres plus longs à converger sont signalés ci-dessus ; les phrases rares manquantes retombent sur la voix du navigateur


def load_phrases():
    if not os.path.exists(PHRASES):
        die("tools/phrases.json absent : lance d'abord `python3 tools/generer_voix.py phrases`")
    return json.load(open(PHRASES, encoding='utf-8'))['phrases']


# ---------------------------------------------------------------- manifeste
def load_manifest():
    if os.path.exists(MANIFEST):
        return json.load(open(MANIFEST, encoding='utf-8'))
    return {'voice_id': None, 'model': None, 'clips': {}}


def save_manifest(man):
    os.makedirs(AUDIO_DIR, exist_ok=True)
    tmp = MANIFEST + '.tmp'
    json.dump(man, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, MANIFEST)


def todo_list(units, voice_id, model, man, force):
    todo = []
    for p in units:
        f = clip_name(voice_id, model, p)
        if force or man['clips'].get(p) != f or not os.path.exists(os.path.join(AUDIO_DIR, f)):
            todo.append(p)
    return todo


# ---------------------------------------------------------------- API
def api_key():
    k = os.environ.get('ELEVENLABS_API_KEY')
    if not k:
        die("variable ELEVENLABS_API_KEY absente. Dans ton terminal : export ELEVENLABS_API_KEY=ta_cle")
    return k


def api_request(path, body=None, retries=4):
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            API + path, data=json.dumps(body).encode() if body is not None else None,
            headers={'xi-api-key': api_key(), 'Content-Type': 'application/json', 'Accept': '*/*'})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            detail = e.read().decode('utf-8', 'replace')[:400]
            if e.code in (429, 500, 502, 503) and attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            if e.code == 401:
                die(f'clé API refusée (401). {detail}')
            die(f'ElevenLabs a répondu {e.code} : {detail}')
        except urllib.error.URLError as e:
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            die(f'réseau : {e.reason}')


def synth(text, voice_id, model, speed, stability, similarity):
    body = {'text': text, 'model_id': model,
            'voice_settings': {'stability': stability, 'similarity_boost': similarity, 'style': 0.0,
                               'use_speaker_boost': True, 'speed': speed}}
    return api_request(f'/text-to-speech/{voice_id}?output_format=mp3_44100_64', body)


# ---------------------------------------------------------------- commandes
def cmd_voix(args):
    data = json.loads(api_request('/voices'))
    for v in sorted(data.get('voices', []), key=lambda v: v['name']):
        lab = v.get('labels') or {}
        desc = ', '.join(x for x in (lab.get('language'), lab.get('gender'), lab.get('age'), lab.get('descriptive'), lab.get('use_case')) if x)
        print(f"{v['voice_id']}  {v['name']:<22} {desc}")
    print("\nUne voix de la bibliothèque publique doit d'abord être ajoutée à « Mes voix » sur elevenlabs.io.")


def cmd_essai(args):
    text = args.texte
    audio = synth(text, args.voice_id, args.model, args.speed, args.stability, args.similarity)
    out = os.path.join(ROOT, 'tools', 'essai.mp3')
    open(out, 'wb').write(audio)
    print(f'{len(text)} caractères -> {out}')
    if sys.platform == 'darwin':
        subprocess.run(['afplay', out])


def cmd_estimer(args):
    phrases = load_phrases()
    man = load_manifest()
    todo = todo_list(select_units(phrases, args.exclure), args.voice_id, args.model, man, args.force)
    chars = sum(len(p) for p in todo)
    rate = CREDITS_PER_CHAR.get(args.model, 1.0)
    print(f"{len(select_units(phrases, args.exclure))} clips au total, {len(todo)} à générer ({chars} caractères)")
    print(f"≈ {int(chars * rate)} crédits avec le modèle {args.model} (barème indicatif : {rate} crédit/caractère)")
    print("À comparer au solde de ton abonnement ElevenLabs (Settings > Subscription).")


def cmd_generer(args):
    phrases = load_phrases()
    man = load_manifest()
    units = all_units(phrases)
    todo = todo_list(select_units(phrases, args.exclure), args.voice_id, args.model, man, args.force)
    if args.limit:
        todo = todo[:args.limit]
    if not todo:
        print('Rien à générer : tout est à jour.')
    os.makedirs(AUDIO_DIR, exist_ok=True)
    man['voice_id'], man['model'] = args.voice_id, args.model
    for i, p in enumerate(todo, 1):
        name = clip_name(args.voice_id, args.model, p)
        audio = synth(p, args.voice_id, args.model, args.speed, args.stability, args.similarity)
        open(os.path.join(AUDIO_DIR, name), 'wb').write(audio)
        man['clips'][p] = name
        save_manifest(man)  # après chaque clip : on peut interrompre et reprendre
        print(f'[{i}/{len(todo)}] {p}')
    # le manifeste ne garde que les phrases actuelles de l'app
    current = set(units)
    man['clips'] = {t: f for t, f in man['clips'].items() if t in current}
    save_manifest(man)
    used = set(man['clips'].values())
    orphans = [f for f in os.listdir(AUDIO_DIR) if f.endswith('.mp3') and f not in used]
    if args.purge:
        for f in orphans:
            os.remove(os.path.join(AUDIO_DIR, f))
        print(f'{len(orphans)} fichiers inutilisés supprimés.')
    elif orphans:
        print(f'{len(orphans)} fichiers audio ne sont plus utilisés (relancer avec --purge pour les supprimer).')
    missing = len([u for u in units if u not in man['clips']])
    print(f'Terminé. {len(man["clips"])} clips dans audio/ ; {missing} sans clip (voix du navigateur en repli).')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)

    def voice_opts(p):
        p.add_argument('--voice-id', default=os.environ.get('ELEVENLABS_VOICE_ID'), help='identifiant de la voix (ou variable ELEVENLABS_VOICE_ID)')
        p.add_argument('--model', default=DEFAULT_MODEL, help=f'modèle ElevenLabs (défaut {DEFAULT_MODEL} ; eleven_flash_v2_5 coûte moitié moins)')
        p.add_argument('--speed', type=float, default=0.95, help='vitesse 0.7-1.2 (défaut 0.95, un peu posé pour une enfant)')
        p.add_argument('--stability', type=float, default=0.5)
        p.add_argument('--similarity', type=float, default=0.75)

    sub.add_parser('voix', help='liste les voix du compte').set_defaults(fn=cmd_voix)
    sub.add_parser('phrases', help='recense les phrases de l\'app').set_defaults(fn=cmd_phrases)
    p = sub.add_parser('essai', help='génère et joue une phrase test'); voice_opts(p)
    p.add_argument('texte', nargs='?', default="Entoure sept étoiles. Touche la plus grande collection.")
    p.set_defaults(fn=cmd_essai)
    p = sub.add_parser('estimer', help='compte les phrases et crédits, sans appel API'); voice_opts(p)
    p.add_argument('--force', action='store_true')
    p.add_argument('--exclure', help="ignore les clips dont le texte correspond à cette regex (ex. '^Colorie$|en (bleu|rose|vert|jaune|orange|violet)')")
    p.set_defaults(fn=cmd_estimer)
    p = sub.add_parser('generer', help='génère les MP3 manquants'); voice_opts(p)
    p.add_argument('--force', action='store_true', help='regénère tout')
    p.add_argument('--exclure', help="ignore les clips dont le texte correspond à cette regex (génération en plusieurs fois)")
    p.add_argument('--limit', type=int, help='seulement les N premières phrases (test)')
    p.add_argument('--purge', action='store_true', help='supprime les MP3 qui ne servent plus')
    p.set_defaults(fn=cmd_generer)

    args = ap.parse_args()
    if args.cmd in ('essai', 'estimer', 'generer') and not args.voice_id:
        die('--voice-id manquant (voir `python3 tools/generer_voix.py voix`)')
    args.fn(args)


if __name__ == '__main__':
    main()
