---
name: photo-documentation
description: >
  Comprehensive photo documentation system for construction progress tracking with AI-powered auto-classification. Uses Gemini Vision API to automatically categorize photos, identify construction phase, detect visible trades, tag location/grid references, and assess safety compliance. Handles photo categorization, metadata tagging, before/after pairing, naming conventions, progress tracking by area, RFI/submittal documentation, drone/aerial guidelines, and chain of custody. Triggers: "photo documentation", "site photos", "progress photos", "photo log", "photo report", "document photos", "photo classification", "classify photos", "auto-tag photos", "photo AI", "identify photo", "what trade is this".
version: 1.1.0
---

# Photo Documentation Skill — AI Classification Enhancement

## Overview

The Photo Documentation skill now includes **automatic AI-powered classification** using the Gemini 2.0 Flash Vision API. When photos are uploaded or processed through `/log` or `/photos` commands, the system automatically sends each image to Gemini Vision for intelligent classification, trade detection, safety assessment, and progress tracking.

This enhancement eliminates manual categorization for most photos while maintaining superintendent override capability and learning from corrections.

---

## AI Classification Architecture

### How It Works

1. **Photo Upload**: Superintendent uploads photos via `/log`, `/photos`, or drag-and-drop interface
2. **API Dispatch**: Photos queued for Gemini Vision processing (max 20MB per image)
3. **Parallel Classification**: Multiple photos processed simultaneously with rate limiting (15-60 req/min depending on tier)
4. **Confidence Scoring**: Each classification receives confidence score (0.0-1.0)
5. **Metadata Generation**: Results stored as photo metadata tags and crosslinked to related systems
6. **Override Capability**: Superintendent can accept or reject AI classifications; corrections feed back as training signals

### Processing Flow

```
Photo Upload
    ↓
[Queue for Classification]
    ↓
[Gemini Vision API Call]
    ↓
[Receive Classification Results]
    ↓
[Score Confidence Level]
    ├─ >= 0.85  → Auto-apply (no confirmation needed)
    ├─ 0.60-0.84 → Suggest to superintendent (review recommended)
    └─ < 0.60   → Flag uncertain (requires manual classification)
    ↓
[Store Metadata + Tags]
    ↓
[Link to Related Systems]
    ↓
[Add to Daily Report Summary]
```

---

## Classification Categories with AI Detection Signals

### 1. PROGRESS — Active Construction Visible

**Purpose**: Track construction advancement, work-in-progress activities, phased completion.

**What AI Detects**:
- Active worker activity, equipment operation, material placement
- Exposed structural elements, framing, concrete, mechanical runs
- Work progression compared to previous phases
- Trade-specific activities (concrete crew, steel crew, HVAC installation)
- Completed work relative to building area

**Auto-Tags Applied**:
- `phase_detected`: Foundation | Structural | MEP | Interiors | Finishes | Closeout
- `trade_detected`: Concrete | Structural Steel | MEP | Drywall | Flooring | etc.
- `grid_location_detected`: A-1, B-2, C-3-D-4 (inferred from visible grid marks or building features)
- `percent_visual_complete`: 0-100% estimate of visible work in frame
- `activity_description`: Auto-generated description of observed construction activity
- `sub_contractor_inferred`: (If visible signage or equipment markings)

**Confidence Indicators**:
- High confidence: Clear work in progress, identifiable trades, visible phase markers
- Medium confidence: Obscured work, incomplete view, weather/lighting challenges
- Low confidence: Empty site, ambiguous structures, unclear progress state

**Example AI Output**:
```json
{
  "primary_category": "PROGRESS",
  "trade_detected": "Concrete",
  "phase_detected": "Foundation",
  "grid_location_detected": ["A-1", "A-2", "B-1"],
  "percent_visual_complete": 85,
  "activity_description": "Concrete crew finishing Grade-level SOG at Grid A-1/B-2. Finished surface visible in foreground with final troweling in progress. Rebar placement complete in background. Weather conditions clear.",
  "confidence": 0.94
}
```

---

### 2. SAFETY — PPE, Fall Protection, Hazards, Compliance

**Purpose**: Document safety conditions, corrective measures, worker compliance, environmental hazards.

**What AI Detects**:
- Personal Protective Equipment (PPE) presence/absence: hard hats, safety glasses, hi-vis, gloves, steel-toe boots
- Fall protection: guardrails, safety nets, harnesses (if visible)
- Hazardous conditions: unsecured openings, exposed electrical, loose materials, tripping hazards
- Environmental hazards: standing water, icy surfaces, weather exposure, inadequate ventilation
- Equipment operation: forklift operation, crane safety, power tool usage
- Site housekeeping: organized/cluttered, debris management, storage conditions
- Signage visibility: warning signs, barricades, access control

**Auto-Tags Applied**:
- `compliance_status`: compliant | violation | concern | observation | near_miss
- `hazard_type`: fall | electrical | stored_material | chemical | thermal | environmental | ergonomic | housekeeping
- `ppe_violations`: [hard_hat_missing, gloves_missing, hi_vis_missing, etc.]
- `corrective_needed`: true/false + specific action
- `severity`: observation | warning | critical
- `trade_responsible`: (Inferred from visible work and hazard proximity)

**Confidence Indicators**:
- High confidence: Clear PPE status, obvious hazards, visible safety equipment
- Medium confidence: Partial visibility, distant workers, unclear hazard type
- Low confidence: Obscured views, small figures, ambiguous conditions

**Example AI Output**:
```json
{
  "primary_category": "SAFETY",
  "secondary_categories": ["PROGRESS"],
  "compliance_status": "compliant",
  "ppe_observations": [
    {
      "hazard_type": "fall_protection",
      "observation": "All visible workers wearing hard hats",
      "status": "compliant",
      "confidence": 0.98
    },
    {
      "hazard_type": "housekeeping",
      "observation": "Minor debris accumulation near equipment staging area. No immediate trip hazard.",
      "status": "observation",
      "confidence": 0.85
    }
  ],
  "corrective_needed": false,
  "severity": "observation",
  "confidence": 0.91
}
```

---

### 3. QUALITY — Defects, Alignment, Finish, Workmanship Issues

**Purpose**: Verify work against specifications, document inspection findings, identify deficiencies.

**What AI Detects**:
- Visible defects: concrete cracks/spalling, drywall damage, finish imperfections, paint issues
- Alignment issues: warping, misalignment of components, gap inconsistencies
- Surface quality: smoothness, flatness, texture consistency, color uniformity
- Workmanship quality: joint consistency, detail execution, adherence to visible standards
- Hold point completion: rebar placement verification, embedment confirmation, surface prep adequacy
- Dimension/tolerance: spacing consistency, offset accuracy (if measurable)

**Auto-Tags Applied**:
- `defect_type`: crack | spall | gap | misalignment | color_variation | texture_issue | warping | damage
- `severity`: minor (cosmetic) | major (functional impact) | critical (safety/structural)
- `location_detail`: specific area within frame (e.g., "NE corner", "upper left", "joint line")
- `trade_responsible`: Concrete | Drywall | Flooring | Mechanical | Electrical
- `spec_reference`: Likely spec section (e.g., "03 20 00 Concrete Finishes", "09 29 00 Gypsum Board")
- `rework_required`: true/false
- `comparison_needed`: true/false (if before/after pair needed)

**Confidence Indicators**:
- High confidence: Clear visible defect, obvious severity, spec violation visible
- Medium confidence: Potential issue (angle/lighting dependent), requires closer inspection
- Low confidence: Minor variation (normal within tolerance), inconclusive evidence

**Example AI Output**:
```json
{
  "primary_category": "QUALITY",
  "defect_found": true,
  "defects": [
    {
      "defect_type": "drywall_joint",
      "severity": "minor",
      "description": "Taping joint compound shows slight shrinkage in upper left area of wall. Typical for first coat, requires secondary coat verification.",
      "location_detail": "Upper left quadrant, vertical joint line at approximately 10 feet height",
      "trade_responsible": "Drywall",
      "rework_required": true,
      "specification_reference": "09 29 00 Gypsum Board Finishes",
      "confidence": 0.82
    }
  ],
  "hold_point_status": "pending_verification",
  "confidence": 0.79
}
```

---

### 4. WEATHER — Sky Conditions, Precipitation, Temperature, Site Impact

**Purpose**: Document environmental conditions affecting work, schedule impacts, material protection.

**What AI Detects**:
- Sky conditions: clear, cloudy, overcast, precipitation (rain, snow, sleet)
- Precipitation evidence: wet surfaces, standing water, drainage flow, saturated soil
- Temperature indicators: frost/ice (visual signs), steam (warm work in cold weather)
- Wind indicators: dust/debris movement, flag/banner movement, material movement
- Sun position: shadow patterns indicating time of day, glare intensity
- Site drainage: water flow patterns, ponding areas, drainage effectiveness
- Material exposure: covered/uncovered, weather protection adequacy

**Auto-Tags Applied**:
- `condition`: clear | partly_cloudy | overcast | rain | snow | frost | wind_visible | dust
- `precipitation_observed`: none | light_rain | moderate_rain | heavy_rain | snow | mixed
- `impact_on_work`: none | delay_likely | stop_work | preparation_needed
- `temperature_estimate`: cold (<32F) | cool (32-50F) | moderate (50-70F) | warm (70-85F) | hot (>85F)
- `drainage_status`: adequate | ponding | saturated | flooded
- `material_protection`: exposed | partially_covered | fully_covered
- `work_affected_trade`: (If work must pause or modify due to weather)

**Confidence Indicators**:
- High confidence: Clear sky conditions, obvious precipitation/temperature indicators, visible weather effects
- Medium confidence: Transitional conditions, lighting/shadow uncertainty, minor precipitation
- Low confidence: Overexposed/underexposed sky, unclear conditions, time-of-day estimation

**Example AI Output**:
```json
{
  "primary_category": "WEATHER",
  "conditions": {
    "sky_condition": "overcast",
    "precipitation": "none",
    "precipitation_recent": true,
    "precipitation_evidence": "wet_surfaces_visible",
    "standing_water": true,
    "standing_water_location": "low_points_in_excavation_zone",
    "temperature_estimate": "45-50F",
    "temperature_confidence": 0.72,
    "wind_visible": false
  },
  "drainage_assessment": {
    "status": "adequate",
    "water_flow": "directed_to_sump",
    "ponding_areas": "minimal"
  },
  "work_impact": {
    "impact_on_work": "none",
    "work_may_be_affected": false,
    "trades_working": ["Concrete", "Geotech_Observation"]
  },
  "confidence": 0.88
}
```

---

### 5. DELIVERY — Trucks, Materials, Equipment, Staging Conditions

**Purpose**: Document material/equipment arrivals, condition upon receipt, placement on site.

**What AI Detects**:
- Vehicle type: concrete truck, delivery truck, equipment hauler, crane truck
- Material visible: pallets, bundles, equipment, structural members, mechanical units
- Quantity assessment: single vs. multiple units, full truck vs. partial load
- Condition observation: damage, dents, staining, weathering, packaging integrity
- Storage condition: protected/exposed, organized/haphazard, location appropriateness
- Branding/markings: supplier visible, product identification, certification plaques
- Unloading activity: equipment/personnel present, placement process ongoing

**Auto-Tags Applied**:
- `material_type`: concrete | steel | mechanical | electrical | finish_materials | equipment
- `supplier_detected`: (If signage/markings visible)
- `quantity_estimate`: single | multiple | truck_load_estimate
- `delivery_condition`: good | minor_damage | major_damage | rejected
- `storage_location`: grid_reference (inferred) | laydown_yard | indoor_staging
- `storage_condition`: protected | exposed | temperature_sensitive_risk
- `unloading_status`: in_progress | complete | staged_for_unload

**Confidence Indicators**:
- High confidence: Clear material type, visible branding, obvious condition, readable markings
- Medium confidence: Partially visible material, unclear supplier, condition uncertain
- Low confidence: Distant view, obscured markings, ambiguous material type

**Example AI Output**:
```json
{
  "primary_category": "DELIVERY",
  "material": {
    "type": "mechanical_equipment",
    "specific_items": ["Air Handling Unit (AHU)", "Ductwork sections"],
    "supplier_detected": "Davis and Plomin (inferred from vehicle/signage)",
    "manufacturer_visible": "Carrier (visible on equipment)",
    "quantity": "AHU x1, Ductwork sections x8"
  },
  "delivery_condition": {
    "condition_assessment": "good",
    "visible_damage": false,
    "packaging_integrity": "intact",
    "weathering": "none_visible"
  },
  "unloading_activity": {
    "status": "in_progress",
    "equipment_present": true,
    "equipment_type": "Material handler, forklift"
  },
  "storage": {
    "location_detected": "Grid B2, indoor_staging_area",
    "organization": "organized",
    "weather_protection": "covered",
    "temperature_sensitive": false
  },
  "confidence": 0.89
}
```

---

### 6. DEFICIENCY — Damage, Incorrect Installation, Code Violations, Punch Items

**Purpose**: Document punch list items, repairs, and corrective work with severity assessment.

**What AI Detects**:
- Damage: cracks, breaks, gouges, stains, deterioration, previous water damage
- Installation errors: incorrect assembly, backwards installation, misaligned components
- Code violations: spacing violations, support inadequacy, missing fasteners/connections
- Finishing issues: incomplete work, skipped steps, failed materials
- Safety concerns: exposed edges, missing guards, inadequate bracing
- Scope deviation: work performed but not per plan/spec

**Auto-Tags Applied**:
- `deficiency_type`: damage | installation_error | code_violation | incomplete | safety_concern | deviation
- `severity`: minor (cosmetic, user satisfaction) | major (function impaired) | critical (safety/code)
- `trade_responsible`: (Inferred from work type)
- `corrective_action`: required | recommended | optional
- `photo_pair_needed`: true/false (before/after documentation)
- `punch_reference`: (If already logged as punch item)
- `cost_impact_estimate`: low | medium | high | unknown

**Confidence Indicators**:
- High confidence: Clear deficiency, obvious impact, visible violation
- Medium confidence: Potential issue, context-dependent severity, angle-dependent assessment
- Low confidence: Ambiguous condition, unclear severity, requires expert review

**Example AI Output**:
```json
{
  "primary_category": "DEFICIENCY",
  "deficiency_details": {
    "type": "installation_error",
    "description": "HVAC return air duct installation shows misalignment at connection point. Return collar offset approximately 0.75 inches from planned centerline per shop drawings.",
    "location": "Grid B-3, mechanical room ceiling cavity",
    "specific_area": "northeast corner of return air plenum"
  },
  "severity": "major",
  "reason_severity": "Misalignment may impair airflow distribution and system balancing. Could affect comfort and efficiency.",
  "trade_responsible": "Mechanical (Davis and Plomin)",
  "corrective_action_required": true,
  "corrective_action_description": "Re-install return collar to proper centerline. Rework ductwork connection as needed.",
  "before_after_needed": true,
  "photo_pair_suggestion": true,
  "estimated_cost_impact": "medium",
  "confidence": 0.86
}
```

---

### 7. CLOSEOUT — Completed Areas, Final Finishes, Punch Item Verification

**Purpose**: Document completed work, remaining punch items, final conditions for turnover.

**What AI Detects**:
- Finished spaces: flooring complete, wall finishes applied, trim installed, hardware mounted
- Equipment installation completion: all equipment visible, mounted, labeled
- System functionality indicators: units installed, connections visible, controls visible
- Completion status: work appears substantially complete, minor items remaining, major gaps
- Cleanliness/condition: clean/clutter, packaging removed, site-ready appearance
- As-built verification: equipment location, final configuration, deviation documentation

**Auto-Tags Applied**:
- `completion_status`: substantially_complete | minor_punch_remaining | major_work_remaining
- `area_name`: Room identifier, zone, building section
- `visible_punch_items`: [list of identified minor deficiencies/incomplete tasks]
- `systems_complete`: [electrical, mechanical, plumbing, fire_alarm, etc.]
- `finish_quality`: clean | acceptable | needs_cleanup
- `ready_for_owner_use`: true/false
- `punchlist_count_estimate`: number of visible minor items

**Confidence Indicators**:
- High confidence: Space substantially complete, finish quality obvious, systems visible and complete
- Medium confidence: Unclear whether minor items exist, completion status transitional
- Low confidence: Early finishes phase, many variables affect completion status

**Example AI Output**:
```json
{
  "primary_category": "CLOSEOUT",
  "space": {
    "area_name": "Room 107 - Resident Suite",
    "floor_level": 1,
    "grid_location": "B-2",
    "room_type": "Resident Bedroom"
  },
  "completion_assessment": {
    "overall_status": "substantially_complete",
    "percent_complete_estimate": 95,
    "major_work_remaining": false,
    "minor_items_visible": true
  },
  "systems_complete": {
    "flooring": true,
    "wall_finishes": true,
    "ceiling_finishes": true,
    "doors_hardware": true,
    "light_fixtures": true,
    "receptacles": true,
    "plumbing_fixtures": true,
    "hvac": true
  },
  "punch_items_visible": [
    "Door frame caulking gap at northeast corner",
    "Light fixture lens trim ring installation",
    "Floor finish touch-up in SW corner"
  ],
  "punchlist_count": 3,
  "cleanliness": "clean",
    "ready_for_handoff": true,
  "confidence": 0.91
}
```

---


---

> **Extended reference**: Detailed examples, templates, scoring rubrics, and best practices are in `references/skill-detail.md`.
