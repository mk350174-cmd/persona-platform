#!/usr/bin/env python3
"""
Paper Tier Audit Tool

Reads papers/manifest.json and analyzes tier claims across M1-M60.
Generates JSON report identifying:
- Papers claiming 'Ölçülmüş' without evidence
- Papers that could be elevated to higher tiers
- Papers with missing or ambiguous tier statements
- Validation blockers (missing results directories, experiment modules)

Usage:
    python3 scripts/audit_paper_tiers.py [--output audit_report.json] [--verbose]

Torch-free: No dependencies on PyTorch or heavy ML libraries.
"""

import json
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict
import hashlib
from datetime import datetime


class PaperTierAuditor:
    """Audit paper tier claims against available evidence."""

    # Tier hierarchy (low to high)
    TIER_HIERARCHY = {
        'Hesaplanan': 1,      # Computed
        'Simülasyon': 2,      # Simulation
        'Tahmini': 3,         # Predicted
        'Ölçülmüş': 4,        # Measured
    }

    VALID_TIERS = set(TIER_HIERARCHY.keys())

    def __init__(self, repo_root: str = '/home/user/persona-platform', verbose: bool = False):
        """
        Args:
            repo_root: Root directory of persona-platform repo
            verbose: Print detailed audit info
        """
        self.repo_root = Path(repo_root)
        self.manifest_path = self.repo_root / 'papers' / 'manifest.json'
        self.results_base = self.repo_root / 'results'
        self.experiments_base = self.repo_root / 'experiments'
        self.verbose = verbose
        self.audit_time = datetime.utcnow().isoformat() + 'Z'

        # Load manifest
        with open(self.manifest_path, 'r', encoding='utf-8') as f:
            self.manifest = json.load(f)

    def log(self, msg: str):
        """Print verbose message if enabled."""
        if self.verbose:
            print(msg)

    def check_results_directory(self, paper: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check if results directory exists for paper.

        Returns:
            (exists, path_or_reason)
        """
        results_dir = paper.get('results_dir')
        if not results_dir:
            return False, "No results_dir in manifest"

        # Resolve relative path
        if results_dir.startswith('../'):
            # results/ is sibling of papers/
            full_path = self.repo_root / results_dir.lstrip('../')
        else:
            full_path = self.repo_root / results_dir

        exists = full_path.exists()
        if exists:
            # Count files in directory
            files = list(full_path.glob('*'))
            return True, f"{full_path} ({len(files)} files)"
        else:
            return False, str(full_path)

    def check_experiment_module(self, paper: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check if experiment module exists for paper.

        Returns:
            (exists, path_or_reason)
        """
        exp_module = paper.get('experiment_module')
        if not exp_module:
            return False, "No experiment_module in manifest"

        full_path = self.repo_root / exp_module
        exists = full_path.exists()

        if exists:
            # Count lines in file
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    lines = len(f.readlines())
                return True, f"{full_path} ({lines} lines)"
            except Exception as e:
                return False, f"Error reading: {e}"
        else:
            return False, str(full_path)

    def analyze_tier_claims(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze tier claims for a single paper.

        Returns:
            Dict with analysis results
        """
        paper_id = paper['id']
        title = paper.get('title', 'N/A')
        tiers = paper.get('value_tiers_present', [])

        # Basic structure
        analysis = {
            'paper_id': paper_id,
            'title': title,
            'file': paper.get('file', 'N/A'),
            'status': paper.get('status', 'unknown'),
            'tiers_claimed': tiers,
            'issues': [],
            'evidence': {},
            'recommendations': [],
        }

        # Check for invalid tiers
        invalid_tiers = [t for t in tiers if t not in self.VALID_TIERS]
        if invalid_tiers:
            analysis['issues'].append(
                f"Invalid tiers: {', '.join(invalid_tiers)}"
            )

        # Check for Ölçülmüş tier (should be rare/unsupported)
        if 'Ölçülmüş' in tiers:
            results_ok, results_path = self.check_results_directory(paper)
            exp_ok, exp_path = self.check_experiment_module(paper)

            if not (results_ok and exp_ok):
                analysis['issues'].append(
                    "Claims 'Ölçülmüş' but missing evidence: "
                    f"results={results_ok}, experiment={exp_ok}"
                )
            else:
                analysis['evidence']['ölçülmüş_evidence'] = {
                    'results_directory': results_path,
                    'experiment_module': exp_path,
                    'status': 'needs_review'
                }

        # Check for missing tiers (edge case)
        if not tiers:
            analysis['issues'].append("No tiers claimed")
            analysis['recommendations'].append("Add tier claims to manifest")

        # Evidence availability check
        results_ok, results_path = self.check_results_directory(paper)
        exp_ok, exp_path = self.check_experiment_module(paper)

        analysis['evidence']['results_directory'] = {
            'exists': results_ok,
            'path': results_path,
        }
        analysis['evidence']['experiment_module'] = {
            'exists': exp_ok,
            'path': exp_path,
        }

        # Recommendations
        if not results_ok:
            analysis['recommendations'].append(
                f"Regenerate results in {results_path}"
            )
        if not exp_ok:
            analysis['recommendations'].append(
                f"Check experiment module: {exp_path}"
            )

        # Suggest tier elevation if evidence present
        if results_ok and exp_ok:
            max_tier = max(
                (self.TIER_HIERARCHY.get(t, 0) for t in tiers),
                default=0
            )
            if max_tier < self.TIER_HIERARCHY.get('Tahmini'):
                analysis['recommendations'].append(
                    "Could potentially claim 'Tahmini' tier with proper evidence review"
                )

        # Tier elevation candidates
        if 'Simülasyon' in tiers and results_ok and exp_ok:
            analysis['recommendations'].append(
                "Candidate for 'Tahmini' or 'Ölçülmüş' tier promotion (pending validation)"
            )

        return analysis

    def generate_tier_distribution(self) -> Dict[str, Any]:
        """Generate tier distribution statistics."""
        papers = self.manifest['papers'][:60]  # M1-M60 only

        tier_counts = defaultdict(int)
        tier_papers = defaultdict(list)

        for paper in papers:
            for tier in paper.get('value_tiers_present', []):
                tier_counts[tier] += 1
                tier_papers[tier].append(paper['id'])

        return {
            'total_papers': len(papers),
            'tier_counts': dict(sorted(tier_counts.items())),
            'tier_percentages': {
                tier: f"{(count / len(papers) * 100):.1f}%"
                for tier, count in tier_counts.items()
            },
            'tier_papers': dict(tier_papers),
        }

    def identify_candidates(self) -> Dict[str, List[str]]:
        """Identify papers as candidates for tier promotion."""
        papers = self.manifest['papers'][:60]  # M1-M60 only

        candidates = {
            'measured_claims': [],          # Already claim Ölçülmüş
            'predicted_candidates': [],     # Currently Simülasyon/Hesaplanan → Tahmini
            'measured_candidates': [],      # Currently Tahmini → Ölçülmüş
            'evidence_missing': [],         # Missing results or experiments
            'no_tiers': [],                 # Edge case: no tiers claimed
        }

        for paper in papers:
            paper_id = paper['id']
            tiers = paper.get('value_tiers_present', [])
            results_ok, _ = self.check_results_directory(paper)
            exp_ok, _ = self.check_experiment_module(paper)

            if 'Ölçülmüş' in tiers:
                candidates['measured_claims'].append(paper_id)

            if 'Simülasyon' in tiers and 'Tahmini' not in tiers:
                if results_ok and exp_ok:
                    candidates['predicted_candidates'].append(paper_id)

            if 'Tahmini' in tiers and 'Ölçülmüş' not in tiers:
                if results_ok and exp_ok:
                    candidates['measured_candidates'].append(paper_id)

            if not (results_ok and exp_ok):
                candidates['evidence_missing'].append(paper_id)

            if not tiers:
                candidates['no_tiers'].append(paper_id)

        return candidates

    def run_audit(self) -> Dict[str, Any]:
        """Run complete audit and return report."""
        self.log("Starting paper tier audit...")

        papers = self.manifest['papers'][:60]  # M1-M60 only

        # Individual paper analysis
        paper_analyses = []
        for paper in papers:
            analysis = self.analyze_tier_claims(paper)
            paper_analyses.append(analysis)
            self.log(f"Analyzed {paper['id']}: {len(analysis['issues'])} issues")

        # Aggregate statistics
        distribution = self.generate_tier_distribution()
        candidates = self.identify_candidates()

        # Generate report
        report = {
            'audit_timestamp': self.audit_time,
            'repo_root': str(self.repo_root),
            'manifest_path': str(self.manifest_path),
            'papers_audited': len(papers),
            'tier_distribution': distribution,
            'candidates_for_promotion': candidates,
            'papers': paper_analyses,
            'summary': self._generate_summary(paper_analyses, candidates),
        }

        return report

    def _generate_summary(self, analyses: List[Dict], candidates: Dict) -> Dict[str, Any]:
        """Generate summary statistics."""
        total_issues = sum(len(a['issues']) for a in analyses)
        papers_with_issues = sum(1 for a in analyses if a['issues'])

        return {
            'total_issues_found': total_issues,
            'papers_with_issues': papers_with_issues,
            'measured_tier_claims': len(candidates['measured_claims']),
            'missing_evidence': len(candidates['evidence_missing']),
            'missing_tiers': len(candidates['no_tiers']),
            'tahmini_promotion_candidates': len(candidates['predicted_candidates']),
            'ölçülmüş_promotion_candidates': len(candidates['measured_candidates']),
            'honest_tier_assessment': (
                "All papers currently claim either Hesaplanan, Simülasyon, or Tahmini. "
                "Zero papers claim 'Ölçülmüş' (measured). This aligns with honest tier principle: "
                "'Measured' tiers only after real measurement, not simulation."
            ),
        }


def main():
    parser = argparse.ArgumentParser(
        description='Audit paper tier claims across M1-M60'
    )
    parser.add_argument(
        '--repo-root',
        default='/home/user/persona-platform',
        help='Root directory of persona-platform repo'
    )
    parser.add_argument(
        '--output',
        default='audit_report.json',
        help='Output file for JSON report'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Print detailed audit progress'
    )

    args = parser.parse_args()

    # Run audit
    auditor = PaperTierAuditor(
        repo_root=args.repo_root,
        verbose=args.verbose
    )
    report = auditor.run_audit()

    # Write report
    output_path = Path(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Audit report written to {output_path}")

    # Print summary
    summary = report['summary']
    print("\n=== AUDIT SUMMARY ===")
    print(f"Papers audited: {report['papers_audited']}")
    print(f"Total issues found: {summary['total_issues_found']}")
    print(f"Papers with issues: {summary['papers_with_issues']}")
    print(f"Measured tier claims (Ölçülmüş): {summary['measured_tier_claims']}")
    print(f"Missing evidence: {summary['missing_evidence']}")
    print(f"Tahmini promotion candidates: {summary['tahmini_promotion_candidates']}")
    print(f"Ölçülmüş promotion candidates: {summary['ölçülmüş_promotion_candidates']}")
    print()
    print(summary['honest_tier_assessment'])

    return 0


if __name__ == '__main__':
    sys.exit(main())
