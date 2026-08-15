"""Process exit-code contract.

Values are stable CLI-boundary constants. Helpers must never call
``sys.exit``; the CLI boundary translates exceptions into these codes.
"""

SUCCESS = 0
USAGE_ERROR = 2
CONFIGURATION_ERROR = 3
ENVIRONMENT_ERROR = 4
INTERNAL_ERROR = 10
