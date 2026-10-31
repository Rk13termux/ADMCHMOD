-- ===========================================================================
-- CHMODX · Esquema mínimo para el Panel de Administración Pro
-- Ejecuta este archivo en Supabase → SQL Editor.
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- 1. Visitas
-- ---------------------------------------------------------------------------
create table if not exists public.page_views (
    id          bigint generated always as identity primary key,
    path        text        not null,
    referrer    text,
    device      text,
    country     text,
    visitor_id  text,
    created_at  timestamptz not null default now()
);

create index if not exists page_views_created_at_idx
    on public.page_views (created_at desc);

create index if not exists page_views_path_idx
    on public.page_views (path);

create index if not exists page_views_visitor_idx
    on public.page_views (visitor_id);

-- ---------------------------------------------------------------------------
-- 2. Leads / suscriptores
-- ---------------------------------------------------------------------------
create table if not exists public.leads (
    id          bigint generated always as identity primary key,
    email       text        not null unique,
    source      text,
    status      text        not null default 'nuevo',
    created_at  timestamptz not null default now()
);

create index if not exists leads_created_at_idx
    on public.leads (created_at desc);

-- ---------------------------------------------------------------------------
-- 3. Seguridad (RLS)
--
-- El sitio público solo puede INSERTAR. La lectura queda reservada al panel,
-- que usa la service_role key desde el escritorio (nunca en el navegador).
-- ---------------------------------------------------------------------------
alter table public.page_views enable row level security;
alter table public.leads      enable row level security;

drop policy if exists "sitio_inserta_visitas" on public.page_views;
create policy "sitio_inserta_visitas"
    on public.page_views
    for insert
    to anon, authenticated
    with check (true);

drop policy if exists "sitio_inserta_leads" on public.leads;
create policy "sitio_inserta_leads"
    on public.leads
    for insert
    to anon, authenticated
    with check (true);

-- Sin políticas de SELECT: la anon key no puede leer nada.
-- Si prefieres no usar service_role en el panel, descomenta lo siguiente y
-- protege la lectura con un usuario autenticado concreto:
--
-- create policy "panel_lee_visitas"
--     on public.page_views for select to authenticated using (true);
-- create policy "panel_lee_leads"
--     on public.leads for select to authenticated using (true);

-- ---------------------------------------------------------------------------
-- 4. Ejemplos de inserción desde el sitio
-- ---------------------------------------------------------------------------
-- insert into public.page_views (path, referrer, device, visitor_id)
-- values ('/guias/termux-desde-cero/', 'https://google.com', 'mobile', 'v_123');
--
-- insert into public.leads (email, source) values ('alguien@ejemplo.com', 'hero');

-- ---------------------------------------------------------------------------
-- 5. Vista opcional para volúmenes grandes
--
-- Con millones de filas conviene agregar en la base y no en el panel.
-- ---------------------------------------------------------------------------
create or replace view public.analytics_daily as
select
    date_trunc('day', created_at)::date as day,
    count(*)                            as views,
    count(distinct visitor_id)          as visitors
from public.page_views
group by 1
order by 1 desc;

create or replace view public.analytics_pages as
select
    path,
    count(*)                   as views,
    count(distinct visitor_id) as visitors
from public.page_views
group by 1
order by views desc;
