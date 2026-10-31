import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from maintainerops.models.base import BaseModel, Field

PLACEHOLDER_VALUES = {
    "n/a", "na", "none", "no", "todo", "fill this out", "tbd", "nil", "null", "-", "--", "...", "?"
}


class TemplateField(BaseModel):
    id: str
    label: str
    required: bool = False
    field_type: str = "textarea"  # input, textarea, dropdown, checkboxes
    placeholder: Optional[str] = None


class IssueTemplate(BaseModel):
    name: str
    filename: str
    description: Optional[str] = None
    is_form: bool = False  # True for YAML forms, False for markdown templates
    fields: List[TemplateField] = Field(default_factory=list)
    raw_content: str = ""


class TemplateValidationIssue(BaseModel):
    field_label: str
    issue_type: str  # missing_field, placeholder_value, unedited_comment
    details: str


def parse_yaml_form_template(content: str, filename: str) -> Optional[IssueTemplate]:
    """Parses a GitHub Issue Form YAML file (.github/ISSUE_TEMPLATE/*.yml)."""
    try:
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            return None

        name = data.get("name", filename)
        desc = data.get("description", "")
        fields: List[TemplateField] = []

        for item in data.get("body", []):
            if not isinstance(item, dict):
                continue
            item_type = item.get("type", "")
            if item_type in ["markdown"]:
                continue

            attributes = item.get("attributes", {})
            validations = item.get("validations", {})
            label = attributes.get("label") or item.get("id") or "Unnamed Field"
            required = bool(validations.get("required", False))

            fields.append(
                TemplateField(
                    id=item.get("id", label.lower().replace(" ", "_")),
                    label=label,
                    required=required,
                    field_type=item_type,
                    placeholder=attributes.get("placeholder"),
                )
            )

        return IssueTemplate(
            name=name,
            filename=filename,
            description=desc,
            is_form=True,
            fields=fields,
            raw_content=content,
        )
    except Exception:
        return None


def parse_markdown_template(content: str, filename: str) -> IssueTemplate:
    """Parses a GitHub Markdown Issue Template (.github/ISSUE_TEMPLATE/*.md)."""
    # Extract frontmatter if present
    name = filename
    desc = ""
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            body = parts[2]
            try:
                fm_data = yaml.safe_load(fm_text) or {}
                name = fm_data.get("name", filename)
                desc = fm_data.get("about") or fm_data.get("description") or ""
            except Exception:
                pass

    fields: List[TemplateField] = []
    # Find all Markdown headers (## or ###)
    header_matches = re.findall(r"^(#{1,4})\s+(.+)$", body, re.MULTILINE)
    for _, header_title in header_matches:
        cleaned_title = header_title.strip()
        fields.append(
            TemplateField(
                id=cleaned_title.lower().replace(" ", "_"),
                label=cleaned_title,
                required=True,  # Sections in markdown templates are treated as expected
                field_type="markdown_section",
            )
        )

    return IssueTemplate(
        name=name,
        filename=filename,
        description=desc,
        is_form=False,
        fields=fields,
        raw_content=content,
    )


def load_repository_templates(
    repo_dir: Optional[str] = None,
    raw_templates: Optional[List[Dict[str, str]]] = None,
) -> List[IssueTemplate]:
    """Finds and parses all issue templates in a repository directory or raw list."""
    templates: List[IssueTemplate] = []

    # 1. From provided raw fixtures (useful for offline tests and mocks)
    if raw_templates:
        for t in raw_templates:
            fname = t.get("filename", "template.yml")
            cnt = t.get("content", "")
            if fname.endswith((".yml", ".yaml")):
                parsed = parse_yaml_form_template(cnt, fname)
                if parsed:
                    templates.append(parsed)
            else:
                templates.append(parse_markdown_template(cnt, fname))
        return templates

    # 2. From local directory .github/ISSUE_TEMPLATE
    base_path = Path(repo_dir) if repo_dir else Path.cwd()
    template_dir = base_path / ".github" / "ISSUE_TEMPLATE"

    if template_dir.exists() and template_dir.is_dir():
        for file_path in template_dir.iterdir():
            if file_path.suffix.lower() in [".yml", ".yaml"]:
                try:
                    text = file_path.read_text(encoding="utf-8")
                    parsed = parse_yaml_form_template(text, file_path.name)
                    if parsed:
                        templates.append(parsed)
                except Exception:
                    pass
            elif file_path.suffix.lower() == ".md":
                try:
                    text = file_path.read_text(encoding="utf-8")
                    templates.append(parse_markdown_template(text, file_path.name))
                except Exception:
                    pass

    return templates


def validate_issue_against_template(
    issue_title: str,
    issue_body: str,
    template: IssueTemplate,
) -> List[TemplateValidationIssue]:
    """Validates an issue body against a specific repository issue template."""
    violations: List[TemplateValidationIssue] = []
    body_text = issue_body or ""

    # Check for unaltered HTML comments from template: e.g. <!-- Describe here -->
    unfilled_comments = re.findall(r"<!--\s*([^>]+?)\s*-->", body_text)
    for c in unfilled_comments:
        c_clean = c.strip()
        if any(w in c_clean.lower() for w in ["describe", "steps", "replace", "example", "fill"]):
            violations.append(
                TemplateValidationIssue(
                    field_label="Template Comments",
                    issue_type="unedited_comment",
                    details=f"Contains unaltered template instructional comment: '<!-- {c_clean[:30]}... -->'.",
                )
            )

    # Extract all markdown sections by header: e.g. '### Steps to Reproduce'
    sections: Dict[str, str] = {}
    current_header = None
    current_lines: List[str] = []

    for line in body_text.splitlines():
        header_match = re.match(r"^[ \t]*#{1,4}\s*(?:\d+\.\s*)?(.+?)[ \t]*$", line)
        if header_match:
            if current_header is not None:
                sections[current_header.strip().lower()] = "\n".join(current_lines).strip()
            current_header = header_match.group(1).strip()
            current_lines = []
        elif current_header is not None:
            current_lines.append(line)

    if current_header is not None:
        sections[current_header.strip().lower()] = "\n".join(current_lines).strip()

    # Validate each required field in the template
    for field in template.fields:
        if not field.required:
            continue

        field_key = field.label.strip().lower()
        matched_content: Optional[str] = None

        # 1. Match against extracted markdown sections
        for sec_name, sec_val in sections.items():
            if sec_name == field_key or field_key in sec_name or sec_name in field_key:
                matched_content = sec_val
                break

        # 2. Match against inline label (e.g. 'Version: 1.2.3' or '**Version**: 1.2.3')
        if matched_content is None:
            inline_pattern = rf"(?:^|\n)[ \t]*\*?\*?{re.escape(field.label)}\*?\*?:\s*(.+)"
            match_inline = re.search(inline_pattern, body_text, re.IGNORECASE)
            if match_inline:
                matched_content = match_inline.group(1).strip()

        if matched_content is None:
            violations.append(
                TemplateValidationIssue(
                    field_label=field.label,
                    issue_type="missing_field",
                    details=f"Required template field '{field.label}' is absent from the report.",
                )
            )
            continue

        # Check for placeholder / lazy values
        no_comments = re.sub(r"<!--[\s\S]*?-->", "", matched_content).strip().lower()
        clean_val = re.sub(r"[`*_\-\[\]()]", "", no_comments).strip()

        if not clean_val or clean_val in PLACEHOLDER_VALUES or len(clean_val) < 3:
            violations.append(
                TemplateValidationIssue(
                    field_label=field.label,
                    issue_type="placeholder_value",
                    details=f"Field '{field.label}' was populated with placeholder or insufficient text ('{matched_content[:20]}').",
                )
            )

    return violations

