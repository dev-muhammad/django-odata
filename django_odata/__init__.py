"""
Django OData package for creating OData-inspired REST API endpoints.

This package combines drf-flex-fields and odata-query to provide:
- Dynamic field selection and expansion
- OData query parameter support ($filter, $orderby, $top, $skip, etc.)
- Automatic Django ORM query translation
- Extensible architecture for custom OData features
"""

__version__ = "0.1.0"
__author__ = "Your Name"

from .mixins import ODataMixin, ODataSerializerMixin
from .serializers import ODataModelSerializer, ODataSerializer
from .utils import apply_odata_query_params, parse_odata_query
from .viewsets import ODataModelViewSet, ODataViewSet

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
