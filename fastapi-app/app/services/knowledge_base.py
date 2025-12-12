"""
Knowledge Base - Contains all the business context for the RAG system.
This includes:
- Data dictionary
- Metric definitions
- Business rules
- Documentation
"""

from typing import List, Dict, Any


def get_data_dictionary() -> List[Dict[str, Any]]:
    """
    Returns the data dictionary with table and column descriptions.
    """
    return [
        # Regions table
        {
            "id": "table_regions",
            "content": """Table: regions
Description: Contains geographical regions where the company operates.
Columns:
- id (INTEGER): Primary key, unique identifier for each region
- name (VARCHAR): Name of the region (e.g., Dhaka, Chattogram, Sylhet)
- country (VARCHAR): Country name, default is Bangladesh
- created_at (DATETIME): Timestamp when the region was added

Use this table to filter or group data by geographical location.""",
            "metadata": {"type": "table", "table_name": "regions"}
        },

        # Products table
        {
            "id": "table_products",
            "content": """Table: products
Description: Product catalog containing all items sold by the company.
Columns:
- id (INTEGER): Primary key, unique product identifier
- name (VARCHAR): Product name (e.g., Laptop Pro 15, Smartphone X12)
- category (VARCHAR): Product category (Electronics, Furniture, Stationery)
- unit_price (FLOAT): Selling price per unit in BDT
- cost_price (FLOAT): Cost price per unit in BDT (used for margin calculations)
- description (TEXT): Detailed product description
- created_at (DATETIME): Timestamp when product was added

Use this table to get product information, categories, and pricing.""",
            "metadata": {"type": "table", "table_name": "products"}
        },

        # Customers table
        {
            "id": "table_customers",
            "content": """Table: customers
Description: Customer database containing all customer information.
Columns:
- id (INTEGER): Primary key, unique customer identifier
- name (VARCHAR): Customer/Company name
- email (VARCHAR): Customer email address
- phone (VARCHAR): Customer phone number
- region_id (INTEGER): Foreign key to regions table
- customer_type (VARCHAR): Type of customer - 'retail', 'wholesale', or 'corporate'
- created_at (DATETIME): Timestamp when customer was added

Use this table to filter sales by customer type or identify customers.""",
            "metadata": {"type": "table", "table_name": "customers"}
        },

        # Sales table
        {
            "id": "table_sales",
            "content": """Table: sales
Description: Main sales transactions table containing all orders.
Columns:
- id (INTEGER): Primary key, unique sale/order identifier
- order_date (DATE): Date when the order was placed
- product_id (INTEGER): Foreign key to products table
- customer_id (INTEGER): Foreign key to customers table
- region_id (INTEGER): Foreign key to regions table
- quantity (INTEGER): Number of units sold
- unit_price (FLOAT): Price per unit at time of sale
- discount (FLOAT): Discount amount applied to the order
- amount (FLOAT): Total sale amount = (quantity * unit_price) - discount
- status (VARCHAR): Order status - 'COMPLETED', 'PENDING', 'CANCELLED', 'REFUNDED'
- payment_method (VARCHAR): Payment method used - 'Cash', 'Card', 'Bank Transfer', 'Mobile Banking'
- created_at (DATETIME): Timestamp when record was created

IMPORTANT: For revenue/sales calculations, only include records where status = 'COMPLETED'""",
            "metadata": {"type": "table", "table_name": "sales"}
        },

        # Invoices table
        {
            "id": "table_invoices",
            "content": """Table: invoices
Description: Invoice records for sales transactions.
Columns:
- id (INTEGER): Primary key, unique invoice identifier
- invoice_number (VARCHAR): Unique invoice number
- sale_id (INTEGER): Foreign key to sales table
- invoice_date (DATE): Date when invoice was generated
- due_date (DATE): Payment due date
- total_amount (FLOAT): Total invoice amount
- paid_amount (FLOAT): Amount paid so far
- status (VARCHAR): Invoice status - 'PENDING', 'PAID', 'OVERDUE'
- created_at (DATETIME): Timestamp when invoice was created

Use this table for accounts receivable and payment tracking.""",
            "metadata": {"type": "table", "table_name": "invoices"}
        },

        # Expenses table
        {
            "id": "table_expenses",
            "content": """Table: expenses
Description: Company expense records.
Columns:
- id (INTEGER): Primary key, unique expense identifier
- expense_date (DATE): Date when expense was incurred
- category (VARCHAR): Expense category - 'Salary', 'Rent', 'Utilities', 'Marketing', 'Transportation', 'Office Supplies'
- description (TEXT): Expense description
- amount (FLOAT): Expense amount in BDT
- region_id (INTEGER): Foreign key to regions table (which region incurred the expense)
- created_at (DATETIME): Timestamp when record was created

Use this table for expense analysis and profit calculations.""",
            "metadata": {"type": "table", "table_name": "expenses"}
        },
    ]


def get_metric_definitions() -> List[Dict[str, Any]]:
    """
    Returns metric definitions with formulas and business logic.
    """
    return [
        {
            "id": "metric_total_sales",
            "content": """Metric: Total Sales / Sales Amount
Definition: The total monetary value of all completed sales transactions.
Formula: SUM(amount) FROM sales WHERE status = 'COMPLETED'
Unit: BDT (Bangladeshi Taka)
Notes:
- Only include COMPLETED orders
- The 'amount' column already includes quantity * unit_price - discount
- Can be filtered by date, region, product, or customer""",
            "metadata": {"type": "metric", "metric_name": "total_sales"}
        },

        {
            "id": "metric_revenue",
            "content": """Metric: Revenue / Total Revenue
Definition: Same as Total Sales - the sum of all completed sale amounts.
Formula: SUM(amount) FROM sales WHERE status = 'COMPLETED'
Unit: BDT
Notes: Revenue and Total Sales are used interchangeably in this system.""",
            "metadata": {"type": "metric", "metric_name": "revenue"}
        },

        {
            "id": "metric_gross_margin",
            "content": """Metric: Gross Margin / Gross Profit
Definition: Revenue minus cost of goods sold.
Formula: SUM(s.amount) - SUM(s.quantity * p.cost_price) FROM sales s JOIN products p ON s.product_id = p.id WHERE s.status = 'COMPLETED'
Alternative: ((Revenue - COGS) / Revenue) * 100 for percentage
Unit: BDT or Percentage
Notes:
- Use cost_price from products table
- Only include COMPLETED sales""",
            "metadata": {"type": "metric", "metric_name": "gross_margin"}
        },

        {
            "id": "metric_order_count",
            "content": """Metric: Order Count / Number of Orders
Definition: The total number of orders/transactions.
Formula: COUNT(*) FROM sales [WHERE status = 'COMPLETED' if only counting successful orders]
Unit: Count
Notes: Specify whether to count all orders or only completed ones based on context.""",
            "metadata": {"type": "metric", "metric_name": "order_count"}
        },

        {
            "id": "metric_average_order_value",
            "content": """Metric: Average Order Value (AOV)
Definition: The average monetary value per order.
Formula: AVG(amount) FROM sales WHERE status = 'COMPLETED'
Alternative: SUM(amount) / COUNT(*) FROM sales WHERE status = 'COMPLETED'
Unit: BDT
Notes: Only include completed orders for accurate AOV.""",
            "metadata": {"type": "metric", "metric_name": "aov"}
        },

        {
            "id": "metric_total_quantity",
            "content": """Metric: Total Quantity Sold
Definition: The total number of product units sold.
Formula: SUM(quantity) FROM sales WHERE status = 'COMPLETED'
Unit: Units/Pieces
Notes: Can be grouped by product, category, or region.""",
            "metadata": {"type": "metric", "metric_name": "total_quantity"}
        },

        {
            "id": "metric_total_expenses",
            "content": """Metric: Total Expenses
Definition: Sum of all company expenses.
Formula: SUM(amount) FROM expenses
Unit: BDT
Notes: Can be filtered by category, region, or date range.""",
            "metadata": {"type": "metric", "metric_name": "total_expenses"}
        },

        {
            "id": "metric_net_profit",
            "content": """Metric: Net Profit
Definition: Total revenue minus total expenses.
Formula: (SELECT SUM(amount) FROM sales WHERE status = 'COMPLETED') - (SELECT SUM(amount) FROM expenses)
Unit: BDT
Notes: This is a simplified calculation. For accurate profit, consider time periods.""",
            "metadata": {"type": "metric", "metric_name": "net_profit"}
        },
    ]


def get_business_rules() -> List[Dict[str, Any]]:
    """
    Returns business rules and conditions.
    """
    return [
        {
            "id": "rule_completed_sales",
            "content": """Business Rule: Completed Sales Only
When calculating revenue, sales, or any monetary metrics, ALWAYS filter by status = 'COMPLETED'.
Orders with status 'PENDING', 'CANCELLED', or 'REFUNDED' should NOT be included in revenue calculations.
SQL Pattern: WHERE status = 'COMPLETED'""",
            "metadata": {"type": "rule", "rule_name": "completed_sales"}
        },

        {
            "id": "rule_date_today",
            "content": """Business Rule: Today's Date Filter
For questions about 'today', use: WHERE order_date = CURRENT_DATE
For questions about 'yesterday': WHERE order_date = CURRENT_DATE - INTERVAL '1 day'
For SQLite use: WHERE order_date = date('now') or WHERE order_date = date('now', '-1 day')""",
            "metadata": {"type": "rule", "rule_name": "date_today"}
        },

        {
            "id": "rule_date_ranges",
            "content": """Business Rule: Date Range Filters
- 'This month': WHERE order_date >= date('now', 'start of month')
- 'Last month': WHERE order_date >= date('now', 'start of month', '-1 month') AND order_date < date('now', 'start of month')
- 'This quarter': Calculate based on current month (Q1: Jan-Mar, Q2: Apr-Jun, Q3: Jul-Sep, Q4: Oct-Dec)
- 'This year': WHERE order_date >= date('now', 'start of year')
- 'Last 7 days': WHERE order_date >= date('now', '-7 days')
- 'Last 30 days': WHERE order_date >= date('now', '-30 days')

For PostgreSQL, use DATE_TRUNC and INTERVAL syntax instead.""",
            "metadata": {"type": "rule", "rule_name": "date_ranges"}
        },

        {
            "id": "rule_currency",
            "content": """Business Rule: Currency
All monetary values are in BDT (Bangladeshi Taka).
When displaying amounts, format with comma separators for readability.
Example: 12,45,000 BDT (uses Indian/Bangladeshi number formatting)""",
            "metadata": {"type": "rule", "rule_name": "currency"}
        },

        {
            "id": "rule_regional_analysis",
            "content": """Business Rule: Regional Analysis
When asked about regional performance, JOIN the sales table with regions table.
SQL Pattern: SELECT r.name as region, SUM(s.amount) as total_sales
FROM sales s JOIN regions r ON s.region_id = r.id
WHERE s.status = 'COMPLETED' GROUP BY r.name ORDER BY total_sales DESC""",
            "metadata": {"type": "rule", "rule_name": "regional_analysis"}
        },

        {
            "id": "rule_product_analysis",
            "content": """Business Rule: Product Analysis
When asked about product performance, JOIN the sales table with products table.
SQL Pattern: SELECT p.name as product, p.category, SUM(s.amount) as total_sales
FROM sales s JOIN products p ON s.product_id = p.id
WHERE s.status = 'COMPLETED' GROUP BY p.name, p.category ORDER BY total_sales DESC""",
            "metadata": {"type": "rule", "rule_name": "product_analysis"}
        },
    ]


def get_documentation() -> List[Dict[str, Any]]:
    """
    Returns general documentation and notes.
    """
    return [
        {
            "id": "doc_schema_overview",
            "content": """Database Schema Overview:
The analytics database contains 6 main tables:
1. regions - Geographical regions (Dhaka, Chattogram, etc.)
2. products - Product catalog with pricing
3. customers - Customer information with types (retail, wholesale, corporate)
4. sales - Main transaction table with order details
5. invoices - Invoice and payment tracking
6. expenses - Company expense records

Key Relationships:
- sales.region_id -> regions.id
- sales.product_id -> products.id
- sales.customer_id -> customers.id
- invoices.sale_id -> sales.id
- expenses.region_id -> regions.id""",
            "metadata": {"type": "documentation", "doc_name": "schema_overview"}
        },

        {
            "id": "doc_common_queries",
            "content": """Common Query Patterns:
1. Total sales for a period: SUM(amount) WHERE status = 'COMPLETED' AND date filter
2. Sales by region: GROUP BY region after joining regions table
3. Sales by product/category: GROUP BY product/category after joining products table
4. Top customers: GROUP BY customer_id, ORDER BY SUM(amount) DESC, LIMIT N
5. Expense analysis: SUM(amount) FROM expenses GROUP BY category
6. Profit calculation: Total Revenue - Total Expenses for a period""",
            "metadata": {"type": "documentation", "doc_name": "common_queries"}
        },

        {
            "id": "doc_sql_dialect",
            "content": """SQL Dialect Notes:
This system supports both SQLite and PostgreSQL.
For SQLite date functions use: date('now'), date('now', '-1 day'), date('now', 'start of month')
For PostgreSQL date functions use: CURRENT_DATE, CURRENT_DATE - INTERVAL '1 day', DATE_TRUNC('month', CURRENT_DATE)

Always use standard SQL syntax that works with both when possible.
Avoid database-specific features unless necessary.""",
            "metadata": {"type": "documentation", "doc_name": "sql_dialect"}
        },
    ]


def initialize_knowledge_base(vector_store) -> None:
    """
    Initialize the vector store with all knowledge base content.

    Args:
        vector_store: VectorStoreService instance
    """
    print("Initializing knowledge base...")

    # Clear existing data
    vector_store.clear_all()

    # Add data dictionary
    data_dict = get_data_dictionary()
    vector_store.add_data_dictionary(data_dict)
    print(f"  Added {len(data_dict)} data dictionary items")

    # Add metric definitions
    metrics = get_metric_definitions()
    vector_store.add_metrics(metrics)
    print(f"  Added {len(metrics)} metric definitions")

    # Add business rules
    rules = get_business_rules()
    vector_store.add_business_rules(rules)
    print(f"  Added {len(rules)} business rules")

    # Add documentation
    docs = get_documentation()
    vector_store.add_documentation(docs)
    print(f"  Added {len(docs)} documentation items")

    print("Knowledge base initialized successfully!")
