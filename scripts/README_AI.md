# Operations scripts

open_brain.py resolves configuration, starts the service, waits for readiness,
and reads the private owner credential before opening a token fragment URL. Do not print or commit the configured token.
watch_inbox.py supervises the bundled ingest CLI. It owns input movement,
retry metadata and collision-safe archives; parsing, embedding and database writes
remain the ingest component's responsibility. Source, private dotenv and durable
inbox locations are independently configurable. This script uses stdlib and python-dotenv.

setup_append_role.py is an owner-run provisioning command. Stop Bifröst before
rerunning it, since it rotates the private worker database password. It refuses
unowned existing roles and inherited destructive privileges. It never migrates or
changes knowledge rows. Credentials are written outside Git with mode 0600.
