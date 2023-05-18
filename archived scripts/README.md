## browser_auto_open.py

```
usage: browser_auto_open.py [-h] (--chrome | --firefox) [--file_start FILE_START] [--file_end FILE_END] [--pywb] [--collection COLLECTION] [--port PORT] url_list

A tool that opens multiple URLs in a browser from a list of URLs supplied via .txt file. Built to be used in conjunction with Python Wayback (PyWb) in record mode.

positional arguments:
  url_list              .txt file containing list of URLs

optional arguments:
  -h, --help            show this help message and exit
  --chrome              mutually exclusive argument, either --chrome or--firefox flags must be provided
  --firefox             mutually exclusive argument, either --chrome or--firefox flags must be provided
  --file_start FILE_START
                        start point of .txt file to read
  --file_end FILE_END   end point of .txt file to read
  --pywb                this flag enables 'pywb record mode' and builds/opens URLs in the form of localhost:{PORT}/{COLLECTION}/record/{URL}
  --collection COLLECTION
                        required flag when 'pywb record mode' is enabled
  --port PORT           required flag when 'pywb record mode' is enabled
```

## excel2dc.py

Tool to read an Excel spreadsheet and output .metadata XML files that conform to Preservica's metadata input. Template Excel file is included in rep. Columns are customizable and repeatable.

## get_html.py

```
usage: get_html.py [-h] [--authenticate] [--file_start FILE_START] [--file_end FILE_END] [--to_json TO_JSON] [--to_pickle TO_PICKLE] url_list

A tool which visits a list of URLs and saves the HTML content to a Python dictionary. Outputs to json, pickle or terminal (default).

positional arguments:
  url_list              .txt file containing list of URLs to visit

optional arguments:
  -h, --help            show this help message and exit
  --authenticate        gives option to provide authentication credentials
  --file_start FILE_START
                        start point of .txt file to read
  --file_end FILE_END   end point of .txt file to read
  --to_json TO_JSON     file path to .json file output
  --to_pickle TO_PICKLE
                        file path to .pkl file output
```

## os_path_to_url.py

Takes a directory of files and converts the files in the directory to "pseudo" URLs. Built to rebuild the URL path of files/directories from a downloaded and extracted .zip file.

## xml_metadata_validation.py

A tool to quickly find malformed XML .metadata files. Built to test XML .metadata files prior to ingest into Preservica.

## web-scrape.ipynb

A Jupyter notebook that takes the pickle file from get_html.py. This notebook can be used to scrape the HTML content contained in the pickle file. Useful for gathering information about a website prior to web-archiving.

