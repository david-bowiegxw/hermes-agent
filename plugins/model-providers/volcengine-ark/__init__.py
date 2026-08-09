"""Volcengine Ark (火山引擎) — ByteDance unified model platform.

Ark is ByteDance's API gateway that gives access to models from multiple
vendors (doubao-seed, deepseek-v4, glm-5.2, kimi-k2, minimax-m3) through
a single API key.

The platform provides two subscription plans:
  - Agent Plan: General-purpose AI agent usage, AFP billing, multi-modal
  - Coding Plan: Coding-focused, token quotas, AI coding tools only

Both plans share the same Anthropic-compatible /api/coding endpoint.

IMPORTANT — model list maintenance:
  Ark's /models endpoint returns 124+ stale model IDs from the full
  platform catalog, not the user's actual subscription. This provider
  hardcodes the current Agent Plan text-generation model list and must
  be updated when Ark adds/removes models.

  Last updated: 2026-08-09 (12 models)

  Re-verified 2026-07-22: sent a live request to /api/coding for each of
  the 11 hardcoded IDs; all still respond 200. Volcengine's 2026-07-22
  account notice retires the legacy bare "Doubao-Seed-Code" model ID on
  2026-08-05 in favor of the Seed 2.0 lineup — this list already used
  the Seed 2.0 names (doubao-seed-2.0-pro/lite/mini/code) from day one,
  so the migration requires no change here.

  Re-verified 2026-08-09, after two more account notices (doubao-seed-2.1
  -turbo added; doubao-seed-2.0-pro/-code retiring 2026-08-08; kimi-k2.6
  and minimax-m2.7 retiring 2026-08-18). Live probe of every ID below:
  all 12 respond 200, including the four announced for retirement and the
  legacy "Doubao-Seed-Code" that was due to go on 2026-08-05.

  That gap is the reason retired IDs are annotated rather than deleted:
  Ark's announced retirement dates run ahead of the actual cutoff, and
  dropping an ID the gateway still serves would break working configs for
  no gain. The probe discriminates — an invented ID returns
  404 UnsupportedModel, so a 200 is a real answer, not a catch-all route.
"""

import logging
from typing import Any

from providers import register_provider
from providers.base import ProviderProfile

logger = logging.getLogger(__name__)

# ── Hardcoded model list (Agent Plan text generation, as of 2026-08-09) ──
# Ark's auto-discovery returns 124 stale models. We hardcode the actual
# working list to avoid confusion. Update when the provider's lineup changes.
#
# Prompt-caching on Ark's Anthropic /api/coding endpoint is per-model AND
# prefix-size-dependent (the hit shows up as usage.cache_read_input_tokens).
# Measured 2026-06-26 by sending an identical cached prefix twice per model
# at sizes 4k..64k tokens (doubao-seed-2.1-turbo measured the same way on
# 2026-08-09, with a per-run salt so a warm prefix from an earlier probe
# cannot read as a hit). Two caveats worth knowing:
#   - Each model has its own minimum cacheable prefix (4k..48k below).
#   - Hits are probabilistic, not guaranteed (Ark routes implicitly; a
#     supported model can miss on any given call). This diverges from
#     Anthropic's deterministic cache_control guarantee.
# So this is empirical and does NOT match Ark's /api/v3 implicit-cache docs.
#
# "retires YYYY-MM-DD" marks an ID Volcengine has announced for removal.
# Those stay listed until the gateway actually stops serving them (see the
# module docstring) — re-probe and delete once one starts returning 404.
_ARK_MODELS = [
    "deepseek-v4-flash",       # no cache (0 across 4k..64k)
    "deepseek-v4-pro",         # caches >= ~4k
    "glm-5.2",                 # caches >= ~4k
    "doubao-seed-2.1-turbo",   # caches >= ~4k (partial prefix: ~54% @4k, ~81% @8k)
    "doubao-seed-2.0-pro",     # caches only >= ~48k (high threshold); retires 2026-08-08
    "doubao-seed-2.0-lite",    # caches >= ~4k (flaky hit rate)
    "doubao-seed-2.0-mini",    # caches >= ~8k; dropped from the published plan list 2026-08
    "doubao-seed-2.0-code",    # caches >= ~8k; retires 2026-08-08
    "kimi-k2.7-code",          # caches >= ~4k
    "kimi-k2.6",               # no cache (0 across 4k..64k); retires 2026-08-18
    "minimax-m3",              # caches >= ~4k
    "minimax-m2.7",            # no cache (0 across 4k..64k); retires 2026-08-18
]


class VolcengineArkProfile(ProviderProfile):
    """Volcengine Ark — hardcoded model list to avoid stale auto-discovery."""

    def fetch_models(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 8.0,
    ) -> list[str] | None:
        """Return hardcoded model list.

        We intentionally skip the API call because Ark's /models endpoint
        returns 124+ stale model IDs from the full platform catalog rather
        than the user's actual subscription.
        """
        return list(_ARK_MODELS)


volcengine_ark = VolcengineArkProfile(
    name="volcengine-ark",
    aliases=(
        "ark",
        "volcengine",
        "volcano",
        "bytedance",
    ),
    display_name="Volcengine Ark (火山引擎)",
    description="ByteDance model platform — doubao-seed, deepseek-v4, glm-5.2, kimi-k2, minimax",
    signup_url="https://console.volcengine.com/ark/region:ark+cn-beijing/",
    api_mode="anthropic_messages",
    env_vars=("ARK_API_KEY",),
    base_url="https://ark.cn-beijing.volces.com/api/coding",
    auth_type="api_key",
    # Aux model runs high-frequency background tasks (titles, compression,
    # etc.) where a cached system/context prefix pays off. deepseek-v4-flash
    # is cheap but never caches on /api/coding (see _ARK_MODELS notes), so
    # every aux call re-bills the full prefix. doubao-seed-2.0-lite is the
    # cheapest model that DOES cache, and at the lowest prefix threshold
    # (~4k) — the best cost pick for aux. Swap back to a non-caching model
    # only if you specifically want flash's latency over cache savings.
    default_aux_model="doubao-seed-2.0-lite",
)

register_provider(volcengine_ark)
