[[Monash Nimbus customer app]]
### Detailed feature notes for report builds

#### 1. Deleted Agreements Report

**1.1 Filters / UI at top of report**

- Compact filter bar with:
    - **Location Group selector**
        - Location groups act as _containers_
        - Must support **recursive inclusion**:
            - Selecting a location group (e.g. “Journalism”) automatically includes:
                - That location group
                - All child location groups
                - All locations under those groups
    - **Location selector**
        - Ability to target a single location (non-recursive) where needed
    - **Person lookup**
        - Lookup by:
            - First name + surname (combined search)
            - Payroll number
            - Username (email address)
        - Must perform **type‑ahead / as‑you‑type search**
        - Needs to be performant for **21,000+ active users**
            - Responsive search (avoid current “horrendously slow” Nimbus lookup)
    - **Agreement type multi-select**
        - Ability to choose which agreement types to include
        - Provide an option to **exclude vacant shift agreements** (low value system-wide)
    - **(Optional / deprioritized) Department**
        - Departments are directly linked to locations and may share names
        - If ever included, department options must be **filtered to the selected location**
        - Current leaning: **omit department filtering** for this report (“forget departments”)

**1.2 Core use cases / logic**

- Primary purpose:
    - Extract detailed **agreement history for a shift** and the **person allocated** to that shift
- Expected workflows:
    - Pull all lease/agreements for a chosen **location group** (e.g. Journalism + its sub-structure)
    - Narrow down to:
        - A **specific person** (via person lookup), or
        - **Everyone at a specific location/group**
- Person/location alignment:
    - Filtering should be based on **scheduled locations**, not just static assignments:
        - Looking for: “a shift at a location and someone allocated to it”
        - Examples:
            - “Bring back just that person”
            - “Bring back everyone at a specific location”
            - If “Journalism” is selected, list **journalism staff** (i.e., people scheduled at journalism-related locations)

**1.3 Data model / SAP integration**

- There is an **org hierarchy** field (likely `SAP Org ID` / similar):
    - Present in the database as something like **org ID / “ad hoc org id”**
    - Populated for the **SAP hierarchy**
    - **Location Groups**:
        - Each location group has a **matching location** with the same SAP org ID
        - Same table, same field name in both location and location-group related tables
- SAP-driven placement:
    - When a user is imported from SAP into Nimbus:
        - SAP org ID is used to locate the matching org record
        - User is placed into **User Locations** table as an initial placeholder
    - Workforce managers then add **additional locations as “activities”**:
        - Activities are things like:
            - Lectures
            - Tutorials
            - Workshops
        - Each activity is represented as a **location**
        - Example:
            - Base org location: “Medicine”
            - Activity location: “Biology 101” under Medicine

**1.4 Settings / usability**

- **Settings / preferences storage**
    - A “settings file” or equivalent persistence to:
        - Remember previous filter selections (location, location group, person, agreement types, etc.)
        - Potentially store additional report-specific settings
    - Goal: allow users to easily **re-run commonly used filters** without reconfiguring each time

---

#### 2. Location & Personnel Filtering Model (cross-report concept)

- **Recursive selection behavior**
    - Selecting a **location group** should:
        - Traverse all descendants (sub-groups and locations)
        - Include all relevant agreements/shifts/personnel across that tree
- **Person list constrained by location context**
    - When a user has selected a location group / location:
        - Person picker should be filtered to **people scheduled at those locations**, not global list
- **Focus on scheduled locations**
    - Filters should be grounded in where people are **actually scheduled** (shifts), not just where they’re originally org-placed
- **Example behavior**
    - Select “Journalism”:
        - Underlying query:
            - Resolve Journalism → SAP org ID
            - Find all related locations / activities
            - Return:
                - Shifts at those locations
                - Agreements attached to those shifts
                - People allocated to those shifts

---

#### 3. Activities TT Changes Report

- **Purpose**
    - Identify **mismatches** in activities/TT changes (not primarily people lookup)
- **Filters**
    - **Date range**:
        - Support both **historical** and **future** date ranges
    - **Location group / location**:
        - Same location/location group selection concepts as above
- **Focus**
    - Emphasis on:
        - Detecting mismatches / inconsistencies
        - Less emphasis on detailed per-person lookup

---

#### 4. Missing Job Roles / Missing Shifts / General Grid UX

- **Missing shifts report**
    - Agreements report is intended to find:
        - Shifts that:
            - Have somebody allocated / a signed person, and
            - Do **not** have an associated activity
    - Current concern:
        - Agreements report may be **missing shifts** again
        - Not critical to show full person details here, but missing-shift logic must be correct
- **Missing job roles report**
    - Needs:
        - **Hyperlink** from each row to the **corresponding schedule**
        - Ideally a deep link that opens the **specific shift** if technically feasible
- **Horizontal scroll UX issue**
    - Floating horizontal scrollbar is **no longer visible**
        - Users must scroll to the bottom to find the scrollbar
        - This affects **all reports**
    - Required fix:
        - Restore a **floating/sticky horizontal scroll bar** that remains accessible regardless of vertical scroll position

---

#### 5. Hyperlinks to Schedules (all relevant reports)

- For Deleted Agreements, Activities TT changes, Missing Shifts, Missing Job Roles, etc.:
    - Include **hyperlinks** from each row to:
        - The **relevant schedule view**
        - If possible: **directly open the relevant shift** (deep-linking into the schedule)
    - Intent:
        - Move quickly from diagnostic/report view → actionable scheduling context

---

#### 6. Authentication & Secure Access Layer

- **Current constraint**
    - Nimbus API/OData authentication requires **Okta** in production
    - Okta returns auth to a URL that cannot easily be controlled for these external tools
- **Requested secure-access mechanism**
    - A **password-protected section** or similar for more sensitive reports:
        - Bound either to:
            - A specific machine, and/or
            - A specific user
        - Capabilities might include:
            - Read-only access to more privileged extracts
    - Key use case:
        - Allow **payroll** staff secure access to:
            - **UAT extract** report from Nimbus User Loader (previously built in “Nimbus MUI MUI”)
        - Need some robust gating so that only permitted roles can access this dataset

---

#### 7. Change History Report (Shifts & Users)

**7.1 Scope and usage patterns**

- Users want a **comprehensive, all‑encompassing change history** for shifts, including:
    - Agreements
    - People assigned
    - Timesheet events
    - Attendance events
- Two primary lookup paths:
    - **By user**:
        - Example: “Show all changes to shifts for **Matt Delhay** for this period”
    - **By shift / unit / date**:
        - Example: “Show the history for **APG5095** on **21st March/April**”

**7.2 Features**

- **Filters**
    - By **user**
        - Person lookup (same as Deleted Agreements person lookup)
    - By **unit / location / activity**
    - By **date range**
- **History detail requirements**
    - Each change record should clarify:
        - What changed (before vs after)
        - When it changed (timestamp)
        - Optional: who made the change (if data available)
    - Need to do “serious analysis” on:
        - Current change data structures
        - How to present them so **the actual change is clear**
- **Timesheets and attendance**
    - Next step is to:
        - Work out the full **timesheet history**
        - Represent:
            - Timesheet events
            - Attendance events
            - How each change relates to the shift/agreements

---

If you want, I can convert this into a requirements-style spec (fields, endpoints, and example queries) for your dev team.