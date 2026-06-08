# needle.pipeline — bulk persona bundler

Builds a deployable bundle for **every** persona in the library (495 personas). Personas
without a trained GGUF / visual / audio asset get `PlaceholderFactory` stand-ins and the
bundle is marked `untrained`. Bundles are written via
`needle.finetune.export.PersonaBundler` (manifest + 15–20 MB size target; placeholder
bundles are smaller).

## Usage

```bash
# Bundle all personas (placeholders for missing components):
python -m needle.pipeline.bulk_bundler --output needle/bundles/ --workers 4

# Only personas that have a trained GGUF (needs --trained-dir):
python -m needle.pipeline.bulk_bundler --trained-only --trained-dir path/to/gguf

# Dry run (report what would happen, write nothing):
python -m needle.pipeline.bulk_bundler --dry-run

# Catalog only (needle/bundles/catalog.json over all personas):
python -m needle.pipeline.bulk_bundler --catalog-only
```

## Outputs

```
needle/bundles/
├── .gitkeep
├── catalog.json          # committed — metadata for all personas (size, untrained, domain)
├── bundle_progress.json  # gitignored — checkpoint for resume
└── <persona_id>/         # gitignored — per-persona bundle (model + k_layer + visual + audio + manifest.json)
```

`bundle_all` is parallel (`ThreadPoolExecutor`), checkpointed (`bundle_progress.json`),
and resumable (existing bundles are skipped). Per-persona bundles are gitignored; only
`catalog.json` and `.gitkeep` are tracked.

## Notes

- **Untrained vs trained:** a persona is `untrained` until a real `{id}.gguf` exists under
  `--trained-dir`. Placeholder GGUFs are minimal-but-valid (magic + metadata, 0 tensors);
  placeholder visuals are 256×256 gray PNGs; placeholder audio is 1 s of silent WAV.
- **Torch-free:** the whole pipeline runs without torch / the `gguf` lib — only the *real*
  trained models (from `needle/finetune/`) need them.
