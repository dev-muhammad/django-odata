# Django OData

**Bringing OData Standards to Django** - A comprehensive Django package that implements the OData (Open Data Protocol) specification for REST APIs, enabling standardized data access patterns with powerful querying capabilities.

This package transforms your Django models into OData-compliant endpoints by seamlessly integrating `drf-flex-fields` and `odata-query`, providing enterprise-grade API functionality with minimal configuration.

## Features

### 🎯 **OData Specification Compliance**
- **Complete OData v4 Query Support**: Full implementation of OData query options (`$filter`, `$orderby`, `$top`, `$skip`, `$select`, `$expand`, `$count`)
- **OData Response Format**: Standards-compliant JSON responses with proper `@odata.context` and metadata annotations
- **Service Metadata**: Built-in `$metadata` endpoint for complete API discovery and client generation
- **OData Error Handling**: Standardized error responses following OData specifications

### ⚡ **Performance & Optimization**
- **Intelligent Query Optimization**: Automatic `select_related()` and `prefetch_related()` application to prevent N+1 queries
- **Smart Query Translation**: OData filter expressions automatically converted to optimized Django ORM queries
- **Efficient Data Loading**: Only requested fields are serialized and transmitted

### 🔧 **Developer Experience**
- **Minimal Configuration**: Transform existing Django models into OData endpoints with just a few lines of code
- **Django REST Framework Integration**: Seamlessly extends DRF viewsets and serializers
- **Type Safety**: Proper OData-to-Django field type mapping for all Django field types
- **Flexible Architecture**: Easy to customize and extend for specific business requirements

## Installation

```bash
pip install django-odata
```

Or install from source:

```bash
git clone https://github.com/dev-muhammad/django-odata.git
cd django-odata
pip install -e .
```

## Dependencies

- Django >= 4.2 LTS
- Python >= 3.8
- djangorestframework >= 3.12.0
- drf-flex-fields >= 1.0.0
- odata-query >= 0.9.0

**Note**: Django 4.2 LTS is supported until April 2026. Please verify that `drf-flex-fields` supports Django 4.2 in your environment, as compatibility may vary between versions.

## Quick Start

### 1. Add to INSTALLED_APPS

```python
INSTALLED_APPS = [
    # ... your other apps
    'rest_framework',
    'rest_flex_fields',
    'django_odata',
]
```

### 2. Create OData Serializers

```python
from django_odata.serializers import ODataModelSerializer
from .models import BlogPost, Author, Category

class AuthorSerializer(ODataModelSerializer):
    class Meta:
        model = Author
        fields = ['id', 'name', 'email', 'bio']

class CategorySerializer(ODataModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description']

class BlogPostSerializer(ODataModelSerializer):
    class Meta:
        model = BlogPost
        fields = ['id', 'title', 'content', 'status', 'created_at']
        expandable_fields = {
            'author': (AuthorSerializer, {}),
            'categories': (CategorySerializer, {'many': True}),
        }
```

### 3. Create OData ViewSets

```python
from django_odata.viewsets import ODataModelViewSet
from .models import BlogPost, Author, Category
from .serializers import BlogPostSerializer, AuthorSerializer, CategorySerializer

class BlogPostViewSet(ODataModelViewSet):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer

class AuthorViewSet(ODataModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

class CategoryViewSet(ODataModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
```

### 4. Configure URLs

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BlogPostViewSet, AuthorViewSet, CategoryViewSet

router = DefaultRouter()
router.register(r'posts', BlogPostViewSet)
router.register(r'authors', AuthorViewSet)
router.register(r'categories', CategoryViewSet)

urlpatterns = [
    path('odata/', include(router.urls)),
]
```

## Usage Examples

### Basic Queries

```bash
# Get all blog posts
GET /odata/posts/

# Get a specific blog post
GET /odata/posts/1/

# Get first 10 posts
GET /odata/posts/?$top=10

# Skip first 20 posts, get next 10
GET /odata/posts/?$skip=20&$top=10
```

### Filtering

```bash
# Get published posts
GET /odata/posts/?$filter=status eq 'published'

# Get posts with more than 100 views
GET /odata/posts/?$filter=view_count gt 100

# Get posts created this year
GET /odata/posts/?$filter=year(created_at) eq 2024

# Complex filter
GET /odata/posts/?$filter=status eq 'published' and view_count gt 50
```

### Sorting

```bash
# Sort by creation date (newest first)
GET /odata/posts/?$orderby=created_at desc

# Sort by title alphabetically
GET /odata/posts/?$orderby=title asc

# Multiple sort criteria
GET /odata/posts/?$orderby=status desc,created_at desc
```

### Field Selection

```bash
# Select specific fields (OData standard)
GET /odata/posts/?$select=id,title,status

# If no $select specified, returns all available fields
GET /odata/posts/

# Omit specific fields (legacy feature)
GET /odata/posts/?omit=content
```

### Field Expansion

```bash
# Include author information (automatically adds 'author' to selected fields)
GET /odata/posts/?$expand=author

# Include multiple related fields
GET /odata/posts/?$expand=author,categories

# When using $expand, expanded fields are automatically selected
GET /odata/posts/?$expand=author
# Returns: all fields + author (with expanded data)

# Explicit field selection with expansion
GET /odata/posts/?$select=id,title&$expand=author
# Returns: id, title, author (with expanded data)

# Nested field selection in expanded properties (OData standard)
GET /odata/posts/?$expand=author($select=name,bio)
# Returns: all fields + author (with only name and bio)

# Multiple nested expansions
GET /odata/posts/?$expand=author($select=name,bio),categories($select=id,name)
# Returns: all fields + author (name,bio) + categories (id,name)

# Mixed simple and nested expansions
GET /odata/posts/?$expand=author($select=name),categories,tags($select=name)
# Returns: all fields + author (name only) + categories (all fields) + tags (name only)

# Combine explicit selection with nested expansions
GET /odata/posts/?$select=id,title&$expand=author($select=name,bio)
# Returns: id, title, author (with name and bio only)
```

### Automatic Query Optimization

The package automatically optimizes database queries when using `$expand` to prevent N+1 query problems:

```bash
# This request automatically applies prefetch_related('posts')
GET /odata/authors/?$expand=posts($select=id,title)

# This request automatically applies select_related('author') 
GET /odata/posts/?$expand=author($select=name,bio)
```

**Optimization Rules:**
- **Forward relationships** (ForeignKey, OneToOne): Uses `select_related()` for efficient JOINs
- **Reverse relationships** (reverse ForeignKey, ManyToMany): Uses `prefetch_related()` for separate optimized queries
- **No manual optimization needed**: The package detects relationship types and applies the appropriate optimization automatically

### Counting

```bash
# Get total count along with results
GET /odata/posts/?$count=true

# Get count of filtered results
GET /odata/posts/?$filter=status eq 'published'&$count=true
```

### Metadata

```bash
# Get service metadata
GET /odata/posts/$metadata

# Get service document
GET /odata/
```

## Advanced Usage

### Custom ViewSets

```python
from django_odata.viewsets import ODataModelViewSet

class CustomBlogPostViewSet(ODataModelViewSet):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer
    
    def get_queryset(self):
        \"\"\"Add custom filtering logic.\"\"\"
        queryset = super().get_queryset()
        
        # Only show published posts to non-staff users
        if not self.request.user.is_staff:
            queryset = queryset.filter(status='published')
        
        return queryset
```

### Factory Functions

```python
from django_odata.serializers import create_odata_serializer
from django_odata.viewsets import create_odata_viewset

# Create serializer automatically
BlogPostSerializer = create_odata_serializer(
    BlogPost,
    fields=['id', 'title', 'content', 'status'],
    expandable_fields={
        'author': ('myapp.serializers.AuthorSerializer', {}),
    }
)

# Create viewset automatically
BlogPostViewSet = create_odata_viewset(BlogPost, serializer_class=BlogPostSerializer)
```

### Query Builder

```python
from django_odata.utils import ODataQueryBuilder

# Build queries programmatically
query = (ODataQueryBuilder()
         .filter("status eq 'published'")
         .filter("view_count gt 100")
         .order('created_at', desc=True)
         .limit(20)
         .select('id', 'title', 'author')
         .expand('author')
         .build())

# query now contains the query parameters dictionary
```

## OData Query Options Reference

| Option | Description | Example |
|--------|-------------|---------|
| `$filter` | Filter results based on conditions | `$filter=status eq 'published'` |
| `$orderby` | Sort results | `$orderby=created_at desc` |
| `$top` | Limit number of results | `$top=10` |
| `$skip` | Skip number of results | `$skip=20` |
| `$select` | Choose specific fields | `$select=id,title,status` |
| `$expand` | Include related data | `$expand=author,categories` or `$expand=author($select=name,bio)` |
| `$count` | Include total count | `$count=true` |

### Filter Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equal | `status eq 'published'` |
| `ne` | Not equal | `status ne 'draft'` |
| `gt` | Greater than | `view_count gt 100` |
| `ge` | Greater than or equal | `rating ge 4.0` |
| `lt` | Less than | `view_count lt 50` |
| `le` | Less than or equal | `rating le 3.0` |
| `and` | Logical AND | `status eq 'published' and featured eq true` |
| `or` | Logical OR | `status eq 'published' or status eq 'featured'` |
| `not` | Logical NOT | `not (status eq 'draft')` |

### String Functions

| Function | Description | Example |
|----------|-------------|---------|
| `contains` | String contains | `contains(title,'django')` |
| `startswith` | String starts with | `startswith(title,'How to')` |
| `endswith` | String ends with | `endswith(title,'Guide')` |
| `length` | String length | `length(title) gt 10` |
| `tolower` | Convert to lowercase | `tolower(title) eq 'django guide'` |
| `toupper` | Convert to uppercase | `toupper(status) eq 'PUBLISHED'` |

### Date Functions

| Function | Description | Example |
|----------|-------------|---------|
| `year` | Extract year | `year(created_at) eq 2024` |
| `month` | Extract month | `month(created_at) eq 12` |
| `day` | Extract day | `day(created_at) eq 25` |
| `hour` | Extract hour | `hour(created_at) eq 14` |
| `minute` | Extract minute | `minute(created_at) eq 30` |
| `second` | Extract second | `second(created_at) eq 45` |

## Configuration

Add optional settings to your Django settings:

```python
# Optional django-odata settings
DJANGO_ODATA = {
    'SERVICE_ROOT': '/odata/',
    'MAX_PAGE_SIZE': 1000,
    'DEFAULT_PAGE_SIZE': 50,
    'ENABLE_METADATA': True,
    'ENABLE_SERVICE_DOCUMENT': True,
}
```

## Response Format

### Collection Response

```json
{
  "@odata.context": "http://example.com/odata/$metadata#posts",
  "@odata.count": 150,
  "value": [
    {
      "id": 1,
      "title": "Introduction to Django",
      "status": "published",
      "author": {
        "id": 1,
        "name": "John Doe",
        "email": "john@example.com"
      }
    }
  ]
}
```

### Single Entity Response

```json
{
  "@odata.context": "http://example.com/odata/$metadata#posts/$entity",
  "id": 1,
  "title": "Introduction to Django",
  "content": "This is a comprehensive guide...",
  "status": "published",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Error Response

```json
{
  "error": {
    "code": "BadRequest",
    "message": "The query specified in the URI is not valid."
  }
}
```

## Testing

Run the test suite:

```bash
# Install test dependencies
pip install -e .[dev]

# Run tests
pytest

# Run tests with coverage
pytest --cov=django_odata
```

## Example Project

See the `example/` directory for a complete Django project demonstrating all features:

```bash
cd example/
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Then visit:
- http://localhost:8000/odata/posts/ - Blog posts endpoint
- http://localhost:8000/odata/posts/$metadata - Metadata
- http://localhost:8000/odata/posts/?$filter=status eq 'published'&$expand=author

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Credits

- Built on top of [Django REST Framework](https://www.django-rest-framework.org/)
- Uses [drf-flex-fields](https://github.com/rsinger86/drf-flex-fields) for dynamic field selection
- Uses [odata-query](https://github.com/gorilla-llm/odata-query) for OData query parsing

## Changelog

### v0.1.0 (2025-08-30)
- Initial release
- Full OData query support ($filter, $orderby, $top, $skip, $select, $expand, $count)
- Dynamic field selection and expansion
- Metadata endpoints ($metadata, service document)
- Comprehensive test suite
- Example application
- Support for Django 4.2 LTS and Python 3.8+
