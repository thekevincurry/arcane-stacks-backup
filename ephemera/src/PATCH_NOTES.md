# Local build notes

The official `ghcr.io/orwellianepilogue/ephemera` image (and the upstream
`bannert1337/ephemera` it's forked from) is no longer accessible via GHCR as
of 2026-08 — the original project appears to have been taken down. This is a
snapshot of the `main` branch of the fork at
https://github.com/Nsoromma/ephemera-book-downloader, built locally instead.

One patch applied to the Dockerfile: `corepack prepare pnpm@latest` was
changed to `pnpm@9` (both build stages). The lockfile is pnpm v9
(lockfileVersion 9.0), but the Dockerfile pinned `@latest`, which has since
moved to v10+ and dropped the `enable-pre-post-scripts` config key the build
script depends on — this broke the build with the unpatched Dockerfile.

Known issue in this app version: Settings page/API errors with
`SqliteError: no such column: "post_download_delete_temp"` — a genuine
schema/migration mismatch in the source, not something introduced here. Core
search/download functionality is unaffected.
