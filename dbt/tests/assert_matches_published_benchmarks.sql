-- National figures must match NHTSA's published 2023 Final File totals (see published_benchmarks seed).
select b.*, c.value as computed
from {{ ref('published_benchmarks') }} as b
left join {{ ref('agg_fars_state_year_counts') }} as c
    on c.state_fips = 0 and c.year = b.year and c.measure_id = b.measure_id
where c.value is null or abs(round(c.value) - b.published_value) > b.tolerance
