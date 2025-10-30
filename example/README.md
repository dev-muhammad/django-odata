# Django OData - Example Application

This is a complete example Django application demonstrating all features of django-odata.

## Quick Start

### 1. Install Dependencies

From the project root directory:

```bash
# Install django-odata in development mode
pip install -e .

# Or install from the example directory
cd example/
pip install -r ../requirements.txt
```

### 2. Set Up Database

```bash
# Create database and apply migrations
python manage.py migrate

# Create a superuser (optional, for admin access)
python manage.py createsuperuser

# Load sample data (optional)
python manage.py loaddata blog/fixtures/sample_data.json
```

### 3. Run the Development Server

```bash
python manage.py runserver
```

The server will start at http://localhost:8000/

## Available Endpoints

### OData Endpoints

- **Blog Posts**: http://localhost:8000/odata/posts/
- **Authors**: http://localhost:8000/odata/authors/
- **Categories**: http://localhost:8000/odata/categories/

### Metadata Endpoints

- **Service Document**: http://localhost:8000/odata/
- **Posts Metadata**: http://localhost:8000/odata/posts/$metadata

### Admin Interface

- **Django Admin**: http://localhost:8000/admin/

## Example Queries

### Basic Queries

```bash
# Get all blog posts
curl http://localhost:8000/odata/posts/

# Get a specific post
curl http://localhost:8000/odata/posts/1/

# Get first 5 posts
curl http://localhost:8000/odata/posts/?$top=5
```

### Filtering

```bash
# Get published posts
curl "http://localhost:8000/odata/posts/?$filter=status eq 'published'"

# Get posts with specific title
curl "http://localhost:8000/odata/posts/?$filter=contains(title,'Django')"

# Complex filter
curl "http://localhost:8000/odata/posts/?$filter=status eq 'published' and view_count gt 50"
```

### Field Selection and Expansion

```bash
# Select specific fields
curl "http://localhost:8000/odata/posts/?$select=id,title,status"

# Expand author information
curl "http://localhost:8000/odata/posts/?$expand=author"

# Expand with nested field selection
curl "http://localhost:8000/odata/posts/?$expand=author($select=name,email)"

# Multiple expansions
curl "http://localhost:8000/odata/posts/?$expand=author,categories"
```

### Sorting and Pagination

```bash
# Sort by creation date
curl "http://localhost:8000/odata/posts/?$orderby=created_at desc"

# Pagination
curl "http://localhost:8000/odata/posts/?$skip=10&$top=5"

# Get count
curl "http://localhost:8000/odata/posts/?$count=true"
```

### Combined Queries

```bash
# Published posts, sorted by date, with author info
curl "http://localhost:8000/odata/posts/?$filter=status eq 'published'&$orderby=created_at desc&$expand=author&$top=10"

# Select specific fields with expansion
curl "http://localhost:8000/odata/posts/?$select=id,title&$expand=author($select=name)&$top=5"
```

## Project Structure

```
example/
├── manage.py           # Django management script
├── db.sqlite3         # SQLite database (created after migrate)
├── blog/              # Example blog application
│   ├── models.py      # BlogPost, Author, Category models
│   ├── serializers.py # OData serializers
│   ├── views.py       # OData viewsets
│   └── admin.py       # Django admin configuration
└── example/           # Django project settings
    ├── settings.py    # Project settings
    ├── urls.py        # URL configuration
    └── wsgi.py        # WSGI configuration
```

## Models

### BlogPost
- `id`: Integer (auto)
- `title`: String (max 200 chars)
- `content`: Text
- `status`: Choice (draft/published/archived)
- `view_count`: Integer (default 0)
- `created_at`: DateTime (auto)
- `updated_at`: DateTime (auto)
- `author`: ForeignKey to Author
- `categories`: ManyToMany to Category

### Author
- `id`: Integer (auto)
- `name`: String (max 100 chars)
- `email`: Email
- `bio`: Text (optional)

### Category
- `id`: Integer (auto)
- `name`: String (max 50 chars)
- `description`: Text (optional)

## Testing the Native Implementation

This example app now uses the **native field selection and expansion** implementation, completely removing the `drf-flex-fields` dependency. You can verify this works correctly by:

1. **Testing `$select`**:
   ```bash
   curl "http://localhost:8000/odata/posts/?$select=id,title"
   ```
   Should return only `id` and `title` fields.

2. **Testing `$expand`**:
   ```bash
   curl "http://localhost:8000/odata/posts/?$expand=author"
   ```
   Should include full author data inline.

3. **Testing nested `$select` in `$expand`**:
   ```bash
   curl "http://localhost:8000/odata/posts/?$expand=author($select=name,email)"
   ```
   Should include author with only `name` and `email` fields.

## Troubleshooting

### Database Issues

If you encounter database errors:

```bash
# Delete the database and start fresh
rm db.sqlite3
python manage.py migrate
```

### Import Errors

If you get import errors for `django_odata`:

```bash
# Make sure you're in the project root and install in development mode
cd ..
pip install -e .
cd example/
```

### Port Already in Use

If port 8000 is already in use:

```bash
# Use a different port
python manage.py runserver 8001
```

## Next Steps

- Explore the code in `blog/serializers.py` and `blog/views.py`
- Try different OData query combinations
- Check the Django admin to see the data
- Modify the models and see how OData adapts
- Review the test suite in `../tests/` for more examples