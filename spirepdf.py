from spire.pdf import *
from spire.xls import *

# Define a function to extract data from PDF tables to Excel
def extract_table_data_to_excel(pdf_path, xls_path):
    # Create an instance of the PdfDocument class
    doc = PdfDocument()

    try:
        # Load a PDF document
        doc.LoadFromFile(pdf_path)

        # Create an instance of the PdfTableExtractor class
        extractor = PdfTableExtractor(doc)

        # Create an instance of the Workbook class
        workbook = Workbook()
        # Remove the default 3 worksheets
        workbook.Worksheets.Clear()
        
        # Iterate through the pages in the PDF document
        for page_index in range(doc.Pages.Count):
            # Extract tables from each page
            tables = extractor.ExtractTable(page_index)
            if tables is not None and len(tables) > 0:
                # Iterate through the extracted tables
                for table_index, table in enumerate(tables):
                    # Create a new worksheet for each table
                    worksheet = workbook.CreateEmptySheet()  
                    # Set the worksheet name
                    worksheet.Name = f"Table {table_index + 1} of Page {page_index + 1}"  
                    
                    row_count = table.GetRowCount()
                    col_count = table.GetColumnCount()

                    # Extract data from the table and populate the worksheet
                    for row_index in range(row_count):
                        for column_index in range(col_count):
                            data = table.GetText(row_index, column_index)
                            worksheet.Range[row_index + 1, column_index + 1].Value = data.strip()
                    
                    # Auto adjust column widths of the worksheet
                    worksheet.Range.AutoFitColumns()

        # Save the workbook to the specified Excel file
        workbook.SaveToFile(xls_path, ExcelVersion.Version2013)

    except Exception as e:
        print(f"Error occurred: {str(e)}")

# Example usage
pdf_path = "Tables.pdf"
xls_path = "table_data.xlsx"
extract_table_data_to_excel(pdf_path, xls_path)