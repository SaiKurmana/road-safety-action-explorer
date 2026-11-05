-- Vehicle miles traveled (millions), FHWA Highway Statistics Table VM-2 for each year.
{% if var('source_mode') == 'raw' %}

select
    cast(STATE as integer) as state_fips,
    cast(YEAR as integer) as year,
    round(VMT_TOTAL_MILLIONS, 3) as vmt_total_millions,
    round(VMT_RURAL_MILLIONS, 3) as vmt_rural_millions,
    round(VMT_URBAN_MILLIONS, 3) as vmt_urban_millions,
    round(VMT_FC_INTERSTATE_MILLIONS, 3) as vmt_fc_interstate_millions,
    round(VMT_FC_FREEWAY_EXPRESSWAY_MILLIONS, 3) as vmt_fc_freeway_expressway_millions,
    round(VMT_FC_OTHER_PRINCIPAL_ARTERIAL_MILLIONS, 3) as vmt_fc_other_principal_arterial_millions,
    round(VMT_FC_MINOR_ARTERIAL_MILLIONS, 3) as vmt_fc_minor_arterial_millions,
    round(VMT_FC_COLLECTOR_MILLIONS, 3) as vmt_fc_collector_millions,
    round(VMT_FC_LOCAL_MILLIONS, 3) as vmt_fc_local_millions
from {{ source('staging', 'vmt') }}

{% else %}

select
    cast(state_fips as integer) as state_fips,
    cast(year as integer) as year,
    * exclude (state_fips, year)
from {{ source('committed', 'vmt_state_year') }}

{% endif %}
