# TechnoWorld Transaction Processing and Classification

Welcome to **TechnoWorld**, an integrated system for processing and analyzing financial transactions using Beancount and a custom LLM-based transaction classifier. This repository provides tools to automatically categorize bank transactions (including UPI transactions), generate Beancount journal entries, and enable manual review via a Beancount-import web server.

## Project Overview

TechnoWorld is designed to help you:

- **Automatically classify transactions**: The LLM-based classifier reads transaction files (CSV/Excel), applies rule-based logic and regular expressions to classify transactions, and extracts key data (e.g., UPI payee information).
- **Generate Beancount entries**: Convert classified transactions into Beancount journal entries for further financial processing.
- **Enable manual review & categorization**: Use the integrated Beancount-import web server for manual transaction review and refinement.

## Project Structure

- **accountparser/**: Contains raw statements and parsing scripts (e.g., CSV, PDF).
- **beancount/**: Contains Beancount configuration files and sample journals.
- **llm_classification/**:
  - `llm_classifier.py`: The LLM-based transaction classifier that processes bank statements, classifies transactions, and generates output files.
  - `summary_report.py`: Generates a detailed summary report including statistics and UPI transaction analysis.
- **README.md**: This documentation file.

## Installation

### Prerequisites

- **Python 3.12** or higher
- **virtualenv** for creating isolated Python environments
- **uv** (or your preferred package manager) for installing dependencies

### Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/smukherjee/technoworld.git
   cd technoworld
   ```

2. **Create and Activate a Virtual Environment**
   ```bash
   python -m venv technoworld
   source technoworld/bin/activate  # On macOS/Linux
   ```

3. **Install Dependencies**
   Install required Python packages:
   ```bash
   uv pip install -r requirements.txt
   ```
   If a `requirements.txt` is not available, manually install:
   ```bash
   uv pip install pandas openpyxl xlrd beancount beancount-import
   ```

## Usage

### Running the LLM Transaction Classifier

The classifier processes bank transaction files (both CSV and Excel) and outputs:

- A classified CSV file (`llm_classification/classified_transactions.csv`) with detailed results and confidence scores.
- A Beancount journal file (`llm_classification/classified_transactions.beancount`) ready for import.

To run the classifier:

```bash
source technoworld/bin/activate
python llm_classification/llm_classifier.py
```

### Viewing the Classification Summary

Generate a summary report with statistics and UPI analysis:

```bash
python llm_classification/summary_report.py
```

### Using the Beancount-import Web Server

For manual review and categorization:

```bash
cd beancount/beancount_import_output
source /path/to/technoworld/bin/activate
python -m beancount_import.webserver --port 8080 --default_output ./journal_output.beancount --journal_input base_journal.beancount --ignored_journal /dev/null
```

Adjust the paths as necessary.

## Functions and Files Overview

- **LLM Transaction Classifier (`llm_classifier.py`)**: Reads transaction files, extracts key information (including UPI details), classifies transactions into categories (e.g., food, shopping, salary), and generates CSV and Beancount outputs.
- **Summary Report (`summary_report.py`)**: Provides a detailed report of overall statistics, UPI transaction analysis, and amount analysis.
- **Accountparser**: Contains raw bank statement files and parsing scripts.
- **Beancount Integration**: Tools and configurations for converting transactions into Beancount journal entries.

## Contributing

Contributions to improve classification accuracy, extend functionality, or integrate with external APIs are welcome. Please open issues or submit pull requests.

## License

This project is licensed under the [MIT License](LICENSE).

## Contact

For any issues or inquiries, please contact [smukherjee](mailto:smukherjee@github.com).
