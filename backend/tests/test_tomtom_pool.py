"""The shared pooled httpx client behind the TomTom integration (routing + tiles).

Reusing one client keeps TLS connections alive across the two routing calls and the many tile
fetches; here we just assert the pooling/lifecycle, no network.
"""

import asyncio

from app.integrations import tomtom


def test_shared_client_is_reused_and_recreated_after_close():
    async def go():
        await tomtom.aclose_shared_client()  # start clean
        c1 = tomtom._client()
        c2 = tomtom._client()
        assert c1 is c2  # same pooled client across calls
        assert not c1.is_closed

        await tomtom.aclose_shared_client()
        assert c1.is_closed  # closed on shutdown

        c3 = tomtom._client()
        assert c3 is not c1 and not c3.is_closed  # a fresh one is made on demand
        await tomtom.aclose_shared_client()

    asyncio.run(go())
