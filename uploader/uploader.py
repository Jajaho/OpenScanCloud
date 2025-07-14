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
"""

import os
import requests
import time
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


def stop(error_message):
    """
    Print error message and halt execution.
    
    Args:
        error_message (str): The error message to display
    """
    print(error_message)
    while True:
        pass


def OpenScanCloud(cmd, msg):
    """
    Make API request to OpenScanCloud server.
    
    Args:
        cmd (str): API endpoint command
        msg (dict): Parameters to send with the request
    
    Returns:
        requests.Response: The API response object
    """
    r = requests.get(server + cmd, auth=(user, pw), params=msg)
    return r


def uploadAndStart(filelist, ulinks):
    """
    Upload file parts to the server and start processing.
    
    Args:
        filelist (list): List of file paths to upload
        ulinks (list): List of upload URLs from the server
    """
    i = 0
    for file in filelist:
        print('uploading part ' + str(i+1) + ' of ' + str(len(filelist)))
        link = ulinks[i]
        i = i+1
        
        # Read file data and upload
        data = open(file, 'rb').read()
        r = requests.post(url=link, data=data, headers={'Content-type': 'application/octet-stream'})
        
        if r.status_code != 200:
            stop('ERROR: could not upload file')
    
    print('starting project')
    r = OpenScanCloud('startProject', msg)
    
    if r.status_code != 200:
        stop('ERROR: could not start processing')
    
    print('processing started ... you will get an email soon')
    stop('thank you for testing OpenScanCloud')


def getAndVerifyToken():
    """
    Verify the provided token and retrieve account limits.
    
    Updates global variables:
        - limit_filesize: Maximum file size allowed
        - limit_photos: Maximum number of photos allowed
        - credit: Available processing credits
    """
    print('verifying token')
    global limit_filesize
    global limit_photos
    global credit
    
    tokenInfo = OpenScanCloud('getTokenInfo', msg)
    
    if tokenInfo.status_code != 200:
        stop('ERROR: invalid token')
    
    # Extract limits from API response
    limit_filesize = tokenInfo.json()['limit_filesize']
    limit_photos = tokenInfo.json()['limit_photos']
    credit = tokenInfo.json()['credit']


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
    """
    print('preparing imageset')
    
    # Collect valid image files
    image_list = []
    for filename in os.listdir(dir_images):
        if os.path.splitext(filename)[1] in allowed_extensions:
            image_list.append(filename)
    
    if len(image_list) == 0:
        stop('ERROR: no images found in ' + dir_images)
    
    # Calculate total file size
    total_filesize = 0
    for filename in image_list:
        total_filesize += os.path.getsize(dir_images + filename)
    
    # Store photo count in message for API
    msg['photos'] = len(image_list)
    
    # Validate against account limits
    if total_filesize > limit_filesize or len(image_list) > limit_photos:
        stop('ERROR: Limits exceeded')
    
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
    """
    print('zipping images')
    
    # Clean temporary directory
    for filename in os.listdir(dir_temp):
        os.remove(dir_temp + filename)
    
    # Generate unique project name with timestamp
    projectname = str(int(time.time()*100)) + '-OSC.zip'
    zipfile_path = dir_temp + projectname
    
    print('projectname: ' + projectname)
    msg['project'] = projectname
    
    # Create ZIP file with all images
    with ZipFile(zipfile_path, 'w') as zip_file:
        for filename in imagelist:
            zip_file.write(dir_images + filename, filename)
    
    # Store file size and initialize parts list
    msg['filesize'] = os.path.getsize(zipfile_path)
    msg['partslist'] = [zipfile_path]
    
    # Split file if it exceeds size limit
    if os.path.getsize(zipfile_path) > size_to_split:
        msg['partslist'] = []
        part_number = 1
        
        with open(zipfile_path, 'rb') as source_file:
            chunk = source_file.read(size_to_split)
            
            while chunk:
                # Create part file
                part_filename = zipfile_path + '_' + str(part_number)
                with open(part_filename, 'wb+') as part_file:
                    part_file.write(chunk)
                
                msg['partslist'].append(part_filename)
                part_number += 1
                chunk = source_file.read(size_to_split)
        
        # Remove original ZIP file after splitting
        os.remove(zipfile_path)
    
    # Store number of parts
    msg['parts'] = len(msg['partslist'])
    
    print('preparing project on the OpenScanCloud server')
    r = OpenScanCloud('createProject', msg)
    
    if r.status_code != 200:
        stop('ERROR: Could not create project')
    
    # Get upload links from server response
    msg['ulink'] = r.json()['ulink']


def main():
    """
    Main execution function that orchestrates the entire process.
    
    Process flow:
        1. Verify token and get account limits
        2. Prepare and validate image set
        3. Create ZIP archive and split if needed
        4. Upload files and start processing
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
        
    except Exception as e:
        stop(f'ERROR: Unexpected error occurred: {str(e)}')


# Execute main function if script is run directly
if __name__ == "__main__":
    # Validate configuration before starting
    if not dir_images:
        stop('ERROR: Please configure dir_images variable')
    if not dir_temp:
        stop('ERROR: Please configure dir_temp variable')
    if not token:
        stop('ERROR: Please configure token variable')
    
    # Ensure directories exist and have proper path separators
    if not os.path.exists(dir_images):
        stop('ERROR: Image directory does not exist: ' + dir_images)
    if not os.path.exists(dir_temp):
        stop('ERROR: Temporary directory does not exist: ' + dir_temp)
    
    # Run the main process
    main()