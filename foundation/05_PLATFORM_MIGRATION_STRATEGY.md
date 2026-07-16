\# Platform Migration Strategy



\## Purpose



This document defines how existing investment intelligence platforms will be

prepared for integration without disrupting their current working states.



\## Migration Principle



Migration will be incremental.



Existing repositories will not be renamed, moved, or substantially reorganized

until their current state has been documented and preserved through Git.



The Universal Platform will initially reference current local paths through the

platform registry.



\## Migration Order



Recommended order:



1\. Crypto

2\. Metals

3\. Housing

4\. MTG

5\. Macro

6\. Personal Finance

7\. Stocks and ETFs



\## Why This Order



\### Crypto



Crypto is the most actively developed platform and has the clearest known

integration issue. It is a good candidate for defining the first universal

export contract.



\### Metals



Metals is operational and relatively stable. It can validate that the universal

contract works for a second asset class.



\### Housing



Housing has mature forecast and Monte Carlo outputs but differs structurally

from tradable assets. It will test schema flexibility.



\### MTG



MTG has large archive and historical-data dependencies. It should be migrated

after the standard process is proven on easier repositories.



\### Macro



Macro produces regime and indicator signals rather than conventional asset

recommendations. It requires specialized contracts.



\### Personal Finance



Personal Finance contains user-specific financial data and requires additional

privacy and security decisions.



\### Stocks and ETFs



Stocks and ETFs will be built using the established standards rather than

retrofitted later.



\## Migration Stages



Each platform will pass through the following stages.



\### Stage 1 — Inventory



Document:



\- Local repository path

\- Current version

\- Main run command

\- Primary database

\- Inputs

\- Outputs

\- Dependencies

\- Known issues



\### Stage 2 — Freeze



Before changes:



1\. Create or verify the Git repository.

2\. Add an appropriate `.gitignore`.

3\. Commit the current working state.

4\. Create a baseline version tag.

5\. Create an integration branch.



\### Stage 3 — Documentation



Add:



\- `README.md`

\- `docs/CURRENT\_STATE.md`

\- `docs/RUNBOOK.md`

\- `requirements.txt` or equivalent dependency file



\### Stage 4 — Export Adapter



Add platform-specific code that converts existing outputs into Universal

Platform data contracts.



The adapter should not replace the platform's internal logic.



\### Stage 5 — Validation



Confirm:



\- Required columns exist

\- Identifiers are valid

\- Scores remain within expected ranges

\- Forecast horizons are complete

\- Dates and timestamps are valid

\- Duplicate records are controlled

\- Existing platform results have not changed unintentionally



\### Stage 6 — Registration



Add the platform to the Universal Platform Registry.



\### Stage 7 — Integration



Publish the standardized output to the platform's exchange folder and import it

into the Universal integration database.



\## No-Break Migration Rule



A platform is not considered migrated unless:



\- Its original pipeline still runs.

\- Its original outputs remain available.

\- The universal export is generated separately.

\- The migration can be reversed through Git.

\- Validation confirms no unintended model changes.



\## Local Folder Names



Existing local folder names may remain during Phase 0.



Repository naming standards describe the preferred long-term GitHub names and

do not require immediate folder renaming.



\## MTG Migration



The MTG platform may remain on the secondary laptop until its environment is

fully reproduced.



The successful `py7zr` test indicates that system-installed 7-Zip is not a hard

requirement.



Migration should begin with one copied archive and one copied project snapshot

before the original working environment is changed.



\## Data Migration



Raw data and platform databases will not initially be copied into the Universal

repository.



The Universal Platform will receive only validated standardized outputs.



\## Rollback



Rollback consists of:



1\. Stop the migration work.

2\. Return to the platform baseline tag.

3\. Preserve failed migration files for review.

4\. Document the reason in the architecture decision log.

