#!/usr/bin/env python3
"""
Test parallel agent spawning.

This demonstrates the key advantage of the orchestrator: spawning multiple
isolated Claude agents simultaneously for parallel execution.
"""

import asyncio
import time
from orchestrator_prototype import AgentOrchestrator


async def test_parallel_spawning():
    """Spawn 3 agents simultaneously and measure performance."""
    orchestrator = AgentOrchestrator()

    print("=" * 70)
    print("PARALLEL AGENT SPAWNING TEST")
    print("=" * 70)
    print()

    # Define 3 different tasks
    tasks = [
        {
            'agent_type': 'coder-haiku',
            'task': 'Write a Python function to validate IPv4 addresses',
            'workspace': 'C:/Projects/claude-family'
        },
        {
            'agent_type': 'coder-haiku',
            'task': 'Write a Python function to calculate Fibonacci numbers',
            'workspace': 'C:/Projects/claude-family'
        },
        {
            'agent_type': 'coder-haiku',
            'task': 'Write a Python function to check if a string is a palindrome',
            'workspace': 'C:/Projects/claude-family'
        }
    ]

    # Test 1: Sequential execution (baseline)
    print("Test 1: SEQUENTIAL EXECUTION (baseline)")
    print("-" * 70)
    start_sequential = time.time()

    for i, task_config in enumerate(tasks, 1):
        print(f"  Task {i}: {task_config['task'][:50]}...")
        result = await orchestrator.spawn_agent(
            task_config['agent_type'],
            task_config['task'],
            task_config['workspace']
        )
        print(f"    ✓ Completed in {result['execution_time_seconds']:.2f}s")

    sequential_time = time.time() - start_sequential
    print(f"\nTotal sequential time: {sequential_time:.2f}s")
    print()

    # Test 2: Parallel execution
    print("Test 2: PARALLEL EXECUTION")
    print("-" * 70)
    start_parallel = time.time()

    # Create coroutines for all tasks
    coroutines = []
    for i, task_config in enumerate(tasks, 1):
        print(f"  Task {i}: {task_config['task'][:50]}... (spawning)")
        coro = orchestrator.spawn_agent(
            task_config['agent_type'],
            task_config['task'],
            task_config['workspace']
        )
        coroutines.append(coro)

    # Execute all in parallel
    print("\n  Executing all tasks in parallel...")
    results = await asyncio.gather(*coroutines)

    parallel_time = time.time() - start_parallel

    # Display results
    print("\n  Results:")
    for i, result in enumerate(results, 1):
        status = "✓" if result['success'] else "✗"
        print(f"    {status} Task {i}: {result['execution_time_seconds']:.2f}s")

    print(f"\nTotal parallel time: {parallel_time:.2f}s")
    print()

    # Calculate speedup
    speedup = sequential_time / parallel_time if parallel_time > 0 else 0

    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Sequential execution: {sequential_time:.2f}s")
    print(f"Parallel execution:   {parallel_time:.2f}s")
    print(f"Speedup:              {speedup:.2f}x")
    print(f"Time saved:           {sequential_time - parallel_time:.2f}s ({(1 - parallel_time/sequential_time)*100:.1f}%)")
    print()

    # Cost analysis
    total_cost = sum(r['estimated_cost_usd'] for r in results)
    print(f"Total cost (3 tasks): ${total_cost:.3f}")
    print(f"Cost per task:        ${total_cost/3:.3f}")
    print()

    return {
        'sequential_time': sequential_time,
        'parallel_time': parallel_time,
        'speedup': speedup,
        'results': results
    }


if __name__ == '__main__':
    asyncio.run(test_parallel_spawning())
