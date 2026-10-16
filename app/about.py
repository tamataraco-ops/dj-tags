"""Release metadata shown in the About dialog and sent in the MusicBrainz User-Agent.

Before publishing a build, replace AUTHOR and REPO_URL with real values
(build-release.ps1 refuses to build while the placeholders are still here).
"""

APP_NAME = "DJ Tags"
APP_ID = "dj-tags"  # used in the User-Agent
VERSION = "0.1.0"

AUTHOR = "たまたらこ"
REPO_URL = "https://github.com/tamataraco-ops/dj-tags"

COPYRIGHT_YEAR = "2026"

# MusicBrainz requires "Application/version ( contact )":
# https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting#Provide_meaningful_User-Agent_strings
USER_AGENT = f"{APP_ID}/{VERSION} ( {REPO_URL} )"
