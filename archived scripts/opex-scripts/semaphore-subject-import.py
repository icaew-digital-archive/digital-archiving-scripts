#!/usr/bin/env python
"""
Combines the Semaphore CSV output with the output of a_files_to_csv.py to write the 'dc:subject' terms.

Usage: semaphore-subject-import.py [-h] semaphore_csv dublin_core_csv csv_output
"""

import argparse
import os

import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description='Process CSV files.')

    parser.add_argument('semaphore_csv', help='Path to the Semaphore CSV file')
    parser.add_argument('dublin_core_csv',
                        help='Path to the Dublin Core metadata CSV file')
    parser.add_argument('csv_output', help='Path for the output CSV file')

    args = parser.parse_args()

    # Read the Semaphore CSV into df
    df = pd.read_csv(args.semaphore_csv)

    # Read the Dublin Core metadata CSV into df
    df2 = pd.read_csv(args.dublin_core_csv)

    # Filter to Generic_UPWARD
    df = df[df['Rulebase Class'] == 'Generic_UPWARD']

    # Filter to include only scores higher than 0.48 threshold
    df = df[df['Score'] >= 0.48]

    # Use apply with os.path.basename to get the filenames
    df['Document'] = df['Document'].apply(lambda x: os.path.basename(x))

    # Get unique filenames from the Semaphore df
    unique_documents = df['Document'].unique()

    # Create a dictionary where the unique documents are the key and the subject terms are the value as a list

    # Initialize an empty dictionary to store the results
    result_dict = {}

    # Loop through each unique document and create a dictionary entry
    for document in unique_documents:
        # Filter the DataFrame for the current document
        filtered_df = df[df['Document'] == document]

        # Extract the unique descriptions into a list
        unique_descriptions = filtered_df['Term'].unique().tolist()

        # Create a dictionary entry with the document as the key
        result_dict[document] = unique_descriptions

    # Drop the 'dc:subject' column in the Dublin Core df
    df2 = df2.drop('dc:subject', axis=1)

    # Get the longest list from the dictionary. This is to create the correct number of 'dc:subject' columns
    longest_list = max(result_dict.values(), key=len)

    # Create a list of 'dc:subject' columns
    column_names = ['dc:subject'] * len(longest_list)

    # Create a new df with these column names
    df3 = pd.DataFrame(columns=column_names)

    # Loop through cells in the first column ('Name')
    for value in df2['filename']:
        if value in result_dict:
            new_row_values = result_dict[value]
            # Fill the remaining columns with None values (or any other desired placeholder)
            remaining_columns = len(longest_list) - len(result_dict[value])
            new_row_values.extend([None] * remaining_columns)
            new_row_df = pd.DataFrame(
                [result_dict[value]], columns=df3.columns)
            new_row_df
            df3 = df3._append(new_row_df, ignore_index=True)
        else:
            empty_row = pd.Series(dtype='object')
            df3 = df3._append(empty_row, ignore_index=True)

    # Get first slice from df2
    # Specify the column up to which you want to slice (exclusive)
    specified_column = 'dc:description'

    # Get the column number of the specified column
    column_number = df2.columns.get_loc(specified_column)

    # Slice the DataFrame up to the specified column (exclusive)
    first_slice = df2.iloc[:, :column_number]

    # Get last slice from df2
    # Specify the column up to which you want to slice (exclusive)
    specified_column = 'dc:description'

    # Get the column number of the specified column
    column_number = df2.columns.get_loc(specified_column)

    # Slice the DataFrame up to the specified column (exclusive)
    last_slice = df2.iloc[:, column_number:]

    # Combine the two df slices with df3 (the 'dc:subject' df)
    final_df = first_slice.join(df3).join(last_slice)
    # Strip suffixes that are created when duplicate column names are imported from the CSV
    final_df.columns = final_df.columns.str.rstrip('.1234567890')
    # Convert None values to NaN
    final_df = final_df.fillna(np.nan)

    # Save the DataFrame to a CSV file
    final_df.to_csv(args.csv_output, index=False)


if __name__ == '__main__':
    main()
