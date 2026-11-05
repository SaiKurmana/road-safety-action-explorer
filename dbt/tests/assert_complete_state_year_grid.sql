-- Every state (50 + DC + U.S.) has every fatality measure in every analysis year.
with expected as (
    select s.state_fips, y.year, m.measure_id
    from {{ ref('states') }} as s
    cross join (select distinct year from {{ ref('agg_population_state_year') }}) as y
    cross join (select measure_id from {{ ref('measures') }} where unit = 'deaths') as m
)

select e.*
from expected as e
left join {{ ref('fct_state_year_measures') }} as f using (state_fips, year, measure_id)
where f.count is null or f.rate_per_100k is null
