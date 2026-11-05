"""FARS release-status classification (no network)."""

from pipeline.sources import FarsYear, S3Object, classify_release, resolve_unstated

# Phrases copied from the real NHTSA release notes for each wording variant.
NOTES = {
    2015: "1/11/2017: \nUpdated with the FARS final data for 2015.",
    2016: "07/07/2017: files are released with FARS 2016 annual data.\n09/27/2018: files are released for FARS 2016 final data.",
    2017: "09/27/2018: files are released for FARS 2017 annual data.\n10/22/2019: this is the first release of the FARS 2017 final file.",
    2018: "10/22/2019: This is the release of FARS 2018 annual file.\n12/18/2020: This is the release of FARS 2018 final files.",
    2023: "04/08/2025\nThis is the first release of the 2023 FARS annual file.\n04/01/2026\nThis is the first release of the 2023 FARS final file.",
    2024: "04/01/2026: This is the first release of the 2024 FARS annual file.",
}


def test_classify_each_wording():
    for year in (2015, 2016, 2017, 2018, 2023):
        assert classify_release(NOTES[year], year) == "final", year
    assert classify_release(NOTES[2024], 2024) == "annual_report_file"
    assert classify_release("FARS National and Puerto Rico Files", 2014) == "not_stated"


def test_year_specific_match():
    # A note mentioning another year's final file must not mark this year final.
    assert classify_release("This is the first release of the 2023 FARS final file.", 2024) == "not_stated"


def _fy(year, status):
    o = S3Object(key=f"k{year}", size=1, etag="x", last_modified="")
    return FarsYear(year, status, o, o, o)


def test_unstated_years_older_than_explicit_final_are_final():
    years = [_fy(2014, "not_stated"), _fy(2015, "final"), _fy(2024, "annual_report_file"), _fy(2025, "not_stated")]
    resolve_unstated(years)
    assert years[0].status == "final" and "inferred" in years[0].status_basis
    assert years[3].status == "not_stated"  # newer than every explicit final: never assumed final
