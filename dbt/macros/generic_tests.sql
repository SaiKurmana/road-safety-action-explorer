{% test unique_combination(model, combination) %}
select {{ combination | join(', ') }}, count(*) as n
from {{ model }}
group by {{ combination | join(', ') }}
having count(*) > 1
{% endtest %}


{% test value_between(model, column_name, min_value, max_value, where_sql=None) %}
select *
from {{ model }}
where {{ column_name }} is not null
  and ({{ column_name }} < {{ min_value }} or {{ column_name }} > {{ max_value }})
  {% if where_sql %}and ({{ where_sql }}){% endif %}
{% endtest %}
