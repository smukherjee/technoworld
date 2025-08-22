"""
Main script to process ICICI bank statement from Excel file and classify transactions.
This script uses only the Excel file and creates beancount entries with classifications.
"""

import os
import pandas as pd
from excel_parser import ExcelTransactionParser
from transaction_classifier_new import TransactionClassifier
from beancount_import_processor import integrate_with_main_workflow
import logging

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('beancount_processor.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def main():
    """Main function to process Excel file and generate classified beancount entries."""
    logger = setup_logging()
    
    # File paths
    # excel_file = "/Users/sujoymukherjee/code/technoworld/beancount/OpTransactionHistory15-08-2025.xls"
    # output_csv = "/Users/sujoymukherjee/code/technoworld/beancount/classified_OpTransactionHistory15-08-2025.csv"
    # output_beancount = "/Users/sujoymukherjee/code/technoworld/beancount/transactions_OpTransactionHistory15-08-2025.beancount"

    excel_file = "/Users/sujoymukherjee/code/technoworld/beancount/parsed_transactions.xlsx"
    output_csv = "/Users/sujoymukherjee/code/technoworld/beancount/classified_parsed_transactions.csv"
    output_beancount = "/Users/sujoymukherjee/code/technoworld/beancount/transactions_parsed_transactions.beancount"

    # Check if Excel file exists
    if not os.path.exists(excel_file):
        logger.error(f"Excel file not found: {excel_file}")
        logger.info("Please ensure the file 'OpTransactionHistory15-08-2025.xls' is in the current directory")
        return
    
    try:
        # Step 1: Parse Excel file
        logger.info(f"Parsing Excel file: {excel_file}")
        parser = ExcelTransactionParser()
        transactions_df = parser.parse_excel(excel_file)
        
        if transactions_df.empty:
            logger.error("No transactions found in the Excel file")
            return
        
        logger.info(f"Successfully parsed {len(transactions_df)} transactions")
        
        # Step 2: Classify transactions
        logger.info("Classifying transactions...")
        classifier = TransactionClassifier()
        classified_df = classifier.classify_transactions(transactions_df)
        
        # Step 3: Save classified transactions to CSV
        logger.info(f"Saving classified transactions to: {output_csv}")
        classified_df.to_csv(output_csv, index=False)
        
        # Step 4: Generate beancount file
        logger.info(f"Generating beancount file: {output_beancount}")
        classifier.save_beancount_file(classified_df, output_beancount, "Assets:Bank:ICICI:Checking")
        
        # Step 5: Enhanced post-processing with beancount-import
        logger.info("Starting beancount-import post-processing...")
        post_process_results = integrate_with_main_workflow(
            classified_df, 
            source_account="Assets:Bank:ICICI:Checking",
            enable_post_processing=True
        )
        
        if post_process_results.get('success', False):
            logger.info("Beancount-import post-processing completed successfully!")
            logger.info(f"Enhanced transactions: {post_process_results.get('enhanced_transactions', 'N/A')}")
            logger.info(f"Web interface files: {post_process_results.get('output_directory', 'N/A')}")
            logger.info("To start the web interface:")
            logger.info(f"  cd {post_process_results.get('output_directory', '')}")
            logger.info("  python web/start_web_interface.py")
        else:
            logger.warning(f"Beancount-import post-processing failed: {post_process_results.get('message', 'Unknown error')}")
        
        # Step 6: Print summary
        print_summary(classified_df, logger, post_process_results)
        
        logger.info("Processing completed successfully!")
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise

def print_summary(df: pd.DataFrame, logger, post_process_results: dict = None):
    """Print a summary of the processed transactions."""
    logger.info("\n" + "="*50)
    logger.info("TRANSACTION PROCESSING SUMMARY")
    logger.info("="*50)
    
    # Basic statistics
    total_transactions = len(df)
    total_credits = len(df[df['Credit'].notna() & (df['Credit'] != '0.00')])
    total_debits = len(df[df['Debit'].notna() & (df['Debit'] != '0.00')])
    
    logger.info(f"Total Transactions: {total_transactions}")
    logger.info(f"Credit Transactions: {total_credits}")
    logger.info(f"Debit Transactions: {total_debits}")
    
    # Amount calculations
    try:
        credits_sum = df[df['Credit'].notna()]['Credit'].astype(str).str.replace(',', '').astype(float).sum()
        debits_sum = df[df['Debit'].notna()]['Debit'].astype(str).str.replace(',', '').astype(float).sum()
        
        logger.info(f"Total Credits: ₹{credits_sum:,.2f}")
        logger.info(f"Total Debits: ₹{debits_sum:,.2f}")
        logger.info(f"Net Amount: ₹{credits_sum - debits_sum:,.2f}")
    except Exception as e:
        logger.warning(f"Could not calculate amounts: {e}")
    
    # Category breakdown
    logger.info("\nCategory Breakdown:")
    category_counts = df['Category'].value_counts()
    for category, count in category_counts.head(10).items():
        percentage = (count / total_transactions) * 100
        logger.info(f"  {category}: {count} ({percentage:.1f}%)")
    
    # Date range
    try:
        date_col = df['Date'].dropna()
        if not date_col.empty:
            # Try to parse dates to find range
            dates = pd.to_datetime(date_col, format='%d-%m-%Y', errors='coerce').dropna()
            if not dates.empty:
                logger.info(f"\nDate Range: {dates.min().strftime('%d-%m-%Y')} to {dates.max().strftime('%d-%m-%Y')}")
    except Exception as e:
        logger.warning(f"Could not determine date range: {e}")
    
    logger.info("="*50)
    
    # Post-processing summary
    if post_process_results and post_process_results.get('success', False):
        logger.info("\nBEANCOUNT-IMPORT POST-PROCESSING:")
        logger.info(f"Enhanced transactions file: {post_process_results.get('enhanced_transactions', 'N/A')}")
        logger.info(f"Output directory: {post_process_results.get('output_directory', 'N/A')}")
        logger.info(f"Web interface available: {bool(post_process_results.get('web_interface'))}")
        
        if post_process_results.get('web_interface'):
            logger.info("\nTo start the enhanced web interface:")
            web_dir = post_process_results['web_interface'].get('web_directory', '')
            if web_dir:
                logger.info(f"  cd {web_dir}")
                logger.info("  python start_web_interface.py")
                logger.info("  Open http://localhost:8080 in your browser")
        
        logger.info("\nEnhanced features available:")
        logger.info("  ✓ Machine Learning-based account prediction")
        logger.info("  ✓ Web-based transaction review interface")
        logger.info("  ✓ Training system for improved classification")
        logger.info("  ✓ Duplicate transaction detection")
        logger.info("  ✓ Advanced reconciliation capabilities")
    
    logger.info("="*50)

if __name__ == "__main__":
    main()
