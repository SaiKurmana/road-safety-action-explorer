-- Pooled-window comparison table: one row per state (0 = U.S.) x measure for the signal window
-- (most recent `window_years` final years), with the prior window of equal length for trend,
-- the U.S. value, the median of the 50 states + DC, and the median of the state's peers.

{% set w = var('window_years') %}

with sym as (
    select * from {{ ref('fct_state_year_measures') }}
),

bounds as (
    select max(year) as max_year from sym
),

windows as (
    select 'current' as which, max_year - {{ w }} + 1 as y0, max_year as y1 from bounds
    union all
    select 'prior', max_year - {{ 2 * w }} + 1, max_year - {{ w }} from bounds
),

pooled as (
    select
        s.state_fips,
        s.measure_id,
        w.which,
        w.y0,
        w.y1,
        -- Round pooled sums to their natural precision so results do not depend on the order in
        -- which floating-point values are added (keeps exports byte-identical across rebuilds).
        round(sum(s.count), 1) as count,
        sum(s.population) as population,
        round(sum(s.vmt_millions), 3) as vmt_millions
    from sym as s
    inner join windows as w on s.year between w.y0 and w.y1
    group by all
),

rates as (
    select
        *,
        count / population * 100000 as rate_per_100k,
        case when vmt_millions > 0 then count / (vmt_millions / 100) end as rate_per_100m_vmt
    from pooled
),

cur as (select * from rates where which = 'current'),
prior as (select * from rates where which = 'prior'),

state_medians as (
    select
        measure_id,
        median(rate_per_100k) as state_median_rate_per_100k,
        median(rate_per_100m_vmt) as state_median_rate_per_100m_vmt
    from cur
    where state_fips <> 0
    group by measure_id
),

peer_medians as (
    select
        p.state_fips,
        c.measure_id,
        median(c.rate_per_100k) as peer_median_rate_per_100k,
        median(c.rate_per_100m_vmt) as peer_median_rate_per_100m_vmt
    from {{ ref('dim_peers') }} as p
    inner join cur as c on c.state_fips = p.peer_fips
    group by all
),

nat as (
    select measure_id, rate_per_100k as national_rate_per_100k, rate_per_100m_vmt as national_rate_per_100m_vmt
    from cur
    where state_fips = 0
)

select
    c.state_fips,
    c.measure_id,
    c.y0 as window_start,
    c.y1 as window_end,
    c.count as count_window,
    round(c.count / {{ w }}, 2) as count_annual_avg,
    c.count < 20 as low_count_flag,
    round(c.rate_per_100k, 4) as rate_per_100k,
    round(c.rate_per_100m_vmt, 4) as rate_per_100m_vmt,
    p.y0 as prior_window_start,
    p.y1 as prior_window_end,
    round(p.rate_per_100k, 4) as prior_rate_per_100k,
    round(p.rate_per_100m_vmt, 4) as prior_rate_per_100m_vmt,
    round(case when p.rate_per_100k > 0 then (c.rate_per_100k / p.rate_per_100k - 1) * 100 end, 1)
        as pct_change_rate_per_100k,
    round(n.national_rate_per_100k, 4) as national_rate_per_100k,
    round(n.national_rate_per_100m_vmt, 4) as national_rate_per_100m_vmt,
    round(sm.state_median_rate_per_100k, 4) as state_median_rate_per_100k,
    round(sm.state_median_rate_per_100m_vmt, 4) as state_median_rate_per_100m_vmt,
    round(pm.peer_median_rate_per_100k, 4) as peer_median_rate_per_100k,
    round(pm.peer_median_rate_per_100m_vmt, 4) as peer_median_rate_per_100m_vmt,
    case when c.state_fips <> 0 then
        rank() over (partition by c.measure_id, c.state_fips = 0 order by c.rate_per_100k desc)
    end as rank_rate_per_100k
from cur as c
left join prior as p using (state_fips, measure_id)
inner join nat as n using (measure_id)
inner join state_medians as sm using (measure_id)
left join peer_medians as pm using (state_fips, measure_id)
