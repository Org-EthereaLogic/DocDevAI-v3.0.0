/**
 * DevDocAI v3.0.0 - Quality Analyzer Component
 * 
 * Interface for M005 Quality Engine module
 * Provides documentation quality analysis and scoring across multiple dimensions.
 */

import React, { useState } from 'react';
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
}

const QualityAnalyzer: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState('');
  const [documentContent, setDocumentContent] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [results, setResults] = useState<AnalysisResult[]>([]);
  const [expandedAccordion, setExpandedAccordion] = useState<string | false>(false);

  const qualityDimensions = [
    'Completeness',
    'Clarity',
    'Structure',
    'Examples',
    'Accessibility'
  ];

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
    };

    setResults(prev => [newAnalysis, ...prev]);
    setIsAnalyzing(true);

    try {
      // Call the production API server with proper structure
      const response = await fetch('http://localhost:5000/api/analyze', {
        method: 'POST',
        mode: 'cors',
        credentials: 'omit',
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

        setResults(prev => prev.map(result =>
          result.id === newAnalysis.id
            ? {
                ...result,
                status: 'complete' as const,
                scores: transformedScores,
                overallScore: analysisResult.overallScore,
                analysisDate: new Date(analysisResult.analysisDate),
              }
            : result
        ));
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

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Quality Analyzer
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Analyze documentation quality across multiple dimensions with AI-powered insights and recommendations.
      </Typography>

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
                            <IconButton size="small">
                              <ExportIcon />
                            </IconButton>
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
    </Box>
  );
};

export default QualityAnalyzer;