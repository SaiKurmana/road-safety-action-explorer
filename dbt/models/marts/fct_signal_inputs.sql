-- Uniform (state, measure, metric) table that signal rules are evaluated against.

with wm as (
    select * from {{ ref('fct_window_measures') }}
),

rate_inputs as (
    select
        state_fips, measure_id, 'rate_per_100k' as metric,
        rate_per_100k as value, count_window as n,
        national_rate_per_100k as national_value, state_median_rate_per_100k as state_median,
        peer_median_rate_per_100k as peer_median,
        window_start, window_end
    from wm
    union all
    select
        state_fips, measure_id, 'rate_per_100m_vmt',
        rate_per_100m_vmt, count_window,
        national_rate_per_100m_vmt, state_median_rate_per_100m_vmt,
        peer_median_rate_per_100m_vmt,
        window_start, window_end
    from wm
    where rate_per_100m_vmt is not null
),

ems as (
    select * from {{ ref('fct_ems_times') }} where is_signal_window
),

ems_long as (
    select state_fips, 'ems_minutes_crash_to_scene' as measure_id, median_minutes_to_scene as value,
           n_scene_valid as n, period_start, period_end
    from ems
    union all
    select state_fips, 'ems_minutes_crash_to_hospital', median_minutes_to_hospital,
           n_hospital_valid, period_start, period_end
    from ems
),

ems_peer as (
    select p.state_fips, e.measure_id, median(e.value) as peer_median
    from {{ ref('dim_peers') }} as p
    inner join ems_long as e on e.state_fips = p.peer_fips
    group by all
),

ems_inputs as (
    select
        e.state_fips,
        e.measure_id,
        'median_minutes' as metric,
        e.value,
        e.n,
        us.value as national_value,
        (select median(x.value) from ems_long as x where x.state_fips <> 0 and x.measure_id = e.measure_id)
            as state_median,
        ep.peer_median,
        e.period_start as window_start,
        e.period_end as window_end
    from ems_long as e
    inner join ems_long as us on us.state_fips = 0 and us.measure_id = e.measure_id
    left join ems_peer as ep on ep.state_fips = e.state_fips and ep.measure_id = e.measure_id
)

select * from rate_inputs
union all
select * from ems_inputs
