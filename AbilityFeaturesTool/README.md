# Ability Features Creator

A cross-platform Qt utility (built with PySide6) for browsing, templating and
editing `AbilityFeatures.txt` files used by Memoria-based Final Fantasy IX mods.

## Quick start

```bash
python -m pip install -r requirements.txt
python -m AbilityFeaturesTool.main
```

## Current capabilities

- Load an existing `AbilityFeatures.txt` and browse entries via the left pane.
- Choose between Support Ability (SA/Global) and Active Ability (AA/Global)
  contexts with helpful tooltips describing when to use each type.
- Inspect scopes (Permanent, Ability, Command, etc.) with descriptions lifted
  from the Memoria wiki, making it clearer where a hook executes.
- Drop in curated templates (tiered SA unlock, AA upgrade patches, etc.) that
  populate the editor pane ready for custom values.
- Replace an existing entry or append a brand new block without hand-editing the
  text file.

## Roadmap ideas

- Inline validation of placeholders and auto-populated field editors.
- Import/export of custom template packs so mod authors can share presets.
- Live preview diff before writing back to disk.
- Batch operations (e.g. generate an entire spell chain from a CSV sheet).

Contributions and pull requests are welcome!
