import json
import random

#Production use cases would utilize a database query with proper authentication, conection pooling, error handling, etc.
#ORD-1234 will represent an order shipped, has tracking number, and eligible for return
#ORD-5678 will represent an order still processing, no tracking number, and not eligible for returns yet
MOCK_ORDERS = {
    "ORD-1234": {
        "id": "ORD-1234",
        "customer_email": "customer@example.com",
        "items": ["Greenlights", "Atomic Habits"],
        "total": 32.98,
        "status": "shipped",
        "tracking_number": "1Z999AA10123456784",
        "estimated_delivery": "March 30, 2026",
        "order_date": "March 20, 2026"
    },
    "ORD-5678": {
        "id": "ORD-5678",
        "customer_email": "customer@example.com",
        "items": ["Dune"],
        "total": 18.99,
        "status": "processing",
        "tracking_number": None,
        "estimated_delivery": "March 31, 2026",
        "order_date": "March 21, 2026"
    }
}

#Failure path returns structured error rather than raising an exception and having to handle multiple response shapes
def get_order_status(order_id: str) -> dict:
    order_id = order_id.upper().strip()
    if order_id in MOCK_ORDERS:
        return {"success": True, "order": MOCK_ORDERS[order_id]}
    return {"success": False, "error": f"No order found with ID {order_id}. Please check the order ID and try again."}

def process_return_request(order_id: str, reason: str, items: list) -> dict:
    order_id = order_id.upper().strip()
    if order_id not in MOCK_ORDERS:
        return {"success": False, "error": "Order not found."}
    order = MOCK_ORDERS[order_id]
    #Business rule enforcement that lives in code due to having financial implications
    if order["status"] == "processing":
        return {
            "success": False,
            "error": "This order is still processing and cannot be returned yet. Please wait until it ships."
        }
    return_id = f"RET-{random.randint(10000, 99999)}"
    return {
        "success": True,
        "return_id": return_id,
        "order_id": order_id,
        "items": items,
        "reason": reason,
        "instructions": "A prepaid shipping label will be emailed to you within 24 hours. Items must be returned within 14 days.",
        "refund_timeline": "3-5 business days after we receive your return"
    }

#Policies exist as tools rather than in the prompt for accuracy, hallucination prevention, and auditability purposes
def lookup_policy(policy_type: str) -> dict:
    policies = {
        "returns": {
            "window": "30 days from delivery date",
            "condition": "Books must be in original, unread condition",
            "process": "Initiate return through support, prepaid label provided",
            "refund": "3-5 business days after we receive the return"
        },
        "shipping": {
            "standard": "5-7 business days, free on orders over $25",
            "expedited": "2-3 business days, $8.99",
            "overnight": "Next business day, $19.99",
            "international": "10-21 business days, rates vary by destination"
        },
        "password_reset": {
            "process": "Click Forgot Password on the login page",
            "delivery": "Reset email arrives within 5 minutes",
            "expiry": "Reset link expires after 1 hour",
            "tip": "Check your spam folder if you don't see the email"
        }
    }
    policy_type = policy_type.lower().strip()
    if policy_type in policies:
        return {"success": True, "policy": policies[policy_type]}
    return {"success": False, "error": f"Policy type '{policy_type}' not found. Valid types: returns, shipping, password_reset"}