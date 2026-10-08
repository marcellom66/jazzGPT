# Collegare un modello a JazzGPT

## Tre contratti, tre livelli

1. **NoteModel**: `next_pitch(NoteContext, Random) -> int`. È il punto usato
   dalla demo: ritmo e accompagnamento restano responsabilità del director.
2. **TorchTokenModel**: riceve un modello già costruito e un forward che
   restituisce logits `[1, T, V]` (oppure un oggetto con `.logits`). Genera
   token in sequenza, con limite al contesto, temperatura, seed ed EOS.
   Serve ancora un decoder/validatore musicale per usarlo nel director.
3. **ContinuationBackend**: `continue_midi(Performance, max_new_tokens) -> Performance`.
   È il contratto utilizzato da AriaAdapter per continuare una performance.

Questi contratti non sono intercambiabili automaticamente. In particolare,
un Transformer su token eventi non restituisce necessariamente un singolo pitch.

## PyTorch: esempio minimo

Installare l'extra `torch` e usare un modello locale già inizializzato:

```python
from jazzgpt.models.torch_adapter import TorchTokenModel
from jazzgpt.tokenizer import EventTokenizer

tokenizer = EventTokenizer()
# model deve avere vocabolario tokenizer.vocab_size e forward [1, T, V].
sampler = TorchTokenModel(model, device="auto", context_length=1024)
tokens = sampler.generate_tokens(
    [tokenizer.token_id("BOS")], max_new_tokens=256,
    eos_id=tokenizer.token_id("EOS"), seed=42,
)
```

`model` qui è un parametro da fornire, non un modello implementato nel progetto.
Il sampler non carica checkpoint e non addestra nulla. L'output di una rete
non addestrata può essere musicalmente o sintatticamente invalido: il decoder
rifiuta NOTE_OFF orfani, note pendenti, tempi nulli e sequenze senza BOS/EOS.
Per un'integrazione reale servono masking degli eventi validi e politiche di
chiusura delle note alla fine del budget; qui non si inventa una validazione
che renderebbe arbitrariamente “buono” qualsiasi modello.

MPS è opzionale, selezionato in base alla disponibilità effettiva. Non c'è KV
cache: ogni step ricalcola la finestra di contesto. È un adapter di sviluppo,
non una promessa di throughput o latenza live. Il campionamento avviene su CPU
con un generatore locale per non alterare il seed globale del progetto.

## Aria: placeholder esplicito e percorso reale

Fonte verificata il 7 ottobre 2026:
[EleutherAI/aria](https://github.com/EleutherAI/aria).
Il repository ufficiale richiede Python 3.11+ e fornisce generazione con
PyTorch/CUDA e MLX/Apple Silicon. Aria lavora bene nella continuazione di prompt
pianistici; il suo tokenizer e la sua configurazione devono corrispondere ai pesi.

**Non dare i token JazzGPT a un checkpoint Aria**. Il vocabolario interno v1 è
un nostro formato di laboratorio, non il vocabolario ufficiale Aria.

Procedura consigliata, da realizzare nella fase successiva:

1. Generare un MIDI originale con il baseline come prompt.
2. Preparare Aria in un ambiente separato seguendo il README ufficiale e
   scegliere un checkpoint di continuazione con la relativa licenza.
3. Provare la CLI ufficiale su quel MIDI con il backend MLX del Mac.
4. Implementare un backend che serializzi il prompt con `write_midi`, richiami
   la generazione ufficiale e importi il risultato con `read_midi`.
5. Passare quel backend ad `AriaAdapter(backend)`; validare lunghezza,
   note-off, timing, consumo di memoria e tempo di generazione.

Uso del bridge una volta fornito il backend:

```python
from jazzgpt.models.aria import AriaAdapter

# backend implementa continue_midi(prompt, max_new_tokens).
continuation = AriaAdapter(backend).generate(prompt, max_new_tokens=512)
```

Senza backend `AriaAdapter.generate` solleva NotImplementedError descrittivo.
Nessun tentativo di fingere una generazione neurale dietro il baseline.
La CLI v0.1 espone solo il generatore baseline, non un falso `--model aria`.

## Cosa serve per il training futuro

Dataset con provenienza/licenze; preprocessing dei tempi e degli strumenti;
split per registrazione e artista per ridurre leakage; tokenizer versionato;
batch con padding e causal mask; checkpoint riproducibili; metriche musicali
e ascolti controllati. I ruoli del director e della memoria andranno valutati:
un modello di performance completo non riceve automaticamente i controlli
armonici del nostro baseline. Questo progetto prepara i confini dei moduli,
non una pipeline di training già pronta.
