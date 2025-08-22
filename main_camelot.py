#!/usr/bin/env python3
"""
Test script for ICICI parser using Camelot library.
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    # Import after setting up path
    from bank_statement_parser.icici_parser_camelot import ICICIParserCamelot
    
    logger = logging.getLogger(__name__)
    
    # File paths
    pdf_file = "accountparser/ICICI Saving Acc 11117 - PW_KRIS2705 copy.pdf"
    output_file = "accountparser/ICICI Saving Acc 11117 - PW_KRIS2705 copy_camelot.csv"
    password = "KRIS2705"  # PDF password
    
    if not os.path.exists(pdf_file):
        logger.error(f"PDF file not found: {pdf_file}")
        return
    
    try:
        # Initialize parser with password
        parser = ICICIParserCamelot(pdf_file, password)
        
        # Parse the PDF
        logger.info(f"Parsing PDF file: {pdf_file}")
        transactions_df = parser.process_pdf()
        
        if transactions_df.empty:
            logger.warning("No transactions extracted from the PDF")
            return
        
        # Save to CSV
        transactions_df.to_csv(output_file, index=False)
        logger.info(f"Saved transactions to {output_file}")
        logger.info(f"\nExtracted {len(transactions_df)} transactions")
        
        # Display first few transactions
        logger.info(f"\nFirst 5 transactions:")
        logger.info(f"\n{transactions_df.head().to_string()}")
        
        # Display summary statistics
        logger.info(f"\nSummary:")
        logger.info(f"Total transactions: {len(transactions_df)}")
        logger.info(f"Date range: {transactions_df['Date'].min()} to {transactions_df['Date'].max()}")
        
        # Count credit vs debit transactions
        credit_count = len(transactions_df[transactions_df['Credit'] != ''])
        debit_count = len(transactions_df[transactions_df['Debit'] != ''])
        logger.info(f"Credit transactions: {credit_count}")
        logger.info(f"Debit transactions: {debit_count}")
        
    except Exception as e:
        logger.error(f"Error parsing PDF: {e}", exc_info=True)

if __name__ == "__main__":
    main()
