/**
 * DevDocAI v3.0.0 - Quality Analyzer Component
 * 
 * Interface for M005 Quality Engine module
 * Provides documentation quality analysis and scoring across multiple dimensions.
 */

import React, { useState, useEffect } from 'react';
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
} from '@mui/icons-material';

interface QualityScore {
  dimension: string;
  score: number;
  maxScore: number;
  issues: string[];
  suggestions: string[];
}

interface AnalysisResult {
  id: string;
  fileName: string;
  overallScore: number;
  analysisDate: Date;
  scores: QualityScore[];
  status: 'analyzing' | 'complete' | 'error';
  documentContent?: string; // Store the analyzed content
}

// LocalStorage keys
const STORAGE_KEY_CURRENT = 'devdocai_quality_analysis_current';
const STORAGE_KEY_HISTORY = 'devdocai_quality_analysis_history';
const MAX_HISTORY_ITEMS = 10;

const QualityAnalyzer: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState('');
  const [documentContent, setDocumentContent] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [results, setResults] = useState<AnalysisResult[]>([]);
  const [expandedAccordion, setExpandedAccordion] = useState<string | false>(false);
  const [historyMenuAnchor, setHistoryMenuAnchor] = useState<null | HTMLElement>(null);
  const [historyItems, setHistoryItems] = useState<AnalysisResult[]>([]);
  const [clearDialogOpen, setClearDialogOpen] = useState(false);
  const [dataRestored, setDataRestored] = useState(false);

  const qualityDimensions = [
    'Completeness',
    'Clarity',
    'Structure',
    'Examples',
    'Accessibility'
  ];

  // Helper functions for localStorage operations
  const saveToLocalStorage = (key: string, data: any) => {
    try {
      const serialized = JSON.stringify(data, (key, value) => {
        // Convert Date objects to ISO strings
        if (value instanceof Date) {
          return value.toISOString();
        }
        return value;
      });
      localStorage.setItem(key, serialized);
    } catch (error) {
      console.error('Error saving to localStorage:', error);
    }
  };

  const loadFromLocalStorage = (key: string): any => {
    try {
      const item = localStorage.getItem(key);
      if (!item) return null;
      
      return JSON.parse(item, (key, value) => {
        // Convert ISO strings back to Date objects
        if (typeof value === 'string' && /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(value)) {
          return new Date(value);
        }
        return value;
      });
    } catch (error) {
      console.error('Error loading from localStorage:', error);
      return null;
    }
  };

  // Load saved data on component mount
  useEffect(() => {
    let hasRestoredData = false;
    
    // Load current analysis
    const savedCurrent = loadFromLocalStorage(STORAGE_KEY_CURRENT);
    if (savedCurrent) {
      const { fileName, documentContent: savedContent, results: savedResults } = savedCurrent;
      if (fileName) {
        setSelectedFile(fileName);
        hasRestoredData = true;
      }
      if (savedContent) {
        setDocumentContent(savedContent);
        hasRestoredData = true;
      }
      if (savedResults && Array.isArray(savedResults)) {
        // Filter out any 'analyzing' status results on load
        const completedResults = savedResults.filter((r: AnalysisResult) => r.status !== 'analyzing');
        if (completedResults.length > 0) {
          setResults(completedResults);
          hasRestoredData = true;
        }
      }
    }

    // Load history
    const savedHistory = loadFromLocalStorage(STORAGE_KEY_HISTORY);
    if (savedHistory && Array.isArray(savedHistory)) {
      setHistoryItems(savedHistory);
    }
    
    // Show indicator if data was restored
    if (hasRestoredData) {
      setDataRestored(true);
      // Hide the indicator after 5 seconds
      setTimeout(() => setDataRestored(false), 5000);
    }
  }, []);

  // Save current state whenever results change
  useEffect(() => {
    if (results.length > 0) {
      const currentState = {
        fileName: selectedFile,
        documentContent: documentContent,
        results: results,
        savedAt: new Date().toISOString()
      };
      saveToLocalStorage(STORAGE_KEY_CURRENT, currentState);
    }
  }, [results, selectedFile, documentContent]);

  // Add completed analysis to history
  const addToHistory = (result: AnalysisResult) => {
    if (result.status === 'complete') {
      const newHistoryItem = { ...result, documentContent };
      const updatedHistory = [newHistoryItem, ...historyItems]
        .filter((item, index, self) => 
          // Remove duplicates based on id
          index === self.findIndex(t => t.id === item.id)
        )
        .slice(0, MAX_HISTORY_ITEMS);
      
      setHistoryItems(updatedHistory);
      saveToLocalStorage(STORAGE_KEY_HISTORY, updatedHistory);
    }
  };

  const handleAnalyze = async () => {
    if (!documentContent) {
      alert('Please paste some content to analyze');
      return;
    }

    const newAnalysis: AnalysisResult = {
      id: Date.now().toString(),
      fileName: selectedFile || 'document.md',
      overallScore: 0,
      analysisDate: new Date(),
      scores: [],
      status: 'analyzing',
      documentContent: documentContent, // Store the content being analyzed
    };

    setResults(prev => [newAnalysis, ...prev]);
    setIsAnalyzing(true);

    try {
      // Use relative URL to leverage webpack's proxy configuration
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          content: documentContent,
          file_name: selectedFile || 'document.md',
        }),
      });

      if (!response.ok) {
        throw new Error(`API request failed: ${response.status} - ${response.statusText}`);
      }

      const data = await response.json();
      console.log('API Response:', data);

      // The production server returns a different structure
      if (data.success && data.result) {
        const analysisResult = data.result;
        
        // Transform API response to match our component's structure
        const transformedScores: QualityScore[] = analysisResult.scores.map((score: any) => ({
          dimension: score.dimension,
          score: score.score,
          maxScore: score.maxScore || 100,
          issues: score.issues || [],
          suggestions: score.suggestions || [],
        }));

        const completedAnalysis = {
          ...newAnalysis,
          status: 'complete' as const,
          scores: transformedScores,
          overallScore: analysisResult.overallScore,
          analysisDate: new Date(analysisResult.analysisDate),
          documentContent: documentContent,
        };

        setResults(prev => prev.map(result =>
          result.id === newAnalysis.id ? completedAnalysis : result
        ));

        // Add to history after successful analysis
        addToHistory(completedAnalysis);
      } else {
        throw new Error('Invalid API response structure');
      }
    } catch (error) {
      console.error('Quality analysis error:', error);
      
      // Show user-friendly error message
      alert(`Analysis failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
      
      setResults(prev => prev.map(result =>
        result.id === newAnalysis.id
          ? { ...result, status: 'error' as const }
          : result
      ));
    } finally {
      setIsAnalyzing(false);
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

  const handleAccordionChange = (panel: string) => (event: React.SyntheticEvent, isExpanded: boolean) => {
    setExpandedAccordion(isExpanded ? panel : false);
  };

  // Clear all data functions
  const handleClearCurrent = () => {
    setResults([]);
    setDocumentContent('');
    setSelectedFile('');
    localStorage.removeItem(STORAGE_KEY_CURRENT);
  };

  const handleClearHistory = () => {
    setHistoryItems([]);
    localStorage.removeItem(STORAGE_KEY_HISTORY);
    setClearDialogOpen(false);
  };

  const handleClearAll = () => {
    handleClearCurrent();
    handleClearHistory();
  };

  // Load analysis from history
  const handleLoadFromHistory = (historyItem: AnalysisResult) => {
    setSelectedFile(historyItem.fileName);
    setDocumentContent(historyItem.documentContent || '');
    setResults([historyItem]);
    setHistoryMenuAnchor(null);
  };

  // Delete specific item from history
  const handleDeleteHistoryItem = (itemId: string) => {
    const updatedHistory = historyItems.filter(item => item.id !== itemId);
    setHistoryItems(updatedHistory);
    saveToLocalStorage(STORAGE_KEY_HISTORY, updatedHistory);
  };

  // Export analysis results
  const handleExportResults = (result: AnalysisResult) => {
    const exportData = {
      fileName: result.fileName,
      analysisDate: result.analysisDate,
      overallScore: result.overallScore,
      scores: result.scores,
      documentContent: result.documentContent,
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `quality-analysis-${result.fileName}-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Quality Analyzer
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Analyze documentation quality across multiple dimensions with AI-powered insights and recommendations.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="View analysis history">
            <Button
              variant="outlined"
              startIcon={<HistoryIcon />}
              onClick={(e) => setHistoryMenuAnchor(e.currentTarget)}
              disabled={historyItems.length === 0}
            >
              History ({historyItems.length})
            </Button>
          </Tooltip>
          <Tooltip title="Clear current analysis">
            <Button
              variant="outlined"
              startIcon={<ClearIcon />}
              onClick={handleClearCurrent}
              disabled={results.length === 0}
            >
              Clear Current
            </Button>
          </Tooltip>
          <Tooltip title="Clear all data">
            <Button
              variant="outlined"
              color="error"
              startIcon={<DeleteIcon />}
              onClick={() => setClearDialogOpen(true)}
              disabled={results.length === 0 && historyItems.length === 0}
            >
              Clear All
            </Button>
          </Tooltip>
        </Box>
      </Box>

      {/* Data Restored Notification */}
      {dataRestored && (
        <Alert 
          severity="info" 
          sx={{ mb: 2 }}
          onClose={() => setDataRestored(false)}
        >
          Previous analysis data has been restored from your last session.
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Analysis Input */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Analyze Documentation
              </Typography>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <TextField
                  label="Document Name (Optional)"
                  value={selectedFile}
                  onChange={(e) => setSelectedFile(e.target.value)}
                  placeholder="README.md"
                  fullWidth
                />

                <TextField
                  label="Document Content"
                  multiline
                  rows={10}
                  value={documentContent}
                  onChange={(e) => setDocumentContent(e.target.value)}
                  placeholder="Paste your documentation here for quality analysis..."
                  fullWidth
                  required
                  helperText="Paste your markdown, code documentation, or any text content here"
                />

                <Button
                  variant="contained"
                  startIcon={<AnalyzeIcon />}
                  onClick={handleAnalyze}
                  disabled={!documentContent || isAnalyzing}
                  size="large"
                >
                  {isAnalyzing ? 'Analyzing...' : 'Analyze Quality'}
                </Button>
              </Box>
            </CardContent>
          </Card>

          {/* Quality Dimensions Overview */}
          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Quality Dimensions
              </Typography>
              <List>
                {qualityDimensions.map((dimension) => (
                  <ListItem key={dimension} sx={{ py: 0.5 }}>
                    <ListItemIcon>
                      <MetricsIcon fontSize="small" />
                    </ListItemIcon>
                    <ListItemText
                      primary={dimension}
                      secondary={`Measures ${dimension.toLowerCase()} aspects`}
                    />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Analysis Results */}
        <Grid item xs={12} md={8}>
          {results.length === 0 ? (
            <Card>
              <CardContent>
                <Alert severity="info">
                  No quality analysis performed yet. Select a file or directory to analyze its documentation quality.
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
                          {result.fileName}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Analyzed: {result.analysisDate.toLocaleString()}
                        </Typography>
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
                            <Tooltip title="Export analysis results">
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
                        {/* Overall Progress */}
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

                        {/* Dimension Scores */}
                        <Typography variant="subtitle1" gutterBottom>
                          Quality Breakdown
                        </Typography>
                        {result.scores.map((score, index) => (
                          <Accordion
                            key={score.dimension}
                            expanded={expandedAccordion === `${result.id}-${index}`}
                            onChange={handleAccordionChange(`${result.id}-${index}`)}
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
                                    Issues Found ({score.issues.length})
                                  </Typography>
                                  <List dense>
                                    {score.issues.map((issue, i) => (
                                      <ListItem key={i} sx={{ py: 0 }}>
                                        <ListItemIcon>
                                          <ErrorIcon color="error" fontSize="small" />
                                        </ListItemIcon>
                                        <ListItemText primary={issue} />
                                      </ListItem>
                                    ))}
                                    {score.issues.length === 0 && (
                                      <Typography variant="body2" color="text.secondary">
                                        No issues found
                                      </Typography>
                                    )}
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
                                        <ListItemText primary={suggestion} />
                                      </ListItem>
                                    ))}
                                    {score.suggestions.length === 0 && (
                                      <Typography variant="body2" color="text.secondary">
                                        No suggestions available
                                      </Typography>
                                    )}
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
                        Failed to analyze the selected file. Please check the path and try again.
                      </Alert>
                    )}
                  </CardContent>
                </Card>
              ))}
            </Box>
          )}
        </Grid>
      </Grid>

      {/* History Menu */}
      <Menu
        anchorEl={historyMenuAnchor}
        open={Boolean(historyMenuAnchor)}
        onClose={() => setHistoryMenuAnchor(null)}
        PaperProps={{
          style: {
            maxHeight: 400,
            width: '350px',
          },
        }}
      >
        {historyItems.length === 0 ? (
          <MenuItem disabled>No history available</MenuItem>
        ) : (
          historyItems.map((item) => (
            <MenuItem
              key={item.id}
              onClick={() => handleLoadFromHistory(item)}
              sx={{ 
                display: 'flex', 
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: 1,
              }}
            >
              <Box sx={{ flex: 1 }}>
                <Typography variant="body2">{item.fileName}</Typography>
                <Typography variant="caption" color="text.secondary">
                  Score: {Math.round(item.overallScore)}/100 • {item.analysisDate.toLocaleDateString()}
                </Typography>
              </Box>
              <Tooltip title="Delete from history">
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteHistoryItem(item.id);
                  }}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </MenuItem>
          ))
        )}
      </Menu>

      {/* Clear Confirmation Dialog */}
      <Dialog
        open={clearDialogOpen}
        onClose={() => setClearDialogOpen(false)}
      >
        <DialogTitle>Clear All Data?</DialogTitle>
        <DialogContent>
          <Typography>
            This will permanently delete all current analysis results and history. 
            This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setClearDialogOpen(false)}>Cancel</Button>
          <Button 
            onClick={handleClearAll} 
            color="error" 
            variant="contained"
          >
            Clear All
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default QualityAnalyzer;