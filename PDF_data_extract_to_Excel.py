from pdfminer.layout import LAParams, LTTextBox
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
import pandas as pd

fp = open(r'C:\Users\lcheng\Downloads\MPD.pdf', 'rb')
rsrcmgr = PDFResourceManager()
laparams = LAParams()
device = PDFPageAggregator(rsrcmgr, laparams=laparams)
interpreter = PDFPageInterpreter(rsrcmgr, device)
pages = PDFPage.get_pages(fp)


# Define boxes (Example: {'box_name': (x0, y0, x1, y1)})
boxes = {
    'Aircraft Model': (40.033, 153.713675, 106.85308400000002, 480.04184),
    'Engine Model': (122.245, 153.71417500000032, 202.48306300000002, 480.04283999999996),
    'LIGHT(A)': (225.902, 344.68397500000003, 363.00790699999993, 478.61283999999995),
    'Intermediate(C)': (371.023, 344.68397500000003, 506.30226999999996, 478.61283999999995),
    'Medium (4C)': (225.902, 151.794075, 362.507731, 297.74784),
    'Heavy (8C)': (371.738, 151.794075, 508.300607, 297.74784),
    'Additonal information': (40.033, 58.313375, 829.6429730000018, 120.09204),
    'Airline Name': (554.748, 519.6141749999999, 828.9829729999997, 533.29324)
}


all_page_data = []

for page in pages:
    print('Processing next page...')
    interpreter.process_page(page)
    layout = device.get_result()
    # Initialize a dictionary to hold collected text for each box
    collected_text = {box_name: "" for box_name in boxes.keys()}
    for lobj in layout:
        if isinstance(lobj, LTTextBox):
            x0, y0, x1, y1 = lobj.bbox
            for box_name, (bx0, by0, bx1, by1) in boxes.items():
                # Check if the text box overlaps with the box
                if not (x1 < bx0 or x0 > bx1 or y1 < by0 or y0 > by1):
                    collected_text[box_name] += lobj.get_text() + " "  # Concatenate text within the same box

    # Print collected text for each box
    for box_name, text in collected_text.items():
        print(f'{box_name} contains text: {text.strip()}')
    
    for check_type in ['LIGHT(A)', 'Intermediate(C)', 'Medium (4C)', 'Heavy (8C)']:
        row = {
                "Year": 2022,
                "Source": "Airbus",
                "Aircraft Model": collected_text['Aircraft Model'].strip(),
                "Engine Type": collected_text['Engine Model'].strip(),
                "Event Name": check_type,
                "Mx Interval (FC/ FH/ MO)": collected_text[check_type].strip(),
                "Airline": collected_text['Airline Name'].strip(),
                "Additional information": collected_text['Additonal information'].strip()
            }
        
        # Only add the row if there is data for the Mx Interval
        if row["Mx Interval (FC/ FH/ MO)"]:
            all_page_data.append(row)


# Convert the data to a DataFrame
df = pd.DataFrame(all_page_data)

# Define the file path where the Excel file will be saved
output_excel_path = 'test.xlsx'

# Save the DataFrame to an Excel file
df.to_excel(output_excel_path, index=False)

# # Create boxes in the fake PDF so that you know where the box coordinates is
# for page in pages:
#     print('Processing next page...')
#     interpreter.process_page(page)
#     layout = device.get_result()
#     for lobj in layout:
#         if isinstance(lobj, LTTextBox):
#             x0, y0, x1, y1 = lobj.bbox
#             text = lobj.get_text()
#             print('At %r is text: %s' % ((x0, y0, x1, y1), text))
            


fp.close()