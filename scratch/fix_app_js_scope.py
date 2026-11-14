with open('web/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

marker = '// Milestone 13E: Atlas Joint Mission Co-Design Studio & 3D Theater Integration'
if marker in content:
    parts = content.split('// ==============================================================================\n' + marker)
    before_joint = parts[0]
    joint_code = '// ==============================================================================\n' + marker + parts[1]

    # Find the closing })();
    iife_close = '\n})();'
    if iife_close in before_joint:
        subparts = before_joint.split(iife_close)
        # Put joint_code right before iife_close
        fixed_content = subparts[0] + '\n\n' + joint_code.strip() + '\n\n})();' + iife_close.join(subparts[1:])
        with open('web/app.js', 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        print("Successfully moved Milestone 13E code inside IIFE!")
    else:
        print("ERROR: iife_close not found in before_joint!")
else:
    print("ERROR: marker not found!")
