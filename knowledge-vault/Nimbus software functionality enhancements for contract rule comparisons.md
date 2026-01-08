# Nimbus software functionality enhancements for contract rule comparisons

Wed, 07 Jan 26

### New Nimbus Comparison Functionality Requirements

Need to add comparison capabilities for three key areas:

- Contract rules comparison across database instances
    
    - Pull contract rules from system and compare between databases
        
    - Rules recently updated to JSON format - need to verify decodability
        
    - Enable automatic updates (future enhancement)
        
- Security roles configuration comparison
    
    - Compare individual keys allocated to different user security roles
        
    - Identify differences in role configurations
        
- Award interpretation rules comparison
    
    - Extract and examine rule differences
        
    - Compare award interpretation logic between systems
        

### Implementation Approach

- Add new left-hand menu option for “Comparisons” or individual work items
    
- Require secondary database connection setup
    
    - Primary database already configured in first screen
        
    - Add authentication for secondary database
        
- Consider separate components for each comparison type
    
    - Different APIs and result formats for each area
        
    - May be easier to implement as distinct modules
        

### Upload and Management Features

- Enable rule selection and upload capabilities
    
- Support multiple rule combinations
    
- Two upload options:
    
    1. Incremental rules for matching/merging
        
    2. Complete rule upload to singular database
        
- Provide option to upload to individual database instances