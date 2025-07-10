#!/usr/bin/env python3
"""
Test runner for My AI Personal Assistant.
Runs all tests and generates a coverage report.
"""
import unittest
import sys
import os
from io import StringIO

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def run_tests():
    """Run all tests and return results."""
    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = os.path.join(project_root, 'tests')
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Create test runner
    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    result = runner.run(suite)
    
    # Print results
    print("=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    print(stream.getvalue())
    
    # Summary
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    # Return True if all tests passed
    return len(result.failures) == 0 and len(result.errors) == 0


def run_coverage():
    """Run tests with coverage analysis."""
    try:
        import coverage
        
        # Start coverage
        cov = coverage.Coverage()
        cov.start()
        
        # Run tests
        success = run_tests()
        
        # Stop coverage and generate report
        cov.stop()
        cov.save()
        
        print("\n" + "=" * 70)
        print("COVERAGE REPORT")
        print("=" * 70)
        cov.report()
        
        # Generate HTML report
        try:
            cov.html_report(directory='htmlcov')
            print("\nHTML coverage report generated in 'htmlcov' directory")
        except Exception as e:
            print(f"Could not generate HTML report: {e}")
        
        return success
        
    except ImportError:
        print("Coverage package not installed. Running tests without coverage...")
        return run_tests()


if __name__ == '__main__':
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == '--coverage':
        success = run_coverage()
    else:
        success = run_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)
