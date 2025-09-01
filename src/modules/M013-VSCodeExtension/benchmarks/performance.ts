/**
 * Performance Benchmarks for M013 VS Code Extension
 * 
 * Measures key performance metrics before and after optimization
 */

import * as vscode from 'vscode';
import { performance } from 'perf_hooks';

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

export class PerformanceBenchmark {
    private metrics: PerformanceMetrics = {
        activationTime: 0,
        commandResponseTime: new Map(),
        webviewLoadTime: new Map(),
        memoryUsage: {
            baseline: 0,
            peak: 0,
            afterGC: 0
        },
        cpuUsage: {
            idle: 0,
            active: 0
        },
        cliOperations: {
            syncBlocking: 0,
            asyncNonBlocking: 0,
            streamingLatency: 0
        }
    };
    
    private marks: Map<string, number> = new Map();
    
    /**
     * Starts a performance measurement
     */
    public startMeasure(name: string): void {
        this.marks.set(name, performance.now());
    }
    
    /**
     * Ends a performance measurement and records the duration
     */
    public endMeasure(name: string): number {
        const startTime = this.marks.get(name);
        if (!startTime) {
            console.warn(`No start mark found for ${name}`);
            return 0;
        }
        
        const duration = performance.now() - startTime;
        this.marks.delete(name);
        
        // Categorize the measurement
        if (name === 'activation') {
            this.metrics.activationTime = duration;
        } else if (name.startsWith('command:')) {
            this.metrics.commandResponseTime.set(name.replace('command:', ''), duration);
        } else if (name.startsWith('webview:')) {
            this.metrics.webviewLoadTime.set(name.replace('webview:', ''), duration);
        } else if (name.startsWith('cli:')) {
            const cliOp = name.replace('cli:', '');
            if (cliOp === 'sync') {
                this.metrics.cliOperations.syncBlocking = duration;
            } else if (cliOp === 'async') {
                this.metrics.cliOperations.asyncNonBlocking = duration;
            } else if (cliOp === 'streaming') {
                this.metrics.cliOperations.streamingLatency = duration;
            }
        }
        
        return duration;
    }
    
    /**
     * Measures memory usage
     */
    public measureMemory(): void {
        if (global.gc) {
            // Force garbage collection if available (requires --expose-gc flag)
            global.gc();
        }
        
        const usage = process.memoryUsage();
        const heapUsedMB = usage.heapUsed / 1024 / 1024;
        
        if (this.metrics.memoryUsage.baseline === 0) {
            this.metrics.memoryUsage.baseline = heapUsedMB;
        }
        
        this.metrics.memoryUsage.peak = Math.max(this.metrics.memoryUsage.peak, heapUsedMB);
        this.metrics.memoryUsage.afterGC = heapUsedMB;
    }
    
    /**
     * Measures CPU usage
     */
    public measureCPU(): void {
        const usage = process.cpuUsage();
        const totalMicros = usage.user + usage.system;
        const totalSeconds = totalMicros / 1000000;
        const uptime = process.uptime();
        const percentage = (totalSeconds / uptime) * 100;
        
        // Determine if idle or active based on current activity
        if (this.marks.size === 0) {
            this.metrics.cpuUsage.idle = percentage;
        } else {
            this.metrics.cpuUsage.active = percentage;
        }
    }
    
    /**
     * Runs a complete benchmark suite
     */
    public async runBenchmark(): Promise<PerformanceMetrics> {
        console.log('🚀 Starting Performance Benchmark...');
        
        // Measure baseline memory
        this.measureMemory();
        
        // Simulate activation
        this.startMeasure('activation');
        await this.simulateActivation();
        this.endMeasure('activation');
        
        // Measure commands
        const commands = [
            'devdocai.generateDocumentation',
            'devdocai.analyzeQuality',
            'devdocai.runSecurityScan'
        ];
        
        for (const command of commands) {
            this.startMeasure(`command:${command}`);
            await this.simulateCommand(command);
            this.endMeasure(`command:${command}`);
        }
        
        // Measure webview loading
        const webviews = ['dashboard', 'generator', 'settings'];
        
        for (const webview of webviews) {
            this.startMeasure(`webview:${webview}`);
            await this.simulateWebviewLoad(webview);
            this.endMeasure(`webview:${webview}`);
        }
        
        // Measure CLI operations
        this.startMeasure('cli:sync');
        await this.simulateSyncCLI();
        this.endMeasure('cli:sync');
        
        this.startMeasure('cli:async');
        await this.simulateAsyncCLI();
        this.endMeasure('cli:async');
        
        this.startMeasure('cli:streaming');
        await this.simulateStreamingCLI();
        this.endMeasure('cli:streaming');
        
        // Final measurements
        this.measureMemory();
        this.measureCPU();
        
        return this.metrics;
    }
    
    /**
     * Generates a performance report
     */
    public generateReport(): string {
        const report = [
            '📊 Performance Benchmark Report',
            '================================',
            '',
            '⏱️ Activation Time:',
            `   Current: ${this.metrics.activationTime.toFixed(2)}ms`,
            `   Target:  <100ms`,
            `   Status:  ${this.metrics.activationTime < 100 ? '✅ PASS' : '❌ FAIL'}`,
            '',
            '🎯 Command Response Times:',
            ...Array.from(this.metrics.commandResponseTime.entries()).map(([cmd, time]) => 
                `   ${cmd}: ${time.toFixed(2)}ms (Target: <50ms) ${time < 50 ? '✅' : '❌'}`
            ),
            '',
            '🖼️ Webview Load Times:',
            ...Array.from(this.metrics.webviewLoadTime.entries()).map(([view, time]) => 
                `   ${view}: ${time.toFixed(2)}ms (Target: <200ms) ${time < 200 ? '✅' : '❌'}`
            ),
            '',
            '💾 Memory Usage:',
            `   Baseline: ${this.metrics.memoryUsage.baseline.toFixed(2)}MB`,
            `   Peak:     ${this.metrics.memoryUsage.peak.toFixed(2)}MB`,
            `   After GC: ${this.metrics.memoryUsage.afterGC.toFixed(2)}MB`,
            `   Target:   <30MB baseline`,
            `   Status:   ${this.metrics.memoryUsage.baseline < 30 ? '✅ PASS' : '❌ FAIL'}`,
            '',
            '🖥️ CPU Usage:',
            `   Idle:   ${this.metrics.cpuUsage.idle.toFixed(2)}%`,
            `   Active: ${this.metrics.cpuUsage.active.toFixed(2)}%`,
            `   Target: <2% idle`,
            `   Status: ${this.metrics.cpuUsage.idle < 2 ? '✅ PASS' : '❌ FAIL'}`,
            '',
            '🔄 CLI Operations:',
            `   Sync Blocking:      ${this.metrics.cliOperations.syncBlocking.toFixed(2)}ms`,
            `   Async Non-blocking: ${this.metrics.cliOperations.asyncNonBlocking.toFixed(2)}ms`,
            `   Streaming Latency:  ${this.metrics.cliOperations.streamingLatency.toFixed(2)}ms`,
            '',
            '📈 Performance Improvements:',
            `   Activation:    ${this.calculateImprovement(200, this.metrics.activationTime)}%`,
            `   Command Resp:  ${this.calculateAverageImprovement(100, this.metrics.commandResponseTime)}%`,
            `   Webview Load:  ${this.calculateAverageImprovement(500, this.metrics.webviewLoadTime)}%`,
            `   Memory:        ${this.calculateImprovement(50, this.metrics.memoryUsage.baseline)}%`,
            `   CPU Idle:      ${this.calculateImprovement(5, this.metrics.cpuUsage.idle)}%`,
            '',
            '================================'
        ];
        
        return report.join('\n');
    }
    
    // Simulation methods for testing
    private async simulateActivation(): Promise<void> {
        await new Promise(resolve => setTimeout(resolve, 200));
    }
    
    private async simulateCommand(command: string): Promise<void> {
        await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    private async simulateWebviewLoad(webview: string): Promise<void> {
        await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    private async simulateSyncCLI(): Promise<void> {
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    private async simulateAsyncCLI(): Promise<void> {
        await new Promise(resolve => setTimeout(resolve, 50));
    }
    
    private async simulateStreamingCLI(): Promise<void> {
        await new Promise(resolve => setTimeout(resolve, 10));
    }
    
    private calculateImprovement(baseline: number, current: number): string {
        const improvement = ((baseline - current) / baseline * 100);
        return improvement.toFixed(1);
    }
    
    private calculateAverageImprovement(baseline: number, times: Map<string, number>): string {
        if (times.size === 0) return '0.0';
        const avg = Array.from(times.values()).reduce((a, b) => a + b, 0) / times.size;
        return this.calculateImprovement(baseline, avg);
    }
}

// Export function to run benchmark from command
export async function runPerformanceBenchmark(): Promise<void> {
    const benchmark = new PerformanceBenchmark();
    const metrics = await benchmark.runBenchmark();
    const report = benchmark.generateReport();
    
    console.log(report);
    
    // Show in VS Code output channel
    const outputChannel = vscode.window.createOutputChannel('DevDocAI Performance');
    outputChannel.appendLine(report);
    outputChannel.show();
    
    // Save to file for comparison
    const fs = require('fs');
    const path = require('path');
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const benchmarkDir = path.join(__dirname, '..', 'benchmarks', 'results');
    
    if (!fs.existsSync(benchmarkDir)) {
        fs.mkdirSync(benchmarkDir, { recursive: true });
    }
    
    const filename = path.join(benchmarkDir, `benchmark-${timestamp}.json`);
    fs.writeFileSync(filename, JSON.stringify(metrics, null, 2));
    
    vscode.window.showInformationMessage(`Performance benchmark saved to ${filename}`);
}