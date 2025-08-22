"""
ICICI Bank Statement Parser - Clean Implementation
This parser extracts transaction data from ICICI bank PDF statements.
"""

from typing import List, Dict, Any, Optional, Tuple
import re
import logging
import pandas as pd
import pdfplumber
from datetime import datetime
from .base_parser import BankStatementParser


class ICICIParser(BankStatementParser):
    """Clean implementation of ICICI Bank statement parser"""
    
    def __init__(self, pdf_path: str, password: Optional[str] = None):
        super().__init__(pdf_path, password)
        self.setup_logging()
        self.setup_patterns()
        
    def setup_logging(self):
        """Set up detailed logging"""
        self.logger.setLevel(logging.DEBUG)
        
    def setup_patterns(self):
        """Define regex patterns for transaction parsing"""
        # Date pattern: DD-MM-YYYY or DD/MM/YYYY
        self.date_pattern = r'\b(\d{2}[-/]\d{2}[-/]\d{4})\b'
        
        # Amount pattern: Numbers with optional commas and decimal
        self.amount_pattern = r'\b(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\b'
        
        # Transaction type indicators
        self.credit_indicators = ['credit', 'deposit', 'transfer credit', 'imps cr', 'neft cr']
        self.debit_indicators = ['debit', 'withdrawal', 'transfer debit', 'imps dr', 'neft dr']
        
    def extract_transactions(self) -> List[Dict[str, Any]]:
        """Main method to extract transactions from PDF"""
        transactions = []
        
        try:
            with pdfplumber.open(self.pdf_path, password=self.password) as pdf:
                self.logger.info(f"Opening PDF with {len(pdf.pages)} pages")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    self.logger.info(f"Processing page {page_num}")
                    page_transactions = self._process_page(page, page_num)
                    transactions.extend(page_transactions)
                    
        except Exception as e:
            self.logger.error(f"Error reading PDF: {e}")
            raise
            
        self.logger.info(f"Extracted {len(transactions)} total transactions")
        return self.validate_transactions(transactions)
    
    def _process_page(self, page, page_num: int) -> List[Dict[str, Any]]:
        """Process a single page to extract transactions"""
        transactions = []
        
        # Strategy 1: Try table extraction
        tables = self._extract_tables_from_page(page)
        if tables:
            for table_idx, table in enumerate(tables):
                self.logger.debug(f"Processing table {table_idx} on page {page_num}")
                table_transactions = self._process_table(table)
                transactions.extend(table_transactions)
        
        # Strategy 2: If no tables found, try line-by-line parsing
        if not transactions:
            self.logger.debug(f"No tables found on page {page_num}, trying line parsing")
            text_transactions = self._process_text_lines(page)
            transactions.extend(text_transactions)
            
        return transactions
    
    def _extract_tables_from_page(self, page) -> List[List[List[str]]]:
        """Extract tables from a page using multiple strategies"""
        tables = []
        
        # Strategy 1: Text-based detection
        try:
            text_tables = page.extract_tables(table_settings={
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
                "intersection_tolerance": 15,
                "min_words_vertical": 1,
                "min_words_horizontal": 1
            })
            if text_tables:
                tables.extend(text_tables)
                self.logger.debug(f"Found {len(text_tables)} tables using text strategy")
        except Exception as e:
            self.logger.debug(f"Text-based table extraction failed: {e}")
        
        # Strategy 2: Line-based detection
        if not tables:
            try:
                line_tables = page.extract_tables(table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "intersection_tolerance": 10
                })
                if line_tables:
                    tables.extend(line_tables)
                    self.logger.debug(f"Found {len(line_tables)} tables using line strategy")
            except Exception as e:
                self.logger.debug(f"Line-based table extraction failed: {e}")
        
        return tables
    
    def _process_table(self, table: List[List[str]]) -> List[Dict[str, Any]]:
        """Process a table to extract transactions"""
        transactions = []
        
        if not table or len(table) < 2:
            return transactions
            
        # Find header row and identify columns
        header_info = self._identify_table_structure(table)
        if not header_info:
            self.logger.debug("Could not identify table structure")
            return transactions
            
        header_row_idx, column_mapping = header_info
        self.logger.debug(f"Table structure: {column_mapping}")
        
        # Process data rows
        for row_idx in range(header_row_idx + 1, len(table)):
            row = table[row_idx]
            transaction = self._parse_table_row(row, column_mapping)
            if transaction:
                transactions.append(transaction)
                
        return transactions
    
    def _identify_table_structure(self, table: List[List[str]]) -> Optional[Tuple[int, Dict[str, int]]]:
        """Identify the structure of a transaction table"""
        
        # Common header variations for ICICI statements
        header_patterns = {
            'date': ['date', 'dt', 'txn date', 'transaction date', 'value date', 'posting date'],
            'description': ['particulars', 'description', 'narration', 'details', 'transaction details'],
            'debit': ['withdrawals', 'debit', 'dr', 'withdrawal amt', 'debit amount'],
            'credit': ['deposits', 'credit', 'cr', 'deposit amt', 'credit amount'],
            'balance': ['balance', 'closing balance', 'running balance', 'available balance']
        }
        
        for row_idx, row in enumerate(table[:5]):  # Check first 5 rows for headers
            if not row:
                continue
                
            # Clean and normalize row
            cleaned_row = [str(cell).strip().lower() if cell else '' for cell in row]
            
            # Try to match columns
            column_mapping = {}
            matched_columns = 0
            
            for col_idx, cell in enumerate(cleaned_row):
                for field_name, patterns in header_patterns.items():
                    if any(pattern in cell for pattern in patterns):
                        column_mapping[field_name] = col_idx
                        matched_columns += 1
                        break
            
            # Need at least date, description, and one amount column
            required_fields = {'date', 'description'}
            amount_fields = {'debit', 'credit', 'balance'}
            
            if (required_fields.issubset(column_mapping.keys()) and 
                any(field in column_mapping for field in amount_fields)):
                self.logger.debug(f"Found header at row {row_idx}: {column_mapping}")
                return row_idx, column_mapping
        
        return None
    
    def _parse_table_row(self, row: List[str], column_mapping: Dict[str, int]) -> Optional[Dict[str, Any]]:
        """Parse a single table row into a transaction"""
        
        if not row or len(row) <= max(column_mapping.values()):
            return None
            
        transaction = {}
        
        # Extract date
        if 'date' in column_mapping:
            date_cell = row[column_mapping['date']]
            parsed_date = self._parse_date(date_cell)
            if not parsed_date:
                return None  # Skip rows without valid dates
            transaction['Date'] = parsed_date
        else:
            return None
            
        # Extract description
        if 'description' in column_mapping:
            desc_cell = row[column_mapping['description']]
            transaction['Description'] = str(desc_cell).strip() if desc_cell else ''
        else:
            transaction['Description'] = ''
            
        # Extract amounts
        transaction['Credit'] = ''
        transaction['Debit'] = ''
        transaction['Balance'] = ''
        
        for amount_type in ['credit', 'debit', 'balance']:
            if amount_type in column_mapping:
                amount_cell = row[column_mapping[amount_type]]
                cleaned_amount = self._clean_amount(amount_cell)
                transaction[amount_type.capitalize()] = cleaned_amount
        
        # Validate transaction has meaningful content
        if not transaction['Description'] or transaction['Description'].lower() in ['', 'total', 'summary']:
            return None
            
        return transaction
    
    def _process_text_lines(self, page) -> List[Dict[str, Any]]:
        """Process page text line by line to find transactions"""
        transactions = []
        
        try:
            text = page.extract_text()
            if not text:
                return transactions
                
            lines = text.split('\n')
            
            for line in lines:
                transaction = self._parse_text_line(line.strip())
                if transaction:
                    transactions.append(transaction)
                    
        except Exception as e:
            self.logger.debug(f"Error processing text lines: {e}")
            
        return transactions
    
    def _parse_text_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single text line for transaction data"""
        
        if not line or len(line) < 20:  # Skip short lines
            return None
            
        # Look for date pattern
        date_match = re.search(self.date_pattern, line)
        if not date_match:
            return None
            
        parsed_date = self._parse_date(date_match.group(1))
        if not parsed_date:
            return None
            
        # Extract amounts
        amounts = re.findall(self.amount_pattern, line)
        if not amounts:
            return None
            
        # Get description (text between date and first amount)
        date_end = date_match.end()
        first_amount_pos = line.find(amounts[0])
        description = line[date_end:first_amount_pos].strip()
        
        # Clean description
        description = re.sub(r'\s+', ' ', description)
        if len(description) < 3:
            return None
            
        # Determine transaction type and amounts
        transaction = {
            'Date': parsed_date,
            'Description': description,
            'Credit': '',
            'Debit': '',
            'Balance': ''
        }
        
        # Simple heuristic: last amount is usually balance
        if len(amounts) >= 2:
            transaction['Balance'] = amounts[-1]
            
            # Check if it's credit or debit based on description
            desc_lower = description.lower()
            if any(indicator in desc_lower for indicator in self.credit_indicators):
                transaction['Credit'] = amounts[-2] if len(amounts) > 1 else amounts[0]
            elif any(indicator in desc_lower for indicator in self.debit_indicators):
                transaction['Debit'] = amounts[-2] if len(amounts) > 1 else amounts[0]
            else:
                # Default to first amount as transaction amount
                transaction['Credit'] = amounts[0]
        
        return transaction
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse and validate date string"""
        if not date_str:
            return None
            
        # Try different date formats
        date_formats = ['%d-%m-%Y', '%d/%m/%Y', '%d.%m.%Y']
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%d-%m-%Y')  # Standardize format
            except ValueError:
                continue
                
        return None
    
    def _clean_amount(self, amount_str: str) -> str:
        """Clean and format amount string"""
        if not amount_str:
            return ''
            
        # Remove currency symbols and extra spaces
        cleaned = re.sub(r'[^\d.,\-]', '', str(amount_str))
        
        # Handle negative amounts
        is_negative = '-' in cleaned or '(' in str(amount_str)
        
        # Remove everything except digits, commas, and dots
        cleaned = re.sub(r'[^\d.,]', '', cleaned)
        
        if not cleaned:
            return ''
            
        # Handle comma as thousands separator
        if ',' in cleaned and '.' in cleaned:
            # Format like 1,234.56
            cleaned = cleaned.replace(',', '')
        elif ',' in cleaned and cleaned.count(',') == 1 and len(cleaned.split(',')[1]) <= 2:
            # Format like 1234,56 (European style)
            cleaned = cleaned.replace(',', '.')
        elif ',' in cleaned:
            # Thousands separator
            cleaned = cleaned.replace(',', '')
            
        try:
            float(cleaned)
            return f"-{cleaned}" if is_negative else cleaned
        except ValueError:
            return ''
    
    def parse_transaction_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a transaction line (required by base class)"""
        return self._parse_text_line(line)
    
    def is_valid_transaction(self, transaction: Dict[str, Any]) -> bool:
        """Enhanced validation for ICICI transactions"""
        if not super().is_valid_transaction(transaction):
            return False
            
        # Check that we have at least some amount information
        amounts = [transaction.get('Credit', ''), transaction.get('Debit', ''), transaction.get('Balance', '')]
        if not any(amount for amount in amounts):
            return False
            
        # Check description is meaningful
        description = transaction.get('Description', '').strip()
        if len(description) < 3:
            return False
            
        # Skip summary rows
        if description.lower() in ['total', 'summary', 'balance carried forward', 'balance brought forward']:
            return False
            
        return True


def main():
    """Test the parser"""
    parser = ICICIParser("accountparser/ICICI Saving Acc 11117 - PW_KRIS2705 copy.pdf", "KRIS2705")
    transactions = parser.extract_transactions()
    
    if transactions:
        df = pd.DataFrame(transactions)
        print(f"Extracted {len(transactions)} transactions")
        print(df.head())
        df.to_csv("icici_transactions.csv", index=False)
    else:
        print("No transactions found")


if __name__ == "__main__":
    main()
