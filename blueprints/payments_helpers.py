import requests
from flask import current_app
#from uuid import uuid4
from utils import get_marz_authorization_header
import os
import uuid
import json
def send_withdraw_request(withdraw_obj):
    """
    Sends a withdrawal request to MarzPay securely.
    withdraw_obj: instance of Withdrawal model.
    """
    # if withdraw_obj is None:
    #     raise ValueError("withdraw_obj is None")

    # if withdraw_obj.amount is None or withdraw_obj.amount <= 0:
    #     raise ValueError("Withdrawal amount must be positive")

    # phone = withdraw_obj.phone or ""
    # if not phone.strip():
    #     raise ValueError("Phone number is missing")

   