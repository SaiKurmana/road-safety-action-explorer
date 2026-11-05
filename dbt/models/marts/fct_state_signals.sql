-- Every signal rule evaluated for every state (50 + DC). A rule is triggered when the state's
-- value is above (or below) the rule's comparator. Rules with min_n require at least that many
-- underlying records; otherwise the rule is reported as not evaluable.

with rules as (
    select * from {{ ref('signal_rules') }}
),

inputs as (
    select * from {{ ref('fct_signal_inputs') }} where state_fips <> 0
),

evaluated as (
    select
        i.state_fips,
        r.rule_id,
        r.rule_order,
        r.label,
        r.measure_id,
        r.metric,
        r.comparator,
        r.operator,
        r.min_n,
        i.window_start,
        i.window_end,
        i.value,
        i.n,
        case r.comparator
            when 'state_median' then i.state_median
            when 'national_rate' then i.national_value
        end as comparator_value,
        i.national_value,
        i.state_median,
        i.peer_median
    from rules as r
    inner join inputs as i using (measure_id, metric)
)

select
    *,
    value is not null and comparator_value is not null and n >= min_n as evaluable,
    coalesce(
        value is not null and comparator_value is not null and n >= min_n
        and (
            (operator = 'above' and value > comparator_value)
            or (operator = 'below' and value < comparator_value)
        ),
        false
    ) as triggered
from evaluated
