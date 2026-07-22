from __future__ import annotations

from datetime import date as DateValue
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class Vendor(Base):
    """Vendor master-data table."""

    __tablename__ = "vendors"

    vendor_id: Mapped[str] = mapped_column(
        String(10),
        primary_key=True,
    )
    vendor_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    vendor_category: Mapped[str | None] = mapped_column(
        String(100),
    )
    contact_person: Mapped[str | None] = mapped_column(
        String(150),
    )
    city: Mapped[str | None] = mapped_column(
        String(100),
    )
    state: Mapped[str | None] = mapped_column(
        String(100),
    )
    region: Mapped[str | None] = mapped_column(
        String(50),
    )
    average_delivery_days: Mapped[int | None] = mapped_column(
        Integer,
    )
    rating: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 1),
    )
    payment_terms: Mapped[str | None] = mapped_column(
        String(100),
    )
    supply_status: Mapped[str | None] = mapped_column(
        String(50),
    )


class Employee(Base):
    """Employee master-data table."""

    __tablename__ = "employees"

    employee_id: Mapped[str] = mapped_column(
        String(10),
        primary_key=True,
    )
    employee_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    role: Mapped[str | None] = mapped_column(
        String(100),
    )
    department: Mapped[str | None] = mapped_column(
        String(100),
    )
    store_id: Mapped[str | None] = mapped_column(
        String(10),
    )
    region: Mapped[str | None] = mapped_column(
        String(50),
    )
    email: Mapped[str | None] = mapped_column(
        String(150),
    )
    monthly_target: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
    )
    performance_status: Mapped[str | None] = mapped_column(
        String(50),
    )
    employment_status: Mapped[str | None] = mapped_column(
        String(50),
    )


class Store(Base):
    """Store master-data table."""

    __tablename__ = "stores"

    store_id: Mapped[str] = mapped_column(
        String(10),
        primary_key=True,
    )
    store_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    city: Mapped[str | None] = mapped_column(
        String(100),
    )
    state: Mapped[str | None] = mapped_column(
        String(100),
    )
    region: Mapped[str | None] = mapped_column(
        String(50),
    )
    store_type: Mapped[str | None] = mapped_column(
        String(100),
    )
    manager_id: Mapped[str] = mapped_column(
        String(10),
        ForeignKey(
            "employees.employee_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    opening_date: Mapped[DateValue] = mapped_column(
        Date,
        nullable=False,
    )
    monthly_sales_target: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
    )
    operational_status: Mapped[str | None] = mapped_column(
        String(50),
    )


class Product(Base):
    """Product master-data table."""

    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(
        String(10),
        primary_key=True,
    )
    product_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    category: Mapped[str | None] = mapped_column(
        String(100),
    )
    sub_category: Mapped[str | None] = mapped_column(
        String(100),
    )
    brand: Mapped[str | None] = mapped_column(
        String(100),
    )
    unit_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
    )
    cost_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
    )
    margin_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 2),
    )
    reorder_level: Mapped[int | None] = mapped_column(
        Integer,
    )
    shelf_life_days: Mapped[int | None] = mapped_column(
        Integer,
    )
    is_perishable: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )
    vendor_id: Mapped[str] = mapped_column(
        String(10),
        ForeignKey(
            "vendors.vendor_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )


class Sale(Base):
    """Sales transaction table."""

    __tablename__ = "sales"

    sale_id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
    )
    date: Mapped[DateValue] = mapped_column(
        Date,
        nullable=False,
    )
    store_id: Mapped[str] = mapped_column(
        String(10),
        ForeignKey(
            "stores.store_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    store_name: Mapped[str | None] = mapped_column(
        String(150),
    )
    region: Mapped[str | None] = mapped_column(
        String(50),
    )
    product_id: Mapped[str] = mapped_column(
        String(10),
        ForeignKey(
            "products.product_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    product_name: Mapped[str | None] = mapped_column(
        String(200),
    )
    category: Mapped[str | None] = mapped_column(
        String(100),
    )
    employee_id: Mapped[str | None] = mapped_column(
        String(10),
        ForeignKey(
            "employees.employee_id",
            onupdate="CASCADE",
            ondelete="SET NULL",
        ),
    )
    quantity_sold: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        nullable=False,
        server_default=text("0"),
    )
    total_sales: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    total_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    profit: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
    )
    payment_status: Mapped[str | None] = mapped_column(
        String(50),
    )


class Inventory(Base):
    """Inventory snapshot table."""

    __tablename__ = "inventory"

    inventory_id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
    )
    date: Mapped[DateValue] = mapped_column(
        Date,
        nullable=False,
    )
    store_id: Mapped[str] = mapped_column(
        String(10),
        ForeignKey(
            "stores.store_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    store_name: Mapped[str | None] = mapped_column(
        String(150),
    )
    product_id: Mapped[str] = mapped_column(
        String(10),
        ForeignKey(
            "products.product_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    product_name: Mapped[str | None] = mapped_column(
        String(200),
    )
    category: Mapped[str | None] = mapped_column(
        String(100),
    )
    vendor_id: Mapped[str] = mapped_column(
        String(10),
        ForeignKey(
            "vendors.vendor_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    current_stock: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    reorder_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    stock_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    reorder_required: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )
    expiry_date: Mapped[DateValue | None] = mapped_column(
        Date,
    )


class Complaint(Base):
    """Customer complaint table."""

    __tablename__ = "complaints"

    complaint_id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
    )
    date: Mapped[DateValue] = mapped_column(
        Date,
        nullable=False,
    )
    customer_id: Mapped[str | None] = mapped_column(
        String(20),
    )
    store_id: Mapped[str] = mapped_column(
        String(10),
        ForeignKey(
            "stores.store_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    store_name: Mapped[str | None] = mapped_column(
        String(150),
    )
    region: Mapped[str | None] = mapped_column(
        String(50),
    )
    product_id: Mapped[str] = mapped_column(
        String(10),
        ForeignKey(
            "products.product_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    product_name: Mapped[str | None] = mapped_column(
        String(200),
    )
    category: Mapped[str | None] = mapped_column(
        String(100),
    )
    complaint_type: Mapped[str | None] = mapped_column(
        String(150),
    )
    complaint_description: Mapped[str | None] = mapped_column(
        Text,
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    assigned_employee_id: Mapped[str | None] = mapped_column(
        String(10),
        ForeignKey(
            "employees.employee_id",
            onupdate="CASCADE",
            ondelete="SET NULL",
        ),
    )
    resolution_time_days: Mapped[int | None] = mapped_column(
        Integer,
    )


class Finance(Base):
    """Monthly store finance table."""

    __tablename__ = "finance"

    finance_id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
    )
    month: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
    )
    store_id: Mapped[str] = mapped_column(
        String(10),
        ForeignKey(
            "stores.store_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    store_name: Mapped[str | None] = mapped_column(
        String(150),
    )
    region: Mapped[str | None] = mapped_column(
        String(50),
    )
    monthly_sales_target: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
    )
    total_revenue: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
    )
    total_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
    )
    gross_profit: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
    )
    operating_expense: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
    )
    operating_profit: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2),
    )
    target_achievement_percent: Mapped[
        Decimal | None
    ] = mapped_column(
        Numeric(8, 2),
    )
    risk_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )


class VendorDelivery(Base):
    """Vendor purchase-order delivery table."""

    __tablename__ = "vendor_deliveries"

    purchase_order_id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
    )
    order_date: Mapped[DateValue] = mapped_column(
        Date,
        nullable=False,
    )
    expected_delivery_date: Mapped[DateValue] = mapped_column(
        Date,
        nullable=False,
    )
    actual_delivery_date: Mapped[DateValue] = mapped_column(
        Date,
        nullable=False,
    )
    store_id: Mapped[str] = mapped_column(
        String(10),
        ForeignKey(
            "stores.store_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    store_name: Mapped[str | None] = mapped_column(
        String(150),
    )
    vendor_id: Mapped[str] = mapped_column(
        String(10),
        ForeignKey(
            "vendors.vendor_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    vendor_name: Mapped[str | None] = mapped_column(
        String(150),
    )
    product_id: Mapped[str] = mapped_column(
        String(10),
        ForeignKey(
            "products.product_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    product_name: Mapped[str | None] = mapped_column(
        String(200),
    )
    ordered_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    received_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    purchase_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    delay_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    delivery_status: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    quality_rating: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 1),
    )
    assigned_employee_id: Mapped[str | None] = mapped_column(
        String(10),
        ForeignKey(
            "employees.employee_id",
            onupdate="CASCADE",
            ondelete="SET NULL",
        ),
    )


class DataImportLog(Base):
    """History of controlled business-data imports."""

    __tablename__ = "data_import_logs"

    import_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    dataset_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    source_file_name: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
    )
    total_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    successful_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    failed_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    import_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )