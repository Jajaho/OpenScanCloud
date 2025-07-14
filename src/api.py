import os
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path

class OpenScanAPIError(Exception):
    """Custom exception for API-related errors"""
    pass

class OpenScanAPI:
    def __init__(self, server: str, user: str, password: str):
        """Initialize API client with server details and credentials"""
        self.server = server.rstrip('/')
        self.auth = (user, password)

    def _request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make authenticated request to API endpoint"""
        try:
            response = requests.get(
                f"{self.server}/{endpoint}", 
                auth=self.auth,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise OpenScanAPIError(f"API request failed: {str(e)}")

    def request_token(self, email: str, forename: str, lastname: str) -> Dict[str, Any]:
        """Request a new token"""
        return self._request('requestToken', {
            'mail': email,
            'forename': forename,
            'lastname': lastname
        })

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Get token information and limits"""
        return self._request('getTokenInfo', {'token': token})

    def get_project_info(self, token: str, project: str) -> Dict[str, Any]:
        """Get information about a specific project"""
        return self._request('getProjectInfo', {
            'token': token,
            'project': project
        })

    def create_project(self, token: str, project: str, photos: int, 
                      parts: int, filesize: int) -> Dict[str, Any]:
        """Create a new project"""
        return self._request('createProject', {
            'token': token,
            'project': project,
            'photos': photos,
            'parts': parts,
            'filesize': filesize
        })

    def reset_project(self, token: str, project: str) -> Dict[str, Any]:
        """Reset an existing project"""
        return self._request('resetProject', {
            'token': token,
            'project': project
        })

    def start_project(self, token: str, project: str) -> Dict[str, Any]:
        """Start processing a project"""
        return self._request('startProject', {
            'token': token,
            'project': project
        })

    def upload_part(self, file_path: Path, upload_url: str) -> None:
        """Upload file part to provided URL"""
        if not os.path.exists(file_path):
            raise OpenScanAPIError(f"File not found: {file_path}")
        
        try:
            with open(file_path, 'rb') as f:
                response = requests.put(upload_url, data=f)
                response.raise_for_status()
        except requests.RequestException as e:
            raise OpenScanAPIError(f"Failed to upload {file_path}: {str(e)}")

    def get_server_status(self) -> Dict[str, Any]:
        """Get current server status"""
        return self._request('status')

    def get_queue_estimate(self) -> Dict[str, Any]:
        """Get current processing queue status"""
        return self._request('getQueueEstimate')