#!/usr/bin/env python3
"""Test script for parse_expand_fields_v2 function."""

import os
import sys
import django
from django.conf import settings

# Configure Django settings
if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='test-secret-key',
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
        ],
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        }
    )
    django.setup()

# Now import the function
from django_odata.utils import parse_expand_fields_v2
import json

# Test cases
tests = [
    ('Simple expansion', 'author'),
    ('Multiple expansions', 'author,categories'),
    ('Nested $select', 'author($select=name,email)'),
    ('Multiple query options', 'author($select=name;$filter=active eq true;$top=5)'),
    ('Complex nested', 'author($select=name;$expand=posts($top=3)),categories($filter=active eq true)'),
    ('All options', 'orders($filter=status eq \'pending\';$orderby=date desc;$top=10;$skip=5;$count=true)'),
]

print("Testing parse_expand_fields_v2 function")
print("=" * 80)

for name, test in tests:
    print(f"\n{name}:")
    print(f"Input:  {test}")
    result = parse_expand_fields_v2(test)
    print(f"Output: {json.dumps(result, indent=2)}")

print("\n" + "=" * 80)
print("All tests completed successfully!")