"""
setup_secrets.py  (OPTIONAL)
----------------------------
Only needed if you switch from Open-Meteo (keyless) to a provider that requires
an API key, e.g. WeatherAPI.com. Open-Meteo needs NO secrets, so you can skip
this file entirely for the default build.

Run once from a Databricks notebook or terminal in your workspace:

    python setup_secrets.py

It prompts (via getpass, so nothing is echoed or written to shell history)
for your weather API key and stores it as the Databricks secret:

    scope = "weather"   key = "api-key"

Read it back at runtime in weather_broker.py with:

    _secret("weather", "api-key")

This mirrors the setup_secrets.py / _secret() pattern in the reference repo.
Never hardcode a key or commit it to git.
"""

from getpass import getpass

from databricks.sdk import WorkspaceClient

SCOPE = "weather"
KEY = "api-key"


def main() -> None:
    w = WorkspaceClient()

    # Create the scope if it does not already exist.
    existing = {s.name for s in w.secrets.list_scopes()}
    if SCOPE not in existing:
        w.secrets.create_scope(scope=SCOPE)
        print(f"Created secret scope: {SCOPE}")
    else:
        print(f"Secret scope already exists: {SCOPE}")

    api_key = getpass("Enter your weather API key: ").strip()
    if not api_key:
        raise SystemExit("No key entered. Aborting.")

    w.secrets.put_secret(scope=SCOPE, key=KEY, string_value=api_key)
    print(f"Stored secret {SCOPE}/{KEY}. Do not commit this key to git.")


if __name__ == "__main__":
    main()
