"""
Seed database with sample e-commerce data.

Creates realistic test data for demonstrating MCP capabilities:
- 50 customers across multiple countries
- 100 products in various categories
- 200 orders with varying statuses
- Order items with proper relationships

Run this script to populate a fresh database.
"""

import random
from datetime import datetime, timedelta
from src.database import DatabaseManager, Customer, Product, Order, OrderItem


# Sample data generators
FIRST_NAMES = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", 
               "William", "Barbara", "David", "Elizabeth", "Richard", "Susan", "Joseph", "Jessica"]

LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
              "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson", "Anderson", "Thomas"]

COUNTRIES = ["USA", "Canada", "UK", "Germany", "France", "Australia", "Japan", "India"]

PRODUCT_CATEGORIES = ["Electronics", "Clothing", "Home & Garden", "Sports", "Books", "Toys"]

PRODUCT_NAMES = {
    "Electronics": ["Laptop", "Smartphone", "Tablet", "Headphones", "Smart Watch", "Camera"],
    "Clothing": ["T-Shirt", "Jeans", "Jacket", "Sneakers", "Dress", "Hoodie"],
    "Home & Garden": ["Coffee Maker", "Blender", "Vacuum Cleaner", "Plant Pot", "Lamp", "Rug"],
    "Sports": ["Running Shoes", "Yoga Mat", "Dumbbell Set", "Tennis Racket", "Bicycle", "Backpack"],
    "Books": ["Fiction Novel", "Cookbook", "Biography", "Tech Manual", "Mystery Thriller", "Self-Help"],
    "Toys": ["Board Game", "Action Figure", "Puzzle", "Building Blocks", "Doll", "RC Car"]
}

ORDER_STATUSES = ["pending", "processing", "shipped", "delivered", "cancelled"]

CITIES = ["New York", "Los Angeles", "London", "Berlin", "Paris", "Sydney", "Tokyo", "Mumbai"]


def generate_customers(db: DatabaseManager, count: int = 50) -> list[Customer]:
    """Generate random customer data."""
    customers = []
    
    with db.get_session() as session:
        for i in range(count):
            customer = Customer(
                email=f"customer{i+1}@example.com",
                first_name=random.choice(FIRST_NAMES),
                last_name=random.choice(LAST_NAMES),
                phone=f"+1-555-{random.randint(1000, 9999)}",
                country=random.choice(COUNTRIES),
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 365))
            )
            session.add(customer)
            customers.append(customer)
        
        session.flush()  # Get IDs assigned
        print(f"✓ Created {count} customers")
        
    return customers


def generate_products(db: DatabaseManager, count: int = 100) -> list[Product]:
    """Generate random product catalog."""
    products = []
    
    with db.get_session() as session:
        for i in range(count):
            category = random.choice(PRODUCT_CATEGORIES)
            product_name = random.choice(PRODUCT_NAMES[category])
            
            product = Product(
                sku=f"SKU-{category[:3].upper()}-{i+1:04d}",
                name=f"{product_name} - Model {random.choice(['A', 'B', 'C', 'D'])}",
                description=f"High-quality {product_name.lower()} from {category} collection",
                category=category,
                price=round(random.uniform(9.99, 999.99), 2),
                stock_quantity=random.randint(0, 500),
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 180))
            )
            session.add(product)
            products.append(product)
        
        session.flush()
        print(f"✓ Created {count} products across {len(PRODUCT_CATEGORIES)} categories")
        
    return products


def generate_orders(
    db: DatabaseManager, 
    customers: list[Customer], 
    products: list[Product],
    count: int = 200
) -> None:
    """Generate random orders with line items."""
    
    with db.get_session() as session:
        for i in range(count):
            customer = random.choice(customers)
            order_date = datetime.utcnow() - timedelta(days=random.randint(0, 90))
            
            # Create order
            order = Order(
                customer_id=customer.id,
                order_date=order_date,
                status=random.choice(ORDER_STATUSES),
                total_amount=0.0,  # Will be calculated from items
                shipping_address=f"{random.randint(100, 9999)} Main St, {random.choice(CITIES)}, {customer.country}",
                created_at=order_date
            )
            session.add(order)
            session.flush()  # Get order ID
            
            # Add 1-5 random items to order
            num_items = random.randint(1, 5)
            order_total = 0.0
            
            selected_products = random.sample(products, num_items)
            for product in selected_products:
                quantity = random.randint(1, 3)
                unit_price = product.price
                subtotal = round(quantity * unit_price, 2)
                
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=unit_price,
                    subtotal=subtotal
                )
                session.add(order_item)
                order_total += subtotal
            
            # Update order total
            order.total_amount = round(order_total, 2)
        
        print(f"✓ Created {count} orders with line items")


def seed_database(db: DatabaseManager) -> None:
    """Main seeding function."""
    print("🌱 Starting database seeding...")
    print("-" * 50)
    
    # Drop and recreate tables for fresh start
    print("Dropping existing tables...")
    db.drop_all()
    print("Creating fresh schema...")
    db.init_db()
    print("-" * 50)
    
    # Generate data
    customers = generate_customers(db, count=50)
    products = generate_products(db, count=100)
    generate_orders(db, customers, products, count=200)
    
    print("-" * 50)
    print("✅ Database seeding complete!")
    print("\nDatabase summary:")
    with db.get_session() as session:
        print(f"  • Customers: {session.query(Customer).count()}")
        print(f"  • Products: {session.query(Product).count()}")
        print(f"  • Orders: {session.query(Order).count()}")
        print(f"  • Order Items: {session.query(OrderItem).count()}")


if __name__ == "__main__":
    db = DatabaseManager()
    seed_database(db)
