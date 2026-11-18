"""Quản lý taxonomy 10 flow / 55 subflow, chuẩn hóa alias và phân lập danh mục K vs Full."""
from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple
from .policy import AccessPolicy, LeakageError

FLOW_SUBFLOW_CANONICAL: Dict[str, List[str]] = {
    'account_access': ['recover_username', 'recover_password', 'reset_2fa'],
    'manage_account': [
        'status_service_added', 'status_service_removed', 'status_shipping_question',
        'status_credit_missing', 'manage_change_address', 'manage_change_name',
        'manage_change_phone', 'manage_payment_method'
    ],
    'order_issue': [
        'status_mystery_fee', 'status_delivery_time', 'status_payment_method',
        'status_quantity', 'manage_upgrade', 'manage_downgrade', 'manage_create', 'manage_cancel'
    ],
    'product_defect': [
        'refund_initiate', 'refund_update', 'refund_status',
        'return_stain', 'return_color', 'return_size'
    ],
    'purchase_dispute': [
        'bad_price_competitor', 'bad_price_yesterday', 'out_of_stock_general',
        'out_of_stock_one_item', 'promo_code_invalid', 'promo_code_out_of_date',
        'mistimed_billing_already_returned', 'mistimed_billing_never_bought'
    ],
    'shipping_issue': ['status', 'manage', 'missing', 'cost'],
    'single_item_query': ['boots', 'shirt', 'jeans', 'jacket'],
    'storewide_query': ['pricing', 'membership', 'timing', 'policy'],
    'subscription_inquiry': [
        'status_active', 'status_due_amount', 'status_due_date',
        'manage_pay_bill', 'manage_extension', 'manage_dispute_bill'
    ],
    'troubleshoot_site': ['credit_card', 'shopping_cart', 'search_results', 'slow_speed']
}

KNOWN_K_FLOWS = [
    'account_access', 'manage_account', 'order_issue', 'product_defect',
    'purchase_dispute', 'single_item_query', 'storewide_query'
]
HIDDEN_DEV_FLOWS = ['shipping_issue']
HIDDEN_FINAL_FLOWS = ['subscription_inquiry', 'troubleshoot_site']

FLOW_DESCRIPTIONS_EN = {
    'account_access': "Customer inquiries about accessing their account, logging in, recovering forgotten username, password resets, or 2FA two-factor authentication issues.",
    'manage_account': "Customer inquiries about managing account settings, updating address, name, phone number, payment methods, or viewing added or removed account services.",
    'order_issue': "Customer inquiries about issues with existing orders, unexpected fees, delivery times, incorrect quantities, payment problems, or order creation, cancellation, upgrade or downgrade.",
    'product_defect': "Customer inquiries regarding defective items, stains, incorrect sizes or colors, requesting returns, exchanges, or initiating and tracking refunds.",
    'purchase_dispute': "Customer inquiries disputing purchase pricing, price matching competitor prices or previous discounts, expired promo codes, out-of-stock items, or mistimed charges.",
    'single_item_query': "Customer inquiries about specific individual apparel products such as boots, shirts, jeans, or jackets regarding availability, sizing, or product details.",
    'storewide_query': "Customer inquiries regarding general storewide policies, operating hours or timing, membership programs, rewards, and general pricing policies.",
    'shipping_issue': "Customer inquiries regarding shipping carrier status, tracking missing packages, managing delivery preferences, or shipping costs.",
    'subscription_inquiry': "Customer inquiries about recurring subscriptions, active membership status, due dates and amounts, paying bills, extensions, or billing disputes.",
    'troubleshoot_site': "Customer inquiries regarding website technical troubleshooting, shopping cart errors, payment card checkout failures, search result glitches, or slow page loading."
}


def flow_id(flow: str) -> str:
    return f"flow:{flow}"


def subflow_id(flow: str, subflow: str) -> str:
    return f"subflow:{flow}/{subflow}"


def resolve_alias(flow: str, raw_label: str) -> Tuple[Optional[str], str, str]:
    """
    Chuẩn hóa alias theo ontology rules:
    Trả về (canonical_subflow, mapping_rule, resolution_status)
    """
    if flow not in FLOW_SUBFLOW_CANONICAL:
        return None, 'unknown_flow', 'unresolved'

    canonical_subs = FLOW_SUBFLOW_CANONICAL[flow]
    if raw_label in canonical_subs:
        return raw_label, 'canonical', 'resolved'

    # Special unresolved cases from ontology
    if (flow == 'subscription_inquiry' and raw_label == 'status_questions') or \
       (flow == 'order_issue' and raw_label == 'status_delivery_date'):
        return None, 'ambiguous_ontology_label', 'unresolved'

    # single_item_query alias: <item>_how_<n> or <item>_other_<n>
    if flow == 'single_item_query':
        m = re.match(r'^([a-z]+)_(how|other)_([1-4])$', raw_label)
        if m and m.group(1) in canonical_subs:
            return m.group(1), 'ontology_item_alias', 'resolved'

    # storewide_query alias: <category>_<n>
    if flow == 'storewide_query':
        m = re.match(r'^([a-z]+)_([1-4])$', raw_label)
        if m and m.group(1) in canonical_subs:
            return m.group(1), 'ontology_category_alias', 'resolved'

    return None, 'unrecognized_alias', 'unresolved'


def get_known_taxonomy() -> Dict:
    """Trả về taxonomy chỉ gồm các flow và subflow thuộc Known K."""
    return {
        'version': '1.0.0',
        'scope': 'known_k',
        'flows': {
            f: {
                'id': flow_id(f),
                'name': f,
                'description': FLOW_DESCRIPTIONS_EN[f],
                'subflows': {
                    s: {
                        'id': subflow_id(f, s),
                        'name': s
                    }
                    for s in FLOW_SUBFLOW_CANONICAL[f]
                }
            }
            for f in KNOWN_K_FLOWS
        }
    }


def get_full_taxonomy(policy: Optional[AccessPolicy] = None) -> Dict:
    """Trả về full taxonomy 10 flow / 55 subflow; kiểm tra gate G2 qua policy."""
    if policy is not None:
        policy.authorize('reviewer', 'taxonomy_full', 'full_review')

    return {
        'version': '1.0.0',
        'scope': 'full_10_55',
        'flows': {
            f: {
                'id': flow_id(f),
                'name': f,
                'description': FLOW_DESCRIPTIONS_EN[f],
                'subflows': {
                    s: {
                        'id': subflow_id(f, s),
                        'name': s
                    }
                    for s in FLOW_SUBFLOW_CANONICAL[f]
                }
            }
            for f in FLOW_SUBFLOW_CANONICAL
        }
    }
