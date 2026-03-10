from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from Krushi.models import Category, Product, User

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate database with sample data'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Create categories
        categories_data = [
            {'name': 'Equipment', 'description': 'Farming tools and machinery', 'icon': 'fas fa-tractor'},
            {'name': 'Fertilizer', 'description': 'Organic and chemical fertilizers', 'icon': 'fas fa-seedling'},
            {'name': 'Seeds', 'description': 'High-quality crop seeds', 'icon': 'fas fa-seedling'},
            {'name': 'Pesticides', 'description': 'Plant protection products', 'icon': 'fas fa-shield-alt'},
            {'name': 'Irrigation', 'description': 'Water management systems', 'icon': 'fas fa-tint'},
        ]
        
        categories = {}
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            categories[cat_data['name']] = category
            if created:
                self.stdout.write(f'Created category: {category.name}')
        
        # Create sample products
        products_data = [
            {
                'name': 'Mini Tractor',
                'description': 'Compact tractor perfect for small to medium farms. Features include 4-wheel drive, power steering, and multiple attachment points.',
                'price': 250000.00,
                'category': 'Equipment',
                'image': 'https://images.unsplash.com/photo-1586771107445-d3ca888129ce?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1470&q=80',
                'stock_quantity': 5,
                'rating': 4.8,
                'total_reviews': 28
            },
            {
                'name': 'Organic Plant Food',
                'description': '100% organic fertilizer made from natural ingredients. Promotes healthy root development and increases crop yield.',
                'price': 499.00,
                'category': 'Fertilizer',
                'image': 'https://images.unsplash.com/photo-1586771107445-d3ca888129ce?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1470&q=80',
                'stock_quantity': 100,
                'rating': 4.6,
                'total_reviews': 42
            },
            {
                'name': 'Hybrid Wheat Seeds',
                'description': 'High-yield wheat seeds resistant to common diseases. Perfect for wheat farming in various soil conditions.',
                'price': 299.00,
                'category': 'Seeds',
                'image': 'https://images.unsplash.com/photo-1586771107445-d3ca888129ce?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1470&q=80',
                'stock_quantity': 200,
                'rating': 4.9,
                'total_reviews': 35
            },
            {
                'name': 'Neem Oil Spray',
                'description': 'Natural pesticide made from neem tree extracts. Effective against common pests while being safe for plants and beneficial insects.',
                'price': 199.00,
                'category': 'Pesticides',
                'image': 'https://images.unsplash.com/photo-1586771107445-d3ca888129ce?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1470&q=80',
                'stock_quantity': 150,
                'rating': 4.4,
                'total_reviews': 19
            },
            {
                'name': 'Drip Irrigation Kit',
                'description': 'Complete drip irrigation system for efficient water usage. Includes tubing, emitters, and installation guide.',
                'price': 1999.00,
                'category': 'Irrigation',
                'image': 'https://images.unsplash.com/photo-1586771107445-d3ca888129ce?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1470&q=80',
                'stock_quantity': 25,
                'rating': 4.7,
                'total_reviews': 31
            },
            {
                'name': 'NPK 20-20-20 Fertilizer',
                'description': 'Balanced NPK fertilizer with equal parts nitrogen, phosphorus, and potassium. Suitable for most crops and soil types.',
                'price': 899.00,
                'category': 'Fertilizer',
                'image': 'https://images.unsplash.com/photo-1586771107445-d3ca888129ce?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1470&q=80',
                'stock_quantity': 75,
                'rating': 4.9,
                'total_reviews': 47
            },
            {
                'name': 'Garden Tool Set',
                'description': 'Complete set of essential gardening tools including spade, rake, hoe, and pruning shears. Made from durable materials.',
                'price': 1299.00,
                'category': 'Equipment',
                'image': 'https://images.unsplash.com/photo-1586771107445-d3ca888129ce?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1470&q=80',
                'stock_quantity': 50,
                'rating': 4.5,
                'total_reviews': 23
            },
            {
                'name': 'Tomato Seeds Pack',
                'description': 'Hybrid tomato seeds with high disease resistance and excellent fruit quality. Perfect for home gardens and commercial farming.',
                'price': 149.00,
                'category': 'Seeds',
                'image': 'https://images.unsplash.com/photo-1586771107445-d3ca888129ce?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1470&q=80',
                'stock_quantity': 300,
                'rating': 4.8,
                'total_reviews': 56
            },
            {
                'name': 'Organic Pesticide Spray',
                'description': 'Eco-friendly pesticide made from natural plant extracts. Controls common garden pests without harming beneficial insects.',
                'price': 349.00,
                'category': 'Pesticides',
                'image': 'https://images.unsplash.com/photo-1586771107445-d3ca888129ce?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1470&q=80',
                'stock_quantity': 80,
                'rating': 4.3,
                'total_reviews': 27
            },
            {
                'name': 'Sprinkler System',
                'description': 'Automated sprinkler system with programmable timer and adjustable spray patterns. Covers up to 1000 square feet.',
                'price': 2499.00,
                'category': 'Irrigation',
                'image': 'https://images.unsplash.com/photo-1586771107445-d3ca888129ce?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1470&q=80',
                'stock_quantity': 15,
                'rating': 4.6,
                'total_reviews': 18
            }
        ]
        
        for prod_data in products_data:
            category = categories[prod_data['category']]
            product, created = Product.objects.get_or_create(
                name=prod_data['name'],
                defaults={
                    'description': prod_data['description'],
                    'price': prod_data['price'],
                    'category': category,
                    'image': prod_data['image'],
                    'stock_quantity': prod_data['stock_quantity'],
                    'rating': prod_data['rating'],
                    'total_reviews': prod_data['total_reviews']
                }
            )
            if created:
                self.stdout.write(f'Created product: {product.name}')
        
        self.stdout.write(self.style.SUCCESS('Successfully populated database with sample data!'))
