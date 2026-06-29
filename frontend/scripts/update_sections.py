import os
import glob
import re

components_dir = r"c:\Users\froxt\Downloads\jomveo\frontend\src\components"
sections = glob.glob(os.path.join(components_dir, "*Section.jsx"))

for path in sections:
    if "HeroSection" in path:
        continue
    
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Import JobProgress
    if "import JobProgress" not in content:
        content = 'import JobProgress from "./JobProgress";\n' + content

    # Props
    content = re.sub(r'  loading,', '  job,\n  onCancel,\n  sceneJob,\n  onSceneCancel,', content)
    
    # Replace loading usage in buttons (some have loading, some might have sceneLoading)
    content = re.sub(r'disabled=\{loading\}', 'disabled={!!job}', content)
    content = re.sub(r'loading \? "[^"]*" : ', 'job ? "Working..." : ', content)

    content = re.sub(r'disabled=\{sceneLoading\}', 'disabled={!!sceneJob}', content)
    content = re.sub(r'sceneLoading \? "[^"]*" : ', 'sceneJob ? "Working..." : ', content)

    # Result panel injection
    # We want to replace `{result ? (` with `{job ? <JobProgress job={job} onCancel={onCancel} /> : result ? (`
    # We also need to handle sceneResult.
    
    if "ArtStyleSection" in path:
        # Custom logic for ArtStyleSection since it has two results
        content = content.replace('{sceneResult ? (', '{sceneJob ? <JobProgress job={sceneJob} onCancel={onSceneCancel} /> : sceneResult ? (')
        content = content.replace('{result ? (', '{job ? <JobProgress job={job} onCancel={onCancel} /> : result ? (')
    else:
        content = content.replace('{result ? (', '{job ? <JobProgress job={job} onCancel={onCancel} /> : result ? (')
        
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

print("Update sections completed.")
