"""
Excel Template Manager for configurable parsing of bank statements.
Manages templates that define how to parse different Excel file formats.
"""

import json
import logging
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import re


class ExcelTemplateManager:
    """Manages Excel parsing templates for different bank statement formats."""
    
    def __init__(self, template_file: str = "excel_template.json"):
        self.template_file = template_file
        self.template = None
        self.logger = self._setup_logging()
        self.load_template()
    
    def _setup_logging(self):
        """Set up logging for the template manager."""
        logger = logging.getLogger(self.__class__.__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def load_template(self) -> bool:
        """Load template from JSON file."""
        try:
            with open(self.template_file, 'r') as f:
                self.template = json.load(f)
            self.logger.info(f"Loaded template: {self.template.get('template_name', 'Unknown')}")
            return True
        except FileNotFoundError:
            self.logger.error(f"Template file not found: {self.template_file}")
            return False
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in template file: {e}")
            return False
    
    def detect_header_row(self, df: pd.DataFrame) -> Optional[int]:
        """Detect the header row based on template patterns."""
        if not self.template:
            return None
        
        search_rows = self.template['header_detection']['search_rows']
        header_patterns = self.template['header_detection']['header_patterns']
        
        # Check custom override first
        force_header = self.template['custom_overrides'].get('force_header_row')
        if force_header is not None:
            self.logger.info(f"Using forced header row: {force_header}")
            return force_header
        
        for row_idx in search_rows:
            if row_idx >= len(df):
                continue
            
            row_values = [str(val).lower().strip() for val in df.iloc[row_idx].values if pd.notna(val)]
            
            # Count how many header patterns match this row
            matches = 0
            for pattern in header_patterns:
                if any(pattern.lower() in val for val in row_values):
                    matches += 1
            
            # If most patterns match, this is likely the header row
            if matches >= len(header_patterns) * 0.6:  # 60% match threshold
                self.logger.info(f"Detected header row at index {row_idx} with {matches} pattern matches")
                return row_idx
        
        self.logger.warning("Could not detect header row automatically")
        return None
    
    def map_columns(self, df: pd.DataFrame, header_row: int) -> Dict[str, int]:
        """Map template column names to actual DataFrame column indices."""
        if not self.template or header_row is None or header_row >= len(df):
            return {}
        
        column_mapping = {}
        template_columns = self.template['data_mapping']['column_mapping']
        
        # Get the header row values
        header_values = [str(val).lower().strip() for val in df.iloc[header_row].values]
        
        # Check for forced column mapping
        forced_mapping = self.template['custom_overrides'].get('force_column_mapping', {})
        
        for field_name, field_config in template_columns.items():
            col_idx = None
            
            # Check forced mapping first
            if field_name in forced_mapping:
                col_idx = forced_mapping[field_name]
                self.logger.info(f"Using forced mapping for {field_name}: column {col_idx}")
            else:
                # Try to match by possible names
                possible_names = field_config.get('possible_names', [])
                for name in possible_names:
                    name_lower = name.lower().strip()
                    for idx, header_val in enumerate(header_values):
                        if name_lower in header_val or header_val in name_lower:
                            col_idx = idx
                            self.logger.info(f"Mapped {field_name} to column {idx} ({df.columns[idx]})")
                            break
                    if col_idx is not None:
                        break
            
            # Check if column is required
            if col_idx is None and not field_config.get('optional', False):
                if field_name in self.template['data_validation']['required_columns']:
                    self.logger.warning(f"Required column '{field_name}' not found")
            
            if col_idx is not None:
                column_mapping[field_name] = col_idx
        
        return column_mapping
    
    def get_data_start_row(self, header_row: Optional[int]) -> Optional[int]:
        """Get the row where actual data starts."""
        if not self.template:
            return None
        
        # Check custom override first
        force_start = self.template['custom_overrides'].get('force_data_start_row')
        if force_start is not None:
            self.logger.info(f"Using forced data start row: {force_start}")
            return force_start
        
        # Default: data starts one row after header
        if header_row is not None:
            data_start = header_row + 1
            self.logger.info(f"Data starts at row {data_start}")
            return data_start
        
        return None
    
    def clean_data_value(self, value: Any, field_config: Dict[str, Any]) -> Any:
        """Clean a data value based on field configuration."""
        if pd.isna(value) or value == '':
            return None
        
        data_type = field_config.get('data_type', 'string')
        
        if data_type == 'string':
            cleaned = str(value).strip()
            if field_config.get('clean_text', False):
                # Remove extra whitespace
                cleaned = re.sub(r'\s+', ' ', cleaned)
            return cleaned
        
        elif data_type == 'amount':
            # Clean amount field
            amount_str = str(value).strip()
            # Remove currency symbols and commas
            amount_str = re.sub(r'[₹,\s]', '', amount_str)
            try:
                return float(amount_str) if amount_str else 0.0
            except ValueError:
                self.logger.warning(f"Could not parse amount: {value}")
                return 0.0
        
        elif data_type == 'date':
            if isinstance(value, datetime):
                return value
            
            date_str = str(value).strip()
            date_formats = field_config.get('date_format', ['%d/%m/%Y'])
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            self.logger.warning(f"Could not parse date: {value}")
            return None
        
        return value
    
    def should_exclude_row(self, row_data: Dict[str, Any]) -> bool:
        """Check if a row should be excluded based on validation rules."""
        if not self.template:
            return False
        
        filters = self.template['data_validation']['filters']
        
        # Check description for exclusion patterns
        description = row_data.get('description', '')
        if description:
            description_lower = str(description).lower()
            for exclude_pattern in filters.get('exclude_rows_with', []):
                if exclude_pattern.lower() in description_lower:
                    return True
            
            # Check minimum description length
            min_length = filters.get('min_description_length', 0)
            if len(description.strip()) < min_length:
                return True
        
        # Check if description is empty and should be excluded
        if filters.get('exclude_empty_descriptions', False):
            if not description or description.strip() == '':
                return True
        
        return False
    
    def parse_excel_with_template(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse DataFrame using the loaded template."""
        if not self.template:
            raise ValueError("No template loaded")
        
        self.logger.info("Parsing Excel file with template")
        
        # Step 1: Detect header row
        header_row = self.detect_header_row(df)
        if header_row is None:
            raise ValueError("Could not detect header row")
        
        # Step 2: Map columns
        column_mapping = self.map_columns(df, header_row)
        if not column_mapping:
            raise ValueError("Could not map any columns")
        
        # Step 3: Get data start row
        data_start_row = self.get_data_start_row(header_row)
        if data_start_row is None:
            raise ValueError("Could not determine data start row")
        
        # Step 4: Extract and clean data
        parsed_rows = []
        template_columns = self.template['data_mapping']['column_mapping']
        
        for idx in range(data_start_row, len(df)):
            row_data = {}
            
            # Extract data for each mapped column
            for field_name, col_idx in column_mapping.items():
                if col_idx < len(df.columns):
                    raw_value = df.iloc[idx, col_idx]
                    field_config = template_columns[field_name]
                    cleaned_value = self.clean_data_value(raw_value, field_config)
                    row_data[field_name] = cleaned_value
            
            # Check if row should be excluded
            if self.should_exclude_row(row_data):
                continue
            
            # Check if row has required data
            if self._has_required_data(row_data):
                parsed_rows.append(row_data)
        
        # Step 5: Convert to standard format
        return self._convert_to_standard_format(parsed_rows)
    
    def _has_required_data(self, row_data: Dict[str, Any]) -> bool:
        """Check if row has required data."""
        required_columns = self.template['data_validation']['required_columns']
        
        for req_col in required_columns:
            if req_col not in row_data or row_data[req_col] is None:
                return False
            
            # For string fields, check if not empty
            if isinstance(row_data[req_col], str) and row_data[req_col].strip() == '':
                return False
        
        return True
    
    def _convert_to_standard_format(self, parsed_rows: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert parsed rows to standard DataFrame format."""
        if not parsed_rows:
            return pd.DataFrame()
        
        output_format = self.template['output_format']
        standard_columns = output_format['standard_columns']
        date_format = output_format['date_output_format']
        
        # Create DataFrame
        df_data = []
        
        for row in parsed_rows:
            standard_row = {}
            
            # Map to standard column names
            standard_row['Date'] = self._format_date(row.get('date'), date_format)
            standard_row['Description'] = row.get('description', '')
            standard_row['Reference'] = row.get('reference', '')
            standard_row['Debit'] = self._format_amount(row.get('debit'))
            standard_row['Credit'] = self._format_amount(row.get('credit'))
            standard_row['Balance'] = self._format_amount(row.get('balance'))
            
            df_data.append(standard_row)
        
        df = pd.DataFrame(df_data, columns=standard_columns)
        self.logger.info(f"Converted {len(df)} rows to standard format")
        
        return df
    
    def _format_date(self, date_value: Any, output_format: str) -> str:
        """Format date value to string."""
        if date_value is None:
            return ''
        
        if isinstance(date_value, datetime):
            return date_value.strftime(output_format)
        
        return str(date_value)
    
    def _format_amount(self, amount_value: Any) -> str:
        """Format amount value to string."""
        if amount_value is None or amount_value == 0:
            return ''
        
        try:
            amount = float(amount_value)
            decimal_places = self.template['output_format']['amount_decimal_places']
            return f"{amount:.{decimal_places}f}"
        except (ValueError, TypeError):
            return str(amount_value) if amount_value else ''
    
    def save_template(self, template_data: Dict[str, Any], filename: str):
        """Save template data to JSON file."""
        with open(filename, 'w') as f:
            json.dump(template_data, f, indent=2)
        self.logger.info(f"Saved template to {filename}")
    
    def get_template_info(self) -> Dict[str, Any]:
        """Get template information."""
        if not self.template:
            return {}
        
        return {
            'name': self.template.get('template_name', 'Unknown'),
            'description': self.template.get('description', ''),
            'version': self.template.get('version', '1.0'),
            'bank': self.template.get('bank_specific', {}).get('bank_name', 'Unknown'),
            'columns': list(self.template.get('data_mapping', {}).get('column_mapping', {}).keys())
        }
