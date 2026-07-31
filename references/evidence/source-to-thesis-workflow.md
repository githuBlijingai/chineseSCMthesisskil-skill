# Source To Thesis Workflow

Use this reference when the user gives a program, repository, database, API, screenshots, test reports, or hardware design files and wants a thesis.

## Goal

Turn implementation evidence into thesis-ready facts before writing prose.

## Inputs

### For Software Projects

- source repository or project folder
- school template or formatting guide
- task book, proposal, advisor notes
- database schema or migration files
- API docs or route definitions
- screenshots and test reports
- deployment or run instructions

### For Hardware/MCU Projects (Recommended)

**Required for hardware chapters:**
- PCB design files (.pcbdoc, .kicad_pcb, .brd)
- Schematic files (.schdoc, .sch, .dsn)
- BOM (Bill of Materials) in CSV/Excel format
- Gerber files for manufacturing
- Chip datasheets (PDF)

**For software chapters:**
- Source code (C/C++ for MCU)
- Development environment info (IDE, compiler version)
- Configuration files

**For testing chapters:**
- Test reports or logs
- Oscilloscope screenshots
- Serial debug output

## Bootstrap Evidence

### For Software Projects

Run:

```powershell
python .\scripts\evidence\build_project_evidence.py . --out .\paper-context\evidence
```

Outputs:

```text
paper-context/evidence/
  project-evidence.json
  code-structure.md
  tech-stack.md
  api-list.md
  database-schema.md
  test-results.md
```

### For Hardware/MCU Projects (v1.1+)

If your project contains PCB layouts, schematics, or BOM files:

```powershell
# Option 1: Parse hardware files directly
python .\scripts\evidence\parse_hardware_files.py <hardware_directory> --out .\paper-context\evidence

# Option 2: Auto-detect hardware files
python .\scripts\evidence\build_hardware_evidence.py --project-path .
```

Outputs:

```text
paper-context/evidence/
  hardware-evidence.json    # Structured evidence (machine-readable)
  hardware-evidence.md      # Markdown summary (human-readable)
```

**Supported hardware file types:**
| Type | Extensions |
|------|------------|
| PCB | .pcbdoc, .prjpcb, .kicad_pcb, .brd |
| Schematic | .schdoc, .sch, .dsn |
| BOM | .csv, .xlsx, .txt |
| Gerber | .gtl, .gbl, .drl |

The script is a first pass. Read the outputs, then inspect source files before making important claims.

If the workspace was just initialized, also run:

```powershell
python .\scripts\workspace\check_thesis_workspace.py .\thesis-ai-standard
```

Treat warnings as setup tasks before drafting, especially unconfirmed reference standard versions and unfilled thesis type.

## Evidence To Thesis Mapping

| Evidence | Thesis Use |
|----------|------------|
| directory tree | system composition, frontend/backend split, module boundaries |
| package files | technology stack and development environment |
| routes/controllers | API design and detailed implementation |
| SQL/migrations/entities | database design and ER diagrams |
| tests/reports | testing chapter and result credibility |
| screenshots | detailed implementation and testing figures |
| **Hardware Evidence** | |
| hardware-evidence.json/md | Chapter 3: Hardware design description |
| BOM components | Chapter 3.2: Power circuit, Component selection |
| PCB board info | Chapter 3.5: PCB design and layout |
| Schematic components | Chapter 3.1-3.4: Circuit descriptions |

## Evidence Layers

Use five layers instead of jumping directly to chapters:

1. project inventory: files, tech markers, run scripts, database/API candidates
2. verified facts: source files or user materials that confirm a feature or result
3. thesis facts: normalized entries in `thesis-ai-spec.yaml`
4. figure/table plan: entries in `figure-registry.yaml`
5. prose: chapter sections that cite the previous layers

## Draft Order For System Papers

### For General Software Projects
1. Related technology and development environment.
2. Requirement analysis.
3. Overall design.
4. Database/API/module design.
5. Detailed implementation.
6. Testing.
7. Introduction and conclusion last.

### For MCU/Hardware Projects (Recommended)
1. **System scheme and key technologies (Chapter 2)** - After selecting MCU chip
2. **Hardware circuit design (Chapter 3)** - After PCB/schematic is ready
3. **Software program design (Chapter 4)** - After code structure is confirmed
4. **System testing (Chapter 5)** - After test data is available
5. **Introduction (Chapter 1)** - After knowing the complete solution
6. **Conclusion (last)** - After knowing what was achieved

Introduction is easier and less fake after the real contribution is known.

## Stop Conditions

### For General Projects
Do not draft final prose if these are missing:

- no school template or standard profile for layout-sensitive delivery
- no code evidence for claimed modules
- no schema/API evidence for database or interface claims
- no screenshots or run evidence for UI claims
- no test evidence for "tested", "stable", "passed", or "effective" claims

### For MCU/Hardware Projects
Do not draft hardware chapters (Chapter 3) if these are missing:

- no schematic or PCB files
- no BOM with component details
- no chip datasheets for selected components

Do not draft software chapters (Chapter 4) if these are missing:

- no source code files (.c, .h)
- no main program structure or flow chart
- no module decomposition

Do not draft testing chapter (Chapter 5) if these are missing:

- no test data or results
- no test equipment or environment description

Return a missing-material list instead.

## Figure Planning

Create or update `figure-registry.yaml` before drawing:

### For General Projects
- system architecture: based on real directory and deployment structure
- module diagram: based on real feature/module boundaries
- business flow: based on actual user/admin workflow
- ER diagram: based on schema/entities
- sequence diagram: based on controller/service/API flow
- screenshots: based on actual running pages or reports

### For MCU/Hardware Projects (Recommended)
Create figures based on actual hardware evidence:

| Figure | Source | Chapter |
|--------|--------|---------|
| System block diagram | Hardware evidence + project structure | Chapter 2 |
| MCU selection comparison table | Datasheet analysis | Chapter 2.2 |
| Power supply circuit schematic | Schematic files | Chapter 3.2 |
| Sensor interface circuit | Schematic files | Chapter 3.3 |
| Communication interface circuit | Schematic files | Chapter 3.4 |
| PCB layout screenshot | PCB files | Chapter 3.5 |
| Main program flow chart | Code structure | Chapter 4.2 |
| Module hierarchy diagram | Source code files | Chapter 4.3 |
| Interrupt flow chart | Code + interrupt configuration | Chapter 4.4 |
| Communication protocol frame | Protocol specification | Chapter 4.5 |
| Test environment photo | Actual test setup | Chapter 5.1 |
| Test results table | Test data | Chapter 5.2-5.4 |

**Important**: All hardware figures must be traceable to actual design files (schematic, PCB, BOM), not just drawn for decoration.
