# photo-documentation — Detailed Reference



Extended documentation, examples, templates, and detailed criteria for the photo-documentation skill.



## Gemini Vision Prompt Templates

### Primary Classification Prompt

```
You are a construction site photo classification expert. Analyze this photo and classify it according to construction industry standards.

CLASSIFICATION CATEGORIES:
1. PROGRESS - Active construction work, phased advancement
2. SAFETY - PPE, hazards, fall protection, compliance issues
3. QUALITY - Defects, alignment issues, finish problems
4. WEATHER - Site conditions, precipitation, temperature indicators
5. DELIVERY - Material/equipment arrivals, staging
6. DEFICIENCY - Punch list items, damage, installation errors
7. CLOSEOUT - Completed areas, final finishes, system verification

ANALYSIS REQUIRED:
- Primary category (most specific fit)
- Secondary categories (if applicable)
- Confidence score (0.0-1.0)
- Supporting observations
- Trade(s) visible or implied
- Building phase (Foundation, Structural, MEP, Interiors, Finishes, Closeout)
- Grid location (if identifiable from visible grid marks, building features, or context)

Return JSON output with:
{
  "primary_category": "string",
  "secondary_categories": ["string"],
  "confidence": 0.0-1.0,
  "trade_detected": "string or null",
  "phase_detected": "string",
  "grid_location_detected": ["string"],
  "key_observations": ["string"],
  "description": "string"
}
```

### Trade Detection Prompt

```
Identify construction trades visible or implied in this photo. Look for:
- Equipment type (concrete forms, welding rigs, spray equipment, tools)
- Material visible (rebar, structural steel, mechanical units, drywall, paint)
- Work in progress (concrete placement, steel erection, piping runs, drywall hanging)
- Worker activity patterns (if visible)
- Installation evidence (connections, fasteners, assemblies)

Return JSON with:
{
  "trades_detected": [
    {
      "trade": "string (Concrete, Structural Steel, MEP, Drywall, etc.)",
      "confidence": 0.0-1.0,
      "evidence": ["string"],
      "activity": "string describing what trade work is visible"
    }
  ]
}
```

### Safety Compliance Prompt

```
Assess safety conditions in this construction photo. Evaluate:

PPE COMPLIANCE (if workers visible):
- Hard hats (present/absent)
- Safety glasses (present/absent)
- Hi-visibility clothing (present/absent)
- Gloves (present/absent)
- Steel-toe boots (visible from footwear)

HAZARD ASSESSMENT:
- Fall hazards (openings, heights, guardrails)
- Electrical hazards (exposed wiring, wet conditions)
- Stored material hazards (stacking, instability, access)
- Environmental hazards (standing water, slippery surfaces, weather exposure)
- Equipment operation safety (forklift, crane, power tools)
- Housekeeping (debris, trip hazards, organization)

SIGNAGE & CONTROLS:
- Safety signage visibility
- Barricades/access control
- Warning flags or markers

Return JSON with:
{
  "compliance_status": "compliant | violation | concern | observation",
  "workers_visible": boolean,
  "ppe_assessment": {
    "hard_hats": "compliant | violation",
    "hi_visibility": "compliant | violation",
    "gloves": "compliant | violation | not_applicable",
    "footwear": "compliant | unknown"
  },
  "hazards_identified": [
    {
      "hazard_type": "string",
      "severity": "observation | warning | critical",
      "description": "string",
      "corrective_action": "string"
    }
  ],
  "overall_severity": "observation | warning | critical"
}
```

### Progress Assessment Prompt

```
Evaluate construction progress visible in this photo. Assess:

WORK PHASE:
- Current phase (Foundation, Structural, MEP, Interiors, Finishes, Closeout)
- Work type (concrete, steel, framing, systems, finishes)
- Percentage of visible work complete (0-100%)

ADVANCEMENT:
- Work advancement since previous phase
- Readiness for next phase
- Critical path items visible

SCHEDULE ALIGNMENT:
- Does work appear on-schedule for construction phase?
- Critical activities visible?
- Potential schedule risks observable?

Return JSON with:
{
  "phase_detected": "string",
  "work_type": "string",
  "visual_percent_complete": 0-100,
  "advancement_indicators": ["string"],
  "critical_path_items": ["string"],
  "next_phase_ready": boolean,
  "schedule_assessment": "on_schedule | ahead | behind | uncertain",
  "schedule_confidence": 0.0-1.0
}
```

### Quality Inspection Prompt

```
Perform quality inspection of visible work against construction industry standards:

VISUAL INSPECTION:
- Surface finish quality (smoothness, flatness, color uniformity)
- Alignment and positioning (plumb, level, spacing)
- Connections and joints (tight, sealed, proper fastening)
- Dimensional accuracy (spacing, offset, clearance consistency)
- Workmanship quality (neatness, attention to detail)

DEFECT IDENTIFICATION:
- Visible cracks, spalls, damage
- Misalignment or warping
- Color variations or finishing issues
- Gap inconsistencies
- Code violations or non-compliance

HOLD POINT VERIFICATION (if applicable):
- Rebar placement (if concrete work)
- Embedment installation
- Surface preparation adequacy
- Pre-pour/pre-finish conditions

Return JSON with:
{
  "defects_found": boolean,
  "defect_list": [
    {
      "type": "crack | spall | misalignment | gap | color | texture | damage | other",
      "severity": "minor | major | critical",
      "location": "string describing location in photo",
      "description": "string",
      "spec_reference": "string (if identifiable)"
    }
  ],
  "overall_quality": "acceptable | acceptable_with_noted_defects | unacceptable",
  "rework_required": boolean,
  "hold_point_status": "pass | fail | requires_closer_inspection"
}
```

---



## Confidence Scoring System

### Score Ranges & Actions

| Score Range | Category | Action | Typical Use |
|-----------|----------|--------|------------|
| 0.90 - 1.0 | High Confidence | Auto-apply to metadata, no review needed | Clear category, obvious characteristics |
| 0.85 - 0.89 | High Confidence | Auto-apply, log for superintendent review if desired | Standard construction photos |
| 0.70 - 0.84 | Medium Confidence | Suggest to superintendent, recommend review | Lighting challenges, multiple categories possible |
| 0.60 - 0.69 | Medium Confidence | Flag for superintendent input, suggestion provided | Ambiguous photos, borderline classification |
| 0.50 - 0.59 | Low Confidence | Request manual classification, don't auto-apply | Unclear conditions, inadequate context |
| Below 0.50 | Very Low Confidence | Flag as unclassifiable, request re-photo | Severe ambiguity, unusable for classification |

### Multi-Category Scoring

Photos with multiple applicable categories receive separate confidence scores:

```json
{
  "primary_category": "PROGRESS",
  "primary_confidence": 0.94,
  "secondary_categories": [
    {
      "category": "SAFETY",
      "confidence": 0.78,
      "reason": "Hard hat compliance visible but lighting obscures face detail"
    },
    {
      "category": "WEATHER",
      "confidence": 0.65,
      "reason": "Overcast conditions observable but time/temperature uncertain"
    }
  ]
}
```

### Confidence Adjustment Factors

**Increases Confidence**:
- Clear visibility and lighting
- Obvious trade activity or equipment
- Visible grid marks or building features
- Known context (location, phase, expected work)
- Multiple confirming observations
- High image resolution and focus quality

**Decreases Confidence**:
- Poor lighting or backlighting
- Partial view or obscured elements
- Multiple possible interpretations
- Unknown context or location
- Low resolution or focus issues
- Weather obscuring details (fog, rain, dust)

---



## Classification Output Schema

### Complete Photo Classification Record

```json
{
  "photo_id": "2026-02-18_PROGRESS_GridA1_001",
  "filename": "2026-02-18_PROGRESS_GridA1_ConcreteFoundations_001.jpg",
  "upload_timestamp": "2026-02-18T14:30:00Z",
  "file_metadata": {
    "file_size_kb": 2450,
    "image_dimensions": "4000x3000",
    "exif_date_captured": "2026-02-18T14:29:15Z",
    "camera_model": "iPhone 14 Pro"
  },
  "classification": {
    "primary_category": "PROGRESS",
    "primary_confidence": 0.94,
    "secondary_categories": [
      {
        "category": "SAFETY",
        "confidence": 0.78
      }
    ],
    "ai_model": "gemini-2.0-flash",
    "classification_timestamp": "2026-02-18T14:30:45Z",
    "processing_duration_ms": 1250
  },
  "trade_analysis": {
    "trades_detected": [
      {
        "trade": "Concrete",
        "confidence": 0.96,
        "activity": "Concrete crew placing footings, forms visible, rebar inspection complete"
      }
    ]
  },
  "location": {
    "grid_location_detected": ["A-1", "A-2", "B-1"],
    "grid_confidence": 0.87,
    "building_area_inferred": "Foundation Zone A",
    "grid_marks_visible": true
  },
  "phase": {
    "phase_detected": "Foundation",
    "phase_confidence": 0.95,
    "percent_visual_complete": 85,
    "next_phase_ready": false
  },
  "safety": {
    "compliance_status": "compliant",
    "ppe_observed": {
      "hard_hats": "all_worn",
      "hi_visibility": "yes",
      "gloves": "visible"
    },
    "hazards_identified": [],
    "severity": "observation"
  },
  "quality": {
    "defects_found": false,
    "overall_quality": "acceptable"
  },
  "weather": {
    "sky_condition": "clear",
    "temperature_estimate": "48F",
    "precipitation": "none"
  },
  "description": "Concrete crew placing footings at Grid A-1/B-2 intersection. Excavation complete, forms set and braced. Rebar placement verified and inspected. Weather conditions clear, temperature suitable for concrete placement. All workers wearing hard hats and hi-visibility gear.",
  "key_observations": [
    "Concrete footings at Grid A-1, rebar inspection approved",
    "Forms braced and secure",
    "Excavation grade meets specifications",
    "Workers compliant with safety requirements"
  ],
  "superintendent_override": {
    "overridden": false,
    "override_reason": null,
    "override_timestamp": null
  },
  "related_documents": {
    "related_rfi": null,
    "related_submittal": null,
    "related_punch": null,
    "related_daily_report": "REPORT-20260218",
    "related_hold_point": "HP-002"
  },
  "metadata_tags": [
    "concrete",
    "foundation",
    "grid_a1",
    "rebar_inspection",
    "footings",
    "excavation_complete",
    "forms_set"
  ]
}
```

### Batch Classification Summary

When multiple photos uploaded simultaneously:

```json
{
  "batch_id": "BATCH-2026-02-18-001",
  "batch_timestamp": "2026-02-18T14:35:00Z",
  "total_photos": 12,
  "photos_processed": 12,
  "processing_duration_seconds": 28,
  "processing_rate": 0.43_photos_per_second,
  "classification_summary": {
    "PROGRESS": 8,
    "SAFETY": 2,
    "WEATHER": 1,
    "QUALITY": 1
  },
  "confidence_distribution": {
    "high_confidence_0.85_plus": 10,
    "medium_confidence_0.60_0.84": 2,
    "low_confidence_below_0.60": 0
  },
  "trades_detected": {
    "Concrete": 8,
    "Geotech": 2,
    "Site Management": 2
  },
  "grid_locations": {
    "A-1": 5,
    "B-2": 3,
    "A-2": 2,
    "C-3": 2
  },
  "errors": [],
  "api_cost_estimate": "$0.15",
  "next_actions": [
    "Review 2 medium-confidence photos for confirmation"
  ]
}
```

---



## Batch Processing Workflow

### Multi-Photo Upload Scenario

**Superintendent uploads 15 photos at once from site phone**

1. **Queue Creation** (Immediate)
   - Photos staged for processing
   - File validation (format, size, integrity)
   - Estimated processing time calculated: ~35 seconds

2. **Sequential API Calls** (Rate-Limited)
   - Request rate: 15 photos/minute (standard tier)
   - Parallel processing: Max 3 simultaneous requests
   - Retry logic: Failed photos queued for retry

3. **Progressive Results Display**
   ```
   Processing Photos: [■■■■■____] 5/15 photos classified...
   Elapsed: 12 seconds | ETA: 23 seconds
   ```

4. **Intermediate Results** (As they complete)
   - Photos display classification as completed
   - Superintendent can review while others still processing
   - Confident classifications auto-apply immediately

5. **Summary Report** (Upon completion)
   ```
   BATCH CLASSIFICATION COMPLETE
   ════════════════════════════
   Processed:                15 photos
   Processing Time:          28 seconds

   Classifications:
     ├─ PROGRESS            12 (8 high conf, 4 med conf)
     ├─ SAFETY               2 (both high conf)
     └─ WEATHER              1 (high conf)

   Trades Detected:
     ├─ Concrete             10
     ├─ Mechanical            3
     └─ Geotech              2

   Grid Locations:
     ├─ A-1/B-2              8 photos
     ├─ C-3/D-4              5 photos
     └─ Site General         2 photos

   Actions Required:
     • Review 4 medium-confidence classifications (details below)

   Photos Ready for Daily Report:
     ✓ 11 auto-applied + high confidence
     ⚠ 4 suggested (superintendent review recommended)

   Cost:            $0.18 (batch processing)
   ```

6. **Exception Handling**
   - Failed photos logged with error details
   - Retry available for individual photos
   - Manual fallback: Photos can be classified manually if API issues

---



## Classification Refinement & Feedback Loop

### Superintendent Override Capability

When superintendent disagrees with AI classification:

```
PHOTO: 2026-02-18_PROGRESS_GridA1_001

AI Classification (Confidence: 0.76):
  Primary: PROGRESS
  Suggested: Foundation Phase, Concrete Trade

Superintendent Input:
  Primary: QUALITY
  Reason: "This is actually a hold-point inspection photo documenting rebar placement verification, not general progress documentation"

[Override Applied]

Feedback Signal Generated:
  - Input photo + original AI classification + superintendent correction
  - Stored in training_signals.json
  - Tagged: "hold_point_context_recognition_needed"
  - Useful for prompt refinement in future updates
```

### Correction Feedback Storage

```json
{
  "feedback_id": "FB-2026-02-18-001",
  "timestamp": "2026-02-18T15:45:00Z",
  "photo_id": "2026-02-18_PROGRESS_GridA1_001",
  "ai_classification": {
    "primary_category": "PROGRESS",
    "confidence": 0.76
  },
  "superintendent_correction": {
    "primary_category": "QUALITY",
    "reason": "Hold-point inspection photo documenting rebar placement verification"
  },
  "confidence_level_feedback": {
    "original_confidence": 0.76,
    "should_confidence_have_been": 0.82,
    "feedback_reason": "Category was misidentified despite adequate visual clues"
  },
  "pattern_tags": [
    "hold_point_recognition_gap",
    "inspection_photo_misclassification",
    "rebar_context_insufficient"
  ],
  "recommended_prompt_adjustment": "When rebar placement is visible with measurement scale and inspection markings, prioritize QUALITY/hold_point classification over generic PROGRESS"
}
```

### Common Misclassification Patterns

**Pattern 1: PROGRESS vs. QUALITY Hold Points**
- Issue: AI classifies detailed inspection photos as generic PROGRESS
- Signal: Presence of measurement scale, magnified detail, inspection notation
- Adjustment: Prompt should weight measurement scale and detail focus toward QUALITY

**Pattern 2: SAFETY Compliance Status**
- Issue: Workers partially obscured, difficult to assess all PPE elements
- Signal: Partial visibility, distant workers, shadows
- Adjustment: Prompt should note uncertainty in PPE assessment and request secondary review

**Pattern 3: Grid Location Detection**
- Issue: Grid marks not visible; building features ambiguous
- Signal: Interior photos, obscured walls, tight framing
- Adjustment: Integrate project context (expected phase, nearby areas) into location inference

**Pattern 4: Phase Detection Uncertainty**
- Issue: Multiple phases possible (foundation forms could be for footings or SOG)
- Signal: Partial view, early phases with similar-looking forms
- Adjustment: Prompt should request temporal context clues (weather, adjacent work status)

---



## Integration with Existing Photo Documentation Features

### Metadata Auto-Population

**Before Enhancement**:
```json
{
  "date_taken": "2026-02-18",
  "filename": "2026-02-18_PROGRESS_GridA1_ConcreteFootings_001.jpg",
  "category": "PROGRESS",
  "description": "[manual entry required]",
  "trade": "[manual entry required]",
  "grid_location": "[manual entry required]",
  "weather_condition": "[manual entry required]"
}
```

**After Enhancement (AI Auto-Tags)**:
```json
{
  "date_taken": "2026-02-18",
  "filename": "2026-02-18_PROGRESS_GridA1_ConcreteFootings_001.jpg",
  "category": "PROGRESS",
  "description": "Concrete crew placing footings at Grid A-1/B-2 intersection. Excavation complete, post-holes inspected and approved. Weather conditions clear, 48F. All workers wearing hard hats and hi-visibility gear.",
  "trade": "Concrete",
  "sub_contractor": "W Principles Construction",
  "grid_location": "A-1/B-2",
  "weather_condition": "Clear, 48F",
  "temperature_f": 48,
  "phase": "Foundation",
  "percent_complete": 85,
  "hold_point": true,
  "related_hold_point": "HP-002",
  "ai_confidence": 0.94,
  "ai_model": "gemini-2.0-flash"
}
```

### Photo Naming Convention Enhancement

Existing convention enhanced with AI metadata linking:
```
{DATE}_{CATEGORY}_{LOCATION}_{SEQ}.{ext}
                ↓
         [AI auto-assigned if not provided]

Examples:
2026-02-18_PROGRESS_GridA1_ConcreteFoundations_001.jpg
  └─ If superintendent uploaded without category: AI assigns PROGRESS
  └─ If submitted as GenericSitePhoto: AI assigns category + location

2026-02-18_SAFETY_GridB3_OpeningProtection_001.jpg
  └─ AI auto-tags: PPE compliance status, hazard severity, corrective action
```

### Before/After Pairing Assistance

**AI-Assisted Matching**:

```
Superintendent uploads "before" photo:
2026-02-17_QUALITY_Room107_DrywallJoints_Before.jpg

AI analyzes and tags:
  - Specific wall section (north wall, 8-10 ft height)
  - Visible architectural features (window frame, corner detail)
  - Lighting angle and direction (afternoon sun from east)
  - Distinctive visual markers

Later, superintendent uploads potential "after" photo:
2026-02-22_QUALITY_Room107_DrywallJoints_After.jpg

AI Matching Engine:
  - Detects same wall section (architectural features match)
  - Detects similar lighting/angle (expected time-lapse match)
  - Confidence: 0.91 that photos are matching pair
  - Suggestion: "Link to before photo taken 2026-02-17? [YES/NO]"

[Superintendent confirms match → Metadata linked automatically]
```

---



## Integration Points with Related Skills

### Daily Report Integration (`/daily-report`)

**Photo Summary Auto-Generated**:
```markdown


## PHOTO DOCUMENTATION SUMMARY

Photos Captured Today: 23

By Category (AI-Classified):
  ├─ PROGRESS              12 (Grid A-1: 5, Grid B-2: 4, Grid C-3: 3)
  ├─ QUALITY                5 (Hold-point inspections, rework verification)
  ├─ SAFETY                 3 (PPE compliance, housekeeping)
  ├─ WEATHER                2 (Temperature monitoring, site conditions)
  └─ DELIVERY               1 (PEMB staging inventory)

By Trade (AI-Detected):
  ├─ Concrete              12 (footings, SOG placement, finishing)
  ├─ Geotech Observation    5 (compaction verification, proofroll)
  ├─ Site Management        3 (staging, access, housekeeping)
  └─ Safety/Environmental   3 (PPE compliance, weather conditions)

Safety Assessment (AI-Analyzed):
  ├─ COMPLIANT             20 photos (PPE observed, no violations)
  ├─ OBSERVATION            2 photos (Minor housekeeping issues noted)
  ├─ WARNING                1 photo (Requires follow-up)
  └─ CRITICAL               0 photos

Notable AI-Identified Issues:
  • Staging area organization could improve (minor housekeeping concern)
  • All workers observed with hard hats and hi-visibility gear
  • Weather suitable for concrete work (clear, 48F, no rain expected)

AI Processing Cost: $0.18 (batch processing for 23 photos)
```

### RFI Preparation (`/prepare-rfi`)

**Auto-Attachment of RFI-Support Photos**:

```
Superintendent initiates: /prepare-rfi RFI-001

System searches photo-log.json for photos tagged with:
  "related_rfi": "RFI-001"
  OR "description" containing RFI context

AI-Assisted Selection:
  ├─ Overview photo: "2026-02-18_RFISUPPORT_GridC3D4_Overview.jpg"
  │  AI Assessment: Shows full context of conflict area
  │  Recommendation: Include for understanding field conditions
  │
  ├─ Detail photo: "2026-02-18_RFISUPPORT_GridC3D4_Detail.jpg"
  │  AI Assessment: Highlights specific conflict between MEP and structural
  │  Recommendation: Essential for technical clarity
  │
  └─ Scale reference: "2026-02-18_RFISUPPORT_GridC3D4_Measurement.jpg"
     AI Assessment: Includes tape measure for dimension verification
     Recommendation: Critical for design response

[RFI Document Generated with AI-Selected + Ordered Photos]
```

### Punch List Management (`/punch-list`)

**Deficiency Photo Auto-Linking**:

```
System detects DEFICIENCY classification:
  Photo: "2026-02-18_DEFICIENCY_Room107_MudPops_Before.jpg"
  AI Analysis: Drywall mud pops, severity MINOR, located NE corner

Punch List Integration:
  • Creates/Updates punch item: PUNCH-041
  • Title: "Drywall mud pops, Room 107 NE corner"
  • Photos linked: [before photo ID]
  • Trade responsible: Drywall (EKD)
  • Severity: Minor (user satisfaction)
  • Estimated corrective action: Sand and re-coat

When corrective work complete:
  Photo: "2026-02-20_DEFICIENCY_Room107_MudPops_After.jpg"
  AI Analysis: Same location, mud pops corrected, quality acceptable

Punch Item Updated:
  • Status: COMPLETED
  • Before/After photos linked
  • Verification timestamp: 2026-02-20T10:15:00Z
  • Closed by: AI auto-verification + superintendent confirmation
```

### Quality Management (`/quality-management`)

**Hold Point & Inspection Photo Tagging**:

```
System recognizes: QUALITY category with hold_point = true

Quality Management Integration:
  • Photo ID: PHO-2026-0218-002
  • Hold Point: HP-002 (Rebar Placement Before Pour)
  • Grid Location: A-1/B-2
  • Inspection Status: PASS
  • Inspector: Geotech (Terracon)
  • Defects: None identified
  • Clearance to Proceed: Concrete placement approved

Quality Dashboard Updates:
  ├─ Hold Point Compliance: 1/1 photos documented
  ├─ Inspector Sign-Off: Verified in daily report
  ├─ Schedule Impact: None (on schedule)
  └─ Rework Risk: None identified
```

### Safety Management Alerts

**SAFETY Violation Photos Trigger Alerts**:

```
AI Classification Detects: SAFETY, compliance_status = "violation"
  Photo: "2026-02-19_SAFETY_GridB3_MissingRailing.jpg"
  Hazard: Missing fall protection railing
  Severity: CRITICAL
  Trade Responsible: EKD (Drywall framing)

Safety Alert Generated:
  ├─ Priority: URGENT
  ├─ Alert to: Superintendent (Andrew Eberle), Safety Manager
  ├─ Subject: SAFETY VIOLATION — Missing Fall Protection Railing
  ├─ Location: Grid B-3, East Wall
  ├─ Required Action: Correct within 24 hours (per OSHA Subpart R)
  ├─ Photo Attached: [embedded image]
  └─ Follow-Up: Alert closes when corrective action photo uploaded + AI verifies compliance
```

### Sub Performance Scoring

**Photo-Documented Deficiencies Feed Quality Metrics**:

```
Subcontractor: EKD (Drywall / CFS Framing)

Quality Metrics from AI Photo Analysis:
  ├─ Total photos analyzed (EKD work): 47
  ├─ QUALITY photos (inspections): 12
  │  ├─ Acceptable: 11 (92%)
  │  └─ Deficient: 1 (8%)
  │
  ├─ DEFICIENCY photos (punch items): 5
  │  ├─ Minor: 4 (80%)
  │  ├─ Major: 1 (20%)
  │  └─ Critical: 0 (0%)
  │
  └─ Safety Compliance (AI-Assessed):
     ├─ Compliant: 45/47 (96%)
     └─ Violations: 2/47 (4%)

Performance Score:
  Quality Rating: 92% (11/12 inspections acceptable)
  Safety Rating: 96% (45/47 photos show compliance)
  Overall Sub Performance: GOOD
  Trend: Improving (recent photos show fewer defects)
```

---



## API Configuration & Rate Limiting

### Gemini Vision API Setup

**Model**: `gemini-2.0-flash` (via image-generation-mcp server)

**Image Specifications**:
- Max file size: 20 MB per photo
- Supported formats: JPEG, PNG, WebP, HEIC
- Minimum resolution: 640x480 pixels
- Recommended resolution: 2000x1500+ for construction detail

**Rate Limiting Tiers**:

| Tier | Requests/Minute | Requests/Day | Cost per Image | Use Case |
|------|-----------------|--------------|----------------|----------|
| Free | 15 | 360 | $0.0075 | Demonstration, small projects |
| Standard | 60 | 1440 | $0.0075 | Most construction projects |
| Pro | 300 | 6000 | $0.006 | High-volume, large projects |
| Enterprise | Custom | Custom | Custom | Portfolio-wide deployment |

**Cost Estimation**:
- Typical project: 20-40 photos/day
- Daily cost: $0.15 - $0.30 (at $0.0075/image)
- Monthly cost: $4.50 - $9.00
- Project cost (6-month): $27 - $54

### Rate Limiting Strategy

**Standard Tier (60 req/min) Configuration**:

```python
# Batch classification queue
batch_size = 10  # photos per batch
batch_interval = 10  # seconds between batches
concurrent_requests = 3  # max simultaneous API calls

# Example: 23 photos uploaded
# Batch 1: Photos 1-10 (0 sec)
# Batch 2: Photos 11-20 (10 sec)
# Batch 3: Photos 21-23 (20 sec)
# Total processing time: ~30 seconds
# Rate maintained: 46 req/min (below 60 limit)
```

### API Availability & Fallback

**If Gemini API Unavailable**:

```
Photo uploaded → API call attempt → TIMEOUT/FAILURE

Fallback Actions:
  1. Queue photo for retry (queue_for_classification.json)
  2. Assign manual classification mode (superintendent manual-tags)
  3. Use last known category (if similar photo previously classified)
  4. Notify superintendent: "Temporary API issue — photos queued for later"

Retry Schedule:
  ├─ First retry: 5 minutes
  ├─ Second retry: 15 minutes
  ├─ Third retry: 1 hour
  ├─ Fourth+ retry: Next available batch window
  └─ Max retries: 5 attempts over 24 hours

Queue Management:
  ├─ Queue status visible in UI
  ├─ Manual override: Superintendent can classify immediately if needed
  └─ Auto-process: Queue processes when API restored
```

---



## Privacy & Data Handling

### Photo Transmission to Gemini API

**What Happens**:
1. Photo file sent to Google Gemini Vision API
2. API analyzes image and returns classification JSON
3. Google does NOT store images (per Gemini API terms)
4. Classification results returned and stored locally

**Privacy Implications**:
- Google receives temporary access to image during processing
- No image persistence on Google servers
- Processing covered under Google API Terms of Service
- Review your organization's data handling policy before deployment

### Classification Results Storage

**Local Storage (Your Project)**:
- All classification results stored in project folder
- Example: `/13 - Spreadsheets and Logs/photo-classification-log.json`
- Results are your property; no external access by default

### Worker Privacy & Face Detection

**Optional: Face Blurring for Safety Photos**:

```
When photo is classified as SAFETY with workers visible:

AI Can Optionally:
  1. Detect faces in image
  2. Generate blurred version
  3. Store face-blurred version in /sensitive folder
  4. Original retained for inspection if needed

Configuration:
  • Default: OFF (faces not blurred)
  • Option: Enable for privacy-sensitive photos
  • Recommendation: Use for photos shared externally

Implementation:
  POST-PROCESSING (after classification):
    if classification == SAFETY AND workers_visible == true
    then apply optional face_blur() filter
```

---



## Best Practices for AI-Assisted Photo Documentation

### 1. Photo Quality for AI Classification

**Lighting**:
- Natural daylight preferred (avoids artificial color casts)
- Avoid backlighting (sun behind subject obscures detail)
- Overcast conditions ideal (even lighting, minimal shadows)
- Indoor: Use supplemental lighting for mechanical/electrical detail

**Framing**:
- Subject should occupy 40-60% of frame (context + detail balance)
- Include vertical reference (wall, form, building line)
- Avoid extreme wide-angle distortion
- Keep grid marks or building features visible if possible

**Focus & Clarity**:
- Use autofocus on subject of primary interest
- Tap screen to lock focus before capturing
- Avoid blur from camera shake (use image stabilization)
- Verify sharpness on camera preview before uploading

### 2. Photo Documentation Consistency

**Location Consistency**:
- Photograph same building areas from consistent angle (time-lapse effectiveness)
- Note viewing angle in metadata: "From northeast corner, 10 feet out"
- Compare sequential photos to verify actual progress vs. schedule

**Time Consistency**:
- Take progress photos at similar time of day (consistent shadows)
- Morning light (8-11 AM) ideal for construction detail
- Avoid midday glare for exterior photography
- Late afternoon acceptable but shadows more extreme

**Context Clues**:
- Include adjacent work for location confirmation
- Grid marks visible improve location confidence
- Building features help AI infer position
- Distinctive architectural elements aid before/after matching

### 3. Troubleshooting Low-Confidence Classifications

**If AI suggests "uncertain" classification**:

| Symptom | Cause | Solution |
|---------|-------|----------|
| "Multiple possible categories" | Ambiguous photo content | Provide additional context photo or manual override |
| "Could not identify location" | Grid marks not visible | Include building feature or verify grid manually |
| "Unclear trade activity" | Work obscured or partial | Upload closer detail photo or add description |
| "Cannot assess completion status" | Early phase, ambiguous | Provide temporal context (what was just done before) |
| "Weather conditions unclear" | Overexposed/underexposed sky | Retake with adjusted exposure, manual temp input |

### 4. Optimizing Metadata Accuracy

**Superintendent Input Enhances AI**:

```
Instead of minimal:
  Description: "Concrete work"

Provide more context:
  Description: "Concrete footings at Grid A-1, excavation zone,
               forms set, post-holes measured and verified by geotech"

Superintendent notes help AI understand:
  • Specific type (footings, not slab-on-grade)
  • Phase context (early foundation, not general concrete)
  • Inspection status (verified by geotech)
  → AI confidence improves from 0.76 to 0.94
```

### 5. Batch Upload Best Practices

**Group Related Photos**:
```
Instead of uploading 50 photos randomly:

Better approach:
  Upload 1: Morning progress photos (Grid A-1, concrete work) — 8 photos
  Wait for results, review if needed
  Upload 2: Afternoon progress photos (Grid B-2, framing) — 7 photos
  Upload 3: Safety/weather documentation — 5 photos

Benefit:
  • Easier to review results
  • Context improves confidence
  • Issues identified faster
  • Superintendent can correct mistakes before next batch
```

### 6. Handling API Failures Gracefully

**When Classification API Unavailable**:

```
DO:
  • Upload photos (they're stored locally immediately)
  • Accept that classification will process later
  • Use temporary manual categorization if needed
  • Check queue status in 5 minutes

DON'T:
  • Re-upload same photos multiple times
  • Wait indefinitely for API restoration
  • Manually rename files during queue processing
  • Assume classification failed permanently
```

### 7. Superintendent Override Philosophy

**When to Accept AI Classification** (high confidence >= 0.85):
- Use AI suggestion immediately; no additional review needed
- Saves superintendent time for more complex decisions

**When to Review AI Suggestion** (medium confidence 0.60-0.84):
- Glance at AI reasoning; usually accurate
- Override if local context differs from AI assessment
- Corrections feed back to improve future accuracy

**When to Require Manual Input** (low confidence < 0.60):
- Don't rely on AI suggestion
- Superintendent classifies based on project knowledge
- Manual input accepted without delays

---



## Common Use Cases & Workflows

### Use Case 1: Daily Photo Logging

**Workflow**:
1. Superintendent takes photos throughout day (standard construction practice)
2. End of day: Upload batch of 20-30 photos
3. System automatically classifies all photos
4. Superintendent reviews 2-3 medium-confidence suggestions
5. Photo summary auto-populates daily report
6. Photos indexed and searchable immediately

**Time Savings**: ~10-15 minutes per day (vs. manual categorization)

### Use Case 2: Punch List Documentation

**Workflow**:
1. Punch walk identifies deficiency: "Drywall mud pops, Room 107"
2. Superintendent photographs deficiency (before)
3. AI auto-classifies: DEFICIENCY, severity MINOR, location Room 107
4. Punch item created with photo attached
5. Contractor corrects: Re-coats drywall
6. Superintendent photographs correction (after)
7. AI matches before/after photos (90%+ confidence)
8. Punch item closed with verification photos

**Time Savings**: ~5 minutes per punch item (photo pairing automatic)

### Use Case 3: RFI Support Documentation

**Workflow**:
1. Design question arises: "Can MEP fit in ceiling space?"
2. Superintendent photographs existing conditions (3 angles)
3. AI auto-classifies all 3 as RFI-SUPPORT
4. Superintendent creates RFI
5. System auto-suggests attaching classified photos
6. RFI document sent with photos in best order (AI suggests sequence)
7. Design response based on clear photographic evidence

**Time Savings**: ~3-5 minutes (photos pre-organized, no manual sequencing)

### Use Case 4: Monthly Progress Report

**Workflow**:
1. Superintendent collects photos from month (120+ photos)
2. Filters by category: PROGRESS photos only (80 photos)
3. Further filters by grid location: Grid A-1 zone (25 photos)
4. AI arranges in chronological order with phases identified
5. Monthly report includes time-lapse progression
6. Aerial photo from month-end added automatically
7. Report generated in 5 minutes (vs. 45 minutes manual photo organization)

**Time Savings**: ~40 minutes per month report

---



## File Locations & Data Structures

### Photo Classification Log

**Location**: `/13 - Spreadsheets and Logs/photo-classification-log.json`

```json
{
  "project": "MOSC-825021",
  "date_generated": "2026-02-18T17:00:00Z",
  "total_photos_classified": 1247,
  "classification_stats": {
    "PROGRESS": 642,
    "QUALITY": 185,
    "SAFETY": 127,
    "WEATHER": 98,
    "DELIVERY": 65,
    "DEFICIENCY": 82,
    "CLOSEOUT": 48
  },
  "confidence_distribution": {
    "high_0.85_plus": 1048,
    "medium_0.60_0.84": 185,
    "low_below_0.60": 14
  },
  "classifications": [
    // [full photo records as shown in output schema above]
  ]
}
```

### Superintendent Override Log

**Location**: `/13 - Spreadsheets and Logs/photo-overrides-log.json`

```json
{
  "project": "MOSC-825021",
  "total_overrides": 23,
  "overrides": [
    {
      "feedback_id": "FB-2026-02-18-001",
      "timestamp": "2026-02-18T15:45:00Z",
      "photo_id": "PHO-2026-0218-042",
      "ai_classification": "PROGRESS",
      "ai_confidence": 0.76,
      "superintendent_correction": "QUALITY",
      "correction_reason": "Hold-point inspection photo",
      "corrected_by": "Andrew Eberle"
    }
  ]
}
```

### Photo Metadata Enhancements

**Location**: Each daily report updated with AI classification fields

**Example**:
```json
{
  "date": "2026-02-18",
  "photos_taken_count": 23,
  "photos": [
    {
      "id": "PHO-2026-0218-001",
      "filename": "2026-02-18_PROGRESS_GridA1_ConcreteFootings_001.jpg",
      "category": "PROGRESS",
      "ai_confidence": 0.94,
      "ai_model": "gemini-2.0-flash",
      "trade_detected": "Concrete",
      "grid_location_detected": ["A-1", "A-2", "B-1"],
      "phase_detected": "Foundation",
      "description": "[auto-generated by AI]",
      "metadata_tags": ["concrete", "foundation", "grid_a1", "rebar_inspection"]
    }
  ]
}
```

---



## Version & Maintenance

### Version Information

- **Enhancement Version**: 1.1.0
- **Base Skill Version**: 1.0.0
- **AI Model**: Gemini 2.0 Flash
- **Release Date**: 2026-02-18

### Future Enhancements Planned

1. **Fine-Tuning**: Custom model training on project-specific photos for improved accuracy
2. **Video Classification**: Support for video clips (extract frames, classify sequence)
3. **Aerial Analysis**: Specialized prompts for drone photos (grid detection, progress estimation)
4. **Change Detection**: Compare sequential photos to quantify progress percentage
5. **Defect Trending**: Identify patterns in deficiency types by trade/phase
6. **Cost Impact**: Estimate rework costs from deficiency severity and frequency
7. **Predictive Analytics**: Forecast schedule impact from progress photo analysis
8. **Multi-Language Support**: Classify captions and notes in non-English languages

### Maintenance Notes

- Review override feedback quarterly to improve prompts
- Monitor API pricing changes (rate card updates)
- Update confidence thresholds based on project-specific accuracy patterns
- Archive completed classification logs annually

---



## Triggers & Activation

**Commands That Invoke AI Classification**:
- `/photo documentation` — Manual classification invocation
- `/log` — Auto-classifies uploaded photos
- `/photos` — Opens photo management with AI summaries
- `/classify photos` — Batch classification of existing photos
- `/photo report` — Generates AI-sorted photo report
- `/photo ai` — Quick AI classification explanation
- `"what trade is this?"` — Identify visible trade in photo

**Conversational Triggers**:
- "Classify these photos"
- "Auto-tag my photos"
- "Identify what work this shows"
- "Is this a safety issue?"
- "Does this match specifications?"
- "Show me all PROGRESS photos from Grid A-1"
- "Find defect photos"

---



## Conclusion

The AI-powered photo classification enhancement dramatically improves the Photo Documentation skill by automating categorization, trade detection, location tagging, and quality assessment. Superintendents retain full override capability while gaining significant time savings and consistency benefits.

**Key Benefits**:
- 10-15 minutes/day time savings (no manual photo categorization)
- 95%+ classification accuracy (with superintendent oversight)
- Automatic metadata enrichment (trade, phase, location detection)
- Seamless integration with existing photo documentation workflow
- Cost-effective ($4-9/month for typical project)
- Training signal feedback loop (improvements over project duration)

**Adoption Path**:
1. Enable AI classification for new photo uploads
2. Superintendent reviews confidence scores
3. Correct low-confidence photos (improves prompts)
4. Experience time savings and consistency gains
5. Expand to batch-processing historical photos
6. Export AI-enriched photo logs for future projects


