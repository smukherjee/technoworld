# Excel Template System for Bank Statement Parsing

This template system provides a configurable way to parse different Excel file formats for bank statements. It uses JSON templates to define how to map columns, detect headers, and parse data.

## Overview

The template system consists of:

1. **`excel_template.json`** - Template configuration file
2. **`excel_template_manager.py`** - Template management and parsing logic
3. **`excel_parser.py`** - Updated parser that uses templates
4. **`test_template.py`** - Testing and demonstration script

## Template Configuration

### Basic Structure

```json
{
  "template_name": "ICICI Bank Statement Excel Template",
  "description": "Template for parsing ICICI bank statement Excel files",
  "version": "1.0",
  
  "header_detection": {
    "search_rows": [10, 11, 12, 13, 14, 15],
    "header_patterns": ["value date", "transaction date", ...]
  },
  
  "data_mapping": {
    "column_mapping": {
      "date": {
        "possible_names": ["Transaction Date", "Date"],
        "data_type": "date",
        "date_format": ["%d/%m/%y", "%d/%m/%Y"]
      }
    }
  }
}
```

### Key Configuration Sections

#### 1. Header Detection
- **`search_rows`**: Which rows to search for headers (e.g., [10, 11, 12])
- **`header_patterns`**: Keywords that indicate header row (e.g., "transaction date")

#### 2. Column Mapping
For each field type (date, description, debit, credit, etc.):
- **`possible_names`**: Array of possible column header names
- **`data_type`**: How to parse the data ("date", "amount", "string")
- **`date_format`**: Array of date formats to try
- **`optional`**: Whether this column is required

#### 3. Data Validation
- **`required_columns`**: Columns that must be present
- **`filters`**: Rules for excluding rows (e.g., "opening balance")

#### 4. Custom Overrides
- **`force_header_row`**: Manually specify header row number
- **`force_data_start_row`**: Manually specify data start row
- **`force_column_mapping`**: Manual column index mapping

## Usage Examples

### 1. Basic Usage with Template

```python
from excel_parser import ExcelTransactionParser

# Use default template
parser = ExcelTransactionParser("excel_template.json")
transactions = parser.parse_excel("bank_statement.xls")
```

### 2. Creating Custom Templates

```python
from excel_template_manager import ExcelTemplateManager

# Analyze file structure first
template_manager = ExcelTemplateManager()

# Create custom template based on analysis
custom_template = {
    "template_name": "My Bank Template",
    "header_detection": {
        "search_rows": [5, 6, 7, 8],
        "header_patterns": ["date", "description", "amount"]
    },
    "custom_overrides": {
        "force_header_row": 7,
        "force_data_start_row": 8
    }
}

# Save custom template
template_manager.save_template(custom_template, "my_template.json")
```

### 3. Manual Column Mapping

When automatic detection fails, you can force specific mappings:

```json
{
  "custom_overrides": {
    "force_header_row": 11,
    "force_data_start_row": 12,
    "force_column_mapping": {
      "date": 2,
      "description": 4,
      "debit": 5,
      "credit": 6,
      "balance": 7
    }
  }
}
```

## Supported Data Types

### Date Fields
- **Formats**: `%d/%m/%Y`, `%d-%m-%Y`, `%d/%m/%y`, etc.
- **Output**: Standardized as "DD-MM-YYYY"

### Amount Fields  
- **Input**: "1,234.56", "₹1234.56", "1234.5"
- **Processing**: Removes currency symbols and commas
- **Output**: Decimal numbers as strings

### String Fields
- **Processing**: Strips whitespace, optionally cleans text
- **Validation**: Minimum length checks, exclusion patterns

## File Structure Analysis

The `test_template.py` script helps analyze Excel file structure:

```bash
cd beancount
python test_template.py
```

This will:
1. Show the first 15 rows of your Excel file
2. Create a custom template based on the structure
3. Test parsing with the template
4. Generate sample output

## Template Testing Results

With the current ICICI template:
- **File**: OpTransactionHistory15-08-2025.xls
- **Header Row**: 11 (auto-detected)
- **Data Start**: Row 12
- **Transactions Parsed**: 419
- **Columns Mapped**: Date, Description, Reference, Debit, Credit, Balance
- **Date Range**: 01-01-2025 to 08-14-2025

## Troubleshooting

### Common Issues

1. **Header Not Detected**
   - Check `search_rows` range
   - Verify `header_patterns` match your file
   - Use `force_header_row` as fallback

2. **Column Mapping Failed**
   - Check `possible_names` for each field
   - Use `force_column_mapping` for manual mapping
   - Verify column headers in your file

3. **Date Parsing Warnings**
   - Add more `date_format` patterns
   - Check if dates use 2-digit or 4-digit years
   - Verify day/month order

4. **No Transactions Found**
   - Check `data_validation.filters` 
   - Verify `required_columns` are not too strict
   - Look at `exclude_rows_with` patterns

### Template Debugging

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check intermediate files:
- `template_parsed_transactions.csv` - Raw parsed data
- `excel_template_custom.json` - Auto-generated template

## Integration with Beancount

The template system integrates with the beancount classification:

```python
# Parse with template
parser = ExcelTransactionParser("excel_template.json")
transactions = parser.parse_excel("statement.xls")

# Classify transactions  
classifier = TransactionClassifier()
classified = classifier.classify_transactions(transactions)

# Generate beancount entries
classifier.save_beancount_file(classified, "output.beancount")
```

## Creating Templates for Different Banks

1. **Analyze** the Excel file structure
2. **Identify** header row and column patterns
3. **Create** template with appropriate mappings
4. **Test** with sample data
5. **Refine** based on results

Each bank may need a different template due to varying:
- Header row positions
- Column names and order
- Date formats
- Amount formatting
- File structure
