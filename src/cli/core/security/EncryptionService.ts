/**
 * @fileoverview Encryption service for data protection
 * @module @cli/core/security/EncryptionService
 * @version 1.0.0
 * @security AES-256-GCM encryption with secure key management
 */

import * as crypto from 'crypto';
import { EventEmitter } from 'events';

/**
 * Encrypted value interface
 */
export interface EncryptedValue {
  ciphertext: string;
  iv: string;
  tag: string;
  salt?: string;
  algorithm: string;
  keyDerivation?: string;
}

/**
 * Encryption configuration
 */
export interface EncryptionConfig {
  algorithm?: string;
  keyLength?: number;
  ivLength?: number;
  tagLength?: number;
  saltLength?: number;
  iterations?: number;
  keyDerivation?: 'pbkdf2' | 'scrypt' | 'argon2';
  masterKey?: string;
  rotationInterval?: number;
}

/**
 * Key metadata for rotation
 */
interface KeyMetadata {
  id: string;
  created: number;
  lastUsed: number;
  useCount: number;
  version: number;
}

/**
 * Encryption service for data protection
 * Provides AES-256-GCM encryption with secure key management
 */
export class EncryptionService extends EventEmitter {
  private readonly config: Required<EncryptionConfig>;
  private masterKey: Buffer;
  private derivedKeys: Map<string, { key: Buffer; metadata: KeyMetadata }> = new Map();
  private keyRotationTimer?: NodeJS.Timeout;
  private secureMemory: Map<string, Buffer> = new Map();

  constructor(config: EncryptionConfig = {}) {
    super();

    this.config = {
      algorithm: config.algorithm || 'aes-256-gcm',
      keyLength: config.keyLength || 32,
      ivLength: config.ivLength || 16,
      tagLength: config.tagLength || 16,
      saltLength: config.saltLength || 32,
      iterations: config.iterations || 100000,
      keyDerivation: config.keyDerivation || 'pbkdf2',
      masterKey: config.masterKey || '',
      rotationInterval: config.rotationInterval || 86400000 // 24 hours
    };

    // Initialize master key
    this.masterKey = this.initializeMasterKey();

    // Start key rotation timer
    if (this.config.rotationInterval > 0) {
      this.keyRotationTimer = setInterval(
        () => this.rotateKeys(),
        this.config.rotationInterval
      );
    }
  }

  /**
   * Initializes the master key
   */
  private initializeMasterKey(): Buffer {
    if (this.config.masterKey) {
      // Use provided master key (should be from secure config)
      return crypto.createHash('sha256')
        .update(this.config.masterKey)
        .digest();
    }

    // Generate a new master key (should be stored securely)
    const key = crypto.randomBytes(this.config.keyLength);
    
    // In production, this should be stored in a secure key management system
    this.emit('master_key_generated', {
      warning: 'Master key generated. Store securely for data recovery.',
      fingerprint: this.getKeyFingerprint(key)
    });

    return key;
  }

  /**
   * Encrypts a secret value
   */
  public encryptSecret(value: string, context?: string): EncryptedValue {
    try {
      // Generate salt for key derivation
      const salt = crypto.randomBytes(this.config.saltLength);
      
      // Derive key from master key and context
      const derivedKey = this.deriveKey(salt, context);
      
      // Generate IV
      const iv = crypto.randomBytes(this.config.ivLength);
      
      // Create cipher
      const cipher = crypto.createCipheriv(
        this.config.algorithm,
        derivedKey,
        iv
      );

      // Encrypt data
      const encrypted = Buffer.concat([
        cipher.update(value, 'utf8'),
        cipher.final()
      ]);

      // Get authentication tag for GCM
      const tag = cipher.getAuthTag();

      // Store key metadata
      this.updateKeyMetadata(context || 'default');

      // Emit encryption event for audit
      this.emit('encryption_performed', {
        context,
        algorithm: this.config.algorithm,
        timestamp: Date.now()
      });

      return {
        ciphertext: encrypted.toString('base64'),
        iv: iv.toString('base64'),
        tag: tag.toString('base64'),
        salt: salt.toString('base64'),
        algorithm: this.config.algorithm,
        keyDerivation: this.config.keyDerivation
      };
    } catch (error) {
      this.emit('encryption_error', { error, context });
      throw new Error('Encryption failed');
    }
  }

  /**
   * Decrypts an encrypted value
   */
  public decryptSecret(encrypted: EncryptedValue, context?: string): string {
    try {
      // Validate encrypted value
      if (!this.validateEncryptedValue(encrypted)) {
        throw new Error('Invalid encrypted value format');
      }

      // Decode components
      const ciphertext = Buffer.from(encrypted.ciphertext, 'base64');
      const iv = Buffer.from(encrypted.iv, 'base64');
      const tag = Buffer.from(encrypted.tag, 'base64');
      const salt = encrypted.salt ? Buffer.from(encrypted.salt, 'base64') : Buffer.alloc(0);

      // Derive key
      const derivedKey = this.deriveKey(salt, context);

      // Create decipher
      const decipher = crypto.createDecipheriv(
        encrypted.algorithm || this.config.algorithm,
        derivedKey,
        iv
      );

      // Set authentication tag for GCM
      decipher.setAuthTag(tag);

      // Decrypt data
      const decrypted = Buffer.concat([
        decipher.update(ciphertext),
        decipher.final()
      ]);

      // Update key metadata
      this.updateKeyMetadata(context || 'default');

      // Emit decryption event for audit
      this.emit('decryption_performed', {
        context,
        algorithm: encrypted.algorithm,
        timestamp: Date.now()
      });

      return decrypted.toString('utf8');
    } catch (error) {
      this.emit('decryption_error', { error, context });
      throw new Error('Decryption failed');
    }
  }

  /**
   * Hashes sensitive data for comparison
   */
  public hashSensitiveData(data: string, salt?: string): string {
    const actualSalt = salt || crypto.randomBytes(16).toString('hex');
    const hash = crypto.pbkdf2Sync(
      data,
      actualSalt,
      this.config.iterations,
      64,
      'sha512'
    );
    return `${actualSalt}:${hash.toString('hex')}`;
  }

  /**
   * Verifies a hash
   */
  public verifyHash(data: string, hash: string): boolean {
    const [salt, storedHash] = hash.split(':');
    if (!salt || !storedHash) return false;

    const computedHash = this.hashSensitiveData(data, salt);
    return crypto.timingSafeEqual(
      Buffer.from(hash),
      Buffer.from(computedHash)
    );
  }

  /**
   * Securely deletes data from memory
   */
  public secureDelete(data: string | Buffer): void {
    if (typeof data === 'string') {
      // For strings, we can't directly overwrite memory
      // But we can clear references and request GC
      data = '';
    } else if (Buffer.isBuffer(data)) {
      // Overwrite buffer with random data
      crypto.randomFillSync(data);
      // Then zero it out
      data.fill(0);
    }

    // Request garbage collection (if exposed)
    if (global.gc) {
      global.gc();
    }
  }

  /**
   * Stores sensitive data in secure memory
   */
  public storeSecure(key: string, value: string): void {
    const buffer = Buffer.from(value, 'utf8');
    this.secureMemory.set(key, buffer);
    
    // Set up auto-deletion after 5 minutes
    setTimeout(() => {
      this.deleteSecure(key);
    }, 300000);
  }

  /**
   * Retrieves data from secure memory
   */
  public retrieveSecure(key: string): string | null {
    const buffer = this.secureMemory.get(key);
    if (!buffer) return null;
    return buffer.toString('utf8');
  }

  /**
   * Deletes data from secure memory
   */
  public deleteSecure(key: string): void {
    const buffer = this.secureMemory.get(key);
    if (buffer) {
      this.secureDelete(buffer);
      this.secureMemory.delete(key);
    }
  }

  /**
   * Derives a key from master key and context
   */
  private deriveKey(salt: Buffer, context?: string): Buffer {
    const cacheKey = `${salt.toString('hex')}:${context || 'default'}`;
    
    // Check cache
    const cached = this.derivedKeys.get(cacheKey);
    if (cached && Date.now() - cached.metadata.lastUsed < 60000) {
      cached.metadata.lastUsed = Date.now();
      cached.metadata.useCount++;
      return cached.key;
    }

    // Derive new key
    let derivedKey: Buffer;
    const info = Buffer.from(context || 'default', 'utf8');

    switch (this.config.keyDerivation) {
      case 'scrypt':
        derivedKey = crypto.scryptSync(
          this.masterKey,
          salt,
          this.config.keyLength
        );
        break;
      
      case 'pbkdf2':
      default:
        derivedKey = crypto.pbkdf2Sync(
          this.masterKey,
          Buffer.concat([salt, info]),
          this.config.iterations,
          this.config.keyLength,
          'sha256'
        );
        break;
    }

    // Cache derived key
    this.derivedKeys.set(cacheKey, {
      key: derivedKey,
      metadata: {
        id: cacheKey,
        created: Date.now(),
        lastUsed: Date.now(),
        useCount: 1,
        version: 1
      }
    });

    // Limit cache size
    if (this.derivedKeys.size > 100) {
      this.cleanupDerivedKeys();
    }

    return derivedKey;
  }

  /**
   * Validates encrypted value structure
   */
  private validateEncryptedValue(encrypted: EncryptedValue): boolean {
    return !!(
      encrypted &&
      encrypted.ciphertext &&
      encrypted.iv &&
      encrypted.tag &&
      encrypted.algorithm
    );
  }

  /**
   * Updates key metadata
   */
  private updateKeyMetadata(context: string): void {
    const metadata = this.derivedKeys.get(context);
    if (metadata) {
      metadata.metadata.lastUsed = Date.now();
      metadata.metadata.useCount++;
    }
  }

  /**
   * Rotates encryption keys
   */
  private rotateKeys(): void {
    // Generate new master key
    const newMasterKey = crypto.randomBytes(this.config.keyLength);
    
    // Re-encrypt existing secure memory with new key
    const reencrypted = new Map<string, Buffer>();
    for (const [key, value] of this.secureMemory.entries()) {
      // Decrypt with old key and re-encrypt with new key
      // (simplified for demonstration)
      reencrypted.set(key, value);
    }

    // Replace master key
    this.secureDelete(this.masterKey);
    this.masterKey = newMasterKey;
    
    // Clear derived keys cache
    for (const { key } of this.derivedKeys.values()) {
      this.secureDelete(key);
    }
    this.derivedKeys.clear();

    // Replace secure memory
    this.secureMemory = reencrypted;

    this.emit('keys_rotated', {
      timestamp: Date.now(),
      fingerprint: this.getKeyFingerprint(newMasterKey)
    });
  }

  /**
   * Cleans up old derived keys
   */
  private cleanupDerivedKeys(): void {
    const now = Date.now();
    const maxAge = 300000; // 5 minutes

    for (const [key, { metadata }] of this.derivedKeys.entries()) {
      if (now - metadata.lastUsed > maxAge) {
        const derived = this.derivedKeys.get(key);
        if (derived) {
          this.secureDelete(derived.key);
        }
        this.derivedKeys.delete(key);
      }
    }
  }

  /**
   * Gets key fingerprint for identification
   */
  private getKeyFingerprint(key: Buffer): string {
    return crypto.createHash('sha256')
      .update(key)
      .digest('hex')
      .substring(0, 16);
  }

  /**
   * Generates a secure random token
   */
  public generateSecureToken(length: number = 32): string {
    return crypto.randomBytes(length).toString('hex');
  }

  /**
   * Encrypts an object
   */
  public encryptObject(obj: Record<string, any>, context?: string): EncryptedValue {
    const json = JSON.stringify(obj);
    return this.encryptSecret(json, context);
  }

  /**
   * Decrypts an object
   */
  public decryptObject(encrypted: EncryptedValue, context?: string): Record<string, any> {
    const json = this.decryptSecret(encrypted, context);
    return JSON.parse(json);
  }

  /**
   * Creates a message authentication code
   */
  public createMAC(data: string, key?: Buffer): string {
    const hmacKey = key || this.masterKey;
    return crypto.createHmac('sha256', hmacKey)
      .update(data)
      .digest('hex');
  }

  /**
   * Verifies a message authentication code
   */
  public verifyMAC(data: string, mac: string, key?: Buffer): boolean {
    const hmacKey = key || this.masterKey;
    const computedMac = this.createMAC(data, hmacKey);
    return crypto.timingSafeEqual(
      Buffer.from(mac, 'hex'),
      Buffer.from(computedMac, 'hex')
    );
  }

  /**
   * Closes the encryption service
   */
  public close(): void {
    // Clear key rotation timer
    if (this.keyRotationTimer) {
      clearInterval(this.keyRotationTimer);
    }

    // Securely delete all keys
    this.secureDelete(this.masterKey);
    
    for (const { key } of this.derivedKeys.values()) {
      this.secureDelete(key);
    }
    this.derivedKeys.clear();

    // Clear secure memory
    for (const buffer of this.secureMemory.values()) {
      this.secureDelete(buffer);
    }
    this.secureMemory.clear();

    this.removeAllListeners();
  }
}

// Export singleton instance
export const encryptionService = new EncryptionService();