#!/usr/bin/env node

/**
 * Module 1: Core Infrastructure - Performance Benchmark Runner
 * 
 * Usage: npx ts-node src/cli/core/performance/run-benchmarks.ts [--verbose]
 */

import { runBenchmarks } from './benchmarks';

async function main() {
  const verbose = process.argv.includes('--verbose');
  
  try {
    const allPassed = await runBenchmarks(verbose);
    process.exit(allPassed ? 0 : 1);
  } catch (error) {
    console.error('Benchmark runner failed:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}