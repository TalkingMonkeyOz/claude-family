import React, { useState } from 'react';
import { ChevronDown, ChevronRight, CheckCircle, Circle, FileText, Database, Code, Layout, ClipboardCheck, MessageSquare, AlertTriangle } from 'lucide-react';

const phases = [
  {
    id: 1,
    title: "Initial Document Review",
    icon: FileText,
    steps: [
      {
        id: "1.1",
        title: "Load Existing Documentation",
        description: "Provide Claude with all relevant materials",
        checklist: [
          "Draft PID or requirements document",
          "API docs, database schemas",
          "Sample data files (Excel, CSV)",
          "Screenshots of relevant UI/systems"
        ],
        prompt: null
      },
      {
        id: "1.2",
        title: "Request Systematic Gap Analysis",
        description: "Ask Claude to identify all gaps and issues",
        checklist: [],
        prompt: `Review this document systematically and identify:
1. Validation gaps - logic that hasn't been tested or confirmed
2. Field mapping errors - incorrect table/column references
3. Missing workflow steps - gaps in the process flow
4. Undefined application design elements
5. Assumptions that need verification

For each gap, explain what the issue is, why it matters, and what information is needed to resolve it.`
      },
      {
        id: "1.3",
        title: "Compile Questions",
        description: "Claude produces numbered questions grouped by topic",
        checklist: [
          "Questions are specific and actionable",
          "Grouped by topic (validation, design, data flow)",
          "Prioritized (critical blockers vs nice-to-have)"
        ],
        prompt: null
      }
    ]
  },
  {
    id: 2,
    title: "Question Resolution",
    icon: MessageSquare,
    steps: [
      {
        id: "2.1",
        title: "Answer Questions with Evidence",
        description: "Provide real data, not assumptions",
        checklist: [
          "Direct answers where possible",
          "SQL query results for data questions",
          "Screenshots for UI behavior",
          "Swagger/API specs for endpoints",
          "Sample files showing actual format"
        ],
        prompt: `Here's real data from [source]:
[paste SQL results or data]

Map this to what the document says and correct any discrepancies.`
      },
      {
        id: "2.2",
        title: "Validate with Real Data",
        description: "Verify assumptions against actual system",
        checklist: [
          "Database schema → actual table structure",
          "API endpoints → Swagger/OpenAPI spec",
          "Data patterns → sample records",
          "UI workflow → screenshots"
        ],
        prompt: null
      },
      {
        id: "2.3",
        title: "Iterative Refinement",
        description: "Repeat until no gaps remain",
        checklist: [
          "Claude updates document after each answer batch",
          "New questions from answers identified",
          "Continue until all gaps resolved"
        ],
        prompt: null
      }
    ]
  },
  {
    id: 3,
    title: "Technical Validation",
    icon: Database,
    steps: [
      {
        id: "3.1",
        title: "Data Flow Verification",
        description: "Verify each data transformation",
        checklist: [
          "Source field exists with expected format",
          "Target field/table exists",
          "Lookup/cache has required data",
          "Edge cases handled (nulls, duplicates)"
        ],
        prompt: null
      },
      {
        id: "3.2",
        title: "API/Database Verification",
        description: "Confirm all integration points",
        checklist: [
          "Endpoint confirmed in Swagger",
          "Request payload structure validated",
          "Response handling defined",
          "Error scenarios documented"
        ],
        prompt: `Check Swagger for [endpoint]. Confirm:
- Exact endpoint path
- Request payload structure
- Required vs optional fields
- Response format`
      },
      {
        id: "3.3",
        title: "Insert/Update Pattern Verification",
        description: "Validate database operations",
        checklist: [
          "Correct table and column names",
          "Foreign key relationships understood",
          "Required fields identified",
          "Default values/placeholders documented"
        ],
        prompt: null
      }
    ]
  },
  {
    id: 4,
    title: "Application Design",
    icon: Layout,
    steps: [
      {
        id: "4.1",
        title: "Define User Interface",
        description: "Specify screens and workflow",
        checklist: [
          "Screens/steps needed",
          "Data displayed at each step",
          "User actions available",
          "Navigation between steps",
          "Error display approach"
        ],
        prompt: `Based on the workflow, define the application UI:
1. What screens/steps are needed?
2. What data is displayed at each step?
3. What user actions are available?
4. How does the user navigate between steps?
5. How are errors displayed?`
      },
      {
        id: "4.2",
        title: "Define Data Management",
        description: "Specify storage and caching",
        checklist: [
          "Connection/credential storage",
          "Cache building and refresh",
          "Session persistence (resume capability)",
          "Export formats for errors/reports"
        ],
        prompt: null
      },
      {
        id: "4.3",
        title: "Define Logging & Debugging",
        description: "Specify audit and troubleshooting",
        checklist: [
          "What gets logged (payloads, SQL, responses)",
          "Log format and storage",
          "Failure capture and export",
          "Audit trail requirements"
        ],
        prompt: `Define logging requirements:
- Process records ONE AT A TIME, waiting for each to complete
- Log all outbound payloads and SQL for debugging
- Capture failures with full context for review`
      }
    ]
  },
  {
    id: 5,
    title: "Final Review",
    icon: ClipboardCheck,
    steps: [
      {
        id: "5.1",
        title: "End-to-End Walkthrough",
        description: "Trace complete process flow",
        checklist: [
          "All required data available at each step",
          "All lookups will succeed (caches populated)",
          "All validations in place",
          "Error handling defined"
        ],
        prompt: `Walk through the complete process from start to finish:
1. User opens app
2. [Each step in sequence]
3. Import complete

For each step, verify all data, lookups, validations, and error handling.`
      },
      {
        id: "5.2",
        title: "Checklist Validation",
        description: "Final completeness check",
        checklist: [
          "Entity creation order documented",
          "Field mappings verified against schema",
          "API endpoints confirmed",
          "SQL patterns correct (inc. placeholders)",
          "All caches defined with queries",
          "Validation rules specified",
          "Error scenarios handled",
          "UI workflow complete",
          "Logging/debugging complete"
        ],
        prompt: null
      },
      {
        id: "5.3",
        title: "Export Final Document",
        description: "Save and summarize",
        checklist: [],
        prompt: `Export the final PID and provide a summary of:
- Total sections
- Key decisions made
- Any remaining TBDs or assumptions`
      }
    ]
  }
];

const antiPatterns = [
  "Don't assume - Always verify against real data/APIs",
  "Don't batch questions endlessly - Answer and iterate",
  "Don't skip edge cases - Nulls, duplicates, missing data",
  "Don't forget logging - You'll need it for debugging",
  "Don't hardcode - Use lookups/caches for all IDs",
  "Don't trust field names - Verify actual schema"
];

export default function PIDProcess() {
  const [expandedPhase, setExpandedPhase] = useState(1);
  const [completedSteps, setCompletedSteps] = useState(new Set());
  const [copiedPrompt, setCopiedPrompt] = useState(null);

  const toggleStep = (stepId) => {
    const newCompleted = new Set(completedSteps);
    if (newCompleted.has(stepId)) {
      newCompleted.delete(stepId);
    } else {
      newCompleted.add(stepId);
    }
    setCompletedSteps(newCompleted);
  };

  const copyPrompt = (prompt, stepId) => {
    navigator.clipboard.writeText(prompt);
    setCopiedPrompt(stepId);
    setTimeout(() => setCopiedPrompt(null), 2000);
  };

  const getPhaseProgress = (phase) => {
    const stepIds = phase.steps.map(s => s.id);
    const completed = stepIds.filter(id => completedSteps.has(id)).length;
    return { completed, total: stepIds.length };
  };

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-blue-400 mb-2">
          PID Development Process
        </h1>
        <p className="text-gray-400 mb-6">
          Systematic process for developing validated technical PIDs with Claude
        </p>

        {/* Progress Overview */}
        <div className="bg-gray-800 rounded-lg p-4 mb-6">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm text-gray-400">Overall Progress</span>
            <span className="text-sm text-blue-400">
              {completedSteps.size} / {phases.reduce((acc, p) => acc + p.steps.length, 0)} steps
            </span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2">
            <div 
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ 
                width: `${(completedSteps.size / phases.reduce((acc, p) => acc + p.steps.length, 0)) * 100}%` 
              }}
            />
          </div>
        </div>

        {/* Phases */}
        <div className="space-y-4">
          {phases.map((phase) => {
            const Icon = phase.icon;
            const progress = getPhaseProgress(phase);
            const isExpanded = expandedPhase === phase.id;
            
            return (
              <div key={phase.id} className="bg-gray-800 rounded-lg overflow-hidden">
                <button
                  onClick={() => setExpandedPhase(isExpanded ? null : phase.id)}
                  className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-750 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Icon className="w-5 h-5 text-blue-400" />
                    <span className="font-medium">
                      Phase {phase.id}: {phase.title}
                    </span>
                    <span className="text-sm text-gray-500">
                      ({progress.completed}/{progress.total})
                    </span>
                  </div>
                  {isExpanded ? (
                    <ChevronDown className="w-5 h-5 text-gray-400" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-gray-400" />
                  )}
                </button>

                {isExpanded && (
                  <div className="px-4 pb-4 space-y-4">
                    {phase.steps.map((step) => (
                      <div 
                        key={step.id}
                        className={`border rounded-lg p-4 transition-colors ${
                          completedSteps.has(step.id) 
                            ? 'border-green-600 bg-green-900/20' 
                            : 'border-gray-700 bg-gray-850'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <button
                            onClick={() => toggleStep(step.id)}
                            className="mt-0.5 flex-shrink-0"
                          >
                            {completedSteps.has(step.id) ? (
                              <CheckCircle className="w-5 h-5 text-green-500" />
                            ) : (
                              <Circle className="w-5 h-5 text-gray-500" />
                            )}
                          </button>
                          <div className="flex-1">
                            <h3 className="font-medium text-gray-100">
                              {step.id} {step.title}
                            </h3>
                            <p className="text-sm text-gray-400 mt-1">
                              {step.description}
                            </p>

                            {step.checklist.length > 0 && (
                              <ul className="mt-3 space-y-1">
                                {step.checklist.map((item, i) => (
                                  <li key={i} className="text-sm text-gray-300 flex items-center gap-2">
                                    <span className="w-1.5 h-1.5 bg-blue-400 rounded-full" />
                                    {item}
                                  </li>
                                ))}
                              </ul>
                            )}

                            {step.prompt && (
                              <div className="mt-3">
                                <div className="flex items-center justify-between mb-1">
                                  <span className="text-xs text-blue-400 font-medium">
                                    PROMPT TEMPLATE
                                  </span>
                                  <button
                                    onClick={() => copyPrompt(step.prompt, step.id)}
                                    className="text-xs text-gray-400 hover:text-blue-400 transition-colors"
                                  >
                                    {copiedPrompt === step.id ? '✓ Copied!' : 'Copy'}
                                  </button>
                                </div>
                                <pre className="text-xs bg-gray-900 p-3 rounded border border-gray-700 overflow-x-auto whitespace-pre-wrap text-gray-300">
                                  {step.prompt}
                                </pre>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Anti-Patterns */}
        <div className="mt-6 bg-red-900/20 border border-red-800 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-5 h-5 text-red-400" />
            <h2 className="font-medium text-red-400">Anti-Patterns to Avoid</h2>
          </div>
          <ul className="space-y-2">
            {antiPatterns.map((pattern, i) => (
              <li key={i} className="text-sm text-gray-300 flex items-center gap-2">
                <span className="text-red-400">✗</span>
                {pattern}
              </li>
            ))}
          </ul>
        </div>

        {/* Reset Button */}
        <div className="mt-6 text-center">
          <button
            onClick={() => setCompletedSteps(new Set())}
            className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
          >
            Reset Progress
          </button>
        </div>
      </div>
    </div>
  );
}
