import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { useNotificationStore } from './notification';

export const useBatchStore = defineStore('batch', () => {
  // State
  const batches = ref([]);
  const activeBatch = ref(null);
  const isProcessing = ref(false);
  const error = ref(null);
  const queue = ref([]);

  // Batch configuration based on M011 backend
  const config = ref({
    maxConcurrency: 4,       // Based on system memory mode
    batchSize: 50,           // Documents per batch
    retryAttempts: 3,
    retryDelay: 2000,        // 2 seconds
    timeout: 300000,         // 5 minutes per operation
    memoryMode: 'auto',      // 'low', 'medium', 'high', 'auto'
    pauseOnError: false,
    autoCleanup: true
  });

  // Memory mode configurations (aligned with M011)
  const memoryModes = ref({
    low: { maxConcurrency: 1, batchSize: 10 },
    medium: { maxConcurrency: 4, batchSize: 25 },
    high: { maxConcurrency: 8, batchSize: 50 },
    ultra: { maxConcurrency: 16, batchSize: 100 }
  });

  // Operation types
  const operationTypes = ref([
    {
      id: 'generate',
      name: 'Document Generation',
      icon: '📝',
      description: 'Generate multiple documents at once'
    },
    {
      id: 'enhance',
      name: 'AI Enhancement',
      icon: '✨',
      description: 'Enhance documents using MIAIR + LLM'
    },
    {
      id: 'review',
      name: 'Quality Review',
      icon: '🔍',
      description: 'Run quality analysis on documents'
    },
    {
      id: 'export',
      name: 'Export Documents',
      icon: '📤',
      description: 'Export documents in various formats'
    },
    {
      id: 'validate',
      name: 'Validation',
      icon: '✅',
      description: 'Validate document consistency'
    }
  ]);

  // Batch statuses
  const batchStatuses = ref([
    { id: 'pending', name: 'Pending', color: 'gray' },
    { id: 'running', name: 'Running', color: 'blue' },
    { id: 'paused', name: 'Paused', color: 'yellow' },
    { id: 'completed', name: 'Completed', color: 'green' },
    { id: 'failed', name: 'Failed', color: 'red' },
    { id: 'cancelled', name: 'Cancelled', color: 'gray' }
  ]);

  // Real-time processing metrics
  const processingMetrics = ref({
    totalOperations: 0,
    completedOperations: 0,
    failedOperations: 0,
    averageProcessingTime: 0,
    throughput: 0,          // Operations per minute
    estimatedTimeRemaining: 0,
    resourceUsage: {
      cpu: 0,
      memory: 0,
      network: 0
    }
  });

  // Performance statistics
  const performanceStats = ref({
    totalBatches: 0,
    successRate: 0,
    averageBatchTime: 0,
    fastestBatch: null,
    slowestBatch: null,
    peakThroughput: 0,
    errorPatterns: []
  });

  // Computed
  const queueLength = computed(() => queue.value.length);

  const runningBatches = computed(() =>
    batches.value.filter(batch => batch.status === 'running')
  );

  const completedBatches = computed(() =>
    batches.value.filter(batch => batch.status === 'completed')
  );

  const failedBatches = computed(() =>
    batches.value.filter(batch => batch.status === 'failed')
  );

  const batchProgress = computed(() => {
    if (!activeBatch.value) return 0;
    const total = activeBatch.value.operations.length;
    const completed = activeBatch.value.operations.filter(op => op.status === 'completed').length;
    return total > 0 ? Math.round((completed / total) * 100) : 0;
  });

  const currentMemoryMode = computed(() => {
    if (config.value.memoryMode === 'auto') {
      // Auto-detect based on system capabilities
      if (navigator.deviceMemory) {
        if (navigator.deviceMemory <= 2) return 'low';
        if (navigator.deviceMemory <= 4) return 'medium';
        if (navigator.deviceMemory <= 8) return 'high';
        return 'ultra';
      }
      return 'medium'; // Default fallback
    }
    return config.value.memoryMode;
  });

  const effectiveConfig = computed(() => {
    const mode = currentMemoryMode.value;
    const modeConfig = memoryModes.value[mode];
    return {
      ...config.value,
      ...modeConfig
    };
  });

  const canStartNewBatch = computed(() => {
    return !isProcessing.value && runningBatches.value.length < effectiveConfig.value.maxConcurrency;
  });

  const systemLoad = computed(() => {
    const running = runningBatches.value.length;
    const maxConcurrency = effectiveConfig.value.maxConcurrency;
    return maxConcurrency > 0 ? Math.round((running / maxConcurrency) * 100) : 0;
  });

  // Actions
  const createBatch = (operationType, documents, options = {}) => {
    const batchId = `batch_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    const batch = {
      id: batchId,
      operationType,
      status: 'pending',
      documents: documents.map(doc => ({ ...doc })),
      operations: documents.map(doc => ({
        id: `op_${doc.id}_${Date.now()}`,
        documentId: doc.id,
        documentName: doc.name || `Document ${doc.id}`,
        status: 'pending',
        progress: 0,
        startTime: null,
        endTime: null,
        duration: 0,
        result: null,
        error: null,
        retryCount: 0
      })),
      options: {
        priority: options.priority || 'normal',
        retryOnFailure: options.retryOnFailure !== false,
        notifyOnComplete: options.notifyOnComplete !== false,
        ...options
      },
      createdAt: new Date().toISOString(),
      startedAt: null,
      completedAt: null,
      totalDuration: 0,
      progress: 0,
      results: {
        successful: 0,
        failed: 0,
        total: documents.length
      }
    };

    batches.value.unshift(batch);

    // Add to queue if not immediately processed
    if (!canStartNewBatch.value) {
      queue.value.push(batchId);
    }

    return batchId;
  };

  const startBatch = async (batchId) => {
    const batch = batches.value.find(b => b.id === batchId);
    if (!batch || batch.status !== 'pending') {
      throw new Error('Batch not found or not in pending state');
    }

    if (!canStartNewBatch.value) {
      // Add to queue
      if (!queue.value.includes(batchId)) {
        queue.value.push(batchId);
      }
      return false;
    }

    batch.status = 'running';
    batch.startedAt = new Date().toISOString();
    activeBatch.value = batch;
    isProcessing.value = true;

    const notificationStore = useNotificationStore();
    const progressNotification = notificationStore.addProgressNotification(
      `Batch ${batch.operationType}`,
      `Starting batch with ${batch.operations.length} operations...`
    );

    try {
      // Process operations with controlled concurrency
      await processOperationsWithConcurrency(batch, progressNotification);

      batch.status = 'completed';
      batch.completedAt = new Date().toISOString();
      batch.totalDuration = new Date(batch.completedAt) - new Date(batch.startedAt);

      updatePerformanceStats(batch);

      progressNotification.complete(
        `Batch completed: ${batch.results.successful}/${batch.results.total} operations successful`
      );

      if (batch.options.notifyOnComplete) {
        notificationStore.addSuccess(
          'Batch Completed',
          `${batch.operationType} batch completed successfully`
        );
      }

    } catch (err) {
      batch.status = 'failed';
      batch.error = err.message;
      batch.completedAt = new Date().toISOString();

      progressNotification.error(`Batch failed: ${err.message}`);

      notificationStore.addError(
        'Batch Failed',
        `${batch.operationType} batch failed: ${err.message}`
      );

      throw err;
    } finally {
      isProcessing.value = false;
      activeBatch.value = null;

      // Process next batch in queue
      processQueue();
    }

    return true;
  };

  const processOperationsWithConcurrency = async (batch, progressNotification) => {
    const operations = batch.operations;
    const concurrency = effectiveConfig.value.maxConcurrency;
    let completed = 0;
    let failed = 0;

    // Create chunks for processing
    const chunks = [];
    for (let i = 0; i < operations.length; i += concurrency) {
      chunks.push(operations.slice(i, i + concurrency));
    }

    for (const chunk of chunks) {
      // Process operations in this chunk concurrently
      const promises = chunk.map(operation => processOperation(batch, operation));

      try {
        const results = await Promise.allSettled(promises);

        results.forEach((result, index) => {
          const operation = chunk[index];

          if (result.status === 'fulfilled') {
            operation.status = 'completed';
            operation.result = result.value;
            completed++;
          } else {
            operation.status = 'failed';
            operation.error = result.reason.message || 'Operation failed';
            failed++;
          }

          operation.endTime = new Date().toISOString();
          operation.duration = new Date(operation.endTime) - new Date(operation.startTime);
        });

        // Update batch progress
        batch.results.successful = completed;
        batch.results.failed = failed;
        batch.progress = Math.round(((completed + failed) / operations.length) * 100);

        // Update progress notification
        progressNotification.update(
          batch.progress,
          `Processed ${completed + failed}/${operations.length} operations...`
        );

        // Update processing metrics
        updateProcessingMetrics(batch);

      } catch (err) {
        console.error('Error processing chunk:', err);
        // Individual operation errors are handled above
      }

      // Small delay between chunks to prevent overwhelming the system
      if (chunks.indexOf(chunk) < chunks.length - 1) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    }
  };

  const processOperation = async (batch, operation) => {
    operation.status = 'running';
    operation.startTime = new Date().toISOString();
    operation.progress = 0;

    const maxRetries = config.value.retryAttempts;
    let lastError;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      if (attempt > 0) {
        operation.retryCount = attempt;
        // Exponential backoff
        await new Promise(resolve =>
          setTimeout(resolve, config.value.retryDelay * Math.pow(2, attempt - 1))
        );
      }

      try {
        let result;

        // Simulate different operation types
        switch (batch.operationType) {
          case 'generate':
            result = await simulateDocumentGeneration(operation);
            break;
          case 'enhance':
            result = await simulateDocumentEnhancement(operation);
            break;
          case 'review':
            result = await simulateDocumentReview(operation);
            break;
          case 'export':
            result = await simulateDocumentExport(operation);
            break;
          case 'validate':
            result = await simulateDocumentValidation(operation);
            break;
          default:
            throw new Error(`Unknown operation type: ${batch.operationType}`);
        }

        operation.progress = 100;
        return result;

      } catch (err) {
        lastError = err;
        console.error(`Operation ${operation.id} attempt ${attempt + 1} failed:`, err);

        if (attempt === maxRetries) {
          throw lastError;
        }
      }
    }
  };

  // Simulation functions (replace with actual API calls)
  const simulateDocumentGeneration = async (operation) => {
    // Simulate variable processing time
    const processingTime = 1000 + Math.random() * 3000;
    await new Promise(resolve => setTimeout(resolve, processingTime));

    // Simulate occasional failures
    if (Math.random() < 0.05) { // 5% failure rate
      throw new Error('Generation failed due to API rate limit');
    }

    return {
      documentId: operation.documentId,
      generated: true,
      wordCount: Math.floor(Math.random() * 2000) + 500,
      processingTime
    };
  };

  const simulateDocumentEnhancement = async (operation) => {
    const processingTime = 1500 + Math.random() * 2500;
    await new Promise(resolve => setTimeout(resolve, processingTime));

    if (Math.random() < 0.03) {
      throw new Error('Enhancement failed due to content complexity');
    }

    return {
      documentId: operation.documentId,
      enhanced: true,
      improvementScore: Math.floor(Math.random() * 30) + 10,
      processingTime
    };
  };

  const simulateDocumentReview = async (operation) => {
    const processingTime = 800 + Math.random() * 1200;
    await new Promise(resolve => setTimeout(resolve, processingTime));

    return {
      documentId: operation.documentId,
      reviewed: true,
      qualityScore: Math.floor(Math.random() * 40) + 60,
      issues: Math.floor(Math.random() * 5),
      processingTime
    };
  };

  const simulateDocumentExport = async (operation) => {
    const processingTime = 500 + Math.random() * 1000;
    await new Promise(resolve => setTimeout(resolve, processingTime));

    return {
      documentId: operation.documentId,
      exported: true,
      format: 'pdf',
      fileSize: Math.floor(Math.random() * 1000000) + 100000,
      processingTime
    };
  };

  const simulateDocumentValidation = async (operation) => {
    const processingTime = 300 + Math.random() * 700;
    await new Promise(resolve => setTimeout(resolve, processingTime));

    return {
      documentId: operation.documentId,
      validated: true,
      isValid: Math.random() > 0.1, // 90% validity rate
      errors: Math.floor(Math.random() * 3),
      processingTime
    };
  };

  const pauseBatch = (batchId) => {
    const batch = batches.value.find(b => b.id === batchId);
    if (batch && batch.status === 'running') {
      batch.status = 'paused';
      return true;
    }
    return false;
  };

  const resumeBatch = async (batchId) => {
    const batch = batches.value.find(b => b.id === batchId);
    if (batch && batch.status === 'paused') {
      batch.status = 'running';
      return await startBatch(batchId);
    }
    return false;
  };

  const cancelBatch = (batchId) => {
    const batch = batches.value.find(b => b.id === batchId);
    if (batch && ['pending', 'running', 'paused'].includes(batch.status)) {
      batch.status = 'cancelled';
      batch.completedAt = new Date().toISOString();

      // Remove from queue if pending
      queue.value = queue.value.filter(id => id !== batchId);

      return true;
    }
    return false;
  };

  const processQueue = async () => {
    if (queue.value.length > 0 && canStartNewBatch.value) {
      const nextBatchId = queue.value.shift();
      await startBatch(nextBatchId);
    }
  };

  const updateProcessingMetrics = (batch) => {
    const completed = batch.results.successful + batch.results.failed;
    const total = batch.results.total;

    processingMetrics.value.totalOperations = total;
    processingMetrics.value.completedOperations = completed;
    processingMetrics.value.failedOperations = batch.results.failed;

    if (batch.startedAt) {
      const elapsed = (Date.now() - new Date(batch.startedAt)) / 1000; // seconds
      processingMetrics.value.throughput = completed > 0 ? (completed / elapsed) * 60 : 0; // per minute

      if (completed > 0) {
        const avgTime = elapsed / completed;
        processingMetrics.value.averageProcessingTime = avgTime;

        const remaining = total - completed;
        processingMetrics.value.estimatedTimeRemaining = remaining * avgTime;
      }
    }
  };

  const updatePerformanceStats = (batch) => {
    performanceStats.value.totalBatches++;

    const successRate = (batch.results.successful / batch.results.total) * 100;
    performanceStats.value.successRate =
      (performanceStats.value.successRate + successRate) / 2;

    const batchTime = batch.totalDuration / 1000; // seconds
    performanceStats.value.averageBatchTime =
      (performanceStats.value.averageBatchTime + batchTime) / 2;

    if (!performanceStats.value.fastestBatch ||
        batchTime < performanceStats.value.fastestBatch.time) {
      performanceStats.value.fastestBatch = { id: batch.id, time: batchTime };
    }

    if (!performanceStats.value.slowestBatch ||
        batchTime > performanceStats.value.slowestBatch.time) {
      performanceStats.value.slowestBatch = { id: batch.id, time: batchTime };
    }

    if (processingMetrics.value.throughput > performanceStats.value.peakThroughput) {
      performanceStats.value.peakThroughput = processingMetrics.value.throughput;
    }
  };

  const updateConfiguration = (newConfig) => {
    config.value = { ...config.value, ...newConfig };
  };

  const getBatchDetails = (batchId) => {
    return batches.value.find(b => b.id === batchId);
  };

  const deleteBatch = (batchId) => {
    batches.value = batches.value.filter(b => b.id !== batchId);
    queue.value = queue.value.filter(id => id !== batchId);
  };

  const clearCompletedBatches = () => {
    batches.value = batches.value.filter(b =>
      !['completed', 'failed', 'cancelled'].includes(b.status)
    );
  };

  const exportBatchResults = (batchId) => {
    const batch = batches.value.find(b => b.id === batchId);
    if (!batch) return;

    const exportData = {
      batch: {
        id: batch.id,
        operationType: batch.operationType,
        status: batch.status,
        createdAt: batch.createdAt,
        startedAt: batch.startedAt,
        completedAt: batch.completedAt,
        totalDuration: batch.totalDuration,
        results: batch.results
      },
      operations: batch.operations,
      exportDate: new Date().toISOString()
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json'
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `batch-${batchId}-results.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const clearError = () => {
    error.value = null;
  };

  // Reset store
  const $reset = () => {
    batches.value = [];
    activeBatch.value = null;
    isProcessing.value = false;
    error.value = null;
    queue.value = [];
    processingMetrics.value = {
      totalOperations: 0,
      completedOperations: 0,
      failedOperations: 0,
      averageProcessingTime: 0,
      throughput: 0,
      estimatedTimeRemaining: 0,
      resourceUsage: { cpu: 0, memory: 0, network: 0 }
    };
    performanceStats.value = {
      totalBatches: 0,
      successRate: 0,
      averageBatchTime: 0,
      fastestBatch: null,
      slowestBatch: null,
      peakThroughput: 0,
      errorPatterns: []
    };
  };

  return {
    // State
    batches,
    activeBatch,
    isProcessing,
    error,
    queue,
    config,
    memoryModes,
    operationTypes,
    batchStatuses,
    processingMetrics,
    performanceStats,

    // Computed
    queueLength,
    runningBatches,
    completedBatches,
    failedBatches,
    batchProgress,
    currentMemoryMode,
    effectiveConfig,
    canStartNewBatch,
    systemLoad,

    // Actions
    createBatch,
    startBatch,
    pauseBatch,
    resumeBatch,
    cancelBatch,
    processQueue,
    updateConfiguration,
    getBatchDetails,
    deleteBatch,
    clearCompletedBatches,
    exportBatchResults,
    clearError,
    $reset
  };
}, {
  persist: {
    enabled: true,
    strategies: [
      {
        key: 'batch',
        storage: localStorage,
        paths: [
          'config',
          'performanceStats'
        ]
      }
    ]
  }
});