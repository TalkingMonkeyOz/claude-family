use serde_json::{json, Value};
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct LocationGroupRequest {
    pub description: String,
    pub location_ids: Vec<i64>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct LocationGroupResponse {
    pub location_group_id: i64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ScheduleGroupRequest {
    pub description: String,
    pub location_group_id: i64,
    pub start_date: String, // YYYY-MM-DD format
    pub end_date: String,   // YYYY-MM-DD format
    pub learning_period: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ScheduleGroupResponse {
    pub schedule_group_id: i64,
}

/// Creates a LocationGroup via REST API
/// 
/// # Arguments
/// * `base_url` - The base URL for the Nimbus API
/// * `token` - Authentication token
/// * `request` - LocationGroupRequest with description and location_ids
///
/// # Returns
/// LocationGroupID of the created group
#[tauri::command]
pub async fn create_location_group(
    base_url: String,
    token: String,
    request: LocationGroupRequest,
) -> Result<LocationGroupResponse, String> {
    // Build locations array
    let locations: Vec<Value> = request
        .location_ids
        .iter()
        .map(|id| json!({"LocationID": id}))
        .collect();

    // Build request payload
    let payload = json!({
        "Description": request.description,
        "Active": true,
        "Locations": locations
    });

    // Create HTTP client
    let client = reqwest::Client::new();

    // Prepare headers
    let mut headers = reqwest::header::HeaderMap::new();
    headers.insert(
        "AuthenticationToken",
        reqwest::header::HeaderValue::from_str(&token)
            .map_err(|e| format!("Invalid token header: {}", e))?,
    );
    headers.insert(
        "Authorization",
        reqwest::header::HeaderValue::from_str(&format!("Bearer {}", token))
            .map_err(|e| format!("Invalid authorization header: {}", e))?,
    );
    headers.insert(
        "Accept",
        reqwest::header::HeaderValue::from_static("application/json"),
    );
    headers.insert(
        "Content-Type",
        reqwest::header::HeaderValue::from_static("application/json"),
    );

    // Make POST request
    let url = format!("{}/RESTApi/LocationGroup", base_url);
    let response = client
        .post(&url)
        .headers(headers)
        .json(&payload)
        .send()
        .await
        .map_err(|e| format!("Failed to create location group: {}", e))?;

    // Check response status
    if !response.status().is_success() {
        let error_text = response
            .text()
            .await
            .unwrap_or_else(|_| "Unknown error".to_string());
        return Err(format!(
            "API error ({}): {}",
            response.status(),
            error_text
        ));
    }

    // Parse response - expecting LocationGroupID in response
    let response_body: Value = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    let location_group_id = response_body
        .get("LocationGroupID")
        .and_then(|v| v.as_i64())
        .ok_or_else(|| "LocationGroupID not found in response".to_string())?;

    Ok(LocationGroupResponse { location_group_id })
}

/// Creates a ScheduleGroup via REST API
///
/// # Arguments
/// * `base_url` - The base URL for the Nimbus API
/// * `token` - Authentication token
/// * `request` - ScheduleGroupRequest with description, location_group_id, dates, and learning_period
///
/// # Returns
/// ScheduleGroupID of the created group
#[tauri::command]
pub async fn create_schedule_group(
    base_url: String,
    token: String,
    request: ScheduleGroupRequest,
) -> Result<ScheduleGroupResponse, String> {
    // Build adhoc fields array
    let adhoc_fields = json!([
        {
            "FieldName": "adhoc_LearningPeriod",
            "Value": request.learning_period
        }
    ]);

    // Build request payload
    let payload = json!({
        "Description": request.description,
        "Active": true,
        "LocationGroupID": request.location_group_id,
        "GroupStartDate": request.start_date,
        "GroupEndDate": request.end_date,
        "AdhocFields": adhoc_fields
    });

    // Create HTTP client
    let client = reqwest::Client::new();

    // Prepare headers
    let mut headers = reqwest::header::HeaderMap::new();
    headers.insert(
        "AuthenticationToken",
        reqwest::header::HeaderValue::from_str(&token)
            .map_err(|e| format!("Invalid token header: {}", e))?,
    );
    headers.insert(
        "Authorization",
        reqwest::header::HeaderValue::from_str(&format!("Bearer {}", token))
            .map_err(|e| format!("Invalid authorization header: {}", e))?,
    );
    headers.insert(
        "Accept",
        reqwest::header::HeaderValue::from_static("application/json"),
    );
    headers.insert(
        "Content-Type",
        reqwest::header::HeaderValue::from_static("application/json"),
    );

    // Make POST request
    let url = format!("{}/RESTApi/ScheduleGroup", base_url);
    let response = client
        .post(&url)
        .headers(headers)
        .json(&payload)
        .send()
        .await
        .map_err(|e| format!("Failed to create schedule group: {}", e))?;

    // Check response status
    if !response.status().is_success() {
        let error_text = response
            .text()
            .await
            .unwrap_or_else(|_| "Unknown error".to_string());
        return Err(format!(
            "API error ({}): {}",
            response.status(),
            error_text
        ));
    }

    // Parse response - expecting ScheduleGroupID in response
    let response_body: Value = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    let schedule_group_id = response_body
        .get("ScheduleGroupID")
        .and_then(|v| v.as_i64())
        .ok_or_else(|| "ScheduleGroupID not found in response".to_string())?;

    Ok(ScheduleGroupResponse { schedule_group_id })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_location_group_request_serialization() {
        let request = LocationGroupRequest {
            description: "Test Group".to_string(),
            location_ids: vec![1, 2, 3],
        };
        let json = serde_json::to_value(&request).unwrap();
        assert_eq!(json["description"], "Test Group");
        assert_eq!(json["location_ids"].as_array().unwrap().len(), 3);
    }

    #[test]
    fn test_schedule_group_request_serialization() {
        let request = ScheduleGroupRequest {
            description: "Test Schedule".to_string(),
            location_group_id: 42,
            start_date: "2025-01-01".to_string(),
            end_date: "2025-12-31".to_string(),
            learning_period: "30".to_string(),
        };
        let json = serde_json::to_value(&request).unwrap();
        assert_eq!(json["description"], "Test Schedule");
        assert_eq!(json["location_group_id"], 42);
    }
}
