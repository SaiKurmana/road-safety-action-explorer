-- State x year x measure: count, denominators, and rates. state_fips 0 = United States.
-- National counts come from the directly computed national row; population and VMT for the
-- nation are the sum of the 50 states and DC.

with counts as (
    select * from {{ ref('agg_fars_state_year_counts') }}
),

pop as (
    select state_fips, year, population from {{ ref('agg_population_state_year') }}
    union all
    select 0, year, sum(population) from {{ ref('agg_population_state_year') }} group by year
),

vmt_states as (
    select * from {{ ref('agg_vmt_state_year') }}
),

vmt as (
    select * from vmt_states
    union all
    select
        0 as state_fips,
        year,
        sum(vmt_total_millions),
        sum(vmt_rural_millions),
        sum(vmt_urban_millions),
        sum(vmt_fc_interstate_millions),
        sum(vmt_fc_freeway_expressway_millions),
        sum(vmt_fc_other_principal_arterial_millions),
        sum(vmt_fc_minor_arterial_millions),
        sum(vmt_fc_collector_millions),
        sum(vmt_fc_local_millions)
    from vmt_states
    group by year
),

measures as (
    select * from {{ ref('measures') }} where unit = 'deaths'
),

joined as (
    select
        c.state_fips,
        c.year,
        c.measure_id,
        c.value as count,
        p.population,
        m.vmt_denominator,
        case m.vmt_denominator
            when 'total' then v.vmt_total_millions
            when 'rural' then v.vmt_rural_millions
            when 'urban' then v.vmt_urban_millions
            when 'fc_interstate' then v.vmt_fc_interstate_millions
            when 'fc_freeway_expressway' then v.vmt_fc_freeway_expressway_millions
            when 'fc_other_principal_arterial' then v.vmt_fc_other_principal_arterial_millions
            when 'fc_minor_arterial' then v.vmt_fc_minor_arterial_millions
            when 'fc_collector' then v.vmt_fc_collector_millions
            when 'fc_local' then v.vmt_fc_local_millions
        end as vmt_millions
    from counts as c
    inner join measures as m using (measure_id)
    inner join pop as p using (state_fips, year)
    inner join vmt as v using (state_fips, year)
)

select
    state_fips,
    year,
    measure_id,
    count,
    population,
    vmt_denominator,
    round(vmt_millions, 3) as vmt_millions,
    round(count / population * 100000, 4) as rate_per_100k,
    -- VMT is in millions of miles, so 100 million miles = vmt_millions / 100.
    round(case when vmt_millions > 0 then count / (vmt_millions / 100) end, 4) as rate_per_100m_vmt
from joined
