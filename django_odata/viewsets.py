"""
OData-compatible ViewSets that extend Django REST Framework functionality.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .mixins import ODataMixin
from .serializers import ODataModelSerializer


class ODataViewSet(ODataMixin, viewsets.ViewSet):
    """
    Base OData ViewSet that provides OData query support for non-model viewsets.

    This viewset provides:
    - OData query parameter parsing and application
    - OData-formatted responses
    - $metadata endpoint support
    - Service document endpoint support
    """

    def get_odata_entity_set_name(self) -> str:
        """
        Get the entity set name for this viewset.
        Override this method to provide custom entity set names.
        """
        if hasattr(self, "basename"):
            return self.basename
        return self.__class__.__name__.replace("ViewSet", "").lower() + "s"

    def get_odata_entity_type_name(self) -> str:
        """
        Get the entity type name for this viewset.
        Override this method to provide custom entity type names.
        """
        entity_set = self.get_odata_entity_set_name()
        return entity_set.rstrip("s").title()

    def list(self, request, *args, **kwargs):
        """
        Enhanced list method with OData collection formatting.
        """
        # Get base response from parent
        response = super().list(request, *args, **kwargs)

        # Wrap in OData collection format if needed
        if isinstance(response.data, list):
            odata_response = {
                "@odata.context": self._get_collection_context_url(),
                "value": response.data,
            }

            # Add count if requested
            odata_params = self.get_odata_query_params()
            if "$count" in odata_params and odata_params["$count"].lower() == "true":
                odata_response["@odata.count"] = len(response.data)

            response.data = odata_response

        return response

    def _get_collection_context_url(self) -> str:
        """Generate OData context URL for collections."""
        entity_set = self.get_odata_entity_set_name()
        base_url = self.request.build_absolute_uri("/odata/")
        return f"{base_url}$metadata#{entity_set}"


class ODataModelViewSet(ODataMixin, viewsets.ModelViewSet):
    """
    OData-compatible ModelViewSet that provides full CRUD operations with OData query support.

    This viewset provides:
    - All standard ModelViewSet functionality
    - OData query parameter support ($filter, $orderby, $top, $skip, etc.)
    - Dynamic field selection and expansion
    - OData-formatted responses with proper context
    - $metadata and service document endpoints
    """

    serializer_class = ODataModelSerializer

    def get_odata_entity_set_name(self) -> str:
        """
        Get the entity set name for this model.
        """
        if hasattr(self.get_serializer_class(), "Meta") and hasattr(
            self.get_serializer_class().Meta, "model"
        ):
            model = self.get_serializer_class().Meta.model
            return model.__name__.lower() + "s"
        return super().get_odata_entity_set_name()

    def get_odata_entity_type_name(self) -> str:
        """
        Get the entity type name for this model.
        """
        if hasattr(self.get_serializer_class(), "Meta") and hasattr(
            self.get_serializer_class().Meta, "model"
        ):
            model = self.get_serializer_class().Meta.model
            return model.__name__
        return super().get_odata_entity_type_name()

    def perform_create(self, serializer):
        """
        Enhanced create with OData support.
        """
        super().perform_create(serializer)

        # Add any OData-specific post-creation logic here
        # For example, handling of related entity creation

    def perform_update(self, serializer):
        """
        Enhanced update with OData support.
        """
        super().perform_update(serializer)

        # Add any OData-specific post-update logic here

    def create(self, request, *args, **kwargs):
        """
        Enhanced create method with OData response formatting.
        """
        response = super().create(request, *args, **kwargs)

        # Add OData context to created entity
        if response.status_code == status.HTTP_201_CREATED:
            entity_set = self.get_odata_entity_set_name()
            base_url = request.build_absolute_uri("/odata/")
            response.data["@odata.context"] = (
                f"{base_url}$metadata#{entity_set}/$entity"
            )

        return response

    def update(self, request, *args, **kwargs):
        """
        Enhanced update method with OData response formatting.
        """
        response = super().update(request, *args, **kwargs)

        # Add OData context to updated entity
        if response.status_code == status.HTTP_200_OK:
            entity_set = self.get_odata_entity_set_name()
            base_url = request.build_absolute_uri("/odata/")
            response.data["@odata.context"] = (
                f"{base_url}$metadata#{entity_set}/$entity"
            )

        return response

    @action(
        detail=True,
        methods=["get"],
        url_path=r"\$links/(?P<navigation_property>[\w-]+)",
    )
    def get_navigation_links(self, request, navigation_property=None, pk=None):
        """
        Get navigation property links for an entity.
        """
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)

            # Check if the navigation property exists
            nav_props = getattr(serializer, "get_navigation_properties", lambda: {})()
            if navigation_property not in nav_props:
                return Response(
                    {
                        "error": {
                            "code": "BadRequest",
                            "message": f'Navigation property "{navigation_property}" does not exist.',
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get the related objects
            if hasattr(instance, navigation_property):
                related_obj = getattr(instance, navigation_property)

                if related_obj is None:
                    links = {"value": []}
                elif hasattr(related_obj, "all"):  # Many-to-many or reverse foreign key
                    links = {
                        "value": [
                            {
                                "url": f"{request.build_absolute_uri().split('$')[0]}{obj.pk}"
                            }
                            for obj in related_obj.all()
                        ]
                    }
                else:  # Single related object
                    links = {
                        "value": [
                            {
                                "url": f"{request.build_absolute_uri().split('$')[0]}{related_obj.pk}"
                            }
                        ]
                    }

                return Response(links)
            else:
                return Response(
                    {
                        "error": {
                            "code": "BadRequest",
                            "message": f'Navigation property "{navigation_property}" is not accessible.',
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response(
                {"error": {"code": "InternalError", "message": str(e)}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"], url_path=r"(?P<navigation_property>[\w-]+)")
    def get_navigation_property(self, request, navigation_property=None, pk=None):
        """
        Get navigation property values for an entity.
        """
        try:
            instance = self.get_object()

            # Check if the navigation property exists
            if not hasattr(instance, navigation_property):
                return Response(
                    {
                        "error": {
                            "code": "BadRequest",
                            "message": f'Navigation property "{navigation_property}" does not exist.',
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            related_obj = getattr(instance, navigation_property)

            if related_obj is None:
                return Response(None, status=status.HTTP_204_NO_CONTENT)
            elif hasattr(related_obj, "all"):  # QuerySet or related manager
                # Apply OData query parameters to the related queryset
                queryset = self.apply_odata_query(related_obj.all())

                # Get appropriate serializer for the related model
                related_serializer_class = self._get_related_serializer_class(
                    navigation_property
                )
                if related_serializer_class:
                    serializer = related_serializer_class(
                        queryset, many=True, context=self.get_serializer_context()
                    )
                    return Response(
                        {
                            "@odata.context": f"{request.build_absolute_uri('/odata/')}$metadata#{navigation_property}",
                            "value": serializer.data,
                        }
                    )
                else:
                    # Fallback to basic serialization
                    return Response(
                        {
                            "@odata.context": f"{request.build_absolute_uri('/odata/')}$metadata#{navigation_property}",
                            "value": list(queryset.values()),
                        }
                    )
            else:  # Single related object
                related_serializer_class = self._get_related_serializer_class(
                    navigation_property
                )
                if related_serializer_class:
                    serializer = related_serializer_class(
                        related_obj, context=self.get_serializer_context()
                    )
                    data = serializer.data
                    data["@odata.context"] = (
                        f"{request.build_absolute_uri('/odata/')}$metadata#{navigation_property}/$entity"
                    )
                    return Response(data)
                else:
                    # Fallback to basic serialization
                    return Response(
                        {
                            "@odata.context": (
                                f"{request.build_absolute_uri('/odata/')}"
                                f"$metadata#{navigation_property}/$entity"
                            ),
                            **{
                                field.name: getattr(related_obj, field.name)
                                for field in related_obj._meta.fields
                            },
                        }
                    )

        except Exception as e:
            return Response(
                {"error": {"code": "InternalError", "message": str(e)}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _get_related_serializer_class(self, navigation_property):
        """
        Get the serializer class for a navigation property.
        """
        serializer = self.get_serializer()
        if hasattr(serializer, "Meta") and hasattr(
            serializer.Meta, "expandable_fields"
        ):
            expandable_fields = serializer.Meta.expandable_fields
            if navigation_property in expandable_fields:
                config = expandable_fields[navigation_property]
                if isinstance(config, tuple) and len(config) > 0:
                    # Try to import the serializer class
                    serializer_path = config[0]
                    try:
                        module_path, class_name = serializer_path.rsplit(".", 1)
                        module = __import__(module_path, fromlist=[class_name])
                        return getattr(module, class_name)
                    except (ImportError, AttributeError):
                        pass
        return None


class ODataReadOnlyModelViewSet(ODataMixin, viewsets.ReadOnlyModelViewSet):
    """
    OData-compatible ReadOnlyModelViewSet for read-only entity sets.

    This viewset provides:
    - Read-only access to model instances
    - OData query parameter support
    - Dynamic field selection and expansion
    - OData-formatted responses
    """

    serializer_class = ODataModelSerializer

    def get_odata_entity_set_name(self) -> str:
        """Get the entity set name for this model."""
        if hasattr(self.get_serializer_class(), "Meta") and hasattr(
            self.get_serializer_class().Meta, "model"
        ):
            model = self.get_serializer_class().Meta.model
            return model.__name__.lower() + "s"
        return self.__class__.__name__.replace("ViewSet", "").lower() + "s"

    def get_odata_entity_type_name(self) -> str:
        """Get the entity type name for this model."""
        if hasattr(self.get_serializer_class(), "Meta") and hasattr(
            self.get_serializer_class().Meta, "model"
        ):
            model = self.get_serializer_class().Meta.model
            return model.__name__
        return self.__class__.__name__.replace("ViewSet", "").title()


# Convenience function for creating OData viewsets
def create_odata_viewset(model_class, serializer_class=None, read_only=False, **kwargs):
    """
    Factory function to create OData viewsets for Django models.

    Args:
        model_class: Django model class
        serializer_class: Optional custom serializer class
        read_only: If True, creates a ReadOnlyModelViewSet
        **kwargs: Additional viewset options

    Returns:
        ODataModelViewSet or ODataReadOnlyModelViewSet subclass
    """
    base_class = ODataReadOnlyModelViewSet if read_only else ODataModelViewSet

    class_attrs = {
        "queryset": model_class.objects.all(),
    }

    if serializer_class:
        class_attrs["serializer_class"] = serializer_class

    # Add any additional attributes
    class_attrs.update(kwargs)

    # Create the viewset class
    viewset_name = f"{model_class.__name__}ODataViewSet"
    viewset_class = type(viewset_name, (base_class,), class_attrs)

    return viewset_class
