"""
Model introspection utilities for SPECKIT-008: Auto-Generate OData Serializers.

This module provides utilities to extract comprehensive metadata from Django models,
including fields, relationships, and properties.
"""

import inspect
from dataclasses import dataclass
from typing import Any, Dict, List

from django.db import models


@dataclass
class FieldInfo:
    """Information about a model field."""

    name: str
    field_type: str
    is_relation: bool
    is_property: bool
    is_required: bool
    help_text: str = ""


@dataclass
class RelationshipInfo:
    """Information about a model relationship."""

    name: str
    related_model: str  # Full model path (app.Model)
    relation_type: str  # FK, M2M, O2O, REVERSE_FK, REVERSE_M2M, REVERSE_O2O
    is_many: bool
    related_name: str = ""


def get_model_fields(model_class) -> List[FieldInfo]:
    """
    Extract all fields from a Django model.

    Includes database fields, foreign keys, many-to-many, and one-to-one fields.
    Excludes auto-created reverse relations.

    Args:
        model_class: Django model class

    Returns:
        List of FieldInfo objects
    """
    fields = []

    for field in model_class._meta.get_fields():
        # Skip auto-created reverse relations
        if (
            field.many_to_one
            and not field.auto_created
            or field.one_to_one
            and not field.auto_created
        ):
            is_relation = True
        elif field.many_to_many:
            is_relation = True
        elif isinstance(field, models.Field):
            is_relation = False
        else:
            continue

        field_info = FieldInfo(
            name=field.name,
            field_type=field.__class__.__name__,
            is_relation=is_relation,
            is_property=False,
            is_required=not field.null and not field.blank
            if hasattr(field, "null")
            else False,
            help_text=getattr(field, "help_text", ""),
        )
        fields.append(field_info)

    return fields


def get_model_properties(model_class) -> List[str]:
    """
    Extract @property decorated methods from a Django model.

    Args:
        model_class: Django model class

    Returns:
        List of property names
    """
    properties = []

    for name, obj in inspect.getmembers(model_class):
        if isinstance(obj, property):
            properties.append(name)

    return properties


def get_model_relationships(model_class) -> List[RelationshipInfo]:
    """
    Extract all relationships from a Django model.

    Includes forward relationships (FK, M2M, O2O) and reverse relationships.

    Args:
        model_class: Django model class

    Returns:
        List of RelationshipInfo objects
    """
    from django.apps import apps

    relationships = []

    for field in model_class._meta.get_fields():
        # Forward relationships
        if isinstance(field, models.ForeignKey):
            # Get full app name from AppConfig
            app_config = apps.get_app_config(field.related_model._meta.app_label)
            related_model = f"{app_config.name}.{field.related_model.__name__}"
            rel_info = RelationshipInfo(
                name=field.name,
                related_model=related_model,
                relation_type="FK",
                is_many=False,
                related_name=field.related_model.__name__,
            )
            relationships.append(rel_info)

        elif isinstance(field, models.OneToOneField):
            # Get full app name from AppConfig
            app_config = apps.get_app_config(field.related_model._meta.app_label)
            related_model = f"{app_config.name}.{field.related_model.__name__}"
            rel_info = RelationshipInfo(
                name=field.name,
                related_model=related_model,
                relation_type="O2O",
                is_many=False,
                related_name=field.related_model.__name__,
            )
            relationships.append(rel_info)

        elif isinstance(field, models.ManyToManyField):
            # Get full app name from AppConfig
            app_config = apps.get_app_config(field.related_model._meta.app_label)
            related_model = f"{app_config.name}.{field.related_model.__name__}"
            rel_info = RelationshipInfo(
                name=field.name,
                related_model=related_model,
                relation_type="M2M",
                is_many=True,
                related_name=field.related_model.__name__,
            )
            relationships.append(rel_info)

        # Reverse relationships
        elif field.many_to_one and field.auto_created:
            # Get full app name from AppConfig
            app_config = apps.get_app_config(field.model._meta.app_label)
            related_model = f"{app_config.name}.{field.model.__name__}"
            rel_info = RelationshipInfo(
                name=field.get_accessor_name(),
                related_model=related_model,
                relation_type="REVERSE_FK",
                is_many=True,
                related_name=field.name,
            )
            relationships.append(rel_info)

        elif field.one_to_one and field.auto_created:
            # Get full app name from AppConfig
            app_config = apps.get_app_config(field.model._meta.app_label)
            related_model = f"{app_config.name}.{field.model.__name__}"
            rel_info = RelationshipInfo(
                name=field.get_accessor_name(),
                related_model=related_model,
                relation_type="REVERSE_O2O",
                is_many=False,
                related_name=field.name,
            )
            relationships.append(rel_info)

        elif isinstance(field, models.ManyToManyField) and field.auto_created:
            # Get full app name from AppConfig
            app_config = apps.get_app_config(field.model._meta.app_label)
            related_model = f"{app_config.name}.{field.model.__name__}"
            rel_info = RelationshipInfo(
                name=field.get_accessor_name(),
                related_model=related_model,
                relation_type="REVERSE_M2M",
                is_many=True,
                related_name=field.name,
            )
            relationships.append(rel_info)

    return relationships


def get_all_model_info(model_class) -> Dict[str, Any]:
    """
    Get comprehensive metadata for a Django model.

    Args:
        model_class: Django model class

    Returns:
        Dictionary with 'fields', 'relationships', and 'properties' keys
    """
    fields = get_model_fields(model_class)
    relationships = get_model_relationships(model_class)
    properties = get_model_properties(model_class)

    # Add properties to fields list
    for prop_name in properties:
        fields.append(
            FieldInfo(
                name=prop_name,
                field_type="property",
                is_relation=False,
                is_property=True,
                is_required=False,
                help_text="",
            )
        )

    return {
        "fields": fields,
        "relationships": relationships,
        "properties": properties,
    }
