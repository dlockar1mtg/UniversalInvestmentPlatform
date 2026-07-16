\# Repository Standards



\## Repository Naming



Preferred long-term repository names:



\- investment-intelligence-platform

\- crypto-intelligence

\- metals-intelligence

\- mtg-intelligence

\- housing-intelligence

\- macro-intelligence

\- stock-intelligence

\- personal-finance-intelligence



Existing local folder names may remain until controlled migration.



\## Default Branch



The protected stable branch is:



`main`



\## Development Branches



Use descriptive branches:



\- `phase-0.2-repository-architecture`

\- `feature/platform-registry`

\- `feature/universal-export`

\- `fix/crypto-identifier-mapping`

\- `release/v1.0.0`



\## Commit Messages



Use clear imperative or descriptive commit messages.



Examples:



\- `Add platform registry schema`

\- `Create universal forecast contract`

\- `Fix crypto asset identifier mapping`

\- `Document MTG archive extraction dependency`



Avoid vague messages such as:



\- `updates`

\- `changes`

\- `fix`

\- `new stuff`



\## Versioning



Use semantic versioning where practical:



`MAJOR.MINOR.PATCH`



Examples:



\- `1.0.0`

\- `1.1.0`

\- `1.1.1`



Definitions:



\- MAJOR: incompatible architectural or schema change

\- MINOR: backward-compatible feature addition

\- PATCH: backward-compatible correction



\## Required Repository Files



Each platform should eventually include:



\- `README.md`

\- `.gitignore`

\- `requirements.txt`

\- `docs/CURRENT\_STATE.md`

\- `docs/RUNBOOK.md`

\- `docs/CHANGELOG.md`

\- `config/`

\- `scripts/`

\- `tests/`



\## Standard Platform Folders



Preferred structure:



platform-repository/

├── config/

├── data/

├── docs/

├── logs/

├── models/

├── outputs/

├── scripts/

├── src/

└── tests/



Existing repositories will be migrated gradually. They do not need to be

restructured immediately.



\## Data Rules



Do not commit:



\- Raw market data

\- Extracted archives

\- Databases

\- API credentials

\- Environment secrets

\- Generated forecasts

\- Large exports

\- Temporary backups



Commit:



\- Source code

\- Schema definitions

\- Documentation

\- Reference mappings

\- Test fixtures

\- Configuration templates

\- Migration scripts



\## Dependency Rules



Each platform should have a project-specific `requirements.txt`.



A global pip freeze may be retained only as an environment record.



Dependencies should not be upgraded without validating existing pipelines.



\## Platform Export Rules



Each platform must eventually publish:



\- Platform status

\- Asset master records

\- Recommendations

\- Forecasts

\- Risk metrics

\- Refresh metadata



Exports must conform to Universal Platform schemas.



\## Recovery Rules



Before major migration work:



1\. Commit the working state.

2\. Create a version tag.

3\. Create a development branch.

4\. Make changes only on the development branch.

5\. Validate before merging to `main`.

