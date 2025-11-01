"""
Django management command for SPECKIT-008: Auto-Generate OData Serializers.

Usage:
    python manage.py generate_odata_serializer blog.BlogPost
    python manage.py generate_odata_serializer --app blog
    python manage.py generate_odata_serializer --app blog --single
    python manage.py generate_odata_serializer --app blog --single --force

Options:
    --single   Generate one combined file instead of separate files per model
    --force    Overwrite existing files without prompting for confirmation
    --output   Specify custom output directory for generated serializers
"""

import re
from pathlib import Path
from typing import Dict

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from django_odata.code_generator import (
    format_python_code,
    generate_serializer_class,
)
from django_odata.dependency_detector import (
    build_relationship_graph,
    detect_cycles,
    resolve_circular_dependencies,
    should_include_relationship,
)
from django_odata.introspection import get_all_model_info


class Command(BaseCommand):
    """Management command to auto-generate OData serializers from Django models."""

    help = "Auto-generate ODataModelSerializer subclasses from Django models"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "models",
            nargs="*",
            help="Model paths in format app_label.ModelName (e.g., blog.BlogPost)",
        )
        parser.add_argument(
            "--app",
            action="append",
            dest="apps",
            help="Generate serializers for all models in specified app",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing files without prompting",
        )
        parser.add_argument(
            "--single",
            action="store_true",
            help="Generate one combined file instead of separate files",
        )
        parser.add_argument(
            "--output",
            type=str,
            help="Custom output directory for generated serializers",
        )

    def handle(self, *args, **options):
        """Main command handler."""
        models_to_generate = []
        output_dir = None

        # Discover models
        if options.get("apps"):
            for app_label in options["apps"]:
                try:
                    app_config = apps.get_app_config(app_label)
                    models_to_generate.extend(app_config.get_models())
                    if not output_dir:
                        # Default output directory is app's serializers folder
                        app_path = Path(app_config.module.__file__).parent
                        output_dir = app_path / "serializers"
                except LookupError:
                    raise CommandError(f"App '{app_label}' not found")
        elif options.get("models"):
            for model_path in options["models"]:
                model = self._load_model_from_path(model_path)
                models_to_generate.append(model)
                if not output_dir:
                    # Default output directory is app's serializers folder
                    app_label = model._meta.app_label
                    app_config = apps.get_app_config(app_label)
                    app_path = Path(app_config.module.__file__).parent
                    output_dir = app_path / "serializers"
        else:
            raise CommandError(
                "Please specify models or use --app flag to specify an app"
            )

        # Override output directory if specified
        if options.get("output"):
            output_dir = Path(options["output"])

        # Remove duplicates
        models_to_generate = list(set(models_to_generate))

        # If using --single, discover all related models for expandable_fields
        if options.get("single", False):
            models_to_generate = self._discover_related_models(models_to_generate)

        self.stdout.write(
            self.style.SUCCESS(
                f"Generating serializers for {len(models_to_generate)} model(s)..."
            )
        )

        # Get model info
        all_model_info = {}
        relationships_map = {}

        for model in models_to_generate:
            model_path = f"{model._meta.app_label}.{model.__name__}"
            info = get_all_model_info(model)
            all_model_info[model_path] = {
                "model": model,
                "info": info,
            }
            relationships_map[model_path] = info["relationships"]

        # Detect circular dependencies
        graph = build_relationship_graph(models_to_generate, relationships_map)
        cycles = detect_cycles(graph)
        excluded_edges = resolve_circular_dependencies(cycles)

        if cycles:
            self.stdout.write(
                self.style.WARNING(
                    f"Detected {len(cycles)} circular dependenc(ies). Will skip some reverse relationships."
                )
            )
            for cycle in cycles:
                self.stdout.write(
                    self.style.WARNING(f"  Cycle: {' -> '.join(cycle.cycle)}")
                )

        # Generate serializers
        serializer_codes = {}
        # In single mode, collect all model paths being generated for direct references
        # We need both the short path (auth.User) and full path (django.contrib.auth.User)
        models_in_file = set()
        if options.get("single", False):
            for model_path, model_data in all_model_info.items():
                app_config = apps.get_app_config(model_data["model"]._meta.app_label)
                full_path = f"{app_config.name}.{model_data['model'].__name__}"
                models_in_file.add(full_path)  # Add full path

        for model_path, model_data in all_model_info.items():
            model = model_data["model"]
            info = model_data["info"]
            # Get the full app name from AppConfig instead of just app_label
            app_config = apps.get_app_config(model._meta.app_label)
            app_label = app_config.name

            # Filter relationships to exclude circular ones
            filtered_relationships = [
                rel
                for rel in info["relationships"]
                if should_include_relationship(
                    model_path, rel.related_model, excluded_edges
                )
            ]

            code = generate_serializer_class(
                model,
                app_label,
                info["fields"],
                filtered_relationships,
                excluded_edges,
                single=options.get("single", False),
                models_in_file=models_in_file,
            )
            code = format_python_code(code)
            serializer_codes[model_path] = code

        # Write files
        self._write_serializer_files(
            serializer_codes,
            output_dir,
            single=options.get("single", False),
            force=options.get("force", False),
            requested_options=options,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully generated {len(serializer_codes)} serializer(s) in {output_dir}"
            )
        )

    def _load_model_from_path(self, model_path: str):
        """Load a Django model from app_label.ModelName format.

        Args:
            model_path: Model path like 'blog.BlogPost'

        Returns:
            Django model class

        Raises:
            CommandError: If model not found
        """
        try:
            app_label, model_name = model_path.split(".")
            model = apps.get_model(app_label, model_name)
            return model
        except (ValueError, LookupError):
            raise CommandError(f"Model '{model_path}' not found")

    def _write_serializer_files(
        self,
        serializer_codes: Dict[str, str],
        output_dir: Path,
        single: bool,
        force: bool,
        requested_options=None,
    ):
        """Write serializer code to files.

        Args:
            serializer_codes: Dict mapping model paths to serializer code
            output_dir: Output directory path
            single: Whether to combine all serializers into one file
            force: Whether to overwrite existing files without prompting
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        primary_model_name = None

        if single:
            # Determine primary app from output directory (e.g., 'blog' from '/path/blog/serializers')
            primary_app = output_dir.parent.name

            # Combine all serializers into one file with deduplicated imports
            combined_code = self._combine_serializers(serializer_codes, primary_app)

            # Use the originally requested model name for the filename
            # Find the model that was originally requested (not discovered)
            requested_model_name = None
            if requested_options.get("models"):
                # Get the first requested model
                requested_model_path = requested_options["models"][0]
                requested_model_name = requested_model_path.split(".")[-1]
            elif requested_options.get("apps"):
                # If using --app, use the first model from the first app
                app_label = requested_options["apps"][0]
                try:
                    app_config = apps.get_app_config(app_label)
                    first_model = app_config.get_models()[0]
                    requested_model_name = first_model.__name__
                except (LookupError, IndexError):
                    requested_model_name = None

            if requested_model_name:
                file_name = self._camel_to_snake(requested_model_name) + ".py"
            else:
                # Fallback to first model in dict
                first_model_path = next(iter(serializer_codes.keys()))
                primary_model_name = first_model_path.split(".")[-1]
                file_name = self._camel_to_snake(primary_model_name) + ".py"

            output_file = output_dir / file_name

            self._write_file_with_overwrite_check(output_file, combined_code, force)
        else:
            # Write one file per model
            for model_path, code in serializer_codes.items():
                model_name = model_path.split(".")[-1]
                # Convert CamelCase to snake_case
                file_name = self._camel_to_snake(model_name) + ".py"
                output_file = output_dir / file_name
                self._write_file_with_overwrite_check(output_file, code, force)

        # Generate __init__.py
        if single:
            # For single mode, pass the actual filename used (without .py extension)
            actual_filename = file_name[:-3]  # Remove .py extension
            self._generate_init_file(
                output_dir, serializer_codes.keys(), single, actual_filename
            )
        else:
            self._generate_init_file(output_dir, serializer_codes.keys(), single, None)

    def _write_file_with_overwrite_check(
        self, output_file: Path, content: str, force: bool
    ):
        """Write file with overwrite check unless force is True.

        Args:
            output_file: Path to the output file
            content: Content to write
            force: Whether to overwrite without prompting
        """
        if output_file.exists() and not force:
            response = input(f"File {output_file} already exists. Overwrite? [y/N]: ")
            if response.lower() not in ("y", "yes"):
                self.stdout.write(self.style.WARNING(f"  Skipped {output_file}"))
                return

        output_file.write_text(content)
        self.stdout.write(self.style.SUCCESS(f"  Written to {output_file}"))

    def _generate_init_file(
        self, output_dir: Path, model_paths, single: bool, primary_model_name=None
    ):
        """Generate __init__.py with imports.

        Args:
            output_dir: Output directory path
            model_paths: Iterable of model paths
            single: Whether serializers are combined into one file
            primary_model_name: Primary model name for single file naming
        """
        imports = []

        if single:
            # Import all serializers from the primary model file
            primary_file_name = (
                primary_model_name if primary_model_name else "blog_post"
            )
            for model_path in model_paths:
                model_name = model_path.split(".")[-1]
                serializer_name = f"{model_name}Serializer"
                imports.append(f"from .{primary_file_name} import {serializer_name}")
        else:
            # Import each serializer from its own file
            for model_path in model_paths:
                model_name = model_path.split(".")[-1]
                serializer_name = f"{model_name}Serializer"
                file_name = self._camel_to_snake(model_name)
                imports.append(f"from .{file_name} import {serializer_name}")

        init_file = output_dir / "__init__.py"
        init_file.write_text("\n".join(imports) + "\n")

    @staticmethod
    def _camel_to_snake(name: str) -> str:
        """Convert CamelCase to snake_case.

        Args:
            name: CamelCase string

        Returns:
            snake_case string
        """
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    def _discover_related_models(self, initial_models: list) -> list:
        """Discover all related models needed for expandable_fields when using --single.

        Args:
            initial_models: List of initially requested models

        Returns:
            List of models including all related models for expandable_fields
        """
        discovered_models = set(initial_models)
        models_to_process = list(initial_models)

        while models_to_process:
            current_model = models_to_process.pop(0)

            # Get model info to find relationships
            model_info = get_all_model_info(current_model)

            for relationship in model_info["relationships"]:
                # Parse the related model path
                try:
                    # Split and get the model name (last part) and app name (everything before)
                    parts = relationship.related_model.split(".")
                    related_model_name = parts[-1]
                    related_app_name = ".".join(parts[:-1])

                    # To get the model, we need the app_label (e.g., 'blog'), not the full app name (e.g., 'example.blog')
                    # Try with the full name first, then fall back to just the last part
                    try:
                        related_model = apps.get_model(
                            related_app_name, related_model_name
                        )
                    except LookupError:
                        # If that fails, try with just the app_label (last part of the app name)
                        related_app_label = parts[-2] if len(parts) > 1 else parts[0]
                        related_model = apps.get_model(
                            related_app_label, related_model_name
                        )

                    # If this is a new model, add it to be processed
                    if related_model not in discovered_models:
                        discovered_models.add(related_model)
                        models_to_process.append(related_model)

                except (ValueError, LookupError) as e:
                    # Skip if related model cannot be found
                    self.stdout.write(
                        self.style.WARNING(
                            f"Could not load related model {relationship.related_model}: {e}"
                        )
                    )
                    continue

        self.stdout.write(
            self.style.SUCCESS(
                f"Discovered {len(discovered_models) - len(initial_models)} additional related model(s) for --single mode"
            )
        )

        return list(discovered_models)

    def _combine_serializers(
        self, serializer_codes: Dict[str, str], primary_app: str
    ) -> str:
        """Combine multiple serializer codes into one file with deduplicated imports.

        Args:
            serializer_codes: Dict mapping model paths to serializer code

        Returns:
            Combined serializer code with single header and deduplicated imports
        """
        imports = set()
        class_definitions = []

        # Collect all the models
        model_info = {}

        for model_path in serializer_codes.keys():
            app_label, model_name = model_path.split(".")
            model_info[model_path] = {"app_label": app_label, "model_name": model_name}

        # Generate imports based on each model's actual app
        imports.add("from django_odata.serializers import ODataModelSerializer")

        # Import ALL models that have serializers being generated
        for model_path, info in model_info.items():
            model_app = info["app_label"]
            model_name = info["model_name"]

            if model_app == primary_app:
                # Use relative imports for same app
                imports.add(f"from ..models import {model_name}")
            else:
                # Use absolute imports for different apps
                # Map Django built-in apps to their full module paths
                app_module_map = {
                    "auth": "django.contrib.auth",
                    "contenttypes": "django.contrib.contenttypes",
                    "sessions": "django.contrib.sessions",
                    "messages": "django.contrib.messages",
                    "admin": "django.contrib.admin",
                    "sites": "django.contrib.sites",
                }
                full_app_path = app_module_map.get(model_app, model_app)
                imports.add(f"from {full_app_path}.models import {model_name}")

        # Extract class definitions from each serializer
        for model_path, code in serializer_codes.items():
            lines = code.split("\n")

            # Skip the docstring (lines starting with """ until closing """)
            in_docstring = False
            code_start = 0

            for i, line in enumerate(lines):
                if line.strip().startswith('"""'):
                    if not in_docstring:
                        in_docstring = True
                    elif line.strip().endswith('"""') and len(line.strip()) > 3:
                        # Single line docstring
                        code_start = i + 1
                        break
                    elif line.strip() == '"""':
                        # End of multi-line docstring
                        code_start = i + 1
                        break
                elif not in_docstring:
                    code_start = i
                    break

            # Process the remaining lines to extract class definitions
            current_class = []
            for line in lines[code_start:]:
                line = line.rstrip()
                # Skip import lines since we're generating our own
                if line.startswith("from ") or line.startswith("import "):
                    continue
                elif line.startswith("class ") or current_class:
                    current_class.append(line)
                elif line.strip() == "" and current_class:
                    # End of class definition
                    class_definitions.append("\n".join(current_class))
                    current_class = []

            # Add the last class if it exists
            if current_class:
                class_definitions.append("\n".join(current_class))

        # Generate combined file header
        from datetime import datetime

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        header = f'''"""
Auto-generated OData serializers (combined file).
Generated on: {now}

DO NOT EDIT THIS FILE MANUALLY.
Regenerate using: python manage.py generate_odata_serializer --single

Available options:
  --single   Generate one combined file instead of separate files
  --force    Overwrite existing files without prompting
"""

'''

        # Combine everything
        sorted_imports = sorted(imports)
        combined = (
            header
            + "\n".join(sorted_imports)
            + "\n\n\n"
            + "\n\n\n".join(class_definitions)
        )

        return combined
