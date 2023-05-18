#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tool to read an Excel spreadsheet and output .metadata XML files that conform 
to Preservica's metadata input. Template Excel file is included in rep.
Columns are customizable and repeatable.
"""

import os.path
from os import path

import pandas as pd


def main():
    excel_file = input('Enter path to Excel file: ').strip().strip("'\"")
    # keep_default_na stops empty cells appearing as 'nan' string
    # includes some extra code to get around pandas not allowing duplicate
    # headers, answer found here - https://github.com/pandas-dev/pandas/issues/19383
    df = pd.read_excel(excel_file, keep_default_na=False, header=None)
    df.columns = df.iloc[0]
    df = df.reindex(df.index.drop(0)).reset_index(drop=True)

    file_content_dict = {}  # dict containing filename:string pairs

    for i in range(len(df)):  # len(df) is number of rows
        xml_body = []
        for j in range(len(df.columns))[1:]:  # skip first column
            xml_body.append(
                f'\t\t<{df.columns[j]}>{df.iloc[i, j]}</{df.columns[j]}>')
        # join list to string
        xml_body_string = '\n'.join(xml_body)
        # add root tags to complete the string
        xml_complete = f"""<?xml version="1.0" encoding="UTF-8"?>\n\t<oai_dc:dc xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/ oai_dc.xsd" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
{xml_body_string}
\t</oai_dc:dc>"""
        # assign to dict
        file_content_dict[df.iloc[i, 0]] = xml_complete

    # create path if it doesn't exist
    if not os.path.isdir('xml-metadata'):
        os.mkdir('xml-metadata')

    # write files
    for filename, content in file_content_dict.items():
        with open(os.path.join('xml-metadata', f'{filename}.metadata'), 'w') as f:
            f.write(content)

    print(f'Finished writing {len(file_content_dict)} .metadata files!')
    input()

if __name__ == '__main__':
    main()
