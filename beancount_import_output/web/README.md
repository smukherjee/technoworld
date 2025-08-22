# Beancount-Import Web Interface

## Quick Start

1. **Start the web interface:**
   ```bash
   python start_web_interface.py
   ```

2. **Open your browser:**
   Navigate to http://localhost:8080

3. **Review transactions:**
   - View pending transactions
   - Confirm or modify account predictions
   - Train the ML classifier with your choices

## Features

- **Visual Transaction Review**: See all pending transactions in a web interface
- **Account Prediction**: ML-based automatic account classification
- **Manual Correction**: Edit accounts, descriptions, and add tags/links
- **Training**: The system learns from your choices to improve predictions
- **Duplicate Detection**: Automatic matching and merging of similar transactions

## Keyboard Shortcuts

- `Enter`: Accept selected transaction
- `i`: Ignore transaction
- `t`: Retrain classifier
- `1-9`: Quick account selection
- `Arrow Keys`: Navigate between transactions

## Files

- `enhanced_transactions.beancount`: Transactions with ML predictions
- `base_journal.beancount`: Base chart of accounts
- `import_config.py`: Configuration for beancount-import

For more information, see: https://github.com/jbms/beancount-import
