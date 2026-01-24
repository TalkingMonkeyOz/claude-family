

# Nimbus client application requirements for Monash University reporting

Tue, 20 Jan 26

### Application Requirements

- Build standalone client application specifically for Monash University reporting needs
- Read-only data interrogation targeting Nimbus time-to-work database
- Leverage existing Nimbus Mui architecture and learnings around OData and API integration
- Connection management system:
    - Singular active connection with dropdown selection interface
    - Production environment connection (read-only enforced)
    - Ability to repoint connections to alternative environments
    - Similar UX pattern to existing Nimbus Mui connection selector

### Required Reports

- **Deleted Agreements Report**
    - **Purpose**: Track agreement deletions and identify who performed deletions
    - **Filters**:
        - Date range selector (to/from dates)
        - Shift-based filtering
    - **Columns/Fields**:
        1. Shift description
        2. Shift date
        3. Shift to/from times
        4. Syllabus plus activity code (exact field name TBD)
        5. Last updated by (mapped to actual user identity)
        6. Agreement deletion status
    - **Business Rules**:
        - Include ALL deleted agreements for specified shifts
        - Include non-deleted agreements for empty/unallocated shifts
        - Track repeat agreement deletion patterns
    - **Open Questions**:
        - Exact database field name for “syllabus plus activity code”
        - User identity mapping mechanism for “last updated by”
- **Activities Report**
    - **Purpose**: Flag inappropriate activity code changes from timetable to non-timetable activities
    - **Filters**:
        - Date range selection (to/from dates)
        - Location dropdown (optional)
        - Location group dropdown (optional)
    - **Columns/Fields**:
        - Shift identifier and details
        - Original vs current activity codes
        - Syllabus plus activity code
        - Ad hoc fill-in status
        - Location and location group
    - **Business Rules**:
        - Report shifts with ad hoc fill-ins using syllabus plus activity code
        - Flag when TT-prefix activities changed to non-TT activities
        - TT activities = lectures, workshops, tutorials (timetable activities)
        - Concern activities = meetings, non-academic assignments
    - **Validation Logic**:
        - IF shift has ad hoc fill-in AND activity code lacks TT prefix → REPORT
        - Example concern: TT lecture changed to “meeting”
    - **Open Questions**:
        - Complete list of valid TT prefix codes
        - Location vs location group data structure
- **Missing Activities Report**
    - **Purpose**: Identify shifts with person allocation but missing activity assignment
    - **Filters**:
        - Date range selection (to/from dates)
        - Location filtering capability
        - Location group filtering capability
    - **Columns/Fields**:
        - Shift details (date, time, description)
        - Assigned person information
        - Activity assignment status (empty/null)
        - Location and location group data
    - **Business Rules**:
        - Report shifts where person allocated BUT no activity assigned
        - Example scenario: “John allocated 10-11 for meeting but forgot to set meeting activity”
    - **Edge Cases**:
        - Partially configured shifts
        - Multiple person allocations with mixed activity assignments

### Technical Specifications

- **Platform & Distribution**:
    - Self-contained Windows desktop application (.exe)
    - Target: Secured Windows environments (reasonably up-to-date versions)
    - Single executable deployment model
    - Tauri + Rust stack (leverage existing successful implementation)
- **Data Access & Integration**:
    - Read-only database connections to Nimbus time-to-work system
    - OData and API integration patterns from Nimbus Mui
    - Connection string management with environment switching
- **User Interface**:
    - Grid-based data display for all reports
    - Built-in filtering capabilities per grid
    - Export functionality: Excel and CSV formats
    - Dropdown selectors for connections, locations, date ranges
- **Security & Encryption**:
    - Encrypted credential storage in local application folder
    - All file operations restricted to desktop/application folder
    - Username/password encryption for connection credentials
    - No sensitive data persistence outside encrypted local storage
- **Offline & Local Behavior**:
    - All writes/updates/saves contained within application folder
    - No external dependencies for core functionality
    - Local configuration and settings management
- **Update & Distribution Flow**:
    - Git-based distribution mechanism
    - Controlled access update process with key authentication
    - Prevent public download availability
    - Update notification and deployment system
    - Version management and rollback capability
- **Logging & Configuration**:
    - Local application logging within folder constraints
    - Configurable connection parameters
    - User preference persistence
- **Open Questions**:
    - Specific Windows version compatibility requirements
    - Network connectivity assumptions for secured environments
    - Certificate/authentication requirements for database access

### Next Steps

1. **Field Mapping & Database Schema** (Priority: Critical, Due: This Week)
    - [ ] Owner: [TBD] - Identify exact field name for “syllabus plus activity code”
    - [ ] Owner: [TBD] - Map “last updated by” to user identity system
    - [ ] Owner: [TBD] - Document complete TT activity code prefix list
    - [ ] Owner: [TBD] - Validate location/location group data structure
2. **Technical Architecture Setup** (Priority: Critical, Due: This Weekend)
    - [ ] Owner: [TBD] - Configure Tauri/Rust development environment
    - [ ] Owner: [TBD] - Implement OData/API connection framework
    - [ ] Owner: [TBD] - Design encrypted credential storage system
    - [ ] Owner: [TBD] - Create single-folder deployment structure
3. **Report Development** (Priority: High, Due: This Weekend)
    - [ ] Owner: [TBD] - Build deleted agreements report with filtering
    - [ ] Owner: [TBD] - Implement activities validation logic and reporting
    - [ ] Owner: [TBD] - Create missing activities detection and display
    - [ ] Owner: [TBD] - Add Excel/CSV export functionality for all reports
4. **Security & Distribution** (Priority: Medium, Due: Next Week)
    - [ ] Owner: [TBD] - Implement Git-based distribution with access controls
    - [ ] Owner: [TBD] - Create update mechanism with authentication keys
    - [ ] Owner: [TBD] - Test deployment on secured Windows environments
5. **Final Delivery** (Priority: Critical, Due: This Weekend)
    - [ ] Owner: [TBD] - Complete application testing and validation
    - [ ] Owner: [TBD] - Package single .exe with all dependencies
    - [ ] Owner: [TBD] - Document deployment and usage instructions

---

Chat with meeting transcript: [https://notes.granola.ai/t/7f54e630-875a-4244-b22e-113b8d4cd7e6-00demib2](https://notes.granola.ai/t/7f54e630-875a-4244-b22e-113b8d4cd7e6-00demib2)