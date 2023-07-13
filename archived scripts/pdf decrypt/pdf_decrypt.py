#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple tool to decrypt a folder of PDFs using pikepdf.
"""

import os

import pikepdf
from pikepdf import _cpphelpers


def main():

    # Get folder containing PDF
    dir_path = input(
        "Enter path to folder containing PDFs: ").strip().strip("'\"")
    dir_path_split = os.path.split(dir_path)
    parent_folder, folder_name = dir_path_split[0], dir_path_split[1]

    # Get PDF paths
    pdf_paths = []
    for root, directories, filenames in os.walk(dir_path):
        for filename in filenames:
            if filename.endswith(('.pdf', '.PDF')):
                pdf_paths.append(os.path.join(root, filename))

    # Create folder to save decrypted PDFs
    decrypted_folder_name = f'{folder_name}-decrypted'
    if not os.path.exists(os.path.join(parent_folder, decrypted_folder_name)):
        print(f'Creating {decrypted_folder_name} directory')
        os.mkdir(os.path.join(parent_folder, decrypted_folder_name))

    # Open and create decrypted PDFs in decrypted-PDFs folder
    for pdf in pdf_paths:
        pdf_path_split = os.path.split(pdf)
        pdf_parent_folder, pdf_name = pdf_path_split[0], pdf_path_split[1]
        decrypted_pdf = pikepdf.open(pdf)
        save_path = os.path.join(parent_folder, decrypted_folder_name)
        decrypted_pdf.save(os.path.join(save_path, pdf_name))
        print(f"Successfully decrypted {pdf_name}")


if __name__ == '__main__':
    main()
