from pathlib import Path
import logging
import pandas as pd
from bank_statement_parser.icici_parser_new import ICICIParser

# Set up logging
logging.basicConfig(
    level=logging.INFO,  # Changed from DEBUG to INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress pdfminer debug logs
logging.getLogger('pdfminer').setLevel(logging.WARNING)

def main():
    """Main entry point"""
    pdf_path = "accountparser/ICICI Saving Acc 11117 - PW_KRIS2705 copy.pdf"
    process_bank_statement(pdf_path, "ICICI", "KRIS2705")

def process_bank_statement(pdf_path: str, bank_type: str, password: str = None) -> None:
    """Process a bank statement and save to CSV"""
    try:
        # Validate PDF path
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
        # Use the new ICICI parser directly
        if bank_type.upper() == "ICICI":
            parser = ICICIParser(pdf_path, password)
        else:
            raise ValueError(f"Bank type {bank_type} not supported")
        
        # Log initial settings
        logger.info(f"Processing {bank_type} bank statement: {pdf_path}")
        if password:
            logger.info("Using password-protected PDF")
        
        # Process the PDF
        transactions = parser.extract_transactions()
        
        if not transactions:
            logger.warning("No transactions were extracted from the PDF")
            return
            
        # Convert to DataFrame
        df = pd.DataFrame(transactions)
        logger.debug(f"DataFrame columns: {df.columns.tolist()}")
        
        # Basic validation
        required_cols = ['Date', 'Description']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return
        
        # Save to CSV
        csv_path = str(Path(pdf_path).with_suffix('.csv'))
        df.to_csv(csv_path, index=False)
        logger.info(f"Saved transactions to {csv_path}")
        
        # Display summary
        logger.info(f"\nExtracted {len(df)} transactions")
        logger.info("\nFirst 5 transactions:")
        if not df.empty:
            logger.info("\n" + df.head().to_string())
            
    except FileNotFoundError as e:
        logger.error(str(e))
        raise
    except Exception as e:
        logger.error(f"Error processing bank statement: {str(e)}")
        logger.debug("Full error details:", exc_info=True)
        raise

if __name__ == "__main__":
    main()