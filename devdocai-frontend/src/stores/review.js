import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { reviewAPI } from '@/services/api';

export const useReviewStore = defineStore('review', () => {
  // State
  const reviews = ref([]);
  const currentReview = ref(null);
  const loading = ref(false);
  const error = ref(null);
  const filters = ref({
    status: '', // 'pending', 'in_progress', 'completed', 'failed'
    severity: '', // 'critical', 'high', 'medium', 'low'
    type: '', // 'quality', 'security', 'performance', 'accessibility'
    sortBy: 'created', // 'created', 'updated', 'severity', 'score'
    sortOrder: 'desc'
  });

  // Review configuration
  const reviewTypes = ref([
    { id: 'quality', name: 'Quality Review', icon: '✨', description: 'Code quality and best practices' },
    { id: 'security', name: 'Security Review', icon: '🔒', description: 'Security vulnerabilities and compliance' },
    { id: 'performance', name: 'Performance Review', icon: '⚡', description: 'Performance bottlenecks and optimization' },
    { id: 'accessibility', name: 'Accessibility Review', icon: '♿', description: 'Accessibility standards compliance' },
    { id: 'documentation', name: 'Documentation Review', icon: '📚', description: 'Documentation completeness and clarity' }
  ]);

  const severityLevels = ref([
    { id: 'critical', name: 'Critical', color: 'red', priority: 4 },
    { id: 'high', name: 'High', color: 'orange', priority: 3 },
    { id: 'medium', name: 'Medium', color: 'yellow', priority: 2 },
    { id: 'low', name: 'Low', color: 'green', priority: 1 }
  ]);

  const reviewStatuses = ref([
    { id: 'pending', name: 'Pending', color: 'gray' },
    { id: 'in_progress', name: 'In Progress', color: 'blue' },
    { id: 'completed', name: 'Completed', color: 'green' },
    { id: 'failed', name: 'Failed', color: 'red' }
  ]);

  // Computed
  const filteredReviews = computed(() => {
    let filtered = reviews.value;

    // Apply status filter
    if (filters.value.status) {
      filtered = filtered.filter(review => review.status === filters.value.status);
    }

    // Apply severity filter
    if (filters.value.severity) {
      filtered = filtered.filter(review =>
        review.findings?.some(finding => finding.severity === filters.value.severity)
      );
    }

    // Apply type filter
    if (filters.value.type) {
      filtered = filtered.filter(review => review.type === filters.value.type);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      const { sortBy, sortOrder } = filters.value;
      let aVal = a[sortBy];
      let bVal = b[sortBy];

      if (sortBy === 'created' || sortBy === 'updated') {
        aVal = new Date(aVal);
        bVal = new Date(bVal);
      } else if (sortBy === 'severity') {
        // Sort by highest severity finding
        const severityMap = { critical: 4, high: 3, medium: 2, low: 1 };
        aVal = Math.max(...(a.findings?.map(f => severityMap[f.severity] || 0) || [0]));
        bVal = Math.max(...(b.findings?.map(f => severityMap[f.severity] || 0) || [0]));
      }

      if (sortOrder === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });

    return filtered;
  });

  const pendingReviews = computed(() =>
    reviews.value.filter(r => r.status === 'pending')
  );

  const inProgressReviews = computed(() =>
    reviews.value.filter(r => r.status === 'in_progress')
  );

  const completedReviews = computed(() =>
    reviews.value.filter(r => r.status === 'completed')
  );

  const criticalFindings = computed(() => {
    const findings = [];
    reviews.value.forEach(review => {
      if (review.findings) {
        findings.push(...review.findings.filter(f => f.severity === 'critical'));
      }
    });
    return findings;
  });

  const reviewStats = computed(() => {
    const stats = {
      total: reviews.value.length,
      pending: 0,
      in_progress: 0,
      completed: 0,
      failed: 0,
      avgScore: 0,
      findingsCounts: {
        critical: 0,
        high: 0,
        medium: 0,
        low: 0
      }
    };

    let totalScore = 0;
    let reviewsWithScore = 0;

    reviews.value.forEach(review => {
      stats[review.status]++;

      if (review.score !== undefined) {
        totalScore += review.score;
        reviewsWithScore++;
      }

      if (review.findings) {
        review.findings.forEach(finding => {
          if (stats.findingsCounts[finding.severity] !== undefined) {
            stats.findingsCounts[finding.severity]++;
          }
        });
      }
    });

    if (reviewsWithScore > 0) {
      stats.avgScore = Math.round(totalScore / reviewsWithScore);
    }

    return stats;
  });

  const hasReviews = computed(() => reviews.value.length > 0);
  const hasError = computed(() => !!error.value);

  // Actions
  const fetchReviews = async (params = {}) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await reviewAPI.getReviews(params);
      reviews.value = response.data.data || [];
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to fetch reviews';
      console.error('Error fetching reviews:', err);
    } finally {
      loading.value = false;
    }
  };

  const startReview = async (reviewData) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await reviewAPI.startReview(reviewData);
      const newReview = response.data;

      reviews.value.unshift(newReview);
      currentReview.value = newReview;

      return newReview;
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to start review';
      console.error('Error starting review:', err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const getReview = async (id) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await reviewAPI.getReview(id);
      currentReview.value = response.data;

      // Update in the list if it exists
      const index = reviews.value.findIndex(r => r.id === id);
      if (index !== -1) {
        reviews.value[index] = response.data;
      }

      return response.data;
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to get review';
      console.error('Error getting review:', err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const stopReview = async (id) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await reviewAPI.stopReview(id);
      const updatedReview = response.data;

      const index = reviews.value.findIndex(r => r.id === id);
      if (index !== -1) {
        reviews.value[index] = updatedReview;
      }

      if (currentReview.value?.id === id) {
        currentReview.value = updatedReview;
      }

      return updatedReview;
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to stop review';
      console.error('Error stopping review:', err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const deleteReview = async (id) => {
    loading.value = true;
    error.value = null;

    try {
      await reviewAPI.deleteReview(id);

      reviews.value = reviews.value.filter(r => r.id !== id);

      if (currentReview.value?.id === id) {
        currentReview.value = null;
      }

      return true;
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to delete review';
      console.error('Error deleting review:', err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const setCurrentReview = (review) => {
    currentReview.value = review;
  };

  const clearCurrentReview = () => {
    currentReview.value = null;
  };

  const applyFilters = (newFilters) => {
    filters.value = { ...filters.value, ...newFilters };
  };

  const resetFilters = () => {
    filters.value = {
      status: '',
      severity: '',
      type: '',
      sortBy: 'created',
      sortOrder: 'desc'
    };
  };

  const clearError = () => {
    error.value = null;
  };

  // Review analysis helpers
  const getReviewStatusColor = (status) => {
    const statusObj = reviewStatuses.value.find(s => s.id === status);
    return statusObj?.color || 'gray';
  };

  const getSeverityColor = (severity) => {
    const severityObj = severityLevels.value.find(s => s.id === severity);
    return severityObj?.color || 'gray';
  };

  const calculateHealthScore = (review) => {
    if (!review.findings || review.findings.length === 0) {
      return 100;
    }

    const severityWeights = { critical: 25, high: 10, medium: 5, low: 1 };
    let totalDeduction = 0;

    review.findings.forEach(finding => {
      totalDeduction += severityWeights[finding.severity] || 0;
    });

    return Math.max(0, 100 - totalDeduction);
  };

  const getRecommendations = (review) => {
    if (!review.findings || review.findings.length === 0) {
      return [];
    }

    const recommendations = [];
    const findingsBySeverity = {};

    // Group findings by severity
    review.findings.forEach(finding => {
      if (!findingsBySeverity[finding.severity]) {
        findingsBySeverity[finding.severity] = [];
      }
      findingsBySeverity[finding.severity].push(finding);
    });

    // Generate recommendations based on findings
    if (findingsBySeverity.critical?.length > 0) {
      recommendations.push({
        priority: 'critical',
        action: 'Address critical security vulnerabilities immediately',
        count: findingsBySeverity.critical.length
      });
    }

    if (findingsBySeverity.high?.length > 0) {
      recommendations.push({
        priority: 'high',
        action: 'Fix high-priority issues within 24 hours',
        count: findingsBySeverity.high.length
      });
    }

    if (findingsBySeverity.medium?.length > 5) {
      recommendations.push({
        priority: 'medium',
        action: 'Consider refactoring to address multiple medium-priority issues',
        count: findingsBySeverity.medium.length
      });
    }

    return recommendations;
  };

  // Export/import functionality
  const exportReview = (review) => {
    const exportData = {
      id: review.id,
      type: review.type,
      status: review.status,
      score: review.score,
      findings: review.findings,
      metadata: review.metadata,
      createdAt: review.createdAt,
      completedAt: review.completedAt,
      exportedAt: new Date().toISOString()
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json'
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `review-${review.id}-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Reset store
  const $reset = () => {
    reviews.value = [];
    currentReview.value = null;
    loading.value = false;
    error.value = null;
    filters.value = {
      status: '',
      severity: '',
      type: '',
      sortBy: 'created',
      sortOrder: 'desc'
    };
  };

  return {
    // State
    reviews,
    currentReview,
    loading,
    error,
    filters,
    reviewTypes,
    severityLevels,
    reviewStatuses,

    // Computed
    filteredReviews,
    pendingReviews,
    inProgressReviews,
    completedReviews,
    criticalFindings,
    reviewStats,
    hasReviews,
    hasError,

    // Actions
    fetchReviews,
    startReview,
    getReview,
    stopReview,
    deleteReview,
    setCurrentReview,
    clearCurrentReview,
    applyFilters,
    resetFilters,
    clearError,
    getReviewStatusColor,
    getSeverityColor,
    calculateHealthScore,
    getRecommendations,
    exportReview,
    $reset
  };
}, {
  persist: {
    enabled: true,
    strategies: [
      {
        key: 'review',
        storage: sessionStorage,
        paths: ['filters']
      }
    ]
  }
});
