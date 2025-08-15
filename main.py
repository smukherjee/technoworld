import fitz  # PyMuPDF
import pandas as pd
import re
from datetime import datetime

def extract_icici_statement():
    # PDF file path
    pdf_path = "accountparser/ICICI Saving Acc 11117 - PW_KRIS2705 copy.pdf"
    password = "KRIS2705"
    doc = None
    
    try:
        # Open the PDF with the password
        doc = fitz.open(pdf_path)
        doc.authenticate(password)
        
        print("Extracting ICICI bank statement data...")
        
        # Extract all transaction data
        transactions = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_transactions = extract_transactions_from_page(page, page_num + 1)
            transactions.extend(page_transactions)
        
        if transactions:
            # Create and save the final DataFrame
            df = create_clean_dataframe(transactions)
            
            # Save to CSV
            csv_path = "accountparser/account_statement.csv"
            df.to_csv(csv_path, index=False)
            print(f"CSV file created: {csv_path}")
            
            # Display results
            print(f"\nExtracted {len(df)} transactions")
            print("\nFirst 10 rows:")
            print(df.head(10).to_string(index=False))
            
            # Show column info
            print(f"\nColumns: {list(df.columns)}")
            
        else:
            print("No transactions found in the PDF")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if doc is not None and not doc.is_closed:
            doc.close()

def extract_transactions_from_page(page, page_num):
    """Extract transactions from a single page using coordinate-based approach"""
    print(f"Processing page {page_num}...")
    
    # Get text with positions using words
    words = page.get_text("words")
    
    if not words:
        return []
    
    # Group words by lines (Y-coordinate)
    lines = group_words_by_lines(words)
    
    # Filter and process transaction lines
    transactions = []
    
    for line_y, line_words in lines.items():
        transaction = parse_transaction_line(line_words)
        if transaction:
            transactions.append(transaction)
    
    return transactions

def group_words_by_lines(words, y_tolerance=2):
    """Group words by their Y-coordinate to form lines"""
    from collections import defaultdict
    
    lines = defaultdict(list)
    
    for word in words:
        x0, y0, x1, y1, text, block_no, line_no, word_no = word
        
        # Round Y-coordinate for grouping
        y_key = round(y0)
        
        lines[y_key].append({
            'x0': x0,
            'x1': x1,
            'y0': y0,
            'text': text.strip()
        })
    
    # Sort words within each line by X-coordinate
    for y_key in lines:
        lines[y_key].sort(key=lambda w: w['x0'])
    
    return lines

def parse_transaction_line(line_words):
    """Parse a line to extract transaction information"""
    if len(line_words) < 3:
        return None
    
    # Combine all text to analyze
    full_line_text = ' '.join([w['text'] for w in line_words])
    
    # Check if this looks like a transaction line (contains date)
    date_pattern = r'\b(\d{2}-\d{2}-\d{4})\b'
    date_match = re.search(date_pattern, full_line_text)
    
    if not date_match:
        return None
    
    # Extract date
    transaction_date = date_match.group(1)
    
    # Define approximate column boundaries based on ICICI statement format
    # These coordinates are estimated from typical ICICI statements
    date_end = 100
    mode_end = 200
    particulars_end = 750
    deposits_end = 850
    withdrawals_end = 950
    
    # Extract data based on X-coordinates
    date_text = ""
    mode_text = ""
    particulars_text = ""
    deposits_text = ""
    withdrawals_text = ""
    balance_text = ""
    
    for word in line_words:
        x = word['x0']
        text = word['text']
        
        if x < date_end:
            date_text += text + " "
        elif x < mode_end:
            mode_text += text + " "
        elif x < particulars_end:
            particulars_text += text + " "
        elif x < deposits_end:
            deposits_text += text + " "
        elif x < withdrawals_end:
            withdrawals_text += text + " "
        else:
            balance_text += text + " "
    
    # Clean up the extracted text
    date_text = date_text.strip()
    mode_text = mode_text.strip()
    particulars_text = particulars_text.strip()
    deposits_text = deposits_text.strip()
    withdrawals_text = withdrawals_text.strip()
    balance_text = balance_text.strip()
    
    # Skip if no meaningful particulars
    if len(particulars_text) < 2:
        return None
    
    # Clean and format amounts
    deposits_amount = clean_amount(deposits_text)
    withdrawals_amount = clean_amount(withdrawals_text)
    balance_amount = clean_amount(balance_text)
    
    return {
        'Date': date_text if date_text else transaction_date,
        'Mode': mode_text,
        'Particulars': particulars_text,
        'Deposits': deposits_amount,
        'Withdrawals': withdrawals_amount,
        'Balance': balance_amount
    }

def clean_amount(amount_text):
    """Clean and format amount text"""
    if not amount_text:
        return ""
    
    # Remove non-numeric characters except decimal point and comma
    cleaned = re.sub(r'[^\d.,]', '', amount_text)
    
    # Handle Indian number formatting (lakhs, crores)
    if cleaned and any(c.isdigit() for c in cleaned):
        return cleaned
    
    return ""

def create_clean_dataframe(transactions):
    """Create a clean DataFrame from extracted transactions"""
    df = pd.DataFrame(transactions)
    
    # Remove rows where essential data is missing
    df = df[df['Date'].str.len() > 5]  # Must have proper date
    df = df[df['Particulars'].str.len() > 2]  # Must have description
    
    # Clean up date format
    df['Date'] = df['Date'].apply(clean_date)
    
    # Sort by date
    df = df.sort_values('Date').reset_index(drop=True)
    
    # Remove duplicates
    df = df.drop_duplicates().reset_index(drop=True)
    
    return df

def clean_date(date_str):
    """Clean and standardize date format"""
    if not date_str:
        return ""
    
    # Extract date pattern
    date_match = re.search(r'(\d{2}-\d{2}-\d{4})', date_str)
    if date_match:
        return date_match.group(1)
    
    return date_str

# Alternative method using text blocks with better parsing
def extract_with_text_blocks():
    """Alternative extraction method using text blocks"""
    pdf_path = "accountparser/ICICI Saving Acc 11117 - PW_KRIS2705 copy.pdf"
    password = "KRIS2705"
    doc = None
    
    try:
        doc = fitz.open(pdf_path)
        doc.authenticate(password)
        
        all_transactions = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Get text as blocks
            text = page.get_text()
            lines = text.split('\n')
            
            current_transaction = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this is a new transaction (starts with date)
                date_match = re.match(r'^(\d{2}-\d{2}-\d{4})', line)
                
                if date_match:
                    # Save previous transaction if exists
                    if current_transaction:
                        all_transactions.append(current_transaction)
                    
                    # Start new transaction
                    current_transaction = parse_transaction_line_simple(line)
                
                elif current_transaction and line:
                    # This might be a continuation of particulars
                    if 'Particulars' in current_transaction:
                        current_transaction['Particulars'] += ' ' + line
            
            # Don't forget the last transaction
            if current_transaction:
                all_transactions.append(current_transaction)
        
        return all_transactions
        
    finally:
        if doc is not None and not doc.is_closed:
            doc.close()

def parse_transaction_line_simple(line):
    """Simple parsing for lines that start with date"""
    # This is a simplified parser - adjust based on your specific format
    parts = line.split()
    
    if len(parts) < 2:
        return None
    
    date = parts[0]
    
    # Look for amount patterns in the line
    amounts = re.findall(r'\d+(?:,\d{3})*(?:\.\d{2})?', line)
    
    # The rest is particulars (everything between date and amounts)
    particulars_start = len(date) + 1
    particulars = line[particulars_start:].strip()
    
    # Remove amounts from particulars
    for amount in amounts:
        particulars = particulars.replace(amount, '').strip()
    
    return {
        'Date': date,
        'Mode': '',
        'Particulars': particulars,
        'Deposits': amounts[0] if len(amounts) >= 2 else '',
        'Withdrawals': amounts[1] if len(amounts) >= 2 else amounts[0] if amounts else '',
        'Balance': amounts[-1] if amounts else ''
    }

if __name__ == "__main__":
    extract_icici_statement()