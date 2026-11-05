{{ config(enabled=(var('source_mode') == 'raw')) }}
-- One row per person killed (PER_AUX A_PERINJ = 1), with NHTSA's derived person type,
-- restraint use, and the body type of the person's vehicle (null for non-occupants).

select
    p.YEAR as year,
    a.STATE as state_fips,
    p.ST_CASE as st_case,
    p.VEH_NO as veh_no,
    p.PER_NO as per_no,
    p.A_PTYPE as person_type,      -- 1 driver, 2 occupant, 3 pedestrian, 4 pedalcyclist, 5 other non-occupant
    p.A_RESTUSE as restraint_use,  -- 1 restrained, 2 unrestrained, 3 unknown, 4 not applicable (2020+)
    v.A_BODY as vehicle_body       -- 1 car, 2-5 light trucks, 6 large truck, 7 motorcycle, 8 bus, 9 other
from {{ source('staging', 'fars_per_aux') }} as p
inner join {{ source('staging', 'fars_accident') }} as a using (YEAR, ST_CASE)
left join {{ source('staging', 'fars_veh_aux') }} as v using (YEAR, ST_CASE, VEH_NO)
where p.A_PERINJ = 1
