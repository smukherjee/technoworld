"""
ICICI Bank Statement Parser using Camelot library.
This parser uses Camelot for more advanced table extraction from PDF files.
"""

import logging
import re
import pandas as pd
import camelot
from datetime import datetime
from .base_parser import BankStatementParser


class ICICIParserCamelot(BankStatementParser):
    """ICICI Bank statement parser using Camelot library for table extraction."""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Date patterns for ICICI statements
        self.date_patterns = [
            r'\b(\d{2})-(\d{2})-(\d{4})\b',      # DD-MM-YYYY
            r'\b(\d{2})/(\d{2})/(\d{4})\b',      # DD/MM/YYYY
            r'\b(\d{1,2})-(\d{1,2})-(\d{4})\b',  # D-M-YYYY or DD-M-YYYY
            r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b',  # D/M/YYYY or DD/M/YYYY
        ]
        
        # Amount patterns
        self.amount_patterns = [
            r'^\d{1,3}(?:,\d{3})*(?:\.\d{2})?$',  # Standard currency format
            r'^\d+(?:\.\d{2})?$',                  # Simple decimal format
        ]
        
    def parse(self, file_path):
        """Parse ICICI bank statement PDF using Camelot."""
        self.logger.info(f"Starting to parse ICICI statement: {file_path}")
        
        try:
            # Extract all tables from the PDF using Camelot
            # Use 'lattice' method for tables with clear borders
            tables = camelot.read_pdf(
                file_path, 
                pages='all',
                flavor='lattice',
                table_areas=None,
                columns=None,
                split_text=False,
                flag_size=True,
                strip_text='\n'
            )
            
            self.logger.info(f"Found {len(tables)} tables using lattice method")
            
            if len(tables) == 0:
                # Fallback to 'stream' method for tables without clear borders
                self.logger.info("No tables found with lattice method, trying stream method")
                tables = camelot.read_pdf(
                    file_path,
                    pages='all',
                    flavor='stream',
                    table_areas=None,
                    columns=None,
                    edge_tol=500,
                    row_tol=10,
                    column_tol=0
                )
                self.logger.info(f"Found {len(tables)} tables using stream method")
            
            all_transactions = []
            
            for i, table in enumerate(tables):
                self.logger.debug(f"Processing table {i+1}/{len(tables)} - Shape: {table.df.shape}")
                transactions = self._extract_transactions_from_table(table.df, i+1)
                all_transactions.extend(transactions)
            
            self.logger.info(f"Extracted {len(all_transactions)} total transactions")
            
            # Convert to DataFrame
            if all_transactions:
                df = pd.DataFrame(all_transactions)
                df = self._clean_dataframe(df)
                return df
            else:
                self.logger.warning("No transactions found in the PDF")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"Error parsing PDF: {str(e)}")
            raise
    
    def _extract_transactions_from_table(self, df, table_num):
        """Extract transactions from a single table DataFrame."""
        transactions = []
        
        if df.empty:
            return transactions
        
        self.logger.debug(f"Table {table_num} columns: {df.columns.tolist()}")
        self.logger.debug(f"Table {table_num} shape: {df.shape}")
        
        # Find the header row and identify column structure
        header_info = self._identify_table_structure(df)
        
        if not header_info:
            self.logger.debug(f"Could not identify table structure for table {table_num}")
            return transactions
        
        header_row = header_info['header_row']
        col_mapping = header_info['columns']
        
        self.logger.debug(f"Table {table_num} structure: {col_mapping}")
        
        # Process data rows (after header)
        for idx in range(header_row + 1, len(df)):
            row = df.iloc[idx]
            
            # Skip empty rows
            if row.isna().all() or (row == '').all():
                continue
            
            # Extract transaction data
            transaction = self._extract_transaction_from_row(row, col_mapping)
            
            if transaction:
                transactions.append(transaction)
        
        self.logger.debug(f"Extracted {len(transactions)} transactions from table {table_num}")
        return transactions
    
    def _identify_table_structure(self, df):
        """Identify the table structure and column mappings."""
        header_keywords = {
            'date': ['date', 'transaction date', 'value date', 'tran date'],
            'description': ['description', 'particulars', 'transaction details', 'narration'],
            'credit': ['credit', 'deposit', 'cr'],
            'debit': ['debit', 'withdrawal', 'dr'],
            'balance': ['balance', 'closing balance', 'running balance']
        }
        
        # Search for header row
        for row_idx in range(min(10, len(df))):  # Check first 10 rows
            row = df.iloc[row_idx]
            row_text = ' '.join(str(cell).lower().strip() for cell in row if str(cell).strip())
            
            # Check if this row contains header keywords
            header_score = 0
            col_mapping = {}
            
            for col_idx, cell in enumerate(row):
                cell_text = str(cell).lower().strip()
                
                for field, keywords in header_keywords.items():
                    if any(keyword in cell_text for keyword in keywords):
                        col_mapping[field] = col_idx
                        header_score += 1
                        break
            
            # If we found at least date and one amount column, consider it a header
            if header_score >= 2 and 'date' in col_mapping:
                self.logger.debug(f"Found header at row {row_idx}: {col_mapping}")
                return {
                    'header_row': row_idx,
                    'columns': col_mapping
                }
        
        # Fallback: assume standard ICICI format
        if len(df.columns) >= 4:
            self.logger.debug("Using fallback column mapping")
            return {
                'header_row': 0,
                'columns': {
                    'date': 0,
                    'description': 1,
                    'credit': 2 if len(df.columns) == 4 else 2,
                    'debit': 3 if len(df.columns) == 4 else 3,
                    'balance': 4 if len(df.columns) > 4 else None
                }
            }
        
        return None
    
    def _extract_transaction_from_row(self, row, col_mapping):
        """Extract transaction data from a table row."""
        try:
            # Extract date
            if 'date' not in col_mapping:
                return None
                
            date_text = str(row.iloc[col_mapping['date']]).strip()
            parsed_date = self._parse_date(date_text)
            
            if not parsed_date:
                return None
            
            # Extract description
            description = ""
            if 'description' in col_mapping:
                desc_col = col_mapping['description']
                if desc_col < len(row):
                    description = str(row.iloc[desc_col]).strip()
            
            # Extract amounts
            credit_amount = ""
            debit_amount = ""
            balance = ""
            
            if 'credit' in col_mapping and col_mapping['credit'] < len(row):
                credit_text = str(row.iloc[col_mapping['credit']]).strip()
                if self._is_valid_amount(credit_text):
                    credit_amount = self._clean_amount(credit_text)
            
            if 'debit' in col_mapping and col_mapping['debit'] < len(row):
                debit_text = str(row.iloc[col_mapping['debit']]).strip()
                if self._is_valid_amount(debit_text):
                    debit_amount = self._clean_amount(debit_text)
            
            if 'balance' in col_mapping and col_mapping['balance'] and col_mapping['balance'] < len(row):
                balance_text = str(row.iloc[col_mapping['balance']]).strip()
                if self._is_valid_amount(balance_text):
                    balance = self._clean_amount(balance_text)
            
            # Skip rows without valid amounts
            if not credit_amount and not debit_amount:
                return None
            
            return {
                'Date': parsed_date,
                'Description': description,
                'Credit': credit_amount,
                'Debit': debit_amount,
                'Balance': balance
            }
            
        except Exception as e:
            self.logger.debug(f"Error extracting transaction from row: {e}")
            return None
    
    def _parse_date(self, date_text):
        """Parse date from text using multiple patterns."""
        if not date_text or date_text.lower() in ['nan', 'none', '']:
            return None
        
        for pattern in self.date_patterns:
            match = re.search(pattern, date_text)
            if match:
                try:
                    day, month, year = match.groups()
                    date_obj = datetime(int(year), int(month), int(day))
                    return date_obj.strftime('%d-%m-%Y')
                except ValueError:
                    continue
        
        return None
    
    def _is_valid_amount(self, amount_text):
        """Check if text represents a valid amount."""
        if not amount_text or amount_text.lower() in ['nan', 'none', '', '-']:
            return False
        
        # Clean the amount text
        cleaned = re.sub(r'[^\d.,]', '', amount_text)
        
        for pattern in self.amount_patterns:
            if re.match(pattern, cleaned):
                return True
        
        return False
    
    def _clean_amount(self, amount_text):
        """Clean and format amount text."""
        if not amount_text:
            return ""
        
        # Remove currency symbols and extra whitespace
        cleaned = re.sub(r'[^\d.,]', '', amount_text)
        
        # Remove commas used as thousand separators
        cleaned = cleaned.replace(',', '')
        
        try:
            # Convert to float and back to string to standardize format
            amount = float(cleaned)
            return f"{amount:.2f}"
        except ValueError:
            return ""
    
    def _clean_dataframe(self, df):
        """Clean and validate the final DataFrame."""
        # Remove rows where both credit and debit are empty
        df = df[~((df['Credit'] == '') & (df['Debit'] == ''))]
        
        # Sort by date
        df['Date_obj'] = pd.to_datetime(df['Date'], format='%d-%m-%Y', errors='coerce')
        df = df.sort_values('Date_obj')
        df = df.drop('Date_obj', axis=1)
        
        # Reset index
        df = df.reset_index(drop=True)
        
        self.logger.info(f"Final dataset contains {len(df)} valid transactions")
        return df
