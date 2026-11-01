-- ===========================================================================
-- CHMODX · 002 · Columnas de atribución para la captura web
--
-- Ejecuta este archivo DESPUÉS de schema.sql, en Supabase → SQL Editor.
-- Sin estas columnas la web sigue registrando visitas, pero sin UTM:
-- no se podrá saber qué artículo o qué CTA lleva al curso.
-- ===========================================================================

alter table public.page_views
    add column if not exists session_id   text,
    add column if not exists utm_source   text,
    add column if not exists utm_medium   text,
    add column if not exists utm_campaign text,
    add column if not exists utm_content  text,
    add column if not exists language     text;

create index if not exists page_views_session_idx
    on public.page_views (session_id);

create index if not exists page_views_utm_idx
    on public.page_views (utm_medium, utm_content);

-- Comprobación rápida: debe devolver 13 columnas.
-- select column_name, data_type
-- from information_schema.columns
-- where table_schema = 'public' and table_name = 'page_views'
-- order by ordinal_position;
