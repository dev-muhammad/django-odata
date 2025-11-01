# SPECKIT-008: Auto-Generate OData Serializers from Django Models

## 1. Objective

Create a Django management command that automatically generates ODataModelSerializer subclasses for Django models. The command will introspect model fields and relationships, detect circular dependencies, and generate complete serializer definitions with all fields and expandable relationships.

## 2. Background

Currently, developers must manually create OData serializers for each Django model, which involves:
- Listing all model fields in the `fields` list
- Identifying all relationships and adding them to `expandable_fields`
- Ensuring proper serializer references and avoiding circular dependencies
- Maintaining consistency across multiple serializers

This manual process is time-consuming, error-prone, and difficult to maintain as models evolve. An automated code generator would:
- Speed up initial OData API development
- Ensure all fields are included
- Automatically detect and handle circular dependencies
- Generate consistent, well-formatted serializer code
- Reduce human error in serializer definitions

## 3. Requirements

### 3.1 Command Interface

- The command must be accessible as `python manage.py generate_odata_serializer`
- Must accept model paths in format `app_label.ModelName` (e.g., `blog.BlogPost`)
- Must support `--app` flag to generate serializers for all models in an app
- Must support `--single` flag to combine all serializers into a single file
- Must support `--force` flag to overwrite existing files without prompting
- Must support `--skip-checks` flag to skip Django system checks during generation
- Generated serializers must be placed in `{app_label}/serializers/` directory by default
- Must support apps with full dotted names (e.g., `example.blog` in `INSTALLED_APPS`)

### 3.2 Field Detection

- Must detect and include ALL model fields:
  - Database fields (CharField, IntegerField, etc.)
  - ForeignKey fields
  - ManyToManyField
  - OneToOneField
  - Properties decorated with `@property` (as read-only fields)
- Must exclude Django's auto-created reverse relation fields from `fields` list
- Must handle all Django field types correctly

### 3.3 Relationship Detection

- Must detect all relationships for `expandable_fields`:
  - ForeignKey (single object expansion)
  - OneToOneField (single object expansion)
  - ManyToManyField (collection expansion with `many=True`)
  - Reverse ForeignKey (collection expansion with `many=True`)
  - Reverse OneToOneField (single object expansion)
  - Reverse ManyToManyField (collection expansion with `many=True`)
- In `--single` mode, must automatically discover and generate serializers for all related models
- Must support nested `$expand` operations (e.g., `$expand=author($expand=user)`)

### 3.4 Circular Dependency Detection

- Must detect circular dependencies between models
- Must NOT include relationships in `expandable_fields` that would create circular dependencies
- Strategy: Skip reverse relationships that create cycles
- Must report detected circular dependencies to the user

### 3.5 Code Generation

- Generated code must be syntactically valid Python
- Must use proper imports for `ODataModelSerializer`
- Must use string references for serializers with full app names (e.g., `'example.blog.serializers.AuthorSerializer'`)
- For apps with full dotted names in `INSTALLED_APPS`, must use the complete app name
- In `--single` mode, serializers for external models (e.g., `User`) must reference the current app's serializers package
- Must include docstrings and generation metadata
- Must format code consistently

### 3.6 File Organization

- Default mode: One file per model (e.g., `blog_post.py`, `author.py`) in `{app_label}/serializers/`
- `--single` mode: All serializers in one file (named after first model, e.g., `blog_post.py`) in `{app_label}/serializers/`
- Must update `__init__.py` with proper imports for all generated serializers
- Must handle file overwrites appropriately (prompt user unless `--force` flag is used)
- In `--single` mode, must include all discovered related models in the same file

## 4. Scope

This specification impacts:
- Creation of new Django management command in `django_odata/management/commands/`
- Creation of utility modules for model introspection and code generation
- Generated serializers placed in each app's `serializers/` directory
- Addition of comprehensive tests for the generator

Changes will involve:
- `django_odata/management/commands/generate_odata_serializer.py` (main command)
- Model introspection utilities (analyze Django models)
- Circular dependency detector (graph-based cycle detection)
- Code generator (template-based Python code generation)
- Test suite for the generator functionality

## 5. Non-Requirements

- The command will NOT modify existing serializers (only create new ones)
- The command will NOT generate custom serializer methods (only Meta configuration)
- The command will NOT support filtering which fields to include/exclude
- The command will NOT generate viewsets (only serializers)

## 6. Example Usage

```bash
# Generate serializer for a specific model
python manage.py generate_odata_serializer blog.BlogPost

# Generate serializers for multiple models
python manage.py generate_odata_serializer blog.BlogPost blog.Author

# Generate serializers for all models in an app
python manage.py generate_odata_serializer --app blog

# Generate all models from app in one combined file
python manage.py generate_odata_serializer --app blog --single

# Generate with auto-discovery of related models (recommended)
python manage.py generate_odata_serializer blog.BlogPost --single

# Force overwrite without prompting
python manage.py generate_odata_serializer blog.BlogPost --single --force

# Skip Django checks during generation (useful when regenerating)
python manage.py generate_odata_serializer blog.BlogPost --single --force --skip-checks

# Specify custom output directory
python manage.py generate_odata_serializer blog.BlogPost --output custom/path
```

## 7. Expected Output

### Example Generated Serializer (Single Mode)

```python
"""
Auto-generated OData serializers (combined file).
Generated on: 2025-11-01 10:01:39

DO NOT EDIT THIS FILE MANUALLY.
Regenerate using: python manage.py generate_odata_serializer --single

Available options:
  --single   Generate one combined file instead of separate files
  --force    Overwrite existing files without prompting
"""

from ..models import Author
from ..models import BlogPost
from ..models import Category
from django.contrib.auth.models import User
from django_odata.serializers import ODataModelSerializer


class CategorySerializer(ODataModelSerializer):
    """OData serializer for Category model."""

    class Meta:
        model = Category
        fields = [
            "posts",
            "id",
            "name",
            "description",
            "created_at",
            "pk",  # @property
        ]
        expandable_fields = {}


class AuthorSerializer(ODataModelSerializer):
    """OData serializer for Author model."""

    class Meta:
        model = Author
        fields = [
            "id",
            "user",
            "bio",
            "website",
            "avatar",
            "created_at",
            "email",  # @property
            "name",  # @property
            "pk",  # @property
        ]
        expandable_fields = {
            "user": ("example.blog.serializers.UserSerializer", {}),
        }


class BlogPostSerializer(ODataModelSerializer):
    """OData serializer for BlogPost model."""

    class Meta:
        model = BlogPost
        fields = [
            "tag_objects",
            "id",
            "title",
            "slug",
            "content",
            "excerpt",
            "author",
            "status",
            "featured",
            "view_count",
            "rating",
            "created_at",
            "updated_at",
            "published_at",
            "tags",
            "metadata",
            "categories",
            "is_published",  # @property
            "pk",  # @property
            "word_count",  # @property
        ]
        expandable_fields = {
            "author": ("example.blog.serializers.AuthorSerializer", {}),
            "categories": ("example.blog.serializers.CategorySerializer", {"many": True}),
        }


class UserSerializer(ODataModelSerializer):
    """OData serializer for User model."""

    class Meta:
        model = User
        fields = [
            "id",
            "password",
            "last_login",
            "is_superuser",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_staff",
            "is_active",
            "date_joined",
            "groups",
            "user_permissions",
            "is_anonymous",  # @property
            "is_authenticated",  # @property
            "pk",  # @property
        ]
        expandable_fields = {
            "groups": ("example.blog.serializers.GroupSerializer", {"many": True}),
            "user_permissions": ("example.blog.serializers.PermissionSerializer", {"many": True}),
        }
```

**Note:** In `--single` mode, all related models (including external models like `User`) are automatically discovered and their serializers are generated in the same file. All `expandable_fields` reference the current app's serializers package (e.g., `example.blog.serializers`) regardless of the model's original app.

## 8. Success Criteria

- ✅ Command successfully generates serializers for any Django model
- ✅ All model fields are included in the `fields` list
- ✅ All relationships are detected and added to `expandable_fields`
- ✅ Circular dependencies are correctly detected and skipped
- ✅ Generated code is syntactically valid Python
- ✅ `--app` flag discovers all models in specified app
- ✅ `--single` flag combines serializers into single file
- ✅ `--force` flag overwrites files without prompting
- ✅ `--skip-checks` flag skips Django system checks
- ✅ Supports apps with full dotted names (e.g., `example.blog`)
- ✅ In `--single` mode, automatically discovers all related models
- ✅ Generated serializers support nested `$expand` operations
- ✅ Serializer paths use full app names to avoid conflicts
- ✅ External model serializers reference current app in `--single` mode
- ✅ Existing files are handled appropriately
- ✅ Clear error messages for invalid inputs
- ✅ Comprehensive test coverage

## 9. Technical Notes

### 9.1 App Name Resolution

When generating serializers, the command must correctly handle apps with full dotted names:

- If `INSTALLED_APPS` contains `"example.blog"`, the app's `AppConfig.name` is `"example.blog"`
- The `app_label` (from `Model._meta.app_label`) is just `"blog"`
- For `apps.get_model()`, use the `app_label` (`"blog"`), not the full name
- For serializer paths, use the full `AppConfig.name` (`"example.blog"`)

### 9.2 Single Mode Behavior

In `--single` mode:
1. Start with requested model(s)
2. Discover all related models recursively
3. Generate serializers for all discovered models in one file
4. All serializers reference the current app's serializers package
5. Example: `UserSerializer` is generated in `example.blog.serializers`, not `django.contrib.auth.serializers`

This ensures all serializers are in one location and can be easily imported.