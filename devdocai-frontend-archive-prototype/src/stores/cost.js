import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { useNotificationStore } from './notification';

export const useCostStore = defineStore('cost', () => {
  // State
  const currentCosts = ref({
    daily: 0,
    weekly: 0,
    monthly: 0,
    total: 0
  });

  const budgets = ref({
    daily: 10.0,    // $10 daily budget (M008 default)
    weekly: 50.0,   // $50 weekly budget
    monthly: 200.0  // $200 monthly budget
  });

  const alerts = ref({
    enabled: true,
    thresholds: {
      warning: 0.75,  // 75% of budget
      critical: 0.90  // 90% of budget
    },
    triggered: {
      daily: { warning: false, critical: false },
      weekly: { warning: false, critical: false },
      monthly: { warning: false, critical: false }
    }
  });

  const transactions = ref([]);
  const providers = ref([
    { id: 'openai', name: 'OpenAI', enabled: true },
    { id: 'anthropic', name: 'Anthropic', enabled: true },
    { id: 'gemini', name: 'Google Gemini', enabled: true },
    { id: 'local', name: 'Local Model', enabled: true, cost: 0 }
  ]);

  const isLoading = ref(false);
  const error = ref(null);

  // Provider costs (per 1K tokens - approximate)
  const providerCosts = ref({
    openai: {
      'gpt-4': { input: 0.03, output: 0.06 },
      'gpt-4-turbo': { input: 0.01, output: 0.03 },
      'gpt-3.5-turbo': { input: 0.0015, output: 0.002 }
    },
    anthropic: {
      'claude-3-opus': { input: 0.015, output: 0.075 },
      'claude-3-sonnet': { input: 0.003, output: 0.015 },
      'claude-3-haiku': { input: 0.00025, output: 0.00125 }
    },
    gemini: {
      'gemini-pro': { input: 0.00025, output: 0.0005 },
      'gemini-pro-vision': { input: 0.00025, output: 0.0005 }
    },
    local: {
      'local-model': { input: 0, output: 0 }
    }
  });

  // Real-time cost tracking
  const realTimeUsage = ref({
    session: 0,
    documents: 0,
    enhances: 0,
    reviews: 0
  });

  // Cost statistics
  const costStats = ref({
    averagePerDocument: 0,
    totalDocuments: 0,
    mostExpensiveOperation: null,
    costTrends: []
  });

  // Computed
  const budgetUsage = computed(() => ({
    daily: currentCosts.value.daily / budgets.value.daily,
    weekly: currentCosts.value.weekly / budgets.value.weekly,
    monthly: currentCosts.value.monthly / budgets.value.monthly
  }));

  const budgetRemaining = computed(() => ({
    daily: Math.max(0, budgets.value.daily - currentCosts.value.daily),
    weekly: Math.max(0, budgets.value.weekly - currentCosts.value.weekly),
    monthly: Math.max(0, budgets.value.monthly - currentCosts.value.monthly)
  }));

  const budgetStatus = computed(() => {
    const usage = budgetUsage.value;
    const status = {};

    Object.keys(usage).forEach(period => {
      if (usage[period] >= alerts.value.thresholds.critical) {
        status[period] = 'critical';
      } else if (usage[period] >= alerts.value.thresholds.warning) {
        status[period] = 'warning';
      } else {
        status[period] = 'good';
      }
    });

    return status;
  });

  const canAffordOperation = computed(() => (estimatedCost) => {
    return budgetRemaining.value.daily >= estimatedCost;
  });

  const mostUsedProvider = computed(() => {
    const providerTotals = {};
    transactions.value.forEach(tx => {
      providerTotals[tx.provider] = (providerTotals[tx.provider] || 0) + tx.cost;
    });

    let maxProvider = null;
    let maxCost = 0;

    Object.entries(providerTotals).forEach(([provider, cost]) => {
      if (cost > maxCost) {
        maxCost = cost;
        maxProvider = provider;
      }
    });

    return maxProvider ? { provider: maxProvider, cost: maxCost } : null;
  });

  // Actions
  const trackTransaction = (transaction) => {
    const newTransaction = {
      id: Date.now() + Math.random(),
      timestamp: new Date().toISOString(),
      type: transaction.type, // 'generation', 'enhancement', 'review'
      provider: transaction.provider,
      model: transaction.model,
      tokensInput: transaction.tokensInput || 0,
      tokensOutput: transaction.tokensOutput || 0,
      cost: transaction.cost || 0,
      documentId: transaction.documentId,
      operation: transaction.operation
    };

    transactions.value.unshift(newTransaction);

    // Update current costs
    updateCurrentCosts(newTransaction.cost);

    // Update real-time usage
    realTimeUsage.value.session += newTransaction.cost;
    if (transaction.type === 'generation') {
      realTimeUsage.value.documents += newTransaction.cost;
    } else if (transaction.type === 'enhancement') {
      realTimeUsage.value.enhances += newTransaction.cost;
    } else if (transaction.type === 'review') {
      realTimeUsage.value.reviews += newTransaction.cost;
    }

    // Update cost statistics
    updateCostStats(newTransaction);

    // Check budget alerts
    checkBudgetAlerts();

    // Limit transaction history
    if (transactions.value.length > 1000) {
      transactions.value = transactions.value.slice(0, 1000);
    }

    return newTransaction.id;
  };

  const updateCurrentCosts = (cost) => {
    currentCosts.value.daily += cost;
    currentCosts.value.weekly += cost;
    currentCosts.value.monthly += cost;
    currentCosts.value.total += cost;
  };

  const updateCostStats = (transaction) => {
    costStats.value.totalDocuments++;

    const avgCost = currentCosts.value.total / costStats.value.totalDocuments;
    costStats.value.averagePerDocument = avgCost;

    if (!costStats.value.mostExpensiveOperation ||
        transaction.cost > costStats.value.mostExpensiveOperation.cost) {
      costStats.value.mostExpensiveOperation = transaction;
    }

    // Add to trends (keep last 30 days)
    const today = new Date().toISOString().split('T')[0];
    const existingTrend = costStats.value.costTrends.find(t => t.date === today);

    if (existingTrend) {
      existingTrend.cost += transaction.cost;
      existingTrend.operations++;
    } else {
      costStats.value.costTrends.push({
        date: today,
        cost: transaction.cost,
        operations: 1
      });
    }

    // Keep only last 30 days
    if (costStats.value.costTrends.length > 30) {
      costStats.value.costTrends = costStats.value.costTrends.slice(-30);
    }
  };

  const checkBudgetAlerts = () => {
    if (!alerts.value.enabled) return;

    const notificationStore = useNotificationStore();
    const usage = budgetUsage.value;
    const thresholds = alerts.value.thresholds;

    Object.keys(usage).forEach(period => {
      const usagePercent = usage[period];
      const triggered = alerts.value.triggered[period];

      // Critical alert (90%+)
      if (usagePercent >= thresholds.critical && !triggered.critical) {
        alerts.value.triggered[period].critical = true;
        notificationStore.addError(
          `Critical: ${period.charAt(0).toUpperCase() + period.slice(1)} Budget Alert`,
          `You've used ${Math.round(usagePercent * 100)}% of your ${period} budget ($${budgets.value[period]}). Consider pausing AI operations.`,
          { persistent: true }
        );
      }
      // Warning alert (75%+)
      else if (usagePercent >= thresholds.warning && !triggered.warning) {
        alerts.value.triggered[period].warning = true;
        notificationStore.addWarning(
          `Warning: ${period.charAt(0).toUpperCase() + period.slice(1)} Budget Alert`,
          `You've used ${Math.round(usagePercent * 100)}% of your ${period} budget ($${budgets.value[period]}). Monitor usage carefully.`
        );
      }
    });
  };

  const estimateOperationCost = (provider, model, inputTokens, outputTokens) => {
    const costs = providerCosts.value[provider]?.[model];
    if (!costs) return 0;

    const inputCost = (inputTokens / 1000) * costs.input;
    const outputCost = (outputTokens / 1000) * costs.output;

    return inputCost + outputCost;
  };

  const updateBudget = (period, amount) => {
    if (budgets.value[period] !== undefined) {
      budgets.value[period] = amount;

      // Reset alerts for this period
      alerts.value.triggered[period] = { warning: false, critical: false };
    }
  };

  const updateAlertSettings = (settings) => {
    alerts.value = { ...alerts.value, ...settings };
  };

  const resetDailyCosts = () => {
    currentCosts.value.daily = 0;
    realTimeUsage.value.session = 0;

    // Reset daily alerts
    alerts.value.triggered.daily = { warning: false, critical: false };
  };

  const resetWeeklyCosts = () => {
    currentCosts.value.weekly = 0;

    // Reset weekly alerts
    alerts.value.triggered.weekly = { warning: false, critical: false };
  };

  const resetMonthlyCosts = () => {
    currentCosts.value.monthly = 0;

    // Reset monthly alerts
    alerts.value.triggered.monthly = { warning: false, critical: false };
  };

  const exportCostData = () => {
    const exportData = {
      costs: currentCosts.value,
      budgets: budgets.value,
      transactions: transactions.value.slice(0, 100), // Last 100 transactions
      stats: costStats.value,
      exportDate: new Date().toISOString()
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json'
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `devdocai-costs-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const clearError = () => {
    error.value = null;
  };

  // Initialize with realistic demo data for development
  const initializeDemoData = () => {
    // Add some sample transactions
    const demoTransactions = [
      {
        type: 'generation',
        provider: 'openai',
        model: 'gpt-4',
        tokensInput: 500,
        tokensOutput: 1000,
        cost: 0.075,
        documentId: 'doc-1',
        operation: 'README generation'
      },
      {
        type: 'enhancement',
        provider: 'anthropic',
        model: 'claude-3-sonnet',
        tokensInput: 800,
        tokensOutput: 600,
        cost: 0.0114,
        documentId: 'doc-1',
        operation: 'MIAIR enhancement'
      },
      {
        type: 'review',
        provider: 'gemini',
        model: 'gemini-pro',
        tokensInput: 1200,
        tokensOutput: 400,
        cost: 0.0005,
        documentId: 'doc-2',
        operation: 'Quality review'
      }
    ];

    demoTransactions.forEach(tx => trackTransaction(tx));
  };

  // Reset store
  const $reset = () => {
    currentCosts.value = { daily: 0, weekly: 0, monthly: 0, total: 0 };
    budgets.value = { daily: 10.0, weekly: 50.0, monthly: 200.0 };
    alerts.value = {
      enabled: true,
      thresholds: { warning: 0.75, critical: 0.90 },
      triggered: {
        daily: { warning: false, critical: false },
        weekly: { warning: false, critical: false },
        monthly: { warning: false, critical: false }
      }
    };
    transactions.value = [];
    realTimeUsage.value = { session: 0, documents: 0, enhances: 0, reviews: 0 };
    costStats.value = {
      averagePerDocument: 0,
      totalDocuments: 0,
      mostExpensiveOperation: null,
      costTrends: []
    };
    isLoading.value = false;
    error.value = null;
  };

  return {
    // State
    currentCosts,
    budgets,
    alerts,
    transactions,
    providers,
    providerCosts,
    realTimeUsage,
    costStats,
    isLoading,
    error,

    // Computed
    budgetUsage,
    budgetRemaining,
    budgetStatus,
    canAffordOperation,
    mostUsedProvider,

    // Actions
    trackTransaction,
    updateCurrentCosts,
    updateCostStats,
    checkBudgetAlerts,
    estimateOperationCost,
    updateBudget,
    updateAlertSettings,
    resetDailyCosts,
    resetWeeklyCosts,
    resetMonthlyCosts,
    exportCostData,
    clearError,
    initializeDemoData,
    $reset
  };
}, {
  persist: {
    enabled: true,
    strategies: [
      {
        key: 'cost',
        storage: localStorage,
        paths: [
          'currentCosts',
          'budgets',
          'alerts',
          'transactions',
          'realTimeUsage',
          'costStats'
        ]
      }
    ]
  }
});