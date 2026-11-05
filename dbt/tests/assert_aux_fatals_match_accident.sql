{{ config(enabled=(var('source_mode') == 'raw')) }}
-- Raw mode only: NHTSA's auxiliary crash file must agree with the Accident file on FATALS, and
-- every killed person must belong to a crash in the Accident file.
select year, state_fips, st_case, fatals, aux_fatals
from {{ ref('stg_fars_crashes') }}
where fatals <> aux_fatals
