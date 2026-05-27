import os
import argparse
import logging
from pyPreservica import simple_asset_package, UploadAPI, UploadProgressCallback
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

# Retrieve environment variables
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
TENANT = os.getenv('TENANT')
SERVER = os.getenv('SERVER')

# Initialize the UploadAPI client
client = UploadAPI(username=USERNAME,
                   password=PASSWORD, tenant=TENANT, server=SERVER)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lists to keep track of successful and failed uploads
successful_uploads = []
failed_uploads = []


def upload_file(file_path, parent_folder_id):
    try:
        # Create a ZIP package for the asset with the provided file path and parent folder ID
        zip_package = simple_asset_package(
            preservation_file=file_path,
            parent_folder=parent_folder_id
        )

        # Create an upload progress callback instance
        upload_callback = UploadProgressCallback(zip_package)

        logger.info(f"Ingesting XIPv6 package of: {file_path}")

        # Upload the ZIP package to the server, with a progress callback and delete the ZIP file after upload
        client.upload_zip_package(
            zip_package,
            delete_after_upload=True,
            callback=upload_callback
        )

        logger.info(f"Successfully uploaded: {file_path}")
        successful_uploads.append(file_path)

    except Exception as e:
        logger.error(f"Failed to upload: {file_path} with error: {e}")
        failed_uploads.append(file_path)


def upload_files_from_directory(directory_path, parent_folder_id):
    try:
        logger.info(
            f"Starting to crawl and upload files from: {directory_path}")

        client.crawl_filesystem(
            filesystem_path=directory_path,
            preservica_parent=parent_folder_id
        )

        logger.info(f"Successfully uploaded files from: {directory_path}")
        successful_uploads.append(directory_path)

    except Exception as e:
        logger.error(
            f"Failed to upload files from: {directory_path} with error: {e}")
        failed_uploads.append(directory_path)


def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(
        description="Upload files or folders to Preservica.")
    parser.add_argument('parent_folder_id',
                        help="The parent folder ID in Preservica")
    parser.add_argument('path', help="The file or folder path to upload")

    args = parser.parse_args()

    path = args.path
    parent_folder_id = args.parent_folder_id

    if os.path.isfile(path):
        upload_file(path, parent_folder_id)
    elif os.path.isdir(path):
        upload_files_from_directory(path, parent_folder_id)
    else:
        logger.error("The provided path is neither a file nor a directory")

    # Print summary of uploads
    logger.info("Upload Summary:")
    logger.info(f"Successful uploads: {len(successful_uploads)}")
    logger.info(f"Failed uploads: {len(failed_uploads)}")

    if failed_uploads:
        logger.info("List of failed uploads:")
        for failed_file in failed_uploads:
            logger.info(failed_file)


if __name__ == "__main__":
    main()
