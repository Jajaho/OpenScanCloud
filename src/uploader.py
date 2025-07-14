#!/usr/bin/env python3
"""
OpenScanCloud Image Processing Script

This script uploads images to the OpenScanCloud service for 3D reconstruction processing.
It handles image validation, compression, splitting large files, and communicating with
the OpenScanCloud API.

Requirements:
- requests library
- Valid OpenScanCloud token (contact cloud@openscan.eu)
- Directory containing images in supported formats

Author: OpenScan Team
Usage: Configure the variables below and run the script

Custom Exceptions:
- OpenScanError: Raised for OpenScan-specific errors
- OpenScanConfigError: Raised for configuration errors
- OpenScanAPIError: Raised for API communication errors
"""

class OpenScanError(Exception):
    """Base exception for OpenScan-related errors."""
    pass

class OpenScanConfigError(OpenScanError):
    """Raised when there are configuration issues."""
    pass

class OpenScanAPIError(OpenScanError):
    """Raised when there are API communication issues."""
    pass

import os
import requests
import time
import sys
from zipfile import ZipFile

################ Configuration Section - Required Changes ##################
# Directory containing your images for processing
dir_images = ''  # Example: '/path/to/your/images/'

# Temporary directory for zip file creation and splitting
dir_temp = ''    # Example: '/tmp/openscan/' or 'C:\\temp\\openscan\\'

# Your OpenScanCloud API token
# To get a free token, send an email to cloud@openscan.eu with your name
token = ''       # Example: 'your-token-here'

################ System Configuration - No Changes Needed ##################

# Maximum size for each upload part (200MB limit per the API)
size_to_split = 200000000  # 200MB in bytes

# Token limits (populated from API response)
limit_filesize = 0  # Maximum total file size allowed
limit_photos = 0    # Maximum number of photos allowed
credit = 0         # Available processing credits

# Supported image file extensions
allowed_extensions = ['.jpg', '.jpeg', '.JPG', '.JPEG', '.png', '.PNG']

# API configuration
user = 'openscan'
pw = 'free'
server = 'http://openscanfeedback.dnsuser.de:1334/'

# Message dictionary for API communication
msg = {}
msg['token'] = token


def handle_error(error_message):
    """
    Print error message and exit cleanly (for CLI usage).
    
    Args:
        error_message (str): The error message to display
    """
    print(f"ERROR: {error_message}")
    sys.exit(1)


def OpenScanCloud(cmd, msg):
    """
    Make API request to OpenScanCloud server.
    
    Args:
        cmd (str): API endpoint command
        msg (dict): Parameters to send with the request
    
    Returns:
        requests.Response: The API response object
        
    Raises:
        OpenScanAPIError: If the request fails
    """
    try:
        r = requests.get(server + cmd, auth=(user, pw), params=msg)
        return r
    except requests.RequestException as e:
        raise OpenScanAPIError(f"Failed to communicate with server: {str(e)}")


def uploadAndStart(filelist, ulinks):
    """
    Upload file parts to the server and start processing.
    
    Args:
        filelist (list): List of file paths to upload
        ulinks (list): List of upload URLs from the server
        
    Raises:
        OpenScanAPIError: If upload or processing start fails
    """
    i = 0
    for file in filelist:
        print('uploading part ' + str(i+1) + ' of ' + str(len(filelist)))
        link = ulinks[i]
        i = i+1
        
        try:
            # Read file data and upload
            with open(file, 'rb') as f:
                data = f.read()
            r = requests.post(url=link, data=data, headers={'Content-type': 'application/octet-stream'})
            
            if r.status_code != 200:
                raise OpenScanAPIError(f'Upload failed for part {i}: HTTP {r.status_code}')
                
        except (IOError, OSError) as e:
            raise OpenScanAPIError(f'Failed to read file {file}: {str(e)}')
        except requests.RequestException as e:
            raise OpenScanAPIError(f'Network error during upload: {str(e)}')
    
    print('starting project')
    r = OpenScanCloud('startProject', msg)
    
    if r.status_code != 200:
        raise OpenScanAPIError(f'Could not start processing: HTTP {r.status_code}')
    
    print('processing started ... you will get an email soon')
    print('thank you for testing OpenScanCloud')


def getAndVerifyToken():
    """
    Verify the provided token and retrieve account limits.
    
    Updates global variables:
        - limit_filesize: Maximum file size allowed
        - limit_photos: Maximum number of photos allowed
        - credit: Available processing credits
        
    Raises:
        OpenScanAPIError: If token is invalid or API request fails
    """
    print('verifying token')
    global limit_filesize
    global limit_photos
    global credit
    
    if not token:
        raise OpenScanConfigError('Token is required. Please configure the token variable.')
    
    tokenInfo = OpenScanCloud('getTokenInfo', msg)
    
    if tokenInfo.status_code != 200:
        raise OpenScanAPIError(f'Invalid token or API error: HTTP {tokenInfo.status_code}')
    
    try:
        # Extract limits from API response
        response_data = tokenInfo.json()
        limit_filesize = response_data['limit_filesize']
        limit_photos = response_data['limit_photos']
        credit = response_data['credit']
    except (KeyError, ValueError) as e:
        raise OpenScanAPIError(f'Invalid API response format: {str(e)}')


def prepareSet():
    """
    Prepare and validate the image set for processing.
    
    Returns:
        list: List of valid image filenames
    
    Validates:
        - Images exist in specified directory
        - File extensions are supported
        - Total file size is within limits
        - Number of photos is within limits
        
    Raises:
        OpenScanConfigError: If directory doesn't exist or no images found
        OpenScanError: If limits are exceeded
    """
    print('preparing imageset')
    
    if not os.path.exists(dir_images):
        raise OpenScanConfigError(f'Image directory does not exist: {dir_images}')
    
    # Collect valid image files
    image_list = []
    try:
        for filename in os.listdir(dir_images):
            if os.path.splitext(filename)[1] in allowed_extensions:
                image_list.append(filename)
    except OSError as e:
        raise OpenScanConfigError(f'Cannot read image directory: {str(e)}')
    
    if len(image_list) == 0:
        raise OpenScanError(f'No images found in {dir_images}. Supported formats: {", ".join(allowed_extensions)}')
    
    # Calculate total file size
    total_filesize = 0
    try:
        for filename in image_list:
            file_path = os.path.join(dir_images, filename)
            total_filesize += os.path.getsize(file_path)
    except OSError as e:
        raise OpenScanError(f'Cannot access image file: {str(e)}')
    
    # Store photo count in message for API
    msg['photos'] = len(image_list)
    
    # Validate against account limits
    if total_filesize > limit_filesize:
        raise OpenScanError(f'Total file size ({total_filesize} bytes) exceeds limit ({limit_filesize} bytes)')
    
    if len(image_list) > limit_photos:
        raise OpenScanError(f'Number of photos ({len(image_list)}) exceeds limit ({limit_photos})')
    
    return image_list


def zipAndSplit(imagelist):
    """
    Create ZIP archive of images and split if necessary.
    
    Args:
        imagelist (list): List of image filenames to include
    
    Process:
        1. Clean temporary directory
        2. Create ZIP file with timestamp-based name
        3. Split ZIP if larger than size_to_split
        4. Create project on server
        5. Get upload links
        
    Raises:
        OpenScanConfigError: If temporary directory issues
        OpenScanError: If ZIP creation or splitting fails
        OpenScanAPIError: If project creation fails
    """
    print('zipping images')
    
    if not os.path.exists(dir_temp):
        raise OpenScanConfigError(f'Temporary directory does not exist: {dir_temp}')
    
    # Clean temporary directory
    try:
        for filename in os.listdir(dir_temp):
            file_path = os.path.join(dir_temp, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
    except OSError as e:
        raise OpenScanConfigError(f'Cannot clean temporary directory: {str(e)}')
    
    # Generate unique project name with timestamp
    projectname = str(int(time.time()*100)) + '-OSC.zip'
    zipfile_path = os.path.join(dir_temp, projectname)
    
    print('projectname: ' + projectname)
    msg['project'] = projectname
    
    # Create ZIP file with all images
    try:
        with ZipFile(zipfile_path, 'w') as zip_file:
            for filename in imagelist:
                source_path = os.path.join(dir_images, filename)
                if not os.path.exists(source_path):
                    raise OpenScanError(f'Image file not found: {source_path}')
                zip_file.write(source_path, filename)
    except Exception as e:
        raise OpenScanError(f'Failed to create ZIP file: {str(e)}')
    
    # Store file size and initialize parts list
    try:
        msg['filesize'] = os.path.getsize(zipfile_path)
        msg['partslist'] = [zipfile_path]
    except OSError as e:
        raise OpenScanError(f'Cannot access ZIP file: {str(e)}')
    
    # Split file if it exceeds size limit
    if msg['filesize'] > size_to_split:
        msg['partslist'] = []
        part_number = 1
        
        try:
            with open(zipfile_path, 'rb') as source_file:
                chunk = source_file.read(size_to_split)
                
                while chunk:
                    # Create part file
                    part_filename = zipfile_path + '_' + str(part_number)
                    with open(part_filename, 'wb') as part_file:
                        part_file.write(chunk)
                    
                    msg['partslist'].append(part_filename)
                    part_number += 1
                    chunk = source_file.read(size_to_split)
            
            # Remove original ZIP file after splitting
            os.remove(zipfile_path)
            
        except (IOError, OSError) as e:
            raise OpenScanError(f'Failed to split ZIP file: {str(e)}')
    
    # Store number of parts
    msg['parts'] = len(msg['partslist'])
    
    print('preparing project on the OpenScanCloud server')
    r = OpenScanCloud('createProject', msg)
    
    if r.status_code != 200:
        raise OpenScanAPIError(f'Could not create project: HTTP {r.status_code}')
    
    # Get upload links from server response
    try:
        response_data = r.json()
        msg['ulink'] = response_data['ulink']
    except (KeyError, ValueError) as e:
        raise OpenScanAPIError(f'Invalid project creation response: {str(e)}')


def main():
    """
    Main execution function that orchestrates the entire process.
    
    Process flow:
        1. Verify token and get account limits
        2. Prepare and validate image set
        3. Create ZIP archive and split if needed
        4. Upload files and start processing
        
    Returns:
        bool: True if successful, False otherwise (for GUI usage)
        
    Raises:
        OpenScanError: For any OpenScan-related errors
    """
    try:
        # Step 1: Verify token and get limits
        getAndVerifyToken()
        
        # Step 2: Prepare image set
        imagelist = prepareSet()
        
        # Step 3: Create ZIP and split if necessary
        zipAndSplit(imagelist)
        
        # Step 4: Upload and start processing
        uploadAndStart(msg['partslist'], msg['ulink'])
        
        return True
        
    except OpenScanError:
        # Re-raise OpenScan errors for GUI handling
        raise
    except Exception as e:
        # Wrap unexpected errors
        raise OpenScanError(f"Unexpected error: {str(e)}")


def run_cli():
    """
    Command-line interface wrapper that handles errors for CLI usage.
    """
    try:
        main()
    except OpenScanConfigError as e:
        handle_error(f"Configuration error: {str(e)}")
    except OpenScanAPIError as e:
        handle_error(f"API error: {str(e)}")
    except OpenScanError as e:
        handle_error(str(e))
    except Exception as e:
        handle_error(f"Unexpected error: {str(e)}")


# Example GUI integration function
def run_for_gui(error_callback=None, progress_callback=None):
    """
    GUI-friendly wrapper that uses callbacks instead of printing/exiting.
    
    Args:
        error_callback: Function to call with error messages
        progress_callback: Function to call with progress updates
        
    Returns:
        bool: True if successful, False if error occurred
    """
    try:
        if progress_callback:
            progress_callback("Verifying token...")
        getAndVerifyToken()
        
        if progress_callback:
            progress_callback("Preparing image set...")
        imagelist = prepareSet()
        
        if progress_callback:
            progress_callback("Creating ZIP archive...")
        zipAndSplit(imagelist)
        
        if progress_callback:
            progress_callback("Uploading files...")
        uploadAndStart(msg['partslist'], msg['ulink'])
        
        if progress_callback:
            progress_callback("Processing complete!")
        
        return True
        
    except OpenScanError as e:
        if error_callback:
            error_callback(str(e))
        return False
    except Exception as e:
        if error_callback:
            error_callback(f"Unexpected error: {str(e)}")
        return False


# Execute main function if script is run directly
if __name__ == "__main__":
    # Validate configuration before starting
    if not dir_images:
        handle_error('Please configure dir_images variable')
    if not dir_temp:
        handle_error('Please configure dir_temp variable')
    if not token:
        handle_error('Please configure token variable')
    
    # Ensure directories exist
    if not os.path.exists(dir_images):
        handle_error(f'Image directory does not exist: {dir_images}')
    if not os.path.exists(dir_temp):
        handle_error(f'Temporary directory does not exist: {dir_temp}')
    
    # Run the CLI version
    run_cli()