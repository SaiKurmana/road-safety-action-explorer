-- EMS timing summary for fatal crashes, by state (0 = United States) and period
-- (each analysis year, plus the pooled signal window). Medians are not additive, so the
-- pooled window is computed here from crash-level records.
{% if var('source_mode') == 'raw' %}

with crashes as (
    select
        *,
        case when minutes_to_scene_raw < {{ var('ems_max_minutes') }} then minutes_to_scene_raw end as minutes_to_scene,
        case when minutes_to_hospital_raw < {{ var('ems_max_minutes') }} then minutes_to_hospital_raw end
            as minutes_to_hospital
    from {{ ref('stg_fars_crashes') }}
),

bounds as (
    select max(year) as max_year from crashes
),

periods as (
    select distinct year as period_start, year as period_end, cast(year as varchar) as period_label
    from crashes
    union all
    select
        max_year - {{ var('window_years') }} + 1,
        max_year,
        cast(max_year - {{ var('window_years') }} + 1 as varchar) || '-' || cast(max_year as varchar)
    from bounds
),

geo_crashes as (
    select state_fips, * exclude (state_fips) from crashes
    union all
    select 0 as state_fips, * exclude (state_fips) from crashes
)

select
    cast(g.state_fips as integer) as state_fips,
    p.period_label,
    cast(p.period_start as integer) as period_start,
    cast(p.period_end as integer) as period_end,
    count(*) as n_crashes,
    count(*) filter (where crash_minute_of_day is not null) as n_crash_time_known,
    count(minutes_to_scene) as n_scene_valid,
    count(*) filter (where scene_not_applicable) as n_scene_not_applicable,
    count(*) filter (where minutes_to_scene_raw >= {{ var('ems_max_minutes') }}) as n_scene_implausible,
    count(minutes_to_hospital) as n_hospital_valid,
    count(*) filter (where hospital_not_applicable) as n_hospital_not_applicable,
    count(*) filter (where minutes_to_hospital_raw >= {{ var('ems_max_minutes') }}) as n_hospital_implausible,
    -- Medians/percentiles are suppressed (null) when fewer than ems_min_n_for_median valid
    -- intervals exist; the counts above still report completeness.
    {% set k = var('ems_min_n_for_median') %}
    case when count(minutes_to_scene) >= {{ k }} then round(median(minutes_to_scene), 1) end
        as median_minutes_to_scene,
    case when count(minutes_to_scene) >= {{ k }} then round(quantile_cont(minutes_to_scene, 0.9), 1) end
        as p90_minutes_to_scene,
    case when count(minutes_to_hospital) >= {{ k }} then round(median(minutes_to_hospital), 1) end
        as median_minutes_to_hospital,
    case when count(minutes_to_hospital) >= {{ k }} then round(quantile_cont(minutes_to_hospital, 0.9), 1) end
        as p90_minutes_to_hospital
from geo_crashes as g
inner join periods as p on g.year between p.period_start and p.period_end
group by all

{% else %}

select * from {{ source('committed', 'fars_ems_summary') }}

{% endif %}
