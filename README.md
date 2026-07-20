# stacksync-workflows-cdk

The **Workflows CDK** — the package and assets a Stacksync workflow connector is built from.
It is driven by the `stacksync` CLI (repo: `stacksync-cli`); connector developers do not
use this repo directly.

## Layout

```
lib/                  The importable package (installed into the connector).
  stacksync_cdk/
    app.py              create_app() — discovers modules and registers routes
    request.py          Request — typed view of the incoming payload
    credentials.py      Credentials — typed connection credentials
    responses.py        SchemaResponse / ContentResponse / ExecuteResponse / Response
    errors.py           ManagedError
    module_config.py    ModuleConfig — per-module capability flags
    validation.py       JSON-string input coercion helpers
templates/            The scaffold the CLI copies for `stacksync connector create`.
  connector/            stacksync.yml, main.py, modules/, guide/, Dockerfile.
```

## How the pieces are used

| Piece | Delivery | Where it runs |
|---|---|---|
| `lib/stacksync_cdk` (incl. the `app.py` router) | **imported** (pip, via the connector's `requirements.txt`) | inside the connector |
| a 3-line `main.py` (`from stacksync_cdk.app import create_app`) | **injected** into `.stacksync_build/` at build time | inside the connector |
| `templates/connector` | **copied** into the new repo by `stacksync connector create` | the developer's machine |

The router is no longer a separate injected file — it ships inside the package, so a
new cdk release updates the router the moment a connector reinstalls the lib.

## Versioning

The CDK is versioned with **git refs** (no PyPI). A connector picks a version with the
one CDK line in its `requirements.txt`, or with `stacksync connector cdk <ref>`:

| Ref | Meaning |
|---|---|
| `@v1` | latest v1.x — non-breaking updates, shielded from v2 (the template default) |
| `@v1.0.0` | an exact release, fully reproducible (like `pandas==1.0.0`) |
| `@v2` | the next major, when you're ready to migrate |
| `@prod` | bleeding edge (latest of everything) |

Cutting a release (git only) — bump `lib/pyproject.toml` `version`, then:

```
git tag v1.0.0 && git push origin v1.0.0     # an exact, immutable release
git branch v1  && git push origin v1         # the rolling v1.x line (updated with patches)
```

`stacksync connector run` prints the installed version and the ref you track, and
force-refreshes **rolling** refs (`@prod` / `@v1`) so updates land automatically; **exact
pins** (`@v1.0.0`) stay put. Deployed connectors update on their next `deploy` (fresh build).

## License

See [LICENSE](LICENSE) — Stacksync Connector Development Kit License (Source Available 1.0),
current terms at
https://docs.stacksync.com/security-and-other-resources/legal/stacksync-connector-development-kit-license
