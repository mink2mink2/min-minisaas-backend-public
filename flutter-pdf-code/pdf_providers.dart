/// PDF service providers and state management with Riverpod

import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'pdf_models.dart';
import 'pdf_service.dart';

// PDF Service Provider
final pdfServiceProvider = Provider<PdfService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return PdfService(apiClient: apiClient);
});

/// Note: Assuming apiClientProvider is defined elsewhere in your project.
/// It should provide a configured Dio instance with base URL and auth headers.
/// Example implementation:
/// ```dart
/// final apiClientProvider = Provider<Dio>((ref) {
///   final dio = Dio(BaseOptions(baseUrl: 'https://your-api.com'));
///   // Add interceptors, auth, etc.
///   return dio;
/// });
/// ```

// State Notifier for managing PDF files list
class PdfFilesNotifier extends StateNotifier<AsyncValue<List<PdfFile>>> {
  final PdfService pdfService;

  PdfFilesNotifier(this.pdfService) : super(const AsyncValue.loading());

  Future<void> loadUserFiles({
    int skip = 0,
    int limit = 20,
  }) async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() async {
      return await pdfService.getUserFiles(skip: skip, limit: limit);
    });
  }

  Future<void> refreshFiles() async {
    await loadUserFiles();
  }

  Future<PdfFile> uploadFile(File file) async {
    try {
      final uploadedFile = await pdfService.uploadPdf(file);
      // Refresh the list after upload
      await loadUserFiles();
      return uploadedFile;
    } catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
      rethrow;
    }
  }

  void removeFile(String fileId) {
    state.whenData((files) {
      state = AsyncValue.data(
        files.where((f) => f.fileId != fileId).toList(),
      );
    });
  }
}

// PDF Files provider (list of user's PDFs)
final pdfFilesProvider =
    StateNotifierProvider<PdfFilesNotifier, AsyncValue<List<PdfFile>>>((ref) {
  final pdfService = ref.watch(pdfServiceProvider);
  return PdfFilesNotifier(pdfService)..loadUserFiles();
});

// PDF File details provider (single file)
final pdfFileProvider = FutureProvider.family<PdfFile, String>((ref, fileId) async {
  final pdfService = ref.watch(pdfServiceProvider);
  return pdfService.getFileDetails(fileId);
});

// PDF Conversion status provider
class PdfConversionStatusNotifier
    extends StateNotifier<AsyncValue<PdfConversionStatus>> {
  final PdfService pdfService;
  final String fileId;

  PdfConversionStatusNotifier({
    required this.pdfService,
    required this.fileId,
  }) : super(const AsyncValue.loading());

  Future<void> requestConversion() async {
    try {
      state = const AsyncValue.loading();
      state = await AsyncValue.guard(
        () => pdfService.requestConversion(fileId),
      );
      // Start polling for status updates
      await pollStatus();
    } catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
      rethrow;
    }
  }

  Future<void> checkStatus() async {
    state = await AsyncValue.guard(
      () => pdfService.getStatus(fileId),
    );
  }

  Future<void> pollStatus({
    Duration interval = const Duration(seconds: 2),
    Duration timeout = const Duration(minutes: 10),
  }) async {
    final stopwatch = Stopwatch()..start();

    while (stopwatch.elapsed < timeout) {
      await Future.delayed(interval);
      await checkStatus();

      state.whenData((status) {
        if (status.status == 'processed' || status.status == 'failed') {
          stopwatch.stop();
        }
      });

      if (stopwatch.elapsed >= timeout) {
        break;
      }
    }
  }
}

// Family provider for conversion status (can track multiple files)
final pdfConversionStatusProvider = StateNotifierProvider.family<
    PdfConversionStatusNotifier,
    AsyncValue<PdfConversionStatus>,
    String>((ref, fileId) {
  final pdfService = ref.watch(pdfServiceProvider);
  return PdfConversionStatusNotifier(
    pdfService: pdfService,
    fileId: fileId,
  )..checkStatus();
});

// Simple provider to get current conversion status
final pdfConversionStatusFutureProvider =
    FutureProvider.family<PdfConversionStatus, String>((ref, fileId) async {
  final pdfService = ref.watch(pdfServiceProvider);
  return pdfService.getStatus(fileId);
});

// Provider for monitoring conversion progress
class ConversionProgressNotifier extends StateNotifier<AsyncValue<String>> {
  final PdfService pdfService;
  final String fileId;

  ConversionProgressNotifier({
    required this.pdfService,
    required this.fileId,
  }) : super(const AsyncValue.data('uploading'));

  Future<void> startConversion() async {
    try {
      state = const AsyncValue.data('requesting');
      await pdfService.requestConversion(fileId);

      state = const AsyncValue.data('processing');

      // Poll until complete or failed
      int attempts = 0;
      const maxAttempts = 300; // 10 minutes with 2-second intervals
      const pollInterval = Duration(seconds: 2);

      while (attempts < maxAttempts) {
        await Future.delayed(pollInterval);
        attempts++;

        try {
          final status = await pdfService.getStatus(fileId);

          if (status.status == 'processed') {
            state = const AsyncValue.data('processed');
            break;
          } else if (status.status == 'failed') {
            state = AsyncValue.error(
              'Conversion failed',
              StackTrace.current,
            );
            break;
          }
          // Keep polling
        } catch (e) {
          // Continue polling even if status check fails
          continue;
        }
      }

      if (attempts >= maxAttempts) {
        state = AsyncValue.error(
          'Conversion timeout',
          StackTrace.current,
        );
      }
    } catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
    }
  }
}

final conversionProgressProvider = StateNotifierProvider.family<
    ConversionProgressNotifier,
    AsyncValue<String>,
    String>((ref, fileId) {
  final pdfService = ref.watch(pdfServiceProvider);
  return ConversionProgressNotifier(
    pdfService: pdfService,
    fileId: fileId,
  );
});

// Provider for file download
final pdfDownloadProvider = FutureProvider.family<void, (String, String)>(
  (ref, params) async {
    final (fileId, savePath) = params;
    final pdfService = ref.watch(pdfServiceProvider);
    await pdfService.downloadCsv(fileId, savePath);
  },
);

// Example usage in a widget:
//
// class PdfUploadExample extends ConsumerWidget {
//   @override
//   Widget build(BuildContext context, WidgetRef ref) {
//     final filesAsync = ref.watch(pdfFilesProvider);
//
//     return filesAsync.when(
//       data: (files) => ListView(
//         children: files.map((file) {
//           return ListTile(
//             title: Text(file.originalFilename),
//             subtitle: Text('Status: ${file.status}'),
//             trailing: file.status == 'processed'
//                 ? IconButton(
//                     icon: const Icon(Icons.download),
//                     onPressed: () => _downloadFile(context, ref, file.fileId),
//                   )
//                 : null,
//           );
//         }).toList(),
//       ),
//       loading: () => const Center(child: CircularProgressIndicator()),
//       error: (err, stack) => Center(child: Text('Error: $err')),
//     );
//   }
//
//   Future<void> _downloadFile(
//     BuildContext context,
//     WidgetRef ref,
//     String fileId,
//   ) async {
//     try {
//       final pdfService = ref.read(pdfServiceProvider);
//       final dir = await getApplicationDocumentsDirectory();
//       final savePath = '${dir.path}/$fileId.csv';
//
//       await pdfService.downloadCsv(fileId, savePath);
//       ScaffoldMessenger.of(context).showSnackBar(
//         SnackBar(content: Text('Downloaded to $savePath')),
//       );
//     } catch (e) {
//       ScaffoldMessenger.of(context).showSnackBar(
//         SnackBar(content: Text('Error: $e')),
//       );
//     }
//   }
// }
