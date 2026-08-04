import json
import os
import sys

# Check if the command line argument for the file path is provided
if len(sys.argv) > 1:
    json_file_path = sys.argv[1]
else:
    print("Please provide the path to the JSON file as a command line argument.")
    sys.exit(1)

if os.path.isfile(json_file_path):
    try:
        with open(json_file_path, 'r') as json_file:
            json_list = json_file.readlines()[1:]  # Exclude the first line

        for json_str in json_list:
            try:
                data = json.loads(json_str)
                print(data['url'])
                # Uncomment the following lines if you need to print additional information
                # print(f"Data: {data}")
                # print(isinstance(data, dict))
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {str(e)}")
    except IOError as e:
        print(f"Error reading file: {str(e)}")
else:
    print(f"File not found: {json_file_path}")

