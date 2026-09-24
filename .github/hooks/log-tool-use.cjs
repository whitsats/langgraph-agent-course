const fs = require('node:fs');
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => (input += chunk));
process.stdin.on('end', () => {
  const event = JSON.parse(input);
  fs.appendFileSync('.github/hooks/tool-use.log',
    `${event.timestamp} ${event.tool_name}\n`);
});
