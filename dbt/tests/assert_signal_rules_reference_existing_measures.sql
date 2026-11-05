-- Every signal rule must reference an existing measure with a metric that measure supports, a known
-- comparator and operator, and at least one tag that links to at least one action.
with rule_tag_actions as (
    select rt.rule_id, count(atg.action_id) as n_actions
    from {{ ref('signal_rule_tags') }} as rt
    left join {{ ref('action_tags') }} as atg using (tag)
    group by rt.rule_id
)

select r.rule_id, r.measure_id, r.metric, m.unit, rta.n_actions
from {{ ref('signal_rules') }} as r
left join {{ ref('measures') }} as m using (measure_id)
left join rule_tag_actions as rta using (rule_id)
where m.measure_id is null
   or r.comparator not in ('state_median', 'national_rate')
   or r.operator not in ('above', 'below')
   or (m.unit = 'deaths' and r.metric not in ('rate_per_100k', 'rate_per_100m_vmt'))
   or (m.unit = 'minutes' and r.metric <> 'median_minutes')
   or (r.metric = 'rate_per_100m_vmt' and coalesce(m.vmt_denominator, '') = '')
   or coalesce(rta.n_actions, 0) = 0
