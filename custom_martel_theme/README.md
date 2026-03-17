# custom_martel_theme — Odoo 18 Custom Theme

Modulo di personalizzazione UI per Martel Innovate.

## Funzionalità

| Feature | Dettaglio |
|---|---|
| **Colore brand** | Header navbar, pulsanti primari, link, focus → `#284b55` |
| **Sidebar menu** | Stile dark (come screenshot) con hover e active state |
| **Chatter in fondo** | Il chatter/messaggistica viene spostato sotto il form, full-width |
| **Timesheet full-width** | La griglia ore si estende al massimo orizzontalmente con scroll se necessario |
| **Sabato & Domenica grigi** | Le colonne weekend sono evidenziate in grigio chiaro + hatching |
| **Input weekend disabilitati** | Click non permesso su celle weekend (rimuovere `pointer-events: none` per abilitarli) |

## Installazione

1. Copia la cartella `custom_martel_theme` dentro la directory `addons` del tuo Odoo  
   (es. `/opt/odoo/custom_addons/custom_martel_theme`)

2. Riavvia il server Odoo:
   ```bash
   sudo systemctl restart odoo
   # oppure nel container Docker:
   docker restart <container_name>
   ```

3. Vai su **Settings → Apps → Update Apps List**

4. Cerca `Martel Custom Theme` e clicca **Install**

5. Aggiorna i moduli dipendenti se necessario:
   ```bash
   ./odoo-bin -u custom_martel_theme -d <your_db>
   ```

## Dipendenze richieste

Il modulo richiede che siano installati:
- `web`
- `mail`
- `timesheet_grid`
- `hr_timesheet`

Se non usi `timesheet_grid` (Odoo Enterprise), rimuovilo dall'array `depends` nel `__manifest__.py`.

## Personalizzazione

### Cambiare il colore brand

Modifica le variabili CSS in `static/src/scss/custom_theme.scss`:

```scss
:root {
    --martel-primary:        #284b55;  // ← cambia qui
    --martel-primary-dark:   #1c363e;
    --martel-primary-light:  #3a6472;
    --martel-primary-hover:  #2f5763;
}
```

### Abilitare l'inserimento ore nel weekend

Rimuovi o commenta questa riga in `custom_theme.scss`:
```scss
pointer-events: none !important;  // rimuovi questa riga
```

### Struttura file

```
custom_martel_theme/
├── __init__.py
├── __manifest__.py
├── static/
│   └── src/
│       ├── scss/
│       │   └── custom_theme.scss       # tutti gli stili
│       └── js/
│           └── weekend_highlighter.js  # logica weekend columns
```

## Note Odoo 18

- Il modulo usa il sistema assets bundle di Odoo 18 (`web.assets_backend`)
- Il JS usa `@odoo/owl` e il sistema `registry` di Odoo 18
- Compatibile con la modalità `debug` e `assets` di sviluppo
