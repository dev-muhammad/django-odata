"""
Code generator for SPECKIT-008: Auto-Generate OData Serializers.

This module provides utilities to generate syntactically valid Python serializer code
from model metadata.
"""

import ast
from datetime import datetime
from typing import List, Set, Tuple

from .introspection import FieldInfo, RelationshipInfo


def generate_imports(model_class, app_label: str) -> str:
    """
    Generate import statements for the serializer.

    Args:
        model_class: Django model class
        app_label: App label for the model

    Returns:
        String containing import statements
    """
    model_name = model_class.__name__
    model_app_label = model_class._meta.app_label

    imports = ["from django_odata.serializers import ODataModelSerializer"]

    # Import model using Django's lazy loading
    if model_app_label == app_label:
        imports.append(f"from django.apps import apps")
        imports.append(f"{model_name} = apps.get_model('{model_app_label}', '{model_name}')")
    else:
        imports.append(f"from django.apps import apps")
        imports.append(f"{model_name} = apps.get_model('{model_app_label}', '{model_name}')")

    return "\n".join(imports)


def generate_regeneration_command(app_label: str, model_name: str, single: bool = False) -> str:
    """
    Generate appropriate regeneration command based on context.
    
    Args:
        app_label: App label for the model
        model_name: Model name
        single: Whether the file was generated with --single option
        
    Returns:
        String containing the regeneration command
    """
    base_cmd = f"python manage.py generate_odata_serializer {app_label}.{model_name}"
    if single:
        base_cmd += " --single"
    return base_cmd


def generate_fields_list(fields: List[FieldInfo]) -> str:
    """
    Generate the fields list for Meta class.

    Args:
        fields: List of FieldInfo objects

    Returns:
        String containing Python list with proper indentation
    """
    field_lines = []
    for field in fields:
        if field.is_property:
            field_lines.append(f'            "{field.name}",  # @property')
        else:
            field_lines.append(f'            "{field.name}",')

    fields_str = "[\n" + "\n".join(field_lines) + "\n        ]"
    return fields_str


def generate_expandable_fields(
    relationships: List[RelationshipInfo],
    app_label: str,
    exclude_edges: Set[Tuple[str, str]],
    models_in_file: Set[str] = None,
) -> str:
    """
    Generate the expandable_fields dict for Meta class.

    Args:
        relationships: List of RelationshipInfo objects
        app_label: App label for the model
        exclude_edges: Set of edges to exclude from expandable_fields
        models_in_file: Set of model paths being generated in the same file (for single mode)

    Returns:
        String containing Python dict with proper indentation
    """
    if not relationships:
        return "{}"

    if models_in_file is None:
        models_in_file = set()

    expandable_lines = ["{"]

    for rel in relationships:
        # Check if this relationship should be excluded
        model_path = f"{app_label}.{rel.related_model.split('.')[-1]}"
        if (model_path, rel.related_model) in exclude_edges:
            continue

        # Extract serializer name and app path from related model
        related_model_name = rel.related_model.split(".")[-1]
        serializer_name = f"{related_model_name}Serializer"

        # Determine the serializer path
        # If in single mode and the related model is in the same file, use the current app
        # Otherwise, use the related model's app
        if rel.related_model in models_in_file:
            # Related model is in the same file, so serializer is in current app
            serializer_path = f"{app_label}.serializers.{serializer_name}"
        else:
            # Related model is external, use its app path
            related_app_parts = rel.related_model.split(".")[:-1]
            related_app = ".".join(related_app_parts)
            serializer_path = f"{related_app}.serializers.{serializer_name}"

        # Always use string path with full app name
        # This avoids circular reference issues with class definitions
        if rel.is_many:
            expandable_lines.append(
                f'            "{rel.name}": ("{serializer_path}", {{"many": True}}),'
            )
        else:
            expandable_lines.append(
                f'            "{rel.name}": ("{serializer_path}", {{}}),'
            )

    expandable_lines.append("        }")
    return "\n".join(expandable_lines)


def generate_serializer_class(
    model_class,
    app_label: str,
    fields: List[FieldInfo],
    relationships: List[RelationshipInfo],
    exclude_edges: Set[Tuple[str, str]],
    single: bool = False,
    models_in_file: Set[str] = None,
) -> str:
    """
    Generate complete serializer class code.

    Args:
        model_class: Django model class
        app_label: App label for the model
        fields: List of FieldInfo objects
        relationships: List of RelationshipInfo objects
        exclude_edges: Set of edges to exclude
        single: Whether the file was generated with --single option
        models_in_file: Set of model paths being generated in the same file

    Returns:
        String containing complete serializer class definition
    """
    model_name = model_class.__name__
    serializer_name = f"{model_name}Serializer"

    # Generate docstring with metadata
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    regeneration_cmd = generate_regeneration_command(app_label, model_name, single)

    docstring = f'''"""
Auto-generated OData serializer for {model_name} model.
Generated on: {now}

DO NOT EDIT THIS FILE MANUALLY.
Regenerate using: {regeneration_cmd}

Available options:
  --single   Generate one combined file instead of separate files
  --force    Overwrite existing files without prompting
"""
'''

    # Generate imports
    imports = generate_imports(model_class, app_label)

    # Generate fields list
    fields_list = generate_fields_list(fields)

    # Generate expandable fields
    expandable_fields = generate_expandable_fields(
        relationships, app_label, exclude_edges, models_in_file
    )

    # Combine into class definition
    class_code = f'''
class {serializer_name}(ODataModelSerializer):
    """OData serializer for {model_name} model."""

    class Meta:
        model = {model_name}
        fields = {fields_list}
        expandable_fields = {expandable_fields}
'''

    # Combine everything
    full_code = f"{docstring}\n{imports}\n{class_code}"
    return full_code


def format_python_code(code: str) -> str:
    """
    Format and validate Python code.

    Args:
        code: Python code string

    Returns:
        Formatted Python code

    Raises:
        SyntaxError: If code is not valid Python
    """
    # Validate syntax
    try:
        ast.parse(code)
    except SyntaxError as e:
        raise SyntaxError(f"Generated code has syntax error: {e}")

    return code
