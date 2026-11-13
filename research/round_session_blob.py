"""Partial build-specific decoder for message31 SESSION_DATA (not its envelope).

Only original-code-proven field semantics are named. This module neither marks
rounds complete nor updates website or lifetime statistics.
"""
from dataclasses import dataclass
import struct

@dataclass(frozen=True)
class HoleSlot:
    index: int
    strokes: int
    par: int
    great_shot_points: int
    raw: bytes

    @property
    def score_relative_to_par(self):
        # Zero strokes is native empty-slot sentinel; do not invent a score.
        return self.strokes-self.par if self.strokes and self.par else None

@dataclass(frozen=True)
class SessionBlob:
    header: bytes
    holes: tuple[HoleSlot, ...]

    @property
    def full_18_score(self):
        scores=[h.score_relative_to_par for h in self.holes]
        return sum(scores) if all(s is not None for s in scores) else None


def decode_session_blob(blob: bytes) -> SessionBlob:
    if not isinstance(blob,bytes) or len(blob)!=444:
        raise ValueError('SESSION_DATA must be exactly444 bytes')
    holes=[]
    for i in range(18):
        raw=blob[12+i*24:12+(i+1)*24]
        holes.append(HoleSlot(i,raw[12],raw[14],struct.unpack_from('<I',raw,16)[0],raw))
    return SessionBlob(blob[:12],tuple(holes))
