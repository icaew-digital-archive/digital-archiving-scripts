# Define the template URL
template_url = "https://open.http.mp.streamamg.com/p/3000931/sp/300093100/playManifest/entryId/REPLACE/flavorParamId/0/format/url/protocol/https"

# Path to the text file containing strings (entry IDs)
txt_file_path = "entry_id_list_complete.txt"  # Replace with the path to your .txt file

# Read the text file and process each line
try:
    with open(txt_file_path, "r") as file:
        for line in file:
            entry_id = line.strip()  # Remove any extra whitespace or newlines
            if entry_id:  # Skip empty lines
                # Replace "0_zogtur3i" with the current entry ID
                updated_url = template_url.replace("REPLACE", entry_id)
                print(updated_url)
except FileNotFoundError:
    print(f"Error: The file '{txt_file_path}' was not found.")
except Exception as e:
    print(f"An error occurred: {e}")
