#!/usr/bin/python3
'''
kybyz1 post
'''
from datetime import datetime, timezone

class Post():
    @property
    def timestamp(self):
        return datetime.now(timezone.utc).isoformat()
