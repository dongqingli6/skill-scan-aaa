# Photo Naming Convention & Workflow Template

## Photo Naming Formula

### Core Format
```
{DATE}_{CATEGORY}_{LOCATION}_{SEQ}.{ext}
```

### Field Specifications

#### DATE (Required)
- **Format**: `YYYY-MM-DD` (ISO 8601)
- **Length**: 10 characters
- **Sorting**: Chronological order automatically
- **Examples**: `2026-02-18`, `2026-03-05`, `2026-07-20`

#### CATEGORY (Required)
- **Format**: All caps abbreviation or full word
- **Length**: 3-12 characters (avoid spaces)
- **Valid Categories**:
  - `PROGRESS` — Construction advancement by area/trade
  - `SAFETY` — Hazard documentation, compliance, protective systems
  - `QUALITY` — Inspection points, finish verification, defect documentation
  - `WEATHER` — Site conditions, temperature, precipitation, wind
  - `DELIVERY` — Material/equipment arrival, staging, condition documentation
  - `RFISUPPORT` — Field conditions supporting RFI documentation
  - `SUBMITTAL` — Product samples, installed condition, conformance
  - `DEFICIENCY` — Punch list items, before/after corrections
  - `ASBUILT` — Final installed conditions, deviation documentation
  - `AERIAL` — Drone/overhead photography from height

#### LOCATION (Conditional)
- **Format**: Grid reference (preferred) OR Building area OR Room number
- **Length**: 4-15 characters
- **Grid Reference** (preferred for large projects):
  - Single grid: `GridA1`, `GridB2`, `GridC3`
  - Grid range: `GridA1B2`, `GridC3D4` (two-grid corners of rectangular area)
  - Pattern: `Grid` + Letter + Number (+ Letter + Number for ranges)
  - Examples: `GridA1`, `GridB4D6`, `GridC3`

- **Building Area** (for multi-building or zone-based projects):
  - Simple areas: `EastWing`, `MainLobby`, `SiteAccess`, `LaydownYard`
  - Floor designation: `Level3`, `Basement`, `GradeLevel`
  - System designation: `MEPRoughIn`, `Structural`, `Envelope`
  - Examples: `EastWing`, `Level3`, `MainLobby`

- **Room Number** (for interior/room-specific work):
  - Patient room format: `Room107`, `Room201`, `Room307B`
  - Operating suite: `OR3`, `OR4`
  - Common areas: `Lobby`, `Conference`, `Kitchen`
  - Examples: `Room107`, `Room214`, `OR3`

- **Special Designations**:
  - Multi-area: `SiteGeneral`, `GeneralView`, `OverallSite`
  - No specific location: Omit or use `General` (for WEATHER, AERIAL, SAFETY that don't apply to specific grid)
  - Examples: `SiteGeneral`, `AllAreas`, `GeneralView`

**Location Omission Rules** (location field optional for):
- AERIAL photos (use cardinal direction instead: `NorthView`, `EastOverview`, etc.)
- WEATHER photos showing full site
- DELIVERY photos of site staging areas
- SAFETY photos of site-wide conditions

#### SEQUENCE (Required)
- **Format**: Three-digit number: `001`, `002`, `003`
- **Increment**: Within same day, category, and location
- **Reset**: Sequence resets daily for each unique category + location combination
- **Rationale**: Enables multiple photos per category/location per day without filename conflicts

#### FILE EXTENSION (Required)
- **Standard formats**: `.jpg` (preferred), `.png`
- **Use JPG**: Preferred for field photos (smaller file size, standard compatibility)
- **Use PNG**: If transparency or lossless compression needed
- **Avoid**: `.bmp`, `.gif`, `.tiff`, `.heic` (compatibility issues with project systems)

---

## Naming Convention Examples by Category

### PROGRESS Photos
```
2026-02-18_PROGRESS_GridA1_ConcreteFootings_001.jpg
2026-02-18_PROGRESS_GridA1_ConcreteFootings_002.jpg
2026-02-18_PROGRESS_GridB3_Rebar_001.jpg
2026-02-20_PROGRESS_GridC3D4_MEPRoughIn_001.jpg
2026-03-05_PROGRESS_SiteGeneral_PEMBDelivery_001.jpg
```

**Notes**:
- Include specific work type in filename (Footings, Rebar, MEPRoughIn) for searchability
- Multiple angles of same area → increment sequence number
- Different areas on same day → new location reference

### SAFETY Photos
```
2026-02-18_SAFETY_GridB3_OpeningProtection_001.jpg
2026-02-17_SAFETY_SiteAccess_RainProtection_001.jpg
2026-02-17_SAFETY_SiteAccess_RainProtection_Before.jpg
2026-02-20_SAFETY_SiteAccess_RainProtection_After.jpg
```

**Notes**:
- Specific hazard type in filename (OpeningProtection, RainProtection)
- Before/after correction pairs use "Before"/"After" suffix instead of sequence

### QUALITY Photos
```
2026-02-18_QUALITY_GridA1_RebarPlacementHoldPoint_001.jpg
2026-02-18_QUALITY_GridA1_RebarPlacementHoldPoint_Detail.jpg
2026-02-18_QUALITY_GridA1_RebarPlacementHoldPoint_Scale.jpg
2026-02-18_QUALITY_Room107_DrywallJoints_Coat1Before.jpg
2026-02-22_QUALITY_Room107_DrywallJoints_Coat1After.jpg
```

**Notes**:
- Hold point photos: Overview, Detail, Scale reference convention
- Before/after taping: Use "CoatNBefore" / "CoatNAfter" format (N = coat number)
- Spec-referenced work: Include relevant spec section if room allows

### WEATHER Photos
```
2026-02-14_WEATHER_SiteConditions_RainGaugeReading_001.jpg
2026-02-15_WEATHER_SiteGeneral_TemperatureReading_45F.jpg
2026-02-16_WEATHER_SiteGeneral_FloodingCondition_001.jpg
```

**Notes**:
- Include measurement reading in filename if critical (temperature, rain gauge depth)
- Time of day relevant: "SiteConditions_7AM" vs "SiteConditions_2PM" (temperature variation)
- Location optional (site-wide condition)

### DELIVERY Photos
```
2026-03-05_DELIVERY_PEMBStructuralSteel_ArrivalCondition.jpg
2026-02-18_DELIVERY_DoorFrames_Staging_GridA1.jpg
2026-02-17_DELIVERY_AHUEquipment_ConditionInspection.jpg
```

**Notes**:
- Material/equipment name critical in filename (PEMBStructuralSteel, DoorFrames, AHUEquipment)
- Include supplier name if helpful: `DoorFrames_Hek_Staging.jpg`
- Condition status: ArrivalCondition, DamageAssessment, Staging, Installation

### RFI SUPPORT Photos
```
2026-02-18_RFISUPPORT_RFI001_GridC3D4_Overview.jpg
2026-02-18_RFISUPPORT_RFI001_GridC3D4_Detail_01.jpg
2026-02-18_RFISUPPORT_RFI001_GridC3D4_ScaleReference.jpg
```

**Notes**:
- RFI number always included: `RFI001`, `RFI042`
- Standard three-photo set: Overview, Detail, Scale
- Multiple details: `Detail_01`, `Detail_02`, `Detail_03`

### SUBMITTAL SUPPORT Photos
```
2026-02-18_SUBMITTAL_SMT023_PaintColor_SampleLocation.jpg
2026-02-18_SUBMITTAL_SMT015_FloringInstallation_ConformanceCheck.jpg
2026-02-17_SUBMITTAL_SMT008_RebarPlacement_ShopDrawingCompliance.jpg
```

**Notes**:
- Submittal number included: `SMT023`, `SMT015`, `SMT008`
- Include work type: PaintColor, FlooringInstallation, RebarPlacement
- Compliance status optional: Conformance, ShopDrawingCompliance, Deviation

### DEFICIENCY / PUNCH List Photos
```
2026-02-18_DEFICIENCY_PUNCH041_Room107_MudPops_Before.jpg
2026-02-22_DEFICIENCY_PUNCH041_Room107_MudPops_After.jpg
2026-02-18_DEFICIENCY_PUNCH042_SouthWall_PaintScuff_Detail.jpg
```

**Notes**:
- Punch list ID always included: `PUNCH041`, `PUNCH042`
- Before/After pairs use "Before"/"After" suffix
- Multiple details increment or add description: `Detail_01`, `NorthCorner`, `SouthWall`

### AS-BUILT Photos
```
2026-05-15_ASBUILT_Room107_MEPRoughInComplete_PreDrywall.jpg
2026-07-20_ASBUILT_GridA1_EastWing_FinishedCondition.jpg
2026-07-18_ASBUILT_Room214_AirDamperLocation_DeviationNote.jpg
```

**Notes**:
- Room/grid/area combination acceptable for location
- Work type/phase critical: MEPRoughInComplete, FinishedCondition, DeviationNote
- Multiple phases: PreDrywall, PostDrywall, FinalFinish

### AERIAL / DRONE Photos
```
2026-02-18_AERIAL_MonthlyProgress_300ftAGL_NorthView.jpg
2026-02-18_AERIAL_MonthlyProgress_300ftAGL_EastView.jpg
2026-03-05_AERIAL_PEMBDelivery_Staging_EastOverview.jpg
2026-03-23_AERIAL_SteelErection_Milestone_300ftAGL.jpg
```

**Notes**:
- Altitude included: `300ftAGL`, `250ftAGL`, `100ftAGL`
- Cardinal direction or view description: `NorthView`, `EastOverview`, `GeneralSiteView`
- Milestone or purpose clear: `MonthlyProgress`, `PEMBDelivery`, `SteelErection`
- Location field optional (set to aerial altitude/bearing if used)

---

## Daily Photo Organization Workflow

### End-of-Day Process (Superintendent)

**Step 1: Download & Review** (5 minutes)
```
1. Connect camera/phone to computer
2. Copy image files to temporary folder: /Temp_Daily_Photos/2026-02-18/
3. Preview each image for quality (focus, composition, clarity)
4. Delete rejects (blurry, duplicates, non-essential)
5. Confirm retained count matches list of categories documented
```

**Step 2: Rename Files** (5 minutes per 20-30 photos)
```
Original filename (camera): IMG_2024.jpg, IMG_2025.jpg, IMG_2026.jpg
Renamed per convention:
  → 2026-02-18_PROGRESS_GridA1_ConcreteFootings_001.jpg
  → 2026-02-18_PROGRESS_GridA1_ConcreteFootings_002.jpg
  → 2026-02-18_QUALITY_GridA1_RebarPlacement_001.jpg

[Renaming script or manual process in file explorer/Finder]
```

**Step 3: Create Daily Folder** (1 minute)
```
Destination: /10 - Project Photos/2026-02-18/
  └─ Move all renamed images to this folder
```

**Step 4: Add Metadata** (5-10 minutes)
```
For each image, document in photo-log entry:
  - Date taken: 2026-02-18
  - Time taken: [actual time photo was captured]
  - Filename: [renamed file from step 2]
  - Category: [PROGRESS, QUALITY, etc.]
  - Location: [Grid, Area, Room reference]
  - Description: [One-sentence description of what's shown]
  - Trade: [Concrete, Electrical, Drywall, etc.]
  - Sub Contractor: [Performing entity name]
  - Related documents: [RFI, Punch, Submittal if applicable]
  - Photographer: [Your name]
```

**Step 5: Link to Project Systems** (3-5 minutes)
```
If photo supports pending documents:
  RFI → Add to RFI record: "photos": ["PHO-2026-0218-001"]
  Punch → Add to punch item: "photos": ["PHO-2026-0218-043"]
  Submittal → Add to submittal: "photos": ["PHO-2026-0218-015"]
  Daily Report → Include 3-5 best photos in daily report summary
```

**Step 6: Backup & Archive** (2 minutes)
```
1. Create backup copy to cloud (Google Drive, OneDrive)
2. Archive original files to project archive folder (7-year retention)
3. Verify backup completion (file size matches original)
```

**Total Time**: 20-30 minutes for typical 20-30 photos per day

---

## Photo Metadata Template

### For Each Photo in Project Photo Log

```json
{
  "id": "PHO-2026-0218-001",
  "date_taken": "2026-02-18",
  "time_taken": "14:30",
  "filename": "2026-02-18_PROGRESS_GridA1_ConcreteFootings_001.jpg",
  "file_path": "/10 - Project Photos/2026-02-18/2026-02-18_PROGRESS_GridA1_ConcreteFootings_001.jpg",
  "file_size_kb": 2450,
  "image_dimensions": "4000x3000",

  "category": "PROGRESS",
  "sub_category": null,
  "description": "Concrete footing excavation complete at Grid A-1/B-2, ready for rebar placement",

  "location_grid": "A-1/B-2",
  "location_building_area": "Foundation Zone A",
  "location_room": null,
  "location_floor_level": "Grade",

  "trade": "Concrete",
  "sub_contractor": "W Principles Construction",
  "sub_contact": "Mike Smith, (859) 555-1234",

  "weather_condition": "Clear, 48F, calm wind",
  "temperature_f": 48,
  "precipitation": "None",
  "wind_condition": "Calm",

  "related_rfi": null,
  "related_submittal": null,
  "related_punch": null,
  "related_daily_report": "REPORT-20260218",

  "hold_point": false,
  "quality_acceptable": true,
  "before_after_pair": null,

  "taken_by": "Andrew Eberle",
  "photo_location_consistency": "Standard A-1/B-2 view from northeast corner, 10 feet from building perimeter",
  "notes": "Geotech proofroll observation completed same day — see inspection log. Excavation depth verified at 12' per plans."
}
```

---

## Bulk Photo Processing Script Logic

### For Field Teams Using Smartphones

**Recommended App Workflow** (Google Pixel, iPhone):

1. **In Camera App**:
   - Enable auto-timestamp (date/time on every photo)
   - Use Grid overlay feature (helps with composition and straight lines)
   - Use burst mode for critical documentation (select best 1-2 from burst)

2. **Immediately After Taking Photo** (in Notes or photo caption app):
   ```
   2026-02-18 PROGRESS GridA1 Concrete excavation complete
   2026-02-18 QUALITY GridA1 Rebar hold point overview
   2026-02-18 SAFETY RainProtection before after
   ```

3. **Daily Sync Process**:
   - Download all photos from phone to computer
   - Rename batch using batch rename tool or script:
     - Windows: PowerShell script or ReNamer tool
     - Mac: Automator or command-line rename
   - Pattern: `{DATE}_{CATEGORY}_{LOCATION}_{SEQ}.{ext}`
   - Verify: All files renamed correctly before proceeding

4. **Organize to Daily Folder**:
   ```
   /10 - Project Photos/2026-02-18/
   └─ [All renamed photos for that day]
   ```

5. **Enter Metadata** (spreadsheet or database):
   - Create CSV with columns: filename, category, location, trade, description, sub, photographer
   - Copy/paste critical photos' metadata
   - Upload CSV to photo-log.json via data import script

---

## Multi-Photo Set Naming Conventions

### BEFORE/AFTER Pairs (Two-Photo Sets)
```
Base: {DATE}_{CATEGORY}_{LOCATION}_{DESCRIPTION}
Before: {DATE}_{CATEGORY}_{LOCATION}_{DESCRIPTION}_Before.jpg
After:  {DATE}_{CATEGORY}_{LOCATION}_{DESCRIPTION}_After.jpg

Example:
2026-02-18_DEFICIENCY_PUNCH041_Room107_MudPops_Before.jpg
2026-02-22_DEFICIENCY_PUNCH041_Room107_MudPops_After.jpg
```

### HOLD POINT Inspection Sets (Three-Photo Set)
```
Base: {DATE}_{CATEGORY}_{LOCATION}_{HOLDPOINT}
Overview:  {DATE}_{CATEGORY}_{LOCATION}_{HOLDPOINT}_Overview.jpg
Detail:    {DATE}_{CATEGORY}_{LOCATION}_{HOLDPOINT}_Detail.jpg
Scale:     {DATE}_{CATEGORY}_{LOCATION}_{HOLDPOINT}_Scale.jpg

Example:
2026-02-18_QUALITY_GridA1_RebarPlacementHoldPoint_Overview.jpg
2026-02-18_QUALITY_GridA1_RebarPlacementHoldPoint_Detail.jpg
2026-02-18_QUALITY_GridA1_RebarPlacementHoldPoint_Scale.jpg
```

### RFI DOCUMENTATION Sets (Three-Photo Set)
```
Base: {DATE}_RFISUPPORT_RFI{NNN}_{LOCATION}
Overview: {DATE}_RFISUPPORT_RFI{NNN}_{LOCATION}_Overview.jpg
Detail:   {DATE}_RFISUPPORT_RFI{NNN}_{LOCATION}_Detail_01.jpg
Scale:    {DATE}_RFISUPPORT_RFI{NNN}_{LOCATION}_ScaleReference.jpg

Example:
2026-02-18_RFISUPPORT_RFI001_GridC3D4_Overview.jpg
2026-02-18_RFISUPPORT_RFI001_GridC3D4_Detail_01.jpg
2026-02-18_RFISUPPORT_RFI001_GridC3D4_ScaleReference.jpg
```

### PROGRESS SEQUENCE Sets (Multiple Angles, Same Day)
```
Base: {DATE}_{CATEGORY}_{LOCATION}_{WORK}
Angle 1: {DATE}_{CATEGORY}_{LOCATION}_{WORK}_001.jpg
Angle 2: {DATE}_{CATEGORY}_{LOCATION}_{WORK}_002.jpg
Angle 3: {DATE}_{CATEGORY}_{LOCATION}_{WORK}_003.jpg

Example (PEMB delivery from multiple angles):
2026-03-05_DELIVERY_PEMB_Structural_Arrival_001.jpg     [Truck entering]
2026-03-05_DELIVERY_PEMB_Structural_Arrival_002.jpg     [Staged on site]
2026-03-05_DELIVERY_PEMB_Structural_Arrival_003.jpg     [Condition inspection]
```

---

## Quick Reference Naming Examples

### Monday, February 18, 2026 — Concrete Work Day

| Activity | Photo Name | Category | Location | Sequence |
|----------|-----------|----------|----------|----------|
| Excavation overview (Grid A-1) | `2026-02-18_PROGRESS_GridA1_Excavation_001.jpg` | PROGRESS | A-1 | 001 |
| Excavation detail | `2026-02-18_PROGRESS_GridA1_Excavation_002.jpg` | PROGRESS | A-1 | 002 |
| Rebar placement before concrete | `2026-02-18_QUALITY_GridA1_RebarPlacement_Before.jpg` | QUALITY | A-1 | Before |
| Concrete placement in progress | `2026-02-18_PROGRESS_GridA1_ConcretePlace_001.jpg` | PROGRESS | A-1 | 001 |
| Concrete finishing | `2026-02-18_PROGRESS_GridA1_ConcretePlace_002.jpg` | PROGRESS | A-1 | 002 |
| Safety: rain protection | `2026-02-18_SAFETY_GridA1_RainProtection_001.jpg` | SAFETY | A-1 | 001 |
| Weather: temperature reading | `2026-02-18_WEATHER_SiteGeneral_TemperatureReading_52F.jpg` | WEATHER | General | 001 |
| **Total Photos for Day** | **7 photos** | — | — | — |

---

## Troubleshooting Common Naming Issues

| Problem | Solution |
|---------|----------|
| Same filename twice (sequence reset) | Increment sequence number: use 001, 002, 003, etc. incrementally within same day/category/location |
| Location ambiguous | Use grid reference if available (GridA1); otherwise building area (EastWing) or room (Room107) |
| Too many words in filename | Abbreviate work type or use standard acronyms (MEP, PEMB, AHU); keep filename under 80 characters |
| Special characters in filename | Use only alphanumeric, underscore, hyphen; avoid spaces and punctuation |
| Date format confusion | Always use YYYY-MM-DD (2026-02-18); never use MM/DD/YYYY or other formats |
| Wrong category assigned | Check category definition; re-categorize and rename if necessary before archiving |
| Missing scale in quality photo | Retake photo with measuring tape or scale reference visible in frame |

---

## Version History
- **v1.0.0** (2026-02-18): Comprehensive photo naming convention, workflow templates, metadata schema, and troubleshooting guide.
