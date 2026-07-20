from stacksync_cdk import ModuleConfig

CONFIG = ModuleConfig(
    module_name="Create Records",
    module_description="Create one or more records of any object type.",
    # Set True if schema() fetches fields from your API (so /schema gets credentials).
    # requires_credentials_for_schema=True,
)
