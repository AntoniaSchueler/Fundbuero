-- Fundbüro am Katharineum
-- In Supabase unter SQL Editor ausführen.
--
-- Die App verwendet den serverseitigen Supabase Secret/Service-Role-Key.
-- Dieser Key darf NIEMALS ins GitHub-Repository gelangen.
--
-- RLS wird aktiviert, damit die Tabellen nicht versehentlich über einen
-- normalen öffentlichen/publishable Schlüssel beschreibbar werden.

create table if not exists public.fundstuecke (
    id uuid primary key default gen_random_uuid(),
    category text not null check (
        category in (
            'Trinkflaschen',
            'Schuhe',
            'T-Shirts',
            'Federtaschen',
            'Sonstiges'
        )
    ),
    location text not null,
    image_path text not null,
    original_filename text,
    status text not null default 'verfuegbar' check (
        status in ('verfuegbar', 'abgeholt')
    ),
    created_at timestamptz not null default now(),
    collected_at timestamptz
);

create index if not exists fundstuecke_status_idx
    on public.fundstuecke(status);

create index if not exists fundstuecke_category_idx
    on public.fundstuecke(category);

create index if not exists fundstuecke_created_at_idx
    on public.fundstuecke(created_at);

alter table public.fundstuecke enable row level security;

-- Keine öffentlichen Policies anlegen.
-- Die Streamlit-App greift serverseitig mit dem geheimen Supabase-Key zu.

-- Storage bucket:
-- Im Supabase Dashboard unter Storage einen Bucket mit exakt diesem Namen
-- anlegen:
--
--     fundstuecke
--
-- Wichtig: Bucket NICHT öffentlich machen.
--
-- Die Streamlit-App erstellt für die Bilder zeitlich begrenzte Signed URLs.
