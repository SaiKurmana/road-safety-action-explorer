-- No subgroup count may exceed all-fatality count for the same state and year, and the rural +
-- urban + unknown land-use split and the function-class split must each sum to the total.
with c as (
    select state_fips, year, measure_id, value from {{ ref('agg_fars_state_year_counts') }}
),

tot as (select state_fips, year, value as total from c where measure_id = 'fatalities_total'),

splits as (
    select
        state_fips, year,
        sum(value) filter (where measure_id in ('fatalities_rural', 'fatalities_urban', 'fatalities_land_use_unknown'))
            as land_use_sum,
        sum(value) filter (where measure_id like 'fatalities_fc_%') as fc_sum
    from c
    group by all
)

select c.state_fips, c.year, c.measure_id, c.value, t.total, 'exceeds total' as problem
from c inner join tot as t using (state_fips, year)
where c.value > t.total or c.value < 0
union all
select s.state_fips, s.year, 'land_use/fc split', s.land_use_sum, t.total, 'split does not sum to total'
from splits as s inner join tot as t using (state_fips, year)
where s.land_use_sum <> t.total or s.fc_sum <> t.total
