# Ferie in Odoo 18 — Formule, Problema, Strategie

Documento di sintesi per decidere come gestire le ferie dei part-time. Niente codice, solo matematica e scelte.

---

## 1. Le formule che Odoo applica (alto livello)

Odoo ragiona su 3 numeri per dipendente:

- **Allocazione** = monte ferie assegnato (in giorni *o* in ore, a seconda del tipo)
- **Consumo** = quanto viene sottratto a ogni richiesta di ferie
- **Residuo** = allocazione − consumo

Le formule cambiano in base a una sola scelta di configurazione: il **tipo di ferie** può essere impostato in **giorni** o in **ore**.

### Modalità "giorni" (oggi in produzione)

```
Allocazione         = N giorni                       (es. 25 per full-time)
Consumo richiesta   = numero di giorni di calendario coperti, arrotondato per eccesso
Ore detratte (info) = somma delle ore reali da calendario in quei giorni
```

> ⚠️ L'arrotondamento "per eccesso" è il punto critico:
> ogni giorno del calendario coperto dalla richiesta vale **1**, indipendentemente da quante ore il dipendente lavora quel giorno.

### Modalità "ore"

```
Allocazione         = N ore                          (es. 200h per full-time)
Consumo richiesta   = somma delle ore reali da calendario nelle date richieste
Giorni mostrati     = ore_consumate / hours_per_day  (vedi sotto)
```

### Cos'è `hours_per_day`

Per ogni dipendente Odoo calcola la **media** delle ore lavorate sui suoi giorni lavorativi:

```
hours_per_day = ore_totali_settimana / numero_di_giorni_lavorativi
```

| Dipendente | Orario settimanale | hours_per_day |
|---|---|---|
| Full-time | Lun–Ven 8h | 40/5 = **8.0** |
| Klaudia (90%) | Lun–Gio 8h + Ven 4h | 36/5 = **7.2** |
| 80% (Ven libero) | Lun–Gio 8h | 32/4 = **8.0** |
| 50% mezza giornata | Lun–Ven 4h | 20/5 = **4.0** |

E nelle allocazioni in modalità "ore", Odoo accoppia *sempre*:

```
ore_allocate  =  giorni_allocati  ×  hours_per_day
```

---

## 2. Il problema concreto (esempio Klaudia)

Klaudia ha contratto 90%, calendario Lun–Gio 8h + Ven 4h.
Le tocca proporzionalmente il 90% di 25 giorni = **22.5 giorni** di ferie/anno.

### Cosa succede oggi (modalità "giorni")

Klaudia chiede **venerdì libero**:
```
giorni di calendario coperti = 1   (il venerdì è 1 giorno nel suo calendario)
ceil(1)                      = 1
→ -1 giorno dal monte ferie
```

Ma quel venerdì lei lavorava solo 4h. Risultato: **paga 1 giorno intero per 4h di ferie**. Sbagliato.

Klaudia chiede **lunedì libero** (8h):
```
giorni di calendario coperti = 1
→ -1 giorno dal monte ferie
```

Stesso costo del venerdì. Ma il lunedì sono 8h vere, il venerdì solo 4h. Incoerente.

### Cosa succederebbe in modalità "ore"

Allocazione: 22.5 giorni × hours_per_day(7.2) = **162h** ❗ (non 180h)

Klaudia chiede venerdì:
```
ore detratte = 4   → -4h dal monte
```

Klaudia chiede lunedì:
```
ore detratte = 8   → -8h dal monte
```

Ora i costi sono proporzionali alle ore reali. ✓

Ma c'è un'asimmetria: la sua allocazione naturale viene fuori 162h, **non 180h** che è il vero 90% di 200h. Per arrivare a 180h serve impostare manualmente "180h" sull'allocazione (e Odoo internamente la traduce in 25 giorni).

---

## 3. Tabella riassuntiva per i 5 profili aziendali

| Profilo | Orario reale | hours_per_day | Allocazione "giorni" (proporzionale) | Allocazione "ore" naturale (gg×hpd) | Allocazione "ore" desiderata (200×%) |
|---|---|---|---|---|---|
| 100% | Lun–Ven 8h | 8.0 | 25 gg | 200h | 200h ✓ |
| 90% (Klaudia) | Lun–Gio 8h + Ven 4h | 7.2 | 22.5 gg | 162h ❌ | 180h |
| 80% Ven libero | Lun–Gio 8h | 8.0 | 20 gg | 160h | 160h ✓ |
| 50% mezza giornata | Lun–Ven 4h | 4.0 | 12.5 gg | 50h ❌ | 100h |
| 45% (da definire) | dipende | dipende | 11.25 gg | dipende | 90h |

**La colonna che conta è l'ultima.** Ogni dipendente, indipendentemente da come lavora, deve ricevere `200h × percentuale_contratto` di monte ferie. Le altre due colonne ("giorni" e "ore naturale") mostrano cosa Odoo farebbe da solo se non lo forziamo.

---

## 4. Strategie possibili — pro, contro, costo

### Strategia A — Tutto resta com'è (modalità "giorni")

- **Cosa:** nessuna modifica
- **Pro:** zero lavoro
- **Contro:** Klaudia (e qualunque part-time con orari sbilanciati) continua a pagare 1 giorno intero per ogni giorno di ferie, anche per i venerdì da 4h
- **Verdetto:** non risolve il problema

### Strategia B — Modalità "ore" + display in giorni con regola "1 giorno = 8h" (modulo `custom_hr_holidays_hours8`)

- **Cosa:**
  1. Cambiare i tipi di ferie da "giorni" a "ore"
  2. Riemettere le allocazioni in ore (200h × percentuale)
  3. Verificare/correggere i `resource.calendar` per riflettere le ore reali per giorno
  4. Usare il modulo custom per mostrare ovunque "ore ÷ 8" come "giorni" all'utente
- **Pro:**
  - Klaudia paga 4h per il venerdì e 8h per il lunedì (corretto)
  - Allocazioni proporzionali e coerenti (180h per Klaudia)
  - L'utente vede sempre "giorni" come prima
- **Contro:**
ro  - Per Klaudia "giorni residui" dipende dall'unità mentale: vede "22.5 giorni" (180/8) ma "consuma" 0.5 per il venerdì e 1 per il lunedì. Math: se prendesse tutti i venerdì dell'anno (≈45) consumerebbe 45 × 0.5 = 22.5 giorni e finirebbe il monte. Coerente.
  - Lavoro di setup HR non banale: ogni part-time deve avere un calendario fedele giorno-per-giorno
  - Se i calendari non sono splittati morning/afternoon, il pulsante "mezza giornata" non funziona
- **Verdetto:** **soluzione consigliata**, è quella che il modulo è già pronto a supportare

### Strategia C — Modalità "ore" + display in giorni con regola "1 giorno = ore reali del dipendente"

- **Cosa:** come la B, ma il display divide per `hours_per_day` del singolo dipendente invece che per 8
- **Pro:**
  - Klaudia vede "25 giorni disponibili" (180/7.2) — corrisponde al numero "naturale" del suo contratto
- **Contro:**
  - Per Klaudia un venerdì libero (4h) appare come **0.56 giorni** (4/7.2), un lunedì come **1.11 giorni** (8/7.2). Numeri innaturali da leggere.
  - Per i full-time tutto resta come prima (8/8 = 1)
  - Per i part-time "puliti" tipo l'80% senza il venerdì: 8/8 = 1, anche qui ok
  - Solo i part-time *sbilanciati* (giornate di durata diversa) vedono i decimali strani
- **Verdetto:** matematicamente più "preciso" ma esteticamente peggio per i casi sbilanciati

### Strategia D — Modalità "ore" e basta, mostrare ore ovunque

- **Cosa:** cambiare tipi di ferie a "ore", riemettere allocazioni in ore, **non** mostrare giorni
- **Pro:**
  - Comportamento corretto, zero ambiguità, zero modulo custom
  - L'utente vede "180h disponibili", "consumati 4h" — è tutto chiaro
- **Contro:**
  - Cambio culturale: dipendenti e HR devono pensare in ore, non in giorni
  - Probabilmente non passa con il management/dipendenti abituati a "ho 25 giorni di ferie"
- **Verdetto:** tecnicamente la più pulita, politicamente difficile

---

## 5. Raccomandazione

**Strategia B**, perché:
1. Risolve il problema di Klaudia in modo proporzionale ed equo
2. Mantiene il vocabolario "giorni" che l'azienda usa già
3. Il modulo è già scritto e installato (manca solo attivare il switch sui tipi di ferie)
4. La regola "1 giorno = 8h" è la più intuitiva da spiegare a tutti

### Cosa serve per implementarla

| Step | Chi | Tempo stimato |
|---|---|---|
| Audit dei `resource.calendar` di tutti i part-time | IT + HR | 1–2 giorni |
| Definire orari reali (giorno/fascia) per ogni dipendente sbilanciato | HR | 1 settimana (da concordare con dipendenti) |
| Aggiornare i calendari in Odoo (split morning/afternoon dove serve) | IT | 1 giorno |
| Cambiare `request_unit` sui tipi di ferie principali (Ferie, Permessi) | IT | 1 ora |
| Riemettere/aggiornare le allocazioni in ore (200h × percentuale) | IT | 1/2 giorno (script) |
| Test in staging con un finto Klaudia | IT | 1/2 giorno |
| Comunicazione ai dipendenti del cambio | HR | 1 giorno |
| Cutover in produzione | IT | 1 ora |

**Totale: ~2 settimane di calendario, di cui la maggior parte è lavoro HR per mappare gli orari reali.**

### Punto di attenzione

Le allocazioni storiche (anni precedenti) e le ferie già richieste **non vengono toccate retroattivamente**. La nuova logica si applica solo a:
- Nuove allocazioni emesse dopo il cutover
- Nuove richieste di ferie

Quindi il cutover ideale è **a inizio anno fiscale** (1 gennaio) per evitare conversioni miste a metà anno.

---

## 6. Domande aperte da decidere col management

1. **Cutover quando?** A inizio 2027 o pro-rata adesso?
2. **Profili 50% e 45%:** com'è organizzato il loro orario reale? (necessario sapere per definire i calendari)
3. **Half-day:** vogliamo abilitare la mezza giornata come opzione esplicita nel form di richiesta? Se sì, tutti i calendari devono essere splittati AM/PM.
4. **Storico:** tocchiamo le ferie già consumate o lasciamo storia immutata?
5. **Comunicazione:** chi spiega il cambio ai dipendenti e con quale messaggio?

---

## 7. Stato attuale in produzione (audit Aprile 2026)

Dopo l'audit del DB di produzione, il punto di partenza è meno catastrofico del previsto. Diverse cose sono **già in atto**:

### Cosa è già a posto

- ✅ Tipo di ferie **`Vacation - Employee`** già configurato in `request_unit = hour`
- ✅ Modulo custom **`custom_hr_holidays_hours8`** già deployato (versione `18.0.1.0.0`, regola `÷8 fissa`)
- ✅ Allocazioni della maggior parte dei dipendenti già impostate in ore (con valori a volte sbagliati)

### Cosa è ancora da sistemare

- ❌ Allocazioni con valori incoerenti (Klaudia ha 162h *e* 180h attive sullo stesso tipo)
- ❌ **Half-day non funzionante** (tutti i calendari hanno solo lo slot `morning`, manca lo split AM/PM)
- ❌ Calendari "horizontal" che generano frazioni innaturali col modulo `÷8` (Patricia, Eugenia, Monique)
- ❌ Calendari template inutilizzati che andrebbero archiviati
- ❌ Altri tipi di ferie (Public Holidays, Paternity, Birth, Civil Protection, Unpaid leave, ecc.) ancora in `day` mode

### Allocazioni rilevate problematiche

| Dipendente | Allocazione attuale | Dovrebbe essere | Note |
|---|---|---|---|
| Klaudia (90%) | 22.5 days = **162h** + 25 days = **180h** | 180h totali | Doppia allocazione attiva, somma 342h |
| Roya (90%) | 22.5 days = **162h** + 23.5 days = **169.2h** | 180h | Doppia, valori entrambi sbagliati |
| Konstantin (45%) | 11.5 days = **103.5h** + 4 days = **36h** | 90h | Incoerente |
| Monique NL (20%) | 12.5 days = **20h** | 40h | Calendario sballato a 1.6h/day |
| Eugenia (100% NL/BE) | 25 days = **190h** | 200h | Calendario 38h/week |

---

## 8. Dettaglio calendari sbilanciati

Sono stati trovati **21 calendari** con `hours_per_day ≠ 8.0`. Di questi, 9 sono assegnati a dipendenti reali, 12 sono template inutilizzati.

### Calendari assegnati (vanno gestiti)

| Calendar | hpd | Distribuzione | Assegnato a | Categoria |
|---|---|---|---|---|
| 90% with half Friday (CH) | 7.2 | Lun-Gio 8h + Ven 4h | Klaudia dos Santos | **Balanced ✓** |
| 90% (NL Wed halfday) | 7.2 | Lun-Mar 8h + Mer 4h + Gio-Ven 8h | Roya Shokoohi | **Balanced ✓** |
| 50% (Mon - Wed morning) | 6.67 | Lun-Mar 8h + Mer 4h | Gabriele Cerfoglio | **Balanced ✓** |
| 50% (Tue, Wed morning - Fri) 2026 | 6.67 | Mar 8h + Mer 4h + Ven 8h | Andrea Falconi | **Balanced ✓** |
| 50% (Mon, Wed afternoon - Thu) | 6.67 | Lun 8h + Mer 4h + Gio 8h | Andrea Falconi D4P | **Balanced ✓** |
| 50% (Wed afternoon - Friday) | 6.67 | Mer 4h + Gio-Ven 8h | Gabriele Cerfoglio D4P | **Balanced ✓** |
| 80% horizontal (CH from 2023) | 6.4 | Lun-Ven 6.4h ogni giorno | Patricia Geraldes | **Horizontal ⚠️** |
| 100% (NL/BE 100% 38h) | 7.6 | Lun-Ven 7.6h ogni giorno | Eugenia Kypriotis | **Horizontal ⚠️** |
| 20% (NL from 2023) | 1.6 | Lun-Ven 1.6h ogni giorno | Monique Calisti NL | **Anomalo ❌** |
| 45% (D4P from 2025) | 9.0 | Lun-Mar 9h | Konstantin Skaburskas | **Anomalo ❌** |

### Problema globale: tutto in `morning`

In **TUTTI** i 21 calendari, le fasce sono marcate come `day_period = morning`, anche quando coprono l'intera giornata (es. `09:00–17:00 morning`). Conseguenza:

- ❌ Half-day **morning** → consuma l'intero slot (8h, non 4h)
- ❌ Half-day **afternoon** → consuma 0h (slot vuoto)

Questo va sistemato per *tutti* i calendari, non solo quelli sbilanciati.

### Come funziona davvero half-day in Odoo (finding aprile 2026)

Odoo **non** divide aritmeticamente la giornata: la half-day è **strutturale**, basata sul campo `day_period` degli `resource.calendar.attendance`. La formula effettiva è:

```
ore_consumate(half-day morning)   = somma(attendance.hours WHERE day_period == 'morning'   AND data nel range)
ore_consumate(half-day afternoon) = somma(attendance.hours WHERE day_period == 'afternoon' AND data nel range)
```

Non c'è nessun `total_giorno / 2`. Odoo prende letteralmente tutti gli slot etichettati come quel periodo e li somma.

**Implicazione pratica per orari corti senza pausa pranzo:**

| Calendario Friday | Half-day morning | Half-day afternoon |
|---|---|---|
| Slot unico `09:00–13:00 morning` | **4h** ❌ (l'intero slot) | **0h** ❌ |
| `09:00–11:00 morning` + `11:00–13:00 afternoon` | **2h** ✓ | **2h** ✓ |

Per far funzionare half-day su un giorno da 4h serve **splittare a metà** il singolo slot in due fasce AM/PM.

**Lo script `scripts/fix_calendars_split_am_pm.py` attuale NON copre questo caso:** la sua `classify()` tratta gli slot con `hour_to <= 13:00` come "tutto AM" e li *rilascia* come morning senza splittarli. Va esteso per dividere a metà anche gli slot singoli interamente in mattina o pomeriggio quando si vuole abilitare half-day su quei giorni.

Alternativa scartata: overridare `_get_durations` nel modulo `custom_hr_holidays_hours8` per calcolare half-day come `total_day_hours / 2`. È una patch invasiva e disallineata dal modello dati di Odoo — meglio sistemare i calendari.

### Calendari template non assegnati (cleanup)

Esistono ma non hanno dipendenti — si possono archiviare:

`40% (CH from 2023)`, `70% (CH from 2023)`, `60% (CH from 2023)`, `60% (NL from 2023)`, `60% Hybrid (NL Weds off)`, `50% (CH from 2023)`, `50% (D4P from 2023)`, `90% (CH from 2024)`, `80% horizontal (NL)`, `50% (Wed afternoon - Fri) 2026`, `100% 42 hrs (CH from 2023)`.

---

## 9. Esempi concreti per dipendente — cosa succede col modulo `÷8`

Per ognuno dei dipendenti sbilanciati, ecco cosa accade quando chiede ferie. Tutti gli esempi assumono allocazione corretta in ore (`200h × %`).

### ✅ Klaudia dos Santos (90%) — calendario balanced

Allocazione: **180h** = "22.5 days" mostrati (180/8).

| Richiesta | Ore consumate | Display | OK? |
|---|---|---|---|
| Lunedì libero | 8h | "1 day" | ✓ |
| Venerdì libero | 4h | "0.5 day" | ✓ |
| Settimana intera Lun-Ven | 36h | "4.5 days" | ✓ |
| Half-day Lun mattina | dovrebbe essere 4h | **8h** ❌ | bug AM/PM |
| Half-day Lun pomeriggio | dovrebbe essere 4h | **0h** ❌ | bug AM/PM |

### ✅ Roya Shokoohi (90% NL Wed halfday) — calendario balanced

Allocazione: **180h** = "22.5 days" mostrati.

| Richiesta | Ore consumate | Display | OK? |
|---|---|---|---|
| Lunedì libero | 8h | "1 day" | ✓ |
| Mercoledì libero | 4h | "0.5 day" | ✓ |
| Settimana intera | 36h | "4.5 days" | ✓ |

### ✅ Gabriele Cerfoglio (50%) — calendario balanced

Allocazione: **100h** = "12.5 days" mostrati.

| Richiesta | Ore consumate | Display | OK? |
|---|---|---|---|
| Lunedì libero | 8h | "1 day" | ✓ |
| Mercoledì libero | 4h | "0.5 day" | ✓ |
| Tutta la settimana lavorativa (Lun-Mer) | 20h | "2.5 days" | ✓ |
| Giovedì libero | 0h | "0 day" — non lavora ☑ | ✓ |

### ✅ Andrea Falconi (50%) — calendario balanced

Allocazione: **100h** = "12.5 days" mostrati.

| Richiesta | Ore consumate | Display | OK? |
|---|---|---|---|
| Martedì libero | 8h | "1 day" | ✓ |
| Mercoledì libero | 4h | "0.5 day" | ✓ |
| Venerdì libero | 8h | "1 day" | ✓ |
| Settimana lavorativa intera | 20h | "2.5 days" | ✓ |

### ⚠️ Patricia Geraldes (80% horizontal) — frazioni innaturali

Allocazione: **160h** = "20 days" mostrati. Lavora 6.4h **ogni giorno** Lun–Ven.

| Richiesta | Ore consumate | Display | Problema? |
|---|---|---|---|
| Lunedì libero | 6.4h | "0.8 day" | 🤨 Lei pensa "ho preso 1 giorno", il sistema dice 0.8 |
| Settimana intera (Lun-Ven) | 32h | "4 days" | 🤨 Lei pensa "ho preso 1 settimana", sistema dice 4 (non 5) |
| Anno intero di ferie (5 settimane reali) | 160h | "20 days" | ✓ totale coerente, ma per arrivarci servono 25 sue giornate |

**Nodo:** Patricia ha 25 sue giornate disponibili (160h ÷ 6.4h) ma vede "20 days" sulla dashboard. Confusione probabile.

### ⚠️ Eugenia Kypriotis (100% NL/BE 38h) — frazioni innaturali

Allocazione: **190h** (25 days × 7.6) o **200h** (target). Lavora 7.6h ogni giorno Lun–Ven.

| Richiesta | Ore consumate | Display | Problema? |
|---|---|---|---|
| Lunedì libero | 7.6h | "0.95 day" | 🤨 Decimali strani per una giornata |
| Settimana intera | 38h | "4.75 days" | 🤨 Per 1 settimana? |

### ❌ Konstantin Skaburskas (45%) — calendario anomalo

Allocazione: **103.5h** (sbagliata) o **90h** (target). Lavora 9h Lun + 9h Mar.

| Richiesta | Ore consumate | Display | Problema? |
|---|---|---|---|
| Lunedì libero | 9h | "1.13 day" | 🤨 9h al giorno è anomalo |
| Mercoledì libero | 0h | "0 day" — non lavora | ✓ ma rigido |

**Da chiarire con HR:** la giornata da 9h è davvero così, o è un errore di setup?

### ❌ Monique Calisti NL (20%) — calendario degenere

Allocazione: **20h** (sbagliata, dovrebbe essere 40h). Lavora 1.6h Lun–Ven (≈ 1h36 al giorno).

| Richiesta | Ore consumate | Display | Problema? |
|---|---|---|---|
| Lunedì libero | 1.6h | "0.2 day" | ❌ |
| Settimana intera | 8h | "1 day" | ❌ |

**Suggerimento:** ridefinire come "1 giorno × 8h alla settimana" (es. solo Lun 09:00–17:00). Meno realistico ma più maneggevole. Da valutare con HR (è un account "for approvals only", forse irrilevante).

---

## 10. Roadmap rivista — Fase 2A vs 2B

Alla luce dell'audit, la roadmap iniziale di §5 si articola in due sotto-fasi.

### Fase 2A — Quick wins puramente tecnici (basso rischio, alto valore)

| Step | Cosa | Chi | Tempo |
|---|---|---|---|
| 1 | Splittare tutti i calendari in slot AM/PM (script automatico, 4h+4h dove possibile) | IT | 1/2 giorno |
| 2 | Pulizia allocazioni doppie/sbagliate (Klaudia, Roya, Konstantin) | IT | 1/2 giorno |
| 3 | Riemettere allocazioni corrette in ore: `200h × percentuale_contratto` | IT | 1/2 giorno |
| 4 | Verifica con Klaudia che vede i numeri attesi | IT + Klaudia | 1 ora |

**Risultato atteso:** half-day funzionante per tutti, allocazioni coerenti, Klaudia smette di lamentarsi.

### Fase 2B — Decisioni di policy (richiedono confronto)

| Step | Cosa | Chi | Tempo |
|---|---|---|---|
| 1 | Decidere se convertire calendari "horizontal" in "vertical" (Patricia, Eugenia) | Management + HR | 1 settimana |
| 2 | Chiarire l'orario reale di Konstantin (9h × 2 giorni o altro?) | HR | 1 giorno |
| 3 | Decidere se riconfigurare Monique NL 20% | HR | 1 giorno |
| 4 | Decidere se estendere modalità `hour` ad altri tipi di ferie (Public Holidays, Paternity, ecc.) | Management | 1 settimana |
| 5 | Cleanup template calendar inutilizzati | IT | 1 ora |

**Risultato atteso:** modello dati pulito, scelte consapevoli, eventuale estensione del modulo ad altri tipi.

### Ordine consigliato

1. Fase 2A subito (basso rischio, risolve il caso Klaudia)
2. Comunicazione ai dipendenti coinvolti
3. Fase 2B in parallelo, con calma, una decisione alla volta
