# Fundbüro am Katharineum – Streamlit

Diese Version benötigt **kein Supabase** und keine Benutzerkonten für die Nutzerinnen und Nutzer.

## Start lokal

```bash
pip install -r requirements.txt
streamlit run app.py
```

Die App legt automatisch `data/fundbuero.db` und `data/images/` an.

## Verwaltungscode

Lokal funktioniert die App ohne Secrets mit dem Fallback-Code `sekretariat123`.

Für eine öffentliche Streamlit-App sollte der Code über Streamlit Secrets überschrieben werden:

```toml
ADMIN_CODE = "DEIN_GEHEIMER_CODE"
```

## Wichtiger Hinweis zu Streamlit Community Cloud

Ohne Supabase oder einen anderen persistenten externen Speicher sind SQLite-Datenbank und hochgeladene Bilder **nicht dauerhaft garantiert**. Streamlit Community Cloud kann die App-Umgebung neu aufbauen bzw. zurücksetzen. Diese Version ist deshalb sehr gut für lokale Nutzung, Schul-PC/Server oder einen Prototypen geeignet, aber nicht für ein dauerhaftes öffentliches Fundbüro auf Community Cloud.

## Automatische Löschung

- abgeholte Gegenstände: nach 7 Tagen
- nicht abgeholte Gegenstände: nach 365 Tagen

Die Prüfung findet beim Start bzw. bei Nutzung der App statt.
