-- Resident population (July 1 estimates), U.S. Census Bureau. 2014-2019: intercensal
-- 2010-2020 series; 2020+: Vintage 2025 series (see sources.yml).
{% if var('source_mode') == 'raw' %}

select
    cast(STATE as integer) as state_fips,
    cast(YEAR as integer) as year,
    cast(POPULATION as bigint) as population,
    SOURCE_ID as source_id
from {{ source('staging', 'population') }}

{% else %}

select
    cast(state_fips as integer) as state_fips,
    cast(year as integer) as year,
    cast(population as bigint) as population,
    source_id
from {{ source('committed', 'population_state_year') }}

{% endif %}
