# Contract Versioning Policy

## Version Format

Universal contracts use semantic versioning:

`MAJOR.MINOR.PATCH`

## Patch Change

Patch changes may:

- Correct documentation
- Clarify validation rules
- Add examples
- Correct nonfunctional metadata

Patch changes may not alter required fields or their meanings.

## Minor Change

Minor changes may:

- Add optional fields
- Add optional recommendation values
- Add new asset subclasses
- Add backward-compatible validation

Existing valid exports must remain valid.

## Major Change

Major changes may:

- Add required fields
- Remove fields
- Rename fields
- Change data types
- Change field meaning
- Change identifier rules

Major changes require explicit platform migration.

## Export Declaration

Every export must include:

- `contract_version`
- `platform_id`
- `run_id`

## Compatibility

The Universal Platform should support at least:

- The current major version
- The immediately preceding major version during migration

## Initial Version

The initial contract version is:

`1.0.0`