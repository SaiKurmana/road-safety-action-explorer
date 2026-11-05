-- Action library (from actions/actions.yaml via generated seeds) with tags and lead sectors
-- flattened for display. default_order implements the documented "upstream first" sort.

with tags as (
    select action_id, string_agg(tag, '; ' order by tag) as topic_tags
    from {{ ref('action_tags') }}
    group by action_id
),

sectors as (
    select action_id, string_agg(lead_sector, '; ' order by lead_sector) as lead_sectors
    from {{ ref('action_sectors') }}
    group by action_id
)

select
    a.*,
    t.topic_tags,
    s.lead_sectors
from {{ ref('actions') }} as a
left join tags as t using (action_id)
left join sectors as s using (action_id)
