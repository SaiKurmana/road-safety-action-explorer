-- Post-crash care signal: time from crash to EMS arrival at the scene and at the hospital, from
-- FARS Accident-file times, with completeness. One row per state (0 = U.S.) x period.

with e as (
    select * from {{ ref('agg_fars_ems_summary') }}
),

window_label as (
    select max(period_label) filter (where period_label like '%-%') as label from e
),

state_medians as (
    select
        median(median_minutes_to_scene) as state_median_minutes_to_scene,
        median(median_minutes_to_hospital) as state_median_minutes_to_hospital
    from e
    where state_fips <> 0 and period_label = (select label from window_label)
)

select
    e.state_fips,
    e.period_label,
    e.period_start,
    e.period_end,
    e.period_label = (select label from window_label) as is_signal_window,
    e.n_crashes,
    e.n_crash_time_known,
    e.n_scene_valid,
    e.n_scene_not_applicable,
    e.n_scene_implausible,
    round(e.n_scene_valid / e.n_crashes * 100, 1) as pct_crashes_scene_time_valid,
    e.n_hospital_valid,
    e.n_hospital_not_applicable,
    e.n_hospital_implausible,
    round(e.n_hospital_valid / e.n_crashes * 100, 1) as pct_crashes_hospital_time_valid,
    round(
        e.n_hospital_valid / nullif(e.n_crashes - e.n_hospital_not_applicable, 0) * 100, 1
    ) as pct_transport_eligible_hospital_time_valid,
    e.median_minutes_to_scene,
    e.p90_minutes_to_scene,
    e.median_minutes_to_hospital,
    e.p90_minutes_to_hospital,
    case when e.period_label = (select label from window_label) then sm.state_median_minutes_to_scene end
        as state_median_minutes_to_scene,
    case when e.period_label = (select label from window_label) then sm.state_median_minutes_to_hospital end
        as state_median_minutes_to_hospital
from e
cross join state_medians as sm
