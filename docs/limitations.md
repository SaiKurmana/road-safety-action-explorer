# Limitations

Read these before using any number or list from Road Safety Action Explorer.

## What the data cover

- **Fatalities only.** FARS is a census of crashes on public trafficways in which someone died within
  30 days. It contains no non-fatal injuries or property-damage crashes, so the burden of serious
  injury, often several times larger, is not represented.
- **50 states and DC.** Puerto Rico and other territories are excluded.
- **Final files only (2014-2023).** The 2024 Annual Report File is provisional and excluded. Final files
  can still be revised by NHTSA; `sources.yml` pins exact versions by checksum.
- **Coding depends on police reports and state FARS analysts.** Speeding involvement, restraint use,
  land use, and EMS times are only as complete as the source records. Unknown categories are counted and
  shown rather than imputed (except BAC, where NHTSA's own imputations are used).

## What rates can and cannot say

- **Exposure is approximated.** Population rates treat every resident as equally exposed; VMT rates treat
  every mile as equal. Neither adjusts for age structure, trip purpose, vehicle mix, weather, terrain,
  enforcement intensity, or the share of travel by non-residents. VMT is a weak denominator for
  pedestrian and bicyclist deaths.
- **Small numbers are unstable.** Rates based on fewer than 20 deaths are flagged, and signal rules
  are not evaluated on them; three-year pooling reduces, but does not remove, year-to-year noise.
- **Comparisons are descriptive.** "Above the median of states" marks where a state sits in the
  distribution; about half of states are above any median by construction. It is not a test of
  statistical significance and not a measure of program performance.
- **Associations are not causal.** A higher rate does not show why it is higher, and a linked resource is
  not evidence that it would change the rate in a particular state.
- **Peer states** are matched on two features only (rural share of VMT and VMT per capita); states can be
  similar on these and different on much else.

## Post-crash care measures

- FARS records EMS arrival **times but not dates**; intervals wrap at midnight and intervals of 720 or more
  minutes are excluded as implausible.
- Completeness varies widely: nationally (2021-2023) a usable crash-to-hospital interval exists for about
  22% of fatal crashes, and several states record almost none. Many fatally injured people die at the
  scene and are never transported. Medians are suppressed when fewer than 10 valid intervals exist.
- Time to hospital arrival is not time to definitive trauma care, and FARS does not identify trauma
  center level or inter-facility transfers.

## Evidence and the action library

- **Evidence ratings come from the cited sources** (e.g. NHTSA *Countermeasures That Work* star ratings,
  FHWA's Proven Safety Countermeasure designation). This project does not rate, rank, or recommend
  countermeasures and does not write new ones.
- *Countermeasures That Work* covers behavioral countermeasures that State Highway Safety Offices fund.
  Roadway and vehicle strategies come mainly from FHWA's Proven Safety Countermeasures. Vehicle
  countermeasures are thinly represented because the cited sources address vehicle safety mostly as
  federal action.
- The 11th edition (2023) of *Countermeasures That Work* is the newest edition that could be opened and
  verified. NHTSA's own site was not reachable from the build environment, and a newer edition may
  exist.
- Safe System element, prevention level, lead sectors, and topic tags are **curator classifications**
  following the documented rules in `docs/action_library_curation.md`. They are not part of the sources.
- Resources are general. They do not account for a state's existing laws, programs, funding, or
  implementation history.

## Independence

Independent portfolio project. Not affiliated with, endorsed by, or produced for CDC, NHTSA, FHWA, or
USDOT. Uses only public data and published guidance.
