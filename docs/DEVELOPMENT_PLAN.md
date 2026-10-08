# Piano di sviluppo JazzGPT

Specifica: ARCHITECTURE.md. Esecuzione locale nella sessione corrente.

1. Scrivere contratti automatici per polifonia/canali, timing, seed,
   trasposizione, memoria limitata, tempo MIDI e CLI; verificarne il fallimento
   prima dell'implementazione.
2. Implementare eventi, tokenizer e MIDI I/O. Verificare roundtrip, cambi di tempo,
   durata positiva, note-off completi e rifiuto delle sequenze incomplete.
3. Implementare harmony, memoria, baseline, director e performer.
   Verificare seed riproducibile, tre voci e limiti della performance.
4. Esporre CLI e adapter opzionali. Verificare demo senza importare torch,
   messaggio esplicito del placeholder Aria e diagnostica del backend.
5. Preparare ambiente Python ARM64, VS Code, esempi e istruzioni.
   Eseguire pytest, lint, build wheel e CLI reale; rileggere il MIDI generato.

Sviluppi successivi separati: backend Aria/MLX reale con MIDI prompt; dataset
con licenze documentate; preparazione token e split per brano/artista;
piccolo Transformer e training; valutazioni musicali e ascolti; scheduler
incrementale live con buffer, gestione latenza e ingresso MIDI.
