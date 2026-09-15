# Metals CPER Recurring Cost Resolution V1

## Objective

Resolve the remaining CPER recurring-cost evidence gap using primary fund-authoritative documentation without relying on a secondary aggregator or silently inferring a value from the issuer web page.

## Prior state

The governed cost snapshot retained CPER as unresolved because the USCF CPER product page exposed the `Total Expense Ratio` label but did not render a numeric value in the collected page response.

Missing remained missing at that time.

## Authoritative resolution

The current CPER prospectus dated April 24, 2026 and filed with the U.S. Securities and Exchange Commission by the United States Copper Index Fund states under `CPER's Fees and Expenses`:

- Management Fees: 0.65%
- Other Fund Expenses: 0.23%
- Total Annual Fund Operating Expenses: 0.88%

The prospectus further states that the 0.65% management fee is contractually paid to United States Commodity Funds LLC and that the other-fund-expense figure is based on amounts for the year ended December 31, 2025.

Primary source:
`https://www.sec.gov/Archives/edgar/data/1479247/000207187626000122/i26205_cper-424b3.htm`

## Governance decision

For the recurring-cost evidence family, CPER is certified at **0.88% Total Annual Fund Operating Expenses**.

The prior blank issuer-page render is preserved in provenance as the reason the earlier snapshot remained unresolved; it is not treated as conflicting evidence because the filed prospectus supplies the explicit numeric value.

## Boundary

This resolves CPER recurring-cost evidence only. It does not create a preferred implementation label, authorize publication writes, capital allocation, position sizing, trade execution, source-schedule changes, or central cron restoration.

Preferred-vehicle ranking remains fail-closed until all other required evidence families are complete, including tracking-quality evidence or an explicitly governed not-applicable state where permitted.
