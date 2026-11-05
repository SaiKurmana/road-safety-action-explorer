# Action library curation

`actions/actions.yaml` is the single source of truth for the resources the app and site display.
This document explains how entries were selected and cited, and how to add one.

## Principles

1. **Published sources only.** An entry exists only if it appears in a published document that was
   opened and read, and the citation points to the exact page.
2. **Verbatim carry-over.** Titles, evidence ratings, rating definitions, and benefit statements are
   copied exactly as published. If a rating cannot be verified, `rating_status` is `not_verified`. If a
   source publishes no rating, `rating_status` is `not_rated_by_source`. Ratings are never inferred.
3. **No new recommendations.** Entries describe what a source says. Wording that tells a state what to
   do is not allowed in titles, descriptions, or classifications.
4. **Transparent classification.** Fields that are not in the source (Safe System element, prevention
   level, lead sectors, topic tags) follow the fixed rules below and are labeled as curator
   classifications in the app.

## Sources used (and why)

| Source | Entries | What is carried over |
|---|---|---|
| NHTSA, *Countermeasures That Work: A Highway Safety Countermeasure Guide for State Highway Safety Offices*, 11th Edition, 2023 (DOT HS 813 490), ROSA P record 72947 | 77 | Title as printed in the chapter summary table; star rating (1-5) and its legend definition; cost, use, and time-to-implement codes; table footnotes; section and printed page of the countermeasure's detail section |
| FHWA, *Making Our Roads Safer: One Countermeasure at a Time* - 28 Proven Safety Countermeasures (FHWA-SA-21-071), ROSA P record 88186 | 28 | Title, focus area, handout number, and the full "Safety Benefits" sidebar text |
| U.S. DOT, *National Roadway Safety Strategy* (January 2022), ROSA P record 66388 | 2 | Objective definitions for Post-Crash Care and Safer Vehicles (no ratings published) |
| CDC, Motor Vehicle Injury Prevention Interventions (MV PICCS pages) | linked as `related_resources` | Page title and URL. CDC publishes no rating scale, so these pages are attached to matching entries and never carry a rating |

**Edition check.** The 11th edition (November 2023) of *Countermeasures That Work* is the most recent
edition that could be opened. NHTSA's own pages returned HTTP 403 from the build environment, and a
2025 NHTSA procurement notice refers to a 12th edition. That edition could not be opened, so it is
not used. Re-check when access allows.

**Scope choices.**
- *Countermeasures That Work* chapters on alcohol-impaired driving, seat belts and child restraints,
  speeding, motorcycles, young drivers, older drivers, pedestrians, and bicycles are included because
  each maps to a FARS measure.
- Drug-impaired, distracted, and drowsy driving are not included: FARS coding for these is not used
  in this project.
- Approaches listed under "Approaches That Are Unproven or Need Further Evaluation" carry no star
  rating and are not included.

## How ratings were verified

- **CTW star ratings** are graphics, so text extraction cannot read them.
  - Each chapter's summary table was rendered as an image and the stars transcribed.
  - An automated count of star shapes on the same pages matched the transcription for all 77
    rows.
- **PSC safety-benefit figures** were read from each handout's "Safety Benefits" sidebar image,
  because text extraction drops some figures (e.g. the 78% roundabout value).
- **`make verify-citations`** (`pipeline/verify_citations.py`) opens each cited PDF page and checks:
  - the action title appears on that page;
  - for CTW, it also appears on the summary-table page;
  - for PSC, the handout number appears on the page.

  All 107 entries pass.

## Classification rules

| Field | Rule |
|---|---|
| `safe_system_element` | CTW: by chapter. Speeding chapter → Safe Speeds; every other chapter → Safe Road Users; "Lower Speed Limits" in the pedestrian and bicycle chapters → Safe Speeds. PSC: Speed Management focus area → Safe Speeds; all other focus areas → Safe Roads. NRSS: the objective's own element. |
| `prevention_level` | Safe Roads, Safe Speeds, Safe Vehicles → `primary_upstream`; Safe Road Users → `individual_behavior`; Post-Crash Care → `post_crash`. |
| `topic_tags` | CTW chapter → one tag (alcohol, occupant_protection, speed, motorcycle, young_driver, older_driver, pedestrian, bicycle). PSC focus area → speed, roadway_departure, intersection, pedestrian + bicycle, or crosscutting. NRSS → post_crash or vehicles. Signal rules use these tags. |
| `lead_sectors` | Generic roles only: legislation → state legislature + highway safety office (+ driver licensing agency for licensing measures); enforcement → law enforcement + highway safety office; other behavioral strategies → highway safety office + community groups, with documented overrides where the strategy is delivered by courts, health care, schools, employers, or EMS. PSC → state DOT + local transportation agencies. These describe who is *typically involved*, not who should act. |

## Default ordering

Implemented in `pipeline/yaml_to_seeds.py` (`sort_key`):

1. prevention level (upstream → behavior → post-crash);
2. Safe System element;
3. star rating, highest first (unrated after rated);
4. title.

## How to add an entry

1. Open the source document and find the page that describes the countermeasure. If the source
   isn't already in `sources.yml`, add it to `DOCUMENTS` in `pipeline/sources.py` and run
   `make refresh-sources`, which downloads it and records its checksum.
2. Add an entry to `actions/actions.yaml` with:
   - `id`, unique and kebab-case with a source prefix;
   - `title`, verbatim;
   - `source_id`, `source`, `source_url` (the PDF URL plus `#page=N`), `source_landing_url`;
   - `section`, `page` (printed page label), `pdf_page`;
   - classification fields, set by the rules above;
   - `evidence`: `rating` verbatim, `stars` if any, `rating_status`, `rating_definition`
     (verbatim), `rating_source` (page);
   - optional `related_resources`.
3. If the entry should appear for a signal, give it a topic tag used by a rule in
   `actions/signal_rules.yaml`.
4. Run `make verify-citations` and `make test`. The dbt tests fail if:
   - the citation does not point into a `sources.yml` document;
   - a star rating is malformed;
   - a rule no longer reaches any resource.
5. Run `make site` and check the entry in the action library page.
