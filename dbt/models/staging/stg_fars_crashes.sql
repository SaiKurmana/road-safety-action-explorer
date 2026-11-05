{{ config(enabled=(var('source_mode') == 'raw')) }}
-- One row per fatal crash, FARS final files. Joins the Accident file to NHTSA's derived
-- auxiliary crash file (ACC_AUX) and to NHTSA's multiply-imputed highest-driver-BAC file
-- (MIDRVACC), and derives EMS time intervals.

with accident as (
    select * from {{ source('staging', 'fars_accident') }}
),

acc_aux as (
    select * from {{ source('staging', 'fars_acc_aux') }}
),

-- Share of NHTSA's 10 imputations in which the highest driver BAC is >= .08 g/dL.
-- MIDRVACC stores BAC in hundredths (0-94), so .08 g/dL = 8.
alcohol as (
    select
        YEAR,
        ST_CASE,
        (
            (A1 >= 8)::int + (A2 >= 8)::int + (A3 >= 8)::int + (A4 >= 8)::int + (A5 >= 8)::int
            + (A6 >= 8)::int + (A7 >= 8)::int + (A8 >= 8)::int + (A9 >= 8)::int + (A10 >= 8)::int
        ) / 10.0 as p_driver_bac_08plus
    from {{ source('staging', 'fars_midrvacc') }}
),

base as (
    select
        a.YEAR as year,
        a.STATE as state_fips,
        a.ST_CASE as st_case,
        a.FATALS as fatals,
        x.FATALS as aux_fatals,
        x.A_RU as land_use,                  -- 1 rural, 2 urban, 3 unknown
        x.A_ROADFC as road_function_class,   -- 1..6 classes, 7 unknown
        x.A_SPCRA = 1 as is_speeding_related,
        x.A_D15_20 = 1 as has_driver_15_20,
        x.A_D65PLS = 1 as has_driver_65_plus,
        x.A_RD = 1 as is_roadway_departure,
        x.A_INTSEC = 1 as is_intersection,
        coalesce(al.p_driver_bac_08plus, 0) as p_driver_bac_08plus,
        -- Times. FARS codes: hours 0-23 valid; 88 = not applicable / not notified (or not
        -- transported, for hospital); 99 = unknown. Minutes 0-59 valid; 96 terminated transport,
        -- 97 officially cancelled, 98 unknown if arrived/transported, 99 unknown.
        case when a.HOUR between 0 and 23 and a.MINUTE between 0 and 59
            then a.HOUR * 60 + a.MINUTE end as crash_minute_of_day,
        case when a.ARR_HOUR between 0 and 23 and a.ARR_MIN between 0 and 59
            then a.ARR_HOUR * 60 + a.ARR_MIN end as scene_minute_of_day,
        case when a.HOSP_HR between 0 and 23 and a.HOSP_MN between 0 and 59
            then a.HOSP_HR * 60 + a.HOSP_MN end as hospital_minute_of_day,
        a.ARR_HOUR = 88 as scene_not_applicable,
        a.HOSP_HR = 88 or a.HOSP_MN in (96, 97) as hospital_not_applicable
    from accident as a
    inner join acc_aux as x using (YEAR, ST_CASE)
    left join alcohol as al using (YEAR, ST_CASE)
)

select
    *,
    -- Arrival can be on the next calendar day; FARS does not record arrival dates, so the
    -- interval wraps at midnight. Intervals of ems_max_minutes or more are treated as implausible.
    case when crash_minute_of_day is not null and scene_minute_of_day is not null
        then (scene_minute_of_day - crash_minute_of_day + 1440) % 1440 end as minutes_to_scene_raw,
    case when crash_minute_of_day is not null and hospital_minute_of_day is not null
        then (hospital_minute_of_day - crash_minute_of_day + 1440) % 1440 end as minutes_to_hospital_raw
from base
