import argparse
import sys
from pathlib import Path
from typing import Optional

from api import OpenScanAPI, OpenScanAPIError
from backend import OpenScanBackend, OpenScanBackendError

DEFAULT_CONFIG = {
    'server': 'http://openscanfeedback.dnsuser.de:1334/',
    'user': 'openscan',
    'password': 'free',
    'allowed_extensions': ['.jpg', '.jpeg', '.JPG', '.JPEG', '.png', '.PNG'],
    'size_to_split': 200_000_000  # 200MB in bytes
}

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='OpenScanCloud Command Line Interface'
    )
    parser.add_argument(
        '-t', '--token',
        required=True,
        help='Your OpenScanCloud API token'
    )
    parser.add_argument(
        '-i', '--input',
        type=Path,
        required=True,
        help='Directory containing images to process'
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        default=Path.home() / 'OpenScanCloud' / 'temp',
        help='Temporary directory for processing'
    )
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Only verify the token without processing images'
    )
    return parser.parse_args()

def verify_token(api: OpenScanAPI, token: str) -> Optional[dict]:
    """Verify token and return account limits"""
    try:
        info = api.verify_token(token)
        print(f"Token verified successfully!")
        print(f"Credit remaining: {info['credit'] / 1_000_000_000:.2f}GB")
        print(f"Max filesize: {info['limit_filesize'] / 1_000_000:.2f}MB")
        print(f"Max photos: {info['limit_photos']}")
        return info
    except OpenScanAPIError as e:
        print(f"Error verifying token: {e}", file=sys.stderr)
        return None

def main():
    args = parse_args()

    # Create API client
    api = OpenScanAPI(
        DEFAULT_CONFIG['server'],
        DEFAULT_CONFIG['user'],
        DEFAULT_CONFIG['password']
    )

    # Verify token
    info = verify_token(api, args.token)
    if not info or args.verify_only:
        sys.exit(1 if not info else 0)

    # Initialize backend
    backend = OpenScanBackend(
        allowed_extensions=DEFAULT_CONFIG['allowed_extensions'],
        size_to_split=DEFAULT_CONFIG['size_to_split']
    )

    try:
        # Prepare images
        print(f"Scanning directory: {args.input}")
        image_list = backend.prepare_image_list(args.input)
        print(f"Found {len(image_list)} valid images")

        # Create temporary directory
        args.output.mkdir(parents=True, exist_ok=True)
        
        # Zip and split files
        print("Creating zip archive...")
        project_name, parts_list, total_size = backend.zip_and_split(
            image_list, args.input, args.output
        )
        print(f"Created {len(parts_list)} parts, total size: {total_size/1_000_000:.2f}MB")

        # Prepare API message
        msg = {
            'token': args.token,
            'project': project_name,
            'photos': len(image_list),
            'filesize': total_size,
            'parts': len(parts_list)
        }

        # Create project
        print("Creating project on server...")
        project = api.create_project(msg)
        
        # Upload parts
        print("Uploading files...")
        for i, part in enumerate(parts_list, 1):
            print(f"Uploading part {i}/{len(parts_list)}...")
            api.upload_part(part, project['ulink'][i-1])

        # Start processing
        print("Starting processing...")
        api.start_project(msg)
        print("Processing started successfully! You will receive an email when complete.")

    except (OpenScanAPIError, OpenScanBackendError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    finally:
        # Cleanup temporary files
        if args.output.exists():
            print("Cleaning up temporary files...")
            backend.cleanup_temp_dir(args.output)

if __name__ == '__main__':
    main()