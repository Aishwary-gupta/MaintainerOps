from maintainerops.models.github import IssueItem, User
from maintainerops.rules.completeness import CompletenessRule
from maintainerops.templates import (
    load_repository_templates,
    parse_markdown_template,
    parse_yaml_form_template,
    validate_issue_against_template,
)

SAMPLE_FORM_YML = """
name: "Bug Report"
description: "File a bug"
body:
  - type: textarea
    id: reproduction
    attributes:
      label: "Steps to Reproduce"
    validations:
      required: true
  - type: input
    id: version
    attributes:
      label: "Version"
    validations:
      required: true
"""

SAMPLE_MD = """---
name: Bug Report
about: Create a report
---

### Steps to Reproduce
<!-- Describe steps here -->

### Environment
"""


def test_parse_yaml_form_template():
    tmpl = parse_yaml_form_template(SAMPLE_FORM_YML, "bug_report.yml")
    assert tmpl is not None
    assert tmpl.name == "Bug Report"
    assert tmpl.is_form is True
    assert len(tmpl.fields) == 2
    assert tmpl.fields[0].label == "Steps to Reproduce"
    assert tmpl.fields[0].required is True


def test_parse_markdown_template():
    tmpl = parse_markdown_template(SAMPLE_MD, "bug.md")
    assert tmpl.name == "Bug Report"
    assert tmpl.is_form is False
    assert len(tmpl.fields) >= 2


def test_validate_issue_missing_fields_and_placeholders():
    tmpl = parse_yaml_form_template(SAMPLE_FORM_YML, "bug_report.yml")
    assert tmpl is not None

    # Issue missing 'Version' and having placeholder for 'Steps to Reproduce'
    bad_body = """
### Steps to Reproduce
N/A
"""
    violations = validate_issue_against_template("Crash", bad_body, tmpl)
    assert len(violations) >= 2

    types = [v.issue_type for v in violations]
    assert "placeholder_value" in types
    assert "missing_field" in types


def test_completeness_rule_with_templates():
    tmpl = parse_yaml_form_template(SAMPLE_FORM_YML, "bug_report.yml")
    rule = CompletenessRule(templates=[tmpl])

    issue = IssueItem(
        number=109,
        title="Crash when opening settings",
        body="### Steps to Reproduce\nnone\n<!-- describe steps -->",
        state="open",
        user=User(login="lazy_reporter"),
    )

    findings = rule.analyze([issue], [])
    assert len(findings) == 1
    f = findings[0]
    assert "fails repository template validation" in f.summary
    assert "template_placeholder_value" in [ev.metric_name for ev in f.evidence]
