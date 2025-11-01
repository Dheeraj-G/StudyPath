/**
 * File Upload Service with GCS Signed URLs
 * Handles file uploads to Google Cloud Storage using signed URLs
 */

export interface FileUploadRequest {
  file_name: string;
  file_type: string;
  file_size: number;
  content_type: string;
}

export interface FileUploadResponse {
  upload_url: string;
  file_id: string;
  file_path: string;
  expires_at: string;
  fields: Record<string, string>;
}

export interface FileUploadComplete {
  file_id: string;
  file_path: string;
  file_size: number;
}

export interface UploadedFile {
  file_id: string;
  file_name: string;
  file_size: number;
  content_type: string;
  uploaded_at: string;
  status: 'uploading' | 'uploaded' | 'processing' | 'completed' | 'error';
}

class FileUploadService {
  private baseUrl: string;
  private authToken: string | null = null;

  constructor(baseUrl: string = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  setAuthToken(token: string) {
    this.authToken = token;
  }

  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> | undefined),
    };

    if (this.authToken) {
      headers.Authorization = `Bearer ${this.authToken}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`HTTP ${response.status}: ${error}`);
    }

    return response.json();
  }

  async generateUploadUrl(file: File): Promise<FileUploadResponse> {
    const request: FileUploadRequest = {
      file_name: file.name,
      file_type: file.type,
      file_size: file.size,
      content_type: file.type,
    };

    return this.makeRequest<FileUploadResponse>('/api/files/upload-url', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async uploadFileToGCS(file: File, uploadInfo: FileUploadResponse): Promise<void> {
    // Upload directly to GCS using the signed URL (PUT request)
    try {
      const response = await fetch(uploadInfo.upload_url, {
        method: 'PUT',
        body: file,
        headers: {
          'Content-Type': file.type,
        },
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'No error details available');
        throw new Error(`Upload failed: ${response.status} ${response.statusText} - ${errorText}`);
      }
    } catch (error) {
      // Handle network errors (CORS, connection issues, etc.)
      if (error instanceof TypeError && error.message === 'Failed to fetch') {
        throw new Error(
          'Failed to upload file. This may be a CORS issue. Please ensure your GCS/Firebase Storage bucket has CORS configured to allow PUT requests from your origin. See backend/CORS_SETUP.md for setup instructions.'
        );
      }
      throw error;
    }
  }

  async completeFileUpload(fileId: string, filePath: string, fileSize: number): Promise<void> {
    const request: FileUploadComplete = {
      file_id: fileId,
      file_path: filePath,
      file_size: fileSize,
    };

    await this.makeRequest('/api/files/complete', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async uploadFile(file: File): Promise<UploadedFile> {
    try {
      // Step 1: Generate signed URL
      const uploadInfo = await this.generateUploadUrl(file);
      
      // Step 2: Upload file to GCS
      await this.uploadFileToGCS(file, uploadInfo);
      
      // Step 3: Complete upload
      await this.completeFileUpload(uploadInfo.file_id, uploadInfo.file_path, file.size);
      
      return {
        file_id: uploadInfo.file_id,
        file_name: file.name,
        file_size: file.size,
        content_type: file.type,
        uploaded_at: new Date().toISOString(),
        status: 'uploaded',
      };
    } catch (error) {
      console.error('File upload error:', error);
      throw error;
    }
  }

  async getUserFiles(): Promise<UploadedFile[]> {
    const response = await this.makeRequest<{ files: UploadedFile[] }>('/api/files/files');
    return response.files;
  }

  async deleteFile(fileId: string): Promise<void> {
    await this.makeRequest(`/api/files/files/${fileId}`, {
      method: 'DELETE',
    });
  }

  async startLearningSession(topic: string, goals: string[] = []): Promise<{ session_id: string; status: string }> {
    return this.makeRequest(`/api/orchestrator/learning-session`, {
      method: 'POST',
      body: JSON.stringify({ topic, goals }),
    });
  }

  // Utility method to format file size
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  // Utility method to validate file type
  isValidFileType(file: File): boolean {
    const allowedTypes = [
      'application/pdf',
      'text/plain',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'image/jpeg',
      'image/png',
      'image/gif',
      'video/mp4',
      'video/mpeg',
      'video/quicktime',
      'audio/mpeg',
      'audio/wav',
      'audio/mp3',
      // Also check by file extension as fallback (browser may not set MIME type correctly)
    ];
    
    // Check by MIME type
    if (allowedTypes.includes(file.type)) {
      return true;
    }
    
    // Fallback: Check by file extension for audio files
    const fileName = file.name.toLowerCase();
    const audioExtensions = ['.mp3', '.wav', '.m4a', '.aac'];
    if (audioExtensions.some(ext => fileName.endsWith(ext))) {
      return true;
    }
    
    return false;
  }

  // Utility method to validate file size (100MB limit)
  isValidFileSize(file: File): boolean {
    const maxSize = 100 * 1024 * 1024; // 100MB
    return file.size <= maxSize;
  }
}

export const fileUploadService = new FileUploadService();
