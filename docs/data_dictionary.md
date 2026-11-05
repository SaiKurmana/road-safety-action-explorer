# Data dictionary

_Generated from the dbt project by `python -m pipeline.data_dictionary`; do not edit by hand._

All counts are deaths in fatal crashes on public roads in the 50 states and DC, from NHTSA FARS final files. `state_fips = 0` denotes the United States. See [methods.md](methods.md) for derivations.

## Measures

| measure_id | Label | VMT denominator | Definition |
|---|---|---|---|
| `fatalities_total` | All traffic fatalities | total | Sum of FATALS in the FARS Accident file (all persons who died within 30 days of a crash on a public trafficway). |
| `fatalities_pedestrian` | Pedestrian fatalities | total | Persons killed (PER_AUX A_PERINJ=1) whose person type is pedestrian (A_PTYPE=3). |
| `fatalities_pedalcyclist` | Bicyclist and other pedalcyclist fatalities | total | Persons killed (A_PERINJ=1) whose person type is pedalcyclist (A_PTYPE=4). |
| `fatalities_motorcyclist` | Motorcyclist fatalities | total | Drivers and passengers killed (A_PTYPE in 1,2; A_PERINJ=1) in vehicles whose VEH_AUX body type is motorcycle (A_BODY=7). |
| `fatalities_speeding_related` | Speeding-related fatalities | total | Sum of FATALS in crashes involving speeding (ACC_AUX A_SPCRA=1). |
| `fatalities_alcohol_impaired_driving` | Alcohol-impaired-driving fatalities | total | NHTSA definition: fatalities in crashes involving a driver with BAC .08 g/dL or higher. Computed as the mean over NHTSA's 10 multiply-imputed highest-driver-BAC values (MIDRVACC A1-A10 >= 8) of the crash's FATALS, which reproduces NHTSA's published 2023 national figure (12,382). |
| `fatalities_pv_occupant` | Passenger-vehicle occupant fatalities | total | Drivers and passengers killed (A_PTYPE in 1,2; A_PERINJ=1) in passenger cars and light trucks (A_BODY 1-5). |
| `fatalities_unrestrained_pv_occupant` | Unrestrained passenger-vehicle occupant fatalities | total | Passenger-vehicle occupants killed whose restraint use is unrestrained (PER_AUX A_RESTUSE=2). |
| `fatalities_pv_occupant_restraint_unknown` | Passenger-vehicle occupant fatalities with unknown restraint use | total | Passenger-vehicle occupants killed whose restraint use is unknown (A_RESTUSE=3); shown as a data-completeness measure. |
| `fatalities_young_driver_involved` | Fatalities in crashes involving a young driver (15-20) | total | Sum of FATALS in crashes involving at least one driver aged 15-20 (ACC_AUX A_D15_20=1). Counts everyone killed in those crashes, not only the young driver. |
| `fatalities_older_driver_involved` | Fatalities in crashes involving an older driver (65+) | total | Sum of FATALS in crashes involving at least one driver aged 65+ (ACC_AUX A_D65PLS=1). Counts everyone killed in those crashes. |
| `fatalities_rural` | Rural fatalities | rural | Sum of FATALS where land use is rural (ACC_AUX A_RU=1); VMT rate uses rural VMT. |
| `fatalities_urban` | Urban fatalities | urban | Sum of FATALS where land use is urban (A_RU=2); VMT rate uses urban VMT. |
| `fatalities_land_use_unknown` | Fatalities with unknown rural/urban land use | n/a | Sum of FATALS where land use is unknown (A_RU=3); data-completeness measure. |
| `fatalities_roadway_departure` | Roadway-departure fatalities | total | Sum of FATALS in crashes involving a roadway departure, FHWA definition (ACC_AUX A_RD=1). |
| `fatalities_intersection_related` | Intersection-related fatalities | total | Sum of FATALS in crashes at an intersection (ACC_AUX A_INTSEC=1). |
| `fatalities_fc_interstate` | Fatalities on Interstates (principal arterial) | fc_interstate | Sum of FATALS where roadway function class is Interstate (ACC_AUX A_ROADFC=1); VMT rate uses VM-2 Interstate VMT. |
| `fatalities_fc_freeway_expressway` | Fatalities on other freeways and expressways | fc_freeway_expressway | A_ROADFC=2 (freeway and expressway, principal arterial); VMT rate uses VM-2 other freeways and expressways VMT. |
| `fatalities_fc_other_principal_arterial` | Fatalities on other principal arterials | fc_other_principal_arterial | A_ROADFC=3; VMT rate uses VM-2 other principal arterial VMT. |
| `fatalities_fc_minor_arterial` | Fatalities on minor arterials | fc_minor_arterial | A_ROADFC=4; VMT rate uses VM-2 minor arterial VMT. |
| `fatalities_fc_collector` | Fatalities on collectors | fc_collector | A_ROADFC=5; VMT rate uses VM-2 major + minor collector VMT. |
| `fatalities_fc_local` | Fatalities on local roads | fc_local | A_ROADFC=6; VMT rate uses VM-2 local VMT. |
| `fatalities_fc_unknown` | Fatalities with unknown function class | n/a | A_ROADFC=7 (unknown); data-completeness measure. |
| `ems_minutes_crash_to_scene` | Minutes from crash to EMS arrival at scene (median) | n/a | Median of (EMS arrival time - crash time) over fatal crashes where both times are valid (Accident HOUR/MINUTE, ARR_HOUR/ARR_MIN); wraps past midnight; values of 720+ minutes treated as implausible. |
| `ems_minutes_crash_to_hospital` | Minutes from crash to EMS arrival at hospital (median) | n/a | Median of (EMS hospital arrival time - crash time) over fatal crashes where both times are valid (HOSP_HR/HOSP_MN); wraps past midnight; values of 720+ minutes treated as implausible. |

## Committed aggregates (data/aggregates/)

### `agg_fars_ems_summary`

EMS timing summary for fatal crashes by state (0 = U.S.) and period (each year plus the pooled signal window). Exported to data/aggregates/fars_ems_summary.csv.

| Column | Description |
|---|---|
| `state_fips` | State FIPS code; 0 = United States. |
| `period_label` | Single year (e.g. "2023") or pooled window (e.g. "2021-2023"). |
| `n_crashes` | Fatal crashes in the period. |
| `n_crash_time_known` | Crashes with a valid crash hour and minute. |
| `n_scene_valid` | Crashes with a valid, plausible (< 720 min) interval from crash to EMS arrival at scene. |
| `n_scene_not_applicable` | Crashes coded "not applicable or not notified" for EMS arrival (ARR_HOUR = 88). |
| `n_scene_implausible` | Crashes whose computed crash-to-scene interval is 720 minutes or more (excluded). |
| `n_hospital_valid` | Crashes with a valid, plausible interval from crash to EMS arrival at hospital. |
| `n_hospital_not_applicable` | Crashes coded not applicable / not notified / not transported, terminated, or cancelled. |
| `n_hospital_implausible` | Crashes whose computed crash-to-hospital interval is 720 minutes or more (excluded). |
| `median_minutes_to_scene` | Median minutes from crash to EMS arrival at scene, among valid intervals. |
| `p90_minutes_to_scene` | 90th percentile of minutes from crash to EMS arrival at scene. |
| `median_minutes_to_hospital` | Median minutes from crash to EMS arrival at hospital, among valid intervals. |
| `p90_minutes_to_hospital` | 90th percentile of minutes from crash to EMS arrival at hospital. |

### `agg_fars_state_year_counts`

FARS fatality counts by state, year, and measure (long format). state_fips 0 is the United States computed directly from all records. Exported to data/aggregates/fars_state_year_counts.csv.

| Column | Description |
|---|---|
| `state_fips` | State FIPS code; 0 = United States (50 states + DC; Puerto Rico excluded). |
| `year` | Crash year (FARS final file). |
| `measure_id` | Measure identifier; see the measures seed for definitions. |
| `value` | Number of fatalities. Alcohol-impaired-driving fatalities are the mean over NHTSA's 10 BAC imputations and can therefore carry one decimal place. |

### `agg_population_state_year`

Census Bureau resident population estimates (July 1) by state and year. Exported to data/aggregates/population_state_year.csv.

| Column | Description |
|---|---|
| `state_fips` | State FIPS code. |
| `year` | Estimate year (July 1). |
| `population` | Resident population estimate. |
| `source_id` | sources.yml id of the Census file the estimate came from. |

### `agg_vmt_state_year`

FHWA Highway Statistics Table VM-2 vehicle miles traveled (millions) by state and year, with rural/urban and functional-system totals. Exported to data/aggregates/vmt_state_year.csv.

| Column | Description |
|---|---|
| `state_fips` | State FIPS code. |
| `year` | Data year of the Highway Statistics edition. |
| `vmt_total_millions` | Total annual VMT, millions of miles. |
| `vmt_rural_millions` | Rural VMT, millions. |
| `vmt_urban_millions` | Urban VMT, millions. |
| `vmt_fc_interstate_millions` | Interstate VMT (rural + urban), millions. |
| `vmt_fc_freeway_expressway_millions` | Other freeways and expressways VMT, millions. |
| `vmt_fc_other_principal_arterial_millions` | Other principal arterial VMT, millions. |
| `vmt_fc_minor_arterial_millions` | Minor arterial VMT, millions. |
| `vmt_fc_collector_millions` | Major + minor collector VMT, millions. |
| `vmt_fc_local_millions` | Local road VMT, millions. |


## Marts (data/marts/, read by the app and site)

### `dim_actions`

Action library with flattened tags and lead sectors.

| Column | Description |
|---|---|
| `action_id` | Stable identifier. |
| `default_order` | Upstream-first sort position. |
| `title` | Title as printed in the source. |
| `source_id` | sources.yml document id. |
| `source` | Citation of the source document. |
| `source_url` | PDF link with |
| `source_landing_url` | Catalog record of the document. |
| `section` | Chapter/section path in the source. |
| `page` | Printed page label (or handout number). |
| `pdf_page` | PDF page number of the citation. |
| `safe_system_element` | Safe Road Users, Safe Vehicles, Safe Speeds, Safe Roads, or Post-Crash Care. |
| `prevention_level` | primary_upstream, individual_behavior, or post_crash. |
| `rating` | Evidence rating exactly as published (e.g. CTW stars) or "Not rated by source". |
| `stars` | Number of CTW stars (null for sources without stars). |
| `rating_status` | published, not_rated_by_source, or not_verified. |
| `rating_definition` | The source's own definition of the rating level. |
| `rating_source` | Where the rating appears in the source. |
| `evidence_detail` | Published benefit statement (PSC) or objective text (NRSS). |
| `topic_tags` | Semicolon-separated topic tags used by signal rules. |
| `lead_sectors` | Generic roles typically involved (curator classification). |

### `dim_peers`

Peer states: the n_peers nearest states by Euclidean distance on z-scored rural VMT share and VMT per capita (most recent year). Ties broken by FIPS.

| Column | Description |
|---|---|
| `state_fips` | State FIPS code. |
| `peer_rank` | 1 = most similar. |
| `peer_fips` | Peer state FIPS code. |
| `distance` | Euclidean distance in standardized feature space. |

### `dim_state_profile`

Most-recent-year denominators and peer-matching features per state (0 = U.S.).

| Column | Description |
|---|---|
| `state_fips` | State FIPS code; 0 = United States. |
| `state_abbr` | USPS abbreviation. |
| `state_name` | State name. |
| `profile_year` | Year of the features (most recent analysis year). |
| `population` | Resident population. |
| `vmt_total_millions` | Total VMT, millions. |
| `rural_vmt_share` | Rural VMT / total VMT (FHWA VM-2). |
| `vmt_per_capita` | Total VMT / population, miles per resident per year. |

### `fct_ems_times`

Time from crash to EMS arrival at scene and at hospital for fatal crashes, with completeness, by state (0 = U.S.) and period. Medians use only valid, plausible intervals.

| Column | Description |
|---|---|
| `state_fips` | State FIPS code; 0 = United States. |
| `period_label` | Year or pooled window label. |
| `period_start` | First year of the period. |
| `period_end` | Last year of the period. |
| `is_signal_window` | True for the pooled signal window used by rules. |
| `n_crashes` | Fatal crashes. |
| `n_crash_time_known` | Crashes with valid crash time. |
| `n_scene_valid` | Crashes with a valid crash-to-scene interval. |
| `n_scene_not_applicable` | EMS arrival coded not applicable / not notified. |
| `n_scene_implausible` | Intervals of 720+ minutes, excluded. |
| `pct_crashes_scene_time_valid` | n_scene_valid / n_crashes x 100 (completeness). |
| `n_hospital_valid` | Crashes with a valid crash-to-hospital interval. |
| `n_hospital_not_applicable` | Hospital arrival coded not applicable / not transported / terminated / cancelled. |
| `n_hospital_implausible` | Intervals of 720+ minutes, excluded. |
| `pct_crashes_hospital_time_valid` | n_hospital_valid / n_crashes x 100. |
| `pct_transport_eligible_hospital_time_valid` | n_hospital_valid / (n_crashes - n_hospital_not_applicable) x 100. |
| `median_minutes_to_scene` | Median minutes, crash to EMS arrival at scene. |
| `p90_minutes_to_scene` | 90th percentile minutes, crash to EMS arrival at scene. |
| `median_minutes_to_hospital` | Median minutes, crash to EMS arrival at hospital. |
| `p90_minutes_to_hospital` | 90th percentile minutes, crash to EMS arrival at hospital. |
| `state_median_minutes_to_scene` | Median of state medians (signal window only). |
| `state_median_minutes_to_hospital` | Median of state medians (signal window only). |

### `fct_signal_actions`

Action-library entries linked to each state's triggered signals (via topic tags).

| Column | Description |
|---|---|
| `state_fips` | State FIPS code. |
| `action_id` | Action identifier. |
| `default_order` | Upstream-first default sort order. |
| `safe_system_element` | Safe System element of the action. |
| `prevention_level` | primary_upstream, individual_behavior, or post_crash. |
| `triggered_by_rules` | Rule ids (semicolon-separated) that linked this action. |

### `fct_signal_inputs`

Uniform (state, measure, metric) values with comparators, used to evaluate signal rules.

| Column | Description |
|---|---|
| `state_fips` | State FIPS code; 0 = United States. |
| `measure_id` | Measure identifier. |
| `metric` | rate_per_100k, rate_per_100m_vmt, or median_minutes. |
| `value` | The state's value. |
| `n` | Records behind the value (deaths in window, or crashes with valid EMS times). |
| `national_value` | U.S. value for the same metric and window. |
| `state_median` | Median across the 50 states + DC. |
| `peer_median` | Median across the state's peers. |
| `window_start` | First year of the window. |
| `window_end` | Last year of the window. |

### `fct_state_signals`

Every signal rule evaluated for every state (50 + DC), with the values used.

| Column | Description |
|---|---|
| `state_fips` | State FIPS code. |
| `rule_id` | Rule identifier from actions/signal_rules.yaml. |
| `rule_order` | Display order of the rule. |
| `label` | Rule label. |
| `measure_id` | Measure the rule reads. |
| `metric` | Metric the rule reads. |
| `comparator` | state_median or national_rate. |
| `operator` | above or below. |
| `min_n` | Minimum underlying records required to evaluate the rule. |
| `window_start` | First year of the window. |
| `window_end` | Last year of the window. |
| `value` | State value. |
| `n` | Underlying records. |
| `comparator_value` | Value the state is compared against. |
| `national_value` | U.S. value (context). |
| `state_median` | Median of states (context). |
| `peer_median` | Median of peer states (context). |
| `evaluable` | False when data are missing or fewer than min_n records exist. |
| `triggered` | True when the comparison holds and the rule is evaluable. |

### `fct_state_year_measures`

State x year x measure counts with population and VMT rates. state_fips 0 = United States.

| Column | Description |
|---|---|
| `state_fips` | State FIPS code; 0 = United States. |
| `year` | Crash year. |
| `measure_id` | Measure identifier (see measures seed). |
| `count` | Fatalities (see measure definition). |
| `population` | Census resident population for the state and year. |
| `vmt_denominator` | Which VMT is the denominator for rate_per_100m_vmt (total, rural, urban, or a function class); empty when no VMT rate applies. |
| `vmt_millions` | VMT used as denominator, millions of miles. |
| `rate_per_100k` | count / population x 100,000. |
| `rate_per_100m_vmt` | count / (VMT in hundred-million miles). Null when no VMT denominator applies. |

### `fct_window_measures`

Pooled signal-window comparison (most recent window_years final years) per state x measure, with prior-window trend, U.S. value, median of the 50 states + DC, and median of the state's peers.

| Column | Description |
|---|---|
| `state_fips` | State FIPS code; 0 = United States. |
| `measure_id` | Measure identifier. |
| `window_start` | First year of the pooled window. |
| `window_end` | Last year of the pooled window (most recent final FARS year). |
| `count_window` | Fatalities summed over the window. |
| `count_annual_avg` | Average annual fatalities in the window. |
| `low_count_flag` | True when the window count is below 20; rates on small counts are unstable. |
| `rate_per_100k` | Pooled fatalities / pooled population x 100,000. |
| `rate_per_100m_vmt` | Pooled fatalities per 100 million VMT (pooled). |
| `prior_window_start` | First year of the prior window of equal length. |
| `prior_window_end` | Last year of the prior window. |
| `prior_rate_per_100k` | Rate per 100k in the prior window. |
| `prior_rate_per_100m_vmt` | Rate per 100M VMT in the prior window. |
| `pct_change_rate_per_100k` | Percent change in rate per 100k, prior window to current window. |
| `national_rate_per_100k` | U.S. pooled rate per 100k for the same window. |
| `national_rate_per_100m_vmt` | U.S. pooled rate per 100M VMT for the same window. |
| `state_median_rate_per_100k` | Median rate per 100k across the 50 states + DC. |
| `state_median_rate_per_100m_vmt` | Median rate per 100M VMT across the 50 states + DC. |
| `peer_median_rate_per_100k` | Median rate per 100k across the state's peer states (dim_peers). |
| `peer_median_rate_per_100m_vmt` | Median rate per 100M VMT across the state's peer states. |
| `rank_rate_per_100k` | Rank among the 50 states + DC by rate per 100k (1 = highest). Null for the U.S. row. |
