/**
 * Performance Benchmarks for M013 VS Code Extension
 *
 * Measures key performance metrics before and after optimization
 */
export interface PerformanceMetrics {
    activationTime: number;
    commandResponseTime: Map<string, number>;
    webviewLoadTime: Map<string, number>;
    memoryUsage: {
        baseline: number;
        peak: number;
        afterGC: number;
    };
    cpuUsage: {
        idle: number;
        active: number;
    };
    cliOperations: {
        syncBlocking: number;
        asyncNonBlocking: number;
        streamingLatency: number;
    };
}
export declare class PerformanceBenchmark {
    private metrics;
    private marks;
    /**
     * Starts a performance measurement
     */
    startMeasure(name: string): void;
    /**
     * Ends a performance measurement and records the duration
     */
    endMeasure(name: string): number;
    /**
     * Measures memory usage
     */
    measureMemory(): void;
    /**
     * Measures CPU usage
     */
    measureCPU(): void;
    /**
     * Runs a complete benchmark suite
     */
    runBenchmark(): Promise<PerformanceMetrics>;
    /**
     * Generates a performance report
     */
    generateReport(): string;
    private simulateActivation;
    private simulateCommand;
    private simulateWebviewLoad;
    private simulateSyncCLI;
    private simulateAsyncCLI;
    private simulateStreamingCLI;
    private calculateImprovement;
    private calculateAverageImprovement;
}
export declare function runPerformanceBenchmark(): Promise<void>;
//# sourceMappingURL=performance.d.ts.map