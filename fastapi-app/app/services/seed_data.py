"""
Seed data script for the analytics database.
Creates sample data for testing the RAG system.
"""

from datetime import datetime, date, timedelta
import random
from sqlalchemy.orm import Session

from app.models.database import Region, Product, Customer, Sales, Invoice, Expense


def seed_regions(session: Session) -> list[Region]:
    """Create sample regions."""
    regions_data = [
        {"name": "Dhaka", "country": "Bangladesh"},
        {"name": "Chattogram", "country": "Bangladesh"},
        {"name": "Sylhet", "country": "Bangladesh"},
        {"name": "Rajshahi", "country": "Bangladesh"},
        {"name": "Khulna", "country": "Bangladesh"},
    ]

    regions = []
    for data in regions_data:
        region = Region(**data)
        session.add(region)
        regions.append(region)

    session.flush()
    return regions


def seed_products(session: Session) -> list[Product]:
    """Create sample products."""
    products_data = [
        {"name": "Laptop Pro 15", "category": "Electronics", "unit_price": 85000, "cost_price": 70000, "description": "High-performance laptop"},
        {"name": "Smartphone X12", "category": "Electronics", "unit_price": 45000, "cost_price": 35000, "description": "Flagship smartphone"},
        {"name": "Wireless Headphones", "category": "Electronics", "unit_price": 5000, "cost_price": 3000, "description": "Bluetooth headphones"},
        {"name": "Office Chair Ergonomic", "category": "Furniture", "unit_price": 15000, "cost_price": 10000, "description": "Ergonomic office chair"},
        {"name": "Standing Desk", "category": "Furniture", "unit_price": 25000, "cost_price": 18000, "description": "Adjustable standing desk"},
        {"name": "LED Monitor 27inch", "category": "Electronics", "unit_price": 22000, "cost_price": 16000, "description": "4K LED monitor"},
        {"name": "Mechanical Keyboard", "category": "Electronics", "unit_price": 8000, "cost_price": 5000, "description": "RGB mechanical keyboard"},
        {"name": "Printer Multifunction", "category": "Electronics", "unit_price": 18000, "cost_price": 12000, "description": "All-in-one printer"},
        {"name": "Notebook Pack (100)", "category": "Stationery", "unit_price": 2000, "cost_price": 1200, "description": "Pack of 100 notebooks"},
        {"name": "Pen Set Premium", "category": "Stationery", "unit_price": 500, "cost_price": 250, "description": "Premium pen set"},
    ]

    products = []
    for data in products_data:
        product = Product(**data)
        session.add(product)
        products.append(product)

    session.flush()
    return products


def seed_customers(session: Session, regions: list[Region]) -> list[Customer]:
    """Create sample customers."""
    customer_names = [
        "ABC Corporation", "XYZ Traders", "Tech Solutions Ltd",
        "Global Imports", "City Electronics", "Metro Supplies",
        "Delta Trading", "Sunrise Enterprises", "Pacific Group",
        "Summit Industries", "Valley Distributors", "Horizon Ltd"
    ]

    customer_types = ["retail", "wholesale", "corporate"]

    customers = []
    for i, name in enumerate(customer_names):
        customer = Customer(
            name=name,
            email=f"contact@{name.lower().replace(' ', '')}.com",
            phone=f"+880 1{random.randint(700000000, 999999999)}",
            region_id=random.choice(regions).id,
            customer_type=random.choice(customer_types),
        )
        session.add(customer)
        customers.append(customer)

    session.flush()
    return customers


def seed_sales(
    session: Session,
    products: list[Product],
    customers: list[Customer],
    regions: list[Region],
    start_year: int = 2023
) -> list[Sales]:
    """Create sample sales data from start_year to today."""
    sales = []
    statuses = ["COMPLETED", "COMPLETED", "COMPLETED", "COMPLETED", "PENDING", "CANCELLED"]  # Weighted toward COMPLETED
    payment_methods = ["Cash", "Card", "Bank Transfer", "Mobile Banking"]

    # Start from January 1st of start_year
    start_date = date(start_year, 1, 1)
    end_date = date.today()
    total_days = (end_date - start_date).days

    for day_offset in range(total_days + 1):
        current_date = start_date + timedelta(days=day_offset)

        # Seasonal variation: more sales in Q4 (Oct-Dec) and less in Q1 (Jan-Mar)
        month = current_date.month
        if month in [10, 11, 12]:  # Q4 - holiday season
            num_sales = random.randint(8, 20)
        elif month in [1, 2, 3]:  # Q1 - slow season
            num_sales = random.randint(3, 10)
        else:  # Q2, Q3 - normal
            num_sales = random.randint(5, 15)

        for _ in range(num_sales):
            product = random.choice(products)
            customer = random.choice(customers)
            region = random.choice(regions)
            quantity = random.randint(1, 10)
            discount = random.choice([0, 0, 0, 500, 1000, 2000])  # Mostly no discount
            amount = (quantity * product.unit_price) - discount

            sale = Sales(
                order_date=current_date,
                product_id=product.id,
                customer_id=customer.id,
                region_id=region.id,
                quantity=quantity,
                unit_price=product.unit_price,
                discount=discount,
                amount=amount,
                status=random.choice(statuses),
                payment_method=random.choice(payment_methods),
            )
            session.add(sale)
            sales.append(sale)

    session.flush()
    return sales


def seed_expenses(session: Session, regions: list[Region], start_year: int = 2023) -> list[Expense]:
    """Create sample expense data from start_year to today."""
    expense_categories = [
        ("Salary", 50000, 200000),
        ("Rent", 20000, 100000),
        ("Utilities", 5000, 20000),
        ("Marketing", 10000, 50000),
        ("Transportation", 5000, 30000),
        ("Office Supplies", 2000, 10000),
    ]

    expenses = []
    start_date = date(start_year, 1, 1)
    end_date = date.today()
    total_days = (end_date - start_date).days

    for day_offset in range(0, total_days + 1, 7):  # Weekly expenses
        current_date = start_date + timedelta(days=day_offset)

        for category, min_amt, max_amt in expense_categories:
            if random.random() > 0.3:  # 70% chance of expense
                expense = Expense(
                    expense_date=current_date,
                    category=category,
                    description=f"{category} expense for the week",
                    amount=random.randint(min_amt, max_amt),
                    region_id=random.choice(regions).id,
                )
                session.add(expense)
                expenses.append(expense)

    session.flush()
    return expenses


def seed_invoices(session: Session, sales: list[Sales]) -> list[Invoice]:
    """Create invoices for completed sales."""
    invoices = []
    invoice_num = 1000

    # Create an invoice for each completed sale
    completed_sales = [s for s in sales if s.status == "COMPLETED"]

    # Sample ~30% of completed sales for invoices to keep it manageable
    sampled_sales = random.sample(completed_sales, min(len(completed_sales) // 3, 3000))

    for sale in sampled_sales:
        paid_amount = sale.amount if random.random() > 0.2 else sale.amount * random.uniform(0.5, 0.9)
        status = "PAID" if paid_amount >= sale.amount else ("PARTIAL" if paid_amount > 0 else "PENDING")

        invoice = Invoice(
            invoice_number=f"INV-{invoice_num}",
            sale_id=sale.id,
            invoice_date=sale.order_date,
            due_date=sale.order_date + timedelta(days=30),
            total_amount=sale.amount,
            paid_amount=paid_amount,
            status=status,
        )
        session.add(invoice)
        invoices.append(invoice)
        invoice_num += 1

    session.flush()
    return invoices


def seed_database(session: Session):
    """Main function to seed all data."""
    print("Seeding regions...")
    regions = seed_regions(session)

    print("Seeding products...")
    products = seed_products(session)

    print("Seeding customers...")
    customers = seed_customers(session, regions)

    print("Seeding sales data (2023-2025)...")
    sales = seed_sales(session, products, customers, regions, start_year=2023)

    print("Seeding invoices...")
    invoices = seed_invoices(session, sales)

    print("Seeding expenses (2023-2025)...")
    expenses = seed_expenses(session, regions, start_year=2023)

    session.commit()

    print(f"\nSeeding complete!")
    print(f"  - Regions: {len(regions)}")
    print(f"  - Products: {len(products)}")
    print(f"  - Customers: {len(customers)}")
    print(f"  - Sales: {len(sales)}")
    print(f"  - Invoices: {len(invoices)}")
    print(f"  - Expenses: {len(expenses)}")


if __name__ == "__main__":
    from app.services.database_service import get_database_service

    # Use SQLite for demo
    db_service = get_database_service("sqlite:///./analytics.db")
    db_service.create_tables()

    with db_service.get_session() as session:
        seed_database(session)
