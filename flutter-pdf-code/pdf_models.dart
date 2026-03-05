/// PDF file and conversion status models

class PdfFile {
  final String fileId;
  final String originalFilename;
  final int fileSizeBytes;
  final String status;  // uploading/uploaded/processing/processed/failed/deleted
  final int? pageCount;
  final int conversionCost;
  final String? outputPath;
  final DateTime createdAt;
  final DateTime? processedAt;

  PdfFile({
    required this.fileId,
    required this.originalFilename,
    required this.fileSizeBytes,
    required this.status,
    this.pageCount,
    required this.conversionCost,
    this.outputPath,
    required this.createdAt,
    this.processedAt,
  });

  factory PdfFile.fromJson(Map<String, dynamic> json) => PdfFile(
    fileId: json['file_id'] as String,
    originalFilename: json['original_filename'] as String,
    fileSizeBytes: json['file_size_bytes'] as int,
    status: json['status'] as String,
    pageCount: json['page_count'] as int?,
    conversionCost: json['conversion_cost'] as int? ?? 0,
    outputPath: json['output_path'] as String?,
    createdAt: DateTime.parse(json['created_at'] as String),
    processedAt: json['processed_at'] != null
        ? DateTime.parse(json['processed_at'] as String)
        : null,
  );

  Map<String, dynamic> toJson() => {
    'file_id': fileId,
    'original_filename': originalFilename,
    'file_size_bytes': fileSizeBytes,
    'status': status,
    'page_count': pageCount,
    'conversion_cost': conversionCost,
    'output_path': outputPath,
    'created_at': createdAt.toIso8601String(),
    'processed_at': processedAt?.toIso8601String(),
  };

  @override
  String toString() => 'PdfFile(fileId: $fileId, status: $status)';
}

class PdfConversionStatus {
  final String fileId;
  final String status;
  final int conversionCost;
  final String? outputPath;
  final String message;
  final DateTime createdAt;
  final DateTime? processedAt;

  PdfConversionStatus({
    required this.fileId,
    required this.status,
    required this.conversionCost,
    this.outputPath,
    required this.message,
    required this.createdAt,
    this.processedAt,
  });

  factory PdfConversionStatus.fromJson(Map<String, dynamic> json) =>
      PdfConversionStatus(
        fileId: json['file_id'] as String,
        status: json['status'] as String,
        conversionCost: json['conversion_cost'] as int? ?? 0,
        outputPath: json['output_path'] as String?,
        message: json['message'] as String,
        createdAt: DateTime.parse(json['created_at'] as String),
        processedAt: json['processed_at'] != null
            ? DateTime.parse(json['processed_at'] as String)
            : null,
      );

  Map<String, dynamic> toJson() => {
    'file_id': fileId,
    'status': status,
    'conversion_cost': conversionCost,
    'output_path': outputPath,
    'message': message,
    'created_at': createdAt.toIso8601String(),
    'processed_at': processedAt?.toIso8601String(),
  };

  @override
  String toString() => 'PdfConversionStatus(fileId: $fileId, status: $status)';
}
