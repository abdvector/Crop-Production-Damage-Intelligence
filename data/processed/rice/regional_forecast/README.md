# Derived district rice forecasting data

These files contain district-level administrative aggregates and project model results, not individual survey records. Original provider: Swamikannu et al. (2021), District Level Data (DLD) and Dashboard for Agriculture and Allied-sectors in India, ICRISAT Dataverse, V1, https://doi.org/10.21421/D2/XFB1BZ. Weather estimates: NASA POWER https://power.larc.nasa.gov/.

This data was provided by the International Crops Research Institute for the Semi-Arid Tropics (ICRISAT). ICRISAT bears no responsibility or liability for the analyses or interpretations of the data presented here. The Content is available at http://dataverse.icrisat.org/.

Research/educational use under the source's ICRISAT Data Sharing Agreement: http://data.icrisat.org/document/ICRISAT-Data-Sharing-Agreement.html. No CC BY claim is made for ICRISAT inputs. See the source catalogue for original terms. Reuse should retain source attribution and geographic/temporal definitions.

District identifiers are historical apportioned units. Year is the agricultural start year. Yield and intervals are kg/ha; rain features are monthly mean daily mm/day. Rows in district_years.csv combine original administrative rice measures, past-only historical summaries and June–August weather estimates. Current-year area and production are retained for source auditing but excluded from predictors. Negative source sentinel values do not become valid targets.

Protocol and selection are saved before final evaluation. Aggregate and per-year results are separate from development and calibration. Forecasts are retrospective; low-yield risk is exploratory and not a damage diagnosis. See docs/Rice_Regional_Forecast.md in the project root for methods and limitations.
