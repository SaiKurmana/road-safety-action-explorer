-- One row per state (and the U.S.) for the most recent analysis year: denominators and the
-- two features used to find peer states (rural share of VMT, VMT per capita).

with latest as (
    select max(year) as year from {{ ref('agg_population_state_year') }}
),

pop as (
    select p.state_fips, p.year, p.population
    from {{ ref('agg_population_state_year') }} as p
    inner join latest using (year)
),

vmt as (
    select v.state_fips, v.vmt_total_millions, v.vmt_rural_millions
    from {{ ref('agg_vmt_state_year') }} as v
    inner join latest using (year)
),

states as (
    select
        s.state_fips,
        s.state_abbr,
        s.state_name,
        p.year as profile_year,
        p.population,
        v.vmt_total_millions,
        v.vmt_rural_millions / v.vmt_total_millions as rural_vmt_share,
        v.vmt_total_millions * 1000000 / p.population as vmt_per_capita
    from {{ ref('states') }} as s
    inner join pop as p using (state_fips)
    inner join vmt as v using (state_fips)
),

us as (
    select
        0 as state_fips,
        'US' as state_abbr,
        'United States' as state_name,
        max(profile_year) as profile_year,
        sum(population) as population,
        sum(vmt_total_millions) as vmt_total_millions,
        sum(vmt_total_millions * rural_vmt_share) / sum(vmt_total_millions) as rural_vmt_share,
        sum(vmt_total_millions) * 1000000 / sum(population) as vmt_per_capita
    from states
)

select
    state_fips,
    state_abbr,
    state_name,
    profile_year,
    population,
    round(vmt_total_millions, 3) as vmt_total_millions,
    round(rural_vmt_share, 4) as rural_vmt_share,
    round(vmt_per_capita, 1) as vmt_per_capita
from (select * from states union all select * from us)
