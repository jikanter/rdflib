"""
Push claude memory to neo4j using n8n as a middleman
"""
import httpx
import json
from json import JSONDecodeError
from pathlib import Path
from os import environ
import sys

if not 'CLAUDE_MEMORY' in environ or 'N8N_URL' not in environ:
    print('Please set CLAUDE_MEMORY and N8N_URL environment variables to the correct values before running this script')
    exit(1)

CLAUDE_MEMORY = Path(environ['CLAUDE_MEMORY'])
memoryJson = []
N8N_URL = environ['N8N_URL']

# json is in jsonl format, so read and parse linewise

with open(CLAUDE_MEMORY, 'r', encoding='utf-8') as fd:
    lines = fd.readlines()
    # load the linee
    for line in lines:
        try:
            o = json.loads(line)
            memoryJson.append(o)
        except JSONDecodeError as e:
            print(f'Error parsing line: {line}')
            print(e)
            sys.exit(2)

# create items from the two different types of nodes
finalPayload = {
    'entities': list(filter(lambda x: x.get('type') == 'entity', memoryJson)),
    'relations': list(filter(lambda x: x.get('type') == 'relation', memoryJson))
}

# Validate payload has data
if not finalPayload['entities'] and not finalPayload['relations']:
    print('Warning: No entities or relations found in memory file')
    sys.exit(0)

ENDPOINT_URL = f'{N8N_URL}/webhook/claude-memory-persist'
headers = {"Content-Type": "application/json"}


try:
    response = httpx.post(ENDPOINT_URL, headers=headers, json=finalPayload, timeout=30.0, verify=False)
    print(f"\nPushing claude memory to neo4j using n8n at {ENDPOINT_URL}...")
    response.raise_for_status()
    print("\n✅ Success!")
    print(json.dumps(response.json(), indent=2))
except httpx.HTTPError as e:
    print(f'\n❌ HTTP Error: {e}')
    if hasattr(e, 'response') and e.response is not None:
        print(f'Response: {e.response.text}')
    sys.exit(3)
except Exception as e:
    print(f'\n❌ Unexpected error: {e}')
    sys.exit(4)
