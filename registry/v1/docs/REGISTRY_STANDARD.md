\# Platform Registry Standard v1



\## Purpose



The Platform Registry is the machine-readable directory of all investment

intelligence systems connected or planned for connection to the Universal

Investment Intelligence Platform.



The registry describes platforms without requiring them to be running.



\## Registry Version



Current registry version:



`1.0.0`



\## Platform Status Vocabulary



\### operational



The platform's primary pipeline is working and its expected outputs are

available.



\### partially\_operational



Some important components work, but one or more known failures prevent full

operation.



\### development



The platform is actively being built and should not be treated as production

ready.



\### planning



The platform is defined conceptually but implementation has not started.



\### not\_started



No implementation currently exists.



\### blocked



Implementation or execution cannot continue because of a known dependency,

access limitation, missing source, or unresolved technical issue.



\### unavailable



The platform is expected to exist, but its files or machine are not currently

accessible.



\### archived



The platform is retained for historical purposes but is no longer actively

maintained.



\## Health Status Vocabulary



Health is calculated separately from the manually assigned platform status.



Allowed health statuses:



\- `healthy`

\- `warning`

\- `stale`

\- `unavailable`

\- `blocked`

\- `not\_configured`

\- `unknown`



\## Freshness



Each platform may define its expected refresh frequency.



Examples:



\- `daily`

\- `weekly`

\- `monthly`

\- `quarterly`

\- `manual`

\- `event\_driven`

\- `not\_applicable`



Freshness thresholds are expressed in hours.



A platform with no published output may still be operational if its registry

entry marks integration as not yet configured.



\## Machine Roles



Initial machine roles:



\- `primary\_workstation`

\- `secondary\_laptop`

\- `cloud\_worker`

\- `external\_service`

\- `not\_assigned`



\## Integration Stages



Allowed integration stages:



\- `not\_started`

\- `inventory`

\- `baseline\_frozen`

\- `documented`

\- `adapter\_development`

\- `export\_ready`

\- `registered`

\- `integrated`

\- `validated`

\- `production`



\## Contract Publication



The registry records which Universal Data Contracts each platform is expected

to publish.



Initial contract names:



\- `platform\_status`

\- `asset\_master`

\- `recommendations`

\- `forecasts`

\- `risk\_metrics`

\- `portfolio\_positions`

\- `macro\_signals`

\- `export\_manifest`



Multiple contracts are stored as pipe-delimited values in CSV files.



Example:



`platform\_status|asset\_master|recommendations|forecasts`



\## Path Rules



Local Windows paths may be stored during Phase 0.



Paths must:



\- Use absolute paths

\- Avoid credentials

\- Avoid network secrets

\- Point to folders rather than temporary files where practical



Future versions may support:



\- OneDrive paths

\- Network shares

\- Cloud object storage

\- APIs

\- Remote databases



\## Security



The registry must never contain:



\- Passwords

\- API keys

\- Authentication tokens

\- Private connection strings

\- Full personal financial records

