# Kharif rice district identity and boundary review

Reviewed 20 October 2026. This step checks geographic metadata without reading the seasonal yield, area or production files, including reserved newer outcomes. It does not train models, replace old results or certify unchanged borders across 1997–2022.

## Findings

The [official Census 2011 state/district catalogue](https://censusindia.gov.in/nada/index.php/catalog/6191) supplies **640 unique national district codes**. Its state hierarchy is retained. These are Census 2011 identifiers, **not current Local Government Directory (LGD) codes**.

The 147 district-name rows in the official Kharif rice report have the following dispositions:

| Disposition | Source rows | Meaning |
| --- | ---: | --- |
| Exact name after case and punctuation normalization | 103 | Same named entry in the official 2011 register; does not establish the same territory in every year |
| Explicitly reviewed spelling/translation candidate | 24 | A named rule maps to a 2011 entry; no fuzzy matching and no source-issued DES code crosswalk |
| Post-2011 territorial unit or remainder | 20 | Cannot be assigned the complete old parent polygon as its own geometry |
| Total | 147 | Every source row receives a disposition; none silently disappears |

Examples of review candidates are Boudh/Baudh, Korea/Koriya, and the reordered Dinajpur names. Source spellings are preserved. The East singhbum/Purbi Singhbhum rule is explicitly a reviewed candidate, not confirmation that DES supplied a matching district code. Current LGD fields remain empty. The government DILRMP roster request timed out; no codes were invented from names or borrowed from Census numbering.

The 20 non-equivalent 2011 units comprise **15 Chhattisgarh rows** and **five West Bengal rows**: Alipurduar, Jhargram, Kalimpong, Purba Bardhaman and Paschim Bardhaman. Purba is included because it is a territorial remainder, not simply a new spelling of the complete old district.

See [the crosswalk](../data/processed/rice/seasonal_geography/district_crosswalk.csv), [all official reference codes](../data/processed/rice/seasonal_geography/official_census2011_districts.csv), and [district/year flags](../data/processed/rice/seasonal_geography/district_year_flags.csv). The crosswalk distinguishes direct reference IDs from related ancestor IDs; ancestor IDs are never presented as current district identity codes.

## Dated reference geometry

The [DataMeet Census_2011 map](https://github.com/datameet/maps/tree/5ea90379e67dece749b01448ca438161a3534b79/Districts/Census_2011) was downloaded at pinned commit `5ea90379e67dece749b01448ca438161a3534b79`. Its [dataset documentation](https://raw.githubusercontent.com/datameet/maps/5ea90379e67dece749b01448ca438161a3534b79/Districts/README.md) explains that geometry was assembled from taluk sources, with district names/extents derived from the Census Administrative Atlas. This is a community-derived reference, **not an authoritative survey boundary or proof of geographic equivalence in each yield year**.

The source has 641 geometry records: 640 registered districts and one explicitly labelled Data Not Available record with code zero. That zero record is retained in the original source and is not treated as a district. All 640 global identifiers match the official roster and its state codes. The five-state reference subset has 129 polygons: Bihar 38, Chhattisgarh 18, Jharkhand 24, Odisha 30 and West Bengal 19. It includes old Barddhaman and Kolkata even though the rice report has no equivalent whole-district row for them.

All **129 original reference geometries pass validity checks**. No polygon is automatically repaired, simplified or reassigned. The geographic coordinate system is checked as WGS84 degrees. Each valid polygon has an interior representative point; those points are diagnostic locations, not district rice-area centroids or verified weather inputs. Five map name labels differ from the official roster after simple normalization; they are retained and reported rather than silently renamed. Linking uses the validated global `censuscode` field, not the shapefile's state-local `DT_CEN_CD` sequence.

The [reference geometry audit](../data/processed/rice/seasonal_geography/reference_geometry_audit.csv) and [five-state reference GeoJSON](../data/processed/rice/seasonal_geography/reference_geometries.geojson) preserve these qualifications. Matching a valid polygon to a code verifies neither historical agricultural reporting geography nor measurement quality.

## Territorial changes that matter

The frozen evidence ledger contains 22 reviewed event records. It is a screening inventory, not an exhaustive gazette of every village transfer, border adjustment or rename. Important examples are:

- [Alipurduar district administration](https://alipurduar.gov.in/) identifies its separation from Jalpaiguri in 2014. Jalpaiguri's continuing name therefore does not justify reusing its entire 2011 polygon for later reduced-area observations.
- [Kalimpong](https://kalimpong.gov.in/) and [Jhargram](https://jhargram.gov.in/) district administrations identify their 2017 separations from Darjeeling and Paschim Medinipur.
- [Paschim Bardhaman's official history](https://paschimbardhaman.gov.in/history/) records the 2017 division into Purba and Paschim Bardhaman. Both rows have a related ancestor code 335; neither receives that code as a direct same-polygon identity.
- [Sarangarh–Bilaigarh's official history](https://sarangarh-bilaigarh.cg.gov.in/en/history/) names both Raigarh and Balodabazar-Bhatapara as source districts. Following the documented Balodabazar lineage reaches two different 2011 ancestors, 403 and 410. A one-parent assignment or indiscriminate aggregation would be wrong.
- Government profiles document [Gaurela-Pendra-Marwahi's 2020 separation from Bilaspur](https://tourism.cgstate.gov.in/destinations/Gaurela-Pendra-Marwahi), [Arwal's 2001 separation from Jehanabad](https://arwal.nic.in/history/), and the 2007 creations of [Ramgarh](https://ramgarh.nic.in/overview/) and [Khunti](https://outcome.jharkhand.gov.in/district/khunti).

For the nine 2012 Chhattisgarh districts, the ledger uses a primary RBI circular, RBI/2012-13/242, available as an [explicitly identified third-party-hosted copy](https://www.dtf.in/wp-content/files/Circular_dated_10.10.2012_-_Formation_of_nine_new_Districts_in_the_State_of_Chhattisgarh_-_Allotment_of_Lead_Responsibility.pdf), alongside government district evidence. Its bank working codes are not Census or LGD codes. Where legal-effect and inauguration dates differ, the ledger uses a year-level flag rather than asserting a precise boundary transition day. The [state department](https://tribal.cg.gov.in/en/preliminary-information) confirms the 2022 Khairagarh-Chhuikhadan-Gandai creation, but the reviewed source does not establish a full parent partition; its ancestor ID remains unassigned.

The [evidence ledger](../data/processed/rice/seasonal_geography/change_events.json) records sources, parent links, date precision and gaps, including a date-only Jamtara source whose parent relationship is explicitly unverified. Transition-year flags are metadata cautions, not automatic numerical yield exclusions.

## Why weather acquisition is still gated

There are **3,822 metadata district/year flags**, covering 147 names and 26 start years. They contain no numeric outcomes. Pre-2011 equivalence is not inferred from a 2011 code; documented creation years and changed parent territories are flagged separately. Absence from the reviewed change ledger is not proof that a boundary stayed unchanged.

No district is marked verified for the **entire** 1997–2022 interval, and no row is automatically promoted as weather-ready. This means the complete historical equivalence check is still incomplete, not that every district's data is invalid. Copying an older parent point/polygon to a new child would add a systematic spatial mismatch that more algorithms cannot fix.

A defensible next step is one of these two explicit designs:

1. **Keep the five-state scope:** obtain a source-issued DES/Census/LGD crosswalk and dated territorial epochs, or establish complete split/merge partitions. Reconstruct common geography only with documented non-overlapping components. If aggregation is justified, sum production and area for the same year and season before taking their ratio; never average district yields or assign a multi-parent child arbitrarily.
2. **Reduce geographic complexity before evaluating models:** start with a region whose reporting geography can be documented more easily. Odisha is the strongest initial candidate in the current inventory: it has 30 reference districts, and government [district documentation](https://odisha.gov.in/en/about-us/districts) and [historical reorganization material](https://bargarh.odisha.gov.in/en/about-district/about-us) place the major expansion before 1997. Counts and creation history alone still do not establish the absence of every later territorial adjustment. This is a metadata-based recommendation, not a model-performance choice or an automatic change of project scope.

After fixing geography, verify the Kharif crop calendar and dated reporting assumptions, declare the new evaluation protocol, and acquire pre-issue daily weather on the chosen geographic support. A polygon-area or crop-area-weighted estimate must be described according to the actual weighting used. The original annual forecast remains the working dashboard deliverable during this work.

## Attribution, files and reproduction

District map attribution: **DataMeet Community Maps Project**, https://projects.datameet.org/maps/, under **Creative Commons Attribution 2.5 India**, https://creativecommons.org/licenses/by/2.5/in/. The dataset-specific licence is used; the repository's MIT software licence is not substituted for the geometry licence. Official district-code attribution: Office of the Registrar General & Census Commissioner, India, Census 2011 PCA SD catalogue.

Original national shapefile components and the Census source page remain local under `data/raw/rice/seasonal_geography/`. Checked-in derived metadata, the reference subset and checksums are under `data/processed/rice/seasonal_geography/`. The source receipt pins URLs, commit and hashes. A cached source change is rejected rather than silently replacing the receipt. The raw seasonal report and the old 1966-apportioned model are not modified.

Using the project environment, with `pyshp==2.3.1`, in a project-root Python session:

```python
from src.rice_geography import run_geography_audit
run_geography_audit()
```

This imports a functional module, not another app launcher. It requires the recorded raw caches for full source re-verification. A fresh clone can inspect the published crosswalk and reference subset without claiming to reproduce missing raw-source downloads. `app.py` remains the sole application entry point; its Data and research scope tab exposes the geography review.
