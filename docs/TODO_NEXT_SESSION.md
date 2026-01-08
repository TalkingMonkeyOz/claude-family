# Next Session TODO

**Last Updated**: 2026-01-08
**Last Session**: Playwright batch testing - Run 4 completion and final deliverables

---

## Completed This Session

- [x] Ran create_final_master_v2.py to update results with Run 4 data
- [x] Verified all 3 failures: 276099, 276669, 277019
- [x] Created FINAL_DELIVERABLES folder with organized output
- [x] Created DATA_ISSUES_TO_FIX.csv with 66 data issues (staff IDs + actions)
- [x] Archived obsolete intermediate files to archive_intermediate/
- [x] Created clear README.md for final deliverables

---

## Playwright Batch Testing - COMPLETED

**Location**: `C:\Projects\DRY_RUN_playwright\FINAL_DELIVERABLES\`

### Final Results (All 4 Runs)

| Outcome | Count | % |
|---------|-------|---|
| PASSED | 945 | 93.3% |
| ABORTED | 65 | 6.4% |
| FAILED | 3 | 0.3% |

### Key Files

- `FINAL_DELIVERABLES/ALL_SCHEDULES_RESULTS.csv` - Master results (1,013 schedules)
- `FINAL_DELIVERABLES/DATA_ISSUES_TO_FIX.csv` - 66 data issues with staff IDs
- `FINAL_DELIVERABLES/README.md` - Complete documentation

### 3 Failures (Technical)

| Schedule | Run | Cause |
|----------|-----|-------|
| 276099 | Run 3 | Server timeout |
| 276669 | Run 3 | Server timeout |
| 277019 | Run 4 | TelerikModalOverlay blocking |

### 65 Aborted (Data Issues)

- 31 job_role issues (staff needs Sessional role)
- 34 overlap_diff_schedule issues (schedule conflicts)

---

## Priority 1: Nimbus Data Fixes

The 65 aborted schedules need data fixes in Nimbus:

1. Use `DATA_ISSUES_TO_FIX.csv` to identify staff IDs
2. Assign Sessional role where missing
3. Resolve schedule overlaps

---

## Backlog

- [ ] Add rust.instructions.md to ~/.claude/instructions/
- [ ] Add azure.instructions.md (Bicep, Functions, Logic Apps)
- [ ] Implement forbidden_patterns in standards_validator.py
- [ ] Delete deprecated session_state.todo_list content
- [ ] Archive old todos (created_at > 30 days, status=pending)

---

## Key Learnings (This Session)

1. **Worker count matters** - 10 workers caused 137 server failures; 5 workers reduced to 2
2. **handleExistingWorkingCopyDialog()** - Added to handle orphaned working copies
3. **Data issues vs technical failures** - 65 aborted are data quality, not test issues
4. **Organize final deliverables** - Separate folder with clear README avoids confusion

---

**Version**: 15.0
**Created**: 2026-01-02
**Updated**: 2026-01-08
**Location**: docs/TODO_NEXT_SESSION.md
