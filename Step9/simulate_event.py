"""Validate declared event before any hypothetical state transition."""
import json
from datetime import datetime
from pathlib import Path
import jsonschema


def load_event(payload,snapshot):
    event=payload['event']
    schema=json.loads((Path(__file__).parent/'schemas/event_schema.json').read_text())
    jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).validate(payload)
    if event['effective_date']!=snapshot or not event['simulated']:
        raise ValueError('Event must explicitly be simulated and contemporaneous with frozen snapshot')
    if datetime.fromisoformat(event['event_time'])<=datetime.fromisoformat(event['initial_recommendation_time']):
        raise ValueError('New event must happen AFTER first simulated recommendation')
    if event['event_time'][:10]!=snapshot or event['initial_recommendation_time'][:10]!=snapshot:
        raise ValueError('Only same-day replanning is supported by dated V2 model')
    return event
