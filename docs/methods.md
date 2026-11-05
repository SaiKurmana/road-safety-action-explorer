# Methods

Road Safety Action Explorer turns public federal data into a one-page snapshot of each state's
traffic fatality burden and links what the data show to published Safe System countermeasures.
Every number is computed from the files listed in [`sources.yml`](../sources.yml); every resource
comes from a document that was opened and cited to the page.

## 1. Data sources and why bulk files are used

| Role | Source | Years | Identifier |
|---|---|---|---|
| Fatalities | NHTSA Fatality Analysis Reporting System (FARS), National CSV and Auxiliary CSV files | 2014-2023 (final) | `FARS{year}NationalCSV.zip`, `FARS{year}NationalAuxiliaryCSV.zip` |
| Population | U.S. Census Bureau intercensal estimates (2010-2020) | 2014-2019 | SC-EST2020INT-ALLDATA6 |
| Population | U.S. Census Bureau Vintage 2025 estimates | 2020-2023 | NST-EST2025-ALLDATA |
| Travel (VMT) | FHWA Highway Statistics, Table VM-2 (each year's edition) | 2014-2023 | VM-2 |

**Why FARS bulk files and not the FARS CrashAPI.** The FARS CrashAPI
(`https://crashviewer.nhtsa.dot.gov/CrashAPI/`) returned **HTTP 403 "Access Denied"** from the cloud
build environment. The response came from NHTSA's content-delivery network (`server: AkamaiGHost`,
with an `errors.edgesuite.net` reference), not from a local proxy, and the same block applies to
`www.nhtsa.gov` pages. GitHub Actions runners also use cloud IP ranges, so a pipeline that called
the API would fail unpredictably in CI and in the weekly refresh. The project therefore uses
NHTSA's official downloadable FARS files and never calls the CrashAPI, including in the
scheduled workflow. Bulk files have further advantages: they include NHTSA's derived auxiliary
variables and multiply-imputed BAC files, and their checksums can be pinned.

**How files are found and verified.** NHTSA's file-download page
(`https://www.nhtsa.gov/file-downloads?p=nhtsa/downloads/FARS/`) is served from the
`static.nhtsa.gov` storage bucket. The page itself is behind the same 403 block, so
`pipeline/sources.py` reads the bucket's public XML listing, which is the same directory the page
displays. No download URL is constructed by guessing. For every file the pipeline:

1. takes the URL from the listing;
2. checks the downloaded size against the listing and the MD5 against the object's ETag;
3. tests zip integrity;
4. records URL, size, MD5, SHA-256, last-modified date, and access date in `sources.yml`.

`make ingest` re-verifies every SHA-256 before staging. A changed file stops the build until it
has been reviewed and `sources.yml` refreshed.

**Final vs. provisional data.** Each FARS year first appears as an Annual Report File (ARF) and
is replaced about a year later by a final file (FARS Analytical User's Manual, DOT HS 813 794).
The pipeline reads each year's release notes in the listing. 2015-2023 state explicitly that the
final file was released. 2014's notes are silent, so 2014 is classified final because finals
replace ARFs in year order and later years are explicitly final; `sources.yml` records the basis.
**2024 is an Annual Report File (provisional) and is excluded**, so the analysis covers the ten
most recent final years, 2014-2023.

## 2. Measures

All measures cover the 50 states and DC; Puerto Rico is published in separate FARS files and
excluded. Full definitions are in [data_dictionary.md](data_dictionary.md). The main rules:

- **Total fatalities**: sum of `FATALS` in the Accident file. This reproduces NHTSA's published
  2023 final count of 41,025 exactly.
- **Pedestrian / pedalcyclist**: persons killed (`PER_AUX.A_PERINJ = 1`) by NHTSA's derived
  person type (`A_PTYPE` = 3 / 4).
- **Motorcyclist**: drivers and passengers killed in vehicles whose derived body type is
  motorcycle (`VEH_AUX.A_BODY = 7`).
- **Speeding-related**: fatalities in crashes involving speeding (`ACC_AUX.A_SPCRA = 1`).
- **Alcohol-impaired driving** (NHTSA definition): fatalities in crashes in which at least one
  driver had a BAC of .08 g/dL or higher. Many drivers are not tested, so NHTSA publishes 10
  multiply-imputed values of the highest driver BAC in each crash (`MIDRVACC` A1-A10). The count
  is the crash's fatalities × the share of imputations at or above .08, summed, which equals the
  mean over the 10 imputations. This **reproduces NHTSA's published 2023 national figure of
  12,382** (NHTSA, *Traffic Safety Facts 2024 Data: Alcohol-Impaired Driving*, DOT HS 813 815,
  PDF p. 12: "The number of alcohol-impaired-driving fatalities from the 2023 Final File was
  12,382"), so replicating NHTSA's imputation-based estimate was feasible and NHTSA's published
  state tables were not needed. State values can be fractional.
- **Unrestrained passenger-vehicle occupants**: drivers and passengers killed in passenger cars
  and light trucks (`A_BODY` 1-5) with derived restraint use "unrestrained" (`A_RESTUSE = 2`).
  Unknown restraint use (`A_RESTUSE = 3`) is reported separately. Motorcycles are excluded
  because before 2020 motorcyclists were coded "unrestrained".
- **Rural / urban** (`A_RU`) and **roadway function class** (`A_ROADFC`: Interstate, other
  freeways and expressways, other principal arterial, minor arterial, collector, local, unknown).
- **Young (15-20) and older (65+) driver-involved**: fatalities in crashes with at least one
  driver in the age group (`A_D15_20`, `A_D65PLS`). Everyone killed in those crashes is counted.
- **Roadway departure** (FHWA definition, `A_RD`) and **intersection-related** (`A_INTSEC`).
- **Post-crash care signal**: minutes from crash time (`HOUR`, `MINUTE`) to EMS arrival at the
  scene (`ARR_HOUR`, `ARR_MIN`) and at the hospital (`HOSP_HR`, `HOSP_MN`), crash-level:
  - FARS records arrival times but not arrival dates, so intervals wrap at midnight.
  - Codes 88 (not applicable / not notified / not transported), 96-99 (terminated, cancelled,
    unknown) and intervals of 720+ minutes are excluded and counted.
  - Completeness is reported alongside every median.
  - Medians need at least 10 valid intervals; otherwise they are suppressed.

  Nationally in 2021-2023, a usable crash-to-scene interval exists for 43% of fatal crashes and a
  crash-to-hospital interval for 22%. 38% of crashes are coded not transported / not applicable.
  Several states record almost no hospital-arrival times.

## 3. Rates, comparisons, and peers

- **Rates**: deaths per 100,000 resident population (Census July 1 estimates), and deaths per
  100 million VMT.
  - Total and most measures use total VMT.
  - Rural and urban fatalities use rural and urban VMT.
  - Each function class uses that class's VMT, with VM-2 major and minor collectors combined to
    match `A_ROADFC`.
  - VMT rates for person-type measures (e.g. pedestrians) are shown for completeness, but travel
    is a weaker exposure measure for them.
- **Signal window**: comparisons pool the most recent three final years (2021-2023). The rate is
  pooled deaths divided by pooled denominators, which steadies rates for small states. The
  prior three years (2018-2020) give a percent-change trend. Window counts below 20 deaths are
  flagged.
- **National comparison**:
  - the U.S. rate is all-state deaths divided by the all-state denominator;
  - the *median of states* is the median of the 51 state rates.
  - The U.S. row is computed directly from all records, and a dbt test requires the 51 state
    counts to sum to it for every measure and year.
- **Peer states**: for each state, the 5 nearest states by Euclidean distance on two standardized
  (z-scored across the 51) features from the most recent year:
  - rural share of VMT (rurality);
  - VMT per capita (travel exposure).

  Ties are broken by FIPS code. The *peer median* is the median rate of those 5 states.

## 4. Signal rules → resources

Rules are listed in [`actions/signal_rules.yaml`](../actions/signal_rules.yaml) and shown verbatim in
the app. Each rule names:

- a measure;
- a metric (rate per 100k, rate per 100M VMT, or median minutes);
- a comparator (median of states, or the U.S. value);
- an operator;
- a minimum number of underlying records;
- the topic tags whose resources are shown when the rule triggers.

Example: *pedestrian fatality rate per 100,000 (2021-2023) above the median of the 50 states and
DC → show resources tagged `pedestrian`*. A rule is "not evaluated" when fewer than `min_n`
records exist: 20 deaths for rate rules, 30 valid crash-to-hospital intervals for the post-crash
rule.

The logic is deterministic. No AI-generated advice is produced, and the tool describes and
points to resources; it does not tell states what to do. A rule that compares with the median
flags about half of all states by construction; it marks where a state's data differ from the
middle of the distribution, not a finding of need.

**Ordering of resources ("upstream first")**:

1. prevention level: primary/upstream system design (Safe Roads, Safe Speeds, Safe Vehicles),
   then individual behavior (Safe Road Users), then post-crash care;
2. Safe System element;
3. the source's published star rating (highest first; sources without stars after rated
   entries);
4. title.

## 5. Action library

See [action_library_curation.md](action_library_curation.md):

- 77 rated countermeasures from NHTSA *Countermeasures That Work*, 11th edition (2023);
- 28 FHWA Proven Safety Countermeasures;
- 2 National Roadway Safety Strategy framework entries.

Ratings and published benefit statements are copied verbatim, and `make verify-citations` checks
every cited page. The CTW chapters on drug-impaired, distracted, and drowsy driving are not
included because no FARS measure in this project maps to them.

## 6. Reproducibility and testing

- **`make ingest`** fetches and verifies the raw files.
- **`make transform`** runs dbt in *raw* mode on record-level data and exports:
  - state × year aggregates (`data/aggregates/`, committed, < 1 MB);
  - marts (`data/marts/`, committed).
- **`make test`**, used by CI:
  - lints with ruff;
  - rebuilds every model from the committed aggregates alone (*committed* mode) and runs all
    dbt tests;
  - requires the rebuilt marts to match the committed marts byte for byte;
  - runs pytest.
- **dbt tests cover**: unique and non-null keys, plausible rate ranges, state-national
  reconciliation, NHTSA-published 2023 benchmarks, complete state × year grids, subgroup ≤ total
  and splits summing to totals, a valid citation for every action, and every signal rule
  referencing an existing measure and reaching at least one resource.

See [limitations.md](limitations.md) before interpreting any number.
