# JazzGPT: specifica iniziale

Obiettivo: laboratorio Python modulare che generi subito una breve performance
pianistica MIDI e consenta di sostituire il generatore con un modello appreso.
Python 3.11+, ambiente locale Python 3.12 ARM64; solo mido è obbligatorio.
Nessun peso, dataset o backend audio scaricato automaticamente.

Flusso: GenerationConfig → Director → HarmonyEngine + PhraseMemory →
NoteModel.next_pitch(context, rng) → note in secondi → Humanizer →
Performance → MIDI / EventTokenizer. Il baseline è autoregressivo a livello di
note: ogni scelta usa il contesto delle precedenti. Non è una rete addestrata.

- events.py: Note, Pedal, Performance validati, tempo in secondi.
- harmony.py: cadenza ii–V–I–VI dominante in 12 tonalità.
- memory.py: memoria limitata di intervalli per richiamo/trasposizione dei motivi.
- director.py: forma, tensione, densità, frasi e accompagnamento in 4/4.
- performer.py: swing sugli ottavi nel director, microtiming e dinamica nel performer.
- models/base.py e baseline.py: contratto e scelta condizionata della prossima nota.
- models/torch_adapter.py: campionatore autoregressivo per modelli di logits PyTorch.
- models/aria.py: contratto di continuazione MIDI per un backend Aria futuro.
- tokenizer.py: vocabolario eventi v1, risoluzione 1 ms, canali e sustain.
- midi_io.py: lettura con cambi di tempo, scrittura e playback opzionale CoreMIDI.
- cli.py: generate, inspect, tokenize, doctor, ports, play.

Tokenizer interno distinto da Aria: nessuna compatibilità binaria dei token.
Aria va integrato con checkpoint, configurazione e tokenizer ufficiali tramite
un backend di continuazione MIDI. PyTorch opzionale; selezione auto MPS/CPU.
La prima versione genera offline; playback di file non equivale a improvvisazione
interattiva in tempo reale. Nessun trainer e nessuna valutazione d'ascolto umano.

Accettazione: demo deterministica per seed; melodia, bassi e accordi;
tempi/velocity MIDI validi; roundtrip di eventi e MIDI; errori chiari per input
invalidi; ambiente, debug, test e task VS Code pronti.
