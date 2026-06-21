"""Sound-based bird ID, intended to use Cornell Lab's open BirdNET model in place of the
closed Merlin Bird ID app (no third-party integration path exists for Merlin itself).

Not yet implemented: running BirdNET requires either self-hosting the BirdNET-Analyzer
model or calling a hosted inference service, which is a separate infrastructure decision
deferred to a later phase. This stub exists to fix the interface other code can build on.
"""


class BirdNetClient:
    async def identify_from_audio(self, audio: bytes) -> list[dict]:
        raise NotImplementedError("BirdNET inference is not wired up yet (see module docstring)")
