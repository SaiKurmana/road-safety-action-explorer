{#
  Measure definitions shared by the state-level and national aggregates.
  `geo` is the SQL expression used as state_fips (the state column, or 0 for the national row).
#}

{% macro crash_measures(geo) %}
    select
        {{ geo }} as state_fips,
        year,
        sum(fatals) as fatalities_total,
        sum(case when is_speeding_related then fatals else 0 end) as fatalities_speeding_related,
        round(sum(fatals * p_driver_bac_08plus), 1) as fatalities_alcohol_impaired_driving,
        sum(case when has_driver_15_20 then fatals else 0 end) as fatalities_young_driver_involved,
        sum(case when has_driver_65_plus then fatals else 0 end) as fatalities_older_driver_involved,
        sum(case when land_use = 1 then fatals else 0 end) as fatalities_rural,
        sum(case when land_use = 2 then fatals else 0 end) as fatalities_urban,
        sum(case when land_use = 3 then fatals else 0 end) as fatalities_land_use_unknown,
        sum(case when is_roadway_departure then fatals else 0 end) as fatalities_roadway_departure,
        sum(case when is_intersection then fatals else 0 end) as fatalities_intersection_related,
        sum(case when road_function_class = 1 then fatals else 0 end) as fatalities_fc_interstate,
        sum(case when road_function_class = 2 then fatals else 0 end) as fatalities_fc_freeway_expressway,
        sum(case when road_function_class = 3 then fatals else 0 end) as fatalities_fc_other_principal_arterial,
        sum(case when road_function_class = 4 then fatals else 0 end) as fatalities_fc_minor_arterial,
        sum(case when road_function_class = 5 then fatals else 0 end) as fatalities_fc_collector,
        sum(case when road_function_class = 6 then fatals else 0 end) as fatalities_fc_local,
        sum(case when road_function_class = 7 then fatals else 0 end) as fatalities_fc_unknown
    from {{ ref('stg_fars_crashes') }}
    group by all
{% endmacro %}

{% macro person_measures(geo) %}
    select
        {{ geo }} as state_fips,
        year,
        count(*) filter (where person_type = 3) as fatalities_pedestrian,
        count(*) filter (where person_type = 4) as fatalities_pedalcyclist,
        count(*) filter (where person_type in (1, 2) and vehicle_body = 7) as fatalities_motorcyclist,
        count(*) filter (where person_type in (1, 2) and vehicle_body between 1 and 5) as fatalities_pv_occupant,
        count(*) filter (
            where person_type in (1, 2) and vehicle_body between 1 and 5 and restraint_use = 2
        ) as fatalities_unrestrained_pv_occupant,
        count(*) filter (
            where person_type in (1, 2) and vehicle_body between 1 and 5 and restraint_use = 3
        ) as fatalities_pv_occupant_restraint_unknown
    from {{ ref('stg_fars_persons_killed') }}
    group by all
{% endmacro %}
