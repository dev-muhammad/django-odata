"""
Management command to export blog data using clean architecture.

This demonstrates how to use the repository pattern and OData queries
in management commands without depending on Django REST Framework.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import json
import csv
import os
from datetime import datetime

from ...services import BlogService, BlogDataExporter


class Command(BaseCommand):
    help = 'Export blog data using OData queries and clean architecture'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            choices=['json', 'csv'],
            default='json',
            help='Export format (default: json)'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path (default: stdout)'
        )
        parser.add_argument(
            '--query',
            type=str,
            default='',
            help='OData query string to filter posts'
        )
        parser.add_argument(
            '--include-unpublished',
            action='store_true',
            help='Include unpublished posts'
        )
        parser.add_argument(
            '--stats-only',
            action='store_true',
            help='Export only statistics, not full data'
        )

    def handle(self, *args, **options):
        """Execute the export command."""
        service = BlogService()
        exporter = BlogDataExporter(service)

        if options['stats_only']:
            self.export_stats(service, options)
        else:
            self.export_posts(exporter, options)

    def export_stats(self, service: BlogService, options):
        """Export blog statistics."""
        self.stdout.write('Fetching blog statistics...')

        stats = service.get_blog_stats()

        if options['output']:
            output_path = options['output']
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                if options['format'] == 'json':
                    json.dump(stats, f, indent=2, ensure_ascii=False)
                else:
                    # CSV format for stats
                    writer = csv.writer(f)
                    writer.writerow(['Metric', 'Value'])
                    for key, value in stats.items():
                        writer.writerow([key.replace('_', ' ').title(), value])

            self.stdout.write(
                self.style.SUCCESS(f'Statistics exported to {output_path}')
            )
        else:
            # Print to stdout
            self.stdout.write('Blog Statistics:')
            for key, value in stats.items():
                self.stdout.write(f'  {key.replace("_", " ").title()}: {value}')

    def export_posts(self, exporter: BlogDataExporter, options):
        """Export blog posts."""
        self.stdout.write('Fetching blog posts...')

        # Get posts using the service
        posts_data = exporter.export_published_posts(options['format'])

        if 'error' in posts_data:
            self.stderr.write(
                self.style.ERROR(f'Export failed: {posts_data["error"]}')
            )
            return

        if options['output']:
            output_path = options['output']
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                if options['format'] == 'json':
                    json.dump(posts_data, f, indent=2, ensure_ascii=False)
                else:
                    # Would implement CSV export for posts
                    self.stderr.write('CSV export for posts not yet implemented')

            self.stdout.write(
                self.style.SUCCESS(f'Posts exported to {output_path}')
            )
        else:
            # Print summary to stdout
            total_posts = posts_data.get('total_count', 0)
            self.stdout.write(
                f'Successfully exported {total_posts} published posts'
            )

            # Show first few posts as examples
            posts = posts_data.get('posts', [])[:3]
            if posts:
                self.stdout.write('\nFirst 3 posts:')
                for post in posts:
                    self.stdout.write(f'  - {post["title"]} by {post["author_name"]}')


# Example usage:
# python manage.py export_blog_data --format=json --output=blog_export.json
# python manage.py export_blog_data --stats-only --output=blog_stats.csv
# python manage.py export_blog_data --query="$filter=featured eq true&$top=10"