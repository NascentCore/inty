#!/usr/bin/env python3
"""
Google Play Service Account Verification Script

This script verifies that the Google Cloud Service Account has the proper permissions
to access the Google Play Developer API for subscription validation.

Usage:
    python scripts/verify_google_play_service_account.py
"""

import json
import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timezone
import traceback

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Test purchase token from the error logs
TEST_PURCHASE_TOKEN = "ccdjlaolioidnhfbjgknfdip.AO-J1OzF2In1NkiyhGz_uPjYqjxHUa0_jQknEb8e-b__DfSspV8xSVl5v78pkREr_Ivebve4oJ3BSDyzZlMrZLuFcPfswHQIAA"

# Common subscription product IDs to test
TEST_SUBSCRIPTION_PRODUCT_IDS = [
    "com.ai.inty.premium.monthly",
    "com.ai.inty.premium.yearly",
    "com.ai.inty.premium.quarterly",
]

# Common in-app product IDs to test
TEST_INAPP_PRODUCT_IDS = [
    "com.ai.inty.coins.100",
    "com.ai.inty.coins.500",
    "com.ai.inty.coins.1000",
    "com.ai.inty.remove_ads",
    "com.ai.inty.unlock_premium",
    "com.ai.inty.extra_features",
]


class GooglePlayVerifier:
    """Google Play Service Account Verifier"""

    def __init__(self):
        """Initialize the verifier"""
        self.service = None
        self.package_name = None
        self.service_account_key_path = None
        self.results = {
            "config_validation": {},
            "authentication": {},
            "permissions": {},
            "subscription_tests": {},
            "inapp_product_tests": {},
            "product_catalog": {},
            "diagnostics": {},
        }

    def run_verification(self) -> Dict[str, Any]:
        """Run the complete verification process"""
        print("=" * 60)
        print("🔍 Google Play Service Account Verification")
        print("=" * 60)

        try:
            # Step 1: Validate configuration
            print("\n1. 📋 Validating Configuration...")
            self._validate_configuration()

            # Step 2: Test authentication
            print("\n2. 🔑 Testing Authentication...")
            self._test_authentication()

            # Step 3: Test permissions
            print("\n3. 🛡️  Testing Permissions...")
            self._test_permissions()

            # Step 4: Test subscription operations
            print("\n4. 📦 Testing Subscription Operations...")
            self._test_subscription_operations()

            # Step 5: Test in-app product operations
            print("\n5. 🛒 Testing In-App Product Operations...")
            self._test_inapp_product_operations()

            # Step 6: Retrieve product catalog
            print("\n6. 📋 Retrieving Product Catalog...")
            self._retrieve_product_catalog()

            # Step 7: Generate diagnostics
            print("\n7. 🔬 Generating Diagnostics...")
            self._generate_diagnostics()

        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
            self.results["error"] = str(e)
            self.results["traceback"] = traceback.format_exc()

        # Print final report
        self._print_final_report()

        return self.results

    def _validate_configuration(self) -> None:
        """Validate the configuration settings"""
        config_result = self.results["config_validation"]

        # Check if Google Play configuration exists
        if not hasattr(settings, "google_play"):
            config_result["google_play_config"] = {
                "status": "❌ FAILED",
                "error": "Google Play configuration not found in settings",
            }
            return

        # Check package name
        self.package_name = settings.google_play.package_name
        if not self.package_name:
            config_result["package_name"] = {
                "status": "❌ FAILED",
                "error": "Package name not configured",
            }
        else:
            config_result["package_name"] = {
                "status": "✅ PASSED",
                "value": self.package_name,
            }
            print(f"   📱 Package Name: {self.package_name}")

        # Check service account key
        service_account_key = settings.google_play.service_account_key
        if not service_account_key:
            config_result["service_account_key"] = {
                "status": "❌ FAILED",
                "error": "Service account key not configured",
            }
            return

        # Check if it's a file path or JSON string
        if service_account_key.endswith(".json"):
            self.service_account_key_path = service_account_key
            key_path = Path(service_account_key)

            if not key_path.exists():
                config_result["service_account_key"] = {
                    "status": "❌ FAILED",
                    "error": f"Service account key file not found: {service_account_key}",
                }
                return

            if not key_path.is_file():
                config_result["service_account_key"] = {
                    "status": "❌ FAILED",
                    "error": f"Service account key path is not a file: {service_account_key}",
                }
                return

            # Try to read and parse the JSON file
            try:
                with open(key_path, "r") as f:
                    service_account_info = json.load(f)

                config_result["service_account_key"] = {
                    "status": "✅ PASSED",
                    "type": "file",
                    "path": str(key_path),
                    "client_email": service_account_info.get("client_email"),
                    "project_id": service_account_info.get("project_id"),
                }
                print(f"   🔑 Service Account File: {key_path}")
                print(f"   📧 Client Email: {service_account_info.get('client_email')}")
                print(f"   🏗️  Project ID: {service_account_info.get('project_id')}")

            except json.JSONDecodeError as e:
                config_result["service_account_key"] = {
                    "status": "❌ FAILED",
                    "error": f"Invalid JSON in service account key file: {str(e)}",
                }
                return
            except Exception as e:
                config_result["service_account_key"] = {
                    "status": "❌ FAILED",
                    "error": f"Error reading service account key file: {str(e)}",
                }
                return
        else:
            # It's a JSON string
            try:
                service_account_info = json.loads(service_account_key)
                config_result["service_account_key"] = {
                    "status": "✅ PASSED",
                    "type": "json_string",
                    "client_email": service_account_info.get("client_email"),
                    "project_id": service_account_info.get("project_id"),
                }
                print(f"   🔑 Service Account: JSON string")
                print(f"   📧 Client Email: {service_account_info.get('client_email')}")
                print(f"   🏗️  Project ID: {service_account_info.get('project_id')}")

            except json.JSONDecodeError as e:
                config_result["service_account_key"] = {
                    "status": "❌ FAILED",
                    "error": f"Invalid JSON in service account key: {str(e)}",
                }
                return

    def _test_authentication(self) -> None:
        """Test authentication to Google Play Developer API"""
        auth_result = self.results["authentication"]

        if not self.package_name:
            auth_result["initialization"] = {
                "status": "❌ FAILED",
                "error": "Package name not available from configuration validation",
            }
            return

        try:
            # Get service account credentials
            service_account_key = settings.google_play.service_account_key

            if service_account_key.endswith(".json"):
                # File path
                key_path = Path(service_account_key)
                with open(key_path, "r") as f:
                    service_account_info = json.load(f)
            else:
                # JSON string
                service_account_info = json.loads(service_account_key)

            # Create credentials
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=["https://www.googleapis.com/auth/androidpublisher"],
            )

            auth_result["credentials"] = {
                "status": "✅ PASSED",
                "scopes": ["https://www.googleapis.com/auth/androidpublisher"],
            }
            print(f"   🔐 Credentials created successfully")

            # Build the service
            self.service = build("androidpublisher", "v3", credentials=credentials)

            auth_result["service"] = {"status": "✅ PASSED", "version": "v3"}
            print(f"   🔧 Google Play Developer API service initialized")

        except Exception as e:
            auth_result["error"] = {
                "status": "❌ FAILED",
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
            print(f"   ❌ Authentication failed: {str(e)}")

    def _test_permissions(self) -> None:
        """Test Google Play API permissions"""
        permissions_result = self.results["permissions"]

        if not self.service:
            permissions_result["service_unavailable"] = {
                "status": "❌ FAILED",
                "error": "Google Play service not initialized",
            }
            return

        # Test different permission levels
        self._test_basic_api_access()
        self._test_subscription_permissions()
        self._test_purchase_permissions()

    def _test_basic_api_access(self) -> None:
        """Test basic API access"""
        try:
            # Try to access the API with a simple call
            # This will fail if there are basic permission issues
            _ = self.service.purchases()

            self.results["permissions"]["basic_api_access"] = {
                "status": "✅ PASSED",
                "message": "Basic API access successful",
            }
            print(f"   ✅ Basic API access: PASSED")

        except Exception as e:
            self.results["permissions"]["basic_api_access"] = {
                "status": "❌ FAILED",
                "error": str(e),
            }
            print(f"   ❌ Basic API access: FAILED - {str(e)}")

    def _test_subscription_permissions(self) -> None:
        """Test subscription-specific permissions"""
        try:
            # Test subscription API access
            _ = self.service.purchases().subscriptions()

            self.results["permissions"]["subscription_api"] = {
                "status": "✅ PASSED",
                "message": "Subscription API access successful",
            }
            print(f"   ✅ Subscription API access: PASSED")

        except Exception as e:
            self.results["permissions"]["subscription_api"] = {
                "status": "❌ FAILED",
                "error": str(e),
            }
            print(f"   ❌ Subscription API access: FAILED - {str(e)}")

    def _test_purchase_permissions(self) -> None:
        """Test purchase-specific permissions"""
        try:
            # Test purchase API access
            _ = self.service.purchases().products()

            self.results["permissions"]["purchase_api"] = {
                "status": "✅ PASSED",
                "message": "Purchase API access successful",
            }
            print(f"   ✅ Purchase API access: PASSED")

        except Exception as e:
            self.results["permissions"]["purchase_api"] = {
                "status": "❌ FAILED",
                "error": str(e),
            }
            print(f"   ❌ Purchase API access: FAILED - {str(e)}")

    def _test_subscription_operations(self) -> None:
        """Test actual subscription operations"""
        subscription_result = self.results["subscription_tests"]

        if not self.service:
            subscription_result["service_unavailable"] = {
                "status": "❌ FAILED",
                "error": "Google Play service not initialized",
            }
            return

        # Test with the actual purchase token from the error logs
        print(f"   🧪 Testing with purchase token: {TEST_PURCHASE_TOKEN[:20]}...")

        # Test different product IDs
        for product_id in TEST_SUBSCRIPTION_PRODUCT_IDS:
            print(f"   📦 Testing product ID: {product_id}")
            self._test_single_subscription(product_id, TEST_PURCHASE_TOKEN)

    def _test_single_subscription(self, product_id: str, purchase_token: str) -> None:
        """Test a single subscription"""
        try:
            # Try to get subscription details
            result = (
                self.service.purchases()
                .subscriptions()
                .get(
                    packageName=self.package_name,
                    subscriptionId=product_id,
                    token=purchase_token,
                )
                .execute()
            )

            self.results["subscription_tests"][product_id] = {
                "status": "✅ PASSED",
                "message": "Subscription retrieved successfully",
                "data": {
                    "start_time": result.get("startTimeMillis"),
                    "expiry_time": result.get("expiryTimeMillis"),
                    "auto_renewing": result.get("autoRenewing"),
                    "payment_state": result.get("paymentState"),
                    "order_id": result.get("orderId"),
                },
            }
            print(f"      ✅ {product_id}: SUCCESS")

            # Print subscription details
            if result.get("startTimeMillis"):
                start_time = datetime.fromtimestamp(
                    int(result.get("startTimeMillis")) / 1000, timezone.utc
                )
                print(f"         📅 Start Time: {start_time}")

            if result.get("expiryTimeMillis"):
                expiry_time = datetime.fromtimestamp(
                    int(result.get("expiryTimeMillis")) / 1000, timezone.utc
                )
                print(f"         ⏰ Expiry Time: {expiry_time}")

            print(f"         🔄 Auto Renewing: {result.get('autoRenewing')}")
            print(f"         💳 Payment State: {result.get('paymentState')}")

        except HttpError as e:
            error_details = self._parse_http_error(e)
            self.results["subscription_tests"][product_id] = {
                "status": "❌ FAILED",
                "error": error_details,
                "http_status": e.resp.status,
                "error_content": e.content.decode() if e.content else None,
            }
            print(f"      ❌ {product_id}: FAILED - {error_details['message']}")

            # Print additional error details
            if error_details.get("reason"):
                print(f"         🔍 Reason: {error_details['reason']}")
            if error_details.get("domain"):
                print(f"         🌐 Domain: {error_details['domain']}")

        except Exception as e:
            self.results["subscription_tests"][product_id] = {
                "status": "❌ FAILED",
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
            print(f"      ❌ {product_id}: FAILED - {str(e)}")

    def _test_inapp_product_operations(self) -> None:
        """Test in-app product operations"""
        inapp_result = self.results["inapp_product_tests"]

        if not self.service:
            inapp_result["service_unavailable"] = {
                "status": "❌ FAILED",
                "error": "Google Play service not initialized",
            }
            return

        # Test with the actual purchase token from the error logs
        print(f"   🧪 Testing with purchase token: {TEST_PURCHASE_TOKEN[:20]}...")

        # Test different in-app product IDs
        for product_id in TEST_INAPP_PRODUCT_IDS:
            print(f"   🛒 Testing in-app product ID: {product_id}")
            self._test_single_inapp_product(product_id, TEST_PURCHASE_TOKEN)

    def _test_single_inapp_product(self, product_id: str, purchase_token: str) -> None:
        """Test a single in-app product"""
        try:
            # Try to get in-app product purchase details
            result = (
                self.service.purchases()
                .products()
                .get(
                    packageName=self.package_name,
                    productId=product_id,
                    token=purchase_token,
                )
                .execute()
            )

            self.results["inapp_product_tests"][product_id] = {
                "status": "✅ PASSED",
                "message": "In-app product purchase retrieved successfully",
                "data": {
                    "purchase_time": result.get("purchaseTimeMillis"),
                    "purchase_state": result.get("purchaseState"),
                    "consumption_state": result.get("consumptionState"),
                    "developer_payload": result.get("developerPayload"),
                    "order_id": result.get("orderId"),
                    "acknowledgement_state": result.get("acknowledgementState"),
                },
            }
            print(f"      ✅ {product_id}: SUCCESS")

            # Print purchase details
            if result.get("purchaseTimeMillis"):
                purchase_time = datetime.fromtimestamp(
                    int(result.get("purchaseTimeMillis")) / 1000, timezone.utc
                )
                print(f"         📅 Purchase Time: {purchase_time}")

            purchase_state = result.get("purchaseState", 0)
            state_names = {0: "Purchased", 1: "Canceled", 2: "Pending"}
            print(
                f"         💳 Purchase State: {state_names.get(purchase_state, purchase_state)}"
            )

            consumption_state = result.get("consumptionState", 0)
            consumption_names = {0: "Yet to be consumed", 1: "Consumed"}
            print(
                f"         🍽️  Consumption State: {consumption_names.get(consumption_state, consumption_state)}"
            )

            acknowledgement_state = result.get("acknowledgementState", 0)
            ack_names = {0: "Yet to be acknowledged", 1: "Acknowledged"}
            print(
                f"         ✅ Acknowledgement State: {ack_names.get(acknowledgement_state, acknowledgement_state)}"
            )

        except HttpError as e:
            error_details = self._parse_http_error(e)
            self.results["inapp_product_tests"][product_id] = {
                "status": "❌ FAILED",
                "error": error_details,
                "http_status": e.resp.status,
                "error_content": e.content.decode() if e.content else None,
            }
            print(f"      ❌ {product_id}: FAILED - {error_details['message']}")

            # Print additional error details
            if error_details.get("reason"):
                print(f"         🔍 Reason: {error_details['reason']}")
            if error_details.get("domain"):
                print(f"         🌐 Domain: {error_details['domain']}")

        except Exception as e:
            self.results["inapp_product_tests"][product_id] = {
                "status": "❌ FAILED",
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
            print(f"      ❌ {product_id}: FAILED - {str(e)}")

    def _retrieve_product_catalog(self) -> None:
        """Retrieve and display product catalog from Google Play Console"""
        catalog_result = self.results["product_catalog"]

        if not self.service:
            catalog_result["service_unavailable"] = {
                "status": "❌ FAILED",
                "error": "Google Play service not initialized",
            }
            return

        # Retrieve subscription products
        print("   📦 Retrieving Subscription Products...")
        self._get_subscription_products()

        # Retrieve in-app products
        print("   🛒 Retrieving In-App Products...")
        self._get_inapp_products()

    def _get_subscription_products(self) -> None:
        """Get subscription products from Google Play Console"""
        try:
            # Get subscription products using the monetization API
            result = (
                self.service.monetization()
                .subscriptions()
                .list(packageName=self.package_name)
                .execute()
            )

            subscriptions = result.get("subscriptions", [])

            self.results["product_catalog"]["subscriptions"] = {
                "status": "✅ PASSED",
                "count": len(subscriptions),
                "products": subscriptions,
            }

            print(f"      ✅ Found {len(subscriptions)} subscription products")

            # Display subscription details
            for subscription in subscriptions:
                product_id = subscription.get("productId", "Unknown")
                print(f"         📦 {product_id}")

                # Get base plan info
                base_plans = subscription.get("basePlans", [])
                for base_plan in base_plans:
                    base_plan_id = base_plan.get("basePlanId", "Unknown")
                    state = base_plan.get("state", "Unknown")
                    print(f"            📋 Base Plan: {base_plan_id} (State: {state})")

                    # Get pricing info
                    regional_configs = base_plan.get("regionalConfigs", [])
                    for config in regional_configs:
                        region = config.get("regionCode", "Unknown")
                        price = config.get("price", {})
                        currency = price.get("currencyCode", "Unknown")
                        units = price.get("units", "0")
                        nanos = price.get("nanos", 0)
                        amount = float(units) + (nanos / 1_000_000_000)
                        print(f"               💰 {region}: {amount} {currency}")

                        # Only show first few regions to avoid clutter
                        if len(regional_configs) > 3:
                            remaining = len(regional_configs) - 3
                            print(f"               ... and {remaining} more regions")
                            break

                    # Get billing period
                    auto_renewing_plan = base_plan.get("autoRenewingBasePlanType", {})
                    billing_period = auto_renewing_plan.get("billingPeriod", "Unknown")
                    if billing_period != "Unknown":
                        print(f"            🔄 Billing Period: {billing_period}")

                print()  # Empty line between products

        except HttpError as e:
            error_details = self._parse_http_error(e)
            self.results["product_catalog"]["subscriptions"] = {
                "status": "❌ FAILED",
                "error": error_details,
                "http_status": e.resp.status,
                "error_content": e.content.decode() if e.content else None,
            }
            print(
                f"      ❌ Failed to retrieve subscription products: {error_details['message']}"
            )

            # Print additional error details
            if error_details.get("reason"):
                print(f"         🔍 Reason: {error_details['reason']}")
            if error_details.get("domain"):
                print(f"         🌐 Domain: {error_details['domain']}")

        except Exception as e:
            self.results["product_catalog"]["subscriptions"] = {
                "status": "❌ FAILED",
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
            print(f"      ❌ Failed to retrieve subscription products: {str(e)}")

    def _get_inapp_products(self) -> None:
        """Get in-app products from Google Play Console"""
        try:
            # Get in-app products using the legacy inappproducts API
            # Note: The monetization API doesn't have a products() method for in-app products
            result = (
                self.service.inappproducts()
                .list(packageName=self.package_name)
                .execute()
            )

            products = result.get("inappproduct", [])

            self.results["product_catalog"]["inapp_products"] = {
                "status": "✅ PASSED",
                "count": len(products),
                "products": products,
            }

            print(f"      ✅ Found {len(products)} in-app products")

            # Display product details
            for product in products:
                product_id = product.get("sku", "Unknown")
                status = product.get("status", "Unknown")
                print(f"         🛒 {product_id} (Status: {status})")

                # Get pricing info
                prices = product.get("prices", {})
                for currency, price_info in prices.items():
                    price_amount = price_info.get("priceMicros", 0)
                    amount = price_amount / 1_000_000
                    print(f"            💰 {currency}: {amount}")

                    # Only show first few currencies to avoid clutter
                    if len(prices) > 3:
                        remaining = len(prices) - 3
                        print(f"            ... and {remaining} more currencies")
                        break

                # Get purchase type
                purchase_type = product.get("purchaseType", "Unknown")
                if purchase_type != "Unknown":
                    print(f"            📋 Purchase Type: {purchase_type}")

                # Get listings (localized info)
                listings = product.get("listings", {})
                if listings:
                    # Show first listing
                    first_lang = list(listings.keys())[0] if listings else None
                    if first_lang:
                        listing = listings[first_lang]
                        title = listing.get("title", "Unknown")
                        print(f"            📝 Title ({first_lang}): {title}")

                print()  # Empty line between products

        except HttpError as e:
            error_details = self._parse_http_error(e)
            self.results["product_catalog"]["inapp_products"] = {
                "status": "❌ FAILED",
                "error": error_details,
                "http_status": e.resp.status,
                "error_content": e.content.decode() if e.content else None,
            }
            print(
                f"      ❌ Failed to retrieve in-app products: {error_details['message']}"
            )

            # Print additional error details
            if error_details.get("reason"):
                print(f"         🔍 Reason: {error_details['reason']}")
            if error_details.get("domain"):
                print(f"         🌐 Domain: {error_details['domain']}")

        except Exception as e:
            self.results["product_catalog"]["inapp_products"] = {
                "status": "❌ FAILED",
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
            print(f"      ❌ Failed to retrieve in-app products: {str(e)}")

    def _parse_http_error(self, error: HttpError) -> Dict[str, Any]:
        """Parse HttpError to extract meaningful information"""
        error_info = {"status_code": error.resp.status, "message": str(error)}

        try:
            if error.content:
                error_content = json.loads(error.content.decode())
                error_info["full_response"] = error_content

                # Extract error details
                if "error" in error_content:
                    error_details = error_content["error"]
                    error_info["message"] = error_details.get("message", str(error))
                    error_info["errors"] = error_details.get("errors", [])

                    if error_info["errors"]:
                        first_error = error_info["errors"][0]
                        error_info["reason"] = first_error.get("reason")
                        error_info["domain"] = first_error.get("domain")
                        error_info["message"] = first_error.get(
                            "message", error_info["message"]
                        )

        except (json.JSONDecodeError, KeyError):
            pass

        return error_info

    def _generate_diagnostics(self) -> None:
        """Generate diagnostic information and recommendations"""
        diagnostics = self.results["diagnostics"]

        # Check overall health
        has_config_issues = any(
            result.get("status") == "❌ FAILED"
            for result in self.results["config_validation"].values()
        )

        has_auth_issues = any(
            result.get("status") == "❌ FAILED"
            for result in self.results["authentication"].values()
        )

        has_permission_issues = any(
            result.get("status") == "❌ FAILED"
            for result in self.results["permissions"].values()
        )

        has_subscription_issues = any(
            result.get("status") == "❌ FAILED"
            for result in self.results["subscription_tests"].values()
        )

        has_inapp_issues = any(
            result.get("status") == "❌ FAILED"
            for result in self.results["inapp_product_tests"].values()
        )

        has_catalog_issues = any(
            result.get("status") == "❌ FAILED"
            for result in self.results["product_catalog"].values()
        )

        diagnostics["overall_health"] = {
            "configuration": "✅ HEALTHY" if not has_config_issues else "❌ ISSUES",
            "authentication": "✅ HEALTHY" if not has_auth_issues else "❌ ISSUES",
            "permissions": "✅ HEALTHY" if not has_permission_issues else "❌ ISSUES",
            "subscription_operations": (
                "✅ HEALTHY" if not has_subscription_issues else "❌ ISSUES"
            ),
            "inapp_product_operations": (
                "✅ HEALTHY" if not has_inapp_issues else "❌ ISSUES"
            ),
            "product_catalog": "✅ HEALTHY" if not has_catalog_issues else "❌ ISSUES",
        }

        # Generate recommendations
        recommendations = []

        if has_config_issues:
            recommendations.append(
                {
                    "issue": "Configuration Problems",
                    "solution": "Check your config.yaml file and ensure all Google Play settings are properly configured",
                }
            )

        if has_auth_issues:
            recommendations.append(
                {
                    "issue": "Authentication Problems",
                    "solution": "Verify your service account key file is valid and has the correct format",
                }
            )

        if has_permission_issues:
            recommendations.append(
                {
                    "issue": "Permission Problems",
                    "solution": [
                        "1. Go to Google Play Console -> Setup -> API access",
                        "2. Ensure your service account is linked to your Google Play Console account",
                        "3. Grant the following permissions to your service account:",
                        "   - View financial reports",
                        "   - View app information and download bulk reports",
                        "   - Manage orders and subscriptions",
                        "4. Make sure the service account has the 'Android Publisher' role",
                    ],
                }
            )

        if has_subscription_issues:
            recommendations.append(
                {
                    "issue": "Subscription Operation Problems",
                    "solution": [
                        "1. Verify the package name matches your Google Play Console app",
                        "2. Check if the subscription products are properly configured in Google Play Console",
                        "3. Ensure the purchase token is valid and from the correct app",
                        "4. Verify the service account has subscription management permissions",
                    ],
                }
            )

        if has_inapp_issues:
            recommendations.append(
                {
                    "issue": "In-App Product Operation Problems",
                    "solution": [
                        "1. Verify the package name matches your Google Play Console app",
                        "2. Check if the in-app products are properly configured in Google Play Console",
                        "3. Ensure the purchase token is valid and from the correct app",
                        "4. Verify the service account has in-app product management permissions",
                        "5. Check if the in-app products are published and available in the console",
                    ],
                }
            )

        if has_catalog_issues:
            recommendations.append(
                {
                    "issue": "Product Catalog Retrieval Problems",
                    "solution": [
                        "1. Verify the service account has 'View app information' permission in Google Play Console",
                        "2. Check if the monetization API is enabled for your project",
                        "3. Ensure the service account has the correct roles and permissions",
                        "4. Verify the package name matches your Google Play Console app",
                    ],
                }
            )

        diagnostics["recommendations"] = recommendations

        # Generate next steps
        next_steps = []

        if has_permission_issues:
            next_steps.append("Fix Google Play Console API access and permissions")

        if has_subscription_issues:
            next_steps.append(
                "Verify subscription configuration in Google Play Console"
            )

        if has_inapp_issues:
            next_steps.append(
                "Verify in-app product configuration in Google Play Console"
            )

        if has_catalog_issues:
            next_steps.append(
                "Fix product catalog retrieval permissions in Google Play Console"
            )

        if not any(
            [
                has_config_issues,
                has_auth_issues,
                has_permission_issues,
                has_subscription_issues,
                has_inapp_issues,
                has_catalog_issues,
            ]
        ):
            next_steps.append(
                "All tests passed! Your Google Play integration should be working correctly."
            )

        diagnostics["next_steps"] = next_steps

    def _print_final_report(self) -> None:
        """Print the final verification report"""
        print("\n" + "=" * 60)
        print("📊 VERIFICATION REPORT")
        print("=" * 60)

        # Overall status
        diagnostics = self.results["diagnostics"]
        if "overall_health" in diagnostics:
            print("\n🏥 Overall Health:")
            for component, status in diagnostics["overall_health"].items():
                print(f"   {component.title()}: {status}")

        # Recommendations
        if "recommendations" in diagnostics and diagnostics["recommendations"]:
            print("\n💡 Recommendations:")
            for i, rec in enumerate(diagnostics["recommendations"], 1):
                print(f"\n   {i}. {rec['issue']}:")
                if isinstance(rec["solution"], list):
                    for step in rec["solution"]:
                        print(f"      {step}")
                else:
                    print(f"      {rec['solution']}")

        # Next steps
        if "next_steps" in diagnostics and diagnostics["next_steps"]:
            print("\n🚀 Next Steps:")
            for i, step in enumerate(diagnostics["next_steps"], 1):
                print(f"   {i}. {step}")

        print("\n" + "=" * 60)
        print("✅ Verification Complete")
        print("=" * 60)


def main():
    """Main function"""
    verifier = GooglePlayVerifier()
    results = verifier.run_verification()

    # Save results to file
    results_file = "google_play_verification_results.json"
    try:
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Results saved to: {results_file}")
    except Exception as e:
        print(f"\n❌ Failed to save results: {str(e)}")

    # Return exit code based on results
    if "error" in results:
        return 1

    # Check if there are any critical failures
    has_critical_failures = any(
        [
            any(
                result.get("status") == "❌ FAILED"
                for result in results.get("config_validation", {}).values()
            ),
            any(
                result.get("status") == "❌ FAILED"
                for result in results.get("authentication", {}).values()
            ),
        ]
    )

    return 1 if has_critical_failures else 0


if __name__ == "__main__":
    sys.exit(main())
