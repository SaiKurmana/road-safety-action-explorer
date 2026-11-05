-- Peer states: for each state, the n_peers nearest other states by Euclidean distance on two
-- standardized features from the most recent analysis year:
--   1. rural share of VMT (FHWA VM-2 rural VMT / total VMT)  -- rurality
--   2. VMT per capita (VM-2 total VMT / Census population)   -- travel exposure
-- Features are z-scored across the 50 states and DC. Ties are broken by state FIPS code.

with s as (
    select state_fips, rural_vmt_share, vmt_per_capita
    from {{ ref('dim_state_profile') }}
    where state_fips <> 0
),

z as (
    select
        state_fips,
        (rural_vmt_share - avg(rural_vmt_share) over ()) / stddev_pop(rural_vmt_share) over () as z_rural,
        (vmt_per_capita - avg(vmt_per_capita) over ()) / stddev_pop(vmt_per_capita) over () as z_vmt_pc
    from s
),

pairs as (
    select
        a.state_fips,
        b.state_fips as peer_fips,
        sqrt(power(a.z_rural - b.z_rural, 2) + power(a.z_vmt_pc - b.z_vmt_pc, 2)) as distance
    from z as a
    inner join z as b on a.state_fips <> b.state_fips
),

ranked as (
    select
        *,
        row_number() over (partition by state_fips order by distance, peer_fips) as peer_rank
    from pairs
)

select state_fips, peer_rank, peer_fips, round(distance, 4) as distance
from ranked
where peer_rank <= {{ var('n_peers') }}
