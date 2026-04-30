---
name: keep-todos
description: 'Complete any TODO, task, or feature request by implementing code changes end-to-end. Use when: implementing tasks from TASK_LIST.md, fixing TODOs in code, completing features, or handling multi-file edits. Default to keeping all generated code—never ask for manual Keep clicks.'
argument-hint: 'Describe the task, file path, or feature to implement'
user-invocable: true
---

# Keep Todos: Task-to-Code Automation

## When to Use This Skill

✓ **Use this skill when**:
- You have a TODO or task from a list (e.g., TASK_LIST.md, NEXT_100_TASKS.md)
- You're implementing a feature or fixing a code issue
- You need to edit multiple files efficiently
- You want to complete work and immediately recommend **Keep** (no manual approval needed)

✗ **Don't use this skill for**:
- Architecture planning or design discussion
- Code review or feedback (no changes yet)
- Debugging runtime errors (use error-specific skills instead)
- Questions that don't require code changes

## Core Philosophy

1. **Proactive Implementation**: Read the task, understand requirements, execute fully
2. **DRY & Clean Code**: Use shared base classes, avoid redundancy, follow workspace conventions
3. **Batch Efficient Edits**: Use `multi_replace_string_in_file` for multiple changes
4. **Track Progress**: Update `manage_todo_list` after each substantial step
5. **Recommend Keep**: Always conclude with "Ready to Keep all changes" — don't ask for approval

## Step-by-Step Procedure

### 1. Understand the Task
- Read the TODO or task description from the user
- Check related files, tests, or documentation
- Identify all files that need changes
- Note any constraints (DRY principles, naming conventions, dependencies)

**Example**:
```
Task: "Add performance profiler to planes.html with FPS tracking"
→ Check planes.html structure
→ Review existing renderer code
→ Note: Must integrate with existing air_service.js
```

### 2. Plan the Implementation
- Break task into logical steps (schema → core logic → UI integration → tests)
- Identify which files change and in what order
- Determine if new files are needed or edits to existing ones
- Estimate scope (simple edit vs. multi-file refactor)

**Example**:
```
Plan:
  1. Create performance_profiler.js with PerformanceProfiler class
  2. Update planes.html to import and initialize profiler
  3. Add profiler.startFrame()/endFrame() hooks in renderer loop
  4. Add test case in smoke_test_planes.py
```

### 3. Implement with Efficiency
- Create all new files in one pass (use `create_file` sequentially if dependent)
- Batch multi-file edits into one `multi_replace_string_in_file` call
- Use 3-5 lines of context before/after changes to ensure unambiguous matching
- Keep code modular and DRY (share base classes, avoid copy-paste)

**Tools to use**:
- `create_file` for new files
- `multi_replace_string_in_file` for 2+ edits (more efficient than sequential calls)
- `replace_string_in_file` for single edits only if necessary
- `read_file` to gather context before editing

### 4. Track Progress
- Use `manage_todo_list` to mark task steps as in-progress/completed
- Update after each logical milestone (e.g., "Created 3 renderer files", "Integrated UI")
- Only mark a task complete when tests pass or integration verified

**Example**:
```
manage_todo_list:
  - { id: 5, title: "Add performance profiler to planes.html", status: "in-progress" }
  # After file creation
  - { id: 5, title: "Add performance profiler to planes.html", status: "in-progress" }
  # After HTML integration
  - { id: 5, title: "Add performance profiler to planes.html", status: "completed" }
```

### 5. Verify & Summarize
- Read back one critical file to ensure edits applied correctly
- Check imports and cross-file references
- Summarize what files were changed and why
- **Always conclude with**: "Ready to Keep all changes"

**Example summary**:
```
✓ Created performance_profiler.js (220 LOC)
✓ Updated planes.html with profiler initialization and metrics display
✓ Added test case for frame timing in smoke_test_planes.py
Ready to Keep all changes
```

## Best Practices

### Code Quality
- **DRY Principle**: Shared base classes before copy-paste (see `renderers/base.js` pattern)
- **Naming**: Follow workspace conventions (e.g., `air_` prefix for flight system, `cc-` CSS prefix)
- **Type Safety**: Use dataclasses/TypeScript/JSDoc where applicable
- **Error Handling**: Include graceful fallback and recovery logic

### Efficiency
- **Batch edits**: Use `multi_replace_string_in_file` for 2+ unrelated changes
- **Parallel reads**: Read multiple files in one `read_file` call with large ranges
- **Avoid loops**: Don't call `replace_string_in_file` multiple times in a loop; batch them

### Testing
- Add unit tests for new modules (`tests/test_*.py`)
- Add smoke test scenario for integration (`scripts/smoke_test_*.py`)
- Run validation hook if available

### Documentation
- Update TASK_LIST.md or TODO.md to reflect completion
- Link new functions to related documentation
- Leave comments in complex logic

## Workspace Conventions (Jarvis Project)

### Backend (Python)
- Location: `jarvis/*.py` or `jarvis/<module>/*.py`
- Naming: `snake_case` for files, classes, functions
- Schema: Use `dataclasses` with `@dataclass` decorator
- Exports: Provide clear `__all__` list or module-level examples

### Frontend (JavaScript)
- Location: `jarvis/web/command_center/<feature>/` or `jarvis/web/hud/<feature>/`
- Format: ES6 modules imported from `https://esm.sh` (no bundler, no npm)
- Naming: `camelCase` for files/functions, `PascalCase` for classes
- Exports: Use `export default class` or named exports

### CSS
- Naming: `.cc-*` prefix for command center, `.hud-*` for HUD views
- No Tailwind, no framework — plain CSS with custom properties
- Animation: Use CSS keyframes, not JavaScript transitions

### Tests
- Python: `tests/test_<module>.py` with `pytest` conventions
- JavaScript: Smoke tests in `scripts/smoke_test_*.py` (integration tests)
- Coverage: Aim for 80%+ coverage of new code

### Docs
- Runbooks: `docs/runbooks/<feature>.md` (operational guides)
- Checklists: `docs/<FEATURE>_CHECKLIST.md` (production readiness)
- Architecture: `docs/ARCHITECTURE.md` or feature-specific `.md` files

## Example Invocation

**User**: "Complete the task in TASK_LIST.md #14: Add terrain toggle to mapbox renderer"

**Skill Execution**:
1. ✓ Read TASK_LIST.md and identify task #14
2. ✓ Check mapbox.js to understand current structure
3. ✓ Plan: Add `toggleTerrain()` method, add UI button, add test
4. ✓ Create terrain toggle in mapbox.js (DRY with base class pattern)
5. ✓ Update planes.html UI to show terrain button
6. ✓ Update smoke_test_planes.py with terrain toggle test
7. ✓ Mark task #14 complete in manage_todo_list
8. ✓ Verify edits, summarize changes
9. ✓ **Ready to Keep all changes**

## Reference: File Templates

### Python Module Template
```python
"""Brief module description."""

from dataclasses import dataclass
from typing import Optional

@dataclass
class MyClass:
    """Docstring describing the class."""
    field1: str
    field2: Optional[int] = None

def my_function(arg: str) -> dict:
    """Docstring describing the function."""
    return {"result": arg}

__all__ = ["MyClass", "my_function"]
```

### JavaScript Module Template
```javascript
/**
 * Brief module description.
 */

export class MyClass {
  constructor(options = {}) {
    this.config = options;
  }

  method() {
    return "result";
  }
}

export default MyClass;
```

### Test Template (pytest)
```python
import pytest
from module import MyClass

class TestMyClass:
    def test_init(self):
        obj = MyClass()
        assert obj is not None

    def test_method(self):
        obj = MyClass()
        result = obj.method()
        assert result == "expected"
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Import not found | Check that new file is created before dependent imports; verify `__all__` exports |
| Edits didn't apply | Verify the context strings (3-5 lines before/after) match exactly; check whitespace |
| Performance degradation | Use culling/pagination for large datasets; profile with PerformanceProfiler |
| Tests fail after changes | Run `python scripts/smoke_test_*.py` to validate integration; check error logs |

## Success Criteria

✓ **Task is complete when**:
- [ ] All code files created/edited without errors
- [ ] Tests pass (unit + smoke tests)
- [ ] No console errors in browser (if frontend change)
- [ ] TASK_LIST.md or TODO.md updated to reflect completion
- [ ] Summary provided and "Ready to Keep" stated

---

**Last Updated**: 2026-04-30  
**Used by**: JarvisEngineer agent (auto-activate on task/todo/implementation requests)  
**Related Skills**: `address-pr-comments`, `create-pull-request`
