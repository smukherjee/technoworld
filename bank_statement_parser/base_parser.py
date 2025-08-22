from abc import ABC, abstractmethod
from pathlib import Path
import pandas as pd
import re
from typing import List, Dict, Any, Optional

class BankStatementParser(ABC):
    """Abstract base class for bank statement parsers"""
    
    def __init__(self, pdf_path: str, password: Optional[str] = None):
        self.pdf_path = Path(pdf_path)
        self.password = password
        self.doc = None
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        """Set up logging for the parser"""
        import logging
        logger = logging.getLogger(self.__class__.__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    @abstractmethod
    def extract_transactions(self) -> List[Dict[str, Any]]:
        """Extract transactions from the PDF"""
        pass
    
    @abstractmethod
    def parse_transaction_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single transaction line"""
        pass
    
    def process_pdf(self) -> pd.DataFrame:
        """Process the PDF and return a DataFrame of transactions"""
        try:
            self.logger.info(f"Processing PDF: {self.pdf_path}")
            
            transactions = self.extract_transactions()
            self.logger.info(f"Extracted {len(transactions)} transactions")
            
            df = pd.DataFrame(transactions)
            df = self.standardize_dataframe(df)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error processing PDF: {str(e)}")
            raise
    
    def standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize the DataFrame format"""
        if df.empty:
            return pd.DataFrame(columns=['Date', 'Description', 'Credit', 'Debit', 'Balance'])
        
        # Ensure all required columns exist
        required_columns = ['Date', 'Description', 'Credit', 'Debit', 'Balance']
        for col in required_columns:
            if col not in df.columns:
                df[col] = ''
        
        # Convert amounts to float
        for col in ['Credit', 'Debit', 'Balance']:
            df[col] = df[col].apply(self.convert_amount_to_float)
        
        # Convert dates to datetime
        df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y', errors='coerce')
        
        # Sort by date
        df = df.sort_values('Date').reset_index(drop=True)
        
        # Remove duplicates
        df = df.drop_duplicates().reset_index(drop=True)
        
        return df[required_columns]
    
    @staticmethod
    def convert_amount_to_float(amount: Any) -> float:
        """Convert amount string to float"""
        if pd.isna(amount) or amount == '':
            return 0.0
        
        if isinstance(amount, (int, float)):
            return float(amount)
        
        # Remove any currency symbols and commas
        amount_str = str(amount)
        amount_str = re.sub(r'[^\d.-]', '', amount_str)
        
        try:
            return float(amount_str)
        except ValueError:
            return 0.0
    
    def validate_transactions(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate extracted transactions"""
        valid_transactions = []
        
        for transaction in transactions:
            if self.is_valid_transaction(transaction):
                valid_transactions.append(transaction)
            else:
                self.logger.warning(f"Invalid transaction found: {transaction}")
        
        return valid_transactions
    
    def is_valid_transaction(self, transaction: Dict[str, Any]) -> bool:
        """Check if a transaction is valid"""
        required_fields = ['Date', 'Description']
        
        # Check required fields exist and are not empty
        for field in required_fields:
            if field not in transaction or not transaction[field]:
                return False
        
        # Validate date format
        date_str = transaction['Date']
        if not re.match(r'^\d{2}-\d{2}-\d{4}$', str(date_str)):
            return False
        
        return True
