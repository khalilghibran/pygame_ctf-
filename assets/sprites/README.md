# Production sprite overrides

Export transparent PNGs into this directory using the filenames from
`../../spec/assets_manifest.json`.

`SpriteLibrary` loads these files before its procedural fallbacks. Actor art
should use a consistent bottom-center pivot; tiles should be authored on the
manifest's 32×32 logical grid and can be scaled by the game at runtime.

The two PNGs in `../reference/` are visual-reference boards, not runtime
sprite sheets.
