"""
Stripe Payment Integration for YouTube Transcript Generator
Handles subscriptions, webhooks, and payment tracking
"""

import stripe
import os
from typing import Dict, Optional
from datetime import datetime

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")

# Price IDs (from Stripe dashboard)
PRICES = {
    "starter": os.getenv("STRIPE_PRICE_STARTER", "price_starter_placeholder"),
    "professional": os.getenv("STRIPE_PRICE_PROFESSIONAL", "price_pro_placeholder"),
    "enterprise": None  # Custom pricing
}

class PaymentManager:
    """Handle all payment operations"""
    
    @staticmethod
    def create_customer(email: str, name: str = None) -> Dict:
        """Create a Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={"created_at": datetime.now().isoformat()}
            )
            return {"success": True, "customer_id": customer.id}
        except stripe.error.StripeError as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def create_checkout_session(email: str, price_id: str, success_url: str, cancel_url: str) -> Dict:
        """Create a Stripe checkout session"""
        try:
            session = stripe.checkout.Session.create(
                customer_email=email,
                line_items=[{"price": price_id, "quantity": 1}],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"email": email, "created_at": datetime.now().isoformat()}
            )
            return {"success": True, "session_id": session.id, "url": session.url}
        except stripe.error.StripeError as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_subscription(customer_id: str) -> Dict:
        """Get customer's active subscription"""
        try:
            subscriptions = stripe.Subscription.list(
                customer=customer_id,
                status="active",
                limit=1
            )
            
            if subscriptions.data:
                sub = subscriptions.data[0]
                return {
                    "success": True,
                    "subscription_id": sub.id,
                    "status": sub.status,
                    "price_id": sub.items.data[0].price.id,
                    "current_period_end": sub.current_period_end,
                    "cancel_at_period_end": sub.cancel_at_period_end
                }
            else:
                return {"success": False, "error": "No active subscription"}
        except stripe.error.StripeError as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def cancel_subscription(subscription_id: str) -> Dict:
        """Cancel a subscription at end of period"""
        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
            return {"success": True, "status": subscription.status}
        except stripe.error.StripeError as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_invoice_history(customer_id: str) -> Dict:
        """Get customer's invoice history"""
        try:
            invoices = stripe.Invoice.list(customer=customer_id, limit=10)
            return {
                "success": True,
                "invoices": [{
                    "id": inv.id,
                    "date": inv.created,
                    "amount": inv.total,
                    "status": inv.status,
                    "url": inv.hosted_invoice_url
                } for inv in invoices.data]
            }
        except stripe.error.StripeError as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def handle_webhook(payload: Dict, sig_header: str) -> Dict:
        """Process Stripe webhook"""
        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                os.getenv("STRIPE_WEBHOOK_SECRET")
            )
            
            event_type = event["type"]
            data = event["data"]["object"]
            
            # Handle different event types
            if event_type == "customer.subscription.created":
                return {"action": "subscription_created", "customer_id": data["customer"]}
            elif event_type == "customer.subscription.updated":
                return {"action": "subscription_updated", "customer_id": data["customer"]}
            elif event_type == "customer.subscription.deleted":
                return {"action": "subscription_deleted", "customer_id": data["customer"]}
            elif event_type == "invoice.payment_succeeded":
                return {"action": "payment_succeeded", "customer_id": data["customer"]}
            elif event_type == "invoice.payment_failed":
                return {"action": "payment_failed", "customer_id": data["customer"]}
            else:
                return {"action": "event_received", "type": event_type}
                
        except ValueError:
            return {"success": False, "error": "Invalid payload"}
        except stripe.error.SignatureVerificationError:
            return {"success": False, "error": "Invalid signature"}


# Pricing constants for frontend
TIERS = {
    "free": {
        "name": "Free",
        "price": "$0",
        "videos_per_month": 3,
        "features": [
            "Summary only",
            "Basic transcription",
            "Email support"
        ]
    },
    "starter": {
        "name": "Starter",
        "price": "$29",
        "videos_per_month": 50,
        "price_id": PRICES["starter"],
        "features": [
            "Full analysis",
            "Twitter threads",
            "Show notes",
            "SEO metadata",
            "Email support"
        ]
    },
    "professional": {
        "name": "Professional",
        "price": "$99",
        "videos_per_month": 500,
        "price_id": PRICES["professional"],
        "features": [
            "Everything in Starter",
            "API access",
            "Batch processing",
            "Priority support",
            "Custom integrations"
        ]
    }
}

if __name__ == "__main__":
    # Test Stripe connection
    try:
        account = stripe.Account.retrieve()
        print(f"✅ Stripe connected: {account.email}")
        print(f"Tiers available: {list(TIERS.keys())}")
    except Exception as e:
        print(f"❌ Stripe connection failed: {str(e)}")
