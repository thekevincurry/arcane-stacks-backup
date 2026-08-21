# Attempted local patch: html.py 403/cookie-refresh fix (REVERTED - does not work)

## The real bug (confirmed, still present upstream)
`_get_download_links_single_domain` in `downloader/html.py` does a plain
`d.session.get()` with no 403 handling. The sibling function in
`downloader/mirrors.py` (for external_mirror downloads) correctly retries via
`d.prewarm_cookies()` (FlareSolverr) on a 403 - html.py is missing the same
logic, which is why Anna's Archive lookups fail even with FlareSolverr
configured and enabled.

## Why the fix attempt failed
Tried bind-mounting a patched html.py over its path inside the container's
runtime PEX extraction cache (/tmp/pex/user_code/0/<hash>/stacks/downloader/html.py).
This broke the app entirely (ImportError: No module named stacks.main) - PEX
(the Python packaging format this app ships as) appears to do its own content
verification/extraction bookkeeping that a raw file swap inside its cache
directory violates, taking down module resolution for the whole app, not just
this one file. Reverted immediately; compose.yaml no longer references this.

## What would actually be needed to fix this properly
Either: (a) unpack the actual .pex archive, patch html.py inside it, and
repack it into a custom image built FROM zelest/stacks:latest, or (b) get
this fixed upstream in zelestcarlyone/stacks. html.py (in this same folder)
is the working patch content if either path is pursued later - it's just not
safe to apply via a runtime bind mount for a PEX-based app like this one.
