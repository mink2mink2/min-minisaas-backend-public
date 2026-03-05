/// PDF service for API interactions

import 'dart:io';
import 'package:dio/dio.dart';
import 'package:path_provider/path_provider.dart';
import 'pdf_models.dart';

class PdfService {
  final Dio _dio;
  static const String _baseUrl = '/api/v1/pdf';

  PdfService({required Dio apiClient}) : _dio = apiClient;

  /// Upload a PDF file
  ///
  /// POST /api/v1/pdf/upload
  /// Returns: PdfFile with status 'uploaded'
  Future<PdfFile> uploadPdf(File file) async {
    try {
      final formData = FormData.fromMap({
        'file': await MultipartFile.fromFile(
          file.path,
          filename: file.path.split('/').last,
        ),
      });

      final response = await _dio.post(
        '$_baseUrl/upload',
        data: formData,
      );

      return PdfFile.fromJson(response.data);
    } on DioException catch (e) {
      throw PdfServiceException(
        'Failed to upload PDF: ${e.message}',
        statusCode: e.response?.statusCode,
      );
    }
  }

  /// Request PDF conversion
  ///
  /// POST /api/v1/pdf/{fileId}/convert
  /// Returns: PdfConversionStatus with status 'processing'
  /// Throws: 402 if insufficient points
  Future<PdfConversionStatus> requestConversion(String fileId) async {
    try {
      final response = await _dio.post('$_baseUrl/$fileId/convert');
      return PdfConversionStatus.fromJson(response.data);
    } on DioException catch (e) {
      if (e.response?.statusCode == 402) {
        throw InsufficientPointsException(
          e.response?.data['detail'] ?? 'Insufficient points',
        );
      }
      throw PdfServiceException(
        'Failed to request conversion: ${e.message}',
        statusCode: e.response?.statusCode,
      );
    }
  }

  /// Get conversion status
  ///
  /// GET /api/v1/pdf/{fileId}/status
  /// Returns: PdfConversionStatus with current status
  Future<PdfConversionStatus> getStatus(String fileId) async {
    try {
      final response = await _dio.get('$_baseUrl/$fileId/status');
      return PdfConversionStatus.fromJson(response.data);
    } on DioException catch (e) {
      throw PdfServiceException(
        'Failed to get status: ${e.message}',
        statusCode: e.response?.statusCode,
      );
    }
  }

  /// Get user's PDF files
  ///
  /// GET /api/v1/pdf/user/files?skip=0&limit=20
  /// Returns: List of PdfFile objects
  Future<List<PdfFile>> getUserFiles({
    int skip = 0,
    int limit = 20,
  }) async {
    try {
      final response = await _dio.get(
        '$_baseUrl/user/files',
        queryParameters: {
          'skip': skip,
          'limit': limit,
        },
      );

      if (response.data is List) {
        return (response.data as List)
            .map((item) => PdfFile.fromJson(item as Map<String, dynamic>))
            .toList();
      }
      return [];
    } on DioException catch (e) {
      throw PdfServiceException(
        'Failed to get files: ${e.message}',
        statusCode: e.response?.statusCode,
      );
    }
  }

  /// Get file details
  ///
  /// GET /api/v1/pdf/{fileId}
  /// Returns: PdfFile object
  Future<PdfFile> getFileDetails(String fileId) async {
    try {
      final response = await _dio.get('$_baseUrl/$fileId');
      return PdfFile.fromJson(response.data);
    } on DioException catch (e) {
      throw PdfServiceException(
        'Failed to get file details: ${e.message}',
        statusCode: e.response?.statusCode,
      );
    }
  }

  /// Download converted CSV file
  ///
  /// GET /api/v1/pdf/{fileId}/download
  /// Streams CSV file to savePath
  Future<void> downloadCsv(
    String fileId,
    String savePath,
  ) async {
    try {
      await _dio.download(
        '$_baseUrl/$fileId/download',
        savePath,
      );
    } on DioException catch (e) {
      throw PdfServiceException(
        'Failed to download CSV: ${e.message}',
        statusCode: e.response?.statusCode,
      );
    }
  }

  /// Download converted CSV file with progress callback
  ///
  /// GET /api/v1/pdf/{fileId}/download
  /// Streams CSV file with progress updates
  Future<void> downloadCsvWithProgress(
    String fileId,
    String savePath, {
    required Function(int received, int total) onProgress,
  }) async {
    try {
      await _dio.download(
        '$_baseUrl/$fileId/download',
        savePath,
        onReceiveProgress: onProgress,
      );
    } on DioException catch (e) {
      throw PdfServiceException(
        'Failed to download CSV: ${e.message}',
        statusCode: e.response?.statusCode,
      );
    }
  }

  /// Delete a PDF file
  ///
  /// DELETE /api/v1/pdf/{fileId}
  Future<void> deleteFile(String fileId) async {
    try {
      await _dio.delete('$_baseUrl/$fileId');
    } on DioException catch (e) {
      throw PdfServiceException(
        'Failed to delete file: ${e.message}',
        statusCode: e.response?.statusCode,
      );
    }
  }
}

/// Exception for insufficient points
class InsufficientPointsException implements Exception {
  final String message;
  InsufficientPointsException(this.message);

  @override
  String toString() => 'InsufficientPointsException: $message';
}

/// Exception for PDF service errors
class PdfServiceException implements Exception {
  final String message;
  final int? statusCode;

  PdfServiceException(
    this.message, {
    this.statusCode,
  });

  @override
  String toString() => 'PdfServiceException: $message' +
      (statusCode != null ? ' (HTTP $statusCode)' : '');
}
