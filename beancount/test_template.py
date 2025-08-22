"""
Test script for template-based Excel parsing.
This script demonstrates how to use the template system to parse Excel files.
"""

import pandas as pd
import logging
from excel_parser import ExcelTransactionParser
from excel_template_manager import ExcelTemplateManager

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def test_template_parsing():
    """Test the template-based parsing system."""
    logger = setup_logging()
    
    # Test files
    excel_file = "OpTransactionHistory15-08-2025.xls"
    template_file = "excel_template.json"
    
    try:
        # Test 1: Load and display template info
        logger.info("=== Testing Template Manager ===")
        template_manager = ExcelTemplateManager(template_file)
        template_info = template_manager.get_template_info()
        
        logger.info(f"Template Name: {template_info.get('name')}")
        logger.info(f"Bank: {template_info.get('bank')}")
        logger.info(f"Expected Columns: {template_info.get('columns')}")
        
        # Test 2: Parse Excel file with template
        logger.info("\n=== Testing Template-based Parsing ===")
        parser = ExcelTransactionParser(template_file)
        
        # Read the raw Excel file first to show structure
        df_raw = pd.read_excel(excel_file, engine='xlrd')
        logger.info(f"Raw Excel file has {len(df_raw)} rows and {len(df_raw.columns)} columns")
        
        # Show first few rows for inspection
        logger.info("First 20 rows of raw data:")
        for i in range(min(20, len(df_raw))):
            row_data = {}
            for j, col in enumerate(df_raw.columns):
                value = df_raw.iloc[i, j]
                if pd.notna(value) and str(value).strip():
                    row_data[f"Col_{j}"] = str(value)[:50]  # Truncate long values
            if row_data:
                logger.info(f"Row {i}: {row_data}")
        
        # Parse using template
        transactions_df = parser.parse_excel(excel_file)
        
        # Display results
        logger.info(f"\nParsed {len(transactions_df)} transactions")
        logger.info(f"Columns: {transactions_df.columns.tolist()}")
        
        # Show sample transactions
        if len(transactions_df) > 0:
            logger.info("\nSample transactions:")
            for i in range(min(5, len(transactions_df))):
                logger.info(f"Transaction {i+1}:")
                for col in transactions_df.columns:
                    value = transactions_df.iloc[i][col]
                    if value and str(value).strip():
                        logger.info(f"  {col}: {value}")
        
        # Test 3: Save results
        output_file = "template_parsed_transactions.csv"
        transactions_df.to_csv(output_file, index=False)
        logger.info(f"\nSaved parsed transactions to {output_file}")
        
        return transactions_df
        
    except Exception as e:
        logger.error(f"Error in template testing: {e}")
        raise

def create_custom_template():
    """Create a custom template based on the actual Excel file structure."""
    logger = setup_logging()
    
    try:
        # Read the Excel file to analyze structure
        excel_file = "OpTransactionHistory15-08-2025.xls"
        df = pd.read_excel(excel_file, engine='xlrd')
        
        logger.info("Analyzing Excel file structure...")
        logger.info(f"File has {len(df)} rows and {len(df.columns)} columns")
        
        # Look for header patterns in first 20 rows
        for i in range(min(20, len(df))):
            row_values = [str(val) for val in df.iloc[i].values if pd.notna(val)]
            if row_values:
                logger.info(f"Row {i}: {row_values}")
        
        # Create a custom template based on findings
        custom_template = {
            "template_name": "ICICI Bank Statement Custom Template",
            "description": "Custom template based on OpTransactionHistory15-08-2025.xls analysis",
            "version": "1.0",
            
            "header_detection": {
                "search_rows": [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
                "header_patterns": ["transaction date", "value date", "description", "debit", "credit", "balance"]
            },
            
            "data_mapping": {
                "column_mapping": {
                    "date": {
                        "possible_names": ["Transaction Date", "Date", "Trans Date"],
                        "column_index": 0,
                        "data_type": "date",
                        "date_format": ["%d/%m/%Y", "%d-%m-%Y"]
                    },
                    "value_date": {
                        "possible_names": ["Value Date"],
                        "column_index": 1,
                        "data_type": "date",
                        "date_format": ["%d/%m/%Y", "%d-%m-%Y"]
                    },
                    "description": {
                        "possible_names": ["Description", "Particulars"],
                        "column_index": 2,
                        "data_type": "string",
                        "clean_text": True
                    },
                    "reference": {
                        "possible_names": ["Chq/Ref Number", "Reference"],
                        "column_index": 3,
                        "data_type": "string",
                        "optional": True
                    },
                    "debit": {
                        "possible_names": ["Debit", "Withdrawal"],
                        "column_index": 4,
                        "data_type": "amount"
                    },
                    "credit": {
                        "possible_names": ["Credit", "Deposit"],
                        "column_index": 5,
                        "data_type": "amount"
                    },
                    "balance": {
                        "possible_names": ["Balance"],
                        "column_index": 6,
                        "data_type": "amount",
                        "optional": True
                    }
                }
            },
            
            "custom_overrides": {
                "force_header_row": 8,  # Based on manual inspection
                "force_data_start_row": 9
            }
        }
        
        # Save custom template
        template_manager = ExcelTemplateManager()
        template_manager.save_template(custom_template, "excel_template_custom.json")
        logger.info("Created custom template: excel_template_custom.json")
        
    except Exception as e:
        logger.error(f"Error creating custom template: {e}")
        raise

if __name__ == "__main__":
    print("Excel Template Testing")
    print("=" * 50)
    
    # First, create a custom template
    print("\n1. Creating custom template...")
    create_custom_template()
    
    # Then test the template parsing
    print("\n2. Testing template-based parsing...")
    test_template_parsing()
