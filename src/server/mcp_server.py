"""
MCP Server implementation for database operations.

This server exposes database schema, query execution, and prompt templates
to LLM clients via the Model Context Protocol.

Key capabilities:
- Resources: Expose database schema metadata
- Tools: Safe SQL query execution with validation
- Prompts: Pre-defined analytical query templates
"""

import asyncio
import json
import logging
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.types import (
    Resource,
    Tool,
    Prompt,
    TextContent,
    ImageContent,
    EmbeddedResource,
    PromptMessage,
    GetPromptResult,
    INVALID_PARAMS,
    INTERNAL_ERROR,
)

from src.database import DatabaseManager, Customer, Product, Order, OrderItem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize database
db = DatabaseManager()

# Create MCP server instance
server = Server("mcp-database-server")


@server.list_resources()
async def list_resources() -> list[Resource]:
    """
    List available database resources (schemas, metadata).
    
    Resources are read-only context that LLMs can reference.
    """
    return [
        Resource(
            uri="db://schema/customers",
            name="Customer Table Schema",
            mimeType="application/json",
            description="Schema definition and sample data for customers table"
        ),
        Resource(
            uri="db://schema/products",
            name="Product Table Schema",
            mimeType="application/json",
            description="Schema definition and sample data for products table"
        ),
        Resource(
            uri="db://schema/orders",
            name="Order Table Schema",
            mimeType="application/json",
            description="Schema definition and sample data for orders table"
        ),
        Resource(
            uri="db://schema/order_items",
            name="Order Items Table Schema",
            mimeType="application/json",
            description="Schema definition for order line items"
        ),
        Resource(
            uri="db://stats/summary",
            name="Database Statistics",
            mimeType="application/json",
            description="Summary statistics: record counts, value ranges, etc."
        ),
    ]


@server.read_resource()
async def read_resource(uri: str) -> str | bytes:
    """
    Read a specific resource by URI.
    
    Returns JSON-formatted schema information and sample data.
    """
    # Convert AnyUrl to string if needed
    uri_str = str(uri)
    logger.info(f"=== READ_RESOURCE CALLED ===")
    logger.info(f"Original URI type: {type(uri)}")
    logger.info(f"URI string: {repr(uri_str)}")
    logger.info(f"Checking equality: {uri_str == 'db://schema/customers'}")
    logger.info(f"==============================")
    
    content_text = ""
    
    if uri_str == "db://schema/customers":
        logger.info("Matched customers schema")
        content_text = json.dumps({
            "table": "customers",
            "description": "Customer master data with contact information",
            "columns": [
                {"name": "id", "type": "INTEGER", "primary_key": True},
                {"name": "email", "type": "VARCHAR(255)", "unique": True, "indexed": True},
                {"name": "first_name", "type": "VARCHAR(100)"},
                {"name": "last_name", "type": "VARCHAR(100)"},
                {"name": "phone", "type": "VARCHAR(20)", "nullable": True},
                {"name": "country", "type": "VARCHAR(100)", "indexed": True},
                {"name": "created_at", "type": "DATETIME"},
                {"name": "updated_at", "type": "DATETIME"},
            ],
            "relationships": ["Has many Orders"],
            "indexes": ["idx_customer_name (last_name, first_name)", "idx_customer_country (country)"],
            "sample_query": "SELECT * FROM customers WHERE country = 'USA' LIMIT 10"
        }, indent=2)
    
    elif uri_str == "db://schema/products":
        content_text = json.dumps({
            "table": "products",
            "description": "Product catalog with pricing and inventory",
            "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": True},
                    {"name": "sku", "type": "VARCHAR(50)", "unique": True, "indexed": True},
                    {"name": "name", "type": "VARCHAR(255)"},
                    {"name": "description", "type": "VARCHAR(1000)", "nullable": True},
                    {"name": "category", "type": "VARCHAR(100)", "indexed": True},
                    {"name": "price", "type": "FLOAT"},
                    {"name": "stock_quantity", "type": "INTEGER"},
                    {"name": "created_at", "type": "DATETIME"},
                    {"name": "updated_at", "type": "DATETIME"},
                ],
            "relationships": ["Has many OrderItems"],
            "indexes": ["idx_product_category_price (category, price)"],
            "sample_query": "SELECT * FROM products WHERE category = 'Electronics' ORDER BY price DESC LIMIT 10"
        }, indent=2)
    
    elif uri_str == "db://schema/orders":
        content_text = json.dumps({
            "table": "orders",
            "description": "Customer orders with status tracking",
            "columns": [
                {"name": "id", "type": "INTEGER", "primary_key": True},
                {"name": "customer_id", "type": "INTEGER", "foreign_key": "customers.id", "indexed": True},
                {"name": "order_date", "type": "DATETIME"},
                {"name": "status", "type": "VARCHAR(50)", "indexed": True, "values": ["pending", "processing", "shipped", "delivered", "cancelled"]},
                {"name": "total_amount", "type": "FLOAT"},
                {"name": "shipping_address", "type": "VARCHAR(500)"},
                {"name": "created_at", "type": "DATETIME"},
                {"name": "updated_at", "type": "DATETIME"},
            ],
            "relationships": ["Belongs to Customer", "Has many OrderItems"],
            "indexes": ["idx_order_customer_date (customer_id, order_date)", "idx_order_status_date (status, order_date)"],
            "sample_query": "SELECT * FROM orders WHERE status = 'delivered' ORDER BY order_date DESC LIMIT 10"
        }, indent=2)
    
    elif uri_str == "db://schema/order_items":
        content_text = json.dumps({
            "table": "order_items",
            "description": "Line items for orders with quantity and pricing snapshot",
            "columns": [
                {"name": "id", "type": "INTEGER", "primary_key": True},
                {"name": "order_id", "type": "INTEGER", "foreign_key": "orders.id", "indexed": True},
                {"name": "product_id", "type": "INTEGER", "foreign_key": "products.id", "indexed": True},
                {"name": "quantity", "type": "INTEGER"},
                {"name": "unit_price", "type": "FLOAT"},
                {"name": "subtotal", "type": "FLOAT"},
            ],
            "relationships": ["Belongs to Order", "Belongs to Product"],
            "indexes": ["idx_order_item_order_product (order_id, product_id)"],
            "sample_query": "SELECT * FROM order_items WHERE order_id = 1"
        }, indent=2)
    
    elif uri_str == "db://stats/summary":
        # Generate live statistics
        with db.get_session() as session:
            stats = {
                "record_counts": {
                    "customers": session.query(Customer).count(),
                    "products": session.query(Product).count(),
                    "orders": session.query(Order).count(),
                    "order_items": session.query(OrderItem).count(),
                },
                "order_status_distribution": _get_order_status_dist(session),
                "product_categories": _get_product_categories(session),
                "date_range": _get_date_range(session),
            }
            content_text = json.dumps(stats, indent=2, default=str)
    
    else:
        logger.error(f"Unknown resource URI: {uri}")
        raise ValueError(f"Unknown resource URI: {uri}")
    
    # Return plain string - SDK will wrap it
    logger.info(f"Returning content for {uri}, length: {len(content_text)}")
    return content_text


def _get_order_status_dist(session) -> dict[str, int]:
    """Helper to get order status distribution."""
    from sqlalchemy import func
    results = session.query(
        Order.status, func.count(Order.id)
    ).group_by(Order.status).all()
    return {status: count for status, count in results}


def _get_product_categories(session) -> list[str]:
    """Helper to get unique product categories."""
    from sqlalchemy import func
    results = session.query(Product.category).distinct().all()
    return [cat[0] for cat in results]


def _get_date_range(session) -> dict[str, str]:
    """Helper to get order date range."""
    from sqlalchemy import func
    result = session.query(
        func.min(Order.order_date),
        func.max(Order.order_date)
    ).first()
    return {
        "earliest_order": str(result[0]) if result[0] else None,
        "latest_order": str(result[1]) if result[1] else None
    }


@server.list_tools()
async def list_tools() -> list[Tool]:
    """
    List available tools (actions) that LLMs can invoke.
    """
    return [
        Tool(
            name="query_database",
            description="Execute a read-only SQL SELECT query against the database. Returns results as JSON. Query must be SELECT only (no INSERT/UPDATE/DELETE).",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "SQL SELECT query to execute. Must be valid SQLite syntax."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of rows to return (default: 100, max: 1000)",
                        "default": 100
                    }
                },
                "required": ["sql"]
            }
        ),
        Tool(
            name="get_customer_orders",
            description="Get all orders for a specific customer by customer ID or email.",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "integer",
                        "description": "Customer ID"
                    },
                    "email": {
                        "type": "string",
                        "description": "Customer email address"
                    }
                },
                "oneOf": [
                    {"required": ["customer_id"]},
                    {"required": ["email"]}
                ]
            }
        ),
        Tool(
            name="analyze_product_sales",
            description="Analyze sales performance for products in a specific category or overall.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product category to analyze (optional, omit for all categories)"
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Number of top products to return (default: 10)",
                        "default": 10
                    }
                }
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """
    Execute a tool with given arguments.
    
    Implements safety checks, validation, and error handling.
    """
    logger.info(f"Tool call: {name} with arguments: {arguments}")
    
    try:
        if name == "query_database":
            return await _tool_query_database(arguments)
        elif name == "get_customer_orders":
            return await _tool_get_customer_orders(arguments)
        elif name == "analyze_product_sales":
            return await _tool_analyze_product_sales(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(e), "tool": name})
        )]


async def _tool_query_database(arguments: dict) -> list[TextContent]:
    """Execute raw SQL query with safety checks."""
    sql = arguments.get("sql", "").strip().upper()
    limit = min(arguments.get("limit", 100), 1000)
    
    # Safety: only allow SELECT
    if not sql.startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed")
    
    # Safety: block dangerous keywords
    forbidden = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE"]
    if any(keyword in sql for keyword in forbidden):
        raise ValueError(f"Query contains forbidden keywords: {forbidden}")
    
    # Execute in thread pool (SQLAlchemy is sync)
    def _execute():
        with db.get_session() as session:
            result = session.execute(arguments["sql"])
            rows = result.fetchmany(limit)
            columns = result.keys()
            return [dict(zip(columns, row)) for row in rows]
    
    results = await asyncio.to_thread(_execute)
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "rows": results,
            "count": len(results),
            "truncated": len(results) == limit
        }, indent=2, default=str)
    )]


async def _tool_get_customer_orders(arguments: dict) -> list[TextContent]:
    """Get customer orders by ID or email."""
    def _execute():
        with db.get_session() as session:
            # Find customer
            if "customer_id" in arguments:
                customer = session.query(Customer).filter_by(id=arguments["customer_id"]).first()
            else:
                customer = session.query(Customer).filter_by(email=arguments["email"]).first()
            
            if not customer:
                return {"error": "Customer not found"}
            
            # Get orders with items
            orders = session.query(Order).filter_by(customer_id=customer.id).all()
            
            return {
                "customer": {
                    "id": customer.id,
                    "name": f"{customer.first_name} {customer.last_name}",
                    "email": customer.email,
                    "country": customer.country
                },
                "orders": [
                    {
                        "id": order.id,
                        "order_date": str(order.order_date),
                        "status": order.status,
                        "total_amount": order.total_amount,
                        "items_count": len(order.order_items)
                    }
                    for order in orders
                ],
                "total_orders": len(orders),
                "total_spent": sum(order.total_amount for order in orders)
            }
    
    result = await asyncio.to_thread(_execute)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _tool_analyze_product_sales(arguments: dict) -> list[TextContent]:
    """Analyze product sales by category."""
    category = arguments.get("category")
    top_n = arguments.get("top_n", 10)
    
    def _execute():
        with db.get_session() as session:
            from sqlalchemy import func
            
            query = session.query(
                Product.id,
                Product.name,
                Product.category,
                Product.price,
                func.sum(OrderItem.quantity).label("total_quantity"),
                func.sum(OrderItem.subtotal).label("total_revenue"),
                func.count(OrderItem.id).label("order_count")
            ).join(OrderItem).group_by(Product.id)
            
            if category:
                query = query.filter(Product.category == category)
            
            query = query.order_by(func.sum(OrderItem.subtotal).desc()).limit(top_n)
            
            results = query.all()
            
            return {
                "category": category or "All Categories",
                "top_products": [
                    {
                        "product_id": r.id,
                        "name": r.name,
                        "category": r.category,
                        "price": r.price,
                        "units_sold": r.total_quantity,
                        "total_revenue": round(r.total_revenue, 2),
                        "orders_count": r.order_count
                    }
                    for r in results
                ],
                "count": len(results)
            }
    
    result = await asyncio.to_thread(_execute)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    """
    List available prompt templates.
    
    Prompts are pre-defined workflows that LLMs can invoke with parameters.
    """
    from mcp.types import PromptArgument
    
    return [
        Prompt(
            name="analyze_customer",
            description="Analyze a customer's purchase history and behavior",
            arguments=[
                PromptArgument(
                    name="customer_id",
                    description="Customer ID to analyze",
                    required=True
                )
            ]
        ),
        Prompt(
            name="category_performance",
            description="Generate a performance report for a product category",
            arguments=[
                PromptArgument(
                    name="category",
                    description="Product category name",
                    required=True
                ),
                PromptArgument(
                    name="period_days",
                    description="Analysis period in days (default: 30)",
                    required=False
                )
            ]
        ),
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    """
    Get a specific prompt with arguments populated.
    
    Returns a structured prompt that the LLM can execute.
    """
    args = arguments or {}
    
    if name == "analyze_customer":
        customer_id = args.get("customer_id")
        return GetPromptResult(
            description=f"Analyze customer {customer_id}",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""Please analyze customer {customer_id} using the following steps:

1. Use the `get_customer_orders` tool to retrieve all orders for customer_id={customer_id}
2. Analyze their purchase patterns:
   - Total orders and spend
   - Favorite product categories
   - Average order value
   - Order frequency
3. Provide insights and recommendations:
   - Customer segment (high-value, occasional, at-risk)
   - Product recommendations based on purchase history
   - Potential upsell opportunities

Format the analysis professionally with clear sections and actionable insights."""
                    )
                )
            ]
        )
    
    elif name == "category_performance":
        category = args.get("category")
        period_days = args.get("period_days", "30")
        return GetPromptResult(
            description=f"Analyze performance for {category} category",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""Generate a performance report for the '{category}' product category:

1. Use `analyze_product_sales` tool with category='{category}' to get top products
2. Use `query_database` to find:
   - Total orders containing {category} products in last {period_days} days
   - Average order value for {category} items
   - Inventory levels (stock_quantity)
3. Provide analysis:
   - Best-performing products and why
   - Revenue trends
   - Inventory recommendations (restock alerts)
   - Pricing optimization opportunities

Present findings in a executive summary format suitable for leadership."""
                    )
                )
            ]
        )
    
    else:
        raise ValueError(f"Unknown prompt: {name}")


async def main():
    """Main entry point for MCP server."""
    logger.info("Starting MCP Database Server")
    
    # Initialize database
    logger.info("Initializing database...")
    db.init_db()
    
    # Run server with stdio transport
    async with stdio_server() as (read_stream, write_stream):
        logger.info("Server running on stdio transport")
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
