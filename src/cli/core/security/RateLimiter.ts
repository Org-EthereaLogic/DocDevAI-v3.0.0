/**
 * @fileoverview Rate limiting service for DDoS protection
 * @module @cli/core/security/RateLimiter
 * @version 1.0.0
 * @security Token bucket algorithm with sliding window for rate limiting
 */

import { EventEmitter } from 'events';
import { createHash } from 'crypto';

/**
 * Rate limit configuration
 */
export interface RateLimitConfig {
  windowMs?: number;          // Time window in milliseconds
  maxRequests?: number;        // Maximum requests per window
  skipSuccessfulRequests?: boolean;  // Skip counting successful requests
  skipFailedRequests?: boolean;      // Skip counting failed requests
  keyGenerator?: (source: string) => string;  // Custom key generator
  handler?: (source: string) => void;         // Custom handler when limit exceeded
  enableSlidingWindow?: boolean;              // Use sliding window algorithm
  enableTokenBucket?: boolean;                // Use token bucket algorithm
  bucketCapacity?: number;                    // Token bucket capacity
  refillRate?: number;                        // Tokens per second
}

/**
 * Rate limit entry
 */
interface RateLimitEntry {
  count: number;
  firstRequest: number;
  lastRequest: number;
  tokens?: number;
  lastRefill?: number;
  violations: number;
  blocked: boolean;
}

/**
 * Rate limit result
 */
export interface RateLimitResult {
  allowed: boolean;
  limit: number;
  remaining: number;
  resetTime: number;
  retryAfter?: number;
}

/**
 * Rate limiter service for DDoS protection
 * Implements multiple algorithms for flexible rate limiting
 */
export class RateLimiter extends EventEmitter {
  private readonly defaultConfig: Required<RateLimitConfig> = {
    windowMs: 60000,           // 1 minute
    maxRequests: 100,          // 100 requests per minute
    skipSuccessfulRequests: false,
    skipFailedRequests: false,
    keyGenerator: (source: string) => source,
    handler: () => {},
    enableSlidingWindow: false,
    enableTokenBucket: true,
    bucketCapacity: 100,
    refillRate: 2              // 2 tokens per second
  };

  // Different rate limits for different operations
  private readonly limits: Map<string, Required<RateLimitConfig>> = new Map([
    ['config_load', {
      ...this.defaultConfig,
      windowMs: 60000,
      maxRequests: 10,        // 10 config loads per minute
      bucketCapacity: 10,
      refillRate: 0.5
    }],
    ['error_generation', {
      ...this.defaultConfig,
      windowMs: 60000,
      maxRequests: 50,        // 50 errors per minute
      bucketCapacity: 50,
      refillRate: 1
    }],
    ['memory_detection', {
      ...this.defaultConfig,
      windowMs: 1000,
      maxRequests: 10,        // 10 detections per second
      bucketCapacity: 10,
      refillRate: 10
    }],
    ['logging', {
      ...this.defaultConfig,
      windowMs: 1000,
      maxRequests: 1000,      // 1000 logs per second
      bucketCapacity: 1000,
      refillRate: 1000
    }],
    ['api_call', {
      ...this.defaultConfig,
      windowMs: 60000,
      maxRequests: 60,        // 60 API calls per minute
      bucketCapacity: 60,
      refillRate: 1
    }]
  ]);

  // Storage for rate limit tracking
  private readonly storage: Map<string, RateLimitEntry> = new Map();
  
  // Blacklist for repeated violators
  private readonly blacklist: Set<string> = new Set();
  
  // Cleanup interval
  private cleanupInterval?: NodeJS.Timeout;

  constructor() {
    super();
    
    // Start cleanup interval
    this.cleanupInterval = setInterval(() => this.cleanup(), 60000);
  }

  /**
   * Checks if config load is allowed
   */
  public checkConfigLoadLimit(source: string): boolean {
    return this.checkLimit('config_load', source);
  }

  /**
   * Checks if error generation is allowed
   */
  public checkErrorGenerationLimit(type: string): boolean {
    return this.checkLimit('error_generation', type);
  }

  /**
   * Checks if memory detection is allowed
   */
  public checkMemoryDetectionLimit(): boolean {
    return this.checkLimit('memory_detection', 'system');
  }

  /**
   * Checks if logging is allowed
   */
  public checkLoggingRate(level: string): boolean {
    // Allow critical logs always
    if (level === 'error' || level === 'critical') {
      return true;
    }
    return this.checkLimit('logging', level);
  }

  /**
   * Generic rate limit check
   */
  public checkLimit(operation: string, source: string): boolean {
    const config = this.limits.get(operation) || this.defaultConfig;
    const key = this.generateKey(operation, source, config);
    
    // Check blacklist
    if (this.blacklist.has(key)) {
      this.emit('blocked', { operation, source, reason: 'blacklisted' });
      return false;
    }

    const now = Date.now();
    let entry = this.storage.get(key);

    if (!entry) {
      entry = this.createEntry(now, config);
      this.storage.set(key, entry);
      return true;
    }

    // Check if entry is blocked
    if (entry.blocked) {
      const blockExpiry = entry.lastRequest + (config.windowMs * 2);
      if (now < blockExpiry) {
        this.emit('blocked', { operation, source, reason: 'temporary_block' });
        return false;
      }
      entry.blocked = false;
    }

    let allowed = false;

    if (config.enableTokenBucket) {
      allowed = this.checkTokenBucket(entry, now, config);
    } else if (config.enableSlidingWindow) {
      allowed = this.checkSlidingWindow(entry, now, config);
    } else {
      allowed = this.checkFixedWindow(entry, now, config);
    }

    if (!allowed) {
      entry.violations++;
      
      // Block after 3 violations
      if (entry.violations >= 3) {
        entry.blocked = true;
        this.emit('rate_limit_exceeded', {
          operation,
          source,
          violations: entry.violations,
          blocked: true
        });
        
        // Add to blacklist after 10 violations
        if (entry.violations >= 10) {
          this.blacklist.add(key);
          this.emit('blacklisted', { operation, source });
        }
      } else {
        this.emit('rate_limit_exceeded', {
          operation,
          source,
          violations: entry.violations,
          blocked: false
        });
      }
      
      config.handler(source);
    } else {
      // Reset violations on successful request
      if (entry.violations > 0) {
        entry.violations = Math.max(0, entry.violations - 1);
      }
    }

    entry.lastRequest = now;
    return allowed;
  }

  /**
   * Get rate limit status
   */
  public getStatus(operation: string, source: string): RateLimitResult {
    const config = this.limits.get(operation) || this.defaultConfig;
    const key = this.generateKey(operation, source, config);
    const entry = this.storage.get(key);
    const now = Date.now();

    if (!entry) {
      return {
        allowed: true,
        limit: config.maxRequests,
        remaining: config.maxRequests,
        resetTime: now + config.windowMs
      };
    }

    let remaining = 0;
    let resetTime = 0;

    if (config.enableTokenBucket) {
      const refilled = this.refillTokens(entry, now, config);
      remaining = Math.floor(refilled.tokens || 0);
      resetTime = now + (1000 / config.refillRate);
    } else {
      const windowStart = now - config.windowMs;
      if (entry.firstRequest < windowStart) {
        remaining = config.maxRequests;
        resetTime = now + config.windowMs;
      } else {
        remaining = Math.max(0, config.maxRequests - entry.count);
        resetTime = entry.firstRequest + config.windowMs;
      }
    }

    return {
      allowed: remaining > 0 && !entry.blocked,
      limit: config.maxRequests,
      remaining,
      resetTime,
      retryAfter: entry.blocked ? (entry.lastRequest + config.windowMs * 2 - now) : undefined
    };
  }

  /**
   * Checks fixed window algorithm
   */
  private checkFixedWindow(
    entry: RateLimitEntry,
    now: number,
    config: Required<RateLimitConfig>
  ): boolean {
    const windowStart = now - config.windowMs;
    
    if (entry.firstRequest < windowStart) {
      // Reset window
      entry.count = 1;
      entry.firstRequest = now;
      return true;
    }

    if (entry.count >= config.maxRequests) {
      return false;
    }

    entry.count++;
    return true;
  }

  /**
   * Checks sliding window algorithm
   */
  private checkSlidingWindow(
    entry: RateLimitEntry,
    now: number,
    config: Required<RateLimitConfig>
  ): boolean {
    const windowStart = now - config.windowMs;
    const windowProgress = (now - entry.firstRequest) / config.windowMs;
    
    if (entry.firstRequest < windowStart) {
      // Full window has passed
      entry.count = 1;
      entry.firstRequest = now;
      return true;
    }

    // Calculate weighted count
    const weightedCount = entry.count * (1 - windowProgress);
    
    if (weightedCount >= config.maxRequests) {
      return false;
    }

    entry.count++;
    return true;
  }

  /**
   * Checks token bucket algorithm
   */
  private checkTokenBucket(
    entry: RateLimitEntry,
    now: number,
    config: Required<RateLimitConfig>
  ): boolean {
    // Refill tokens
    const refilled = this.refillTokens(entry, now, config);
    entry.tokens = refilled.tokens;
    entry.lastRefill = refilled.lastRefill;

    if ((entry.tokens || 0) < 1) {
      return false;
    }

    entry.tokens = (entry.tokens || 0) - 1;
    entry.count++;
    return true;
  }

  /**
   * Refills tokens in bucket
   */
  private refillTokens(
    entry: RateLimitEntry,
    now: number,
    config: Required<RateLimitConfig>
  ): { tokens: number; lastRefill: number } {
    const lastRefill = entry.lastRefill || entry.firstRequest;
    const timePassed = (now - lastRefill) / 1000; // Convert to seconds
    const tokensToAdd = timePassed * config.refillRate;
    
    const tokens = Math.min(
      config.bucketCapacity,
      (entry.tokens || config.bucketCapacity) + tokensToAdd
    );

    return { tokens, lastRefill: now };
  }

  /**
   * Creates a new rate limit entry
   */
  private createEntry(now: number, config: Required<RateLimitConfig>): RateLimitEntry {
    return {
      count: 1,
      firstRequest: now,
      lastRequest: now,
      tokens: config.enableTokenBucket ? config.bucketCapacity - 1 : undefined,
      lastRefill: config.enableTokenBucket ? now : undefined,
      violations: 0,
      blocked: false
    };
  }

  /**
   * Generates a key for storage
   */
  private generateKey(
    operation: string,
    source: string,
    config: Required<RateLimitConfig>
  ): string {
    const customKey = config.keyGenerator(source);
    return createHash('md5')
      .update(`${operation}:${customKey}`)
      .digest('hex');
  }

  /**
   * Cleans up old entries
   */
  private cleanup(): void {
    const now = Date.now();
    const maxAge = 3600000; // 1 hour

    for (const [key, entry] of this.storage.entries()) {
      if (now - entry.lastRequest > maxAge) {
        this.storage.delete(key);
      }
    }

    // Clear blacklist entries older than 24 hours
    // Note: In production, blacklist should persist
    if (this.blacklist.size > 1000) {
      this.blacklist.clear();
    }
  }

  /**
   * Resets rate limit for a source
   */
  public reset(operation: string, source: string): void {
    const config = this.limits.get(operation) || this.defaultConfig;
    const key = this.generateKey(operation, source, config);
    this.storage.delete(key);
    this.blacklist.delete(key);
  }

  /**
   * Resets all rate limits
   */
  public resetAll(): void {
    this.storage.clear();
    this.blacklist.clear();
  }

  /**
   * Updates rate limit configuration
   */
  public updateConfig(operation: string, config: RateLimitConfig): void {
    const existing = this.limits.get(operation) || this.defaultConfig;
    this.limits.set(operation, { ...existing, ...config });
  }

  /**
   * Gets current statistics
   */
  public getStatistics(): {
    entries: number;
    blacklisted: number;
    violations: number;
    blocked: number;
  } {
    let violations = 0;
    let blocked = 0;

    for (const entry of this.storage.values()) {
      violations += entry.violations;
      if (entry.blocked) blocked++;
    }

    return {
      entries: this.storage.size,
      blacklisted: this.blacklist.size,
      violations,
      blocked
    };
  }

  /**
   * Closes the rate limiter
   */
  public close(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
    }
    this.removeAllListeners();
  }
}

// Export singleton instance
export const rateLimiter = new RateLimiter();