#!/usr/bin/env python3
"""
Database Schema Exploration Script

This script connects to the AWB Editor PostgreSQL database and provides
tools for exploring the schema, understanding table relationships,
and generating documentation.

Usage:
    python explore_database.py --help
    python explore_database.py list-tables
    python explore_database.py describe-table document
    python explore_database.py count-all
    python explore_database.py sample-data document 5
"""

import os
import sys
import argparse
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, inspect, text, MetaData
from sqlalchemy.orm import sessionmaker
from tabulate import tabulate

# Database connection - modify these or use environment variables
DATABASE_URL = os.getenv(
    "AWB_DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/awb_editor"
)


def get_engine():
    """Create database engine."""
    return create_engine(DATABASE_URL, echo=False)


def list_tables(engine):
    """List all tables in the database."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print(f"\n{'='*60}")
    print(f"Database Tables ({len(tables)} total)")
    print(f"{'='*60}\n")
    
    for i, table in enumerate(sorted(tables), 1):
        print(f"  {i:2}. {table}")
    
    print()


def describe_table(engine, table_name: str):
    """Describe a specific table's structure."""
    inspector = inspect(engine)
    
    # Check if table exists
    if table_name not in inspector.get_table_names():
        print(f"Error: Table '{table_name}' not found")
        return
    
    # Get columns
    columns = inspector.get_columns(table_name)
    
    # Get primary keys
    pk_constraint = inspector.get_pk_constraint(table_name)
    pk_columns = set(pk_constraint.get('constrained_columns', []))
    
    # Get foreign keys
    fk_constraints = inspector.get_foreign_keys(table_name)
    fk_map = {fk['constrained_columns'][0]: fk for fk in fk_constraints if fk['constrained_columns']}
    
    # Get indexes
    indexes = inspector.get_indexes(table_name)
    indexed_columns = set()
    for idx in indexes:
        indexed_columns.update(idx['column_names'])
    
    print(f"\n{'='*80}")
    print(f"Table: {table_name}")
    print(f"{'='*80}\n")
    
    # Column details
    table_data = []
    for col in columns:
        col_name = col['name']
        col_type = str(col['type'])
        nullable = "YES" if col.get('nullable', True) else "NO"
        default = col.get('default', '')
        
        # Markers
        markers = []
        if col_name in pk_columns:
            markers.append("PK")
        if col_name in fk_map:
            ref = fk_map[col_name]
            markers.append(f"FK→{ref['referred_table']}")
        if col_name in indexed_columns:
            markers.append("IDX")
        
        table_data.append([
            col_name,
            col_type,
            nullable,
            default or '',
            ', '.join(markers)
        ])
    
    print(tabulate(
        table_data,
        headers=['Column', 'Type', 'Nullable', 'Default', 'Keys/Indexes'],
        tablefmt='grid'
    ))
    
    # Foreign key details
    if fk_constraints:
        print(f"\nForeign Keys:")
        for fk in fk_constraints:
            local_cols = ', '.join(fk['constrained_columns'])
            ref_table = fk['referred_table']
            ref_cols = ', '.join(fk['referred_columns'])
            print(f"  • {local_cols} → {ref_table}({ref_cols})")
    
    print()


def count_all_tables(engine):
    """Count rows in all tables."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print(f"\n{'='*50}")
    print("Row Counts")
    print(f"{'='*50}\n")
    
    counts = []
    for table in sorted(tables):
        try:
            result = session.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
            count = result.scalar()
            counts.append([table, f"{count:,}"])
        except Exception as e:
            counts.append([table, f"Error: {e}"])
    
    session.close()
    
    print(tabulate(counts, headers=['Table', 'Row Count'], tablefmt='simple'))
    
    # Total
    total = sum(int(c[1].replace(',', '')) for c in counts if not c[1].startswith('Error'))
    print(f"\nTotal rows: {total:,}")
    print()


def sample_data(engine, table_name: str, limit: int = 5):
    """Show sample data from a table."""
    inspector = inspect(engine)
    
    if table_name not in inspector.get_table_names():
        print(f"Error: Table '{table_name}' not found")
        return
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get column names
        columns = inspector.get_columns(table_name)
        col_names = [col['name'] for col in columns]
        
        # Skip binary columns for display
        display_cols = [c for c in col_names if not any(
            x in c.lower() for x in ['data', 'image', 'blob']
        )]
        
        cols_str = ', '.join(f'"{c}"' for c in display_cols[:10])  # Limit columns
        
        result = session.execute(
            text(f'SELECT {cols_str} FROM "{table_name}" LIMIT {limit}')
        )
        rows = result.fetchall()
        
        print(f"\n{'='*80}")
        print(f"Sample Data: {table_name} ({len(rows)} rows)")
        print(f"{'='*80}\n")
        
        if rows:
            # Format data
            data = []
            for row in rows:
                formatted_row = []
                for val in row:
                    if val is None:
                        formatted_row.append('NULL')
                    elif isinstance(val, datetime):
                        formatted_row.append(val.strftime('%Y-%m-%d %H:%M'))
                    elif isinstance(val, str) and len(val) > 30:
                        formatted_row.append(val[:27] + '...')
                    else:
                        formatted_row.append(str(val))
                data.append(formatted_row)
            
            print(tabulate(
                data,
                headers=display_cols[:10],
                tablefmt='grid',
                maxcolwidths=30
            ))
        else:
            print("No data found")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()
    
    print()


def generate_erd_summary(engine):
    """Generate a summary of table relationships."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print(f"\n{'='*60}")
    print("Entity Relationship Summary")
    print(f"{'='*60}\n")
    
    relationships = []
    
    for table in sorted(tables):
        fks = inspector.get_foreign_keys(table)
        for fk in fks:
            if fk['constrained_columns'] and fk['referred_columns']:
                local_col = fk['constrained_columns'][0]
                ref_table = fk['referred_table']
                ref_col = fk['referred_columns'][0]
                relationships.append([
                    table,
                    local_col,
                    '→',
                    ref_table,
                    ref_col
                ])
    
    if relationships:
        print(tabulate(
            relationships,
            headers=['Table', 'Column', '', 'References', 'Column'],
            tablefmt='simple'
        ))
    else:
        print("No foreign key relationships found")
    
    print()


def main():
    parser = argparse.ArgumentParser(
        description='AWB Database Schema Explorer',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List tables command
    subparsers.add_parser('list-tables', help='List all tables')
    
    # Describe table command
    desc_parser = subparsers.add_parser('describe-table', help='Describe a table')
    desc_parser.add_argument('table', help='Table name')
    
    # Count all command
    subparsers.add_parser('count-all', help='Count rows in all tables')
    
    # Sample data command
    sample_parser = subparsers.add_parser('sample-data', help='Show sample data')
    sample_parser.add_argument('table', help='Table name')
    sample_parser.add_argument('limit', type=int, nargs='?', default=5, help='Number of rows')
    
    # ERD summary command
    subparsers.add_parser('erd', help='Show entity relationships')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        engine = get_engine()
        
        if args.command == 'list-tables':
            list_tables(engine)
        elif args.command == 'describe-table':
            describe_table(engine, args.table)
        elif args.command == 'count-all':
            count_all_tables(engine)
        elif args.command == 'sample-data':
            sample_data(engine, args.table, args.limit)
        elif args.command == 'erd':
            generate_erd_summary(engine)
            
    except Exception as e:
        print(f"Database connection error: {e}")
        print("\nMake sure to set the AWB_DATABASE_URL environment variable or edit the script.")
        sys.exit(1)


if __name__ == '__main__':
    main()

