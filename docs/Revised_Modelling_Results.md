# Revised modelling: methods, statistical review and results

Completed 21 October 2026. **The revised comparison is reproducible, but it does not establish a reliable forecasting or damage-alert model.** The nested selection procedure did not beat the recent-yield mean. No existing deployment model was replaced. This is a valid negative result from exploratory research, not evidence that every assumption is satisfied.

## What was run

Followed the [protocol declared before execution](Revised_Modelling_Protocol.md) and the [statistical foundation](Statistical_Foundation.md). One observation is an Odisha district and Kharif start year; response is harvested rice yield in kg/ha. Used 420 complete-history development rows in 2004–2017, from the original 600 observed district-years in 1998–2017. No 2018–2022 target labels were read by this run. Because the archive and legacy results were inspected previously, the redevelopment is exploratory throughout.

Three baselines plus 14 learned configurations: history-only and history-plus-weather Ridge, Random Forest and histogram gradient boosting. Numeric X excludes the exact-duplicate historical mean/trend; these remain reference auxiliaries. District identifiers are categorical, with a dropped reference category. Preprocessing fits only on training data. Learned models predict departures from the historical reference, then add that reference back and floor at zero.

The six outer forecast years are 2012–2017, 30 districts per year, 180 outcomes per strategy. Inner chronological validation chooses a configuration separately before each outer year, using only labels through Y−2; each inner fit also stops two years before its own prediction year. Model selection, hyperparameter tuning and feature-block comparisons therefore use earlier labels. No random train/test shuffle or selection from outer results.

## What checks mean for these models

Gaussian predictors are not a prerequisite for linear regression. Residual normality is useful for particular classical inference/interval formulas, not a requirement for computing least-squares or Ridge predictions. Ridge is penalised and these district-year observations are dependent; ordinary iid OLS coefficient tests would not justify coefficient significance here. Trees do not require linearity or normal residuals. All models still need defensible data, timing, evaluation and predictive-error behaviour.

| Check | Actual evidence | Decision |
|---|---|---|
| Data integrity and complete inputs | Original receipt hashes verified, no duplicate modelling keys, finite X/Y, valid historical lags, complete common cohort | Passed enforced data checks |
| Temporal leakage | Every fit ends at Y−2; each outer selection uses inner outcomes only through Y−2 | Passed; historical release dates remain assumed |
| Preprocessing leakage | Scaling/encoding inside each fitting pipeline; target/current-year area/production excluded | Passed implementation checks |
| Redundancy and numeric stability | Primary numeric training designs full rank; largest recorded standardized numeric condition number about 110.5 | No detected rank failure; not proof of stable effects or suitable specification |
| Functional form and error bias | Forecast-versus-observed/error plots, bias by year and predicted-yield quartile | Adequacy concerns remain |
| Changing error size | Absolute-error patterns; primary absolute-error versus prediction Spearman −0.278 | Descriptive evidence of variation; no constant-variance claim |
| Temporal error structure | Within-district consecutive-year error correlation, primary −0.085 | Small pooled correlation is not proof of independence |
| Spatial error structure | Annual descriptive Moran I approximately 0.171–0.475 for the primary strategy | Positive spatial patterns; no independence claim |
| Error distribution | Q–Q plot and descriptive skewness | Not an eligibility gate; no Gaussian interval formula used |
| Generalisation beyond baselines | Paired chronological errors on identical outcomes | Primary procedure worse than recent mean |
| Low-yield detection | Prespecified threshold and full confusion matrix | Failed to detect observed low-yield events in the primary strategy |
| Uncertainty | Separate calibration/evaluation branch, width and interval score | Pooled coverage masks large year-to-year differences |

These are data checks and predictive diagnostics, not a collection of independent-observation hypothesis tests. The whole-year bootstrap intervals below are exploratory and assume exchangeable year clusters; six years and possible serial dependence limit their inferential meaning. No normality, VIF, Breusch–Pagan, Durbin–Watson or OLS p-value has been manufactured to label every model statistically valid. Numeric full rank is not a sufficient condition for sound forecasting. Good predictive validation does not establish causal effects or no omitted-variable bias.

## Primary results

| Strategy | MAE (kg/ha) | RMSE (kg/ha) | R² |
|---|---:|---:|---:|
| Nested selection across all 17 configurations | 780.2 | 952.3 | −0.589 |
| Recent five-yield mean | 684.3 | 814.5 | −0.162 |
| Last available yield | 834.8 | 1017.6 | −0.814 |
| Historical trend | 921.1 | 1106.7 | −1.146 |

The primary procedure has WAPE 44.8% and mean predicted-minus-observed error −353.8 kg/ha. Negative R² means its squared error exceeds the pooled assessment-mean comparator; that comparator is a descriptive reference, not an available real-time forecast. The recent historical mean is the actual operationally available baseline used here.

The primary selection chose recent mean in 2012, 2013, 2015, 2016 and 2017. It chose history Ridge alpha 10 in 2014. Its 2014 MAE was 1,540.1 kg/ha versus 964.9 for recent mean, accounting for the overall disadvantage. That Ridge fit had fitting MAE 262.1 kg/ha: fitting well did not ensure future-year accuracy. Do not use the discovered 2014 outcome to retroactively substitute a better model for that fold.

| Outer year | Primary MAE | Recent-mean MAE |
|---|---:|---:|
| 2012 | 808.6 | 808.6 |
| 2013 | 613.0 | 613.0 |
| 2014 | 1,540.1 | 964.9 |
| 2015 | 352.8 | 352.8 |
| 2016 | 905.1 | 905.1 |
| 2017 | 461.7 | 461.7 |

All figures use the same 180 outer records. These errors are not directly comparable to the earlier 2018–2022 model errors, which concern different years and fitting rules. No claim that the earlier results were reproduced or improved is made.

## Did weather help?

Each row compares the same model family with history only versus history plus weather. Hyperparameters are chosen separately within inner folds. Improvement is history MAE minus weather MAE; positive favours weather.

| Family | History MAE | Weather MAE | Improvement | Exploratory 95% interval |
|---|---:|---:|---:|---:|
| Ridge | 804.7 | 768.5 | +36.2 | −32.3 to +91.9 |
| Random Forest | 750.2 | 798.3 | −48.2 | −140.3 to +26.2 |
| Histogram boosting | 740.3 | 823.8 | −83.6 | −191.2 to −13.8 |

Ridge shows a small uncertain improvement. Forest and boosting do not show a general benefit here. The boosting interval is below zero under the stated bootstrap assumptions, but this short exploratory multi-comparison study does not establish a universal harmful weather effect. No consistent beneficial weather contribution is demonstrated.

## Sensitivities and changes considered

- Adding the redundant historical mean/trend back to the selected models changed mean predictions by only 0.83 kg/ha and gave MAE 781.0 versus primary 780.2. Removing redundancy improves clarity; it did not solve the forecasting problem.
- Removing the most unusual training year, chosen using training data only, gave primary-strategy sensitivity MAE 728.9. It remains worse than recent mean (684.3). The original data and primary results are retained; this sensitivity does not justify deleting real unusual seasons or claiming a new validated winner.
- Using June/July weather only gave the same overall nested selection and MAE 780.2. Weather-family MAEs changed to Ridge 776.3, Forest 781.4 and boosting 788.8. The information-window sensitivity does not overturn the primary conclusion.
- Nonlinear trees, regularisation and complexity constraints were compared within inner folds as planned remedies for overly rigid or unstable predictors. None established overall superiority to the recent mean here. Further transformations or corrections chosen after seeing these outer errors would be a new exploratory version, not a repair that makes these same outcomes independent validation.

## Low-yield flags and intervals

Low yield means actual yield below 80% of its past-yield reference. Among 180 outcomes, 52 were low-yield. The primary strategy generated 30 flags: TP 0, FP 30, FN 52, TN 98. Precision and recall are both 0%. These flags are not suitable as operational alerts.

Intervals belong to a separate fixed-configuration branch, not the adaptive primary strategy. The configuration selected in 2012 was recent mean, using selection labels 2008–2010. Its 90 rolling calibration errors came from 2012–2014, and its 60 interval evaluation outcomes from 2016–2017. Calibration labels are separate from configuration-selection labels and available by the evaluation issue dates under the assumed two-year delay.

Nominal 80% intervals covered 78.3% overall with average width 2,221.3 kg/ha and mean interval score 3,096.7 kg/ha (lower score is better). However, coverage was only 60.0% in 2016 and 96.7% in 2017. Two years, dependent data, broad intervals and unstable conditional coverage do not establish reliability. No risk probability or Gaussian residual-based coverage guarantee is presented.

## Reproducibility and verified safeguards

Run `python app.py --compare-models`. The completed command checks frozen code/protocol/input/output hashes and returns the saved result without refitting. The data audit remains `python app.py --audit-data`. No auxiliary launch scripts are needed.

Verified checks: 17 configurations; 25 full numeric predictors versus 16 in the June/July sensitivity; redundant auxiliaries absent from primary X; future target removed/altered and arbitrary current-year production added without changing a Ridge prediction; invalid fitting cutoffs rejected; identical 180-record cohorts for every nested strategy; no duplicate candidate/district/year records; all fitting and inner-selection cutoffs correct; perturbing 2017 outer outcomes cannot change the nested decisions; history controls unchanged across weather windows; interval label timing and sizes correct; completed reruns do not refit. Existing frozen-model receipts also remain unchanged.

Outputs: `data/processed/rice/revised_modelling/` contains configuration and nested predictions, inner selection decisions, fitting and error diagnostics, district/year results, paired comparisons, sensitivities, interval evaluation, three PNG/SVG figures and hash receipts. No private field records or new personal identifiers are exported.

## What can be claimed

The project now has a transparent, reproducible, time-aware comparison with model-appropriate diagnostics and an explicit negative finding: these predictors and methods have not produced reliable low-yield alerts or consistent gains over a simple historical mean in this redevelopment period. It is suitable for presenting research methods and limitations. It is not statistically cleared for operational forecasting, causal attribution or financial-savings claims. New compatible independent outcomes are needed for confirmation of any future revised method.
