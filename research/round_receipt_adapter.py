"""Durable LOCAL event receipt; never declares a completed round or wallet update.
Caller must explicitly enable only event shapes witnessed on its cabinet.
"""
from round_event_journal import inspect_round_events,DurableRoundEventJournal
from registration_fixture import frame_for
from reencoding_relay import body

def response(plain_request,identity,*,guard,journal,witnessed):
    events=inspect_round_events(body(plain_request),identity)
    if type(witnessed) is not frozenset or not witnessed:
        raise ValueError('Explicit witnessed event shapes required')
    if any((event.message,event.version,event.raw[0]&15) not in witnessed for event in events):
        raise ValueError('Event shape has not been witnessed')
    if not callable(guard) or not isinstance(journal,DurableRoundEventJournal):
        raise ValueError('Guard and durable round journal required')
    reply=frame_for(plain_request,b'\x04'*len(events))
    guard()
    journal.record(body(plain_request),identity)
    return reply
