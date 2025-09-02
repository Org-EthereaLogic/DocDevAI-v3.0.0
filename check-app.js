const http = require('http');

console.log('Checking if DevDocAI app is rendering...\n');

// Make a request to the app
http.get('http://localhost:3000', (res) => {
  let data = '';
  
  res.on('data', (chunk) => {
    data += chunk;
  });
  
  res.on('end', () => {
    // Check if the HTML includes the necessary scripts
    const hasReactBundle = data.includes('main.bundle.js');
    const hasRuntimeBundle = data.includes('runtime.bundle.js');
    const hasRoot = data.includes('<div id="root">');
    
    console.log('Checking app status:');
    console.log('- HTML served: YES');
    console.log(`- React bundle included: ${hasReactBundle ? 'YES' : 'NO'}`);
    console.log(`- Runtime bundle included: ${hasRuntimeBundle ? 'YES' : 'NO'}`);
    console.log(`- Root element present: ${hasRoot ? 'YES' : 'NO'}`);
    
    if (hasReactBundle && hasRuntimeBundle && hasRoot) {
      console.log('\n✅ App infrastructure is working correctly!');
      console.log('The app should be rendering. If you see a white screen, check the browser console for JavaScript errors.');
    } else {
      console.log('\n❌ There might be issues with the app setup.');
    }
    
    // Extract title to see if it's the correct app
    const titleMatch = data.match(/<title>(.*?)<\/title>/);
    if (titleMatch) {
      console.log(`\nPage title: "${titleMatch[1]}"`);
    }
  });
}).on('error', (err) => {
  console.error('Error connecting to app:', err.message);
  console.log('Make sure the dev server is running (npm run dev:react)');
});