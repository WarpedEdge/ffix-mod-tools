# Battle SFX Creator

A Qt-based companion tool for browsing, templating, and editing battle
special-effect sequences used by Memoria-based Final Fantasy IX mods.

## Quick start

```bash
python -m pip install -r requirements.txt
python -m BattleSFXCreator.main
```

## Feature overview

- Load an `StreamingAssets/Data/SpecialEffects` directory and inspect every
  `ef####` folder and `.seq` file in a tree view.
- Edit `Sequence.seq` / `PlayerSequence.seq` files directly with dirty-state
  tracking and quick save/revert buttons.
- Right-click to rename folders or sequence files with undo support to recover
  from mistakes.
- Browse curated templates grouped by category and insert them straight into the
  editor.
- Import/export additional template packs as JSON files so modders can share
  presets.
- Built-in help popups that mirror the Memoria wiki reference for instruction
  syntax and argument types, plus quick links out to the full documentation.

Contributions and suggestions are welcome!
