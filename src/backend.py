import os
import time
import shutil
from typing import List, Tuple
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

class OpenScanBackendError(Exception):
    """Custom exception for backend processing errors"""
    pass

class OpenScanBackend:
    def __init__(self, allowed_extensions: List[str], size_to_split: int):
        """Initialize backend with configuration"""
        self.allowed_extensions = allowed_extensions
        self.size_to_split = size_to_split

    def prepare_image_list(self, input_dir: Path) -> List[str]:
        """Validate directory and return list of valid image files"""
        if not input_dir.exists():
            raise OpenScanBackendError(f"Directory not found: {input_dir}")
        if not input_dir.is_dir():
            raise OpenScanBackendError(f"Not a directory: {input_dir}")

        images = [
            f.name for f in input_dir.iterdir()
            if f.is_file() and f.suffix in self.allowed_extensions
        ]

        if not images:
            raise OpenScanBackendError(
                f"No valid images found in {input_dir}. "
                f"Supported formats: {', '.join(self.allowed_extensions)}"
            )

        return sorted(images)

    def zip_and_split(
        self, 
        image_list: List[str], 
        input_dir: Path, 
        temp_dir: Path
    ) -> Tuple[str, List[Path], int]:
        """Create zip archive and split if needed"""
        # Create unique project name
        project_name = f"{int(time.time()*100)}-OSC.zip"
        zip_path = temp_dir / project_name

        # Create zip archive
        with ZipFile(zip_path, 'w', ZIP_DEFLATED) as zipf:
            for img in image_list:
                zipf.write(input_dir / img, img)

        total_size = zip_path.stat().st_size
        parts: List[Path] = []

        # Split if needed
        if total_size > self.size_to_split:
            parts = self._split_file(zip_path)
            zip_path.unlink()
        else:
            parts = [zip_path]

        return project_name, parts, total_size

    def _split_file(self, file_path: Path) -> List[Path]:
        """Split large file into smaller parts"""
        parts: List[Path] = []
        part_num = 1

        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(self.size_to_split)
                if not chunk:
                    break

                part_path = file_path.with_name(f"{file_path.name}_{part_num}")
                with open(part_path, 'wb') as part_file:
                    part_file.write(chunk)
                parts.append(part_path)
                part_num += 1

        return parts

    def cleanup_temp_dir(self, temp_dir: Path) -> None:
        """Remove temporary directory and its contents"""
        try:
            shutil.rmtree(temp_dir)
        except OSError as e:
            print(f"Warning: Failed to clean up {temp_dir}: {e}")