from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
    Date,
    Enum,
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class OrderStatus(enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class Region(Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    country = Column(String(100), default="Bangladesh")
    created_at = Column(DateTime, default=datetime.utcnow)

    sales = relationship("Sales", back_populates="region")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    unit_price = Column(Float, nullable=False)
    cost_price = Column(Float, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    sales = relationship("Sales", back_populates="product")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200))
    phone = Column(String(50))
    region_id = Column(Integer, ForeignKey("regions.id"))
    customer_type = Column(String(50), default="retail")  # retail, wholesale, corporate
    created_at = Column(DateTime, default=datetime.utcnow)

    region = relationship("Region")
    sales = relationship("Sales", back_populates="customer")


class Sales(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    order_date = Column(Date, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    discount = Column(Float, default=0.0)
    amount = Column(Float, nullable=False)  # (quantity * unit_price) - discount
    status = Column(String(20), default="COMPLETED")
    payment_method = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="sales")
    customer = relationship("Customer", back_populates="sales")
    region = relationship("Region", back_populates="sales")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(50), unique=True, nullable=False)
    sale_id = Column(Integer, ForeignKey("sales.id"))
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date)
    total_amount = Column(Float, nullable=False)
    paid_amount = Column(Float, default=0.0)
    status = Column(String(20), default="PENDING")  # PENDING, PAID, OVERDUE
    created_at = Column(DateTime, default=datetime.utcnow)


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    expense_date = Column(Date, nullable=False)
    category = Column(String(100), nullable=False)
    description = Column(Text)
    amount = Column(Float, nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    region = relationship("Region")
