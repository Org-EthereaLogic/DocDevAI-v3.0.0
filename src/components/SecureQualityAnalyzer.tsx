/**
 * DevDocAI v3.0.0 - Secure Quality Analyzer Component
 * 
 * Production-ready component with enhanced security:
 * - No sensitive data in localStorage
 * - Input sanitization
 * - PII detection
 * - Secure data handling
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Grid,
  LinearProgress,
  Alert,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Paper,
  IconButton,
  Chip,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Rating,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tooltip,
  Snackbar,
} from '@mui/material';
import {
  PlayArrow as AnalyzeIcon,
  Assessment as MetricsIcon,
  TrendingUp as TrendIcon,
  Warning as WarningIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  ExpandMore as ExpandMoreIcon,
  Refresh as RefreshIcon,
  FileDownload as ExportIcon,
  Clear as ClearIcon,
  History as HistoryIcon,
  Save as SaveIcon,
  Delete as DeleteIcon,
  Security as SecurityIcon,
  Lock as LockIcon,
} from '@mui/icons-material';
import * as crypto from 'crypto-js';

// Security utilities
class SecurityUtils {
  // Sanitize file name to prevent XSS and path traversal
  static sanitizeFileName(fileName: string): string {
    // Remove any path components
    const name = fileName.split(/[/\\]/).pop() || 'document.md';
    // Allow only safe characters
    const sanitized = name.replace(/[^a-zA-Z0-9._-]/g, '');
    // Limit length
    const limited = sanitized.substring(0, 100);
    // Ensure has extension
    return limited || 'document.md';
  }

  // Sanitize text content for display
  static sanitizeForDisplay(text: string): string {
    // Basic HTML entity encoding
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Generate content hash for verification
  static generateContentHash(content: string): string {
    return crypto.SHA256(content).toString();
  }

  // Check for potential PII patterns
  static detectPII(content: string): { hasPII: boolean; types: string[] } {
    const patterns = {
      ssn: /\b\d{3}-\d{2}-\d{4}\b/,
      creditCard: /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/,
      email: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/,
      phone: /\b(\+?1?\d{10,14}|\(\d{3}\)\s?\d{3}-\d{4})\b/,
      ipAddress: /\b(?:\d{1,3}\.){3}\d{1,3}\b/,
    };

    const detectedTypes: string[] = [];
    for (const [type, pattern] of Object.entries(patterns)) {
      if (pattern.test(content)) {
        detectedTypes.push(type);
      }
    }

    return {
      hasPII: detectedTypes.length > 0,
      types: detectedTypes,
    };
  }

  // Validate content size
  static validateContentSize(content: string): { valid: boolean; message?: string } {
    const sizeInBytes = new Blob([content]).size;
    const maxSize = 50000; // 50KB

    if (sizeInBytes > maxSize) {
      return {
        valid: false,
        message: `Content exceeds maximum size of ${maxSize} characters`,
      };
    }

    return { valid: true };
  }
}

// Secure storage wrapper - stores only non-sensitive metadata
class SecureStorage {
  private static readonly STORAGE_VERSION = '1.0';
  private static readonly MAX_ITEMS = 10;
  private static readonly EXPIRY_DAYS = 30;

  // Save only non-sensitive analysis metadata
  static saveAnalysisMetadata(analysis: SecureAnalysisMetadata): boolean {
    try {
      const key = 'devdocai_analysis_metadata';
      const existing = this.loadAnalysisHistory();
      
      // Add expiry timestamp
      const withExpiry = {
        ...analysis,
        expiresAt: Date.now() + (this.EXPIRY_DAYS * 24 * 60 * 60 * 1000),
        version: this.STORAGE_VERSION,
      };

      // Limit number of items
      const updated = [withExpiry, ...existing]
        .filter(item => item.expiresAt > Date.now()) // Remove expired
        .slice(0, this.MAX_ITEMS);

      // Check storage quota
      const serialized = JSON.stringify(updated);
      const sizeInBytes = new Blob([serialized]).size;
      if (sizeInBytes > 1024 * 1024) { // 1MB limit for metadata
        console.warn('Storage quota exceeded, removing oldest items');
        updated.pop();
      }

      localStorage.setItem(key, JSON.stringify(updated));
      return true;
    } catch (error) {
      console.error('Failed to save analysis metadata:', error);
      return false;
    }
  }

  // Load analysis history (metadata only)
  static loadAnalysisHistory(): SecureAnalysisMetadata[] {
    try {
      const key = 'devdocai_analysis_metadata';
      const stored = localStorage.getItem(key);
      if (!stored) return [];

      const parsed = JSON.parse(stored);
      // Filter out expired items
      return parsed.filter((item: any) => 
        item.expiresAt > Date.now() && 
        item.version === this.STORAGE_VERSION
      );
    } catch (error) {
      console.error('Failed to load analysis history:', error);
      return [];
    }
  }

  // Clear all stored data
  static clearAll(): void {
    const keys = ['devdocai_analysis_metadata'];
    keys.forEach(key => localStorage.removeItem(key));
  }

  // Get storage size
  static getStorageSize(): number {
    let totalSize = 0;
    for (const key in localStorage) {
      if (key.startsWith('devdocai_')) {
        totalSize += localStorage.getItem(key)?.length || 0;
      }
    }
    return totalSize;
  }
}

// Secure analysis metadata (no sensitive content)
interface SecureAnalysisMetadata {
  id: string;
  fileName: string;
  contentHash: string; // Store hash instead of content
  overallScore: number;
  analysisDate: number; // Timestamp
  scores: QualityScore[];
  documentSize: number; // Size in bytes
  hasPII?: boolean; // PII detection flag
  expiresAt?: number; // Auto-expiry timestamp
  version?: string; // Storage version
}

interface QualityScore {
  dimension: string;
  score: number;
  maxScore: number;
  issues: string[];
  suggestions: string[];
}

interface AnalysisResult extends SecureAnalysisMetadata {
  status: 'analyzing' | 'complete' | 'error';
  documentContent?: string; // Only in memory, never stored
}

const SecureQualityAnalyzer: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState('');
  const [documentContent, setDocumentContent] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [results, setResults] = useState<AnalysisResult[]>([]);
  const [historyItems, setHistoryItems] = useState<SecureAnalysisMetadata[]>([]);
  const [piiWarning, setPiiWarning] = useState<{ show: boolean; types: string[] }>({ show: false, types: [] });
  const [securityAlert, setSecurityAlert] = useState<{ show: boolean; message: string }>({ show: false, message: '' });
  const [expandedAccordion, setExpandedAccordion] = useState<string | false>(false);
  const [storageInfo, setStorageInfo] = useState({ size: 0, items: 0 });

  const qualityDimensions = [
    'Completeness',
    'Clarity',
    'Structure',
    'Examples',
    'Accessibility'
  ];

  // Load history on mount
  useEffect(() => {
    const history = SecureStorage.loadAnalysisHistory();
    setHistoryItems(history);
    updateStorageInfo();
  }, []);

  // Update storage info
  const updateStorageInfo = useCallback(() => {
    const size = SecureStorage.getStorageSize();
    const items = SecureStorage.loadAnalysisHistory().length;
    setStorageInfo({ size, items });
  }, []);

  // Handle file name input with sanitization
  const handleFileNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const sanitized = SecurityUtils.sanitizeFileName(e.target.value);
    setSelectedFile(sanitized);
    
    if (sanitized !== e.target.value) {
      setSecurityAlert({
        show: true,
        message: 'File name has been sanitized for security',
      });
    }
  };

  // Handle document content change with PII detection
  const handleDocumentContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const content = e.target.value;
    setDocumentContent(content);

    // Check for PII
    const piiCheck = SecurityUtils.detectPII(content);
    if (piiCheck.hasPII) {
      setPiiWarning({
        show: true,
        types: piiCheck.types,
      });
    } else {
      setPiiWarning({ show: false, types: [] });
    }
  };

  // Secure analysis handler
  const handleAnalyze = async () => {
    // Validate content
    const sizeCheck = SecurityUtils.validateContentSize(documentContent);
    if (!sizeCheck.valid) {
      setSecurityAlert({
        show: true,
        message: sizeCheck.message || 'Content validation failed',
      });
      return;
    }

    if (!documentContent.trim()) {
      setSecurityAlert({
        show: true,
        message: 'Please paste some content to analyze',
      });
      return;
    }

    // Check for PII and warn user
    const piiCheck = SecurityUtils.detectPII(documentContent);
    if (piiCheck.hasPII && !confirm('Warning: Personal information detected in your document. Continue with analysis?')) {
      return;
    }

    const contentHash = SecurityUtils.generateContentHash(documentContent);
    const fileName = selectedFile || 'document.md';

    const newAnalysis: AnalysisResult = {
      id: `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      fileName: SecurityUtils.sanitizeFileName(fileName),
      contentHash,
      overallScore: 0,
      analysisDate: Date.now(),
      scores: [],
      status: 'analyzing',
      documentSize: new Blob([documentContent]).size,
      hasPII: piiCheck.hasPII,
      documentContent, // Keep in memory only
    };

    setResults(prev => [newAnalysis, ...prev]);
    setIsAnalyzing(true);

    try {
      // Add security headers to request
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-Content-Hash': contentHash,
          'X-Request-ID': newAnalysis.id,
        },
        body: JSON.stringify({
          content: documentContent,
          file_name: SecurityUtils.sanitizeFileName(fileName),
          // Don't send PII flag to server
        }),
        credentials: 'omit', // Don't send cookies
      });

      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }

      const data = await response.json();

      if (data.success && data.result) {
        const analysisResult = data.result;
        
        const completedAnalysis: AnalysisResult = {
          ...newAnalysis,
          status: 'complete',
          scores: analysisResult.scores,
          overallScore: analysisResult.overallScore,
        };

        setResults(prev => prev.map(result =>
          result.id === newAnalysis.id ? completedAnalysis : result
        ));

        // Save only metadata (no content)
        const metadata: SecureAnalysisMetadata = {
          id: completedAnalysis.id,
          fileName: completedAnalysis.fileName,
          contentHash: completedAnalysis.contentHash,
          overallScore: completedAnalysis.overallScore,
          analysisDate: completedAnalysis.analysisDate,
          scores: completedAnalysis.scores,
          documentSize: completedAnalysis.documentSize,
          hasPII: completedAnalysis.hasPII,
        };

        SecureStorage.saveAnalysisMetadata(metadata);
        updateStorageInfo();
      }
    } catch (error) {
      console.error('Analysis error:', error);
      setResults(prev => prev.map(result =>
        result.id === newAnalysis.id
          ? { ...result, status: 'error' }
          : result
      ));
      
      setSecurityAlert({
        show: true,
        message: 'Analysis failed. Please try again.',
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Secure export (metadata only by default)
  const handleExportResults = (result: AnalysisResult, includeScores = true) => {
    const confirmMessage = 'Export analysis results? (Note: Document content will NOT be included for security)';
    
    if (!confirm(confirmMessage)) {
      return;
    }

    const exportData = {
      fileName: result.fileName,
      analysisDate: new Date(result.analysisDate).toISOString(),
      overallScore: result.overallScore,
      contentHash: result.contentHash,
      documentSize: result.documentSize,
      hasPII: result.hasPII,
      ...(includeScores && { scores: result.scores }),
      _metadata: {
        exported: new Date().toISOString(),
        version: '1.0',
        security: 'content-excluded',
      },
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { 
      type: 'application/json' 
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analysis-${result.fileName}-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Clear all data with confirmation
  const handleClearAll = () => {
    if (confirm('This will permanently delete all analysis history. Continue?')) {
      SecureStorage.clearAll();
      setHistoryItems([]);
      setResults([]);
      updateStorageInfo();
      setSecurityAlert({
        show: true,
        message: 'All data has been securely cleared',
      });
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'success';
    if (score >= 60) return 'warning';
    return 'error';
  };

  const getScoreIcon = (score: number) => {
    if (score >= 80) return <SuccessIcon color="success" />;
    if (score >= 60) return <WarningIcon color="warning" />;
    return <ErrorIcon color="error" />;
  };

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            <SecurityIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
            Secure Quality Analyzer
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Privacy-first documentation analysis with enhanced security and PII protection
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <Chip
            icon={<LockIcon />}
            label={`Storage: ${(storageInfo.size / 1024).toFixed(1)}KB`}
            color="primary"
            size="small"
          />
          <Button
            variant="outlined"
            color="error"
            startIcon={<DeleteIcon />}
            onClick={handleClearAll}
            size="small"
          >
            Clear All
          </Button>
        </Box>
      </Box>

      {/* Security Alerts */}
      {piiWarning.show && (
        <Alert severity="warning" sx={{ mb: 2 }} onClose={() => setPiiWarning({ show: false, types: [] })}>
          <strong>Personal Information Detected:</strong> {piiWarning.types.join(', ')}. 
          This content will NOT be stored locally for your security.
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Input Section */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Analyze Documentation
              </Typography>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <TextField
                  label="Document Name"
                  value={selectedFile}
                  onChange={handleFileNameChange}
                  placeholder="document.md"
                  fullWidth
                  helperText="File name will be sanitized for security"
                />

                <TextField
                  label="Document Content"
                  multiline
                  rows={10}
                  value={documentContent}
                  onChange={handleDocumentContentChange}
                  placeholder="Paste your documentation here..."
                  fullWidth
                  required
                  helperText={`${documentContent.length}/50,000 characters`}
                  error={documentContent.length > 50000}
                />

                <Button
                  variant="contained"
                  startIcon={isAnalyzing ? <CircularProgress size={20} /> : <AnalyzeIcon />}
                  onClick={handleAnalyze}
                  disabled={!documentContent.trim() || isAnalyzing || documentContent.length > 50000}
                  size="large"
                  fullWidth
                >
                  {isAnalyzing ? 'Analyzing...' : 'Analyze Quality'}
                </Button>

                {/* Security Info */}
                <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                  <Typography variant="subtitle2" gutterBottom>
                    <LockIcon sx={{ fontSize: 16, mr: 0.5, verticalAlign: 'middle' }} />
                    Security Features
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    • No document content stored locally<br />
                    • PII detection and warnings<br />
                    • Automatic data expiry (30 days)<br />
                    • Secure metadata-only exports
                  </Typography>
                </Paper>
              </Box>
            </CardContent>
          </Card>

          {/* History */}
          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Analyses ({historyItems.length})
              </Typography>
              <List dense>
                {historyItems.slice(0, 5).map((item) => (
                  <ListItem key={item.id}>
                    <ListItemIcon>
                      <HistoryIcon fontSize="small" />
                    </ListItemIcon>
                    <ListItemText
                      primary={item.fileName}
                      secondary={`Score: ${Math.round(item.overallScore)} • ${new Date(item.analysisDate).toLocaleDateString()}`}
                    />
                  </ListItem>
                ))}
                {historyItems.length === 0 && (
                  <Typography variant="body2" color="text.secondary">
                    No history available
                  </Typography>
                )}
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Results Section */}
        <Grid item xs={12} md={8}>
          {results.length === 0 ? (
            <Card>
              <CardContent>
                <Alert severity="info">
                  No analysis performed yet. Your documents are analyzed securely without storing sensitive content.
                </Alert>
              </CardContent>
            </Card>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {results.map((result) => (
                <Card key={result.id}>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                      <Box>
                        <Typography variant="h6" gutterBottom>
                          {SecurityUtils.sanitizeForDisplay(result.fileName)}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Analyzed: {new Date(result.analysisDate).toLocaleString()}
                        </Typography>
                        {result.hasPII && (
                          <Chip
                            size="small"
                            label="Contains PII"
                            color="warning"
                            sx={{ mt: 1 }}
                          />
                        )}
                      </Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        {result.status === 'analyzing' && <CircularProgress size={24} />}
                        {result.status === 'complete' && (
                          <>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              {getScoreIcon(result.overallScore)}
                              <Typography variant="h5" color={getScoreColor(result.overallScore)}>
                                {Math.round(result.overallScore)}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                / 100
                              </Typography>
                            </Box>
                            <Tooltip title="Export analysis (secure, no content)">
                              <IconButton size="small" onClick={() => handleExportResults(result)}>
                                <ExportIcon />
                              </IconButton>
                            </Tooltip>
                          </>
                        )}
                      </Box>
                    </Box>

                    {result.status === 'complete' && (
                      <>
                        <Box sx={{ mb: 3 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                            <Typography variant="body2">Overall Quality Score</Typography>
                            <Typography variant="body2">{Math.round(result.overallScore)}%</Typography>
                          </Box>
                          <LinearProgress 
                            variant="determinate" 
                            value={result.overallScore}
                            color={getScoreColor(result.overallScore)}
                            sx={{ height: 8, borderRadius: 4 }}
                          />
                        </Box>

                        <Typography variant="subtitle1" gutterBottom>
                          Quality Breakdown
                        </Typography>
                        {result.scores.map((score, index) => (
                          <Accordion
                            key={score.dimension}
                            expanded={expandedAccordion === `${result.id}-${index}`}
                            onChange={(e, isExpanded) => setExpandedAccordion(isExpanded ? `${result.id}-${index}` : false)}
                          >
                            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                                <Typography sx={{ flexGrow: 1 }}>
                                  {score.dimension}
                                </Typography>
                                <Chip 
                                  label={`${score.score}/${score.maxScore}`}
                                  color={getScoreColor(score.score)}
                                  size="small"
                                />
                              </Box>
                            </AccordionSummary>
                            <AccordionDetails>
                              <Grid container spacing={2}>
                                <Grid item xs={12} md={6}>
                                  <Typography variant="subtitle2" gutterBottom color="error">
                                    Issues ({score.issues.length})
                                  </Typography>
                                  <List dense>
                                    {score.issues.map((issue, i) => (
                                      <ListItem key={i} sx={{ py: 0 }}>
                                        <ListItemIcon>
                                          <ErrorIcon color="error" fontSize="small" />
                                        </ListItemIcon>
                                        <ListItemText primary={SecurityUtils.sanitizeForDisplay(issue)} />
                                      </ListItem>
                                    ))}
                                  </List>
                                </Grid>
                                <Grid item xs={12} md={6}>
                                  <Typography variant="subtitle2" gutterBottom color="primary">
                                    Suggestions ({score.suggestions.length})
                                  </Typography>
                                  <List dense>
                                    {score.suggestions.map((suggestion, i) => (
                                      <ListItem key={i} sx={{ py: 0 }}>
                                        <ListItemIcon>
                                          <TrendIcon color="primary" fontSize="small" />
                                        </ListItemIcon>
                                        <ListItemText primary={SecurityUtils.sanitizeForDisplay(suggestion)} />
                                      </ListItem>
                                    ))}
                                  </List>
                                </Grid>
                              </Grid>
                            </AccordionDetails>
                          </Accordion>
                        ))}
                      </>
                    )}

                    {result.status === 'error' && (
                      <Alert severity="error">
                        Analysis failed. Please try again.
                      </Alert>
                    )}
                  </CardContent>
                </Card>
              ))}
            </Box>
          )}
        </Grid>
      </Grid>

      {/* Security Alert Snackbar */}
      <Snackbar
        open={securityAlert.show}
        autoHideDuration={6000}
        onClose={() => setSecurityAlert({ show: false, message: '' })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={() => setSecurityAlert({ show: false, message: '' })} severity="info">
          {securityAlert.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default SecureQualityAnalyzer;