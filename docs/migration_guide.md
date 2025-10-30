# Migration Guide: Upgrading to Django OData v0.2.0 (Native Field Selection/Expansion)

This guide will help you migrate your existing Django OData projects from versions using `drf-flex-fields` for dynamic field selection and expansion to `django-odata` v0.2.0, which features a native, dependency-free implementation.

## Why Migrate?

`django-odata` v0.2.0 removes the dependency on `drf-flex-fields`, offering several benefits:
*   **Reduced Dependencies:** A lighter project footprint with fewer external packages to manage.
*   **Improved Performance:** Native implementation can often be more optimized than a third-party library.
*   **Simplified Codebase:** Direct control over OData logic within `django-odata`.
*   **Enhanced Stability:** Less exposure to breaking changes from an external dependency.

## Migration Steps

The migration process is straightforward, as `django-odata` v0.2.0 maintains 100% API compatibility for `$select` and `$expand` query options.

### 1. Update `django-odata` Package

First, upgrade your `django-odata` package to the latest version:

```bash
pip install --upgrade django-odata
```

### 2. Remove `drf-flex-fields` from `INSTALLED_APPS`

Open your Django project's `settings.py` file and remove `'rest_flex_fields'` from your `INSTALLED_APPS` list.

**Before:**
```python
# myproject/settings.py
INSTALLED_APPS = [
    # ... other apps
    'rest_framework',
    'rest_flex_fields', # REMOVE THIS LINE
    'django_odata',
]
```

**After:**
```python
# myproject/settings.py
INSTALLED_APPS = [
    # ... other apps
    'rest_framework',
    'django_odata',
]
```

### 3. Remove `drf-flex-fields` from `requirements.txt` (or `pyproject.toml`)

Remove `drf-flex-fields` from your project's dependency management file.

**If using `requirements.txt`:**
```diff
--- a/requirements.txt
+++ b/requirements.txt
@@ -1,4 +1,3 @@
 Django>=4.2
 djangorestframework>=3.12.0
-drf-flex-fields>=1.0.0
 odata-query>=0.9.0
```

**If using `pyproject.toml` (recommended):**
```diff
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -42,7 +42,6 @@
     "django>=4.2",
     "djangorestframework>=3.12.0",
-    "drf-flex-fields>=1.0.0",
     "odata-query>=0.9.0",
     "pytest>=6.0",
     "pytest-cov>=2.0",
```

### 4. Review `ODataModelSerializer` Usage

The `expandable_fields` attribute in your `ODataModelSerializer` classes remains fully compatible. No changes are required for how you define expandable fields.

**Example (no changes needed):**
```python
# myapp/serializers.py
from django_odata.serializers import ODataModelSerializer
from .models import BlogPost, Author

class AuthorSerializer(ODataModelSerializer):
    class Meta:
        model = Author
        fields = ['id', 'name', 'email']

class BlogPostSerializer(ODataModelSerializer):
    class Meta:
        model = BlogPost
        fields = ['id', 'title', 'content']
        expandable_fields = {
            'author': (AuthorSerializer, {}),
        }
```

### 5. Test Your Application

After making these changes, run your application's test suite to ensure everything is working as expected.

```bash
pytest
```

## Conclusion

By following these steps, you will successfully migrate your `django-odata` project to use the native field selection and expansion implementation, benefiting from a leaner, more performant, and more maintainable codebase. If you encounter any issues, please refer to the `django-odata` documentation or open an issue on the GitHub repository.