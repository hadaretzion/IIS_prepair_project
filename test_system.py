"""Quick test script to check what works and what doesn't in PrepAIr."""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("PrepAIr System Test")
print("=" * 60)

# Test 1: Check Python environment
print("\n1. Checking Python environment...")
try:
    import sys
    print(f"   ✓ Python version: {sys.version.split()[0]}")
except Exception as e:
    print(f"   ✗ Python check failed: {e}")

# Test 2: Check backend dependencies
print("\n2. Checking backend dependencies...")
deps = {
    'fastapi': 'FastAPI',
    'uvicorn': 'Uvicorn',
    'sqlmodel': 'SQLModel',
    'pydantic': 'Pydantic',
    'google.generativeai': 'Google Generative AI',
    'dotenv': 'python-dotenv'
}

missing_deps = []
for module, name in deps.items():
    try:
        __import__(module)
        print(f"   ✓ {name}")
    except ImportError:
        print(f"   ✗ {name} - NOT INSTALLED")
        missing_deps.append(name)

# Test 3: Check database
print("\n3. Checking database...")
try:
    from backend.db import engine, init_db
    from backend.models import User, QuestionBank
    from sqlmodel import Session, select
    
    init_db()
    print("   ✓ Database initialized")
    
    with Session(engine) as session:
        user_count = len(list(session.exec(select(User)).all()))
        question_count = len(list(session.exec(select(QuestionBank)).all()))
        print(f"   ✓ Users in DB: {user_count}")
        print(f"   ✓ Questions in DB: {question_count}")
        if question_count == 0:
            print("   ⚠️  WARNING: Question bank is empty! Run: python -m backend.services.ingest")
except Exception as e:
    print(f"   ✗ Database check failed: {e}")

# Test 4: Check backend imports
print("\n4. Checking backend imports...")
backend_modules = [
    'backend.main',
    'backend.db',
    'backend.models',
    'backend.schemas',
    'backend.routers.users',
    'backend.routers.cv',
    'backend.routers.jd',
    'backend.routers.interview',
    'backend.routers.progress',
    'backend.services.gemini_client',
    'backend.services.role_profile',
    'backend.services.selection',
    'backend.services.scoring',
    'backend.services.readiness',
]

failed_imports = []
for module in backend_modules:
    try:
        __import__(module)
        print(f"   ✓ {module}")
    except Exception as e:
        print(f"   ✗ {module} - {str(e)[:50]}")
        failed_imports.append(module)

# Test 5: Check API key configuration
print("\n5. Checking API key configuration...")
try:
    from backend.services.gemini_client import get_gemini_api_key
    api_key = get_gemini_api_key()
    if api_key:
        print(f"   ✓ API key found (length: {len(api_key)})")
    else:
        print("   ⚠️  API key not found (system will use fallbacks)")
except Exception as e:
    print(f"   ✗ API key check failed: {e}")

# Test 6: Check frontend dependencies (Node.js)
print("\n6. Checking frontend setup...")
package_json = project_root / "app" / "package.json"
if package_json.exists():
    print("   ✓ package.json exists")
else:
    print("   ✗ package.json not found")

node_modules = project_root / "app" / "node_modules"
if node_modules.exists():
    print("   ✓ node_modules exists")
else:
    print("   ⚠️  node_modules not found - Run: cd app && npm install")

# Test 7: Check data files
print("\n7. Checking data files...")
data_dir = project_root / "src" / "data" / "questions_and_answers"
if data_dir.exists():
    csv_files = list(data_dir.glob("*.csv"))
    print(f"   ✓ Data directory exists ({len(csv_files)} CSV files)")
    required_files = [
        "all_code_questions_with_topics.csv",
        "all_open_questions_with_topics.csv"
    ]
    for file in required_files:
        if (data_dir / file).exists():
            print(f"   ✓ {file}")
        else:
            print(f"   ✗ {file} - MISSING")
else:
    print("   ✗ Data directory not found")

# Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

issues = []
if missing_deps:
    issues.append(f"Missing Python dependencies: {', '.join(missing_deps)}")
if failed_imports:
    issues.append(f"Failed imports: {len(failed_imports)} modules")
if not node_modules.exists():
    issues.append("Frontend dependencies not installed")

if issues:
    print("⚠️  ISSUES FOUND:")
    for issue in issues:
        print(f"   - {issue}")
else:
    print("✓ All basic checks passed!")

print("\n" + "=" * 60)
print("KNOWN CODE ISSUES:")
print("=" * 60)
print("1. ✗ InterviewRoom.tsx: loadQuestion() is empty - first question won't load")
print("2. ✗ No file upload support - only text input")
print("3. ✗ FeedbackPlaceholder.tsx is just a placeholder")
print("4. ✗ User history view not implemented")
print("5. ✗ Exercises/reinforcement not implemented")
print("=" * 60)
