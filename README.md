# JazzGPT 🎹

Progetto Python per sviluppare un pianista jazz generativo autoregressivo con
architettura modulare. La versione 0.1 funziona subito, offline, con un baseline
rule-based: nessun modello pesante, account, API key o dataset necessario.

Il baseline sceglie **una nota alla volta in funzione delle precedenti**, degli
accordi e dei motivi ricordati. Non è una rete neurale e non dimostra capacità
musicali indistinguibili da un pianista umano. È una base eseguibile su cui
sviluppare e confrontare modelli appresi.

## Avvio immediato sul Mac di Marcello

L'ambiente `.venv` è già stato creato con **Python 3.12 ARM64** e le dipendenze
base e di sviluppo sono installate. Apri `JazzGPT.code-workspace` in VS Code.

Nel terminale integrato, dalla cartella del progetto:

```bash
source .venv/bin/activate
jazzgpt generate --bars 8 --bpm 120 --key C --seed 42 \
  --output renders/demo.mid --tokens renders/demo.tokens.json
jazzgpt inspect renders/demo.mid
pytest -q
```

Puoi anche eseguire **F5 → “JazzGPT: genera demo MIDI”**, oppure
**⇧⌘B** per il task predefinito di generazione. I task “JazzGPT: test” e
“JazzGPT: lint” sono disponibili da `Terminale → Esegui attività`.
VS Code suggerisce le estensioni Python, Pylance, Python Debugger e Ruff;
la loro presenza nel tuo editor non è richiesta per la CLI.

Se VS Code conserva un interprete selezionato in precedenza, usa
`Python: Select Interpreter` e scegli `.venv/bin/python` di questo progetto.

**Ascolto:** `renders/demo.mid` è un file di note e comandi, non un file audio.
Importalo in GarageBand o in una DAW e assegna un suono di pianoforte.
Il progetto non contiene un sintetizzatore, un SoundFont o un rendering WAV.

## Installazione pulita o dopo aver spostato la cartella

Un ambiente virtuale contiene percorsi locali: **non copiarlo su un altro Mac e
non riutilizzarlo dopo aver spostato il progetto**. Ricrea `.venv` nella nuova
posizione; lo ZIP distribuito contiene solo sorgenti e demo, non l'ambiente.

Su macOS con Python 3.11+ già disponibile:

```bash
bash scripts/bootstrap_macos.sh
```

Lo script preferisce Python 3.12/3.11 Homebrew, crea `.venv` se assente,
installa il progetto con i tool di sviluppo e genera la demo. Per indicare
un interprete specifico:

```bash
JAZZGPT_PYTHON=/percorso/python3.12 bash scripts/bootstrap_macos.sh
```

In alternativa, su macOS/Linux/Windows con Python 3.11+:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m jazzgpt generate
```

Su Windows il comando di attivazione PowerShell è
`.venv\Scripts\Activate.ps1`; le configurazioni VS Code e lo script bootstrap
inclusi sono predisposti per macOS e vanno adattati per Windows.
Per la sola demo basta `python -m pip install -r requirements.txt`.

## Cosa genera

- Cadenza **ii–V–I–VI7**, un accordo per battuta, in 4/4.
- Melodia nella zona centrale/acuta del piano, con motivi trasformati per gradi
  della scala, direzione melodica, note tenute e pause. Le scelte probabilistiche
  seguono un target di frase, l'armonia e la storia recente.
- Basso con ritmi variabili e avvicinamento all'accordo successivo;
  voicing rootless con terza, settima e nona, registri e ingressi variabili.
- Tre canali MIDI: `0` melodia, `1` basso, `2` accordi. Tutti usano
  General MIDI Acoustic Grand Piano; non sono tre strumenti diversi.
- Ottavi swing alternati a durate più lunghe, variazioni di velocity e
  microtiming confinato alla battuta. Il baseline usa dorico, misolidio e ionico
  secondo l'accordo, senza cromatismi fuori dal modo. Lo stesso seed riproduce
  la stessa performance nel medesimo ambiente e con la stessa versione del codice.

L'8 ottobre l'ambiente è stato ricreato fuori dalla cartella sincronizzata:
`.venv` è un collegamento a `~/Library/Caches/JazzGPT/venv`, con installazione
editable. Il vecchio ambiente è conservato in `.venv-cloud-backup-20261008`.
Alcune dipendenze del vecchio ambiente risultavano `dataless` e bloccavano
Python in attesa della lettura dei file. Terminale e task continuano a usare
`.venv/bin/python`; non è necessario reinstallare dopo ogni modifica ai sorgenti.
Se la cache viene rimossa, l'ambiente deve essere ricreato.

La prova di variazione modale è in `renders/demo_modal.mid`: 8 battute in Do,
120 BPM, swing 0.64, seed 42. È un esperimento con regole esplicite: la maggiore
varietà misurata non dimostra che il risultato suoni come un pianista umano.
Il MIDI precedente `renders/demo.mid` resta disponibile per il confronto.

La demo `renders/demo_dynamics.mid` conserva le stesse note e gli stessi tempi
di `demo_modal.mid`, con un nuovo trattamento delle velocity: crescendo e
diminuendo tra le frasi, accenti melodici e bilanciamento di basso e accordi
in funzione della presenza della melodia. Gli accordi hanno un tocco diverso
tra note inferiori e superiori. Il trattamento agisce sull'intensità degli
attacchi; non crea un crescendo continuo su una nota già tenuta. La resa
di volume e timbro dipende dal pianoforte/sampler utilizzato.

Esempi:

```bash
jazzgpt generate --bars 16 --bpm 105 --key F --seed 123 --output renders/jazz_f.mid
jazzgpt generate --bars 8 --key Bb --swing 0.67 --output renders/jazz_bb.mid
jazzgpt generate --no-humanize --swing 0.5 --output renders/straight.mid
jazzgpt tokenize renders/demo.mid --output renders/imported.tokens.json
jazzgpt doctor
python examples/generate_demo.py
```

Tre stili nella stessa demo (8 battute ciascuno, circa 48 secondi):

```bash
jazzgpt medley --bars-per-style 8 --bpm 120 --key C --seed 42 \
  --output renders/demo_styles.mid --tokens renders/demo_styles.tokens.json
```

Ordine predefinito: `swing`, `ballad`, `latin`. Con 120 BPM e 8 battute per
stile, le sezioni iniziano a 0, 16 e 32 secondi. Il BPM resta costante: la
ballad ha un carattere half-time con note lunghe, accompagnamento più rado
e dinamica più delicata; il profilo latino usa ottavi dritti, sincopi e basso
tra fondamentale e quinta. Sono interpretazioni pianistiche semplificate,
non riproduzioni complete dei linguaggi o di una sezione ritmica.

Per due stili o uno stile singolo:

```bash
jazzgpt medley --styles ballad latin --bars-per-style 8 --output renders/two_styles.mid
jazzgpt generate --style ballad --bars 16 --output renders/ballad.mid
jazzgpt generate --style latin --bars 16 --output renders/latin.mid
```

`--swing` modifica la suddivisione soltanto nello stile swing: ballad e latino
usano suddivisioni dritte. Fraseggio modale e dinamiche restano attivi in tutti
i profili. Il nuovo parametro `GenerationConfig.style` ha default `"swing"`.

Dialogo tra tre strumenti MIDI distinti:

```bash
jazzgpt dialogue --bars 16 --bpm 120 --key C --seed 42 \
  --output renders/demo_dialogue.mid --tokens renders/demo_dialogue.tokens.json
```

Turni di due battute: piano, risposta del contrabbasso, risposta della batteria,
rientro insieme. A 120 BPM ogni turno dura 4 secondi; il ciclo dura 16 secondi
e nella demo viene ripetuto con un nuovo motivo. Nelle risposte di basso e
batteria il piano tace. Le risposte riprendono il ritmo della chiamata, e il
basso ne adatta il profilo alla scala dell'accordo corrente. La batteria chiude
la risposta con un fill e accompagna il rientro con un ride leggero.

`--bars` deve essere un multiplo di 8; `--style` accetta gli stessi profili.
Piano sui canali 0/2, contrabbasso sul canale 1 (programma GM 32, numerazione
da zero), batteria sul canale 9 (canale 10 nella numerazione usuale).
È un arrangiamento offline, non un ascolto o una risposta live a un musicista.
I comandi generate/medley conservano il loro suono di pianoforte solo.

L'assegnazione dei suoni è scritta nel MIDI tramite `write_midi(..., programs=...)`.
Il formato Performance e il JSON di token non conservano i program change:
se si importa e riesporta il brano con queste API, occorre passare di nuovo
`TRIO_PROGRAMS` al writer per mantenere i suoni del trio.

Parametri: `--bars` 1..10000, `--bpm` 30..300, `--key` nomi MIDI inglesi
(C=Do, D=Re, E=Mi, F=Fa, G=Sol, A=La, B=Si; bemolle `b`, diesis `#`),
`--swing` 0.5..0.75, `--seed` intero. Quote una tonalità con diesis se
necessario, per esempio `--key 'F#'`. `--no-humanize` disattiva microtiming
e variazioni di velocity; lo swing rimane quello impostato.

## Struttura

```text
JazzGPT/
├── JazzGPT.code-workspace
├── pyproject.toml
├── requirements*.txt
├── .vscode/                 # interprete, debug, task, estensioni
├── scripts/bootstrap_macos.sh
├── src/jazzgpt/
│   ├── events.py            # Note, Pedal, Performance in secondi
│   ├── midi_io.py           # lettura/scrittura e porte opzionali
│   ├── tokenizer.py         # eventi → ID token → eventi
│   ├── harmony.py           # accordi, scale, voicing, trasposizione
│   ├── memory.py            # memoria limitata di frasi/intervalli
│   ├── director.py          # forma, densità, tensione e orchestrazione
│   ├── performer.py         # microtiming e dinamica
│   ├── cli.py               # comandi di test e diagnostica
│   └── models/
│       ├── base.py          # contratti NoteModel/ContinuationBackend
│       ├── baseline.py      # generatore rule-based autoregressivo
│       ├── torch_adapter.py # campionamento da logits, MPS/CPU
│       └── aria.py          # punto di integrazione MIDI per Aria
├── tests/                   # contratti funzionali e test torch opzionali
├── examples/                # uso dell'API Python
├── docs/                    # architettura, sviluppo, integrazione modelli
├── data/raw/                # dataset originali, ignorati da Git
├── data/processed/          # dataset tokenizzati, ignorati da Git
├── checkpoints/             # futuri pesi, ignorati da Git
└── renders/                 # MIDI e token generati, ignorati da Git
```

`data/` e `checkpoints/` sono pronti per lo sviluppo, ma sono vuoti.
Il progetto non scarica dati o pesi e non include un trainer.

## API e sostituzione del baseline

```python
from jazzgpt.director import GenerationConfig, generate
from jazzgpt.midi_io import write_midi

performance = generate(GenerationConfig(bars=16, bpm=110, key="Eb", seed=7))
write_midi(performance, "renders/my_jazz.mid")
```

Un modello a livello di note implementa
`next_pitch(context: NoteContext, rng: random.Random) -> int`.
Passalo a `generate(config, model=my_model)`. Il context contiene accordo,
ultime 32 note, accento metrico, tensione e un eventuale target melodico.
Il director gestisce ritmi e accompagnamento: questo contratto serve a
sperimentare sulla melodia, non a sostituire una performance completa con Aria.

`ContinuationBackend.continue_midi(prompt, max_new_tokens)` è invece il
contratto per modelli che producono intere performance. Vedi
[MODEL_INTEGRATION.md](docs/MODEL_INTEGRATION.md).

## Tokenizer e conservazione del timing

Il vocabolario `jazzgpt-events-v1` contiene **1529 token**:
`BOS`, `EOS`, `CHANNEL_0..15`, `VELOCITY_1..127`, `NOTE_ON_0..127`,
`NOTE_OFF_0..127`, `PEDAL_0..127`, `TIME_SHIFT_1..1000` in millisecondi.
Le pause oltre un secondo sono suddivise in più TIME_SHIFT. I token di canale
e velocity impostano lo stato per gli eventi successivi. A parità di tempo,
gli off precedono gli on.

Il formato JSON conserva BPM iniziale, titolo e ID dei token. Risoluzione:
**1 ms**, dunque il timing viene arrotondato, non mantenuto senza perdita.
Le durate submillisecondo diventano almeno 1 ms. La lettura MIDI applica
i cambi di tempo alle posizioni assolute in secondi; l'esportazione usa il
BPM della Performance e non ricostruisce la mappa di tempo originale.
Program change, pitch bend, aftertouch e controlli diversi dal sustain non
sono rappresentati. Su note sovrapposte della stessa altezza e canale,
gli off vengono associati agli on in ordine FIFO: il MIDI non distingue
le identità di queste note. Il generatore evita tale sovrapposizione.

Il sustain si può importare, tokenizzare ed esportare. Il baseline iniziale
non compone un uso espressivo del pedale; il writer rilascia a fine file
un sustain eventualmente rimasto premuto.

## Apple Silicon e modelli opzionali

La demo usa la CPU e una sola dipendenza, `mido`. Per sviluppare PyTorch:

```bash
python -m pip install -r requirements-macos-ml.txt
jazzgpt doctor
pytest tests/test_optional_torch.py -q
```

`select_device("auto")` usa MPS quando `torch.backends.mps.is_available()`
lo consente, altrimenti CPU; `"cpu"` forza la CPU e `"mps"` richiede MPS.
Non scarica pesi. Il backend PyTorch non è necessario per la demo.
Le indicazioni del backend sono nella
[documentazione ufficiale PyTorch MPS](https://docs.pytorch.org/docs/stable/notes/mps.html).

Aria dispone di implementazioni ufficiali PyTorch/CUDA e MLX/Apple Silicon.
Per il Mac conviene valutare il percorso MLX ufficiale durante l'integrazione;
il bridge qui incluso non presume che il backend CUDA funzioni su MPS.
Vedi il [repository ufficiale Aria](https://github.com/EleutherAI/aria).

## MIDI live opzionale

```bash
python -m pip install -e '.[live]'
jazzgpt ports
jazzgpt play renders/demo.mid --port 'Nome esatto della porta di uscita'
```

Su macOS il backend python-rtmidi usa CoreMIDI. Una porta deve essere collegata
a uno strumento o sintetizzatore. Il playback usa scadenze monotone e in uscita
invia rilascio sustain e all-notes-off. Le porte fisiche non sono state validate
su hardware durante la preparazione. L'ingresso MIDI si può enumerare; la
registrazione live e la risposta generativa a un pianista non sono implementate.
Il playback di un file precalcolato non è improvvisazione neurale in tempo reale.

## Verifica e sviluppo

```bash
pytest -q
ruff check src tests examples
ruff format --check src tests examples
python -m build --wheel
```

I test verificano polifonia/canali/pedale, token ID e pause lunghe, input
invalidi, trasposizione, memoria limitata, seed, durata, note-off completi,
tempo MIDI e CLI senza torch. I test torch sono saltati quando l'extra manca.
Questi test provano il comportamento software; non valutano la qualità del jazz.

Le dipendenze supportate sono in `pyproject.toml`; la fotografia delle versioni
effettivamente verificate è in `docs/VERIFICATION.md`.

Il percorso di sviluppo successivo è in [DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md):
prima continuazione Aria di un nostro MIDI, poi dataset/licenze e valutazioni,
quindi training e generazione incrementale con misure reali di latenza.
