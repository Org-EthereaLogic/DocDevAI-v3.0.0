/**
 * Logger utility for DevDocAI VS Code Extension
 * 
 * Provides structured logging with different levels
 * and optional debug output channel integration.
 */

import * as vscode from 'vscode';

export class Logger {
    private outputChannel: vscode.OutputChannel;
    private debugMode: boolean;
    
    constructor(name: string) {
        this.outputChannel = vscode.window.createOutputChannel(name);
        this.debugMode = vscode.workspace.getConfiguration('devdocai').get('debug', false);
    }
    
    /**
     * Logs an info message
     */
    public info(message: string, ...args: any[]): void {
        this.log('INFO', message, ...args);
    }
    
    /**
     * Logs a warning message
     */
    public warn(message: string, ...args: any[]): void {
        this.log('WARN', message, ...args);
    }
    
    /**
     * Logs an error message
     */
    public error(message: string, error?: any, ...args: any[]): void {
        this.log('ERROR', message, ...args);
        
        if (error) {
            if (error instanceof Error) {
                this.log('ERROR', `Stack: ${error.stack}`);
            } else {
                this.log('ERROR', `Error details: ${JSON.stringify(error)}`);
            }
        }
    }
    
    /**
     * Logs a debug message (only if debug mode is enabled)
     */
    public debug(message: string, ...args: any[]): void {
        if (this.debugMode) {
            this.log('DEBUG', message, ...args);
        }
    }
    
    /**
     * Core logging function
     */
    private log(level: string, message: string, ...args: any[]): void {
        const timestamp = new Date().toISOString();
        const formattedMessage = `[${timestamp}] [${level}] ${message}`;
        
        // Add additional arguments if provided
        let fullMessage = formattedMessage;
        if (args.length > 0) {
            fullMessage += ' ' + args.map(arg => 
                typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
            ).join(' ');
        }
        
        // Write to output channel
        this.outputChannel.appendLine(fullMessage);
        
        // Also log to console in debug mode
        if (this.debugMode) {
            console.log(fullMessage);
        }
    }
    
    /**
     * Shows the output channel
     */
    public show(): void {
        this.outputChannel.show();
    }
    
    /**
     * Clears the output channel
     */
    public clear(): void {
        this.outputChannel.clear();
    }
    
    /**
     * Disposes the output channel
     */
    public dispose(): void {
        this.outputChannel.dispose();
    }
}