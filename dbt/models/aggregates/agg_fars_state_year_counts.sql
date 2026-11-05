-- State x year fatality counts in long form (state_fips 0 = United States, computed directly
-- from all records rather than by summing states, so the two can be reconciled in tests).
{% if var('source_mode') == 'raw' %}

with crash_state as ({{ crash_measures('state_fips') }}),
crash_us as ({{ crash_measures('0') }}),
person_state as ({{ person_measures('state_fips') }}),
person_us as ({{ person_measures('0') }}),

wide as (
    select * from crash_state inner join person_state using (state_fips, year)
    union all by name
    select * from crash_us inner join person_us using (state_fips, year)
),

long as (
    unpivot wide
    on columns(* exclude (state_fips, year))
    into name measure_id value value
)

select
    cast(state_fips as integer) as state_fips,
    cast(year as integer) as year,
    measure_id,
    cast(value as double) as value
from long

{% else %}

select
    cast(state_fips as integer) as state_fips,
    cast(year as integer) as year,
    cast(measure_id as varchar) as measure_id,
    cast(value as double) as value
from {{ source('committed', 'fars_state_year_counts') }}

{% endif %}
