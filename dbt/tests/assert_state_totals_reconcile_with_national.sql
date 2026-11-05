-- State totals must reconcile with national totals: for every year and measure, the sum over the
-- 50 states + DC equals the national row computed directly from all records (state_fips = 0).
with states as (
    select year, measure_id, sum(value) as state_sum, count(*) as n_states
    from {{ ref('agg_fars_state_year_counts') }}
    where state_fips <> 0
    group by all
),

nat as (
    select year, measure_id, value as national
    from {{ ref('agg_fars_state_year_counts') }}
    where state_fips = 0
)

select *
from states
full outer join nat using (year, measure_id)
where nat.national is null
   or states.state_sum is null
   or abs(states.state_sum - nat.national) > 0.05
   or states.n_states <> 51
