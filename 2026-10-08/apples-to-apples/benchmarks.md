# MRI fair-price benchmark table — sources

All figures researched and accessed **2026-10-07**. Every dollar figure below is
tied to the cited public source; where a value could not be sourced it is
marked **not captured** rather than estimated. Rates are national unless
labeled CA. Medicare figures are *allowed amounts* (what Medicare + patient
together pay), not chargemaster list prices.

**How to read this:** "MPFS" = Medicare Physician Fee Schedule global rate
(freestanding/office setting, technical + professional combined).
"HOPD total" = Medicare hospital-outpatient total allowed (facility +
physician). "ASC total" = ambulatory surgery center total. Fair band used by
`fair_price.py` = **1.0×–2.0× the Medicare reference** (HOPD total when
sourced, else MPFS), a stated negotiation heuristic, not a legal standard.

| CPT | Procedure | Medicare MPFS | Medicare HOPD / ASC total | UCSF published cash price | Typical commercial negotiated | Cash market reference |
|---|---|---|---|---|---|---|
| 70551 | MRI brain, without contrast | ≈$200 (2026) | not captured | **$432** | UCSF negotiated $349–$698 | RadNet SF $550 |
| 70552 | MRI brain, with contrast only | ≈$270 (2026) | not captured | not captured | not captured | RadNet SF $700 |
| 70553 | MRI brain, without then with contrast | $316.97 (2026); CA-LA $359.75 | $672 HOPD / $508 ASC (Medicare.gov 2026) | **$652** | ≈$371–$689 (see notes) | SF hospitals $2,810–$6,946, median $5,499 |
| 72141 | MRI cervical spine, without contrast | $190.72 (2026); CA $216.44 | $434 HOPD / $313 ASC (2026) | not captured | $265.76–$449.69 national avgs | not captured |
| 72148 | MRI lumbar spine, without contrast | $198.97 (2025) | $241.72 published OPPS figure (2025) | **$487** | e.g. St. Mary's SF median $707 | CA hospital median cash $2,614; national median $1,173 |
| 72197 | MRI pelvis, without then with contrast | $334.34 (2026); CA $381.61 | ≈$356 hospital outpatient | not captured | $447.27–$701.21 national avgs | national hospital cash median $2,487 |
| 73721 | MRI lower-extremity joint, without contrast | $204.41 (2026); CA $233 | $447 HOPD / $335 ASC (Medicare.gov 2026) | **$330** | $250–$400 typical | national hospital cash median $1,809 |

## Per-code notes and sources

### 70551 — MRI brain without contrast
- MPFS ≈ $200 (2026, national): CareRoute CPT 70553 cost guide comparison table.
  https://www.careroute.ai/costs/cpt/70553
- UCSF published cash price $432; Stanford Health Care Tri-Valley $2,769 for the
  same code — both from the hospitals' own federal price-transparency files,
  via Itemized. https://itemized.health/compare/stanford-tri-valley-vs-ucsf-medical-center
- UCSF published negotiated range $349–$698 (outpatient), UCSF file dated
  2026-06-17: CarePriceFinder. https://carepricefinder.com/hospital/ca/san-francisco/ucsf-medical-center/
- RadNet Medical Imaging San Francisco listed cash $550 for 70551:
  Expected Healthcare. https://expectedhealthcare.com/place/imaging-clinic/ca/san-francisco/radnet-medical-imaging-san-francisco/
- Context: SF Bay Area hospital median cash for brain MRI $2,440, range
  $2,440–$4,960 across 9 hospitals (ProcedureRadar, data as of Mar 2026;
  contrast status grouped): https://www.procedureradar.com/mri-brain/san-francisco-bay-area

### 70552 — MRI brain with contrast only
- MPFS ≈ $270 (2026, national): CareRoute comparison table (same URL as 70551).
- RadNet SF listed cash $700: Expected Healthcare (same URL as 70551).

### 70553 — MRI brain without then with contrast
- MPFS $316.97 (2026 national); California (Los Angeles) $359.75; average
  provider submitted charge $1,911.21 (≈6.0× Medicare): CareRoute.
  https://www.careroute.ai/costs/cpt/70553
- Medicare.gov Procedure Price Lookup (2026 national averages): total
  Medicare-approved amount $508 (ASC) and $672 (hospital outpatient);
  patient 20% shares $101 and $134 respectively:
  https://www.medicare.gov/procedure-price-lookup/cost/70553/
- UCSF published cash price $652 (Stanford Tri-Valley $3,596): Itemized
  (same URL as 70551).
- SF-Oakland-Fremont hospital cash prices for 70553: $2,810 (UCSF Benioff
  Children's Oakland) to $6,946 (Chinese Hospital), median $5,499; published
  negotiated rates span $261–$12,503; transparency files dated Apr–Jul 2026:
  PricedCare. https://www.pricedcare.com/costs/mri-brain/san-francisco-ca
- Bay Area independent imaging/outpatient centers: median negotiated $371
  all-in (781 insurer rates); hospital self-pay example $4,259 vs $9,180
  median commercial at one facility: The True Penny.
  https://www.thetruepenny.com/costs/mri-brain-contrast/bay-area-ca/
- Commercial negotiated estimates ≈ $436 (BCBS) to $689 (Cigna); source also
  characterizes Medicare at ~$350–$450: CodingAhead 2026 MRI billing guide.
  https://www.codingahead.com/cpt-code-mri/
- National hospital-disclosed cash for 70553: median $1,524, middle range
  $381–$2,798: FairVisitHealth. https://fairvisithealth.com/costs/mri-without-insurance/

### 72141 — MRI cervical spine without contrast
- MPFS $190.72 (2026 national); CA $216.44: Med-Reveal fee-schedule data
  (2026 MPFS, conversion factor $33.4009).
  https://www.med-reveal.com/rates/72141-cpt-fee-schedule
- 2026 Medicare totals: hospital outpatient $434 (physician $191 + facility
  $244); surgery center $313: MedCostCheck.
  https://www.medcostcheck.com/state/florida/mri-cervical-spine
- Published national commercial averages $265.76–$449.69 (payer rows, national
  sample): PayerPrice. https://payerprice.com/rates/72141-CPT-fee-schedule
- Context: average submitted charge ≈ 9.1× the Medicare allowed amount
  (CMS 2024 utilization data): CleverDispute. https://cleverdispute.com/cpt/72141

### 72148 — MRI lumbar spine without contrast
- MPFS $198.97 (2025 national); published Medicare OPPS outpatient figure
  $241.72 (2025): HaggleCare. https://hagglecare.com/cpt/72148
- UCSF published cash price $487 (Stanford Tri-Valley $4,408): Itemized
  (same URL as 70551).
- California hospital median discounted cash $2,614; Saint Mary's Medical
  Center SF median negotiated $707 (25th–75th percentile $355–$4,919, gross
  charge shown $6,959): ClearPrice Health.
  https://clearprice-health.com/ca/procedures/mri-lumbar-spine-without-contrast/
- National hospital cash median $1,173: FairVisitHealth (same URL as 70553).

### 72197 — MRI pelvis without then with contrast
- MPFS $334.34 (2026 national, non-facility and facility identical for this
  code); CA $381.61: MedFeeSchedule / Med-Reveal.
  https://www.medfeeschedule.com/code/72197 ·
  https://www.med-reveal.com/rates/72197-cpt-fee-schedule
- Medicare hospital-outpatient base ≈ $356 (before local adjustment);
  national hospital cash median $2,487, middle 50% $1,419–$3,758:
  CarePriceGuide. https://www.carepriceguide.com/procedures/72197
- Published national commercial averages $447.27–$701.21: PayerPrice.
  https://payerprice.com/rates/72197-CPT-fee-schedule

### 73721 — MRI lower-extremity joint without contrast
- MPFS $204.41 (2026 national); CA $233: GoMedicalBilling (CMS 2026 fee
  schedule data). https://www.gomedicalbilling.com/codes/cpt/73721
- Medicare.gov Procedure Price Lookup (2026 national averages): total
  Medicare-approved amount $335 (ASC) and $447 (hospital outpatient);
  patient shares $66 and $88:
  https://www.medicare.gov/procedure-price-lookup/cost/73721
- UCSF published cash price $330 ("knee/lower-extremity MRI without
  contrast"; Stanford Tri-Valley $3,485): Itemized (same URL as 70551).
- Typical commercial $250–$400 (BCBS $275–$350; UnitedHealthcare/Anthem
  $300–$400): Transcure. https://transcure.net/medical-billing/code/cpt/73721/
- National hospital cash median $1,809, middle 50% $1,052–$2,869;
  Medicare hospital-outpatient yardstick $244: CarePriceGuide, CPT 73721
  hospital cash-prices page (accessed via web search 2026-10-07).

## Methodology and caveats

- **Medicare is the anchor** because it is the only price set by a published
  federal methodology (RVUs × conversion factor, OPPS/APC rates) and is the
  reference most payer contracts negotiate from (commonly expressed as
  "% of Medicare").
- The 1.0×–2.0× fair band brackets the sourced commercial data above:
  negotiated rates found for these codes cluster between ~1.1× and ~2.1×
  the Medicare reference (e.g., 70553 imaging-center median $371 ≈ 0.55×
  HOPD but ≈1.17× MPFS; BCBS/Cigna estimates $436–$689 ≈ 1.4×–2.2× MPFS;
  72197 commercial $447–$701 ≈ 1.3×–2.0× its $356 reference).
- **Hospital "cash prices" published in transparency files vary wildly**
  (e.g., SF median $5,499 for 70553) because many hospitals publish a
  nominal cash figure few patients pay. The facility's *own* published cash
  price (UCSF column) is still powerful in a dispute with that facility:
  it is their own number, in their own federal filing.
- California Medicare rates run ~10–15% above national for these codes
  (see CA figures for 72141, 72197, 73721); the tool's band uses national
  references, which makes the band conservative (arguing *against* the
  patient) rather than inflated.
- Professional (radiologist) and technical (facility) components are
  sometimes billed separately; an itemized statement may show a -26/-TC
  split or a separate radiology-group bill. Benchmarks above are global /
  total figures unless noted.
- Nothing here is a quote for Michael's specific claim: his CPT code,
  date of service, billed vs. allowed amounts, and plan terms come from
  the UCSF itemized statement and his insurer's EOB.
