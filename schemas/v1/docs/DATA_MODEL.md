\# Universal Data Model v1



\## Purpose



This document defines the relationships, logical keys, and referential

integrity rules for the Universal Data Contracts.



\## Core Relationship Model



A platform run begins with one platform-status record.



The run may publish:



\- Asset master records

\- Recommendations

\- Forecasts

\- Risk metrics

\- Macro signals

\- Export manifest records



Portfolio positions are associated with a portfolio and may originate outside

a specific analytical platform run.



\## Logical Keys



\### Platform Status



Logical primary key:



`platform\_id + run\_id`



Rules:



\- Each platform run must have one platform-status record.

\- A run identifier must not be reused by the same platform.

\- A completed run must include `run\_completed\_at\_utc`.



\### Asset Master



Logical primary key:



`platform\_id + run\_id + universal\_asset\_id`



Long-term canonical identity:



`universal\_asset\_id`



Rules:



\- Every analytical asset must exist in an asset-master export.

\- `platform\_asset\_id` may differ across platforms.

\- `universal\_asset\_id` must follow the identifier standard.

\- One platform run must not publish duplicate asset identifiers.



\### Recommendations



Logical primary key:



`platform\_id + run\_id + universal\_asset\_id + as\_of\_date + time\_horizon`



Foreign-key relationships:



\- `platform\_id + run\_id` references platform status.

\- `platform\_id + run\_id + universal\_asset\_id` references asset master.



Rules:



\- A recommendation must reference a published asset.

\- Multiple horizons are permitted.

\- Multiple records for the same asset and horizon are not permitted within one

&#x20; run unless a future contract version adds explicit model identifiers.



\### Forecasts



Logical primary key:



`platform\_id + run\_id + universal\_asset\_id + forecast\_horizon\_months + forecast\_method + scenario\_name`



Foreign-key relationships:



\- `platform\_id + run\_id` references platform status.

\- `platform\_id + run\_id + universal\_asset\_id` references asset master.



Rules:



\- Multiple forecast methodologies are allowed.

\- Multiple forecast horizons are allowed.

\- A methodology may publish bear, base, and bull values in one record.

\- `forecast\_date` must be later than or equal to `forecast\_origin\_date`.



\### Risk Metrics



Logical primary key:



`platform\_id + run\_id + universal\_asset\_id + as\_of\_date`



Foreign-key relationships:



\- `platform\_id + run\_id` references platform status.

\- `platform\_id + run\_id + universal\_asset\_id` references asset master.



Rules:



\- A risk record must reference a published asset.

\- Category-specific risks may remain in the source platform until a later

&#x20; extensible metric contract is introduced.



\### Portfolio Positions



Logical primary key:



`portfolio\_id + universal\_asset\_id + as\_of\_date`



Foreign-key relationship:



\- `universal\_asset\_id` references the canonical asset registry.



Rules:



\- Current weight should normally be between 0 and 1.

\- Portfolio-level validation should evaluate whether weights sum to

&#x20; approximately 1.

\- Cash may be represented as a position.



\### Macro Signals



Logical primary key:



`platform\_id + run\_id + signal\_id + as\_of\_date`



Foreign-key relationship:



\- `platform\_id + run\_id` references platform status.



Rules:



\- Macro signals do not need an asset-master record.

\- `signal\_id` must remain stable over time.

\- Multiple signals may apply to the same asset class.



\### Export Manifest



Logical primary key:



`platform\_id + run\_id + export\_name + file\_name`



Foreign-key relationship:



\- `platform\_id + run\_id` references platform status.



Rules:



\- Every published export should have a manifest record.

\- Record counts must match the corresponding export.

\- Checksums should be populated in production exports.

\- Validation status must be updated after validation.



\## Referential Integrity



For every run:



1\. Platform status must exist.

2\. Every recommendation must reference an asset-master record.

3\. Every forecast must reference an asset-master record.

4\. Every risk record must reference an asset-master record.

5\. Every manifest record must reference the same platform and run.

6\. Contract versions must be compatible within the export package.



\## Canonical Asset Registry



The Universal Platform will eventually maintain a canonical asset registry

containing one durable record for every recognized asset.



The registry will distinguish between:



\- Canonical identity

\- Platform-native identity

\- Display information

\- Historical mappings

\- Active and inactive status



Initial mapping location:



`data/reference/asset\_identifier\_map.csv`



\## Cross-Platform Identity



The same economic exposure may appear in different forms.



Examples:



\- `metal:gold` represents the commodity.

\- `etf:gld` represents an investable fund.

\- `etf:iau` represents another fund with similar exposure.



These remain separate assets. Exposure grouping will be handled through future

classification and portfolio-risk contracts rather than by assigning the same

identifier.

