-- Star ratings are carried over verbatim: the rating text must be exactly `stars` star characters,
-- stars must be 1-5, and only Countermeasures That Work entries carry stars.
select action_id, rating, stars, source_id
from {{ ref('actions') }}
where (stars is not null and (stars not between 1 and 5 or rating <> repeat('★', stars)))
   or (stars is not null and source_id <> 'ctw_11th_2023')
   or (stars is null and source_id = 'ctw_11th_2023')
