# RelayOps production boundary

Winback Ops is a local hackathon demo. Before processing real clinic data,
RelayOps must add: authenticated tenant workspaces; consent and suppression
records; encrypted storage with retention/deletion controls; immutable campaign
versions and approval events; date/identity confidence review queues; and a
container or managed worker that executes generated code with no network,
read-only inputs, constrained CPU/memory, and output-only storage.

`ALLOW_UNSAFE_LOCAL_SANDBOX` exists only for controlled development. It is not a
production control and must remain false in deployed environments.
