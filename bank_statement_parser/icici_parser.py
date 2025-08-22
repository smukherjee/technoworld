from typing import List, Dict, Any, Optional
import re
import pandas as pd
import pdfplumber
from .base_parser import BankStatementParser

class ICICIBankParser(BankStatementParser):
    """Parser for ICICI Bank statements"""
    
    def __init__(self, pdf_path: str, password: Optional[str] = None):
        """Initialize parser with enhanced logging"""
        super().__init__(pdf_path, password)
        # Settings for text-based table detection
        self.table_settings_text = {
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
            "intersection_x_tolerance": 20,  # Increased tolerance
            "intersection_y_tolerance": 20,  # Increased tolerance 
            "snap_y_tolerance": 10,  # Increased tolerance
            "min_words_vertical": 2,  # Reduced requirement for easier detection
            "min_words_horizontal": 2  # Reduced requirement for easier detection
        }
        # Settings for line-based table detection
        self.table_settings_lines = {
            "vertical_strategy": "lines", 
            "horizontal_strategy": "lines",
            "intersection_x_tolerance": 20,  # Increased tolerance
            "intersection_y_tolerance": 20,  # Increased tolerance
            "snap_y_tolerance": 10,  # Increased tolerance
            "edge_min_length": 2,  # Reduced min line length
            "min_words_vertical": 2,  # Reduced requirement
            "min_words_horizontal": 2  # Reduced requirement
        }
        
        self.required_cols = ['date', 'description', 'debit', 'credit', 'balance']
        self.logger.debug("Parser initialized with table detection settings")
    
    def _safe_extract_tables(self, page, settings: dict) -> List[List[Any]]:
        """Safely extract tables from a page with error handling"""
        try:
            self.logger.debug(f"Attempting to extract tables using settings: {settings}")
            text = page.extract_text()
            self.logger.debug(f"Page text sample: {text[:200]}")  # Log first 200 chars
            tables = page.extract_tables(table_settings=settings) 
            if tables:
                self.logger.debug(f"Found {len(tables)} tables")
                for i, table in enumerate(tables):
                    self.logger.debug(f"Table {i} sample: {table[:2] if table else []}")
            else:
                self.logger.debug("No tables found with these settings")
            return tables if tables else []
        except Exception as e:
            self.logger.error(f"Error extracting tables: {str(e)}")
            return []
            
    def _clean_headers(self, header_row: List[str]) -> List[str]:
        """Clean and normalize table headers"""
        headers = []
        for header in header_row:
            if header:
                header = str(header).strip().lower()
                headers.append(header)
        return headers

    def _parse_transaction_row(self, row: List[str], headers: List[str]) -> Optional[Dict[str, Any]]:
        """Parse a transaction row into a structured dictionary"""
        if len(row) != len(headers):
            return None
            
        transaction = {}
        for header, value in zip(headers, row):
            if value:
                transaction[header] = str(value).strip()
            else:
                transaction[header] = None
                
        # Basic validation
        missing_fields = [f for f in ['date', 'description'] if not transaction.get(f)]
        if missing_fields:
            return None
            
        return transaction
    
    # These methods were duplicated, removing duplicates

    def extract_transactions(self) -> List[Dict[str, Any]]:
        """Extract transactions from PDF using pdfplumber with enhanced error handling"""
        transactions = []
        self.logger.info(f"Starting transaction extraction from: {self.pdf_path}")
        
        try:
            if not self.pdf_path:
                raise ValueError("PDF path not specified")
            
            self.logger.info(f"Opening PDF with password: {'Yes' if self.password else 'No'}")
            
            with pdfplumber.open(self.pdf_path, password=self.password) as pdf:
                total_pages = len(pdf.pages)
                self.logger.info(f"Successfully opened PDF. Found {total_pages} pages")
                
                # DEBUG: Limit to first 5 pages
                pages_to_process = min(5, total_pages)
                self.logger.info(f"DEBUG MODE: Processing first {pages_to_process} pages only")
                
                if total_pages == 0:
                    raise ValueError("PDF appears to be empty - no pages found")
                
                for page_num, page in enumerate(pdf.pages[:pages_to_process], 1):
                    self.logger.info(f"Processing page {page_num}/{pages_to_process}")
                    
                    try:
                        # Extract text for debugging
                        text = page.extract_text()
                        if not text:
                            self.logger.warning(f"No text found on page {page_num}")
                            continue
                            
                        # Show text sample with visible line breaks
                        debug_text = text.replace('\n', '⏎').replace('\r', '⏎')
                        self.logger.debug(f"Page {page_num} text sample:\n{debug_text[:1000]}")
                        
                        # Log some word positions for debugging layout
                        words = page.extract_words(x_tolerance=2, y_tolerance=2)
                        self.logger.debug(f"Found {len(words)} words on page {page_num}")
                        for i, w in enumerate(words[:10]):
                            self.logger.debug(f"Word {i}: '{w['text']}' at x={w['x0']:.1f},y={w['top']:.1f}")
                        
                        # Try text-based table detection first
                        tables = self._safe_extract_tables(page, self.table_settings_text)
                        if not tables:
                            self.logger.debug("No tables found with text strategy, trying lines")
                            tables = self._safe_extract_tables(page, self.table_settings_lines)
                        
                        if not tables:
                            self.logger.debug(f"No tables found on page {page_num}")
                            continue
                        
                        # Process each table
                        self.logger.debug(f"Found {len(tables)} tables on page {page_num}")
                        for table_idx, table in enumerate(tables):
                            if not table:
                                self.logger.debug(f"Table {table_idx} is empty")
                                continue
                            
                            self.logger.debug(f"Processing table {table_idx}")
                            self.logger.debug(f"Table dimensions: {len(table)}x{len(table[0]) if table else 0}")
                            
                            # Basic validation
                            if len(table) < 2:  # Need header and data
                                self.logger.debug(f"Table {table_idx} has insufficient rows")
                                continue
                            
                            # Check column consistency
                            col_counts = {len(row) for row in table}
                            if len(col_counts) > 1:
                                self.logger.debug(f"Table {table_idx} has inconsistent columns")
                                continue
                            
                            try:
                                # Log raw data sample
                                self.logger.debug("Table header:")
                                self.logger.debug(table[0])
                                self.logger.debug("First few data rows:")
                                for row in table[1:5]:
                                    self.logger.debug(row)
                                
                                # Convert to DataFrame
                                df = pd.DataFrame(table[1:], columns=table[0])
                                
                                # Clean up the data
                                df = df.replace('', pd.NA).dropna(how='all')
                                df = df.reset_index(drop=True)
                                
                                if df.empty:
                                    self.logger.debug(f"Table {table_idx} is empty after cleaning")
                                    continue
                                
                                self.logger.debug(f"Clean DataFrame shape: {df.shape}")
                                self.logger.debug("\nFirst few rows:")
                                self.logger.debug(df.head().to_string())
                                
                                # Check if it's a transaction table
                                if not self._is_transaction_table(df):
                                    self.logger.debug(f"Table {table_idx} is not a transaction table")
                                    continue
                                
                                # Process valid transaction table
                                table_transactions = self._process_table(df)
                                if table_transactions:
                                    transactions.extend(table_transactions)
                                    self.logger.info(f"Added {len(table_transactions)} transactions from table {table_idx}")
                            
                            except Exception as e:
                                self.logger.warning(f"Error processing table {table_idx}: {e}")
                                continue
                    
                    except Exception as e:
                        self.logger.error(f"Error processing page {page_num}: {e}")
                        continue
                        
                # Final transaction cleanup and validation
                if not transactions:
                    self.logger.warning("No transactions extracted")
                else:
                    self.logger.info(f"Successfully extracted {len(transactions)} total transactions")
                
                return transactions
                
        except pdfplumber.pdfminer.pdfparser.PDFSyntaxError as e:
            raise ValueError("Invalid or corrupted PDF file") from e
        except Exception as e:
            self.logger.error(f"Unexpected error during extraction: {e}")
            raise
                                
                            try:
                                headers = self._clean_headers(table[0])
                                self.logger.debug(f"Found headers: {headers}")
                                
                                for row_num, row in enumerate(table[1:], 1):
                                    if not any(cell for cell in row):
                                        continue
                                        
                                    try:
                                        transaction = self._parse_transaction_row(row, headers)
                                        if transaction:
                                            page_transactions.append(transaction)
                                    except Exception as e:
                                        self.logger.warning(f"Error parsing row {row_num}: {e}")
                                        continue
                                        
                            except Exception as e:
                                self.logger.error(f"Error processing table {table_num}: {e}")
                                continue
                                
                        # Add successful transactions
                        if page_transactions:
                            self.logger.info(f"Found {len(page_transactions)} transactions")
                            transactions.extend(page_transactions)
                                
                    except Exception as e:
                        self.logger.error(f"Error processing page {page_num}: {e}")
                        continue
                        
        except pdfplumber.pdfminer.pdfparser.PDFSyntaxError as e:
            raise ValueError("Invalid or corrupted PDF file") from e
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise
                            
        if not transactions:
            self.logger.warning("No transactions extracted")
        else:
            self.logger.info(f"Extracted {len(transactions)} total transactions")
            
        return transactions
                self.logger.debug(f"Found {len(tables)} tables on page {page_num}")
                for table_idx, table in enumerate(tables):
                    if not table:
                        self.logger.debug(f"Table {table_idx} is empty")
                        continue
                        
                    self.logger.debug(f"Table {table_idx} has {len(table)} rows and {len(table[0]) if table else 0} columns")
                    self.logger.debug(f"First row: {table[0] if table else []}")
                    
                    # Check if table has any rows
                    if len(table) < 2:  # Need at least header and one data row
                        self.logger.debug(f"Table {table_idx} has insufficient rows: {len(table)}")
                        continue
                                
                    # Check if table has consistent column count
                    col_counts = {len(row) for row in table}
                    if len(col_counts) > 1:
                        self.logger.debug(f"Table {table_idx} has inconsistent column counts: {col_counts}")
                        continue
                        
                    try:
                        # Log the raw table data
                        self.logger.debug(f"Raw table data (first few rows):")
                        max_rows = min(5, len(table))
                        for row in table[:max_rows]:
                            self.logger.debug(row)
                            
                        # Convert table to DataFrame
                        df = pd.DataFrame(table[1:], columns=table[0])
                        self.logger.debug(f"DataFrame columns: {df.columns.tolist()}")
                        
                        # Clean up the DataFrame
                        df = df.replace('', pd.NA).dropna(how='all')
                        df = df.reset_index(drop=True)
                        self.logger.debug(f"Shape after cleaning: {df.shape}")
                        
                        # Check if DataFrame is empty after cleaning
                        if df.empty:
                            self.logger.debug(f"Table {table_idx} is empty after cleaning")
                            continue
                        
                        # Log sample of cleaned data    
                        self.logger.debug("First few rows of cleaned data:")
                        self.logger.debug(df.head().to_string())
                        
                        # Check if this looks like a transaction table
                        if not self._is_transaction_table(df):
                            self.logger.debug(f"Table {table_idx} does not look like a transaction table")
                            continue
                        
                        # Process the table rows
                        table_transactions = self._process_table(df)
                        if table_transactions:
                            transactions.extend(table_transactions)
                            
                    except Exception as e:
                        self.logger.warning(f"Could not process table {table_idx}: {e}")
                        continue
        
        # Validate and clean transactions
        transactions = self.validate_transactions(transactions)
        return transactions
    
    def _is_transaction_table(self, df) -> bool:
        """Check if the DataFrame looks like a transaction table"""
        if df.empty:
            self.logger.debug("DataFrame is empty")
            return False
            
        if len(df.columns) < 4:
            self.logger.debug(f"Too few columns: {len(df.columns)}")
            return False
            
        # Check if required columns are present
        required_headers = {'DATE', 'PARTICULARS', 'WITHDRAWALS', 'DEPOSITS', 'BALANCE'}
        found_headers = {str(col).strip().upper() for col in df.columns}
        self.logger.debug(f"Required headers: {required_headers}")
        self.logger.debug(f"Found headers: {found_headers}")
        
        # Check if common header variations exist
        header_variations = {
            'DATE': ['DATE', 'DT', 'TXN DATE', 'TRANSACTION DATE', 'VALUE DATE'],
            'PARTICULARS': ['PARTICULARS', 'DESCRIPTION', 'NARRATION', 'DETAILS', 'TRANSACTION REMARKS'],
            'WITHDRAWALS': ['WITHDRAWALS', 'DEBIT', 'DR', 'WITHDRAWAL AMT', 'AMOUNT DEBITED'],
            'DEPOSITS': ['DEPOSITS', 'CREDIT', 'CR', 'DEPOSIT AMT', 'AMOUNT CREDITED'],
            'BALANCE': ['BALANCE', 'CLOSING BALANCE', 'RUNNING BALANCE', 'AVAIL BAL']
        }
        
        # Track which header types we've found
        found_header_types = set()
        for header_type, variations in header_variations.items():
            found = False
            for col in found_headers:
                if any(var in col for var in variations):
                    found = True
                    found_header_types.add(header_type)
                    break
            self.logger.debug(f"Found header type {header_type}: {found}")
                    
        # Need at least 3 major header types
        matches = found_header_types
        self.logger.debug(f"Found header types: {matches}")
        has_enough_headers = len(matches) >= 3
        
        if not has_enough_headers:
            self.logger.debug("Not enough required headers found")
            return False
            
        self.logger.debug("Table looks like a transaction table")
        return True
    
    def _process_table(self, df) -> List[Dict[str, Any]]:
        """Process a transaction table DataFrame"""
        transactions = []
        
        # Use first row as header and rename columns
        df.columns = df.iloc[0]
        df = df.iloc[1:].reset_index(drop=True)
        
        # Standardize column names
        column_mapping = {
            'DATE': 'Date',
            'PARTICULARS': 'Description',
            'DEPOSITS': 'Credit',
            'WITHDRAWALS': 'Debit',
            'BALANCE': 'Balance',
            'MODE': 'Mode'  # Some statements might have this
        }
        
        df = df.rename(columns=lambda x: column_mapping.get(str(x).strip().upper(), x))
        
        # Process each row
        for _, row in df.iterrows():
            transaction = self._process_row(row)
            if transaction:
                transactions.append(transaction)
        
        return transactions
    
    def _get_line_text(self, line: Dict) -> str:
        """Extract text from a line"""
        return " ".join(span["text"] for span in line["spans"]).strip()
    
    def _is_transaction_start(self, text: str) -> bool:
        """Check if text starts a new transaction"""
        # Match date pattern at start of line
        return bool(re.match(r'^\d{2}-\d{2}-\d{4}', text))
    
    def _process_row(self, row) -> Optional[Dict[str, Any]]:
        """Process a single transaction row"""
        try:
            # Skip rows without a proper date
            if not self._is_valid_date(str(row.get('Date', ''))):
                return None
                
            # Clean up the values
            transaction = {
                'Date': str(row.get('Date', '')).strip(),
                'Description': str(row.get('Description', '')).strip(),
                'Credit': str(row.get('Credit', '0')).strip(),
                'Debit': str(row.get('Debit', '0')).strip(),
                'Balance': str(row.get('Balance', '0')).strip(),
            }
            
            # Add Mode if available
            if 'Mode' in row:
                transaction['Mode'] = str(row['Mode']).strip()
            
            # Clean up the transaction
            return self._clean_transaction(transaction)
            
        except Exception as e:
            self.logger.warning(f"Error processing row: {str(e)}")
            return None
    
    def _clean_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up transaction values"""
        # Remove any currency symbols and extra spaces
        for key in ['Credit', 'Debit', 'Balance']:
            if key in transaction:
                value = transaction[key]
                value = re.sub(r'[^\d.-]', '', str(value))
                transaction[key] = value if value else '0'
        
        # Clean up description
        if 'Description' in transaction:
            desc = transaction['Description']
            desc = re.sub(r'\s+', ' ', desc)  # Replace multiple spaces with single space
            desc = desc.replace('\\n', ' ')    # Replace newlines with space
            transaction['Description'] = desc.strip()
        
        return transaction
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Check if string is a valid date"""
        try:
            # Handle common date formats
            date_formats = [
                r'^\d{2}-\d{2}-\d{4}$',  # DD-MM-YYYY
                r'^\d{2}/\d{2}/\d{4}$',  # DD/MM/YYYY
                r'^\d{2}\.\d{2}\.\d{4}$'  # DD.MM.YYYY
            ]
            
            return any(re.match(pattern, date_str.strip()) for pattern in date_formats)
            
        except Exception:
            return False
    
    def parse_transaction_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a transaction line (used for validation)"""
        # This method is kept for compatibility but not used directly
        # as we're using table-based parsing now
        return None
    
    def is_valid_transaction(self, transaction: Dict[str, Any]) -> bool:
        """Additional validation specific to ICICI bank"""
        if not super().is_valid_transaction(transaction):
            return False
        
        # At least one amount should be present
        has_amount = any(transaction.get(field) for field in ['Credit', 'Debit', 'Balance'])
        if not has_amount:
            return False
        
        # Description should be meaningful
        description = transaction.get('Description', '')
        if len(description) < 3 or description.isspace():
            return False
        
        return True
