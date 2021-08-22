#!/usr/bin/python3
'''
kybyz1 post
'''
POST = {
    'timestamp': {
        'input': 'eval',
        'code': [
            'from datetime import datetime, timezone',
            'datetime.now(timezone.utc).isoformat()'
        ],
    },
    'body': {
        'input': 'textarea',
    },
}
