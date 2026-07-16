\# Repository Architecture



\## Purpose



The Universal Investment Intelligence Platform integrates standardized

outputs from independently operated investment intelligence platforms.



The architecture is designed to preserve the independence of each platform

while allowing shared portfolio analysis, validation, forecasting comparison,

and allocation intelligence.



\## Architecture Model



The ecosystem uses a multi-repository architecture.



Each investment platform:



\- Owns its raw data

\- Owns its platform-specific database

\- Owns its scoring and forecasting logic

\- Remains independently executable

\- Publishes standardized outputs to the Universal Exchange Layer



The Universal Investment Intelligence Platform:



\- Registers connected platforms

\- Validates published outputs

\- Imports standardized data

\- Tracks platform health and freshness

\- Produces cross-asset portfolio intelligence

\- Supports universal dashboards and reporting



\## Repositories



\### Universal Investment Intelligence Platform



Current location:



`C:\\Users\\DevonLockard\\InvestmentPlatform`



Responsibilities:



\- Shared schemas

\- Platform registry

\- Exchange layer

\- Integration database

\- Cross-platform validation

\- Portfolio intelligence

\- Universal reporting



\### Crypto Intelligence Platform



Current location:



`C:\\Users\\DevonLockard\\Crypto`



Responsibilities:



\- Crypto market ingestion

\- Crypto scoring

\- Crypto forecasts

\- Crypto recommendations

\- Crypto portfolio outputs



\### Metals Intelligence Platform



Current location:



To be confirmed.



Responsibilities:



\- Metals market ingestion

\- Metal and vehicle scoring

\- Metals forecasts

\- Metals recommendations



\### MTG Investment Intelligence Platform



Current location:



To be confirmed.



Responsibilities:



\- TCGCSV archive ingestion

\- Sealed product intelligence

\- Secret Lair intelligence

\- MTG forecasts

\- MTG recommendations



\### Housing Intelligence Platform



Current location:



`C:\\Users\\DevonLockard\\HousingPredictorv6`



Responsibilities:



\- Housing market ingestion

\- Affordability analysis

\- Market forecasts

\- Monte Carlo analysis

\- Purchase-window intelligence



\### Macro Intelligence Platform



Current location:



To be confirmed.



Responsibilities:



\- Recession indicators

\- Liquidity and rate intelligence

\- Economic regime classification

\- Cross-asset macro signals



\### Stocks and ETF Intelligence Platform



Status:



Not started.



Responsibilities:



\- Equity and ETF ingestion

\- Valuation

\- Momentum

\- Dividend analysis

\- Factor analysis

\- Forecasts and recommendations



\### Personal Finance Intelligence Platform



Status:



Planning.



Responsibilities:



\- Income

\- Expenses

\- Debt

\- Net worth

\- Cash flow

\- Investment capacity

\- Financial readiness



\## Integration Principle



Platforms communicate through data contracts rather than direct database

access.



The default flow is:



1\. Platform runs independently.

2\. Platform produces standardized exports.

3\. Exports are published to the platform's exchange folder.

4\. Universal validation checks the exports.

5\. Valid records are loaded into the integration database.

6\. Portfolio intelligence combines the results.



\## Exchange Layer



The exchange layer is located at:



`C:\\Users\\DevonLockard\\InvestmentPlatform\\exchange`



Each platform has its own folder:



\- `exchange/crypto`

\- `exchange/metals`

\- `exchange/mtg`

\- `exchange/housing`

\- `exchange/macro`

\- `exchange/stocks`

\- `exchange/personal\_finance`



The Universal Platform reads from these directories.



Individual platforms do not write directly into the Universal integration

database.



\## Platform Independence



A failure in one platform must not prevent other platforms from being

processed.



The Universal Platform must support:



\- Missing platform exports

\- Stale platform exports

\- Partial platform availability

\- Different refresh schedules

\- Platforms running on different computers



\## Data Ownership



Each platform owns:



\- Raw source data

\- Platform-specific transformations

\- Platform database

\- Platform scoring logic

\- Platform forecasts



The Universal Platform owns:



\- Shared identifiers

\- Shared schemas

\- Integration records

\- Cross-platform comparisons

\- Portfolio allocation outputs

\- Validation history



\## Design Constraints



\- The MTG platform may run on a separate computer.

\- Some software installations may require administrator approval.

\- Python-based replacements are preferred when practical.

\- Large databases and generated exports are not stored in Git.

\- Secrets and credentials are never committed.

\- Existing working platforms must remain recoverable during migration.



\## Future Architecture



The architecture may later support:



\- Network shares

\- OneDrive synchronization

\- Cloud storage

\- Scheduled workers

\- APIs

\- Remote databases



The data-contract model should allow those changes without requiring

platform scoring systems to be rewritten.

