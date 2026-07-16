\# Universal Validation Standard



\## Purpose



The Universal Validation Framework evaluates whether the Universal Investment

Intelligence Platform and its connected data are structurally valid,

internally consistent, and ready for analytical use.



Validation is distinct from model accuracy.



A record may conform to its schema while still failing cross-contract,

freshness, referential-integrity, or operational checks.



\## Validation Levels



\### Record Validation



Evaluates an individual record against:



\- Required fields

\- Data types

\- Allowed values

\- Score ranges

\- Identifier patterns

\- Date and timestamp formats



\### Contract Validation



Evaluates an entire contract export for:



\- Required columns

\- Column order

\- Duplicate logical keys

\- Contract-version consistency

\- Record-level validity



\### Package Validation



Evaluates all exports from one platform run for:



\- Shared platform identifier

\- Shared run identifier

\- Shared contract version

\- Asset references

\- Manifest coverage

\- Checksum validity

\- Record-count accuracy



\### Integration Validation



Evaluates records after database import for:



\- Required tables and views

\- Duplicate imports

\- Orphan records

\- Registry references

\- Import audit consistency

\- Analytical-view availability



\### Foundation Validation



Evaluates the complete Phase 0 foundation:



\- Development environment

\- Universal Data Contracts

\- Platform registry

\- Integration database

\- Cross-contract consistency

\- Platform freshness

\- Validation-report completeness



\## Severity Levels



\### info



Informational result that does not represent a problem.



Examples:



\- Optional platform is disabled

\- No real production exports have been published yet

\- A development platform has no successful-run timestamp



\### warning



A condition that should be reviewed but does not invalidate the foundation.



Examples:



\- Platform path is not configured

\- Platform output is stale

\- Optional contract is missing

\- Checksum is not yet populated

\- Platform remains in inventory stage



\### error



A condition that invalidates part of the foundation or imported package.



Examples:



\- Required field is missing

\- Recommendation references an unknown asset

\- Registry references an unknown machine

\- Manifest record count does not match the file

\- A score is outside its allowed range



\### critical



A condition that makes continued processing unsafe.



Examples:



\- Integration database cannot be opened

\- Required schema is missing

\- Contract version is unsupported

\- Database corruption is detected

\- Duplicate imports create conflicting records



\## Exit Codes



Validation commands use:



\- `0` — validation passed

\- `1` — one or more errors or critical findings

\- `2` — command usage or required-resource failure

\- `3` — unexpected internal validation exception



Warnings alone do not produce a failing exit code.



\## Validation Result Structure



Each finding contains:



\- validation\_id

\- category

\- severity

\- platform\_id

\- run\_id

\- contract\_name

\- record\_identifier

\- message

\- suggested\_action



\## Foundation Certification



The Phase 0 foundation is certified when:



\- All required validation commands complete

\- No critical findings exist

\- No error findings exist

\- Warnings are documented and understood

\- The integration smoke test passes

\- The repository working tree is clean at the certification checkpoint

