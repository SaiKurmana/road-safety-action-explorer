-- Every action must cite a document listed in sources.yml, with a deep link to a PDF page in that
-- document, a page/section, and an evidence rating field (or an explicit "not rated"/"not verified").
select a.action_id, a.source_id, a.source_url
from {{ ref('actions') }} as a
left join {{ ref('source_documents') }} as d using (source_id)
where d.source_id is null
   or a.source_url not like d.url || '#page=%'
   or a.pdf_page is null or a.pdf_page < 1
   or coalesce(trim(a.page), '') = ''
   or coalesce(trim(a.section), '') = ''
   or coalesce(trim(a.rating), '') = ''
   or a.rating_status not in ('published', 'not_rated_by_source', 'not_verified')
   or (a.rating_status = 'published' and coalesce(trim(a.rating_source), '') in ('', 'n/a'))
