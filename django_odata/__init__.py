"""
Django OData package for creating OData-inspired REST API endpoints.

This package combines drf-flex-fields and odata-query to provide:
- Dynamic field selection and expansion
- OData query parameter support ($filter, $orderby, $top, $skip, etc.)
- Automatic Django ORM query translation
- Extensible architecture for custom OData features
"""

from importlib import import_module
from typing import Any

__version__ = "0.1.1"
__author__ = "Muhammad Abdugafarov"

__all__ = [
    "ODataModelSerializer",
    "ODataSerializer",
    "ODataModelViewSet",
    "ODataViewSet",
    "ODataMixin",
    "ODataSerializerMixin",
    "apply_odata_query_params",
    "parse_odata_query",
]


_NAME_TO_MODULE = {
    # mixins
    "ODataMixin": "django_odata.mixins",
    "ODataSerializerMixin": "django_odata.mixins",
    # serializers
    "ODataModelSerializer": "django_odata.serializers",
    "ODataSerializer": "django_odata.serializers",
    # utils
    "apply_odata_query_params": "django_odata.utils",
    "parse_odata_query": "django_odata.utils",
    # viewsets
    "ODataModelViewSet": "django_odata.viewsets",
    "ODataViewSet": "django_odata.viewsets",
}


def __getattr__(name: str) -> Any:
    """
    Lazily resolve attributes from submodules to prevent importing Django/DRF
    at package import time. This helps avoid touching app models/settings
    before Django apps are ready.
    """
    if name in _NAME_TO_MODULE:
        module = import_module(_NAME_TO_MODULE[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(list(globals().keys()) + __all__)
