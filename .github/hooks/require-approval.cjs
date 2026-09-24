let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => (input += chunk));
process.stdin.on('end', () => {
  const event = JSON.parse(input);
  const decision = event.tool_name === process.env.SENSITIVE_TOOL_NAME
    ? { hookSpecificOutput: {
          hookEventName: 'PreToolUse',
          permissionDecision: 'ask',
          permissionDecisionReason: '该工具需人工确认。' } }
    : { continue: true };
  process.stdout.write(JSON.stringify(decision));
});
