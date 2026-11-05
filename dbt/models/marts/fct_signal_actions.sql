-- For each state, the action-library entries linked to its triggered signals (via topic tags).
-- One row per state x action, listing every triggered rule that surfaced it.

with triggered as (
    select state_fips, rule_id, rule_order from {{ ref('fct_state_signals') }} where triggered
),

links as (
    select distinct t.state_fips, t.rule_id, t.rule_order, atg.action_id
    from triggered as t
    inner join {{ ref('signal_rule_tags') }} as rt using (rule_id)
    inner join {{ ref('action_tags') }} as atg using (tag)
)

select
    l.state_fips,
    l.action_id,
    a.default_order,
    a.safe_system_element,
    a.prevention_level,
    string_agg(l.rule_id, '; ' order by l.rule_order) as triggered_by_rules
from links as l
inner join {{ ref('actions') }} as a using (action_id)
group by all
