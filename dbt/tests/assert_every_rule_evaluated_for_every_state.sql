-- Each rule must produce exactly one evaluation row for each of the 50 states + DC.
select rule_id, count(*) as n
from {{ ref('fct_state_signals') }}
group by rule_id
having count(*) <> 51
union all
select r.rule_id, 0
from {{ ref('signal_rules') }} as r
where r.rule_id not in (select rule_id from {{ ref('fct_state_signals') }})
