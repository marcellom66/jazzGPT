# Verifica locale — 7 ottobre 2026

Ambiente osservato: macOS 26.6, architettura arm64, Python 3.12.13.
Ambiente di progetto `.venv` separato dal Python di sistema.

Versioni installate: JazzGPT 0.1.0 (editable), mido 1.3.3, pytest 9.1.1,
Ruff 0.16.10, build 1.6.1, packaging 26.3.
Dipendenze opzionali torch e python-rtmidi non installate.

Verifiche eseguite:

- `pytest -q`: 24 passed, 1 skipped (modulo dei test PyTorch opzionali).
- `ruff check src tests examples`: nessun errore.
- `ruff format --check src tests examples`: 18 file conformi.
- `python -m pip check`: nessun conflitto di dipendenze.
- `python -m build --wheel`: wheel `jazzgpt-0.1.0-py3-none-any.whl` costruita.
- Wheel installata in un secondo ambiente pulito e CLI eseguita da fuori
  dalla cartella sorgente: generazione e rilettura MIDI riuscite, torch non caricato.
- Script `bootstrap_macos.sh` rieseguito con ambiente esistente: riuscito.
- Cinque file JSON di configurazione VS Code/workspace validi.
- Demo reale: 8 battute, 120 BPM, C, seed 42; 147 note, circa 15.91 secondi,
  canali MIDI 0, 1, 2. Esportazione e rilettura completate.
- Revisione indipendente: corretti e coperti da regressioni l'ordine dei
  pedali su timestamp collassati al millisecondo e il BPM iniziale quando
  il primo cambio di tempo arriva dopo t=0.

Limiti della verifica: nessun ascolto valutativo, rendering audio, checkpoint
Aria/PyTorch, training o hardware MIDI. Le configurazioni VS Code sono state
controllate come file e l'apertura del workspace è stata richiesta tramite CLI;
non è stata verificata l'installazione delle estensioni o una sessione grafica F5.

## Ripresa nella cartella Visual Studio — 7 ottobre 2026

La copia attuale del progetto non conteneva `.venv`. Eseguito
`bash scripts/bootstrap_macos.sh` nella posizione attuale: ricreato l'ambiente
con Python 3.12.13 ARM64 e installato JazzGPT editable con extra dev.

Verifiche ripetute in questa posizione:

- `python -m pytest -q`: 24 passed, 1 skipped (PyTorch opzionale assente).
- `ruff check src tests examples`: nessun errore.
- `ruff format --check src tests examples`: 18 file conformi.
- `python -m pip check`: nessun conflitto.
- Demo rigenerata dallo script bootstrap e riletta con `jazzgpt inspect`:
  147 note, 15.9109375 secondi, BPM iniziale 120, canali 0/1/2.

Build wheel e installazione in secondo ambiente non ripetute in questa ripresa.
Nessuna generazione Aria, prova hardware MIDI o valutazione di ascolto eseguita.
L'adapter Aria resta il punto di integrazione da implementare.

## Prova di fraseggio e variazione modale — 7 ottobre 2026

Modificati director, baseline e humanizer: motivi rappresentati in gradi
diatonici nella memoria di frase; trasformazione, inversione e variazione
del finale; ritmi melodici con note tenute e pause; ritmi di basso e
accompagnamento variabili. Campionamento softmax su candidati del modo,
con target melodico, peso armonico e penalità per ripetizioni immediate.
Microtiming confinato alla battuta per non anticipare il cambio di modo.

- I 7 nuovi casi iniziali fallivano sul baseline precedente: cromatismi
  fuori dal modo, sole due durate melodiche, ritmo di accompagnamento
  invariato e tre altezze identiche consecutive.
- Aggiunti altri 3 casi per verificare il modo con humanize attivo.
- Suite finale completa: 46 passed, 1 skipped (PyTorch opzionale).
  Vincolo modale provato anche a 31 e 300 BPM, oltre a 120 BPM.
- Ruff check: nessun errore; format check: 19 file conformi.
- Pip check: nessun conflitto.
- Generata e riletta demo_modal.mid: 112 note, 15.9286458 secondi,
  120 BPM, canali 0/1/2, 8 battute in Do, swing 0.64, seed 42.
- Il tentativo di rimuovere UF_HIDDEN dal file editable .pth non è rimasto
  efficace: il flag è ricomparso e Python ignorava di nuovo il collegamento.
  Risolto per questa prova costruendo e installando il pacchetto normale con
  `python -m pip install --force-reinstall --no-deps .`. La CLI finale funziona
  senza PYTHONPATH. Dopo future modifiche ai sorgenti occorre reinstallare.
- Revisione indipendente: nessun problema bloccante nel codice musicale;
  corretto nel test il calcolo floating-point dei confini di battuta.

Confronto previsto con demo.mid, stesso tempo/tonalità/suono di pianoforte.
Il nuovo seed produce risultati diversi dal baseline precedente a parità
di valore. Qualità musicale da valutare all'ascolto con Marcello; nessuna
equivalenza con un pianista umano o con Aria dimostrata.

## Dinamiche pianistiche — 8 ottobre 2026

Aggiunta PhraseDynamics come trattamento successivo alla composizione e
al microtiming: modifica solo la velocity. Inviluppo generale del brano,
crescita/rilascio su gruppi di battute, apice variabile delle singole frasi,
accenti su note tenute e salti, accompagnamento più leggero durante la
melodia e più presente nelle pause, nota alta degli accordi in evidenza.
Generatore random separato da quello della composizione.

- Test nuovi prima dell'implementazione fallivano per l'assenza del trattamento.
- Regressione aggiuntiva verificata prima della correzione: gli accordi con
  microtiming ai confini dell'arrotondamento erano divisi in gruppi errati;
  ora gli attacchi sono raggruppati entro 20 ms dal primo attacco.
- Suite finale: 51 passed, 1 skipped (PyTorch opzionale).
- Ruff check riuscito; format check: 20 file conformi; pip check riuscito.
- demo_dynamics.mid: 112 note, 15.9286458 secondi, 120 BPM, canali 0/1/2.
- Confronto MIDI con demo_modal.mid: altezze, canali, attacchi e durate identici.
- Velocity melodia: prima 61..91, ora 46..88 (media 74.9 in entrambi).
  Basso: media da 55.4 a 49.1; accordi: da 44.1 a 35.5. Questi valori
  misurano i comandi MIDI, non il volume audio percepito.

Ripristino ambiente: il vecchio .venv conteneva file con flag dataless;
un campionamento del processo CLI lo trovava bloccato in read su un .pyc
di packaging. Ricreato ambiente in ~/Library/Caches/JazzGPT/venv e installato
JazzGPT editable. .venv ora è un symlink; il precedente è conservato in
.venv-cloud-backup-20261008, senza cancellarne i contenuti. Test e CLI finali
usano il nuovo ambiente. I sorgenti e le configurazioni restano nel progetto.

La resa musicale e il bilanciamento audio vanno confermati da Marcello
ascoltando lo stesso banco di pianoforte utilizzato nel confronto precedente.

## Demo con tre stili — 8 ottobre 2026

Aggiunti profili swing, ballad e latino al generatore. Lo swing conserva
il comportamento precedente. Ballad: note più lunghe, accompagnamento
più rado, dinamica ridotta. Latino: suddivisione dritta, comping sincopato
e basso fondamentale/quinta. BPM costante, ballad con carattere half-time.

Aggiunti generate --style e comando medley con due o tre sezioni. Confini
calcolati dalle battute e dal BPM, indipendenti dalla durata dell'ultima nota.

- Nuovi test verificati fallenti prima dell'implementazione dei profili/CLI.
- Suite finale: 56 passed, 1 skipped (PyTorch opzionale).
- Ruff check riuscito; format check: 21 file conformi.
- demo_styles.mid: 318 note, 47.9427083 s, 120 BPM, canali 0/1/2.
- Swing 0..16 s, ballad 16..32 s, latino 32..48 s; 8 battute per sezione.
- Sezione swing identica alla demo_dynamics.mid per pitch, canale,
  velocity, attacco e durata, alla precisione del roundtrip MIDI.
- Verifica aggiuntiva su 30 configurazioni: modo rispettato e assenza
  di sovrapposizione della stessa altezza sullo stesso canale.
- Durata media note melodiche nella demo: swing 0.411 s, ballad 0.758 s,
  latino 0.270 s. Le differenze misurate non sostituiscono l'ascolto.

Demo di interpretazioni pianistiche semplificate; non è una validazione
musicologica degli stili o una promessa di realismo umano.

## Dialogo del trio — 8 ottobre 2026

Aggiunto ensemble.generate_dialogue e comando CLI dialogue. Due battute
di piano, due di contrabbasso, due di batteria, due insieme; ciclo ripetibile
con numero totale di battute multiplo di 8. Basso e batteria riprendono
il ritmo della chiamata pianistica, con adattamento modale nel basso.
Piano realmente assente durante le risposte. Il rientro aggiunge un ride
e un accompagnamento di batteria leggero.

Writer MIDI: parametro opzionale programs per assegnazione degli strumenti;
default del generatore pianoforte preservato. Trio: canali 0/2 pianoforte,
1 contrabbasso (programma 32), 9 batteria (kit 0), numerazione da zero.
Il modello Performance e i token non conservano questi program change.

- Cinque test nuovi fallenti prima dell'implementazione del trio/CLI/writer.
- Revisione: individuata sovrapposizione tra rullante della risposta e fill.
  Tre regressioni verificate fallenti prima della correzione; il fill ora
  usa quattro tom distinti, evitando rullante/charleston/cassa della risposta.
- Suite finale: 64 passed, 1 skipped (PyTorch opzionale); Ruff check riuscito.
- Sweep aggiuntivo: 45 configurazioni (3 stili, 3 BPM, 5 seed) rispettano
  modo delle voci melodiche, limiti temporali e assenza di overlap stessa
  altezza sullo stesso canale, inclusa batteria.
- demo_dialogue.mid: 185 note, circa 31.98 s, 120 BPM, canali 0/1/2/9.
- Program change verificati nel file: 0:0, 1:32, 2:0, 9:0.
- Turni: 0s piano, 4s basso, 8s batteria, 12s insieme; poi 16/20/24/28s.

Composizione offline, non dialogo generato ascoltando un musicista live.
Suoni General MIDI del banco locale; qualità e intelligibilità dello
scambio da valutare con Marcello all'ascolto.
