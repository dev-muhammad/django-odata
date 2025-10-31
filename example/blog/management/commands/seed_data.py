from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils.text import slugify
from faker import Faker
import random

from example.blog.models import Category, Author, BlogPost, Comment, Tag


class Command(BaseCommand):
    help = "Seeds the database with fake data for testing OData APIs."

    def handle(self, *args, **options):
        self.stdout.write("Seeding database with fake data...")
        fake = Faker()

        self.stdout.write("Clearing existing data...")
        Comment.objects.all().delete()
        BlogPost.objects.all().delete()
        Tag.objects.all().delete()
        Category.objects.all().delete()
        Author.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

        self.stdout.write("Creating users and authors...")
        users = []
        authors = []
        for _ in range(10):
            first_name = fake.first_name()
            last_name = fake.last_name()
            username = fake.user_name()
            email = fake.email()
            password = "password123"  # Default password for fake users

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            users.append(user)
            author = Author.objects.create(
                user=user,
                bio=fake.paragraph(),
                website=fake.url(),
                avatar=fake.image_url(),
            )
            authors.append(author)
        self.stdout.write(f"Created {len(users)} users and {len(authors)} authors.")

        self.stdout.write("Creating categories...")
        categories = []
        for _ in range(15):
            category = Category.objects.create(
                name=fake.unique.word().capitalize(),
                description=fake.sentence(),
            )
            categories.append(category)
        self.stdout.write(f"Created {len(categories)} categories.")

        self.stdout.write("Creating tags...")
        tags = []
        for _ in range(30):
            tag = Tag.objects.create(
                name=fake.unique.word().lower(),
                color=fake.hex_color(),
            )
            tags.append(tag)
        self.stdout.write(f"Created {len(tags)} tags.")

        self.stdout.write("Creating blog posts...")
        posts = []
        for _ in range(100):
            title = fake.sentence(nb_words=6)
            post_slug = slugify(title) + "-" + fake.uuid4()[:8]
            content = fake.text(max_nb_chars=2000)
            excerpt = fake.paragraph(nb_sentences=3)
            status = random.choice(["draft", "published", "archived"])
            published_at = fake.date_time_between(
                start_date="-2y", end_date="now"
            ) if status == "published" else None

            post = BlogPost.objects.create(
                title=title,
                slug=post_slug,
                content=content,
                excerpt=excerpt,
                author=random.choice(authors),
                status=status,
                featured=fake.boolean(),
                view_count=random.randint(0, 10000),
                rating=round(random.uniform(1.0, 5.0), 2),
                published_at=published_at,
                tags=fake.words(nb=random.randint(1, 5), unique=False),
                metadata={"source": fake.word(), "version": fake.random_int(1, 10)},
            )
            post.categories.set(random.sample(categories, random.randint(1, 4)))
            post.tag_objects.set(random.sample(tags, random.randint(1, 4)))
            posts.append(post)
        self.stdout.write(f"Created {len(posts)} blog posts.")

        self.stdout.write("Creating comments...")
        comments = []
        for _ in range(300):
            comment = Comment.objects.create(
                post=random.choice(posts),
                author_name=fake.name(),
                author_email=fake.email(),
                content=fake.paragraph(),
                is_approved=fake.boolean(),
            )
            comments.append(comment)
        self.stdout.write(f"Created {len(comments)} comments.")

        self.stdout.write(self.style.SUCCESS("Database seeded successfully!"))
