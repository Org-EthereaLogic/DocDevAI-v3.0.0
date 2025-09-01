/**
 * DevDocAI v3.0.0 - Review Engine Component
 * 
 * Interface for M007 Review Engine module
 * Provides documentation review, feedback, and collaborative improvement features.
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
  Chip,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Paper,
  IconButton,
  Avatar,
  Rating,
  Divider,
  Tabs,
  Tab,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Badge,
} from '@mui/material';
import {
  RateReview as ReviewIcon,
  Add as AddIcon,
  Comment as CommentIcon,
  ThumbUp as ApproveIcon,
  ThumbDown as RejectIcon,
  Edit as EditIcon,
  Visibility as ViewIcon,
  PersonAdd as AssignIcon,
  Schedule as PendingIcon,
  CheckCircle as ApprovedIcon,
  Cancel as RejectedIcon,
  TrendingUp as InsightIcon,
} from '@mui/icons-material';

interface Review {
  id: string;
  documentPath: string;
  reviewer: string;
  reviewerAvatar?: string;
  status: 'pending' | 'in_progress' | 'approved' | 'rejected' | 'requires_changes';
  rating: number;
  comments: ReviewComment[];
  createdAt: Date;
  completedAt?: Date;
  assignedBy: string;
}

interface ReviewComment {
  id: string;
  lineNumber?: number;
  section: string;
  comment: string;
  type: 'suggestion' | 'issue' | 'praise' | 'question';
  author: string;
  timestamp: Date;
  resolved: boolean;
}

interface ReviewMetrics {
  totalReviews: number;
  pendingReviews: number;
  averageRating: number;
  averageTimeToComplete: number; // in days
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel = ({ children, value, index, ...other }: TabPanelProps) => {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`review-tabpanel-${index}`}
      aria-labelledby={`review-tab-${index}`}
      {...other}
    >
      {value === index && <Box>{children}</Box>}
    </div>
  );
};

const ReviewEngine: React.FC = () => {
  const [currentTab, setCurrentTab] = useState(0);
  const [reviews, setReviews] = useState<Review[]>([
    {
      id: '1',
      documentPath: '/docs/api-reference.md',
      reviewer: 'Alice Johnson',
      reviewerAvatar: '/avatars/alice.jpg',
      status: 'in_progress',
      rating: 0,
      comments: [
        {
          id: 'c1',
          lineNumber: 45,
          section: 'Authentication',
          comment: 'Missing example for JWT token usage',
          type: 'issue',
          author: 'Alice Johnson',
          timestamp: new Date(Date.now() - 3600000),
          resolved: false,
        },
        {
          id: 'c2',
          section: 'Error Handling',
          comment: 'Great explanation of error codes!',
          type: 'praise',
          author: 'Alice Johnson',
          timestamp: new Date(Date.now() - 1800000),
          resolved: false,
        },
      ],
      createdAt: new Date(Date.now() - 86400000),
      assignedBy: 'Bob Smith',
    },
    {
      id: '2',
      documentPath: '/docs/installation-guide.md',
      reviewer: 'Charlie Davis',
      status: 'approved',
      rating: 4.5,
      comments: [
        {
          id: 'c3',
          section: 'Prerequisites',
          comment: 'Consider adding Docker as an alternative installation method',
          type: 'suggestion',
          author: 'Charlie Davis',
          timestamp: new Date(Date.now() - 172800000),
          resolved: true,
        },
      ],
      createdAt: new Date(Date.now() - 259200000),
      completedAt: new Date(Date.now() - 86400000),
      assignedBy: 'Eve Wilson',
    },
  ]);

  const [newReviewDialog, setNewReviewDialog] = useState(false);
  const [reviewFormData, setReviewFormData] = useState({
    documentPath: '',
    reviewer: '',
    priority: 'medium',
  });

  const [metrics] = useState<ReviewMetrics>({
    totalReviews: 24,
    pendingReviews: 3,
    averageRating: 4.2,
    averageTimeToComplete: 2.5,
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <PendingIcon color="warning" />;
      case 'in_progress':
        return <EditIcon color="primary" />;
      case 'approved':
        return <ApprovedIcon color="success" />;
      case 'rejected':
        return <RejectedIcon color="error" />;
      case 'requires_changes':
        return <EditIcon color="warning" />;
      default:
        return <ReviewIcon />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'success';
      case 'rejected':
        return 'error';
      case 'requires_changes':
        return 'warning';
      case 'in_progress':
        return 'primary';
      default:
        return 'default';
    }
  };

  const getCommentTypeIcon = (type: string) => {
    switch (type) {
      case 'suggestion':
        return <InsightIcon color="primary" />;
      case 'issue':
        return <RejectedIcon color="error" />;
      case 'praise':
        return <ApproveIcon color="success" />;
      case 'question':
        return <CommentIcon color="info" />;
      default:
        return <CommentIcon />;
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const handleCreateReview = () => {
    const newReview: Review = {
      id: Date.now().toString(),
      ...reviewFormData,
      status: 'pending',
      rating: 0,
      comments: [],
      createdAt: new Date(),
      assignedBy: 'Current User',
    };

    setReviews(prev => [...prev, newReview]);
    setNewReviewDialog(false);
    setReviewFormData({ documentPath: '', reviewer: '', priority: 'medium' });
  };

  const handleReviewAction = (reviewId: string, action: 'approve' | 'reject' | 'request_changes') => {
    setReviews(prev => prev.map(review => {
      if (review.id === reviewId) {
        const status = action === 'approve' ? 'approved' : 
                      action === 'reject' ? 'rejected' : 'requires_changes';
        return {
          ...review,
          status,
          completedAt: action === 'approve' || action === 'reject' ? new Date() : undefined,
        };
      }
      return review;
    }));
  };

  const pendingReviews = reviews.filter(r => r.status === 'pending' || r.status === 'in_progress');
  const completedReviews = reviews.filter(r => r.status === 'approved' || r.status === 'rejected');

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Review Engine
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Manage documentation reviews, collaborate on improvements, and track feedback across all documents.
      </Typography>

      {/* Metrics Overview */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="primary">
                {metrics.totalReviews}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total Reviews
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Badge badgeContent={metrics.pendingReviews} color="warning">
                <Typography variant="h4" color="warning.main">
                  {metrics.pendingReviews}
                </Typography>
              </Badge>
              <Typography variant="body2" color="text.secondary">
                Pending Reviews
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
                <Typography variant="h4" color="success.main">
                  {metrics.averageRating}
                </Typography>
                <Rating value={metrics.averageRating} precision={0.1} readOnly size="small" />
              </Box>
              <Typography variant="body2" color="text.secondary">
                Average Rating
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="info.main">
                {metrics.averageTimeToComplete}d
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Avg. Completion Time
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Main Content */}
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Tabs value={currentTab} onChange={handleTabChange}>
              <Tab label={`Active Reviews (${pendingReviews.length})`} />
              <Tab label={`Completed Reviews (${completedReviews.length})`} />
              <Tab label="Analytics" />
            </Tabs>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setNewReviewDialog(true)}
            >
              New Review
            </Button>
          </Box>

          <TabPanel value={currentTab} index={0}>
            {/* Active Reviews */}
            {pendingReviews.length === 0 ? (
              <Alert severity="info">
                No active reviews. Create a new review to get started.
              </Alert>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {pendingReviews.map((review) => (
                  <Paper key={review.id} sx={{ p: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                      <Box>
                        <Typography variant="h6" gutterBottom>
                          {review.documentPath}
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <Avatar sx={{ width: 24, height: 24 }} src={review.reviewerAvatar}>
                            {review.reviewer.charAt(0)}
                          </Avatar>
                          <Typography variant="body2">
                            Assigned to: {review.reviewer}
                          </Typography>
                          <Chip
                            icon={getStatusIcon(review.status)}
                            label={review.status.replace('_', ' ')}
                            size="small"
                            color={getStatusColor(review.status)}
                          />
                        </Box>
                        <Typography variant="caption" color="text.secondary">
                          Created: {review.createdAt.toLocaleString()} • Assigned by: {review.assignedBy}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <IconButton size="small" title="View Details">
                          <ViewIcon />
                        </IconButton>
                        <IconButton 
                          size="small" 
                          color="success"
                          onClick={() => handleReviewAction(review.id, 'approve')}
                          title="Approve"
                        >
                          <ApproveIcon />
                        </IconButton>
                        <IconButton 
                          size="small" 
                          color="error"
                          onClick={() => handleReviewAction(review.id, 'reject')}
                          title="Reject"
                        >
                          <RejectIcon />
                        </IconButton>
                      </Box>
                    </Box>

                    {/* Comments */}
                    {review.comments.length > 0 && (
                      <Box>
                        <Typography variant="subtitle2" gutterBottom>
                          Comments ({review.comments.filter(c => !c.resolved).length} unresolved)
                        </Typography>
                        <List>
                          {review.comments.slice(0, 3).map((comment) => (
                            <ListItem key={comment.id} sx={{ py: 0.5, opacity: comment.resolved ? 0.7 : 1 }}>
                              <ListItemIcon>
                                {getCommentTypeIcon(comment.type)}
                              </ListItemIcon>
                              <ListItemText
                                primary={comment.comment}
                                secondary={
                                  <Box>
                                    <Typography variant="caption">
                                      {comment.section}
                                      {comment.lineNumber && ` (Line ${comment.lineNumber})`}
                                    </Typography>
                                    <Typography variant="caption" display="block">
                                      {comment.author} • {comment.timestamp.toLocaleString()}
                                    </Typography>
                                  </Box>
                                }
                              />
                              {comment.resolved && (
                                <Chip label="Resolved" size="small" color="success" variant="outlined" />
                              )}
                            </ListItem>
                          ))}
                          {review.comments.length > 3 && (
                            <Typography variant="caption" sx={{ pl: 2, color: 'text.secondary' }}>
                              +{review.comments.length - 3} more comments...
                            </Typography>
                          )}
                        </List>
                      </Box>
                    )}
                  </Paper>
                ))}
              </Box>
            )}
          </TabPanel>

          <TabPanel value={currentTab} index={1}>
            {/* Completed Reviews */}
            {completedReviews.length === 0 ? (
              <Alert severity="info">
                No completed reviews yet.
              </Alert>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {completedReviews.map((review) => (
                  <Paper key={review.id} sx={{ p: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <Box>
                        <Typography variant="h6" gutterBottom>
                          {review.documentPath}
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          <Avatar sx={{ width: 24, height: 24 }}>
                            {review.reviewer.charAt(0)}
                          </Avatar>
                          <Typography variant="body2">
                            Reviewed by: {review.reviewer}
                          </Typography>
                          <Chip
                            icon={getStatusIcon(review.status)}
                            label={review.status}
                            size="small"
                            color={getStatusColor(review.status)}
                          />
                          {review.rating > 0 && (
                            <Rating value={review.rating} precision={0.5} size="small" readOnly />
                          )}
                        </Box>
                        <Typography variant="caption" color="text.secondary">
                          Completed: {review.completedAt?.toLocaleString()}
                        </Typography>
                      </Box>
                      <IconButton size="small" title="View Details">
                        <ViewIcon />
                      </IconButton>
                    </Box>
                  </Paper>
                ))}
              </Box>
            )}
          </TabPanel>

          <TabPanel value={currentTab} index={2}>
            {/* Analytics */}
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Review Distribution
                  </Typography>
                  <List>
                    <ListItem>
                      <ListItemText
                        primary="Approved"
                        secondary={`${reviews.filter(r => r.status === 'approved').length} reviews`}
                      />
                      <Typography variant="h6" color="success.main">
                        {Math.round((reviews.filter(r => r.status === 'approved').length / reviews.length) * 100)}%
                      </Typography>
                    </ListItem>
                    <ListItem>
                      <ListItemText
                        primary="Rejected"
                        secondary={`${reviews.filter(r => r.status === 'rejected').length} reviews`}
                      />
                      <Typography variant="h6" color="error.main">
                        {Math.round((reviews.filter(r => r.status === 'rejected').length / reviews.length) * 100)}%
                      </Typography>
                    </ListItem>
                  </List>
                </Paper>
              </Grid>
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Recent Activity
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Analytics and insights coming soon...
                  </Typography>
                </Paper>
              </Grid>
            </Grid>
          </TabPanel>
        </CardContent>
      </Card>

      {/* New Review Dialog */}
      <Dialog open={newReviewDialog} onClose={() => setNewReviewDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Review</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="Document Path"
              value={reviewFormData.documentPath}
              onChange={(e) => setReviewFormData(prev => ({ ...prev, documentPath: e.target.value }))}
              placeholder="/docs/filename.md"
              fullWidth
              required
            />
            <TextField
              label="Reviewer"
              value={reviewFormData.reviewer}
              onChange={(e) => setReviewFormData(prev => ({ ...prev, reviewer: e.target.value }))}
              placeholder="Enter reviewer name or email"
              fullWidth
              required
            />
            <FormControl fullWidth>
              <InputLabel>Priority</InputLabel>
              <Select
                value={reviewFormData.priority}
                onChange={(e) => setReviewFormData(prev => ({ ...prev, priority: e.target.value }))}
                label="Priority"
              >
                <MenuItem value="low">Low</MenuItem>
                <MenuItem value="medium">Medium</MenuItem>
                <MenuItem value="high">High</MenuItem>
                <MenuItem value="urgent">Urgent</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setNewReviewDialog(false)}>Cancel</Button>
          <Button
            onClick={handleCreateReview}
            variant="contained"
            disabled={!reviewFormData.documentPath || !reviewFormData.reviewer}
          >
            Create Review
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ReviewEngine;