# IEC_62304_Auditor_Agent
A multi-agent system for auditing medical software lifecycle compliance according to IEC 62304 standard.
## What is IEC 62304?

IEC 62304 is the international standard for medical device software lifecycle processes. It defines requirements for the development, maintenance, and risk management of medical software to ensure patient safety.

### Key Concepts for Beginners

**Software Safety Classification:**
- **Class A**: No injury or damage to health is possible
- **Class B**: Non-serious injury is possible  
- **Class C**: Death or serious injury is possible

**Main Process Areas:**
- Development Planning (§5.1)
- Software Requirements Analysis (§5.2)
- Software Architectural Design (§5.3)
- Software Detailed Design (§5.4)
- Software Implementation (§5.5)
- Software Integration & Testing (§5.6)
- Software System Testing (§5.7)
- Software Configuration Management (§5.8)
- Software Problem Resolution (§9)

## Features

This tool provides automated audit capabilities across all IEC 62304 requirements:

### Multi-Agent Audit Team
- **Safety Classifier**: Determines software safety class (A/B/C)
- **Lifecycle Auditor**: Verifies development processes (§5.1-5.7)
- **Risk/Config/Problem Auditor**: Checks risk management, configuration, and problem resolution
- **SOUP Auditor**: Validates Software of Unknown Provenance (§8)
- **Traceability Auditor**: Ensures bi-directional traceability
- **Lead Auditor**: Coordinates findings and generates final report

### Document Processing
Supports common medical device documentation formats:
- PDF specifications and plans
- DOCX requirements documents
- XLSX test matrices and traceability tables

### Compliance Reporting
Generates structured audit reports including:
- Safety classification assessment
- Detailed findings per IEC 62304 clause
- Non-conformity register
- Risk statements and recommendations
- Actionable corrective actions with priorities

## Installation

### Prerequisites
```bash
# Install Python dependencies
pip install python-dotenv autogen-agentchat autogen-ext

# Optional document processing
pip install pypdf python-docx openpyxl
```

### API Configuration
Create a `.env` file:
```
ANTHROPIC_API_KEY=your_claude_api_key_here
CLAUDE_MODEL=claude-sonnet-4-20250514
```

## Usage

### Basic Audit Workflow

1. **Start the auditor**:
```bash
python IEC62304_autogen.py
```

2. **Add documentation**:
```
iec62304> add *.pdf *.docx *.xlsx
iec62304> add requirements.pdf design.docx tests.xlsx
```

3. **Review queue**:
```
iec62304> list
```

4. **Run audit**:
```
iec62304> run
```

5. **Clear and exit**:
```
iec62304> clear
iec62304> quit
```

### Understanding Audit Results

The audit generates findings categorized by:

**Status Levels:**
- `CONFORMING`: Meets IEC 62304 requirements
- `MINOR_NC`: Minor non-conformity (documentation gaps)
- `MAJOR_NC`: Major non-conformity (missing critical processes)
- `OBSERVATION`: Areas for improvement

**Severity Levels:**
- `LOW`: Minor documentation issues
- `MEDIUM`: Process gaps that could affect quality
- `HIGH`: Critical safety-related deficiencies

**Priority Levels:**
- `P1`: Must fix before release
- `P2`: Should fix in current cycle
- `P3`: Consider for future releases

## Audit Best Practices

### For Beginners

1. **Start with Classification**: Always determine your software safety class first
2. **Document Everything**: IEC 62304 requires extensive documentation
3. **Maintain Traceability**: Link requirements → design → code → tests
4. **Risk Management**: Integrate ISO 14971 risk analysis throughout
5. **SOUP Management**: Identify and evaluate all third-party software

### Common Audit Findings

**Planning Issues:**
- Missing software development plan
- Unclear safety classification rationale
- Inadequate resource allocation

**Requirements Problems:**
- Incomplete functional requirements
- Missing safety requirements
- Poor traceability to system requirements

**Design Deficiencies:**
- Architectural design not documented
- Missing interface specifications
- Inadequate SOUP integration analysis

**Testing Gaps:**
- Insufficient test coverage for safety class
- Missing integration test procedures
- Inadequate verification of safety requirements

## File Structure

```
project/
├── IEC62304_autogen.py    # Main audit script
├── .env                   # API configuration
├── requirements.pdf       # Software requirements
├── design.docx           # Architectural design
├── tests.xlsx            # Test matrices
└── README.md             # This file
```

## Token Usage and Costs

The tool tracks Claude API usage:
- Input tokens: Document processing
- Output tokens: Audit report generation
- Typical audit: 10,000-50,000 tokens depending on documentation size

## Troubleshooting

**Common Issues:**

1. **Missing API Key**: Ensure `ANTHROPIC_API_KEY` is set in `.env`
2. **Document Processing Errors**: Install optional dependencies for PDF/DOCX/XLSX
3. **Large Documents**: Tool automatically truncates to manage token limits
4. **No Evidence Found**: Ensure file extensions are .pdf, .docx, or .xlsx

**Getting Help:**
- Check file paths and permissions
- Verify document formats are supported
- Review API key configuration
- Monitor token usage for cost management

## Regulatory Context

This tool assists with IEC 62304 compliance but does not replace:
- Qualified Person oversight
- Regulatory submission review
- Clinical evaluation processes
- Post-market surveillance activities

Always consult with regulatory experts for official submissions.

## License

This tool is provided for educational and compliance assistance purposes. Users are responsible for ensuring their medical device software meets all applicable regulatory requirements.
