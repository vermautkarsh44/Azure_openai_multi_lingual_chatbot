from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
import html
import pandas as pd
from tabulate import tabulate

class FormRecognizer:
    def __init__(self, api_key, url):
        formrecognizer_creds = AzureKeyCredential(api_key)
        self.form_recognizer_client = DocumentAnalysisClient(endpoint=url, credential=formrecognizer_creds, headers={"x-ms-useragent": "azure-search-chat-demo/1.0.0"})
    
    def extract_content_from_pdf(self, pdf_path):
        with open(pdf_path, "rb") as f:
            poller = self.form_recognizer_client.begin_analyze_document("prebuilt-document", document = f)
        pages = self.process_form_recognizer_results(poller.result())
        return pages
    
    def extract_content_from_blob(self, blob_bytes):
        poller = self.form_recognizer_client.begin_analyze_document("prebuilt-document", document = blob_bytes)
        pages = self.process_form_recognizer_results(poller.result())
        return pages

    def table_to_html(self, table):
        table_html = "<table>"
        rows = [sorted([cell for cell in table.cells if cell.row_index == i], key=lambda cell: cell.column_index) for i in range(table.row_count)]
        for row_cells in rows:
            table_html += "<tr>"
            for cell in row_cells:
                tag = "th" if (cell.kind == "columnHeader" or cell.kind == "rowHeader") else "td"
                cell_spans = ""
                if cell.column_span > 1: cell_spans += f" colSpan={cell.column_span}"
                if cell.row_span > 1: cell_spans += f" rowSpan={cell.row_span}"
                table_html += f"<{tag}{cell_spans}>{html.escape(cell.content)}</{tag}>"
            table_html +="</tr>"
        table_html += "</table>"
        
        
        df=pd.read_html(table_html)[0]
        try:
            df.replace("", float("NaN"), inplace=True)
            df.dropna(how="all", axis=1, inplace=True)
            df.replace(float("NaN"), "", inplace=True)
            table_str = tabulate(df.to_records(index=False), headers=df.columns, tablefmt="github")
            return '##TABLE##\n'+table_str+'\n'
        except:
            print('html encoding')
            return '##TABLE##\n'+table_html+'\n'
    
    def process_form_recognizer_results(self, form_recognizer_results):
        pages=[]

        for page_num, page in enumerate(form_recognizer_results.pages):
            tables_on_page = [table for table in form_recognizer_results.tables if table.bounding_regions[0].page_number == page_num + 1]

            page_offset = page.spans[0].offset
            page_length = page.spans[0].length
            table_chars = [-1]*page_length
            for table_id, table in enumerate(tables_on_page):
                for span in table.spans:
                    for i in range(span.length):
                        idx = span.offset - page_offset + i
                        if idx >=0 and idx < page_length:
                            table_chars[idx] = table_id

            page_text = ""
            added_tables = set()
            for idx, table_id in enumerate(table_chars):
                if table_id == -1:
                    page_text += form_recognizer_results.content[page_offset + idx]
                elif not table_id in added_tables:
                    page_text += self.table_to_html(tables_on_page[table_id])
                    added_tables.add(table_id)

            page_text += " "

            pages.append(page_text.replace(':selected:','').replace(':unselected:',''))
        
        return pages