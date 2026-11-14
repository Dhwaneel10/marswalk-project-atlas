with open('src/marswalk/core/mars_settlement_construction.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace all COMPLETED with NOT_STARTED except OP-01
parts = text.split('op_id="OP-01-SURVEY"')
header = parts[0] + 'op_id="OP-01-SURVEY"'
rest = parts[1]

# In rest, find where OP-02 starts
rest_parts = rest.split('op_id="OP-02-PAD-GRADING"')
op01_block = rest_parts[0]
remaining_ops = 'op_id="OP-02-PAD-GRADING"' + rest_parts[1]

remaining_ops_updated = remaining_ops.replace(
    'status=OperationStatus.COMPLETED,\n                progress_pct=100.0,',
    'status=OperationStatus.NOT_STARTED,\n                progress_pct=0.0,'
)

new_text = header + op01_block + remaining_ops_updated
with open('src/marswalk/core/mars_settlement_construction.py', 'w', encoding='utf-8') as f:
    f.write(new_text)

print("Updated OP-02 through OP-15 to NOT_STARTED successfully!")
