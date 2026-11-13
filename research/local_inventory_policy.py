"""Explicit empty LOCAL custom-bag policy; no official inventory inference.

This builder neither imports nor replaces website data. Caller must separately
pin identity, correlate requests, preserve evidence, and enforce deployment
policy. No consumable/avatar success builder is provided.
"""
EMPTY_CUSTOM_BAGS_POLICY = 'local-empty-custom-bags-v1'


def empty_custom_bag_reply(*, policy):
    """Return218v0 with zero bags only for an explicitly selected local policy.

    Original handler expands these16 zero-count lists into zero valid bags,
    ten empty names/descriptions, and native club sentinel9999. Real database
    persistence and UI behavior remain live-verification boundaries.
    """
    if policy != EMPTY_CUSTOM_BAGS_POLICY:
        raise ValueError('Explicit local empty custom-bag policy required')
    return b'\x00\xda' + bytes(16)
