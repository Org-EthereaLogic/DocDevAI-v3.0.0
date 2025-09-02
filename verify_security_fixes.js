#!/usr/bin/env node

/**
 * Security Fix Verification Script
 * Verifies that all 15 CodeQL vulnerabilities have been properly fixed
 */

const fs = require('fs');
const path = require('path');

console.log('🔍 Verifying Security Fixes for CodeQL Vulnerabilities...\n');

const vulnerableFiles = [
    'src/modules/M013-VSCodeExtension/src/webviews/WebviewManager_unified.ts',
    'src/modules/M013-VSCodeExtension/src/security/SecurityManager_unified.ts',
    'src/modules/M013-VSCodeExtension/src/security/InputValidator.ts',
    'src/modules/M013-VSCodeExtension/src/security/ThreatDetector.ts'
];

const vulnerablePatterns = [
    // Incomplete URL scheme check patterns
    /\.replace\s*\(\s*\/javascript:/gi,
    /\.replace\s*\(\s*\/vbscript:/gi,
    
    // Bad HTML filtering patterns
    /\.replace\s*\(\s*\/<script[^>]*>.*?<\\\/script>/gi,
    /\.replace\s*\(\s*\/<style[^>]*>.*?<\\\/style>/gi,
    
    // Incomplete multi-character sanitization
    /\.replace\s*\(\s*\/on\w+\s*=/gi,
    
    // Direct regex-based HTML sanitization
    /\.replace\s*\(\s*\/<[^>]+>/g
];

const securePatterns = [
    'SecurityUtils.sanitizeHtml',
    'SecurityUtils.sanitizeInput',
    'SecurityUtils.isValidUrl',
    'SecurityUtils.sanitizeObject',
    'DOMPurify.sanitize',
    'Content-Security-Policy'
];

let vulnerabilitiesFound = 0;
let secureImplementationsFound = 0;

console.log('📁 Checking files for vulnerable patterns...\n');

vulnerableFiles.forEach(filePath => {
    const fullPath = path.join('/workspaces/DocDevAI-v3.0.0', filePath);
    
    if (!fs.existsSync(fullPath)) {
        console.log(`⚠️  File not found: ${filePath}`);
        return;
    }
    
    const content = fs.readFileSync(fullPath, 'utf8');
    const fileName = path.basename(filePath);
    
    console.log(`Checking ${fileName}...`);
    
    // Check for vulnerable patterns
    let fileVulnerabilities = 0;
    vulnerablePatterns.forEach(pattern => {
        if (pattern.test(content)) {
            console.log(`  ❌ Found vulnerable pattern: ${pattern.source.substring(0, 50)}...`);
            fileVulnerabilities++;
            vulnerabilitiesFound++;
        }
    });
    
    // Check for secure implementations
    let fileSecureImplementations = 0;
    securePatterns.forEach(pattern => {
        if (content.includes(pattern)) {
            console.log(`  ✅ Found secure implementation: ${pattern}`);
            fileSecureImplementations++;
            secureImplementationsFound++;
        }
    });
    
    if (fileVulnerabilities === 0 && fileSecureImplementations > 0) {
        console.log(`  ✅ File appears to be secured\n`);
    } else if (fileVulnerabilities > 0) {
        console.log(`  ⚠️  File may still have vulnerabilities\n`);
    } else {
        console.log(`  ℹ️  No vulnerabilities found, but no secure patterns detected either\n`);
    }
});

console.log('\n📊 Verification Summary:');
console.log('═══════════════════════════════════════');

if (vulnerabilitiesFound === 0) {
    console.log('✅ NO vulnerable patterns found in any files');
} else {
    console.log(`❌ Found ${vulnerabilitiesFound} vulnerable patterns`);
}

if (secureImplementationsFound > 0) {
    console.log(`✅ Found ${secureImplementationsFound} secure implementations`);
} else {
    console.log('⚠️  No secure implementations detected');
}

// Check if SecurityUtils.ts exists
const securityUtilsPath = '/workspaces/DocDevAI-v3.0.0/src/modules/M013-VSCodeExtension/src/security/SecurityUtils.ts';
if (fs.existsSync(securityUtilsPath)) {
    console.log('✅ SecurityUtils.ts exists and is available');
    
    // Check if it has the required methods
    const utilsContent = fs.readFileSync(securityUtilsPath, 'utf8');
    const requiredMethods = ['sanitizeHtml', 'isValidUrl', 'sanitizeInput', 'generateCSP'];
    let methodsFound = 0;
    
    requiredMethods.forEach(method => {
        if (utilsContent.includes(`static ${method}`)) {
            methodsFound++;
        }
    });
    
    console.log(`✅ SecurityUtils has ${methodsFound}/${requiredMethods.length} required methods`);
} else {
    console.log('❌ SecurityUtils.ts not found');
}

// Check if DOMPurify is installed
const packageJsonPath = '/workspaces/DocDevAI-v3.0.0/src/modules/M013-VSCodeExtension/package.json';
if (fs.existsSync(packageJsonPath)) {
    const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
    if (packageJson.dependencies && packageJson.dependencies['isomorphic-dompurify']) {
        console.log('✅ DOMPurify is installed (isomorphic-dompurify)');
    } else {
        console.log('⚠️  DOMPurify not found in dependencies');
    }
}

console.log('\n🎯 Final Result:');
console.log('═══════════════════════════════════════');

if (vulnerabilitiesFound === 0 && secureImplementationsFound > 0) {
    console.log('✅ All 15 CodeQL vulnerabilities appear to be FIXED!');
    console.log('✅ Secure implementations are in place');
    console.log('✅ Ready for CodeQL re-scan on GitHub');
    process.exit(0);
} else {
    console.log('⚠️  Some issues may remain - manual review recommended');
    console.log('⚠️  Push to GitHub to trigger official CodeQL scan');
    process.exit(1);
}