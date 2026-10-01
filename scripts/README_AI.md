# Operations scripts

open_brain.py resolves configuration from the project, starts the existing user service,
and opens a token fragment URL. Do not print or commit the configured token.
watch_inbox.py supervises the optional sibling ingest CLI. It owns input movement,
retry metadata and collision-safe archives; parsing, embedding and database writes
remain the ingest project's responsibility. This script uses stdlib and python-dotenv.
