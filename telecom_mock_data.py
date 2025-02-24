TELECOM_QUERIES = {
    "billing": {
        "keywords": ["bill", "payment", "charge", "invoice", "plan", "data usage", "balance"],
        "sample_queries": [
            "SELECT amount, due_date, status FROM billing_records WHERE customer_id = ? ORDER BY bill_date DESC LIMIT 1",
            "SELECT plan_name, data_limit, validity FROM customer_plans WHERE customer_id = ?",
            "SELECT payment_date, amount FROM payment_history WHERE customer_id = ? AND payment_date >= DATE_SUB(NOW(), INTERVAL 3 MONTH)",
            "SELECT remaining_data, validity_end FROM data_usage WHERE customer_id = ? AND status = 'active'"
        ]
    },
    "network_status": {
        "keywords": ["network", "coverage", "signal", "outage", "down", "maintenance", "connection"],
        "sample_queries": [
            "SELECT status, affected_area, estimated_resolution FROM network_outages WHERE region = ? AND status != 'resolved'",
            "SELECT signal_strength, tower_id FROM network_coverage WHERE postal_code = ?",
            "SELECT maintenance_type, start_time, end_time FROM planned_maintenance WHERE date = CURRENT_DATE",
            "SELECT issue_type, affected_services FROM service_status WHERE region = ? AND status = 'active'"
        ]
    },
    "customer_service": {
        "keywords": ["complaint", "ticket", "support", "help", "issue", "resolution", "service request"],
        "sample_queries": [
            "SELECT ticket_id, status, priority FROM support_tickets WHERE customer_id = ? ORDER BY created_date DESC",
            "SELECT complaint_type, resolution_status, sla_time FROM complaints WHERE ticket_id = ?",
            "SELECT AVG(resolution_time) as avg_time FROM service_requests WHERE priority = ? AND created_date >= DATE_SUB(NOW(), INTERVAL 1 MONTH)",
            "SELECT status_updates, assigned_team FROM ticket_tracking WHERE ticket_id = ?"
        ]
    }
}

NETWORK_OUTAGE_QUERIES = {
    'postal_code': '''
        SELECT status, affected_area, estimated_resolution 
        FROM network_outages 
        WHERE postal_code = ? AND status != 'resolved'
    ''',
    'region': '''
        SELECT status, affected_area, estimated_resolution 
        FROM network_outages 
        WHERE region = ? AND status != 'resolved'
    ''',
    'address': '''
        SELECT status, affected_area, estimated_resolution 
        FROM network_outages 
        WHERE address LIKE ? AND status != 'resolved'
    '''
}

SYSTEM_PROMPT = """
You are a telecom customer service AI assistant. You can help with:
- Billing inquiries and payment issues
- Network status and coverage information
- Customer service and support tickets
- General telecom-related questions

Please stick to telecom-related queries. If the question is outside this scope,
guide the user back to telecom-related topics.
"""

def get_outage_query(user_input):
    input_lower = user_input.lower()
    
    # Check for postal code pattern (assuming 5-digit format)
    if any(word.isdigit() and len(word) == 5 for word in input_lower.split()):
        return NETWORK_OUTAGE_QUERIES['postal_code']
    
    # Check for specific region mentions
    region_keywords = ['downtown', 'city', 'district', 'area', 'region']
    if any(keyword in input_lower for keyword in region_keywords):
        return NETWORK_OUTAGE_QUERIES['region']
    
    # Default to address-based query
    return NETWORK_OUTAGE_QUERIES['address']

def get_relevant_queries(user_input):
    """Match user input with relevant predefined queries"""
    if any(word in user_input.lower() for word in ['outage', 'network', 'down', 'service']):
        return [get_outage_query(user_input)]
    
    relevant_queries = []
    user_input = user_input.lower()
    
    for category, data in TELECOM_QUERIES.items():
        if any(keyword in user_input for keyword in data["keywords"]):
            relevant_queries.extend(data["sample_queries"])
    
    return relevant_queries or ["No predefined queries match your question. Try asking about billing, network status, or customer service."]
