"""
Excel Transaction Parser for Beancount
Parses Excel/XLS files containing bank transaction data.
"""

import pandas as pd
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import re
from excel_template_manager import ExcelTemplateManager


class ExcelTransactionParser:
    """Parser for Excel/XLS bank transaction files."""
    
    def __init__(self, template_file: str = "excel_template.json"):
        self.setup_logging()
        self.template_manager = ExcelTemplateManager(template_file)
        
    def setup_logging(self):
        """Set up logging for the parser."""
        self.logger = logging.getLogger(self.__class__.__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def parse_excel(self, file_path: str) -> pd.DataFrame:
        """Parse Excel file and return a DataFrame of transactions using template."""
        self.logger.info(f"Parsing Excel file: {file_path}")
        
        try:
            # Try to read the Excel file
            # First, try reading as .xls
            try:
                df = pd.read_excel(file_path, engine='xlrd')
                self.logger.info(f"Successfully read Excel file with xlrd engine")
            except Exception as e:
                self.logger.warning(f"Failed to read with xlrd: {e}")
                # Try with openpyxl engine
                try:
                    df = pd.read_excel(file_path, engine='openpyxl')
                    self.logger.info(f"Successfully read Excel file with openpyxl engine")
                except Exception as e2:
                    self.logger.error(f"Failed to read with openpyxl: {e2}")
                    raise e2
            
            self.logger.info(f"Read {len(df)} rows and {len(df.columns)} columns")
            self.logger.info(f"Columns: {df.columns.tolist()}")
            
            # Use template manager to parse the data
            if self.template_manager.template:
                self.logger.info("Using template-based parsing")
                return self.template_manager.parse_excel_with_template(df)
            else:
                self.logger.warning("No template available, falling back to generic parsing")
                return self._parse_excel_generic(df)
            
        except Exception as e:
            self.logger.error(f"Error parsing Excel file: {str(e)}")
            raise
    
    def _parse_excel_generic(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fallback generic parsing method."""
        # Clean and standardize the data
        df = self._clean_dataframe(df)
        
        # Convert to standard transaction format
        transactions_df = self._convert_to_standard_format(df)
        
        self.logger.info(f"Converted to {len(transactions_df)} transactions")
        return transactions_df
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean the raw DataFrame."""
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Remove columns that are completely empty
        df = df.dropna(axis=1, how='all')
        
        # Strip whitespace from string columns
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
        
        # Replace NaN values with empty strings for string columns
        df = df.fillna('')
        
        return df
    
    def _convert_to_standard_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert DataFrame to standard transaction format."""
        # First, let's examine the structure and identify columns
        self.logger.info("Analyzing DataFrame structure...")
        self.logger.info(f"DataFrame shape: {df.shape}")
        self.logger.info(f"Columns: {df.columns.tolist()}")
        
        # Display first few rows to understand structure
        self.logger.info("First 5 rows:")
        for i, row in df.head().iterrows():
            self.logger.info(f"Row {i}: {row.to_dict()}")
        
        # Try to identify common column patterns
        column_mapping = self._identify_columns(df)
        self.logger.info(f"Column mapping: {column_mapping}")
        
        if not column_mapping:
            self.logger.warning("Could not identify column structure, using generic approach")
            return self._generic_conversion(df)
        
        # Convert using identified columns
        return self._structured_conversion(df, column_mapping)
    
    def _identify_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """Identify which columns contain which type of data."""
        column_mapping = {}
        
        # Common patterns for different column types
        date_patterns = ['date', 'transaction date', 'value date', 'tran date', 'posting date']
        description_patterns = ['description', 'particulars', 'narration', 'transaction details', 'details']
        amount_patterns = ['amount', 'transaction amount']
        credit_patterns = ['credit', 'deposit', 'cr', 'credit amount']
        debit_patterns = ['debit', 'withdrawal', 'dr', 'debit amount', 'withdraw']
        balance_patterns = ['balance', 'running balance', 'closing balance', 'available balance']
        
        # Convert column names to lowercase for matching
        columns_lower = [str(col).lower().strip() for col in df.columns]
        
        # Try to match columns
        for i, col_name in enumerate(columns_lower):
            original_col = df.columns[i]
            
            # Check for date columns
            if any(pattern in col_name for pattern in date_patterns):
                column_mapping['date'] = original_col
            
            # Check for description columns
            elif any(pattern in col_name for pattern in description_patterns):
                column_mapping['description'] = original_col
            
            # Check for amount columns
            elif any(pattern in col_name for pattern in amount_patterns):
                column_mapping['amount'] = original_col
            
            # Check for credit columns
            elif any(pattern in col_name for pattern in credit_patterns):
                column_mapping['credit'] = original_col
            
            # Check for debit columns
            elif any(pattern in col_name for pattern in debit_patterns):
                column_mapping['debit'] = original_col
            
            # Check for balance columns
            elif any(pattern in col_name for pattern in balance_patterns):
                column_mapping['balance'] = original_col
        
        return column_mapping
    
    def _structured_conversion(self, df: pd.DataFrame, column_mapping: Dict[str, str]) -> pd.DataFrame:
        """Convert DataFrame using identified column structure."""
        transactions = []
        
        for _, row in df.iterrows():
            # Skip header rows or empty rows
            if self._is_header_row(row, column_mapping):
                continue
            
            transaction = {}
            
            # Extract date
            if 'date' in column_mapping:
                date_val = row[column_mapping['date']]
                parsed_date = self._parse_date(str(date_val))
                if parsed_date:
                    transaction['Date'] = parsed_date
                else:
                    continue  # Skip rows without valid dates
            
            # Extract description
            if 'description' in column_mapping:
                transaction['Description'] = str(row[column_mapping['description']])
            else:
                transaction['Description'] = 'Unknown Transaction'
            
            # Extract amounts
            credit_amount = ''
            debit_amount = ''
            
            if 'credit' in column_mapping:
                credit_val = str(row[column_mapping['credit']])
                if self._is_valid_amount(credit_val):
                    credit_amount = self._clean_amount(credit_val)
            
            if 'debit' in column_mapping:
                debit_val = str(row[column_mapping['debit']])
                if self._is_valid_amount(debit_val):
                    debit_amount = self._clean_amount(debit_val)
            
            # If we have a single amount column, determine if it's credit or debit
            if 'amount' in column_mapping and not credit_amount and not debit_amount:
                amount_val = str(row[column_mapping['amount']])
                if self._is_valid_amount(amount_val):
                    amount = self._clean_amount(amount_val)
                    # Check if amount is negative (debit) or positive (credit)
                    if amount.startswith('-'):
                        debit_amount = amount[1:]  # Remove negative sign
                    else:
                        credit_amount = amount
            
            transaction['Credit'] = credit_amount
            transaction['Debit'] = debit_amount
            
            # Extract balance if available
            if 'balance' in column_mapping:
                balance_val = str(row[column_mapping['balance']])
                if self._is_valid_amount(balance_val):
                    transaction['Balance'] = self._clean_amount(balance_val)
                else:
                    transaction['Balance'] = ''
            else:
                transaction['Balance'] = ''
            
            # Only add transaction if it has at least a date and either credit or debit
            if transaction.get('Date') and (transaction.get('Credit') or transaction.get('Debit')):
                transactions.append(transaction)
        
        return pd.DataFrame(transactions)
    
    def _generic_conversion(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generic conversion when column structure cannot be identified."""
        self.logger.info("Using generic conversion approach")
        
        transactions = []
        
        # Assume first few columns might be date, description, amount
        for _, row in df.iterrows():
            # Skip rows that look like headers
            if any('date' in str(val).lower() for val in row.values):
                continue
            
            transaction = {
                'Date': '',
                'Description': '',
                'Credit': '',
                'Debit': '',
                'Balance': ''
            }
            
            # Try to find date in first few columns
            for i, val in enumerate(row.values[:5]):
                date_val = self._parse_date(str(val))
                if date_val:
                    transaction['Date'] = date_val
                    break
            
            # If no date found, skip this row
            if not transaction['Date']:
                continue
            
            # Try to find description (usually text column)
            for val in row.values:
                val_str = str(val)
                if len(val_str) > 10 and not self._is_valid_amount(val_str):
                    transaction['Description'] = val_str
                    break
            
            # Try to find amounts
            amounts = []
            for val in row.values:
                if self._is_valid_amount(str(val)):
                    amounts.append(self._clean_amount(str(val)))
            
            # Assign amounts (assume first is debit, second is credit, or vice versa)
            if len(amounts) >= 1:
                # Simple heuristic: positive amounts are credits, negative are debits
                amount = amounts[0]
                if amount.startswith('-'):
                    transaction['Debit'] = amount[1:]
                else:
                    transaction['Credit'] = amount
            
            if len(amounts) >= 2:
                transaction['Balance'] = amounts[-1]  # Last amount might be balance
            
            transactions.append(transaction)
        
        return pd.DataFrame(transactions)
    
    def _is_header_row(self, row: pd.Series, column_mapping: Dict[str, str]) -> bool:
        """Check if a row is a header row."""
        # Check if any cell contains header-like text
        for val in row.values:
            val_str = str(val).lower()
            if any(header in val_str for header in ['date', 'description', 'amount', 'credit', 'debit', 'balance']):
                return True
        return False
    
    def _parse_date(self, date_text: str) -> Optional[str]:
        """Parse date from text using multiple patterns."""
        if not date_text or date_text.lower() in ['nan', 'none', '']:
            return None
        
        # Common date patterns
        date_patterns = [
            r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b',      # DD/MM/YYYY or DD-MM-YYYY
            r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b',      # YYYY/MM/DD or YYYY-MM-DD
            r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2})\b',      # DD/MM/YY or DD-MM-YY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_text)
            if match:
                try:
                    groups = match.groups()
                    if len(groups[2]) == 4:  # Full year
                        if int(groups[0]) > 12:  # First number > 12, so it's DD/MM/YYYY
                            day, month, year = groups
                        else:  # Could be MM/DD/YYYY or DD/MM/YYYY, assume DD/MM/YYYY for Indian context
                            day, month, year = groups
                    else:  # 2-digit year
                        day, month, year = groups
                        year = '20' + year if int(year) < 50 else '19' + year
                    
                    date_obj = datetime(int(year), int(month), int(day))
                    return date_obj.strftime('%d-%m-%Y')
                except ValueError:
                    continue
        
        # Try to parse as pandas datetime
        try:
            parsed = pd.to_datetime(date_text, errors='coerce')
            if pd.notna(parsed):
                return parsed.strftime('%d-%m-%Y')
        except:
            pass
        
        return None
    
    def _is_valid_amount(self, amount_text: str) -> bool:
        """Check if text represents a valid amount."""
        if not amount_text or amount_text.lower() in ['nan', 'none', '', '-']:
            return False
        
        # Remove currency symbols and whitespace
        cleaned = re.sub(r'[₹$€£,\s]', '', amount_text)
        
        # Check if it looks like a number (including negative)
        pattern = r'^-?\d+(?:\.\d{2})?$'
        return bool(re.match(pattern, cleaned))
    
    def _clean_amount(self, amount_text: str) -> str:
        """Clean and format amount text."""
        if not amount_text:
            return ""
        
        # Remove currency symbols and commas
        cleaned = re.sub(r'[₹$€£,\s]', '', amount_text)
        
        try:
            # Convert to float and back to string to standardize format
            amount = float(cleaned)
            return f"{amount:.2f}"
        except ValueError:
            return ""
